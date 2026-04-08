"""Append-only content log backed by SQLite (aiosqlite)."""
from __future__ import annotations

import json
from typing import Optional

import aiosqlite

from osnova.schemas import ContentEntry, ContentType


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    content_hash  TEXT PRIMARY KEY,
    author_key    TEXT NOT NULL,
    content_type  TEXT NOT NULL,
    body          TEXT NOT NULL,
    parent_hash   TEXT,
    metadata      TEXT NOT NULL DEFAULT '{}',
    timestamp     REAL NOT NULL,
    signature     TEXT NOT NULL DEFAULT ''
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries (timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_entries_author_key ON entries (author_key);",
    "CREATE INDEX IF NOT EXISTS idx_entries_parent_hash ON entries (parent_hash);",
]


def _row_to_entry(row: aiosqlite.Row) -> ContentEntry:
    return ContentEntry(
        author_key=row["author_key"],
        content_type=ContentType(row["content_type"]),
        body=row["body"],
        parent_hash=row["parent_hash"],
        metadata=json.loads(row["metadata"]),
        timestamp=row["timestamp"],
        signature=row["signature"],
    )


class ContentLog:
    """Async append-only log stored in SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Open connection and create tables/indexes if they don't exist."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEXES_SQL:
            await self._db.execute(idx_sql)
        await self._db.commit()

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("ContentLog not initialized - call await log.initialize() first")
        return self._db

    async def append(self, entry: ContentEntry) -> str:
        """Append entry to log. Returns content_hash. Idempotent - rejects duplicates."""
        db = await self._conn()
        content_hash = entry.content_hash

        # Check for duplicate
        async with db.execute(
            "SELECT 1 FROM entries WHERE content_hash = ?", (content_hash,)
        ) as cursor:
            if await cursor.fetchone() is not None:
                raise ValueError(f"Entry with hash {content_hash!r} already exists")

        await db.execute(
            """
            INSERT INTO entries
                (content_hash, author_key, content_type, body, parent_hash, metadata, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content_hash,
                entry.author_key,
                entry.content_type.value,
                entry.body,
                entry.parent_hash,
                json.dumps(entry.metadata),
                entry.timestamp,
                entry.signature,
            ),
        )
        await db.commit()
        return content_hash

    async def get(self, content_hash: str) -> Optional[ContentEntry]:
        """Return a single entry by its hash, or None if not found."""
        db = await self._conn()
        async with db.execute(
            "SELECT * FROM entries WHERE content_hash = ?", (content_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_entry(row)

    async def get_feed(
        self,
        limit: int = 50,
        offset: int = 0,
        author_key: Optional[str] = None,
    ) -> list[ContentEntry]:
        """Return entries in reverse-chronological order, optionally filtered by author."""
        db = await self._conn()
        if author_key is not None:
            sql = """
                SELECT * FROM entries
                WHERE author_key = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params = (author_key, limit, offset)
        else:
            sql = "SELECT * FROM entries ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params = (limit, offset)

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_entry(r) for r in rows]

    async def get_comments(self, parent_hash: str) -> list[ContentEntry]:
        """Return all comments on a given post, oldest first."""
        db = await self._conn()
        async with db.execute(
            "SELECT * FROM entries WHERE parent_hash = ? ORDER BY timestamp ASC",
            (parent_hash,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_entry(r) for r in rows]

    async def get_hashes_since(self, since_timestamp: float) -> list[str]:
        """Return content_hashes for entries newer than since_timestamp (for gossip sync)."""
        db = await self._conn()
        async with db.execute(
            "SELECT content_hash FROM entries WHERE timestamp > ? ORDER BY timestamp ASC",
            (since_timestamp,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [r["content_hash"] for r in rows]

    async def get_entries_by_hashes(self, hashes: list[str]) -> list[ContentEntry]:
        """Bulk-fetch entries by a list of content_hashes (for sync)."""
        if not hashes:
            return []
        db = await self._conn()
        placeholders = ",".join("?" * len(hashes))
        async with db.execute(
            f"SELECT * FROM entries WHERE content_hash IN ({placeholders})",
            tuple(hashes),
        ) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_entry(r) for r in rows]

    async def count(self) -> int:
        """Return total number of entries."""
        db = await self._conn()
        async with db.execute("SELECT COUNT(*) FROM entries") as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
