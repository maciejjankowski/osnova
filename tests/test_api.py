"""Tests for the Osnova FastAPI routes."""
from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from osnova.app import create_app
from osnova.crypto.identity import generate_keypair, public_key_hex, save_keypair
from osnova.schemas import RingLevel


# ---------------------------------------------------------------------------
# App fixture - spins up a fresh app per test with a tmp data dir
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_app(tmp_path):
    """Create a TestClient backed by a fresh Osnova app with a temp data dir."""
    # Pre-generate a keypair so startup is deterministic
    signing_key, verify_key = generate_keypair()
    key_file = tmp_path / "identity.key"
    save_keypair(signing_key, key_file)

    # Write minimal config
    import json
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "display_name": "test-node",
        "host": "127.0.0.1",
        "port": 8099,
        "data_dir": str(tmp_path),
        "gossip_interval_seconds": 3600,  # don't actually gossip during tests
    }))

    app = create_app(config_path=str(config_file))
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, public_key_hex(verify_key)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class TestIdentity:
    def test_get_identity(self, tmp_app):
        client, node_key = tmp_app
        resp = client.get("/api/identity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_key"] == node_key
        assert data["display_name"] == "test-node"
        assert "created_at" in data


# ---------------------------------------------------------------------------
# Posts (content)
# ---------------------------------------------------------------------------

