"""Tests for triangulated content discovery."""
import hashlib

import pytest

from osnova.discovery.triangulation import (
    ChallengeSignal,
    DiscoveryKey,
    DiscoveryTriad,
    combine_witnesses,
    create_discovery_triad,
    derive_candidate_fragment,
    select_decoy,
    split_distribution_targets,
    verify_resolution,
)


@pytest.fixture
def sample_keys():
    return {
        "author": "a" * 64,
        "holder": "b" * 64,
        "decoy": "c" * 64,
        "content_hash": hashlib.sha256(b"test content").hexdigest(),
    }


@pytest.fixture
def sample_triad(sample_keys):
    return create_discovery_triad(
        content_hash=sample_keys["content_hash"],
        author_key=sample_keys["author"],
        real_holder_key=sample_keys["holder"],
        decoy_key=sample_keys["decoy"],
    )


class TestTriadCreation:
    def test_creates_valid_triad(self, sample_triad):
        assert sample_triad.triad_id
        assert sample_triad.witness_a.distribution == "witness_a"
        assert sample_triad.witness_b.distribution == "witness_b"
        assert sample_triad.challenge.candidate_a
        assert sample_triad.challenge.candidate_b
        assert sample_triad.resolution_hash

    def test_witnesses_have_different_pointers(self, sample_triad):
        assert sample_triad.witness_a.pointer_hash != sample_triad.witness_b.pointer_hash

    def test_witnesses_have_different_hints(self, sample_triad):
        assert sample_triad.witness_a.content_hint != sample_triad.witness_b.content_hint

    def test_challenge_candidates_are_different(self, sample_triad):
        assert sample_triad.challenge.candidate_a != sample_triad.challenge.candidate_b

    def test_challenge_contains_real_holder(self, sample_keys, sample_triad):
        real_fragment = derive_candidate_fragment(sample_keys["holder"])
        candidates = {sample_triad.challenge.candidate_a, sample_triad.challenge.candidate_b}
        assert real_fragment in candidates

    def test_challenge_contains_decoy(self, sample_keys, sample_triad):
        decoy_fragment = derive_candidate_fragment(sample_keys["decoy"])
        candidates = {sample_triad.challenge.candidate_a, sample_triad.challenge.candidate_b}
        assert decoy_fragment in candidates

    def test_context_hint_is_present(self, sample_triad):
        assert sample_triad.challenge.context_hint
        assert len(sample_triad.challenge.context_hint) == 8  # hex fragment

    def test_content_hints_are_partial(self, sample_keys, sample_triad):
        full_hash = sample_keys["content_hash"]
        assert sample_triad.witness_a.content_hint == full_hash[:8]
        assert sample_triad.witness_b.content_hint == full_hash[-8:]
        # Neither alone is the full hash
        assert len(sample_triad.witness_a.content_hint) < len(full_hash)


class TestResolution:
    def test_correct_candidate_verifies(self, sample_keys, sample_triad):
        real_fragment = derive_candidate_fragment(sample_keys["holder"])
        assert verify_resolution(
            sample_triad, real_fragment, sample_keys["content_hash"]
        ) is True

    def test_wrong_candidate_fails(self, sample_keys, sample_triad):
        decoy_fragment = derive_candidate_fragment(sample_keys["decoy"])
        assert verify_resolution(
            sample_triad, decoy_fragment, sample_keys["content_hash"]
        ) is False

    def test_wrong_content_hash_fails(self, sample_keys, sample_triad):
        real_fragment = derive_candidate_fragment(sample_keys["holder"])
        assert verify_resolution(
            sample_triad, real_fragment, "wrong_hash"
        ) is False

    def test_random_candidate_fails(self, sample_keys, sample_triad):
        assert verify_resolution(
            sample_triad, "random_garbage", sample_keys["content_hash"]
        ) is False


class TestWitnessCombination:
    def test_combine_produces_locator(self, sample_triad):
        locator = combine_witnesses(sample_triad.witness_a, sample_triad.witness_b)
        assert isinstance(locator, str)
        assert len(locator) == 64  # sha256 hex

    def test_combine_is_deterministic(self, sample_triad):
        loc1 = combine_witnesses(sample_triad.witness_a, sample_triad.witness_b)
        loc2 = combine_witnesses(sample_triad.witness_a, sample_triad.witness_b)
        assert loc1 == loc2

    def test_wrong_distribution_raises(self, sample_triad):
        with pytest.raises(ValueError):
            combine_witnesses(sample_triad.witness_a, sample_triad.witness_a)

    def test_single_witness_insufficient(self, sample_triad, sample_keys):
        # A single witness should not be enough to derive the content hash
        assert sample_triad.witness_a.pointer_hash != sample_keys["content_hash"]
        assert sample_triad.witness_b.pointer_hash != sample_keys["content_hash"]


