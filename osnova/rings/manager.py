"""Ring management module for Osnova peer trust rings."""
from __future__ import annotations

import aiosqlite

from osnova.schemas import Peer, RingLevel, RING_CAPS


class RingManager:
    """Manages peers across Dunbar-capped trust rings backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database connection and create tables if needed."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS peers (
                public_key   TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                ring_level   TEXT NOT NULL,
                endpoint     TEXT NOT NULL,
                added_at     REAL NOT NULL,
                last_seen    REAL NOT NULL DEFAULT 0.0
            )
            """
        )
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_peer(self, row: aiosqlite.Row) -> Peer:
        return Peer(
            public_key=row["public_key"],
            display_name=row["display_name"],
            ring_level=RingLevel(row["ring_level"]),
            endpoint=row["endpoint"],
            added_at=row["added_at"],
            last_seen=row["last_seen"],
        )

    async def _count_ring(self, ring_level: RingLevel) -> int:
        assert self._db is not None
        async with self._db.execute(
            "SELECT COUNT(*) FROM peers WHERE ring_level = ?",
            (ring_level.value,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_peer(self, peer: Peer) -> bool:
        """Add a peer to its ring. Returns False if the ring is at capacity."""
        assert self._db is not None
        cap = RING_CAPS[peer.ring_level]
        current_count = await self._count_ring(peer.ring_level)
        if current_count >= cap:
            return False
        try:
            await self._db.execute(
                """
                INSERT INTO peers (public_key, display_name, ring_level, endpoint, added_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    peer.public_key,
                    peer.display_name,
                    peer.ring_level.value,
                    peer.endpoint,
                    peer.added_at,
                    peer.last_seen,
                ),
            )
            await self._db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Duplicate public_key
            return False

    async def remove_peer(self, public_key: str) -> bool:
        """Remove a peer. Returns False if the peer was not found."""
        assert self._db is not None
        async with self._db.execute(
            "DELETE FROM peers WHERE public_key = ?", (public_key,)
        ) as cur:
            await self._db.commit()
            return cur.rowcount > 0

    async def get_peer(self, public_key: str) -> Peer | None:
        """Return a peer by public key, or None if not found."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM peers WHERE public_key = ?", (public_key,)
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_peer(row) if row else None

    async def get_peers_by_ring(self, ring_level: RingLevel) -> list[Peer]:
        """Return all peers in a given ring level."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM peers WHERE ring_level = ? ORDER BY added_at",
            (ring_level.value,),
        ) as cur:
            rows = await cur.fetchall()
            return [self._row_to_peer(r) for r in rows]

    async def get_all_peers(self) -> list[Peer]:
        """Return every known peer."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM peers ORDER BY ring_level, added_at"
        ) as cur:
            rows = await cur.fetchall()
            return [self._row_to_peer(r) for r in rows]

    async def promote_peer(self, public_key: str, new_level: RingLevel) -> bool:
        """Move a peer to an inner (lower-number) ring.

        Returns False if the peer is not found or the target ring is full.
        """
        assert self._db is not None
        peer = await self.get_peer(public_key)
        if peer is None:
            return False
        if await self._count_ring(new_level) >= RING_CAPS[new_level]:
            return False
        await self._db.execute(
            "UPDATE peers SET ring_level = ? WHERE public_key = ?",
            (new_level.value, public_key),
        )
        await self._db.commit()
        return True

    async def demote_peer(self, public_key: str, new_level: RingLevel) -> bool:
        """Move a peer to an outer (higher-number) ring.

        Returns False if the peer is not found or the target ring is full.
        """
        assert self._db is not None
        peer = await self.get_peer(public_key)
        if peer is None:
            return False
        if await self._count_ring(new_level) >= RING_CAPS[new_level]:
            return False
        await self._db.execute(
            "UPDATE peers SET ring_level = ? WHERE public_key = ?",
            (new_level.value, public_key),
        )
        await self._db.commit()
        return True

    async def update_last_seen(self, public_key: str, timestamp: float) -> None:
        """Update the last_seen timestamp for a peer."""
        assert self._db is not None
        await self._db.execute(
            "UPDATE peers SET last_seen = ? WHERE public_key = ?",
            (timestamp, public_key),
        )
        await self._db.commit()

    async def get_sync_peers(self) -> list[Peer]:
        """Return peers that should receive content during gossip.

        CORE and INNER peers get full sync.
        MIDDLE peers are included but will only receive SEEDs/PARAGRAPHs
        (that filtering is the caller's responsibility; this method just returns
        the full Peer objects so callers can check ring_level).
        OUTER peers are excluded from gossip push.
        """
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM peers WHERE ring_level IN (?, ?, ?) ORDER BY ring_level, added_at",
            (RingLevel.CORE.value, RingLevel.INNER.value, RingLevel.MIDDLE.value),
        ) as cur:
            rows = await cur.fetchall()
            return [self._row_to_peer(r) for r in rows]

    async def get_ring_stats(self) -> dict:
        """Return peer counts per ring level plus a total."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT ring_level, COUNT(*) as cnt FROM peers GROUP BY ring_level"
        ) as cur:
            rows = await cur.fetchall()

        counts: dict = {level.value: 0 for level in RingLevel}
        for row in rows:
            counts[row["ring_level"]] = row["cnt"]

        counts["total"] = sum(counts[level.value] for level in RingLevel)
        return counts
