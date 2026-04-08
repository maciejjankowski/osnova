"""Tests for osnova.crypto.identity module."""
import tempfile
from pathlib import Path

import pytest

from osnova.crypto.identity import (
    generate_keypair,
    get_identity,
    load_keypair,
    public_key_hex,
    save_keypair,
    sign_content,
    verify_content,
)
from osnova.schemas import ContentEntry, ContentType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entry(author_key: str, body: str = "hello osnova") -> ContentEntry:
    return ContentEntry(
        author_key=author_key,
        content_type=ContentType.POST,
        body=body,
        timestamp=1_700_000_000.0,  # fixed timestamp for determinism
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKeypairGeneration:
    def test_returns_signing_and_verify_key(self):
        signing_key, verify_key = generate_keypair()
        assert signing_key is not None
        assert verify_key is not None

    def test_verify_key_matches_signing_key(self):
        signing_key, verify_key = generate_keypair()
        assert signing_key.verify_key == verify_key

    def test_unique_keypairs(self):
        sk1, vk1 = generate_keypair()
        sk2, vk2 = generate_keypair()
        assert public_key_hex(vk1) != public_key_hex(vk2)

    def test_public_key_hex_is_64_chars(self):
        _, vk = generate_keypair()
        hex_str = public_key_hex(vk)
        assert len(hex_str) == 64
        assert all(c in "0123456789abcdef" for c in hex_str)


class TestSaveLoadRoundtrip:
    def test_roundtrip_restores_identical_key(self):
        signing_key, verify_key = generate_keypair()
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "identity.key"
            save_keypair(signing_key, key_path)
            loaded = load_keypair(key_path)
        assert public_key_hex(loaded.verify_key) == public_key_hex(verify_key)

    def test_saved_file_has_restricted_permissions(self):
        signing_key, _ = generate_keypair()
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "identity.key"
            save_keypair(signing_key, key_path)
            mode = oct(key_path.stat().st_mode)[-3:]
        assert mode == "600"

    def test_saved_file_is_hex_string(self):
        signing_key, _ = generate_keypair()
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "identity.key"
            save_keypair(signing_key, key_path)
            content = key_path.read_text().strip()
        assert len(content) == 64
        assert all(c in "0123456789abcdef" for c in content)

    def test_load_creates_parent_dirs(self):
        signing_key, _ = generate_keypair()
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "nested" / "dirs" / "identity.key"
            save_keypair(signing_key, key_path)
            assert key_path.exists()


class TestSignAndVerify:
    def test_sign_fills_signature_field(self):
        signing_key, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        assert entry.signature == ""
        signed = sign_content(signing_key, entry)
        assert signed.signature != ""

    def test_verify_valid_signature(self):
        signing_key, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        signed = sign_content(signing_key, entry)
        assert verify_content(signed) is True

    def test_original_entry_unchanged(self):
        signing_key, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        signed = sign_content(signing_key, entry)
        # original must be immutable / untouched
        assert entry.signature == ""
        assert signed is not entry

    def test_empty_signature_fails_verify(self):
        _, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        assert verify_content(entry) is False


class TestTamperDetection:
    def test_tampered_body_fails_verify(self):
        signing_key, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        signed = sign_content(signing_key, entry)
        tampered = signed.model_copy(update={"body": "tampered content"})
        assert verify_content(tampered) is False

    def test_tampered_author_key_fails_verify(self):
        signing_key, verify_key = generate_keypair()
        _, other_vk = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        signed = sign_content(signing_key, entry)
        tampered = signed.model_copy(update={"author_key": public_key_hex(other_vk)})
        assert verify_content(tampered) is False

    def test_tampered_signature_fails_verify(self):
        signing_key, verify_key = generate_keypair()
        entry = make_entry(public_key_hex(verify_key))
        signed = sign_content(signing_key, entry)
        bad_sig = "ab" * 32  # 64 hex chars, wrong bytes
        tampered = signed.model_copy(update={"signature": bad_sig})
        assert verify_content(tampered) is False

    def test_wrong_key_fails_verify(self):
        sk1, vk1 = generate_keypair()
        sk2, _ = generate_keypair()
        entry = make_entry(public_key_hex(vk1))
        # sign with sk2 but author_key is vk1
        signed_wrong = sign_content(sk2, entry)
        assert verify_content(signed_wrong) is False


class TestGetIdentity:
    def test_returns_identity_with_correct_key(self):
        signing_key, verify_key = generate_keypair()
        identity = get_identity(signing_key, "Alice")
        assert identity.public_key == public_key_hex(verify_key)

    def test_returns_identity_with_display_name(self):
        signing_key, _ = generate_keypair()
        identity = get_identity(signing_key, "Bob")
        assert identity.display_name == "Bob"

    def test_identity_created_at_is_recent(self):
        import time
        signing_key, _ = generate_keypair()
        before = time.time()
        identity = get_identity(signing_key, "Carol")
        after = time.time()
        assert before <= identity.created_at <= after
