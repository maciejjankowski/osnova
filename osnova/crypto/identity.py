"""Ed25519 identity and signing for the Osnova protocol."""
from __future__ import annotations

import time
from pathlib import Path

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey

from osnova.schemas import ContentEntry, Identity


def generate_keypair() -> tuple[SigningKey, VerifyKey]:
    """Generate a new Ed25519 keypair."""
    signing_key = SigningKey.generate()
    return signing_key, signing_key.verify_key


def public_key_hex(verify_key: VerifyKey) -> str:
    """Return hex-encoded public key string."""
    return verify_key.encode(encoder=HexEncoder).decode("ascii")


def save_keypair(signing_key: SigningKey, path: str | Path) -> None:
    """Save private signing key to file (hex-encoded, 0600 permissions)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hex_key = signing_key.encode(encoder=HexEncoder).decode("ascii")
    path.write_text(hex_key)
    path.chmod(0o600)


def load_keypair(path: str | Path) -> SigningKey:
    """Load signing key from hex-encoded file. Returns SigningKey (verify_key accessible via .verify_key)."""
    path = Path(path)
    hex_key = path.read_text().strip()
    return SigningKey(hex_key.encode("ascii"), encoder=HexEncoder)


def sign_content(signing_key: SigningKey, content_entry: ContentEntry) -> ContentEntry:
    """Sign a ContentEntry using its content_hash. Returns a new ContentEntry with signature set."""
    payload = content_entry.content_hash.encode("utf-8")
    signed = signing_key.sign(payload, encoder=HexEncoder)
    # signed.signature is the bare signature (HexEncoder returns bytes of hex)
    signature_hex = signed.signature.decode("ascii")
    return content_entry.model_copy(update={"signature": signature_hex})


def verify_content(content_entry: ContentEntry) -> bool:
    """Verify the signature on a ContentEntry. Returns True if valid, False otherwise."""
    if not content_entry.signature:
        return False
    try:
        verify_key = VerifyKey(content_entry.author_key.encode("ascii"), encoder=HexEncoder)
        payload = content_entry.content_hash.encode("utf-8")
        sig_bytes = bytes.fromhex(content_entry.signature)
        verify_key.verify(payload, sig_bytes)
        return True
    except Exception:
        return False


def get_identity(signing_key: SigningKey, display_name: str) -> Identity:
    """Create an Identity from a signing key and display name."""
    return Identity(
        public_key=public_key_hex(signing_key.verify_key),
        display_name=display_name,
        created_at=time.time(),
    )
