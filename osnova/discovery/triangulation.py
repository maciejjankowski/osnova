"""
Triangulated Content Discovery - Message, Countermessage, Challenge

Content addressing via three signals:
  - MESSAGE (truth): the real content/claim, pointing toward the actual holder
  - COUNTERMESSAGE (falsehood): a plausible counter-claim, structurally
    identical but pointing to a decoy node. Indistinguishable from the
    truth without ring context.
  - CHALLENGE (question): forces interpretation - "which one is real?"
    Only someone with human context (ring membership, shared knowledge)
    can resolve the ambiguity. Machines see two equally valid candidates.

This is PARDES in miniature:
  - Peshat (message): the data, the claim
  - Adversary (countermessage): the structural challenge to the claim
  - Drash (challenge): requires mechanism understanding to resolve

Together, message + countermessage mark a "hot zone" where the content lives.
The challenge prevents machines from completing the last mile.

Also functions as:
  - Lynchpin noise function: two signals in the domain, third requires training
  - Canary trap: choosing the wrong candidate reveals an outsider/infiltrator

Usage:
  # Publisher creates a triad for their content
  triad = create_discovery_triad(content_hash, author_key, real_holder, decoy)

  # Distribute: message to one set of peers, countermessage to another,
  # challenge publicly (or to the broader network)
  # Seeker needs both signals to find the hot zone, then resolves the challenge

  # Verification: only ring members can prove which candidate is real
  is_real = verify_resolution(triad, chosen_candidate, content_hash)
"""

from __future__ import annotations

import hashlib
import hmac
import random
import time
from typing import Optional

from pydantic import BaseModel, Field


class DiscoveryKey(BaseModel):
    """One of two keys that together triangulate content location."""
    key_id: str              # unique identifier for this key
    content_hint: str        # partial hash or semantic hint (not the full content_hash)
    pointer_hash: str        # hash that, combined with the other key, derives the content address
    distribution: str        # "witness_a" or "witness_b" - which key this is
    metadata: dict = Field(default_factory=dict)  # theme-specific camouflage


class ChallengeSignal(BaseModel):
    """Ambiguous signal pointing to two candidates - only one is real."""
    challenge_id: str
    candidate_a: str         # node identifier (public_key hash fragment) - one is real
    candidate_b: str         # node identifier (public_key hash fragment) - one is decoy
    context_hint: str        # human-interpretable clue (domain-specific, like noise function)
    created_at: float = Field(default_factory=time.time)
    # The hint is designed so that someone IN the ring recognizes the real
    # candidate, but someone outside sees two equally plausible options.
    # This is the Lynchpin noise principle applied to discovery.


class DiscoveryTriad(BaseModel):
    """Complete discovery package: two keys + one challenge."""
    triad_id: str
    witness_a: DiscoveryKey
    witness_b: DiscoveryKey
    challenge: ChallengeSignal
    content_hash: str        # the actual content being addressed (NOT distributed publicly)
    author_key: str          # who created this triad
    created_at: float = Field(default_factory=time.time)
    resolution_hash: str     # hash(content_hash + correct_candidate) - for verification


# ---------------------------------------------------------------------------
# TRIAD CREATION
# ---------------------------------------------------------------------------

def _split_hash(content_hash: str, author_key: str) -> tuple[str, str]:
    """
    Split content_hash into two partial hints using author_key as salt.
    Neither half alone reveals the content_hash. Together they do.
    """
    # Derive two independent hashes from content + author
    h1 = hashlib.sha256(f"witness_a:{content_hash}:{author_key}".encode()).hexdigest()
    h2 = hashlib.sha256(f"witness_b:{content_hash}:{author_key}".encode()).hexdigest()

    # The "pointer_hash" is an HMAC - combining both pointers derives the content address
    # pointer_a XOR pointer_b = content locator (simplified: concat + hash)
    return h1[:32], h2[:32]


