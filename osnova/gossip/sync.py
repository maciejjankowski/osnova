"""Pull-based gossip sync between Osnova nodes."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx

from osnova.schemas import ContentEntry, RingLevel, SyncRequest, SyncResponse

if TYPE_CHECKING:
    from osnova.rings.manager import RingManager
    from osnova.storage.log import ContentLog

logger = logging.getLogger(__name__)


class GossipService:
    """Handles pull-based gossip between nodes.

    Each round a node asks its CORE and INNER peers:
    "what do you have that I don't?" - then appends the diff.
    """

    def __init__(
        self,
        content_log: "ContentLog",
        ring_manager: "RingManager",
        node_public_key: str,
    ) -> None:
        self._log = content_log
        self._rings = ring_manager
        self._node_key = node_public_key
        self._running = False
        self._loop_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Pull from a single peer
    # ------------------------------------------------------------------

    async def pull_from_peer(
        self,
        peer_endpoint: str,
        peer_key: str,
        since: float = 0.0,
    ) -> int:
        """Pull new entries from one peer's /api/sync endpoint.

        Sends a SyncRequest with the hashes we already hold (since *since*),
        receives a SyncResponse, and appends entries we don't yet have.

        Returns the number of new entries successfully appended.
        """
        known = await self._log.get_hashes_since(since)
        request_payload = SyncRequest(
            requester_key=self._node_key,
            known_hashes=known,
            since_timestamp=since,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{peer_endpoint.rstrip('/')}/api/sync",
                    json=request_payload.model_dump(),
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Gossip pull from %s (%s) failed: %s", peer_key[:8], peer_endpoint, exc)
            return 0

        sync_resp = SyncResponse.model_validate(resp.json())

        appended = 0
        known_set = set(known)
        for entry in sync_resp.entries:
            if entry.content_hash in known_set:
                continue
            # Signature verification is handled as middleware - store as received.
            try:
                await self._log.append(entry)
                known_set.add(entry.content_hash)
                appended += 1
            except ValueError:
                # Already exists (race condition between concurrent rounds).
                pass

        if appended:
            logger.debug("Pulled %d new entries from %s", appended, peer_key[:8])

        return appended

    # ------------------------------------------------------------------
    # Prepare a sync response for an incoming request
    # ------------------------------------------------------------------

    async def prepare_sync_response(self, request: SyncRequest) -> SyncResponse:
        """Build a SyncResponse for a peer that is requesting our content.

        Returns entries that:
        - are newer than request.since_timestamp, AND
        - are NOT in request.known_hashes.

        Caps the result at request.max_entries (default 100).
        """
        candidates = await self._log.get_hashes_since(request.since_timestamp)

        known_set = set(request.known_hashes)
        missing_hashes = [h for h in candidates if h not in known_set]

        # Apply cap - preserve chronological order (get_hashes_since returns ASC).
        capped = missing_hashes[: request.max_entries]
        has_more = len(missing_hashes) > request.max_entries

        entries: list[ContentEntry] = []
        if capped:
            entries = await self._log.get_entries_by_hashes(capped)
            # Re-sort by timestamp ASC to match the order the requester expects.
            entries.sort(key=lambda e: e.timestamp)

        return SyncResponse(
            entries=entries,
            peer_key=self._node_key,
            has_more=has_more,
        )

    # ------------------------------------------------------------------
    # Gossip round
    # ------------------------------------------------------------------

    async def run_gossip_round(self) -> dict[str, int]:
        """Pull from all CORE and INNER peers.

        Returns a mapping of {peer_public_key: entries_received}.
        Unreachable peers are silently skipped (count = 0).
        """
        peers = await self._rings.get_peers_by_ring(RingLevel.CORE)
        peers += await self._rings.get_peers_by_ring(RingLevel.INNER)

        results: dict[str, int] = {}
        for peer in peers:
            count = await self.pull_from_peer(peer.endpoint, peer.public_key)
            results[peer.public_key] = count

        total = sum(results.values())
        if total:
            logger.info("Gossip round complete: %d new entries from %d peers", total, len(peers))

        return results

    # ------------------------------------------------------------------
    # Background gossip loop
    # ------------------------------------------------------------------

    async def start_gossip_loop(self, interval_seconds: int = 30) -> None:
        """Start a background task that runs gossip rounds on a fixed interval."""
        if self._running:
            logger.warning("Gossip loop already running - ignoring start request")
            return

        self._running = True
        self._loop_task = asyncio.create_task(
            self._gossip_loop(interval_seconds),
            name="osnova-gossip-loop",
        )
        logger.info("Gossip loop started (interval=%ds)", interval_seconds)

    async def stop_gossip_loop(self) -> None:
        """Stop the background gossip loop and wait for it to finish."""
        self._running = False
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        logger.info("Gossip loop stopped")

    async def _gossip_loop(self, interval_seconds: int) -> None:
        """Internal coroutine that fires gossip rounds until stopped."""
        while self._running:
            try:
                await self.run_gossip_round()
            except Exception as exc:  # noqa: BLE001
                logger.error("Unhandled error in gossip round: %s", exc, exc_info=True)
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
