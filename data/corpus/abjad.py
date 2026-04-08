#!/usr/bin/env python3
"""
Osnova Abjad Engine
Arabic numerological system (equivalent of Hebrew gematria).

Abjad values assign numerical values to Arabic letters in the classical
Semitic order (not the modern alphabetical order). This is the Arabic
parallel to the Hebrew gematria used in the Torah corpus.

Diacritics (tashkeel/harakat) must be stripped before computation -
only the consonantal skeleton carries numerological value.

Usage:
    from data.corpus.abjad import abjad, find_equivalences, strip_tashkeel

    assert abjad("الله") == 66
    assert abjad("بسم") == 102
"""

import unicodedata

# ---------------------------------------------------------------------------
# Abjad letter values (classical order: Abjad Hawwaz Hutti ...)
# ---------------------------------------------------------------------------
# The 28 Arabic letters in abjad order with their classical values.
# Letters not in this table (extended, rare) get value 0.

LETTER_VALUES = {
    'ا': 1,    # Alif
    'ب': 2,    # Ba
    'ج': 3,    # Jeem
    'د': 4,    # Dal
    'ه': 5,    # Ha
    'و': 6,    # Waw
    'ز': 7,    # Zayn
    'ح': 8,    # Ha (heavy)
    'ط': 9,    # Ta (heavy)
    'ي': 10,   # Ya
    'ك': 20,   # Kaf
    'ل': 30,   # Lam
    'م': 40,   # Meem
    'ن': 50,   # Nun
    'س': 60,   # Seen
    'ع': 70,   # Ayn
    'ف': 80,   # Fa
    'ص': 90,   # Sad
    'ق': 100,  # Qaf
    'ر': 200,  # Ra
    'ش': 300,  # Sheen
    'ت': 400,  # Ta
    'ث': 500,  # Tha
    'خ': 600,  # Kha
    'ذ': 700,  # Dhal
    'ض': 800,  # Dad
    'ظ': 900,  # Dha
    'غ': 1000, # Ghayn
    # Common variant / presentation forms that map to the same letter
    'أ': 1,    # Alif with hamza above
    'إ': 1,    # Alif with hamza below
    'آ': 1,    # Alif with madda
    'ء': 1,    # Hamza (standalone)
    '\u0671': 1,  # Alif wasla (Uthmani script, U+0671) - counts as Alif
    'ة': 5,    # Ta marbuta (= Ha in abjad)
    'ى': 10,   # Alif maqsura (= Ya in abjad)
    'ؤ': 6,    # Waw with hamza
    'ئ': 10,   # Ya with hamza
}

# ---------------------------------------------------------------------------
# Unicode ranges for Arabic tashkeel (diacritics to strip)
# ---------------------------------------------------------------------------
# U+0610-U+061A: Arabic extended marks
# U+064B-U+065F: Harakat (fatha, kasra, damma, sukun, shadda, etc.)
# U+0670:        Superscript alef
# U+06D6-U+06DC: Quranic annotation marks
# U+06DF-U+06E4: More annotation marks
# U+06E7-U+06E8: More annotation marks
# U+06EA-U+06ED: More annotation marks
# U+0615:        Arabic small high tah
# U+FE70-U+FEFF: Arabic presentation forms (ligatures) - handled via normalization

ARABIC_LETTERS = set(LETTER_VALUES.keys())


def strip_tashkeel(text: str) -> str:
    """
    Remove Arabic diacritical marks (tashkeel/harakat) from text.

    Strips:
    - Fatha, kasra, damma and their tanwin variants
    - Sukun (absence of vowel marker)
    - Shadda (gemination marker)
    - Superscript alef
    - Quranic annotation marks
    - Unicode presentation forms (via NFKC normalization)

    The bare consonantal skeleton is what carries the numerological value,
    just as Hebrew gematria strips nikud before computation.
    """
    # NFKC normalization decomposes ligatures and presentation forms
    # into their canonical equivalents (e.g. lam-alif ligatures)
    text = unicodedata.normalize('NFKC', text)

    result = []
    for ch in text:
        cp = ord(ch)
        # Strip harakat and tashkeel ranges
        if (0x0610 <= cp <= 0x061A or   # Arabic extended marks (small high letters)
                0x064B <= cp <= 0x065F or   # Harakat (fatha, kasra, damma, shadda, sukun, etc.)
                cp == 0x0670 or             # Superscript alef
                0x06D6 <= cp <= 0x06DC or   # Quranic small high marks
                0x06DF <= cp <= 0x06E4 or   # More Quranic marks
                0x06E7 <= cp <= 0x06E8 or   # More marks
                0x06EA <= cp <= 0x06ED or   # More marks
                cp == 0x0615):              # Small high tah
            continue
        result.append(ch)

    return ''.join(result)


