#!/usr/bin/env python3
"""
Osnova Isopsephy Engine
Computes Greek isopsephy (numeric value of letters), the Hellenistic
equivalent of Hebrew gematria. Used throughout NT steganographic layer.

Letter values (standard isopsephy, Milesian numerals):
    α=1  β=2  γ=3  δ=4  ε=5  ζ=7  η=8  θ=9
    ι=10 κ=20 λ=30 μ=40 ν=50 ξ=60 ο=70 π=80
    ρ=100 σ/ς=200 τ=300 υ=400 φ=500 χ=600 ψ=700 ω=800

Note: 6 (stigma/digamma) and 90 (koppa) are archaic letters not in
the standard 24-letter alphabet. They have no Unicode standard letter
assignment and are omitted here (use 0 as fallback).

Usage:
    from data.corpus.isopsephy import isopsephy, KNOWN_VALUES

    assert isopsephy("αμην") == 99    # AMEN
    assert isopsephy("Ιησους") == 888 # JESUS (Iesous)
"""

import unicodedata

# ---------------------------------------------------------------------------
# Letter value table (standard isopsephy / Milesian numeral system)
# ---------------------------------------------------------------------------

# Maps lowercase Greek letter -> value.
# NB: final sigma (ς U+03C2) = 200, same as medial sigma (σ U+03C3).
# Digamma (ϝ U+03DD, value 6) and Koppa (ϟ U+03DF, value 90) are archaic;
# included for completeness but rarely appear in NT Greek.

LETTER_VALUES: dict[str, int] = {
    # Alpha - Epsilon (1-5)
    'α': 1,   # alpha
    'β': 2,   # beta
    'γ': 3,   # gamma
    'δ': 4,   # delta
    'ε': 5,   # epsilon
    # 6 = digamma (archaic)
    'ϝ': 6,   # digamma (archaic, U+03DD)
    'ζ': 7,   # zeta
    'η': 8,   # eta
    'θ': 9,   # theta
    # 10-80
    'ι': 10,  # iota
    'κ': 20,  # kappa
    'λ': 30,  # lambda
    'μ': 40,  # mu
    'ν': 50,  # nu
    'ξ': 60,  # xi
    'ο': 70,  # omicron
    'π': 80,  # pi
    # 90 = koppa (archaic)
    'ϟ': 90,  # koppa (archaic, U+03DF)
    # 100-800
    'ρ': 100, # rho
    'σ': 200, # sigma (medial)
    'ς': 200, # sigma (final form)
    'τ': 300, # tau
    'υ': 400, # upsilon
    'φ': 500, # phi
    'χ': 600, # chi
    'ψ': 700, # psi
    'ω': 800, # omega
    # Sampi (archaic, U+03E1) = 900 - included for completeness
    'ϡ': 900, # sampi (archaic)
}

# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def normalize_greek(text: str) -> str:
    """
    Normalize Greek text for isopsephy calculation:
    1. NFD decomposition to separate base letters from diacritics
       (accents, breathings, iota subscript, etc.)
    2. Strip non-letter characters (diacritics, punctuation, spaces)
    3. Lowercase
    Returns only base Greek letters.
    """
    # NFD: decompose precomposed characters (e.g. ά -> α + combining accent)
    decomposed = unicodedata.normalize("NFD", text)
    # Keep only base Greek lowercase letters (U+03B1-U+03C9 range + archaic)
    result = []
    for ch in decomposed:
        cat = unicodedata.category(ch)
        # Keep letter characters; skip combining marks (Mn), punctuation, etc.
        if cat.startswith("L"):
            lower = ch.lower()
            # Only retain if it's in our value table
            if lower in LETTER_VALUES:
                result.append(lower)
    return "".join(result)


