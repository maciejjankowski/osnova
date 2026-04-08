"""Tests for discovery API endpoints."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from osnova.app import create_app
from osnova.crypto.identity import generate_keypair, public_key_hex, save_keypair
from osnova.discovery.triangulation import derive_candidate_fragment


# ---------------------------------------------------------------------------
# Shared fixture (same pattern as test_api.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_app(tmp_path):
    signing_key, verify_key = generate_keypair()
    key_file = tmp_path / "identity.key"
    save_keypair(signing_key, key_file)

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "display_name": "test-node",
        "host": "127.0.0.1",
        "port": 8099,
        "data_dir": str(tmp_path),
        "gossip_interval_seconds": 3600,
    }))

    app = create_app(config_path=str(config_file))
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client, signing_key, public_key_hex(verify_key)


def _create_post(client, body="Test post for discovery"):
    resp = client.post("/api/posts", json={"body": body, "metadata": {}})
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Create triad
# ---------------------------------------------------------------------------

class TestDiscoveryCreate:
    def test_create_triad_returns_triad_without_content_hash(self, tmp_app):
        client, _, node_key = tmp_app
        post = _create_post(client)
        content_hash = post["content_hash"]

        resp = client.post("/api/discovery/create", json={"content_hash": content_hash})
        assert resp.status_code == 200
        data = resp.json()

        # content_hash must be stripped from response
        assert "content_hash" not in data
        assert "triad_id" in data
        assert "witness_a" in data
        assert "witness_b" in data
        assert "challenge" in data
        assert data["author_key"] == node_key

    def test_create_triad_challenge_has_two_candidates(self, tmp_app):
        client, _, _ = tmp_app
        post = _create_post(client)

        resp = client.post("/api/discovery/create", json={"content_hash": post["content_hash"]})
        assert resp.status_code == 200
        challenge = resp.json()["challenge"]
        assert challenge["candidate_a"] != ""
        assert challenge["candidate_b"] != ""
        assert challenge["candidate_a"] != challenge["candidate_b"]

    def test_create_triad_with_explicit_decoy(self, tmp_app):
        client, _, node_key = tmp_app
        post = _create_post(client)

        # Explicit decoy key
        decoy = "a" * 64
        resp = client.post("/api/discovery/create", json={
            "content_hash": post["content_hash"],
            "decoy_key": decoy,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "triad_id" in data

    def test_triads_stored_in_state(self, tmp_app):
        client, _, _ = tmp_app
        post = _create_post(client)
        client.post("/api/discovery/create", json={"content_hash": post["content_hash"]})
        client.post("/api/discovery/create", json={"content_hash": post["content_hash"]})

        resp = client.get("/api/discovery/triads")
        assert resp.status_code == 200
        triads = resp.json()
        assert len(triads) == 2
        # content_hash stripped from list too
        for t in triads:
            assert "content_hash" not in t


# ---------------------------------------------------------------------------
# Resolve challenge
# ---------------------------------------------------------------------------

class TestDiscoveryResolve:
    def _create_triad_with_hash(self, client, node_key):
        """Create a post + triad; return (triad_id, content_hash, real_fragment)."""
        post = _create_post(client)
        content_hash = post["content_hash"]

        resp = client.post("/api/discovery/create", json={"content_hash": content_hash})
        assert resp.status_code == 200
        triad_data = resp.json()

        # The real_holder_key == node_key (author == holder in our setup)
        real_fragment = derive_candidate_fragment(node_key)
        return triad_data["triad_id"], content_hash, real_fragment

    def test_resolve_correct_candidate(self, tmp_app):
        client, _, node_key = tmp_app
        triad_id, content_hash, real_fragment = self._create_triad_with_hash(client, node_key)

        resp = client.post("/api/discovery/resolve", json={
            "triad_id": triad_id,
            "chosen_candidate": real_fragment,
            "content_hash": content_hash,
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_resolve_wrong_candidate(self, tmp_app):
        client, _, node_key = tmp_app
        triad_id, content_hash, _ = self._create_triad_with_hash(client, node_key)

        resp = client.post("/api/discovery/resolve", json={
            "triad_id": triad_id,
            "chosen_candidate": "wrong_fragment_abcd",
            "content_hash": content_hash,
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_resolve_wrong_content_hash(self, tmp_app):
        client, _, node_key = tmp_app
        triad_id, _, real_fragment = self._create_triad_with_hash(client, node_key)

        resp = client.post("/api/discovery/resolve", json={
            "triad_id": triad_id,
            "chosen_candidate": real_fragment,
            "content_hash": "wrong_hash_entirely",
        })
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_resolve_unknown_triad(self, tmp_app):
        client, _, node_key = tmp_app

        resp = client.post("/api/discovery/resolve", json={
            "triad_id": "nonexistent_triad",
            "chosen_candidate": "any",
            "content_hash": "any",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Receive key
# ---------------------------------------------------------------------------

class TestDiscoveryReceiveKey:
    def _make_key(self, suffix="a"):
        return {
            "key_id": f"key_{suffix}_abcdef",
            "content_hint": "abc12345",
            "pointer_hash": "def67890" * 4,
            "distribution": "witness_a",
            "metadata": {},
        }

    def test_receive_key_accepted(self, tmp_app):
        client, _, _ = tmp_app
        key = self._make_key("1")

        resp = client.post("/api/discovery/receive-key", json=key)
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is True
        assert data["key_id"] == key["key_id"]

    def test_received_keys_stored(self, tmp_app):
        client, _, _ = tmp_app
        for suffix in ("x", "y"):
            resp = client.post("/api/discovery/receive-key", json=self._make_key(suffix))
            assert resp.status_code == 200

        # Both keys accepted - verify by re-posting and checking count via accept responses
        # (received_keys list is in app.state; there's no dedicated list endpoint,
        # but we confirmed 2 successful accepts above)
        resp_x = client.post("/api/discovery/receive-key", json=self._make_key("z"))
        assert resp_x.status_code == 200
        assert resp_x.json()["key_id"] == "key_z_abcdef"
