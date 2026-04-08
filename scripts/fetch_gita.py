#!/usr/bin/env python3
"""
Fetch the complete Bhagavad Gita from deepakrakshit/bhagavad-gita-dataset on GitHub.
Source: https://github.com/deepakrakshit/bhagavad-gita-dataset
Fields per verse: Sanskrit (Devanagari + IAST), English translation + explanation.

Produces: data/corpus/bhagavad_gita_corpus.json

Usage:
    python3 scripts/fetch_gita.py [--dry-run]
"""

import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://raw.githubusercontent.com/deepakrakshit/bhagavad-gita-dataset/main/dataset/chapter_{:02d}.json"

CHAPTER_NAMES = {
    1: "Arjuna's Dilemma",
    2: "Transcendent Knowledge",
    3: "The Yoga of Action",
    4: "Knowledge and Action",
    5: "Renunciation vs. Action",
    6: "The Yoga of Meditation",
    7: "Knowledge of the Absolute",
    8: "The Imperishable Brahman",
    9: "The Most Confidential Knowledge",
    10: "The Opulence of the Absolute",
    11: "The Universal Form",
    12: "Devotional Service",
    13: "Nature, the Enjoyer, and Consciousness",
    14: "The Three Modes of Nature",
    15: "The Supreme Person",
    16: "The Divine and Demoniac Natures",
    17: "The Divisions of Faith",
    18: "The Perfection of Renunciation",
}

# Chapter 18 has a typo in the source: "chapter_18..json"
CHAPTER_URLS = {i: BASE_URL.format(i) for i in range(1, 18)}
CHAPTER_URLS[18] = "https://raw.githubusercontent.com/deepakrakshit/bhagavad-gita-dataset/main/dataset/chapter_18..json"

ESCHATOLOGICAL_THEMES = [
    "kaliyuga",
    "cosmic dissolution (pralaya)",
    "dharmic warfare",
    "divine judgment",
    "karma and rebirth",
    "moksha (liberation)",
    "death and the eternal soul (atman)",
    "universal form (vishvarupa)",
    "time as destroyer (kala)",
    "righteousness vs adharma",
    "sacrifice and sacred duty",
    "cyclical time (yugas)",
]

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "bhagavad_gita_corpus.json"

DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_json(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "osnova-corpus-builder/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt + 1}/{retries} after error: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)


def extract_verse(chapter_num: int, verse_data: dict) -> dict:
    """Extract verse fields into our corpus schema."""
    verse_num = verse_data.get("verse_number", 0)
    key = f"{chapter_num}:{verse_num}"

    sanskrit = verse_data.get("sanskrit", {})
    english = verse_data.get("english", {})
    hindi = verse_data.get("hindi", {})

    text = english.get("translation", "").strip()
    devanagari = sanskrit.get("devanagari", "").strip()
    iast = sanskrit.get("iast", "").strip()

    words = text.split() if text else []

    entry = {
        "text": text,
        "transliteration": iast,
        "devanagari": devanagari,
        "words": words,
        "word_count": len(words),
        "speaker": verse_data.get("speaker", ""),
        "explanation": english.get("explanation", "").strip(),
    }
    # Drop empty fields
    entry = {k: v for k, v in entry.items() if v not in ("", [], None)}
    return key, entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    corpus = {
        "meta": {
            "title": "Bhagavad Gita",
            "source": "deepakrakshit/bhagavad-gita-dataset (GitHub)",
            "source_url": "https://github.com/deepakrakshit/bhagavad-gita-dataset",
            "age": "~200 BCE (compiled in Mahabharata)",
            "language": "Sanskrit (Devanagari + IAST) + English",
            "translator": "Traditional (composite dataset)",
            "eschatological_themes": ESCHATOLOGICAL_THEMES,
            "sections": 18,
            "date_fetched": str(date.today()),
            "chapters": CHAPTER_NAMES,
        },
        "verses": {},
    }

    chapters_to_fetch = range(1, 2) if DRY_RUN else range(1, 19)

    for ch in chapters_to_fetch:
        url = CHAPTER_URLS[ch]
        print(f"Chapter {ch:2d}: {CHAPTER_NAMES[ch]} ... ", end="", flush=True)
        try:
            raw = fetch_json(url)
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            continue

        # The chapter JSON is a list of verse objects
        if isinstance(raw, list):
            verses = raw
        elif isinstance(raw, dict) and "verses" in raw:
            verses = raw["verses"]
        else:
            print(f"Unexpected format: {type(raw)}", file=sys.stderr)
            continue

        ch_count = 0
        for verse_data in verses:
            try:
                key, entry = extract_verse(ch, verse_data)
                corpus["verses"][key] = entry
                ch_count += 1
            except Exception as e:
                print(f"  Error on verse: {e}", file=sys.stderr)

        print(f"{ch_count} verses")
        if not DRY_RUN:
            time.sleep(0.3)  # polite rate limiting

    # Update meta counts
    total_verses = len(corpus["verses"])
    total_words = sum(v.get("word_count", 0) for v in corpus["verses"].values())
    corpus["meta"]["verses"] = total_verses
    corpus["meta"]["total_words"] = total_words

    if DRY_RUN:
        print(f"\n[DRY RUN] Would save {total_verses} verses, {total_words} words")
        print("Sample verse 1:1:")
        print(json.dumps(corpus["verses"].get("1:1", {}), ensure_ascii=False, indent=2))
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Verses: {total_verses} | Words: {total_words:,} | Size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