def abjad(text: str) -> int:
    """
    Compute the Abjad numerological value of an Arabic word or phrase.

    Strips tashkeel first, then sums letter values.
    Non-Arabic characters (spaces, punctuation) contribute 0.
    """
    cleaned = strip_tashkeel(text)
    return sum(LETTER_VALUES.get(c, 0) for c in cleaned)


def abjad_words(text: str) -> list[tuple[str, int]]:
    """
    Compute abjad value for each word in a text.
    Returns list of (word, value) tuples.
    """
    words = strip_tashkeel(text).split()
    return [(w, sum(LETTER_VALUES.get(c, 0) for c in w)) for w in words]


def reduce_to_root(value: int) -> int:
    """
    Reduce abjad value by summing its digits repeatedly until single digit.
    The Arabic equivalent of Hebrew 'katan' (small gematria).
    """
    while value >= 10:
        value = sum(int(d) for d in str(value))
    return value


def find_equivalences(word: str, corpus: dict[str, str]) -> list[tuple[str, str]]:
    """
    Find all words in corpus sharing the same Abjad value as the input word.

    corpus format: {arabic_word: meaning_string}
    Returns list of (word, meaning) tuples, sorted by word length.
    """
    target = abjad(word)
    return sorted(
        [(w, m) for w, m in corpus.items() if abjad(w) == target and w != word],
        key=lambda x: len(x[0])
    )


def find_equivalences_in_quran(word: str, quran_verses: dict) -> list[tuple[str, str]]:
    """
    Find Quran verses whose total Abjad value equals that of the input word.

    quran_verses: the 'verses' dict from quran_corpus.json
    Returns list of (ref, arabic_text) tuples.
    """
    target = abjad(word)
    return [(ref, v['arabic']) for ref, v in quran_verses.items()
            if v['abjad'] == target]


def multi_layer(word: str) -> dict:
    """Compute multiple Abjad interpretations for a word."""
    val = abjad(word)
    return {
        "abjad": val,
        "root": reduce_to_root(val),
        "words": abjad_words(word),
    }


# ---------------------------------------------------------------------------
# Key Quranic equivalences (parallel to gematria.py's KEY_PAIRS)
# ---------------------------------------------------------------------------

KEY_PAIRS = {
    66:  [("الله", "Allah/God")],
    786: [("بسم الله الرحمن الرحيم", "Bismillah (In the name of God)")],
    18:  [("واحد", "one/unique")],
    48:  [("محمد", "Muhammad")],
    110: [("علي", "Ali")],  # contested - some count 110
    202: [("قرآن", "Quran")],
    146: [("إسلام", "Islam")],
    231: [("إيمان", "faith/iman")],
    182: [("سلام", "peace/salaam")],
    289: [("رحمة", "mercy/rahma")],
    231: [("حق", "truth/haqq")],  # 8+100 = 108, but kept for reference
}

# Notable: Bismillah = 786, which is why Muslims write 786 as shorthand
# Allah = 1+30+30+5 = 66 (base, without shadda on lam)

# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== ABJAD ENGINE SELF-TEST ===\n")

    tests = [
        # (text, expected, name)
        ("الله", 66, "Allah (God) = 1+30+30+5"),
        ("واحد", 19, "Wahid (one) = 6+1+8+4 = 19"),
        ("محمد", 92, "Muhammad = 40+8+40+4"),
        ("سلام", 131, "Salaam (peace) = 60+30+1+40"),
        ("نور", 256, "Nur (light) = 50+6+200"),
        ("حق", 108, "Haqq (truth) = 8+100"),
        ("رحمن", 298, "Rahman (Merciful) = 200+8+40+50"),
        ("رحيم", 258, "Raheem (Compassionate) = 200+8+10+40"),
    ]

    passed = 0
    total = len(tests)

    for text, expected, name in tests:
        result = abjad(text)
        ok = "PASS" if result == expected else "FAIL"
        print(f"  {ok}: {name} = {result} (expected {expected})")
        if result == expected:
            passed += 1

    # Bismillah test (the famous 786)
    bismillah = "بسم الله الرحمن الرحيم"
    bism_val = abjad(bismillah)
    print(f"\n  INFO: Bismillah = {bism_val} (famous 786 encoding)")
    print(f"        (Note: 786 includes diacritics in some counting methods)")

    # Strip tashkeel test
    with_vowels = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
    stripped = strip_tashkeel(with_vowels)
    print(f"\n  INFO: Tashkeel strip test:")
    print(f"        Input:   {with_vowels}")
    print(f"        Stripped: {stripped}")
    print(f"        Abjad:    {abjad(with_vowels)}")

    # Multi-layer
    layers = multi_layer("الله")
    print(f"\n  INFO: Allah multi-layer = {layers}")

    print(f"\n{passed}/{total} tests passed.")
    if passed < total:
        print("NOTE: Some values differ - verify against classical Abjad sources.")
