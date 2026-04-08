"""FastAPI APIRouter for the Osnova protocol."""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from osnova.api.middleware import verify_incoming_entries
from osnova.crypto.identity import get_identity, sign_content
from osnova.discovery.triangulation import (
    DiscoveryKey,
    DiscoveryTriad,
    create_discovery_triad,
    select_decoy,
    verify_resolution,
)
from osnova.schemas import (
    CanarySignal,
    ContentEntry,
    ContentType,
    EjectPackage,
    Identity,
    Peer,
    RingLevel,
    SignalType,
    SyncRequest,
    SyncResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request/response helpers
# ---------------------------------------------------------------------------

class CreatePostRequest(BaseModel):
    body: str
    metadata: dict = {}


class CreateCommentRequest(BaseModel):
    body: str


class AddPeerRequest(BaseModel):
    public_key: str
    display_name: str
    ring_level: RingLevel
    endpoint: str


class PromotePeerRequest(BaseModel):
    ring_level: str


class CanaryRequest(BaseModel):
    message: str = ""
    severity: str = "critical"


class EjectRequest(BaseModel):
    closing_message: str = ""
    include_provenance: bool = True


class ReceivedSignal(BaseModel):
    signal_type: SignalType
    author_key: str
    message: str = ""
    timestamp: float
    signature: str = ""
    severity: str = "critical"
    # Eject-specific optional fields
    content_entries: list[ContentEntry] = []
    peer_list: list[Peer] = []
    closing_message: str = ""
    include_provenance: bool = True


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_log(request: Request):
    return request.app.state.content_log


def _get_rings(request: Request):
    return request.app.state.ring_manager


def _get_gossip(request: Request):
    return request.app.state.gossip_service


def _get_signing_key(request: Request):
    return request.app.state.signing_key


def _get_node_key(request: Request) -> str:
    return request.app.state.node_public_key


def _get_display_name(request: Request) -> str:
    return request.app.state.display_name


def _get_signals(request: Request) -> list:
    return request.app.state.received_signals


# ---------------------------------------------------------------------------
# Content endpoints
# ---------------------------------------------------------------------------

@router.post("/api/posts", response_model=ContentEntry)
async def create_post(body: CreatePostRequest, request: Request):
    """Create a new post, auto-signed with this node's key."""
    signing_key = _get_signing_key(request)
    node_key = _get_node_key(request)
    log = _get_log(request)

    entry = ContentEntry(
        author_key=node_key,
        content_type=ContentType.POST,
        body=body.body,
        metadata=body.metadata,
        timestamp=time.time(),
    )
    entry = sign_content(signing_key, entry)

    try:
        await log.append(entry)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return entry


@router.get("/api/posts", response_model=list[ContentEntry])
async def get_feed(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    author_key: Optional[str] = None,
):
    """Get the content feed, optionally filtered by author."""
    log = _get_log(request)
    return await log.get_feed(limit=limit, offset=offset, author_key=author_key)


@router.get("/api/posts/{content_hash}", response_model=ContentEntry)
async def get_post(content_hash: str, request: Request):
    """Get a single post by its content hash."""
    log = _get_log(request)
    entry = await log.get(content_hash)
    if entry is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return entry


@router.post("/api/posts/{content_hash}/comment", response_model=ContentEntry)
async def add_comment(
    content_hash: str,
    body: CreateCommentRequest,
    request: Request,
):
    """Add a comment to a post."""
    log = _get_log(request)
    signing_key = _get_signing_key(request)
    node_key = _get_node_key(request)

    parent = await log.get(content_hash)
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent post not found")

    entry = ContentEntry(
        author_key=node_key,
        content_type=ContentType.COMMENT,
        body=body.body,
        parent_hash=content_hash,
        timestamp=time.time(),
    )
    entry = sign_content(signing_key, entry)

    try:
        await log.append(entry)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return entry


@router.get("/api/posts/{content_hash}/comments", response_model=list[ContentEntry])
async def get_comments(content_hash: str, request: Request):
    """Get all comments on a post."""
    log = _get_log(request)
    parent = await log.get(content_hash)
    if parent is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return await log.get_comments(content_hash)


@router.post("/api/posts/{content_hash}/reshare", response_model=ContentEntry)
async def reshare_post(content_hash: str, request: Request):
    """Reshare a post."""
    log = _get_log(request)
    signing_key = _get_signing_key(request)
    node_key = _get_node_key(request)

    original = await log.get(content_hash)
    if original is None:
        raise HTTPException(status_code=404, detail="Post not found")

    entry = ContentEntry(
        author_key=node_key,
        content_type=ContentType.RESHARE,
        body=original.body,
        parent_hash=content_hash,
        metadata={"reshared_from": original.author_key},
        timestamp=time.time(),
    )
    entry = sign_content(signing_key, entry)

    try:
        await log.append(entry)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return entry


# ---------------------------------------------------------------------------
# Ring management endpoints
# ---------------------------------------------------------------------------

@router.get("/api/rings")
async def get_ring_stats(request: Request):
    """Get peer count statistics for each ring level."""
    rings = _get_rings(request)
    return await rings.get_ring_stats()


@router.get("/api/rings/{ring_level}", response_model=list[Peer])
async def get_ring_peers(ring_level: str, request: Request):
    """Get all peers in a given ring level."""
    rings = _get_rings(request)
    try:
        level = RingLevel(ring_level)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ring level. Must be one of: {[l.value for l in RingLevel]}",
        )
    return await rings.get_peers_by_ring(level)


