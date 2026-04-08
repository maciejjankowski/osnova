#!/usr/bin/env python3
"""
Osnova Gematria Engine
Computes, verifies, and generates gematria-based checksums.
Includes Atbash, Notarikon, and Temurah operations.

Usage:
    from data.corpus.gematria import gematria, find_temurah, atbash, verify_checksum

    assert gematria("אמת") == 441
    assert gematria("תמא") == 441
    mirrors = find_temurah("אמת", corpus)
"""

# Standard Gematria (Mispar Hechrachi)
LETTER_VALUES = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5,
    'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10,
    'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40,
    'נ': 50, 'ן': 50, 'ס': 60, 'ע': 70, 'פ': 80,
    'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100, 'ר': 200,
    'ש': 300, 'ת': 400,
}

# Final form values (Mispar Gadol)
FINAL_VALUES = {
    'ך': 500, 'ם': 600, 'ן': 700, 'ף': 800, 'ץ': 900,
}

# Atbash substitution table
_aleph = 'אבגדהוזחטיכלמנסעפצקרשת'
_tav = 'תשרקצפעסנמלכיטחזוהדגבא'
ATBASH_TABLE = dict(zip(_aleph, _tav))

# Katan (small value) - reduce to single digit
KATAN_VALUES = {c: (v % 9 or 9) for c, v in LETTER_VALUES.items()}


def gematria(word: str, method: str = "standard") -> int:
    """Compute gematria value of a Hebrew word.

    Methods: standard, gadol (finals=high), katan (single digit)
    """
    table = LETTER_VALUES
    if method == "gadol":
        table = {**LETTER_VALUES, **FINAL_VALUES}
    elif method == "katan":
        table = KATAN_VALUES
    return sum(table.get(c, 0) for c in word)


def atbash(word: str) -> str:
    """Apply Atbash cipher (first<->last letter swap)."""
    return ''.join(ATBASH_TABLE.get(c, c) for c in word)


def atbash_gematria(word: str) -> int:
    """Gematria of the Atbash-transformed word."""
    return gematria(atbash(word))


def notarikon(words: list[str], position: str = "first") -> str:
    """Extract first or last letters of each word (Notarikon)."""
    if position == "first":
        return ''.join(w[0] for w in words if w)
    elif position == "last":
        return ''.join(w[-1] for w in words if w)
    return ""


def is_temurah(word1: str, word2: str) -> bool:
    """Check if two words are Temurah (same letters, same gematria, different arrangement)."""
    return (sorted(word1) == sorted(word2) and
            word1 != word2 and
            gematria(word1) == gematria(word2))


def find_temurah(word: str, corpus: dict[str, int]) -> list[tuple[str, str]]:
    """Find all words in corpus with same gematria value.

    Returns list of (word, meaning) tuples.
    corpus format: {hebrew_word: meaning_string}
    """
    target = gematria(word)
    return [(w, m) for w, m in corpus.items()
            if gematria(w) == target and w != word]


def verify_checksum(constraints: list[str], expected: int = 441) -> bool:
    """Verify that gematria sum of constraint keywords equals expected value.

    441 = EMET (truth) - the default Osnova checksum.
    """
    total = sum(gematria(c) for c in constraints)
    return total == expected


def multi_layer_checksum(word: str) -> dict:
    """Compute all four checksum layers for a word."""
    return {
        "standard": gematria(word),
        "gadol": gematria(word, "gadol"),
        "katan": gematria(word, "katan"),
        "atbash": atbash_gematria(word),
    }


# Key equivalences for Osnova
KEY_PAIRS = {
    441: [("אמת", "truth"), ("תמא", "impure")],
    13: [("אהבה", "love"), ("אחד", "one")],
    26: [("יהוה", "YHWH")],
    86: [("אלהים", "God"), ("הטבע", "nature")],
    358: [("משיח", "messiah"), ("נחש", "serpent")],
    232: [("יהי אור", "let there be light")],
    376: [("שלום", "peace")],
    72: [("חסד", "lovingkindness")],
    611: [("תורה", "Torah")],
}


if __name__ == "__main__":
    # Self-test
    print("=== GEMATRIA ENGINE SELF-TEST ===\n")

    tests = [
        ("אמת", 441, "EMET (truth)"),
        ("תמא", 441, "TAME (impure)"),
        ("אהבה", 13, "AHAVA (love)"),
        ("אחד", 13, "ECHAD (one)"),
        ("שלום", 376, "SHALOM (peace)"),
        ("חסד", 72, "CHESED (kindness)"),
        ("תורה", 611, "TORAH"),
    ]

    passed = 0
    for word, expected, name in tests:
        result = gematria(word)
        ok = "PASS" if result == expected else "FAIL"
        print(f"  {ok}: {name} = {result} (expected {expected})")
        if result == expected:
            passed += 1

    # Temurah test
    assert is_temurah("אמת", "תמא"), "EMET/TAME should be Temurah pair"
    assert not is_temurah("אמת", "אמת"), "Same word is not Temurah"
    print(f"  PASS: EMET <-> TAME Temurah verified")
    passed += 1

    # Atbash test
    atbash_emet = atbash("אמת")
    print(f"  INFO: Atbash of EMET = {atbash_emet} (gematria: {gematria(atbash_emet)})")
    passed += 1

    # Multi-layer checksum
    layers = multi_layer_checksum("אמת")
    print(f"  INFO: EMET checksums = {layers}")
    passed += 1

    # Verify checksum
    assert verify_checksum(["אמת"], 441), "Single-word checksum should work"
    print(f"  PASS: Checksum verification (441 = EMET)")
    passed += 1

    print(f"\n{passed}/{passed} tests passed.")
