"""Tests for osnova.gossip.sync.GossipService.

Stubs for ContentLog and RingManager avoid SQLite; httpx calls are mocked
via the pytest-httpx fixture.
"""
from __future__ import annotations

import json
import time

import httpx
import pytest
import pytest_asyncio

from osnova.gossip.sync import GossipService
from osnova.schemas import ContentEntry, ContentType, Peer, RingLevel, SyncRequest, SyncResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    body: str = "hello",
    author: str = "aa" * 32,
    ts: float | None = None,
) -> ContentEntry:
    return ContentEntry(
        author_key=author,
        content_type=ContentType.POST,
        body=body,
        timestamp=ts or time.time(),
    )


def _peer(
    public_key: str = "bb" * 32,
    endpoint: str = "http://peer1:8000",
    ring: RingLevel = RingLevel.CORE,
) -> Peer:
    return Peer(
        public_key=public_key,
        display_name="Peer",
        ring_level=ring,
        endpoint=endpoint,
    )


# ---------------------------------------------------------------------------
# In-memory stubs (no SQLite)
# ---------------------------------------------------------------------------

class StubContentLog:
    """In-memory stand-in for ContentLog."""

    def __init__(self, entries: list[ContentEntry] | None = None) -> None:
        self._entries: dict[str, ContentEntry] = {}
        for e in (entries or []):
            self._entries[e.content_hash] = e

    async def append(self, entry: ContentEntry) -> str:
        h = entry.content_hash
        if h in self._entries:
            raise ValueError(f"Entry {h!r} already exists")
        self._entries[h] = entry
        return h

    async def get_hashes_since(self, since_timestamp: float) -> list[str]:
        return [
            h for h, e in self._entries.items()
            if e.timestamp > since_timestamp
        ]

    async def get_entries_by_hashes(self, hashes: list[str]) -> list[ContentEntry]:
        return [self._entries[h] for h in hashes if h in self._entries]

    # Convenience for assertions
    def all_hashes(self) -> set[str]:
        return set(self._entries.keys())


class StubRingManager:
    """In-memory stand-in for RingManager."""

    def __init__(self, peers: list[Peer] | None = None) -> None:
        self._peers: list[Peer] = peers or []

    async def get_peers_by_ring(self, ring_level: RingLevel) -> list[Peer]:
        return [p for p in self._peers if p.ring_level == ring_level]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NODE_KEY = "cc" * 32


@pytest.fixture
def log() -> StubContentLog:
    return StubContentLog()


@pytest.fixture
def rings() -> StubRingManager:
    return StubRingManager()


@pytest.fixture
def service(log: StubContentLog, rings: StubRingManager) -> GossipService:
    return GossipService(log, rings, NODE_KEY)


# ---------------------------------------------------------------------------
# pull_from_peer tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pull_from_peer_appends_new_entries(httpx_mock, service, log):
    """Entries returned by the peer that we don't know are stored."""
    remote_entry = _make_entry("remote content", ts=1_000_000.0)
    sync_resp = SyncResponse(
        entries=[remote_entry],
        peer_key="bb" * 32,
        has_more=False,
    )
    httpx_mock.add_response(
        url="http://peer1:8000/api/sync",
        method="POST",
        json=sync_resp.model_dump(),
    )

    count = await service.pull_from_peer("http://peer1:8000", "bb" * 32)

    assert count == 1
    assert remote_entry.content_hash in log.all_hashes()


@pytest.mark.asyncio
async def test_pull_from_peer_skips_already_known(httpx_mock, service, log):
    """Entries the log already holds are not double-appended."""
    existing = _make_entry("existing", ts=999_999.0)
    await log.append(existing)

    sync_resp = SyncResponse(
        entries=[existing],
        peer_key="bb" * 32,
        has_more=False,
    )
    httpx_mock.add_response(
        url="http://peer1:8000/api/sync",
        method="POST",
        json=sync_resp.model_dump(),
    )

    count = await service.pull_from_peer("http://peer1:8000", "bb" * 32, since=0.0)
    assert count == 0
    assert len(log.all_hashes()) == 1  # unchanged


