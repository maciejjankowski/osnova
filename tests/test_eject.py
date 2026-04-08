"""Tests for osnova.eject.protocol.EjectProtocol.

Stubs for ContentLog and RingManager avoid SQLite; httpx calls are mocked
via the pytest-httpx fixture (same pattern as test_gossip.py).
"""
from __future__ import annotations

import json
import os
import time

import pytest

from osnova.crypto.identity import generate_keypair, public_key_hex
from osnova.eject.protocol import EjectProtocol, _eject_package_payload, _canary_payload, _sign_bytes
from osnova.schemas import (
    CanarySignal,
    ContentEntry,
    ContentType,
    EjectPackage,
    Peer,
    RingLevel,
    SignalType,
)


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

    async def get_feed(self, limit: int = 50, offset: int = 0, author_key: str | None = None) -> list[ContentEntry]:
        entries = list(self._entries.values())
        if author_key is not None:
            entries = [e for e in entries if e.author_key == author_key]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[offset: offset + limit]

    def all_hashes(self) -> set[str]:
        return set(self._entries.keys())


class StubRingManager:
    """In-memory stand-in for RingManager."""

    def __init__(self, peers: list[Peer] | None = None) -> None:
        self._peers: list[Peer] = peers or []

    async def get_all_peers(self) -> list[Peer]:
        return list(self._peers)

    async def get_peers_by_ring(self, ring_level: RingLevel) -> list[Peer]:
        return [p for p in self._peers if p.ring_level == ring_level]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def keypair():
    signing_key, verify_key = generate_keypair()
    return signing_key, verify_key


@pytest.fixture
def node_key(keypair):
    _, verify_key = keypair
    return public_key_hex(verify_key)


@pytest.fixture
def protocol(node_key):
    return EjectProtocol(node_key=node_key)


# ---------------------------------------------------------------------------
# Package creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_package_content_includes_all_entries(protocol, keypair):
    """package_content exports every entry in the log."""
    signing_key, _ = keypair
    e1 = _make_entry("first", ts=1.0)
    e2 = _make_entry("second", ts=2.0)
    log = StubContentLog([e1, e2])
    rings = StubRingManager()

    pkg = await protocol.package_content(log, rings, signing_key)

    hashes = {e.content_hash for e in pkg.content_entries}
    assert e1.content_hash in hashes
    assert e2.content_hash in hashes
    assert len(pkg.content_entries) == 2


@pytest.mark.asyncio
async def test_package_content_includes_all_peers(protocol, keypair):
    """package_content exports every peer in the ring manager."""
    signing_key, _ = keypair
    p1 = _peer("11" * 32, "http://n1:8000", RingLevel.CORE)
    p2 = _peer("22" * 32, "http://n2:8000", RingLevel.OUTER)
    log = StubContentLog()
    rings = StubRingManager([p1, p2])

    pkg = await protocol.package_content(log, rings, signing_key)

    peer_keys = {p.public_key for p in pkg.peer_list}
    assert p1.public_key in peer_keys
    assert p2.public_key in peer_keys


@pytest.mark.asyncio
async def test_package_content_signing(protocol, keypair):
    """The package has a non-empty signature from the node key."""
    signing_key, verify_key = keypair
    log = StubContentLog([_make_entry()])
    rings = StubRingManager()

    pkg = await protocol.package_content(log, rings, signing_key, closing_message="bye")

    assert pkg.signature != ""
    assert pkg.author_key == public_key_hex(verify_key)

    # Signature must verify against the documented payload
    from osnova.eject.protocol import _verify_signature
    payload = _eject_package_payload(pkg.author_key, pkg.timestamp, pkg.closing_message, len(pkg.content_entries))
    assert _verify_signature(pkg.author_key, payload, pkg.signature)


@pytest.mark.asyncio
async def test_package_content_closing_message(protocol, keypair):
    """closing_message is stored in the package."""
    signing_key, _ = keypair
    log = StubContentLog()
    rings = StubRingManager()

    pkg = await protocol.package_content(log, rings, signing_key, closing_message="farewell")

    assert pkg.closing_message == "farewell"


# ---------------------------------------------------------------------------
# Save / load roundtrip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_load_roundtrip(protocol, keypair, tmp_path):
    """A package saved to disk can be loaded back identically."""
    signing_key, _ = keypair
    e1 = _make_entry("roundtrip entry", ts=42.0)
    log = StubContentLog([e1])
    rings = StubRingManager([_peer()])

    pkg = await protocol.package_content(log, rings, signing_key, closing_message="see you")

    path = str(tmp_path / "eject.json")
    protocol.save_package(pkg, path)

    loaded = protocol.load_package(path)

    assert loaded.author_key == pkg.author_key
    assert loaded.closing_message == pkg.closing_message
    assert loaded.signature == pkg.signature
    assert len(loaded.content_entries) == len(pkg.content_entries)
    assert loaded.content_entries[0].content_hash == e1.content_hash
    assert len(loaded.peer_list) == len(pkg.peer_list)


