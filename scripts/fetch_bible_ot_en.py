#!/usr/bin/env python3
"""
Fetch the complete Old Testament (KJV) from bible-api.com.
Produces a verse-addressed JSON corpus at data/corpus/ot_en_corpus.json.

Source: https://bible-api.com/ (free, public domain KJV)
API: https://bible-api.com/{book}+{chapter}?translation=kjv (whole chapter)

Addressing: Book:chapter:verse (e.g. "Genesis:1:1")

Usage:
    python3 scripts/fetch_bible_ot_en.py [--dry-run] [--book NAME] [--resume]

Options:
    --dry-run   Fetch only Genesis ch.1, don't save
    --book NAME Fetch only one book (e.g. "Psalms")
    --resume    Skip books already in output file
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REQUEST_DELAY = 2.0  # seconds between requests - increased to avoid 429s

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "ot_en_corpus.json"

# 39 OT books in canonical order, with total chapter counts
OT_BOOKS = [
    ("Genesis",         50),
    ("Exodus",          40),
    ("Leviticus",       27),
    ("Numbers",         36),
    ("Deuteronomy",     34),
    ("Joshua",          24),
    ("Judges",          21),
    ("Ruth",             4),
    ("1 Samuel",        31),
    ("2 Samuel",        24),
    ("1 Kings",         22),
    ("2 Kings",         25),
    ("1 Chronicles",    29),
    ("2 Chronicles",    36),
    ("Ezra",            10),
    ("Nehemiah",        13),
    ("Esther",          10),
    ("Job",             42),
    ("Psalms",         150),
    ("Proverbs",        31),
    ("Ecclesiastes",    12),
    ("Song of Solomon",  8),
    ("Isaiah",          66),
    ("Jeremiah",        52),
    ("Lamentations",     5),
    ("Ezekiel",         48),
    ("Daniel",          12),
    ("Hosea",           14),
    ("Joel",             3),
    ("Amos",             9),
    ("Obadiah",          1),
    ("Jonah",            4),
    ("Micah",            7),
    ("Nahum",            3),
    ("Habakkuk",         3),
    ("Zephaniah",        3),
    ("Haggai",           2),
    ("Zechariah",       14),
    ("Malachi",          4),
]

API_BASE = "https://bible-api.com"

# ---------------------------------------------------------------------------
# API fetcher
# ---------------------------------------------------------------------------

def build_api_url(book: str, chapter: int) -> str:
    """
    bible-api.com URL format: /BookName+chapter?translation=kjv
    Spaces in book names are encoded with %20 or +.
    """
    book_encoded = urllib.parse.quote(f"{book} {chapter}")
    return f"{API_BASE}/{book_encoded}?translation=kjv"


def fetch_chapter_api(book: str, chapter: int, retries: int = 3) -> dict:
    """
    Fetch one chapter via bible-api.com JSON API.
    Returns dict: {verse_num: {"text": str, "words": list, "word_count": int}}
    """
    url = build_api_url(book, chapter)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; osnova-corpus-builder/1.0; "
                "+https://github.com/osnova)"
            ),
            "Accept": "application/json",
        }
    )

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as e:
            print(f"    HTTP ERROR {e.code} fetching {url} (attempt {attempt})", file=sys.stderr)
            if attempt < retries:
                time.sleep(REQUEST_DELAY * 3 * attempt)
            else:
                return {}
        except Exception as e:
            print(f"    ERROR fetching {url}: {e} (attempt {attempt})", file=sys.stderr)
            if attempt < retries:
                time.sleep(REQUEST_DELAY * 3 * attempt)
            else:
                return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {url}: {e}", file=sys.stderr)
        return {}

    verses_data = data.get("verses", [])
    if not verses_data:
        print(f"    WARNING: no verses in response for {book} {chapter}", file=sys.stderr)
        return {}

    result = {}
    for v in verses_data:
        verse_num = v.get("verse")
        text = v.get("text", "").strip()
        if not verse_num or not text:
            continue
        # Clean trailing whitespace / newlines
        text = re.sub(r"\s+", " ", text).strip()
        words = text.split()
        result[int(verse_num)] = {
            "text": text,
            "words": words,
            "word_count": len(words),
        }

    return result


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def save_partial(verses: dict, output_path: Path):
    """Write current verses to disk so --resume can recover if interrupted."""
    books_present = len({ref.split(":")[0] for ref in verses})
    output = {
        "meta": {
            "source": "bible-api.com (KJV)",
            "books": books_present,
            "verses": len(verses),
            "language": "English",
            "date_fetched": str(date.today()),
            "status": "partial",
        },
        "verses": verses,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  [checkpoint] {len(verses)} verses saved to disk")


def build_corpus(books_to_fetch=None, resume_from=None, dry_run=False,
                 output_path: Path = None):
    """
    Fetch OT corpus and return as dict ready for JSON serialization.

    books_to_fetch: list of book names, None = all 39
    resume_from:    existing verses dict to resume into
    dry_run:        fetch only Genesis ch.1
    output_path:    if set, save checkpoint after each book
    """
    verses = resume_from or {}
    total_fetched = 0
    errors = 0

    target_books = books_to_fetch or [name for name, _ in OT_BOOKS]

    # Build quick lookup: name -> chapter count
    chapter_map = {name: chapters for name, chapters in OT_BOOKS}

    for book_name in target_books:
        if book_name not in chapter_map:
            print(f"  WARNING: unknown book '{book_name}', skipping", file=sys.stderr)
            continue

        num_chapters = chapter_map[book_name]
        if dry_run:
            num_chapters = 1  # Only first chapter in dry-run

        print(f"\n[{book_name}] ({num_chapters} chapters)")

        book_verse_count = 0
        for chapter in range(1, num_chapters + 1):
            # Check if already fetched (resume mode)
            ref_check = f"{book_name}:{chapter}:1"
            if resume_from and ref_check in verses:
                ch_count = sum(
                    1 for k in verses
                    if k.startswith(f"{book_name}:{chapter}:")
                )
                print(f"  Ch.{chapter:3d}: already in corpus ({ch_count} verses), skipping")
                continue

            print(f"  Ch.{chapter:3d}: fetching... ", end="", flush=True)
            chapter_data = fetch_chapter_api(book_name, chapter)

            if not chapter_data:
                print("NO DATA (error or empty)")
                errors += 1
            else:
                for verse_num, data in sorted(chapter_data.items()):
                    ref = f"{book_name}:{chapter}:{verse_num}"
                    verses[ref] = data
                count = len(chapter_data)
                book_verse_count += count
                total_fetched += count
                sample = next(iter(chapter_data.values()))["text"][:50]
                print(f"{count} verses (sample: {sample!r}...)")

            # Rate limit between chapters (not after the last one)
            if chapter < num_chapters:
                time.sleep(REQUEST_DELAY)

        print(f"  -> {book_verse_count} verses fetched for {book_name}")

        # Save checkpoint after each book (enables --resume recovery)
        if not dry_run and output_path:
            save_partial(verses, output_path)

        if dry_run:
            break

        # Rate limit between books
        if book_name != target_books[-1]:
            time.sleep(REQUEST_DELAY)

    return verses, total_fetched, errors


# ---------------------------------------------------------------------------
# Sorting key for canonical OT order
# ---------------------------------------------------------------------------

BOOK_ORDER = {name: i for i, (name, _) in enumerate(OT_BOOKS)}


def verse_sort_key(ref: str):
    """Sort by canonical book order, then chapter, then verse."""
    parts = ref.split(":")
    book = parts[0]
    chapter = int(parts[1]) if len(parts) > 1 else 0
    verse = int(parts[2]) if len(parts) > 2 else 0
    return (BOOK_ORDER.get(book, 999), chapter, verse)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    resume = "--resume" in args

    # --book NAME option
    book_filter = None
    if "--book" in args:
        idx = args.index("--book")
        try:
            book_filter = [args[idx + 1]]
        except IndexError:
            print("ERROR: --book requires a book name", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    print("OT CORPUS FETCHER - bible-api.com (KJV)")
    print(f"Output: {OUTPUT_PATH}")
    if dry_run:
        print("MODE: DRY RUN (Genesis ch.1 only)")
    if resume:
        print("MODE: RESUME (skipping existing verses)")
    print("=" * 60)

    # Load existing corpus if resuming (or if partial file exists from a checkpoint)
    existing_verses = {}
    if OUTPUT_PATH.exists() and (resume or not book_filter):
        print(f"\nLoading existing corpus from {OUTPUT_PATH}...")
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        existing_verses = existing.get("verses", {})
        print(f"  Found {len(existing_verses)} existing verses")
        if not resume:
            print("  (auto-resume: checkpoint file detected)")

    # Fetch
    print(f"\nStarting fetch at {date.today()}...")
    start_time = time.time()
    verses, total_fetched, errors = build_corpus(
        books_to_fetch=book_filter,
        resume_from=existing_verses if existing_verses else None,
        dry_run=dry_run,
        output_path=OUTPUT_PATH if not dry_run else None,
    )
    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"Fetch complete: {total_fetched} new verses in {elapsed:.1f}s")
    print(f"Total verses in corpus: {len(verses)}")
    if errors:
        print(f"WARNING: {errors} chapters had errors")

    if dry_run:
        print("\nDRY RUN - showing first 3 verses:")
        sorted_items = sorted(verses.items(), key=lambda kv: verse_sort_key(kv[0]))
        for ref, data in sorted_items[:3]:
            print(f"  {ref}: {data['text'][:70]}")
            print(f"       words={data['word_count']}")
        print("\n(Not saving - dry run mode)")
        return

    # Sort by canonical order
    sorted_verses = dict(sorted(verses.items(), key=lambda kv: verse_sort_key(kv[0])))

    # Count unique books present
    books_present = len({ref.split(":")[0] for ref in sorted_verses})

    # Build output
    output = {
        "meta": {
            "source": "bible-api.com (KJV)",
            "books": books_present,
            "verses": len(sorted_verses),
            "language": "English",
            "date_fetched": str(date.today()),
        },
        "verses": sorted_verses,
    }

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {size_kb:.0f} KB ({size_kb / 1024:.2f} MB)")

    # Verification spot-checks
    print("\nVerification:")
    checks = [
        ("Genesis:1:1",       "beginning"),           # creation
        ("Genesis:1:3",       "Let there be light"),  # fiat lux
        ("Exodus:20:3",       "no other gods"),        # first commandment
        ("Psalms:23:1",       "my shepherd"),          # 23rd Psalm
        ("Isaiah:7:14",       "virgin"),               # messianic prophecy
        ("Proverbs:1:7",      "fear of the LORD"),     # wisdom root
        ("Malachi:4:6",       "fathers"),              # OT closing verse area
    ]
    for ref, fragment in checks:
        if ref in sorted_verses:
            text = sorted_verses[ref]["text"]
            found = fragment.lower() in text.lower()
            status = "OK" if found else "MISMATCH"
            print(f"  [{status}] {ref}: {text[:70]}...")
        else:
            print(f"  [MISSING] {ref}")

    # Stats
    total_words = sum(d["word_count"] for d in sorted_verses.values())
    print(f"\nCorpus stats:")
    print(f"  Books: {books_present}")
    print(f"  Verses: {len(sorted_verses)}")
    print(f"  Total word tokens: {total_words}")
    print(f"  Average words/verse: {total_words / max(len(sorted_verses), 1):.1f}")
    print(f"  File size: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
