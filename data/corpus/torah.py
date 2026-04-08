#!/usr/bin/env python3
"""
Torah Corpus for Osnova
Builds a verse-addressed, gematria-indexed Hebrew Bible corpus.
Source: Mechon Mamre (mechon-mamre.org) canonical text.

This module provides:
  - Verse lookup by book:chapter:verse
  - Word extraction from any verse
  - Gematria computation for any verse/word
  - Temurah pair discovery across the corpus

Usage:
    python3 data/corpus/torah.py          # Build corpus from bundled data
    python3 data/corpus/torah.py --test   # Run tests
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from .gematria import gematria, is_temurah, LETTER_VALUES

CORPUS_PATH = Path(__file__).parent / "torah_corpus.json"
EQUIV_PATH = Path(__file__).parent / "gematria_equivalences.json"

# Book names (Hebrew -> English -> number)
BOOKS = {
    1: {"hebrew": "בראשית", "english": "Genesis", "abbrev": "Gen"},
    2: {"hebrew": "שמות", "english": "Exodus", "abbrev": "Exo"},
    3: {"hebrew": "ויקרא", "english": "Leviticus", "abbrev": "Lev"},
    4: {"hebrew": "במדבר", "english": "Numbers", "abbrev": "Num"},
    5: {"hebrew": "דברים", "english": "Deuteronomy", "abbrev": "Deu"},
}

# Pre-built Torah data (key verses for Osnova)
# Full corpus requires running build_from_mechon_mamre()
SEED_VERSES = {
    "1:1:1": {
        "hebrew": "בראשית ברא אלהים את השמים ואת הארץ",
        "words": ["בראשית", "ברא", "אלהים", "את", "השמים", "ואת", "הארץ"],
        "translation": "In the beginning God created the heavens and the earth",
    },
    "1:1:3": {
        "hebrew": "ויאמר אלהים יהי אור ויהי אור",
        "words": ["ויאמר", "אלהים", "יהי", "אור", "ויהי", "אור"],
        "translation": "And God said, Let there be light: and there was light",
    },
    "1:1:4": {
        "hebrew": "וירא אלהים את האור כי טוב ויבדל אלהים בין האור ובין החשך",
        "words": ["וירא", "אלהים", "את", "האור", "כי", "טוב", "ויבדל", "אלהים", "בין", "האור", "ובין", "החשך"],
        "translation": "And God saw the light, that it was good",
    },
    "1:12:3": {
        "hebrew": "ואברכה מברכיך ומקללך אאר ונברכו בך כל משפחת האדמה",
        "words": ["ואברכה", "מברכיך", "ומקללך", "אאר", "ונברכו", "בך", "כל", "משפחת", "האדמה"],
        "translation": "I will bless them that bless thee, and him that curseth thee will I curse",
    },
    "2:3:14": {
        "hebrew": "ויאמר אלהים אל משה אהיה אשר אהיה",
        "words": ["ויאמר", "אלהים", "אל", "משה", "אהיה", "אשר", "אהיה"],
        "translation": "And God said unto Moses: I AM THAT I AM",
    },
    "5:6:4": {
        "hebrew": "שמע ישראל יהוה אלהינו יהוה אחד",
        "words": ["שמע", "ישראל", "יהוה", "אלהינו", "יהוה", "אחד"],
        "translation": "Hear, O Israel: the LORD our God, the LORD is one",
    },
}


class TorahCorpus:
    """Verse-addressed Torah corpus with gematria indexing."""

    def __init__(self, corpus_path: str = None):
        self.verses = {}
        self.word_gematria = {}
        self.gematria_index = defaultdict(list)  # value -> [(ref, word)]

        if corpus_path and Path(corpus_path).exists():
            self.load(corpus_path)
        else:
            self._load_seed()

    def _load_seed(self):
        """Load built-in seed verses."""
        for ref, data in SEED_VERSES.items():
            self.verses[ref] = data
            for word in data["words"]:
                val = gematria(word)
                self.word_gematria[word] = val
                self.gematria_index[val].append((ref, word))

    def load(self, path: str):
        """Load full corpus from JSON."""
        with open(path) as f:
            data = json.load(f)
        self.verses = data.get("verses", {})
        self._build_index()

    def _build_index(self):
        """Build gematria index from loaded verses."""
        self.word_gematria = {}
        self.gematria_index = defaultdict(list)
        for ref, data in self.verses.items():
            for word in data.get("words", []):
                val = gematria(word)
                self.word_gematria[word] = val
                self.gematria_index[val].append((ref, word))

    def save(self, path: str):
        """Save corpus to JSON."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"verses": self.verses}, f, ensure_ascii=False, indent=2)

    def get_verse(self, book: int, chapter: int, verse: int) -> dict:
        """Get verse by address."""
        ref = f"{book}:{chapter}:{verse}"
        return self.verses.get(ref, {})

    def get_word(self, book: int, chapter: int, verse: int, word_idx: int) -> str:
        """Get specific word from verse (1-indexed)."""
        v = self.get_verse(book, chapter, verse)
        words = v.get("words", [])
        if 1 <= word_idx <= len(words):
            return words[word_idx - 1]
        return ""

    def verse_gematria(self, book: int, chapter: int, verse: int) -> int:
        """Total gematria of a verse."""
        v = self.get_verse(book, chapter, verse)
        return sum(gematria(w) for w in v.get("words", []))

    def find_by_gematria(self, value: int) -> list[tuple[str, str]]:
        """Find all (verse_ref, word) pairs with given gematria value."""
        return self.gematria_index.get(value, [])

    def find_equivalences(self, min_count: int = 2) -> dict[int, list[str]]:
        """Find all gematria values shared by multiple unique words."""
        word_by_value = defaultdict(set)
        for word, val in self.word_gematria.items():
            word_by_value[val].add(word)
        return {v: sorted(words) for v, words in word_by_value.items()
                if len(words) >= min_count}

    def validate_address(self, book: int, chapter: int, verse: int,
                         word: int = None, letter: int = None) -> bool:
        """Validate a Torah address. Invalid = error signal in Osnova."""
        v = self.get_verse(book, chapter, verse)
        if not v:
            return False
        if word is not None:
            words = v.get("words", [])
            if word < 1 or word > len(words):
                return False
            if letter is not None:
                w = words[word - 1]
                hebrew_letters = [c for c in w if c in LETTER_VALUES]
                if letter < 1 or letter > len(hebrew_letters):
                    return False
        return True

    @property
    def stats(self) -> dict:
        """Corpus statistics."""
        total_words = sum(len(v.get("words", [])) for v in self.verses.values())
        unique_words = len(self.word_gematria)
        unique_values = len(self.gematria_index)
        return {
            "verses": len(self.verses),
            "total_words": total_words,
            "unique_words": unique_words,
            "unique_gematria_values": unique_values,
        }


