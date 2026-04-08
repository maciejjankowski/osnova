"""Tests for RingManager."""
from __future__ import annotations

import time

import pytest
import pytest_asyncio

from osnova.rings.manager import RingManager
from osnova.schemas import Peer, RingLevel, RING_CAPS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def mgr(tmp_path):
    """Yield an initialised RingManager backed by a temp SQLite file."""
    manager = RingManager(str(tmp_path / "test_rings.db"))
    await manager.initialize()
    yield manager
    await manager.close()


def make_peer(
    pk: str,
    ring: RingLevel = RingLevel.OUTER,
    name: str | None = None,
    endpoint: str | None = None,
) -> Peer:
    return Peer(
        public_key=pk,
        display_name=name or f"peer-{pk}",
        ring_level=ring,
        endpoint=endpoint or f"http://localhost:{8000 + hash(pk) % 1000}",
        added_at=time.time(),
        last_seen=0.0,
    )


# ---------------------------------------------------------------------------
# Basic add / get / remove
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_and_get_peer(mgr):
    peer = make_peer("aaa111", RingLevel.INNER)
    result = await mgr.add_peer(peer)
    assert result is True

    fetched = await mgr.get_peer("aaa111")
    assert fetched is not None
    assert fetched.public_key == "aaa111"
    assert fetched.ring_level == RingLevel.INNER


@pytest.mark.asyncio
async def test_get_missing_peer_returns_none(mgr):
    assert await mgr.get_peer("nonexistent") is None


@pytest.mark.asyncio
async def test_remove_peer(mgr):
    peer = make_peer("bbb222", RingLevel.MIDDLE)
    await mgr.add_peer(peer)

    removed = await mgr.remove_peer("bbb222")
    assert removed is True
    assert await mgr.get_peer("bbb222") is None


@pytest.mark.asyncio
async def test_remove_missing_peer_returns_false(mgr):
    assert await mgr.remove_peer("ghost") is False


@pytest.mark.asyncio
async def test_add_duplicate_returns_false(mgr):
    peer = make_peer("dup000", RingLevel.OUTER)
    assert await mgr.add_peer(peer) is True
    assert await mgr.add_peer(peer) is False


# ---------------------------------------------------------------------------
# Dunbar / ring-cap enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_core_ring_cap_enforced(mgr):
    cap = RING_CAPS[RingLevel.CORE]  # 5
    for i in range(cap):
        ok = await mgr.add_peer(make_peer(f"core{i:03d}", RingLevel.CORE))
        assert ok is True, f"peer {i} should fit"

    overflow = await mgr.add_peer(make_peer("core_overflow", RingLevel.CORE))
    assert overflow is False


@pytest.mark.asyncio
async def test_inner_ring_cap_enforced(mgr):
    cap = RING_CAPS[RingLevel.INNER]  # 15
    for i in range(cap):
        await mgr.add_peer(make_peer(f"inner{i:03d}", RingLevel.INNER))

    overflow = await mgr.add_peer(make_peer("inner_overflow", RingLevel.INNER))
    assert overflow is False


@pytest.mark.asyncio
async def test_caps_are_independent_per_ring(mgr):
    """Filling INNER should not affect CORE capacity."""
    inner_cap = RING_CAPS[RingLevel.INNER]
    for i in range(inner_cap):
        await mgr.add_peer(make_peer(f"inner{i:03d}", RingLevel.INNER))

    # CORE should still accept peers
    assert await mgr.add_peer(make_peer("core001", RingLevel.CORE)) is True


# ---------------------------------------------------------------------------
# get_peers_by_ring / get_all_peers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_peers_by_ring(mgr):
    await mgr.add_peer(make_peer("m1", RingLevel.MIDDLE))
    await mgr.add_peer(make_peer("m2", RingLevel.MIDDLE))
    await mgr.add_peer(make_peer("o1", RingLevel.OUTER))

    middle = await mgr.get_peers_by_ring(RingLevel.MIDDLE)
    assert len(middle) == 2
    assert all(p.ring_level == RingLevel.MIDDLE for p in middle)

    outer = await mgr.get_peers_by_ring(RingLevel.OUTER)
    assert len(outer) == 1


@pytest.mark.asyncio
async def test_get_all_peers(mgr):
    await mgr.add_peer(make_peer("p1", RingLevel.CORE))
    await mgr.add_peer(make_peer("p2", RingLevel.INNER))
    await mgr.add_peer(make_peer("p3", RingLevel.OUTER))

    all_peers = await mgr.get_all_peers()
    assert len(all_peers) == 3


