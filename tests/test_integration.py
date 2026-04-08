"""Multi-node integration tests for Osnova.

Spawns 3 real uvicorn processes on ports 9100-9102 with temp data dirs
and exercises the full peer registration -> content creation -> gossip sync
pipeline over HTTP.

Run with:
    pytest -m integration tests/test_integration.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator

import httpx
import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PORTS = [9100, 9101, 9102]
NAMES = ["alpha", "beta", "gamma"]
STARTUP_TIMEOUT = 30      # seconds to wait for node health
REQUEST_TIMEOUT = 5.0     # seconds per HTTP request
SYNC_WAIT = 2.0           # seconds to wait after triggering sync
POLL_INTERVAL = 0.3       # seconds between health-check polls

BASE_URLS = [f"http://127.0.0.1:{p}" for p in PORTS]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_node(base_url: str, timeout: float = STARTUP_TIMEOUT) -> None:
    """Poll /api/identity until the node responds or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/identity", timeout=1.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Node at {base_url} did not start within {timeout}s")


def _get_identity(base_url: str) -> dict:
    r = httpx.get(f"{base_url}/api/identity", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _add_peer(base_url: str, peer_identity: dict, peer_base_url: str, ring_level: str = "inner") -> dict:
    """Register a peer on a node."""
    payload = {
        "public_key": peer_identity["public_key"],
        "display_name": peer_identity["display_name"],
        "ring_level": ring_level,
        "endpoint": peer_base_url,
    }
    r = httpx.post(f"{base_url}/api/rings/peers", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _create_post(base_url: str, body: str, metadata: dict | None = None) -> dict:
    payload: dict = {"body": body}
    if metadata:
        payload["metadata"] = metadata
    r = httpx.post(f"{base_url}/api/posts", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _get_posts(base_url: str) -> list[dict]:
    r = httpx.get(f"{base_url}/api/posts", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _trigger_pull(base_url: str) -> dict:
    r = httpx.post(f"{base_url}/api/sync/pull", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _get_comments(base_url: str, content_hash: str) -> list[dict]:
    r = httpx.get(f"{base_url}/api/posts/{content_hash}/comments", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _add_comment(base_url: str, content_hash: str, body: str) -> dict:
    r = httpx.post(
        f"{base_url}/api/posts/{content_hash}/comment",
        json={"body": body},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Fixture: 3-node cluster
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def three_nodes() -> Generator[list[dict], None, None]:
    """Start 3 uvicorn nodes, yield their metadata, then tear them down."""
    procs: list[subprocess.Popen] = []
    tmpdirs: list[tempfile.TemporaryDirectory] = []

    try:
        for port, name in zip(PORTS, NAMES):
            tdir = tempfile.TemporaryDirectory(prefix=f"osnova_{name}_")
            tmpdirs.append(tdir)

            env = {
                **os.environ,
                "OSNOVA_NAME": name,
                "OSNOVA_PORT": str(port),
                "OSNOVA_HOST": "127.0.0.1",
                "OSNOVA_DATA_DIR": tdir.name,
                "OSNOVA_GOSSIP_INTERVAL": "9999",  # disable automatic gossip
            }

            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "osnova.app:create_app",
                    "--factory",
                    "--host", "127.0.0.1",
                    "--port", str(port),
                    "--log-level", "warning",
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent),
            )
            procs.append(proc)

        # Wait for all nodes to be healthy
        for base_url in BASE_URLS:
            _wait_for_node(base_url)

        # Collect identities
        identities = [_get_identity(url) for url in BASE_URLS]
        node_info = [
            {"url": url, "identity": ident, "name": name}
            for url, ident, name in zip(BASE_URLS, identities, NAMES)
        ]

        yield node_info

    finally:
        for proc in procs:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for tdir in tmpdirs:
            tdir.cleanup()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_nodes_start_and_have_identities(three_nodes):
    """All 3 nodes start and return distinct public keys."""
    keys = [n["identity"]["public_key"] for n in three_nodes]
    assert len(keys) == 3
    assert len(set(keys)) == 3, "Each node must have a unique public key"
    for node in three_nodes:
        assert node["identity"]["display_name"] in NAMES


@pytest.mark.integration
def test_peer_registration(three_nodes):
    """Node alpha registers beta and gamma as inner ring peers."""
    alpha = three_nodes[0]
    beta = three_nodes[1]
    gamma = three_nodes[2]

    # alpha adds beta
    result = _add_peer(alpha["url"], beta["identity"], beta["url"], ring_level="inner")
    assert result["public_key"] == beta["identity"]["public_key"]
    assert result["ring_level"] == "inner"

    # alpha adds gamma
    result = _add_peer(alpha["url"], gamma["identity"], gamma["url"], ring_level="inner")
    assert result["public_key"] == gamma["identity"]["public_key"]

    # Verify alpha's ring has 2 inner peers
    r = httpx.get(f"{alpha['url']}/api/rings/inner", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    peers = r.json()
    peer_keys = {p["public_key"] for p in peers}
    assert beta["identity"]["public_key"] in peer_keys
    assert gamma["identity"]["public_key"] in peer_keys


@pytest.mark.integration
def test_content_creation_and_sync(three_nodes):
    """Alpha creates a post; after beta pulls from alpha, beta's feed contains it."""
    alpha = three_nodes[0]
    beta = three_nodes[1]

    # Ensure beta knows about alpha (register alpha as beta's peer)
    _add_peer(beta["url"], alpha["identity"], alpha["url"], ring_level="inner")

    # Alpha creates a post
    post = _create_post(alpha["url"], "Integration test post from alpha node")
    post_hash = post["content_hash"]
    assert post["author_key"] == alpha["identity"]["public_key"]
    assert post["body"] == "Integration test post from alpha node"

    # Verify alpha has the post
    alpha_posts = _get_posts(alpha["url"])
    alpha_hashes = {p["content_hash"] for p in alpha_posts}
    assert post_hash in alpha_hashes

    # Beta pulls from its peers (which now includes alpha)
    pull_result = _trigger_pull(beta["url"])
    assert pull_result["peers_contacted"] >= 1
    assert pull_result["total_new_entries"] >= 1

    # Beta's feed should now contain alpha's post
    beta_posts = _get_posts(beta["url"])
    beta_hashes = {p["content_hash"] for p in beta_posts}
    assert post_hash in beta_hashes, (
        f"Post {post_hash[:12]}... not found in beta's feed after sync. "
        f"Beta has: {[h[:12] for h in beta_hashes]}"
    )


@pytest.mark.integration
def test_comment_flow(three_nodes):
    """Beta comments on alpha's post; after alpha syncs from beta, it sees the comment."""
    alpha = three_nodes[0]
    beta = three_nodes[1]

    # Ensure alpha knows about beta
    # (beta was already added to alpha's ring in test_peer_registration - but
    # we use independent state so re-add; 409 is fine if already exists)
    try:
        _add_peer(alpha["url"], beta["identity"], beta["url"], ring_level="inner")
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 409:
            raise

    # Create a fresh post on alpha for this test
    post = _create_post(alpha["url"], "Post for comment flow test")
    post_hash = post["content_hash"]

    # Beta needs this post to comment on it - pull it first
    # (beta already has alpha as peer from previous test)
    _trigger_pull(beta["url"])

    # Verify beta has the post
    beta_posts = _get_posts(beta["url"])
    beta_hashes = {p["content_hash"] for p in beta_posts}
    assert post_hash in beta_hashes, "Beta must have the post before commenting"

    # Beta adds a comment
    comment = _add_comment(beta["url"], post_hash, "Beta's comment on alpha's post")
    comment_hash = comment["content_hash"]
    assert comment["parent_hash"] == post_hash
    assert comment["author_key"] == beta["identity"]["public_key"]

    # Alpha pulls from beta to get the comment
    _trigger_pull(alpha["url"])

    # Alpha should now see beta's comment
    alpha_comments = _get_comments(alpha["url"], post_hash)
    comment_hashes = {c["content_hash"] for c in alpha_comments}
    assert comment_hash in comment_hashes, (
        f"Comment {comment_hash[:12]}... not found on alpha after sync. "
        f"Alpha comments: {[h[:12] for h in comment_hashes]}"
    )


@pytest.mark.integration
def test_riddle_encoding_across_nodes(three_nodes):
    """Alpha creates a riddle-encoded post; after sync, beta can verify integrity."""
    from osnova.integrity.riddle import encode_content, verify_content_integrity

    alpha = three_nodes[0]
    beta = three_nodes[1]

    post_body = (
        "The network relies on trust rings to propagate content.\n"
        "Each node verifies signatures before storing entries.\n"
        "Tamper-evident encoding protects high-integrity posts."
    )

    # Encode the content with riddle metadata
    riddle_metadata = encode_content(post_body, seed=42)
    assert riddle_metadata["encoded"] is True

    # Verify locally before posting
    assert verify_content_integrity(post_body, riddle_metadata) is True

    # Alpha creates the post with riddle metadata
    post = _create_post(alpha["url"], post_body, metadata=riddle_metadata)
    post_hash = post["content_hash"]
    assert post["metadata"]["encoded"] is True

    # Beta pulls from alpha
    pull_result = _trigger_pull(beta["url"])
    assert pull_result["total_new_entries"] >= 1

    # Retrieve the post from beta
    beta_posts = _get_posts(beta["url"])
    synced_post = next((p for p in beta_posts if p["content_hash"] == post_hash), None)
    assert synced_post is not None, f"Riddle post not found on beta after sync"

    # Verify riddle integrity on beta using the synced post's metadata
    assert verify_content_integrity(synced_post["body"], synced_post["metadata"]), (
        "Riddle integrity check failed on beta after sync - metadata or body was corrupted"
    )

    # Verify a tampered version would fail
    assert not verify_content_integrity("tampered body", synced_post["metadata"]), (
        "Tampered body should NOT pass integrity check"
    )
