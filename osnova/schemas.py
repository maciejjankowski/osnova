"""Pydantic models for the Osnova protocol."""
from __future__ import annotations

import hashlib
import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class RingLevel(str, Enum):
    CORE = "core"        # ~5 peers, full real-time sync
    INNER = "inner"      # ~15 peers, full replication
    MIDDLE = "middle"    # ~50 peers, SEEDs + PARAGRAPHs only
    OUTER = "outer"      # ~95 peers, on-demand only


RING_CAPS = {
    RingLevel.CORE: 5,
    RingLevel.INNER: 15,
    RingLevel.MIDDLE: 50,
    RingLevel.OUTER: 95,
}


class ContentType(str, Enum):
    POST = "post"
    COMMENT = "comment"
    RESHARE = "reshare"
    ARTICLE = "article"


class Identity(BaseModel):
    """A node's public identity."""
    public_key: str          # hex-encoded Ed25519 public key
    display_name: str
    created_at: float = Field(default_factory=time.time)


class Peer(BaseModel):
    """A peer in the trust ring."""
    public_key: str
    display_name: str
    ring_level: RingLevel
    endpoint: str            # HTTP endpoint for gossip (e.g. "http://localhost:8001")
    added_at: float = Field(default_factory=time.time)
    last_seen: float = 0.0


class ContentEntry(BaseModel):
    """A single entry in the append-only log."""
    author_key: str          # public key of author
    content_type: ContentType
    body: str                # text content
    parent_hash: Optional[str] = None   # for comments/reshares: hash of parent
    metadata: dict = Field(default_factory=dict)  # PARDES tags, riddle constraints, etc.
    timestamp: float = Field(default_factory=time.time)
    signature: str = ""      # hex-encoded Ed25519 signature

    @computed_field
    @property
    def content_hash(self) -> str:
        """Deterministic hash of the content (excludes signature)."""
        payload = f"{self.author_key}:{self.content_type}:{self.body}:{self.parent_hash}:{self.timestamp}"
        return hashlib.sha256(payload.encode()).hexdigest()


class SyncRequest(BaseModel):
    """Request to sync content from a peer."""
    requester_key: str
    known_hashes: list[str] = Field(default_factory=list)  # hashes we already have
    since_timestamp: float = 0.0  # only entries after this time
    max_entries: int = 100


class SyncResponse(BaseModel):
    """Response containing new content entries."""
    entries: list[ContentEntry]
    peer_key: str
    has_more: bool = False


class SignalType(str, Enum):
    """Network signals a node can broadcast."""
    CANARY = "canary"          # node is compromised/captured
    EJECT = "eject"            # node is voluntarily disappearing
    CLOSING = "closing"        # final message before eject (encrypted for ring)


class EjectPackage(BaseModel):
    """Package created when a node ejects from the network."""
    author_key: str                    # public key of ejecting node
    content_entries: list[ContentEntry]  # all content from the log
    peer_list: list[Peer]              # ring members (for re-attachment)
    timestamp: float = Field(default_factory=time.time)
    signature: str = ""                # signs the whole package
    include_provenance: bool = True    # if False, strip author_key from entries on re-attach
    closing_message: str = ""          # encrypted for ring members only


class CanarySignal(BaseModel):
    """Alert broadcast to trust ring that node is compromised."""
    author_key: str
    signal_type: SignalType = SignalType.CANARY
    message: str = ""          # optional context (encrypted for ring)
    timestamp: float = Field(default_factory=time.time)
    signature: str = ""        # proves this came from the real node
    severity: str = "critical"  # critical = assume all content compromised


class NodeConfig(BaseModel):
    """Configuration for a node."""
    display_name: str
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = "./data"
    gossip_interval_seconds: int = 30
    bootstrap_peers: list[str] = Field(default_factory=list)  # endpoints to discover peers