@pytest.mark.asyncio
async def test_pull_from_peer_handles_connection_error(httpx_mock, service):
    """Network errors are caught; method returns 0 without raising."""
    httpx_mock.add_exception(httpx.ConnectError("timeout"))

    count = await service.pull_from_peer("http://dead-peer:8000", "dd" * 32)
    assert count == 0


@pytest.mark.asyncio
async def test_pull_from_peer_sends_known_hashes(httpx_mock, service, log):
    """The SyncRequest body contains the hashes we already hold."""
    existing = _make_entry("local", ts=500.0)
    await log.append(existing)

    captured_body: dict = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=SyncResponse(entries=[], peer_key="bb" * 32).model_dump(),
        )

    httpx_mock.add_callback(capture, url="http://peer1:8000/api/sync", method="POST")

    await service.pull_from_peer("http://peer1:8000", "bb" * 32, since=0.0)

    assert existing.content_hash in captured_body.get("known_hashes", [])
    assert captured_body["requester_key"] == NODE_KEY


@pytest.mark.asyncio
async def test_pull_from_peer_returns_count_of_appended(httpx_mock, service, log):
    """Only genuinely new entries count toward the return value."""
    e1 = _make_entry("alpha", ts=1.0)
    e2 = _make_entry("beta", ts=2.0)
    e3 = _make_entry("gamma", ts=3.0)
    await log.append(e1)  # pre-existing

    sync_resp = SyncResponse(entries=[e1, e2, e3], peer_key="bb" * 32)
    httpx_mock.add_response(
        url="http://peer1:8000/api/sync",
        method="POST",
        json=sync_resp.model_dump(),
    )

    count = await service.pull_from_peer("http://peer1:8000", "bb" * 32)
    assert count == 2
    assert e2.content_hash in log.all_hashes()
    assert e3.content_hash in log.all_hashes()


# ---------------------------------------------------------------------------
# prepare_sync_response tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prepare_sync_response_excludes_known_hashes(service, log):
    """Entries whose hash the requester already holds are omitted."""
    e_known = _make_entry("known", ts=100.0)
    e_new = _make_entry("new", ts=200.0)
    await log.append(e_known)
    await log.append(e_new)

    req = SyncRequest(
        requester_key="ee" * 32,
        known_hashes=[e_known.content_hash],
        since_timestamp=0.0,
    )
    resp = await service.prepare_sync_response(req)

    hashes_returned = {e.content_hash for e in resp.entries}
    assert e_known.content_hash not in hashes_returned
    assert e_new.content_hash in hashes_returned


@pytest.mark.asyncio
async def test_prepare_sync_response_respects_since_timestamp(service, log):
    """Entries older than since_timestamp are not returned."""
    old = _make_entry("old", ts=50.0)
    recent = _make_entry("recent", ts=150.0)
    await log.append(old)
    await log.append(recent)

    req = SyncRequest(
        requester_key="ee" * 32,
        known_hashes=[],
        since_timestamp=100.0,
    )
    resp = await service.prepare_sync_response(req)

    hashes = {e.content_hash for e in resp.entries}
    assert old.content_hash not in hashes
    assert recent.content_hash in hashes


@pytest.mark.asyncio
async def test_prepare_sync_response_respects_max_entries(service, log):
    """has_more is True when there are more entries than max_entries allows."""
    for i in range(5):
        await log.append(_make_entry(f"entry {i}", ts=float(i + 1)))

    req = SyncRequest(
        requester_key="ee" * 32,
        known_hashes=[],
        since_timestamp=0.0,
        max_entries=3,
    )
    resp = await service.prepare_sync_response(req)

    assert len(resp.entries) == 3
    assert resp.has_more is True


@pytest.mark.asyncio
async def test_prepare_sync_response_no_has_more_when_fits(service, log):
    """has_more is False when all entries fit within max_entries."""
    for i in range(2):
        await log.append(_make_entry(f"entry {i}", ts=float(i + 1)))

    req = SyncRequest(
        requester_key="ee" * 32,
        known_hashes=[],
        since_timestamp=0.0,
        max_entries=10,
    )
    resp = await service.prepare_sync_response(req)

    assert len(resp.entries) == 2
    assert resp.has_more is False