def _generate_context_hint(real_key: str, decoy_key: str, author_key: str,
                           hint_seed: Optional[str] = None) -> str:
    """
    Generate a context hint that is meaningful to insiders, ambiguous to outsiders.

    The hint is derived from the real candidate's relationship to the author.
    Someone who knows the author's ring can recognize which candidate
    has a relationship; someone who doesn't sees two random keys.

    For MVP: the hint is a hash-derived phrase. In production, this would
    use domain-specific vocabulary (fishing terms, laundry prices, etc.)
    from the Lynchpin noise function.
    """
    seed = hint_seed or f"{real_key}:{author_key}"
    h = hashlib.sha256(seed.encode()).hexdigest()

    # Generate a "clue" that is verifiable by ring members
    # The clue encodes a property of the real candidate that ring members know
    # but outsiders can't distinguish from the decoy's properties
    #
    # Example: "The one who shares your Thursday" - ring members know who
    # they meet on Thursdays. Outsiders see a meaningless phrase.
    #
    # For protocol: we use the first 4 bytes of the relationship hash
    # as a "context token" that ring members can verify against their
    # peer list metadata.
    relationship_token = hashlib.sha256(
        f"relationship:{real_key}:{author_key}".encode()
    ).hexdigest()[:8]

    return relationship_token


def create_discovery_triad(
    content_hash: str,
    author_key: str,
    real_holder_key: str,
    decoy_key: str,
    hint_seed: Optional[str] = None,
) -> DiscoveryTriad:
    """
    Create a discovery triad for a piece of content.

    Args:
        content_hash: hash of the content being addressed
        author_key: public key of the content author
        real_holder_key: public key of the node that actually holds the content
        decoy_key: public key of a node that does NOT hold it (the false candidate)
        hint_seed: optional seed for generating the context hint

    Returns:
        DiscoveryTriad with two keys and an ambiguous challenge
    """
    # Split the content pointer into two witnesses
    pointer_a, pointer_b = _split_hash(content_hash, author_key)

    # Content hints: partial information, not enough alone
    hint_a = content_hash[:8]  # first 8 chars
    hint_b = content_hash[-8:]  # last 8 chars

    triad_id = hashlib.sha256(
        f"triad:{content_hash}:{author_key}:{time.time()}".encode()
    ).hexdigest()[:16]

    # Create witness keys
    witness_a = DiscoveryKey(
        key_id=hashlib.sha256(f"key_a:{triad_id}".encode()).hexdigest()[:12],
        content_hint=hint_a,
        pointer_hash=pointer_a,
        distribution="witness_a",
    )

    witness_b = DiscoveryKey(
        key_id=hashlib.sha256(f"key_b:{triad_id}".encode()).hexdigest()[:12],
        content_hint=hint_b,
        pointer_hash=pointer_b,
        distribution="witness_b",
    )

    # Create the ambiguous challenge
    # Randomly order the candidates so position gives no information
    context_hint = _generate_context_hint(real_holder_key, decoy_key, author_key, hint_seed)

    # Truncate keys to fragments - full keys would make identification too easy
    real_fragment = hashlib.sha256(real_holder_key.encode()).hexdigest()[:16]
    decoy_fragment = hashlib.sha256(decoy_key.encode()).hexdigest()[:16]

    # Random ordering - 50/50 which is candidate_a vs candidate_b
    if hashlib.sha256(f"{triad_id}:order".encode()).digest()[0] % 2 == 0:
        cand_a, cand_b = real_fragment, decoy_fragment
    else:
        cand_a, cand_b = decoy_fragment, real_fragment

    challenge = ChallengeSignal(
        challenge_id=hashlib.sha256(f"challenge:{triad_id}".encode()).hexdigest()[:12],
        candidate_a=cand_a,
        candidate_b=cand_b,
        context_hint=context_hint,
    )

    # Resolution hash: proves which candidate is correct without revealing it
    resolution_hash = hashlib.sha256(
        f"resolution:{content_hash}:{real_fragment}".encode()
    ).hexdigest()

    return DiscoveryTriad(
        triad_id=triad_id,
        witness_a=witness_a,
        witness_b=witness_b,
        challenge=challenge,
        content_hash=content_hash,
        author_key=author_key,
        resolution_hash=resolution_hash,
    )


