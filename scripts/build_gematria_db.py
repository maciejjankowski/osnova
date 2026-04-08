#!/usr/bin/env python3
"""
Build gematria equivalence database from Torah corpus.
Finds all word pairs that share gematria values.

Run after fetch_torah.py has created torah_corpus.json.
Can also run with seed data only.

Output: data/corpus/gematria_equivalences.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.corpus.gematria import gematria, atbash, LETTER_VALUES

TANAKH_PATH = Path(__file__).parent.parent / "data/corpus/tanakh_corpus.json"
CORPUS_PATH = TANAKH_PATH if TANAKH_PATH.exists() else Path(__file__).parent.parent / "data/corpus/torah_corpus.json"
OUTPUT_PATH = Path(__file__).parent.parent / "data/corpus/gematria_equivalences.json"

# Standalone Hebrew words with known meanings (for when full corpus isn't available)
KNOWN_WORDS = {
    "אמת": "truth", "תמא": "impure", "אהבה": "love", "אחד": "one",
    "שלום": "peace", "חסד": "kindness", "תורה": "Torah", "אור": "light",
    "חשך": "darkness", "טוב": "good", "רע": "evil", "חיים": "life",
    "מות": "death", "שמים": "heavens", "ארץ": "earth", "אלהים": "God",
    "אדם": "human", "חוה": "Eve", "נחש": "serpent", "משיח": "messiah",
    "ישראל": "Israel", "יהוה": "YHWH", "אברהם": "Abraham", "שרה": "Sarah",
    "יצחק": "Isaac", "יעקב": "Jacob", "משה": "Moses", "דוד": "David",
    "ירושלים": "Jerusalem", "ציון": "Zion", "בראשית": "beginning",
    "עולם": "world/eternity", "נשמה": "soul", "רוח": "spirit",
    "לב": "heart", "דעת": "knowledge", "חכמה": "wisdom", "בינה": "understanding",
    "כבוד": "glory", "צדק": "righteousness", "משפט": "justice",
    "רחמים": "mercy", "גאולה": "redemption", "תשובה": "repentance",
    "קדוש": "holy", "ברית": "covenant", "עדן": "Eden",
    "מלך": "king", "כהן": "priest", "נביא": "prophet",
    "מלאך": "angel", "שטן": "satan/adversary",
    "אש": "fire", "מים": "water", "רוח": "wind/spirit",
    "עפר": "dust/earth",
}


def build_from_corpus():
    """Build equivalence DB from full Torah corpus."""
    if not CORPUS_PATH.exists():
        print(f"  Torah corpus not found at {CORPUS_PATH}")
        print("  Using known words only...")
        return build_from_known_words()

    with open(CORPUS_PATH) as f:
        data = json.load(f)

    word_meanings = {}
    word_by_value = defaultdict(set)

    for ref, verse in data.get("verses", {}).items():
        for word in verse.get("words", []):
            # Strip non-Hebrew chars
            clean = ''.join(c for c in word if c in LETTER_VALUES)
            if not clean or len(clean) < 2:
                continue
            val = gematria(clean)
            word_by_value[val].add(clean)
            if clean not in word_meanings:
                word_meanings[clean] = f"Torah:{ref}"

    return word_by_value, word_meanings


def build_from_known_words():
    """Build equivalence DB from known words."""
    word_by_value = defaultdict(set)
    for word in KNOWN_WORDS:
        val = gematria(word)
        word_by_value[val].add(word)
    return word_by_value, KNOWN_WORDS


def main():
    print("=== GEMATRIA EQUIVALENCE DATABASE BUILDER ===\n")

    word_by_value, word_meanings = build_from_corpus()

    # Filter to values with 2+ words (equivalences)
    equivalences = {}
    for val, words in sorted(word_by_value.items()):
        if len(words) >= 2:
            word_list = []
            for w in sorted(words):
                meaning = word_meanings.get(w, "")
                word_list.append({"word": w, "meaning": meaning, "gematria": val})
            equivalences[str(val)] = word_list

    # Also add atbash values for key words
    atbash_pairs = {}
    for word, meaning in KNOWN_WORDS.items():
        atbash_word = atbash(word)
        atbash_val = gematria(atbash_word)
        if atbash_val != gematria(word):
            atbash_pairs[word] = {
                "original": word,
                "original_gematria": gematria(word),
                "atbash": atbash_word,
                "atbash_gematria": atbash_val,
                "meaning": meaning,
            }

    output = {
        "meta": {
            "total_values": len(equivalences),
            "total_words": sum(len(v) for v in equivalences.values()),
            "source": "Torah corpus + known words",
        },
        "equivalences": equivalences,
        "atbash_pairs": atbash_pairs,
        "key_pairs": {
            "441": {"words": ["אמת", "תמא"], "meanings": ["truth", "impure"], "note": "OSNOVA primary checksum"},
            "13": {"words": ["אהבה", "אחד"], "meanings": ["love", "one"], "note": "Unity signal"},
            "26": {"words": ["יהוה"], "meanings": ["YHWH"], "note": "The Name - reference only"},
            "86": {"words": ["אלהים"], "meanings": ["God/nature"], "note": "Dual-meaning marker"},
            "358": {"words": ["משיח", "נחש"], "meanings": ["messiah", "serpent"], "note": "Redemption/danger share a value"},
        },
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Equivalence values: {len(equivalences)}")
    print(f"  Total word entries: {sum(len(v) for v in equivalences.values())}")
    print(f"  Atbash pairs: {len(atbash_pairs)}")
    print(f"  Saved to: {OUTPUT_PATH}")

    # Show some interesting pairs
    print("\n  Key equivalences:")
    for val_str, words in sorted(equivalences.items(), key=lambda x: -len(x[1]))[:10]:
        word_display = ', '.join(f"{w['word']}({w['meaning'][:15]})" for w in words)
        print(f"    {val_str}: {word_display}")


if __name__ == "__main__":
    main()