class TestCandidateFragment:
    def test_derive_is_deterministic(self):
        frag1 = derive_candidate_fragment("test_key")
        frag2 = derive_candidate_fragment("test_key")
        assert frag1 == frag2

    def test_different_keys_produce_different_fragments(self):
        frag1 = derive_candidate_fragment("key_1")
        frag2 = derive_candidate_fragment("key_2")
        assert frag1 != frag2

    def test_fragment_is_truncated(self):
        frag = derive_candidate_fragment("test_key")
        assert len(frag) == 16


class TestDistribution:
    def test_split_produces_two_groups(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(10)]
        group_a, group_b = split_distribution_targets(peers, "author_key")
        assert len(group_a) > 0
        assert len(group_b) > 0
        assert len(group_a) + len(group_b) == 10

    def test_split_excludes_author(self):
        peers = [
            {"public_key": "author_key"},
            {"public_key": "peer_1"},
            {"public_key": "peer_2"},
        ]
        group_a, group_b = split_distribution_targets(peers, "author_key")
        all_keys = [p["public_key"] for p in group_a + group_b]
        assert "author_key" not in all_keys

    def test_split_is_deterministic(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(10)]
        g1a, g1b = split_distribution_targets(peers, "author")
        g2a, g2b = split_distribution_targets(peers, "author")
        assert [p["public_key"] for p in g1a] == [p["public_key"] for p in g2a]

    def test_no_peer_gets_both_keys(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(20)]
        group_a, group_b = split_distribution_targets(peers, "author")
        keys_a = {p["public_key"] for p in group_a}
        keys_b = {p["public_key"] for p in group_b}
        assert keys_a.isdisjoint(keys_b)

    def test_split_handles_single_peer(self):
        peers = [{"public_key": "only_peer"}]
        group_a, group_b = split_distribution_targets(peers, "author")
        # With one peer, one group gets the peer, other is empty
        # But the function ensures both are non-empty... with 1 peer
        # it can only be in one group
        assert len(group_a) + len(group_b) == 1


class TestDecoySelection:
    def test_select_decoy_excludes_real_holder(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(5)]
        decoy = select_decoy(peers, "peer_0", "content_hash")
        assert decoy != "peer_0"

    def test_select_decoy_is_deterministic(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(5)]
        d1 = select_decoy(peers, "peer_0", "hash_1")
        d2 = select_decoy(peers, "peer_0", "hash_1")
        assert d1 == d2

    def test_select_decoy_returns_none_when_no_candidates(self):
        peers = [{"public_key": "only_peer"}]
        decoy = select_decoy(peers, "only_peer", "content_hash")
        assert decoy is None

    def test_different_content_may_select_different_decoy(self):
        peers = [{"public_key": f"peer_{i}"} for i in range(10)]
        d1 = select_decoy(peers, "peer_0", "hash_aaa")
        d2 = select_decoy(peers, "peer_0", "hash_zzz")
        # Not guaranteed to differ, but with 10 candidates and different hashes, likely
        # Just verify both are valid
        assert d1 in [p["public_key"] for p in peers]
        assert d2 in [p["public_key"] for p in peers]


class TestMachineResistance:
    """
    Tests that validate the core anti-machine property:
    machines can find the hot zone but cannot resolve the challenge.
    """

    def test_two_witnesses_converge_on_hot_zone(self, sample_triad):
        """Both witnesses together produce a deterministic locator."""
        locator = combine_witnesses(sample_triad.witness_a, sample_triad.witness_b)
        assert locator  # hot zone identified

    def test_challenge_is_ambiguous_without_context(self, sample_triad):
        """Both candidates look equally valid without ring context."""
        cand_a = sample_triad.challenge.candidate_a
        cand_b = sample_triad.challenge.candidate_b
        # Both are 16-char hex strings - structurally identical
        assert len(cand_a) == len(cand_b) == 16
        # Both are hex
        assert all(c in "0123456789abcdef" for c in cand_a)
        assert all(c in "0123456789abcdef" for c in cand_b)
        # No structural difference a machine can exploit

    def test_ring_member_can_resolve(self, sample_keys, sample_triad):
        """A ring member who knows the holder's key can resolve the challenge."""
        # Ring member knows the holder's public key
        real_fragment = derive_candidate_fragment(sample_keys["holder"])
        # They check which candidate matches
        if sample_triad.challenge.candidate_a == real_fragment:
            chosen = sample_triad.challenge.candidate_a
        else:
            chosen = sample_triad.challenge.candidate_b
        # Verification succeeds
        assert verify_resolution(sample_triad, chosen, sample_keys["content_hash"])

    def test_outsider_has_50_50_chance(self, sample_keys, sample_triad):
        """
        An outsider without ring context must guess - 50% chance.
        This is the key anti-machine property: no algorithm can do better
        than random without human-interpretable context.
        """
        # Try both candidates
        result_a = verify_resolution(
            sample_triad, sample_triad.challenge.candidate_a, sample_keys["content_hash"]
        )
        result_b = verify_resolution(
            sample_triad, sample_triad.challenge.candidate_b, sample_keys["content_hash"]
        )
        # Exactly one succeeds
        assert result_a != result_b
        assert result_a or result_b
