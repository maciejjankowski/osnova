"""Tests for osnova.storage.log.ContentLog."""
from __future__ import annotations

import time

import pytest
import pytest_asyncio

from osnova.schemas import ContentEntry, ContentType
from osnova.storage.log import ContentLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def log(tmp_path):
    """Fresh in-memory-style ContentLog for each test (temp file)."""
    db_path = str(tmp_path / "test.db")
    content_log = ContentLog(db_path)
    await content_log.initialize()
    yield content_log
    await content_log.close()


def make_entry(
    body: str = "hello world",
    author_key: str = "author_a",
    content_type: ContentType = ContentType.POST,
    parent_hash: str | None = None,
    timestamp: float | None = None,
    metadata: dict | None = None,
) -> ContentEntry:
    kwargs = dict(
        author_key=author_key,
        content_type=content_type,
        body=body,
        parent_hash=parent_hash,
        metadata=metadata or {},
    )
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    return ContentEntry(**kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_append_and_get_roundtrip(log):
    """Appended entry should be retrievable by its hash."""
    entry = make_entry(body="roundtrip test")
    h = await log.append(entry)

    assert h == entry.content_hash

    fetched = await log.get(h)
    assert fetched is not None
    assert fetched.body == "roundtrip test"
    assert fetched.author_key == "author_a"
    assert fetched.content_type == ContentType.POST
    assert fetched.timestamp == pytest.approx(entry.timestamp)


@pytest.mark.asyncio
async def test_get_returns_none_for_unknown_hash(log):
    fetched = await log.get("nonexistent_hash_000")
    assert fetched is None


@pytest.mark.asyncio
async def test_duplicate_rejection(log):
    """Appending the same entry twice should raise ValueError."""
    entry = make_entry(body="duplicate test")
    await log.append(entry)

    with pytest.raises(ValueError, match="already exists"):
        await log.append(entry)


@pytest.mark.asyncio
async def test_count_increments(log):
    assert await log.count() == 0

    await log.append(make_entry(body="a", timestamp=1.0))
    assert await log.count() == 1

    await log.append(make_entry(body="b", timestamp=2.0))
    assert await log.count() == 2


@pytest.mark.asyncio
async def test_feed_reverse_chronological_order(log):
    """get_feed should return entries newest-first."""
    t = time.time()
    await log.append(make_entry(body="oldest", timestamp=t + 0))
    await log.append(make_entry(body="middle", timestamp=t + 1))
    await log.append(make_entry(body="newest", timestamp=t + 2))

    feed = await log.get_feed()
    assert len(feed) == 3
    assert feed[0].body == "newest"
    assert feed[1].body == "middle"
    assert feed[2].body == "oldest"


@pytest.mark.asyncio
async def test_feed_limit_and_offset(log):
    t = time.time()
    for i in range(5):
        await log.append(make_entry(body=f"post_{i}", timestamp=t + i))

    page1 = await log.get_feed(limit=2, offset=0)
    page2 = await log.get_feed(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    # No overlap
    hashes1 = {e.content_hash for e in page1}
    hashes2 = {e.content_hash for e in page2}
    assert hashes1.isdisjoint(hashes2)


@pytest.mark.asyncio
async def test_feed_filtered_by_author(log):
    t = time.time()
    await log.append(make_entry(body="alice post 1", author_key="alice", timestamp=t + 0))
    await log.append(make_entry(body="bob post 1",   author_key="bob",   timestamp=t + 1))
    await log.append(make_entry(body="alice post 2", author_key="alice", timestamp=t + 2))

    alice_feed = await log.get_feed(author_key="alice")
    assert len(alice_feed) == 2
    assert all(e.author_key == "alice" for e in alice_feed)
    # Still reverse-chronological within author
    assert alice_feed[0].body == "alice post 2"
    assert alice_feed[1].body == "alice post 1"


@pytest.mark.asyncio
async def test_comments_retrieval(log):
    """get_comments should return comments on a post, oldest-first."""
    parent = make_entry(body="parent post", timestamp=1000.0)
    parent_hash = await log.append(parent)

    c1 = make_entry(
        body="comment 1",
        content_type=ContentType.COMMENT,
        parent_hash=parent_hash,
        timestamp=1001.0,
    )
    c2 = make_entry(
        body="comment 2",
        content_type=ContentType.COMMENT,
        parent_hash=parent_hash,
        timestamp=1002.0,
    )
    # Unrelated post - should not appear in comments
    await log.append(make_entry(body="unrelated", timestamp=999.0))
    await log.append(c1)
    await log.append(c2)

    comments = await log.get_comments(parent_hash)
    assert len(comments) == 2
    assert comments[0].body == "comment 1"
    assert comments[1].body == "comment 2"


@pytest.mark.asyncio
async def test_get_comments_empty(log):
    comments = await log.get_comments("no_such_parent")
    assert comments == []


@pytest.mark.asyncio
async def test_hashes_since(log):
    """get_hashes_since should return hashes for entries after given timestamp."""
    e1 = make_entry(body="old",    timestamp=100.0)
    e2 = make_entry(body="recent", timestamp=200.0)
    e3 = make_entry(body="newer",  timestamp=300.0)

    h1 = await log.append(e1)
    h2 = await log.append(e2)
    h3 = await log.append(e3)

    hashes = await log.get_hashes_since(since_timestamp=150.0)
    assert set(hashes) == {h2, h3}
    assert h1 not in hashes


@pytest.mark.asyncio
async def test_hashes_since_all(log):
    e1 = make_entry(body="a", timestamp=100.0)
    e2 = make_entry(body="b", timestamp=200.0)
    h1 = await log.append(e1)
    h2 = await log.append(e2)

    hashes = await log.get_hashes_since(since_timestamp=0.0)
    assert set(hashes) == {h1, h2}


@pytest.mark.asyncio
async def test_get_entries_by_hashes(log):
    """Bulk fetch should return all requested entries."""
    e1 = make_entry(body="x", timestamp=1.0)
    e2 = make_entry(body="y", timestamp=2.0)
    e3 = make_entry(body="z", timestamp=3.0)
    h1 = await log.append(e1)
    h2 = await log.append(e2)
    h3 = await log.append(e3)

    fetched = await log.get_entries_by_hashes([h1, h3])
    fetched_hashes = {e.content_hash for e in fetched}
    assert fetched_hashes == {h1, h3}
    assert h2 not in fetched_hashes


@pytest.mark.asyncio
async def test_get_entries_by_hashes_empty_input(log):
    result = await log.get_entries_by_hashes([])
    assert result == []


@pytest.mark.asyncio
async def test_metadata_roundtrip(log):
    """Metadata dict should survive serialization."""
    meta = {"pardes_layer": "drash", "tags": ["truth", "analysis"], "score": 0.92}
    entry = make_entry(body="meta test", metadata=meta)
    h = await log.append(entry)
    fetched = await log.get(h)
    assert fetched.metadata == meta


@pytest.mark.asyncio
async def test_signature_roundtrip(log):
    """Signature field should survive the round-trip."""
    entry = make_entry(body="signed post")
    entry = entry.model_copy(update={"signature": "deadbeef1234"})
    h = await log.append(entry)
    fetched = await log.get(h)
    assert fetched.signature == "deadbeef1234"
