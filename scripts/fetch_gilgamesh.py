#!/usr/bin/env python3
"""
Fetch the Epic of Gilgamesh (Standard Babylonian version).

Primary source: skcin7/gilgamesh on GitHub (N.K. Sandars prose translation
restructured as HTML by Nick Morgan, 2022). Public HTML, no stated copyright.
This organizes the epic into 8 narrative sections (Prologue + 7 Books).

Note on tablets: Sandars reorganized the traditional 12-tablet structure
into a flowing narrative. We map her 8 sections to the approximate
corresponding Standard Babylonian tablets in the metadata.

Produces: data/corpus/gilgamesh_corpus.json

Usage:
    python3 scripts/fetch_gilgamesh.py [--dry-run]
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SOURCE_URL = "https://raw.githubusercontent.com/skcin7/gilgamesh/master/index.html"

SECTION_MAP = {
    "Prologue - Gilgamesh, King in Uruk": {
        "number": 0,
        "tablets_approx": "I",
        "themes": ["kingship", "divine creation", "two-thirds divine nature"],
    },
    "Book 1 - The Coming of Enkidu": {
        "number": 1,
        "tablets_approx": "I-II",
        "themes": ["creation of companion", "wildman civilized", "sacred prostitute", "dreams"],
    },
    "Book 2 - The Forest Journey": {
        "number": 2,
        "tablets_approx": "III-V",
        "themes": ["cedar forest", "Humbaba/Huwawa", "divine combat", "courage vs fear", "fame vs mortality"],
    },
    "Book 3 - Ishtar and Gilgamesh, and the Death of Enkidu": {
        "number": 3,
        "tablets_approx": "VI-VII",
        "themes": ["divine wrath", "Bull of Heaven", "death of companion", "divine judgment", "underworld"],
    },
    "Book 4 - The Search For Everlasting Life": {
        "number": 4,
        "tablets_approx": "VIII-X",
        "themes": ["grief and mortality", "quest for immortality", "underworld journey", "waters of death"],
    },
    "Book 5 - The Story of the Flood": {
        "number": 5,
        "tablets_approx": "XI",
        "themes": ["divine flood", "Noah parallel", "Utnapishtim", "divine judgment on humanity", "ark", "survivors"],
    },
    "Book 6 - The Return": {
        "number": 6,
        "tablets_approx": "XI",
        "themes": ["plant of immortality", "serpent theft", "acceptance of mortality", "legacy through works"],
    },
    "Book 7 - The Death of Gilgamesh": {
        "number": 7,
        "tablets_approx": "XII",
        "themes": ["death", "underworld", "final judgment", "shadow existence after death", "kings in dust"],
    },
}

ESCHATOLOGICAL_THEMES = [
    "divine flood (global judgment)",
    "death and the underworld",
    "quest for immortality",
    "divine punishment of humanity",
    "shadows of the dead (rephaim parallel)",
    "serpent and loss of immortality",
    "kings reduced to dust",
    "Utnapishtim (Noah parallel)",
    "mortality as human condition",
    "divine council and decree",
    "waters of death",
    "tree of life motif",
]

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "gilgamesh_corpus.json"

DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# HTML Parser
# ---------------------------------------------------------------------------

class GilgameshParser(HTMLParser):
    """Parse the skcin7/gilgamesh HTML into sections and paragraphs."""

    def __init__(self):
        super().__init__()
        self.sections: dict[str, list[str]] = {}
        self._current_section: str | None = None
        self._in_h2 = False
        self._h2_buf = ""
        self._in_p = False
        self._p_buf = ""
        self._skip_toc = True  # skip TOC h2 entries

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self._in_h2 = True
            self._h2_buf = ""
        elif tag == "p":
            self._in_p = True
            self._p_buf = ""
        elif tag in ("i", "em", "b", "strong", "span") and self._in_p:
            pass  # inline formatting, just collect text

    def handle_endtag(self, tag):
        if tag == "h2":
            self._in_h2 = False
            name = self._h2_buf.strip()
            if name and name != "Table of Contents" and name not in ("Glossary of Names",):
                self._current_section = name
                if name not in self.sections:
                    self.sections[name] = []
        elif tag == "p":
            self._in_p = False
            text = re.sub(r"\s+", " ", self._p_buf).strip()
            # Filter out very short entries and navigation/TOC items
            if text and self._current_section and len(text) > 30:
                self.sections[self._current_section].append(text)
            self._p_buf = ""

    def handle_data(self, data):
        if self._in_h2:
            self._h2_buf += data
        elif self._in_p:
            self._p_buf += data


# ---------------------------------------------------------------------------
# Corpus builder
# ---------------------------------------------------------------------------

def fetch_html(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "osnova-corpus-builder/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt + 1}/{retries}: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)


def build_corpus(sections: dict[str, list[str]]) -> dict:
    """Convert parsed sections into corpus verse format.

    Each paragraph becomes a verse-like entry. Key format: "section_num:para_num"
    e.g. "0:1" = Prologue paragraph 1, "5:3" = Book 5 (Flood) paragraph 3.
    """
    verses = {}

    for section_name, paragraphs in sections.items():
        meta = SECTION_MAP.get(section_name, {})
        section_num = meta.get("number", 99)

        for i, para in enumerate(paragraphs, start=1):
            key = f"{section_num}:{i}"
            words = para.split()
            verses[key] = {
                "section": section_name,
                "section_number": section_num,
                "tablets_approx": meta.get("tablets_approx", "?"),
                "text": para,
                "words": words,
                "word_count": len(words),
                "themes": meta.get("themes", []),
            }

    return verses


def main():
    print(f"Fetching: {SOURCE_URL}")
    html = fetch_html(SOURCE_URL)
    print(f"Downloaded {len(html):,} bytes")

    parser = GilgameshParser()
    parser.feed(html)

    sections = parser.sections
    print(f"\nParsed sections ({len(sections)}):")
    for name, paras in sections.items():
        word_count = sum(len(p.split()) for p in paras)
        print(f"  {name}: {len(paras)} paragraphs, {word_count:,} words")

    if DRY_RUN:
        print("\n[DRY RUN] Sample - Prologue paragraph 1:")
        for name, paras in sections.items():
            if paras:
                print(f"  [{name}] {paras[0][:200]}...")
                break
        return

    verses = build_corpus(sections)

    total_paragraphs = len(verses)
    total_words = sum(v["word_count"] for v in verses.values())

    corpus = {
        "meta": {
            "title": "The Epic of Gilgamesh",
            "subtitle": "Standard Babylonian Version (Nineveh tablets)",
            "source": "skcin7/gilgamesh (GitHub) - N.K. Sandars translation adapted as HTML",
            "source_url": "https://github.com/skcin7/gilgamesh",
            "original_translator": "N.K. Sandars (Penguin Classics, 1960/1972)",
            "html_adapter": "Nick Morgan, 2022",
            "age": "Standard Babylonian: ~1300-1000 BCE; oral tradition ~2100 BCE",
            "language": "English (translated from Akkadian/Sumerian)",
            "note": (
                "Sandars reorganized the traditional 12-tablet structure into 8 narrative sections. "
                "tablets_approx field maps each section to corresponding Standard Babylonian tablets."
            ),
            "traditional_tablets": 12,
            "sections": len(sections),
            "paragraphs": total_paragraphs,
            "total_words": total_words,
            "eschatological_themes": ESCHATOLOGICAL_THEMES,
            "section_to_tablet_map": {
                name: meta.get("tablets_approx", "?")
                for name, meta in SECTION_MAP.items()
            },
            "date_fetched": str(date.today()),
        },
        "verses": verses,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Sections: {len(sections)} | Paragraphs: {total_paragraphs} | Words: {total_words:,} | Size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
