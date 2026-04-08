"""Eject and canary protocol for voluntary node disappearance and compromise signalling."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Union

import httpx
from nacl.encoding import HexEncoder
from nacl.signing import SigningKey

from osnova.crypto.identity import public_key_hex
from osnova.rings.manager import RingManager
from osnova.schemas import (
    CanarySignal,
    ContentEntry,
    EjectPackage,
    Peer,
    RingLevel,
    SignalType,
)
from osnova.storage.log import ContentLog

logger = logging.getLogger(__name__)


def _sign_bytes(signing_key: SigningKey, payload: bytes) -> str:
    """Sign raw bytes with the given key and return hex signature."""
    signed = signing_key.sign(payload, encoder=HexEncoder)
    return signed.signature.decode("ascii")


def _verify_signature(author_key_hex: str, payload: bytes, signature_hex: str) -> bool:
    """Verify a hex signature over raw bytes using the hex-encoded public key."""
    from nacl.signing import VerifyKey

    try:
        verify_key = VerifyKey(author_key_hex.encode("ascii"), encoder=HexEncoder)
        sig_bytes = bytes.fromhex(signature_hex)
        verify_key.verify(payload, sig_bytes)
        return True
    except Exception:
        return False


def _eject_package_payload(author_key: str, timestamp: float, closing_message: str, entry_count: int) -> bytes:
    """Deterministic payload for signing an EjectPackage."""
    raw = f"{author_key}:{timestamp}:{closing_message}:{entry_count}"
    return hashlib.sha256(raw.encode()).hexdigest().encode("utf-8")


def _canary_payload(author_key: str, signal_type: str, timestamp: float, message: str) -> bytes:
    """Deterministic payload for signing a CanarySignal."""
    raw = f"{author_key}:{signal_type}:{timestamp}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest().encode("utf-8")


class EjectProtocol:
    """Handles voluntary node ejection and canary (compromise) signalling."""

    def __init__(self, node_key: str | None = None) -> None:
        """
        Args:
            node_key: hex public key of this node, used during reattach to strip provenance.
        """
        self.node_key = node_key
        self.received_signals: list[CanarySignal] = []
        # Tracks peer states: public_key -> "ejected" | "compromised"
        self._peer_states: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Eject: voluntary disappearance
    # ------------------------------------------------------------------

    async def package_content(
        self,
        content_log: ContentLog,
        ring_manager: RingManager,
        signing_key: SigningKey,
        closing_message: str = "",
        include_provenance: bool = True,
    ) -> EjectPackage:
        """Export all content and peers into a portable EjectPackage, then sign it.

        The package is plain-text (encryption is post-MVP).
        """
        # Gather all entries (page through in chunks to avoid memory spikes)
        all_entries: list[ContentEntry] = []
        offset = 0
        chunk = 500
        while True:
            batch = await content_log.get_feed(limit=chunk, offset=offset)
            all_entries.extend(batch)
            if len(batch) < chunk:
                break
            offset += chunk

        all_peers: list[Peer] = await ring_manager.get_all_peers()
        author_key = public_key_hex(signing_key.verify_key)
        timestamp = time.time()

        payload = _eject_package_payload(author_key, timestamp, closing_message, len(all_entries))
        signature = _sign_bytes(signing_key, payload)

        return EjectPackage(
            author_key=author_key,
            content_entries=all_entries,
            peer_list=all_peers,
            timestamp=timestamp,
            signature=signature,
            include_provenance=include_provenance,
            closing_message=closing_message,
        )

    async def execute_eject(
        self,
        content_log: ContentLog,
        ring_manager: RingManager,
        gossip_service,
        signing_key: SigningKey,
        closing_message: str = "",
        include_provenance: bool = True,
    ) -> EjectPackage:
        """Package content and broadcast an EJECT signal to all peers.

        Caller is responsible for saving the package and cleaning up local data
        after this method returns.
        """
        package = await self.package_content(
            content_log, ring_manager, signing_key, closing_message, include_provenance
        )

        all_peers = await ring_manager.get_all_peers()
        author_key = public_key_hex(signing_key.verify_key)

        # Build the canary/eject signal to broadcast
        timestamp = time.time()
        signal_payload = _canary_payload(author_key, SignalType.EJECT.value, timestamp, closing_message)
        sig = _sign_bytes(signing_key, signal_payload)

        eject_signal = CanarySignal(
            author_key=author_key,
            signal_type=SignalType.EJECT,
            message=closing_message,
            timestamp=timestamp,
            signature=sig,
            severity="info",
        )

        signal_data = eject_signal.model_dump()
        async with httpx.AsyncClient(timeout=10.0) as client:
            for peer in all_peers:
                try:
                    await client.post(
                        f"{peer.endpoint}/api/signals/receive",
                        json=signal_data,
                    )
                except Exception as exc:
                    logger.warning("Failed to send EJECT signal to %s: %s", peer.endpoint, exc)

        return package

    def save_package(self, package: EjectPackage, output_path: str) -> None:
        """Serialize the EjectPackage to JSON on disk."""
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(package.model_dump(), fh, indent=2, ensure_ascii=False)

    def load_package(self, input_path: str) -> EjectPackage:
        """Deserialize an EjectPackage from a JSON file."""
        with open(input_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return EjectPackage.model_validate(data)

    # ------------------------------------------------------------------
    # Re-attach: join a new network with old content
    # ------------------------------------------------------------------

    async def reattach(
        self,
        package: EjectPackage,
        content_log: ContentLog,
        strip_provenance: bool = False,
    ) -> int:
        """Import content from a package into the current node's log.

        Args:
            package: previously created EjectPackage.
            content_log: log belonging to the new node.
            strip_provenance: if True, replace author_key on all entries with
                this node's key so there is no link to the old identity.

        Returns:
            Number of entries actually imported (skips duplicates).
        """
        imported = 0
        for entry in package.content_entries:
            if strip_provenance and self.node_key:
                entry = entry.model_copy(update={"author_key": self.node_key, "signature": ""})

            try:
                await content_log.append(entry)
                imported += 1
            except ValueError:
                # Already exists - idempotent
                pass

        return imported

    # ------------------------------------------------------------------
    # Canary: compromised node signal
    # ------------------------------------------------------------------

    async def broadcast_canary(
        self,
        ring_manager: RingManager,
        gossip_service,
        signing_key: SigningKey,
        message: str = "",
    ) -> CanarySignal:
        """Create, sign, and broadcast a CANARY signal to ALL peers.

        Every ring level is notified because a compromise signal is critical.
        """
        author_key = public_key_hex(signing_key.verify_key)
        timestamp = time.time()

        payload = _canary_payload(author_key, SignalType.CANARY.value, timestamp, message)
        sig = _sign_bytes(signing_key, payload)

        canary = CanarySignal(
            author_key=author_key,
            signal_type=SignalType.CANARY,
            message=message,
            timestamp=timestamp,
            signature=sig,
            severity="critical",
        )

        all_peers = await ring_manager.get_all_peers()
        signal_data = canary.model_dump()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for peer in all_peers:
                try:
                    await client.post(
                        f"{peer.endpoint}/api/signals/receive",
                        json=signal_data,
                    )
                except Exception as exc:
                    logger.warning("Failed to send CANARY signal to %s: %s", peer.endpoint, exc)

        return canary

    async def handle_received_signal(self, signal: Union[CanarySignal, dict]) -> str:
        """Verify and process an inbound CANARY or EJECT signal.

        Stores valid signals in self.received_signals and marks the peer.

        Returns:
            "canary_received", "eject_received", or "invalid_signature".
        """
        if isinstance(signal, dict):
            signal = CanarySignal.model_validate(signal)

        payload = _canary_payload(
            signal.author_key,
            signal.signal_type.value,
            signal.timestamp,
            signal.message,
        )

        if not _verify_signature(signal.author_key, payload, signal.signature):
            logger.warning("Received signal with invalid signature from %s", signal.author_key)
            return "invalid_signature"

        self.received_signals.append(signal)

        if signal.signal_type == SignalType.CANARY:
            self._peer_states[signal.author_key] = "compromised"
            logger.info("CANARY received from %s - marking as compromised", signal.author_key)
            return "canary_received"

        if signal.signal_type == SignalType.EJECT:
            self._peer_states[signal.author_key] = "ejected"
            logger.info("EJECT received from %s - marking as ejected", signal.author_key)
            return "eject_received"

        # Unknown signal type - still stored above
        return "unknown_signal"