def test_save_package_writes_valid_json(protocol, tmp_path):
    """save_package produces valid JSON on disk."""
    pkg = EjectPackage(
        author_key="aa" * 32,
        content_entries=[],
        peer_list=[],
        closing_message="test",
    )
    path = str(tmp_path / "pkg.json")
    protocol.save_package(pkg, path)

    with open(path) as fh:
        data = json.load(fh)

    assert data["author_key"] == "aa" * 32
    assert data["closing_message"] == "test"


# ---------------------------------------------------------------------------
# Reattach with provenance preserved
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reattach_with_provenance(protocol, keypair):
    """Entries are imported with original author_key intact."""
    signing_key, _ = keypair
    original_author = "dd" * 32
    e1 = _make_entry("content", author=original_author, ts=1.0)

    pkg = EjectPackage(
        author_key=original_author,
        content_entries=[e1],
        peer_list=[],
    )

    new_log = StubContentLog()
    count = await protocol.reattach(pkg, new_log, strip_provenance=False)

    assert count == 1
    stored = list(new_log._entries.values())[0]
    assert stored.author_key == original_author


@pytest.mark.asyncio
async def test_reattach_skips_duplicates(protocol, keypair):
    """Entries already in the log are skipped; reattach is idempotent."""
    e1 = _make_entry("duplicate", ts=1.0)
    existing_log = StubContentLog([e1])

    pkg = EjectPackage(
        author_key="aa" * 32,
        content_entries=[e1],
        peer_list=[],
    )

    count = await protocol.reattach(pkg, existing_log, strip_provenance=False)
    assert count == 0
    assert len(existing_log.all_hashes()) == 1  # unchanged


@pytest.mark.asyncio
async def test_reattach_multiple_entries(protocol, keypair):
    """Multiple entries are all imported."""
    entries = [_make_entry(f"entry {i}", ts=float(i)) for i in range(5)]
    pkg = EjectPackage(author_key="aa" * 32, content_entries=entries, peer_list=[])
    log = StubContentLog()

    count = await protocol.reattach(pkg, log)
    assert count == 5
    assert len(log.all_hashes()) == 5


# ---------------------------------------------------------------------------
# Reattach without provenance (stripped)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reattach_strip_provenance_replaces_author(protocol, node_key, keypair):
    """With strip_provenance=True, author_key is replaced by the node's own key."""
    original_author = "dd" * 32
    e1 = _make_entry("sensitive content", author=original_author, ts=1.0)

    pkg = EjectPackage(
        author_key=original_author,
        content_entries=[e1],
        peer_list=[],
    )

    new_log = StubContentLog()
    count = await protocol.reattach(pkg, new_log, strip_provenance=True)

    assert count == 1
    stored = list(new_log._entries.values())[0]
    # author_key must be the new node's key, not the original
    assert stored.author_key == node_key
    assert stored.author_key != original_author


@pytest.mark.asyncio
async def test_reattach_strip_provenance_clears_signature(protocol, node_key, keypair):
    """Stripped entries have their signature cleared (old sig is invalid for new key)."""
    signing_key, _ = keypair
    e1 = _make_entry("signed entry", author="dd" * 32, ts=1.0)

    pkg = EjectPackage(author_key="dd" * 32, content_entries=[e1], peer_list=[])
    new_log = StubContentLog()
    await protocol.reattach(pkg, new_log, strip_provenance=True)

    stored = list(new_log._entries.values())[0]
    assert stored.signature == ""


# ---------------------------------------------------------------------------
# Canary signal creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_broadcast_canary_returns_signed_signal(httpx_mock, keypair, node_key):
    """broadcast_canary returns a CanarySignal with a valid signature."""
    signing_key, verify_key = keypair
    protocol = EjectProtocol(node_key=node_key)
    rings = StubRingManager([_peer("bb" * 32, "http://peer:8000")])

    httpx_mock.add_response(
        url="http://peer:8000/api/signals/receive",
        method="POST",
        status_code=200,
        json={"ok": True},
    )

    canary = await protocol.broadcast_canary(rings, None, signing_key, message="captured")

    assert canary.signal_type == SignalType.CANARY
    assert canary.author_key == node_key
    assert canary.message == "captured"
    assert canary.signature != ""

    from osnova.eject.protocol import _verify_signature
    payload = _canary_payload(canary.author_key, canary.signal_type.value, canary.timestamp, canary.message)
    assert _verify_signature(canary.author_key, payload, canary.signature)