@pytest.mark.asyncio
async def test_prepare_sync_response_empty_log(service, log):
    """Returns empty response without error when the log has nothing."""
    req = SyncRequest(requester_key="ee" * 32, known_hashes=[], since_timestamp=0.0)
    resp = await service.prepare_sync_response(req)

    assert resp.entries == []
    assert resp.has_more is False
    assert resp.peer_key == NODE_KEY


# ---------------------------------------------------------------------------
# run_gossip_round tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gossip_round_pulls_from_core_and_inner(httpx_mock):
    """run_gossip_round contacts CORE and INNER peers."""
    core_peer = _peer("cc" * 32, "http://core:8000", RingLevel.CORE)
    inner_peer = _peer("dd" * 32, "http://inner:8001", RingLevel.INNER)

    log = StubContentLog()
    rings = StubRingManager([core_peer, inner_peer])
    svc = GossipService(log, rings, NODE_KEY)

    for url in ["http://core:8000/api/sync", "http://inner:8001/api/sync"]:
        httpx_mock.add_response(
            url=url,
            method="POST",
            json=SyncResponse(entries=[], peer_key="zz" * 32).model_dump(),
        )

    results = await svc.run_gossip_round()

    assert core_peer.public_key in results
    assert inner_peer.public_key in results


@pytest.mark.asyncio
async def test_gossip_round_skips_unreachable_peers(httpx_mock):
    """Peers that refuse connection are skipped; round still returns."""
    dead_peer = _peer("ff" * 32, "http://dead:9999", RingLevel.CORE)

    log = StubContentLog()
    rings = StubRingManager([dead_peer])
    svc = GossipService(log, rings, NODE_KEY)

    httpx_mock.add_exception(httpx.ConnectError("refused"))

    results = await svc.run_gossip_round()

    assert results[dead_peer.public_key] == 0


@pytest.mark.asyncio
async def test_gossip_round_aggregates_new_entries(httpx_mock):
    """Entries from multiple peers are all appended to the log."""
    p1 = _peer("11" * 32, "http://n1:8000", RingLevel.CORE)
    p2 = _peer("22" * 32, "http://n2:8000", RingLevel.INNER)

    e1 = _make_entry("from peer 1", ts=1.0)
    e2 = _make_entry("from peer 2", ts=2.0)

    httpx_mock.add_response(
        url="http://n1:8000/api/sync",
        method="POST",
        json=SyncResponse(entries=[e1], peer_key=p1.public_key).model_dump(),
    )
    httpx_mock.add_response(
        url="http://n2:8000/api/sync",
        method="POST",
        json=SyncResponse(entries=[e2], peer_key=p2.public_key).model_dump(),
    )

    log = StubContentLog()
    rings = StubRingManager([p1, p2])
    svc = GossipService(log, rings, NODE_KEY)

    results = await svc.run_gossip_round()

    assert results[p1.public_key] == 1
    assert results[p2.public_key] == 1
    assert e1.content_hash in log.all_hashes()
    assert e2.content_hash in log.all_hashes()


@pytest.mark.asyncio
async def test_gossip_round_no_peers_returns_empty_dict():
    """With no peers configured, returns an empty result dict."""
    svc = GossipService(StubContentLog(), StubRingManager([]), NODE_KEY)
    results = await svc.run_gossip_round()
    assert results == {}


# ---------------------------------------------------------------------------
# Gossip loop lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_and_stop_gossip_loop():
    """Loop starts and can be stopped cleanly without running a real round."""
    svc = GossipService(StubContentLog(), StubRingManager([]), NODE_KEY)

    await svc.start_gossip_loop(interval_seconds=9999)
    assert svc._running is True
    assert svc._loop_task is not None

    await svc.stop_gossip_loop()
    assert svc._running is False


@pytest.mark.asyncio
async def test_start_gossip_loop_idempotent():
    """Calling start twice doesn't create a second task."""
    svc = GossipService(StubContentLog(), StubRingManager([]), NODE_KEY)
    await svc.start_gossip_loop(interval_seconds=9999)
    first_task = svc._loop_task

    await svc.start_gossip_loop(interval_seconds=9999)
    assert svc._loop_task is first_task  # same task object

    await svc.stop_gossip_loop()