@router.post("/api/rings/peers", response_model=Peer)
async def add_peer(peer: Peer, request: Request):
    """Add a new peer to the ring."""
    rings = _get_rings(request)
    success = await rings.add_peer(peer)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Ring {peer.ring_level.value!r} is at capacity or peer already exists",
        )
    return peer


@router.delete("/api/rings/peers/{public_key}")
async def remove_peer(public_key: str, request: Request):
    """Remove a peer by public key."""
    rings = _get_rings(request)
    removed = await rings.remove_peer(public_key)
    if not removed:
        raise HTTPException(status_code=404, detail="Peer not found")
    return {"removed": True, "public_key": public_key}


@router.put("/api/rings/peers/{public_key}/promote")
async def promote_peer(public_key: str, body: PromotePeerRequest, request: Request):
    """Promote a peer to a new ring level."""
    rings = _get_rings(request)
    try:
        new_level = RingLevel(body.ring_level)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ring level. Must be one of: {[l.value for l in RingLevel]}",
        )
    success = await rings.promote_peer(public_key, new_level)
    if not success:
        raise HTTPException(
            status_code=409,
            detail="Peer not found or target ring is at capacity",
        )
    peer = await rings.get_peer(public_key)
    return peer


# ---------------------------------------------------------------------------
# Sync endpoints
# ---------------------------------------------------------------------------

@router.post("/api/sync", response_model=SyncResponse)
async def handle_sync(sync_request: SyncRequest, request: Request):
    """Handle an incoming sync request from another node."""
    gossip = _get_gossip(request)
    rings = _get_rings(request)
    log = _get_log(request)

    # Update last_seen for the requester if we know them
    await rings.update_last_seen(sync_request.requester_key, time.time())

    # If the request carries entries (push-style sync), verify and store them
    if hasattr(sync_request, "entries") and sync_request.entries:
        accepted, rejected = verify_incoming_entries(sync_request.entries)
        if rejected:
            logger.warning(
                "Discarded %d entries with invalid signatures from %s",
                len(rejected),
                sync_request.requester_key[:12],
            )
        for entry in accepted:
            try:
                await log.append(entry)
            except ValueError:
                pass

    return await gossip.prepare_sync_response(sync_request)


@router.post("/api/sync/pull")
async def trigger_gossip_pull(request: Request):
    """Manually trigger a gossip round (pull from all CORE+INNER peers)."""
    gossip = _get_gossip(request)
    results = await gossip.run_gossip_round()
    total = sum(results.values())
    return {
        "peers_contacted": len(results),
        "total_new_entries": total,
        "per_peer": results,
    }