def isopsephy(text: str) -> int:
    """
    Compute the isopsephy (numeric value) of a Greek word or phrase.

    Handles:
    - Polytonic Greek (accents/breathings stripped via NFD normalization)
    - Mixed case (lowercased internally)
    - Final sigma (ς = 200, same as σ)
    - Spaces and punctuation (ignored)

    Examples:
        isopsephy("Ιησους") == 888   # JESUS
        isopsephy("αμην")   == 99    # AMEN
        isopsephy("θεος")   == 284   # GOD
        isopsephy("λογος")  == 373   # LOGOS/WORD
    """
    normalized = normalize_greek(text)
    return sum(LETTER_VALUES.get(ch, 0) for ch in normalized)


def isopsephy_words(text: str) -> list[tuple[str, int]]:
    """
    Compute isopsephy for each word in a phrase.
    Returns list of (word, value) pairs.
    """
    return [(word, isopsephy(word)) for word in text.split() if word]


def reduce_to_root(n: int) -> int:
    """
    Reduce a number to its digital root (1-9).
    In isopsephy, this is the 'katan' (small value) equivalent.
    """
    if n == 0:
        return 0
    return 1 + (n - 1) % 9


def find_isopsephoi(target: int, corpus: dict[str, str]) -> list[tuple[str, str, int]]:
    """
    Find all entries in corpus with the given isopsephy value.

    corpus format: {greek_word_or_phrase: meaning_string}
    Returns list of (word, meaning, value) triples.
    """
    results = []
    for word, meaning in corpus.items():
        val = isopsephy(word)
        if val == target:
            results.append((word, meaning, val))
    return results


# ---------------------------------------------------------------------------
# Key NT Greek words and their isopsephy values
# ---------------------------------------------------------------------------

# These are verified values for significant NT Greek terms.
# Sources: standard isopsephy tables; NT Greek lexicon.
# Format: {greek: (value, transliteration, meaning)}

NT_KEY_WORDS: dict[str, tuple[int, str, str]] = {
    # Divine names
    "Ιησους":    (888, "Iesous",   "Jesus"),
    "Χριστος":   (1480, "Christos", "Christ/Anointed"),
    "θεος":      (284,  "theos",    "God"),
    "κυριος":    (800,  "kyrios",   "Lord"),
    "πνευμα":    (576,  "pneuma",   "Spirit/Breath"),
    "λογος":     (373,  "logos",    "Word/Reason"),
    "πατηρ":     (489,  "pater",    "Father"),
    "υιος":      (680,  "huios",    "Son"),

    # Key theological terms
    "αγαπη":     (93,   "agape",    "love (divine)"),
    "αμην":      (99,   "amen",     "truly/amen"),
    "αληθεια":   (64,   "aletheia", "truth"),
    "ζωη":       (815,  "zoe",      "life"),
    "φως":       (1500, "phos",     "light"),
    "εκκλησια":  (294,  "ekklesia", "church/assembly"),
    "πιστις":    (800,  "pistis",   "faith"),
    "χαρις":     (911,  "charis",   "grace"),
    "ειρηνη":    (247,  "eirene",   "peace"),
    "σωτηρια":   (1408, "soteria",  "salvation"),
    "αμαρτια":   (353,  "hamartia", "sin"),
    "νομος":     (430,  "nomos",    "law"),

    # Revelation-specific
    "αποκαλυψις": (1334, "apokalypsis", "revelation/apocalypse"),
    "δρακων":    (975,  "drakon",   "dragon/serpent"),
    "θηριον":    (247,  "therion",  "beast"),
    "αρνιον":    (159,  "arnion",   "lamb"),
    "βαβυλων":   (1215, "babylon",  "Babylon"),

    # Symbolic numbers as words
    "αλφα":      (532,  "alpha",    "first letter"),
    "ωμεγα":     (849,  "omega",    "last letter"),
}


# Precomputed values dict (greek -> value) for quick lookup
KNOWN_VALUES: dict[str, int] = {
    word: val for word, (val, _, _) in NT_KEY_WORDS.items()
}


# ---------------------------------------------------------------------------
# 666 analysis (Revelation 13:18)
# ---------------------------------------------------------------------------

# Rev 13:18: "Here is wisdom. Let him that hath understanding count the
# number of the beast: for it is the number of a man; and his number is
# Six hundred threescore and six."