@pytest.mark.asyncio
async def test_broadcast_canary_posts_to_all_ring_levels(httpx_mock, keypair, node_key):
    """broadcast_canary contacts peers at all ring levels."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)
    peers = [
        _peer("11" * 32, "http://core:8000", RingLevel.CORE),
        _peer("22" * 32, "http://inner:8001", RingLevel.INNER),
        _peer("33" * 32, "http://middle:8002", RingLevel.MIDDLE),
        _peer("44" * 32, "http://outer:8003", RingLevel.OUTER),
    ]
    rings = StubRingManager(peers)

    for p in peers:
        httpx_mock.add_response(
            url=f"{p.endpoint}/api/signals/receive",
            method="POST",
            status_code=200,
            json={"ok": True},
        )

    canary = await protocol.broadcast_canary(rings, None, signing_key)
    assert canary.severity == "critical"


@pytest.mark.asyncio
async def test_broadcast_canary_tolerates_peer_failure(httpx_mock, keypair, node_key):
    """A failing peer does not prevent the canary from being returned."""
    import httpx as _httpx

    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)
    rings = StubRingManager([_peer("bb" * 32, "http://dead:9999")])

    httpx_mock.add_exception(_httpx.ConnectError("refused"))

    # Should not raise
    canary = await protocol.broadcast_canary(rings, None, signing_key, message="still fires")
    assert canary.signal_type == SignalType.CANARY


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_received_signal_canary(keypair, node_key):
    """A valid CANARY signal is accepted and peer marked compromised."""
    signing_key, verify_key = keypair
    protocol = EjectProtocol(node_key=node_key)
    timestamp = time.time()

    payload = _canary_payload(node_key, SignalType.CANARY.value, timestamp, "under duress")
    sig = _sign_bytes(signing_key, payload)

    signal = CanarySignal(
        author_key=node_key,
        signal_type=SignalType.CANARY,
        message="under duress",
        timestamp=timestamp,
        signature=sig,
    )

    result = await protocol.handle_received_signal(signal)

    assert result == "canary_received"
    assert len(protocol.received_signals) == 1
    assert protocol._peer_states[node_key] == "compromised"


@pytest.mark.asyncio
async def test_handle_received_signal_eject(keypair, node_key):
    """A valid EJECT signal is accepted and peer marked ejected."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)
    timestamp = time.time()

    payload = _canary_payload(node_key, SignalType.EJECT.value, timestamp, "leaving")
    sig = _sign_bytes(signing_key, payload)

    signal = CanarySignal(
        author_key=node_key,
        signal_type=SignalType.EJECT,
        message="leaving",
        timestamp=timestamp,
        signature=sig,
    )

    result = await protocol.handle_received_signal(signal)

    assert result == "eject_received"
    assert protocol._peer_states[node_key] == "ejected"


@pytest.mark.asyncio
async def test_handle_received_signal_invalid_signature(keypair, node_key):
    """A signal with a tampered signature is rejected."""
    protocol = EjectProtocol(node_key=node_key)

    signal = CanarySignal(
        author_key=node_key,
        signal_type=SignalType.CANARY,
        message="tampered",
        timestamp=time.time(),
        signature="00" * 32,  # invalid
    )

    result = await protocol.handle_received_signal(signal)

    assert result == "invalid_signature"
    assert len(protocol.received_signals) == 0


@pytest.mark.asyncio
async def test_handle_received_signal_accepts_dict(keypair, node_key):
    """handle_received_signal accepts a raw dict (from JSON deserialization)."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)
    timestamp = time.time()

    payload = _canary_payload(node_key, SignalType.CANARY.value, timestamp, "")
    sig = _sign_bytes(signing_key, payload)

    signal_dict = {
        "author_key": node_key,
        "signal_type": "canary",
        "message": "",
        "timestamp": timestamp,
        "signature": sig,
        "severity": "critical",
    }

    result = await protocol.handle_received_signal(signal_dict)
    assert result == "canary_received"


@pytest.mark.asyncio
async def test_received_signals_accumulate(keypair, node_key):
    """Multiple signals are all stored in received_signals."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)

    for i in range(3):
        ts = time.time() + i
        payload = _canary_payload(node_key, SignalType.CANARY.value, ts, f"msg{i}")
        sig = _sign_bytes(signing_key, payload)
        signal = CanarySignal(
            author_key=node_key,
            signal_type=SignalType.CANARY,
            message=f"msg{i}",
            timestamp=ts,
            signature=sig,
        )
        await protocol.handle_received_signal(signal)

    assert len(protocol.received_signals) == 3


# ---------------------------------------------------------------------------
# Execute eject (broadcast + package)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_eject_broadcasts_and_returns_package(httpx_mock, keypair, node_key):
    """execute_eject POSTs to all peers and returns the package."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)

    e1 = _make_entry("going away", ts=1.0)
    log = StubContentLog([e1])
    peer = _peer("bb" * 32, "http://peer:8000", RingLevel.CORE)
    rings = StubRingManager([peer])

    httpx_mock.add_response(
        url="http://peer:8000/api/signals/receive",
        method="POST",
        status_code=200,
        json={"ok": True},
    )

    pkg = await protocol.execute_eject(log, rings, None, signing_key, closing_message="goodbye")

    assert isinstance(pkg, EjectPackage)
    assert pkg.closing_message == "goodbye"
    assert len(pkg.content_entries) == 1


@pytest.mark.asyncio
async def test_execute_eject_does_not_delete_data(httpx_mock, keypair, node_key):
    """execute_eject must NOT clear the log - that is the caller's responsibility."""
    signing_key, _ = keypair
    protocol = EjectProtocol(node_key=node_key)

    e1 = _make_entry("keep me", ts=1.0)
    log = StubContentLog([e1])
    rings = StubRingManager()

    await protocol.execute_eject(log, rings, None, signing_key)

    # log still has the entry
    assert e1.content_hash in log.all_hashes()