# ---------------------------------------------------------------------------
# Identity endpoint
# ---------------------------------------------------------------------------

@router.get("/api/identity", response_model=Identity)
async def get_node_identity(request: Request):
    """Return this node's public identity."""
    signing_key = _get_signing_key(request)
    display_name = _get_display_name(request)
    return get_identity(signing_key, display_name)


# ---------------------------------------------------------------------------
# Signal endpoints (canary + eject)
# ---------------------------------------------------------------------------

@router.post("/api/signals/canary", response_model=CanarySignal)
async def broadcast_canary(body: CanaryRequest, request: Request):
    """Broadcast a canary (compromised) signal to all ring peers.

    Notifies CORE + INNER + MIDDLE peers that this node is compromised.
    """
    signing_key = _get_signing_key(request)
    node_key = _get_node_key(request)
    rings = _get_rings(request)

    from nacl.encoding import HexEncoder
    signal = CanarySignal(
        author_key=node_key,
        signal_type=SignalType.CANARY,
        message=body.message,
        timestamp=time.time(),
        severity=body.severity,
    )

    # Sign the signal payload
    payload = f"{signal.author_key}:{signal.signal_type}:{signal.timestamp}".encode()
    signed = signing_key.sign(payload, encoder=HexEncoder)
    signal = signal.model_copy(update={"signature": signed.signature.decode("ascii")})

    # Broadcast to sync peers (fire-and-forget, log failures)
    peers = await rings.get_sync_peers()
    import httpx
    async with httpx.AsyncClient(timeout=5.0) as client:
        for peer in peers:
            try:
                await client.post(
                    f"{peer.endpoint.rstrip('/')}/api/signals/receive",
                    json={
                        "signal_type": signal.signal_type.value,
                        "author_key": signal.author_key,
                        "message": signal.message,
                        "timestamp": signal.timestamp,
                        "signature": signal.signature,
                        "severity": signal.severity,
                    },
                )
            except Exception as e:
                logger.warning("Failed to send canary to %s: %s", peer.public_key[:8], e)

    logger.warning("CANARY signal broadcast: node %s reported compromised", node_key[:8])
    return signal


@router.post("/api/signals/eject")
async def eject_from_network(body: EjectRequest, request: Request):
    """Eject from the network: package content, notify ring, prepare for disappearance.

    The actual eject module will replace this with full implementation.
    This placeholder packages the content and notifies peers.
    """
    signing_key = _get_signing_key(request)
    node_key = _get_node_key(request)
    log = _get_log(request)
    rings = _get_rings(request)

    # Package all content
    all_entries = await log.get_feed(limit=10000, offset=0)
    all_peers = await rings.get_all_peers()

    package = EjectPackage(
        author_key=node_key,
        content_entries=all_entries,
        peer_list=all_peers,
        timestamp=time.time(),
        closing_message=body.closing_message,
        include_provenance=body.include_provenance,
    )

    # Sign the package
    from nacl.encoding import HexEncoder
    import hashlib
    pkg_hash = hashlib.sha256(
        f"{package.author_key}:{package.timestamp}:{len(package.content_entries)}".encode()
    ).hexdigest()
    signed = signing_key.sign(pkg_hash.encode(), encoder=HexEncoder)
    package = package.model_copy(update={"signature": signed.signature.decode("ascii")})

    # Notify ring peers
    import httpx
    peers = await rings.get_sync_peers()
    async with httpx.AsyncClient(timeout=5.0) as client:
        for peer in peers:
            try:
                await client.post(
                    f"{peer.endpoint.rstrip('/')}/api/signals/receive",
                    json={
                        "signal_type": SignalType.EJECT.value,
                        "author_key": node_key,
                        "message": "Node is ejecting from the network",
                        "timestamp": package.timestamp,
                        "signature": package.signature,
                        "closing_message": body.closing_message,
                        "content_entries": [e.model_dump() for e in all_entries],
                        "peer_list": [p.model_dump() for p in all_peers],
                        "include_provenance": body.include_provenance,
                    },
                )
            except Exception as e:
                logger.warning("Failed to send eject notice to %s: %s", peer.public_key[:8], e)

    logger.warning("EJECT signal sent: node %s ejecting, %d entries packaged", node_key[:8], len(all_entries))

    return {
        "ejected": True,
        "author_key": node_key,
        "entries_packaged": len(all_entries),
        "peers_notified": len(peers),
        "timestamp": package.timestamp,
        "package_signature": package.signature,
    }