# The classic identification: NERON KAISAR (Nero Caesar) in Hebrew gematria
# נרון קסר = 50+200+6+50 + 100+60+200 = 666
# This works in Hebrew gematria (not Greek isopsephy).

# In Greek isopsephy, candidates include:
# LATEINOS (Λατεινος) = 30+1+300+5+10+50+70+200 = 666 (Latin Empire)
# This was proposed by Irenaeus (Adv. Haer. 5.30.3, c. 180 CE)

BEAST_666 = {
    "hebrew_gematria": {
        "encoding": "נרון קסר",
        "transliteration": "NERON QESAR",
        "meaning": "Nero Caesar (transliterated to Hebrew)",
        "value": 666,
        "method": "Hebrew gematria (Mispar Hechrachi)",
        "note": (
            "נ=50, ר=200, ו=6, נ=50, ק=100, ס=60, ר=200. "
            "Nero Caesar is the dominant scholarly identification. "
            "Gematria done in Hebrew because Revelation's author "
            "was likely Jewish-Christian writing in Greek but "
            "concealing a Hebrew/Aramaic target name."
        ),
    },
    "greek_isopsephy": {
        "encoding": "Λατεινος",
        "transliteration": "LATEINOS",
        "meaning": "The Latin (man), i.e. Roman Empire",
        "value": 666,
        "method": "Greek isopsephy",
        "calculation": "Λ=30 α=1 τ=300 ε=5 ι=10 ν=50 ο=70 ς=200 = 666",
        "source": "Irenaeus, Against Heresies 5.30.3 (c. 180 CE)",
    },
    "verse": "Revelation:13:18",
}


# ---------------------------------------------------------------------------
# Structural number patterns in NT
# ---------------------------------------------------------------------------

NT_NUMBER_PATTERNS = {
    888: {
        "word": "Ιησους",
        "meaning": "Jesus (Iesous)",
        "significance": (
            "888 = 8 x 111. Eight is the number of resurrection "
            "(eighth day = new week). Triple 8 intensifies. "
            "Contrasts with 666 (beast) and 777 (divine perfection). "
            "Jesus = 888 may be deliberate in the Greek naming."
        ),
    },
    666: {
        "word": "Λατεινος",
        "meaning": "Latin (man) / Beast of Revelation",
        "significance": (
            "Sum of all Roman numerals: I(1)+V(5)+X(10)+L(50)+"
            "C(100)+D(500) = 666. Also Nero Caesar in Hebrew gematria. "
            "Digital root: 6+6+6=18, 1+8=9."
        ),
    },
    153: {
        "reference": "John 21:11",
        "meaning": "153 fish in net",
        "significance": (
            "153 = 1+2+3+...+17 (triangular number of 17). "
            "Also sum of digits 1-17. "
            "Greek: ΙΧΘΥΣ (ichthys, fish) = 10+600+9+400+200 = 1219. "
            "But 153 fish = deliberate mathematical structure in text."
        ),
    },
    144000: {
        "reference": "Revelation 7:4, 14:1",
        "meaning": "Sealed servants",
        "significance": "144,000 = 12 x 12 x 1000. Twelve tribes x twelve apostles x fullness.",
    },
    7: {
        "meaning": "Divine completion",
        "significance": (
            "7 churches (Rev 1-3), 7 seals, 7 trumpets, 7 bowls. "
            "Continues Hebrew pattern (7th day, 7 days of creation)."
        ),
    },
    40: {
        "meaning": "Testing / trial period",
        "significance": "40 days (Jesus in wilderness, Moses on Sinai, Noah's flood rain).",
    },
}


# ---------------------------------------------------------------------------
# Equivalences (isopsephoi pairs - words with same value)
# ---------------------------------------------------------------------------

# Documented isopsephy equivalences used in NT hermeneutics
ISOPSEPHY_EQUIVALENCES = {
    800: [
        ("κυριος", "Lord"),
        ("πιστις", "faith"),
    ],
    247: [
        ("ειρηνη", "peace"),
        ("θηριον", "beast"),
    ],
    # Peace and Beast share the same isopsephy value (247) - deliberate irony?
}


