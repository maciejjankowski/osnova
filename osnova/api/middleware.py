"""Signature verification middleware for Osnova API."""
from __future__ import annotations

import logging

from osnova.crypto.identity import verify_content
from osnova.schemas import ContentEntry

logger = logging.getLogger(__name__)


def verify_incoming_entries(entries: list[ContentEntry]) -> tuple[list[ContentEntry], list[str]]:
    """
    Verify signatures on a list of ContentEntry objects.

    Returns:
        (accepted, rejected_hashes) - valid entries and hashes of rejected ones.
    """
    accepted: list[ContentEntry] = []
    rejected: list[str] = []

    for entry in entries:
        if verify_content(entry):
            accepted.append(entry)
        else:
            logger.warning(
                "Rejected entry with invalid signature: hash=%s author=%s",
                entry.content_hash[:12],
                entry.author_key[:12],
            )
            rejected.append(entry.content_hash)

    return accepted, rejected