class TestPosts:
    def test_create_post(self, tmp_app):
        client, node_key = tmp_app
        resp = client.post("/api/posts", json={"body": "Hello Osnova", "metadata": {}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == "Hello Osnova"
        assert data["author_key"] == node_key
        assert data["content_type"] == "post"
        assert data["signature"] != ""
        assert "content_hash" in data

    def test_create_post_with_metadata(self, tmp_app):
        client, _ = tmp_app
        meta = {"pardes_layer": "peshat", "tags": ["truth", "network"]}
        resp = client.post("/api/posts", json={"body": "Layered post", "metadata": meta})
        assert resp.status_code == 200
        assert resp.json()["metadata"] == meta

    def test_get_feed_empty(self, tmp_app):
        client, _ = tmp_app
        resp = client.get("/api/posts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_feed_returns_posts(self, tmp_app):
        client, node_key = tmp_app
        for i in range(3):
            client.post("/api/posts", json={"body": f"Post {i}", "metadata": {}})

        resp = client.get("/api/posts")
        assert resp.status_code == 200
        posts = resp.json()
        assert len(posts) == 3

    def test_get_feed_limit_offset(self, tmp_app):
        client, _ = tmp_app
        for i in range(5):
            client.post("/api/posts", json={"body": f"Post {i}", "metadata": {}})

        resp = client.get("/api/posts?limit=2&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp2 = client.get("/api/posts?limit=2&offset=2")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 2

    def test_get_feed_filter_by_author(self, tmp_app):
        client, node_key = tmp_app
        client.post("/api/posts", json={"body": "My post", "metadata": {}})

        resp = client.get(f"/api/posts?author_key={node_key}")
        assert resp.status_code == 200
        posts = resp.json()
        assert len(posts) == 1
        assert posts[0]["author_key"] == node_key

        resp2 = client.get("/api/posts?author_key=nonexistent_key")
        assert resp2.status_code == 200
        assert resp2.json() == []

    def test_get_single_post(self, tmp_app):
        client, _ = tmp_app
        create_resp = client.post("/api/posts", json={"body": "Specific post", "metadata": {}})
        content_hash = create_resp.json()["content_hash"]

        resp = client.get(f"/api/posts/{content_hash}")
        assert resp.status_code == 200
        assert resp.json()["content_hash"] == content_hash
        assert resp.json()["body"] == "Specific post"

    def test_get_single_post_not_found(self, tmp_app):
        client, _ = tmp_app
        resp = client.get("/api/posts/deadbeefdeadbeef")
        assert resp.status_code == 404

    def test_add_comment(self, tmp_app):
        client, node_key = tmp_app
        post_resp = client.post("/api/posts", json={"body": "Parent post", "metadata": {}})
        content_hash = post_resp.json()["content_hash"]

        comment_resp = client.post(
            f"/api/posts/{content_hash}/comment",
            json={"body": "A comment"},
        )
        assert comment_resp.status_code == 200
        comment = comment_resp.json()
        assert comment["content_type"] == "comment"
        assert comment["parent_hash"] == content_hash
        assert comment["body"] == "A comment"

    def test_add_comment_to_missing_post(self, tmp_app):
        client, _ = tmp_app
        resp = client.post("/api/posts/notahash/comment", json={"body": "Orphan comment"})
        assert resp.status_code == 404

    def test_get_comments(self, tmp_app):
        client, _ = tmp_app
        post_resp = client.post("/api/posts", json={"body": "Post with comments", "metadata": {}})
        content_hash = post_resp.json()["content_hash"]

        for i in range(2):
            client.post(
                f"/api/posts/{content_hash}/comment",
                json={"body": f"Comment {i}"},
            )

        resp = client.get(f"/api/posts/{content_hash}/comments")
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 2
        assert all(c["parent_hash"] == content_hash for c in comments)

    def test_reshare(self, tmp_app):
        client, node_key = tmp_app
        post_resp = client.post("/api/posts", json={"body": "Original content", "metadata": {}})
        content_hash = post_resp.json()["content_hash"]

        reshare_resp = client.post(f"/api/posts/{content_hash}/reshare")
        assert reshare_resp.status_code == 200
        reshare = reshare_resp.json()
        assert reshare["content_type"] == "reshare"
        assert reshare["parent_hash"] == content_hash
        assert reshare["metadata"]["reshared_from"] == node_key

    def test_reshare_missing_post(self, tmp_app):
        client, _ = tmp_app
        resp = client.post("/api/posts/notahash/reshare")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Ring management
# ---------------------------------------------------------------------------

class TestRings:
    def _make_peer(self, suffix: str = "a", ring_level: str = "outer") -> dict:
        return {
            "public_key": f"pk_{suffix}" + "0" * 58,
            "display_name": f"Peer {suffix}",
            "ring_level": ring_level,
            "endpoint": f"http://localhost:800{suffix}",
            "added_at": 1000000.0,
            "last_seen": 0.0,
        }

    def test_get_ring_stats_empty(self, tmp_app):
        client, _ = tmp_app
        resp = client.get("/api/rings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["core"] == 0

    def test_add_peer(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("1")
        resp = client.post("/api/rings/peers", json=peer)
        assert resp.status_code == 200
        data = resp.json()
        assert data["public_key"] == peer["public_key"]
        assert data["ring_level"] == "outer"

    def test_add_peer_duplicate_rejected(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("2")
        client.post("/api/rings/peers", json=peer)
        resp = client.post("/api/rings/peers", json=peer)
        assert resp.status_code == 409

    def test_get_ring_peers(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("3")
        client.post("/api/rings/peers", json=peer)

        resp = client.get("/api/rings/outer")
        assert resp.status_code == 200
        peers = resp.json()
        assert len(peers) == 1
        assert peers[0]["public_key"] == peer["public_key"]

    def test_get_ring_peers_invalid_level(self, tmp_app):
        client, _ = tmp_app
        resp = client.get("/api/rings/bogus")
        assert resp.status_code == 400

    def test_remove_peer(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("4")
        client.post("/api/rings/peers", json=peer)

        resp = client.delete(f"/api/rings/peers/{peer['public_key']}")
        assert resp.status_code == 200
        assert resp.json()["removed"] is True

        # Confirm gone
        resp2 = client.get("/api/rings/outer")
        assert resp2.json() == []

    def test_remove_peer_not_found(self, tmp_app):
        client, _ = tmp_app
        resp = client.delete("/api/rings/peers/nonexistent_key")
        assert resp.status_code == 404

    def test_promote_peer(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("5", ring_level="outer")
        client.post("/api/rings/peers", json=peer)

        resp = client.put(
            f"/api/rings/peers/{peer['public_key']}/promote",
            json={"ring_level": "middle"},
        )
        assert resp.status_code == 200
        assert resp.json()["ring_level"] == "middle"

    def test_promote_peer_invalid_level(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("6")
        client.post("/api/rings/peers", json=peer)
        resp = client.put(
            f"/api/rings/peers/{peer['public_key']}/promote",
            json={"ring_level": "invalid"},
        )
        assert resp.status_code == 400

    def test_ring_stats_updated(self, tmp_app):
        client, _ = tmp_app
        peer = self._make_peer("7", ring_level="inner")
        client.post("/api/rings/peers", json=peer)

        resp = client.get("/api/rings")
        data = resp.json()
        assert data["inner"] == 1
        assert data["total"] == 1


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------

class TestSync:
    def test_sync_empty_log(self, tmp_app):
        client, node_key = tmp_app
        payload = {
            "requester_key": node_key,
            "known_hashes": [],
            "since_timestamp": 0.0,
            "max_entries": 50,
        }
        resp = client.post("/api/sync", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["peer_key"] == node_key
        assert data["has_more"] is False

    def test_sync_returns_new_entries(self, tmp_app):
        client, node_key = tmp_app

        # Create a post
        post_resp = client.post("/api/posts", json={"body": "Sync me", "metadata": {}})
        content_hash = post_resp.json()["content_hash"]

        # Sync request that doesn't know about that entry
        payload = {
            "requester_key": node_key,
            "known_hashes": [],
            "since_timestamp": 0.0,
            "max_entries": 50,
        }
        resp = client.post("/api/sync", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content_hash"] == content_hash

    def test_sync_excludes_known_hashes(self, tmp_app):
        client, node_key = tmp_app

        post_resp = client.post("/api/posts", json={"body": "Already known", "metadata": {}})
        content_hash = post_resp.json()["content_hash"]

        payload = {
            "requester_key": node_key,
            "known_hashes": [content_hash],
            "since_timestamp": 0.0,
            "max_entries": 50,
        }
        resp = client.post("/api/sync", json=payload)
        assert resp.status_code == 200
        assert resp.json()["entries"] == []

    def test_sync_pull_no_peers(self, tmp_app):
        """Manual gossip pull with no peers configured returns empty results."""
        client, _ = tmp_app
        resp = client.post("/api/sync/pull")
        assert resp.status_code == 200
        data = resp.json()
        assert data["peers_contacted"] == 0
        assert data["total_new_entries"] == 0


# ---------------------------------------------------------------------------
# Signal endpoints
# ---------------------------------------------------------------------------

class TestSignals:
    def test_receive_canary_signal(self, tmp_app):
        client, node_key = tmp_app
        payload = {
            "signal_type": "canary",
            "author_key": node_key,
            "message": "Compromised",
            "timestamp": 1000000.0,
            "signature": "abc123",
            "severity": "critical",
        }
        resp = client.post("/api/signals/receive", json=payload)
        assert resp.status_code == 200
        assert resp.json()["accepted"] is True
        assert resp.json()["signal_type"] == "canary"

    def test_receive_eject_signal(self, tmp_app):
        client, node_key = tmp_app
        payload = {
            "signal_type": "eject",
            "author_key": node_key,
            "message": "Leaving",
            "timestamp": 1000001.0,
            "signature": "def456",
            "severity": "critical",
            "content_entries": [],
            "peer_list": [],
            "closing_message": "Goodbye",
        }
        resp = client.post("/api/signals/receive", json=payload)
        assert resp.status_code == 200
        assert resp.json()["signal_type"] == "eject"

    def test_broadcast_canary_no_peers(self, tmp_app):
        """Canary broadcast with no ring peers succeeds (just no HTTP calls made)."""
        client, _ = tmp_app
        resp = client.post(
            "/api/signals/canary",
            json={"message": "Test compromise", "severity": "critical"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_type"] == "canary"
        assert data["severity"] == "critical"
        assert data["signature"] != ""

    def test_eject_no_content(self, tmp_app):
        """Eject with empty log packages zero entries."""
        client, node_key = tmp_app
        resp = client.post(
            "/api/signals/eject",
            json={"closing_message": "Farewell", "include_provenance": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ejected"] is True
        assert data["author_key"] == node_key
        assert data["entries_packaged"] == 0

    def test_eject_packages_existing_content(self, tmp_app):
        """Eject includes all previously created posts."""
        client, node_key = tmp_app
        for i in range(3):
            client.post("/api/posts", json={"body": f"Post {i}", "metadata": {}})

        resp = client.post(
            "/api/signals/eject",
            json={"closing_message": "", "include_provenance": True},
        )
        assert resp.status_code == 200
        assert resp.json()["entries_packaged"] == 3