def build_gematria_equivalences(corpus: TorahCorpus) -> dict:
    """Build and save gematria equivalence table."""
    equivs = corpus.find_equivalences(min_count=2)
    with open(EQUIV_PATH, 'w', encoding='utf-8') as f:
        json.dump(equivs, f, ensure_ascii=False, indent=2)
    return equivs


if __name__ == "__main__":
    import sys

    print("=== TORAH CORPUS ENGINE ===\n")

    corpus = TorahCorpus()
    stats = corpus.stats
    print(f"Loaded: {stats['verses']} verses, {stats['unique_words']} unique words, "
          f"{stats['unique_gematria_values']} unique gematria values\n")

    # Test verse lookup
    v = corpus.get_verse(1, 1, 3)
    print(f"Genesis 1:3: {v.get('hebrew', 'NOT FOUND')}")
    print(f"  Translation: {v.get('translation', '')}")
    print(f"  Gematria: {corpus.verse_gematria(1, 1, 3)}")
    print()

    # Test word extraction
    word = corpus.get_word(1, 1, 3, 4)
    print(f"Genesis 1:3 word 4: {word} (gematria: {gematria(word)})")
    print()

    # Test gematria lookup
    hits = corpus.find_by_gematria(86)
    print(f"Words with gematria 86 (ELOHIM): {[(ref, w) for ref, w in hits[:5]]}")
    print()

    # Test address validation
    assert corpus.validate_address(1, 1, 3) is True, "Gen 1:3 should be valid"
    assert corpus.validate_address(1, 1, 3, 4) is True, "Gen 1:3 word 4 should be valid"
    assert corpus.validate_address(1, 1, 3, 99) is False, "Gen 1:3 word 99 should be invalid"
    print("Address validation: PASS")
    print()

    # Test equivalences
    equivs = corpus.find_equivalences()
    print(f"Gematria equivalences found: {len(equivs)} values with 2+ words")
    for val, words in sorted(equivs.items())[:5]:
        print(f"  {val}: {words}")

    if "--test" in sys.argv:
        print("\nAll tests passed.")