# ---------------------------------------------------------------------------
# Promote / demote
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_promote_peer(mgr):
    await mgr.add_peer(make_peer("pm1", RingLevel.MIDDLE))
    ok = await mgr.promote_peer("pm1", RingLevel.INNER)
    assert ok is True

    peer = await mgr.get_peer("pm1")
    assert peer.ring_level == RingLevel.INNER


@pytest.mark.asyncio
async def test_demote_peer(mgr):
    await mgr.add_peer(make_peer("dm1", RingLevel.INNER))
    ok = await mgr.demote_peer("dm1", RingLevel.OUTER)
    assert ok is True

    peer = await mgr.get_peer("dm1")
    assert peer.ring_level == RingLevel.OUTER


@pytest.mark.asyncio
async def test_promote_missing_peer_returns_false(mgr):
    assert await mgr.promote_peer("ghost", RingLevel.CORE) is False


@pytest.mark.asyncio
async def test_demote_missing_peer_returns_false(mgr):
    assert await mgr.demote_peer("ghost", RingLevel.OUTER) is False


@pytest.mark.asyncio
async def test_promote_rejected_when_target_ring_full(mgr):
    cap = RING_CAPS[RingLevel.CORE]
    for i in range(cap):
        await mgr.add_peer(make_peer(f"core{i:03d}", RingLevel.CORE))

    # Now try to promote an inner peer into a full CORE ring
    await mgr.add_peer(make_peer("inner_candidate", RingLevel.INNER))
    result = await mgr.promote_peer("inner_candidate", RingLevel.CORE)
    assert result is False


@pytest.mark.asyncio
async def test_demote_rejected_when_target_ring_full(mgr):
    outer_cap = RING_CAPS[RingLevel.OUTER]  # 95
    for i in range(outer_cap):
        await mgr.add_peer(make_peer(f"outer{i:04d}", RingLevel.OUTER))

    # Add one inner peer and try to demote into a full OUTER ring
    await mgr.add_peer(make_peer("inner_victim", RingLevel.INNER))
    result = await mgr.demote_peer("inner_victim", RingLevel.OUTER)
    assert result is False


# ---------------------------------------------------------------------------
# update_last_seen
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_last_seen(mgr):
    await mgr.add_peer(make_peer("ls1", RingLevel.INNER))
    ts = 1_700_000_000.0
    await mgr.update_last_seen("ls1", ts)

    peer = await mgr.get_peer("ls1")
    assert peer.last_seen == ts


# ---------------------------------------------------------------------------
# get_sync_peers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_sync_peers_excludes_outer(mgr):
    await mgr.add_peer(make_peer("c1", RingLevel.CORE))
    await mgr.add_peer(make_peer("i1", RingLevel.INNER))
    await mgr.add_peer(make_peer("mid1", RingLevel.MIDDLE))
    await mgr.add_peer(make_peer("o1", RingLevel.OUTER))

    sync = await mgr.get_sync_peers()
    keys = {p.public_key for p in sync}
    assert "c1" in keys
    assert "i1" in keys
    assert "mid1" in keys
    assert "o1" not in keys


@pytest.mark.asyncio
async def test_get_sync_peers_middle_ring_level_is_preserved(mgr):
    """Callers need ring_level to filter SEED/PARAGRAPH for middle peers."""
    await mgr.add_peer(make_peer("mid1", RingLevel.MIDDLE))
    sync = await mgr.get_sync_peers()
    assert any(p.ring_level == RingLevel.MIDDLE for p in sync)


# ---------------------------------------------------------------------------
# get_ring_stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ring_stats_empty(mgr):
    stats = await mgr.get_ring_stats()
    assert stats["total"] == 0
    for level in ("core", "inner", "middle", "outer"):
        assert stats[level] == 0


@pytest.mark.asyncio
async def test_ring_stats_counts(mgr):
    await mgr.add_peer(make_peer("c1", RingLevel.CORE))
    await mgr.add_peer(make_peer("c2", RingLevel.CORE))
    await mgr.add_peer(make_peer("i1", RingLevel.INNER))
    await mgr.add_peer(make_peer("o1", RingLevel.OUTER))

    stats = await mgr.get_ring_stats()
    assert stats["core"] == 2
    assert stats["inner"] == 1
    assert stats["middle"] == 0
    assert stats["outer"] == 1
    assert stats["total"] == 4