# ---------------------------------------------------------------------------
# Discovery endpoints
# ---------------------------------------------------------------------------

class CreateTriadRequest(BaseModel):
    content_hash: str
    decoy_key: Optional[str] = None


class ResolveRequest(BaseModel):
    triad_id: str
    chosen_candidate: str
    content_hash: str


def _get_triads(request: Request) -> list:
    return request.app.state.triads


def _get_received_keys(request: Request) -> list:
    return request.app.state.received_keys


@router.post("/api/discovery/create")
async def discovery_create(body: CreateTriadRequest, request: Request):
    """Create a discovery triad for a content entry."""
    node_key = _get_node_key(request)
    rings = _get_rings(request)
    triads = _get_triads(request)

    decoy_key = body.decoy_key
    if not decoy_key:
        # Auto-select from known peers
        all_peers = await rings.get_all_peers()
        peer_dicts = [{"public_key": p.public_key} for p in all_peers]
        decoy_key = select_decoy(peer_dicts, node_key, body.content_hash)
        if not decoy_key:
            # Fall back to a deterministic synthetic decoy
            import hashlib as _hashlib
            decoy_key = _hashlib.sha256(
                f"synthetic_decoy:{body.content_hash}".encode()
            ).hexdigest()

    triad = create_discovery_triad(
        content_hash=body.content_hash,
        author_key=node_key,
        real_holder_key=node_key,
        decoy_key=decoy_key,
    )
    triads.append(triad)

    # Strip content_hash from response - that's the secret
    response = triad.model_dump()
    del response["content_hash"]
    return response


@router.post("/api/discovery/resolve")
async def discovery_resolve(body: ResolveRequest, request: Request):
    """Attempt to resolve a discovery challenge."""
    triads = _get_triads(request)

    triad = next((t for t in triads if t.triad_id == body.triad_id), None)
    if triad is None:
        raise HTTPException(status_code=404, detail="Triad not found")

    valid = verify_resolution(triad, body.chosen_candidate, body.content_hash)
    return {"valid": valid}


@router.get("/api/discovery/triads")
async def discovery_list_triads(request: Request):
    """List triads this node has created (content_hash stripped)."""
    triads = _get_triads(request)
    result = []
    for t in triads:
        d = t.model_dump()
        del d["content_hash"]
        result.append(d)
    return result


@router.post("/api/discovery/receive-key")
async def discovery_receive_key(key: DiscoveryKey, request: Request):
    """Receive a discovery key from a peer."""
    received_keys = _get_received_keys(request)
    received_keys.append(key)
    return {"accepted": True, "key_id": key.key_id}


@router.post("/api/signals/receive")
async def receive_signal(signal: ReceivedSignal, request: Request):
    """Receive a canary or eject signal from a peer node."""
    signals = _get_signals(request)

    received = {
        "signal_type": signal.signal_type.value,
        "author_key": signal.author_key,
        "message": signal.message,
        "timestamp": signal.timestamp,
        "signature": signal.signature,
        "severity": signal.severity,
        "received_at": time.time(),
    }

    if signal.signal_type == SignalType.EJECT:
        received["closing_message"] = signal.closing_message
        received["entries_count"] = len(signal.content_entries)
        received["peers_count"] = len(signal.peer_list)

    signals.append(received)

    logger.warning(
        "Received %s signal from %s at %s",
        signal.signal_type.value,
        signal.author_key[:8],
        signal.timestamp,
    )

    return {"accepted": True, "signal_type": signal.signal_type.value}