# ---------------------------------------------------------------------------
# RESOLUTION AND VERIFICATION
# ---------------------------------------------------------------------------

def combine_witnesses(witness_a: DiscoveryKey, witness_b: DiscoveryKey) -> str:
    """
    Combine two witness keys to derive the content locator.
    Both keys are needed - neither alone is sufficient.

    Returns a content locator hash that narrows the search to the "hot zone".
    """
    if witness_a.distribution != "witness_a" or witness_b.distribution != "witness_b":
        raise ValueError("Need exactly one witness_a and one witness_b")

    combined = hashlib.sha256(
        f"{witness_a.pointer_hash}:{witness_b.pointer_hash}".encode()
    ).hexdigest()

    return combined


def verify_resolution(
    triad: DiscoveryTriad,
    chosen_candidate: str,
    content_hash: str,
) -> bool:
    """
    Verify that the seeker chose the correct candidate.

    Args:
        triad: the discovery triad
        chosen_candidate: the candidate fragment the seeker chose (from challenge)
        content_hash: the content hash the seeker claims to have found

    Returns:
        True if the chosen candidate is the real holder and content matches
    """
    expected = hashlib.sha256(
        f"resolution:{content_hash}:{chosen_candidate}".encode()
    ).hexdigest()

    return hmac.compare_digest(expected, triad.resolution_hash)


def derive_candidate_fragment(public_key: str) -> str:
    """
    Derive the candidate fragment from a full public key.
    Used by ring members to check which challenge candidate matches
    a peer they know.
    """
    return hashlib.sha256(public_key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# DISTRIBUTION HELPERS
# ---------------------------------------------------------------------------

def split_distribution_targets(
    peers: list[dict],
    author_key: str,
) -> tuple[list[dict], list[dict]]:
    """
    Split ring peers into two groups for distributing witness_a and witness_b.
    Uses deterministic assignment so the split is reproducible.

    Each peer gets exactly ONE key. No peer gets both.
    The author's node is excluded (they already have the content).

    Args:
        peers: list of peer dicts with at least "public_key" field
        author_key: the content author's public key (excluded from distribution)

    Returns:
        (group_a, group_b) - peers who receive witness_a and witness_b respectively
    """
    eligible = [p for p in peers if p.get("public_key") != author_key]

    group_a = []
    group_b = []

    for peer in eligible:
        # Deterministic assignment based on peer key + author key
        h = hashlib.sha256(f"split:{peer['public_key']}:{author_key}".encode()).digest()
        if h[0] % 2 == 0:
            group_a.append(peer)
        else:
            group_b.append(peer)

    # Ensure both groups are non-empty
    if not group_a and group_b:
        group_a.append(group_b.pop())
    elif not group_b and group_a:
        group_b.append(group_a.pop())

    return group_a, group_b


def select_decoy(
    peers: list[dict],
    real_holder_key: str,
    content_hash: str,
) -> Optional[str]:
    """
    Select a decoy peer for the challenge's false candidate.

    The decoy should be plausible - a real node in the network, just not
    the one holding this specific content. Ideally from a different ring
    level than the real holder to maximize ambiguity.

    Returns the decoy's public_key, or None if no suitable decoy found.
    """
    candidates = [
        p["public_key"] for p in peers
        if p.get("public_key") != real_holder_key
    ]

    if not candidates:
        return None

    # Deterministic selection based on content
    h = hashlib.sha256(f"decoy:{content_hash}:{real_holder_key}".encode()).hexdigest()
    idx = int(h[:8], 16) % len(candidates)
    return candidates[idx]