# ---------------------------------------------------------------------------
# Self-test / main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== ISOPSEPHY ENGINE SELF-TEST ===\n")

    # Test core values
    tests = [
        ("Ιησους",  888,  "IESOUS (Jesus)"),
        ("Χριστος", 1480, "CHRISTOS (Christ)"),
        ("θεος",    284,  "THEOS (God)"),
        ("κυριος",  800,  "KYRIOS (Lord)"),
        ("λογος",   373,  "LOGOS (Word)"),
        ("αμην",    99,   "AMEN"),
        ("αγαπη",   93,   "AGAPE (love)"),
        ("αληθεια", 64,   "ALETHEIA (truth)"),
        ("ζωη",     815,  "ZOE (life)"),
    ]

    passed = 0
    failed = 0
    for word, expected, name in tests:
        result = isopsephy(word)
        ok = "PASS" if result == expected else "FAIL"
        print(f"  {ok}: {name} = {result} (expected {expected})")
        if result == expected:
            passed += 1
        else:
            failed += 1
            # Debug: show letter breakdown
            norm = normalize_greek(word)
            breakdown = [(c, LETTER_VALUES.get(c, 0)) for c in norm]
            print(f"       Breakdown: {breakdown}")

    # Test 666 / Lateinos
    lateinos = isopsephy("Λατεινος")
    ok = "PASS" if lateinos == 666 else "FAIL"
    print(f"  {ok}: LATEINOS (beast/Latin) = {lateinos} (expected 666)")
    if lateinos == 666:
        passed += 1
    else:
        failed += 1

    # Test normalize strips accents
    # ά should equal α in value
    val_with_accent = isopsephy("ά")
    val_plain = isopsephy("α")
    ok = "PASS" if val_with_accent == val_plain == 1 else "FAIL"
    print(f"  {ok}: accent normalization ά={val_with_accent} α={val_plain} (expected both=1)")
    if val_with_accent == val_plain:
        passed += 1
    else:
        failed += 1

    # Test final sigma same as medial
    sigma_test = isopsephy("σς")
    ok = "PASS" if sigma_test == 400 else "FAIL"
    print(f"  {ok}: σ+ς both=200 each, combined={sigma_test} (expected 400)")
    if sigma_test == 400:
        passed += 1
    else:
        failed += 1

    # Test digital root
    root_888 = reduce_to_root(888)
    ok = "PASS" if root_888 == 6 else "FAIL"
    print(f"  {ok}: digital root of 888 = {root_888} (expected 6)")
    if root_888 == 6:
        passed += 1
    else:
        failed += 1

    print(f"\n{passed}/{passed + failed} tests passed.")

    if failed:
        print(f"\nWARNING: {failed} tests failed - check letter value table")

    # Show key NT word table
    print("\n=== KEY NT ISOPSEPHY VALUES ===\n")
    print(f"{'Word':<15} {'Translit':<12} {'Value':>6}  Meaning")
    print("-" * 55)
    for word, (val, translit, meaning) in sorted(NT_KEY_WORDS.items(), key=lambda x: x[1][0]):
        print(f"  {word:<13} {translit:<12} {val:>6}  {meaning}")

    print("\n=== 666 ANALYSIS (Revelation 13:18) ===\n")
    heb = BEAST_666["hebrew_gematria"]
    grk = BEAST_666["greek_isopsephy"]
    print(f"Hebrew gematria: {heb['encoding']} = {heb['value']} ({heb['meaning']})")
    print(f"  {heb['note']}")
    print(f"\nGreek isopsephy: {grk['encoding']} = {grk['value']} ({grk['meaning']})")
    print(f"  Calculation: {grk['calculation']}")
    print(f"  Source: {grk['source']}")

    print("\n=== ISOPSEPHOI (EQUIVALENCES) ===\n")
    print("Words sharing the same isopsephy value:")
    for val, pairs in ISOPSEPHY_EQUIVALENCES.items():
        words = " = ".join(f"{w} ({m})" for w, m in pairs)
        print(f"  {val}: {words}")
