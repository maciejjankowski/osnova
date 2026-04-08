#!/usr/bin/env python3
"""
Fetch the complete New Testament (KJV) from bible-api.com.
Produces a verse-addressed JSON corpus at data/corpus/nt_corpus.json.

Source: https://bible-api.com/ (free, public domain KJV)
API: https://bible-api.com/{book}+{chapter} (whole chapter)
     or https://bible-api.com/{book} (whole book, 'whole_chapter=true' not needed)

Addressing: Book:chapter:verse (e.g. "Matthew:1:1")

Usage:
    python3 scripts/fetch_bible_nt.py [--dry-run] [--book NAME] [--resume]

Options:
    --dry-run   Fetch only Matthew, don't save
    --book NAME Fetch only one book (e.g. "John")
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

REQUEST_DELAY = 2.5  # seconds between requests (respectful - avoid 429s)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "nt_corpus.json"

# 27 NT books in canonical order, with total chapter counts
NT_BOOKS = [
    ("Matthew",          28),
    ("Mark",             16),
    ("Luke",             24),
    ("John",             21),
    ("Acts",             28),
    ("Romans",           16),
    ("1 Corinthians",    16),
    ("2 Corinthians",    13),
    ("Galatians",         6),
    ("Ephesians",         6),
    ("Philippians",       4),
    ("Colossians",        4),
    ("1 Thessalonians",   5),
    ("2 Thessalonians",   3),
    ("1 Timothy",         6),
    ("2 Timothy",         4),
    ("Titus",             3),
    ("Philemon",          1),
    ("Hebrews",          13),
    ("James",             5),
    ("1 Peter",           5),
    ("2 Peter",           3),
    ("1 John",            5),
    ("2 John",            1),
    ("3 John",            1),
    ("Jude",              1),
    ("Revelation",       22),
]

API_BASE = "https://bible-api.com"

# ---------------------------------------------------------------------------
# API fetcher
# ---------------------------------------------------------------------------

def build_api_url(book: str, chapter: int) -> str:
    """
    bible-api.com URL format: /BookName+chapter?translation=kjv
    Spaces in book names are fine (API handles them).
    We use + encoding for spaces.
    """
    book_encoded = urllib.parse.quote(f"{book} {chapter}")
    return f"{API_BASE}/{book_encoded}?translation=kjv"


def fetch_chapter_api(book: str, chapter: int) -> dict:
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

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"    HTTP ERROR {e.code} fetching {url}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"    ERROR fetching {url}: {e}", file=sys.stderr)
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

def checkpoint_save(verses: dict, output_path: Path):
    """Save current verses to disk as a checkpoint (for resume on failure)."""
    sorted_v = dict(sorted(verses.items(), key=lambda kv: verse_sort_key(kv[0])))
    books_present = len({ref.split(":")[0] for ref in sorted_v})
    output = {
        "meta": {
            "source": "bible-api.com (KJV)",
            "books": books_present,
            "verses": len(sorted_v),
            "language": "English (KJV)",
            "date_fetched": str(date.today()),
            "status": "partial",
        },
        "verses": sorted_v,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def build_corpus(books_to_fetch=None, resume_from=None, dry_run=False, checkpoint_path=None):
    """
    Fetch NT corpus and return as dict ready for JSON serialization.

    books_to_fetch:   list of book names, None = all 27
    resume_from:      existing verses dict to resume into
    dry_run:          fetch only Matthew
    checkpoint_path:  if set, save partial results after each book
    """
    verses = resume_from or {}
    total_fetched = 0
    errors = 0

    target_books = books_to_fetch or [name for name, _ in NT_BOOKS]

    # Build quick lookup: name -> chapter count
    chapter_map = {name: chapters for name, chapters in NT_BOOKS}

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
                # Count how many we already have for this chapter
                ch_count = sum(
                    1 for k in verses
                    if k.startswith(f"{book_name}:{chapter}:")
                )
                print(f"  Ch.{chapter:2d}: already in corpus ({ch_count} verses), skipping")
                book_verse_count += ch_count
                continue

            print(f"  Ch.{chapter:2d}: fetching... ", end="", flush=True)
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

        # Checkpoint after each book to enable resume on failure
        if checkpoint_path and not dry_run:
            checkpoint_save(verses, checkpoint_path)
            print(f"  [checkpoint saved: {len(verses)} verses total]")

        if dry_run:
            break

        # Rate limit between books
        if book_name != target_books[-1]:
            time.sleep(REQUEST_DELAY)

    return verses, total_fetched, errors


# ---------------------------------------------------------------------------
# Sorting key for canonical NT order
# ---------------------------------------------------------------------------

BOOK_ORDER = {name: i for i, (name, _) in enumerate(NT_BOOKS)}


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
    print("NT CORPUS FETCHER - bible-api.com (KJV)")
    print(f"Output: {OUTPUT_PATH}")
    if dry_run:
        print("MODE: DRY RUN (Matthew ch.1 only)")
    if resume:
        print("MODE: RESUME (skipping existing verses)")
    print("=" * 60)

    # Load existing corpus if resuming (or if checkpoint exists from prior crash)
    existing_verses = {}
    if OUTPUT_PATH.exists() and (resume or not dry_run):
        print(f"\nLoading existing corpus from {OUTPUT_PATH}...")
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        existing_verses = existing.get("verses", {})
        status = existing.get("meta", {}).get("status", "complete")
        print(f"  Found {len(existing_verses)} existing verses (status: {status})")
        if not resume and status == "complete" and not book_filter:
            print("  Corpus already complete. Use --resume to re-fetch missing chapters.")
            # Still continue - will skip already-fetched chapters

    # Fetch
    print(f"\nStarting fetch at {date.today()}...")
    start_time = time.time()
    verses, total_fetched, errors = build_corpus(
        books_to_fetch=book_filter,
        resume_from=existing_verses,
        dry_run=dry_run,
        checkpoint_path=None if dry_run else OUTPUT_PATH,
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
            "language": "English (KJV)",
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
        ("Matthew:1:1",    "Jesus Christ"),        # genealogy opener
        ("John:1:1",       "In the beginning"),    # Logos
        ("John:3:16",      "For God so loved"),    # most cited verse
        ("Revelation:13:18", "threescore and six"),  # 666 in KJV = "Six hundred threescore and six"
        ("Romans:8:28",    "all things work"),     # providence
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
