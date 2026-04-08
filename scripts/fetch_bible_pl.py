#!/usr/bin/env python3
"""
Fetch the complete Polish Bible (OT + NT) from bolls.life using the
Biblia Gdanska 1632 (translation code: BG) - public domain Protestant
translation.

Source: https://bolls.life/ (BG = Biblia Gdanska, 1632)
API endpoint: GET https://bolls.life/get-text/BG/{book_id}/{chapter}/
Returns: JSON array of {pk, verse, text}

Usage:
    python3 scripts/fetch_bible_pl.py [--dry-run] [--resume] [--book N]

Options:
    --dry-run   Fetch only Genesis ch.1, don't save
    --resume    Skip chapters already in output file
    --book N    Fetch only book number N (1-66)
"""

import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TRANSLATION = "BG"  # Biblia Gdanska 1632 - public domain
BASE_URL = "https://bolls.life/get-text/{translation}/{book}/{chapter}/"
REQUEST_DELAY = 1.0  # seconds between requests

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "bible_pl_corpus.json"

# ---------------------------------------------------------------------------
# Book definitions: (book_id, abbrev, name_pl, chapters, testament)
# ---------------------------------------------------------------------------
# Abbreviations follow Polish Catholic/ecumenical convention (catechism refs)
# OT uses standard Polish Bible abbreviations, NT likewise.

BOOKS = [
    # --- Old Testament (39 books) ---
    (1,  "Rdz",  "Ksiega Rodzaju",               50,  "OT"),
    (2,  "Wj",   "Ksiega Wyjscia",               40,  "OT"),
    (3,  "Kpl",  "Ksiega Kaplanska",             27,  "OT"),
    (4,  "Lb",   "Ksiega Liczb",                 36,  "OT"),
    (5,  "Pwt",  "Ksiega Powtorzonego Prawa",    34,  "OT"),
    (6,  "Joz",  "Ksiega Jozuego",               24,  "OT"),
    (7,  "Sdz",  "Ksiega Sedziow",               21,  "OT"),
    (8,  "Rt",   "Ksiega Rut",                    4,  "OT"),
    (9,  "1Sm",  "I Ksiega Samuela",             31,  "OT"),
    (10, "2Sm",  "II Ksiega Samuela",            24,  "OT"),
    (11, "1Krl", "I Ksiega Krolewska",           22,  "OT"),
    (12, "2Krl", "II Ksiega Krolewska",          25,  "OT"),
    (13, "1Krn", "I Ksiega Kronik",              29,  "OT"),
    (14, "2Krn", "II Ksiega Kronik",             36,  "OT"),
    (15, "Ezd",  "Ksiega Ezdrasza",              10,  "OT"),
    (16, "Ne",   "Ksiega Nehemiasza",            13,  "OT"),
    (17, "Est",  "Ksiega Estery",                10,  "OT"),
    (18, "Hi",   "Ksiega Ijoba",                 42,  "OT"),
    (19, "Ps",   "Ksiega Psalmow",              150,  "OT"),
    (20, "Prz",  "Ksiega Przyslów",             31,  "OT"),
    (21, "Koh",  "Ksiega Koheleta",             12,  "OT"),
    (22, "Pnp",  "Piesn nad Piesniami",          8,  "OT"),
    (23, "Iz",   "Ksiega Izajasza",             66,  "OT"),
    (24, "Jr",   "Ksiega Jeremiasza",           52,  "OT"),
    (25, "Lm",   "Treny Jeremiaszowe",           5,  "OT"),
    (26, "Ez",   "Ksiega Ezechiela",            48,  "OT"),
    (27, "Dn",   "Ksiega Daniela",              12,  "OT"),
    (28, "Oz",   "Ksiega Ozeasza",              14,  "OT"),
    (29, "Jl",   "Ksiega Joela",                 3,  "OT"),
    (30, "Am",   "Ksiega Amosa",                 9,  "OT"),
    (31, "Ab",   "Ksiega Abdiasza",              1,  "OT"),
    (32, "Jon",  "Ksiega Jonasza",               4,  "OT"),
    (33, "Mi",   "Ksiega Micheasza",             7,  "OT"),
    (34, "Na",   "Ksiega Nahuma",                3,  "OT"),
    (35, "Ha",   "Ksiega Habakuka",              3,  "OT"),
    (36, "So",   "Ksiega Sofoniasza",            3,  "OT"),
    (37, "Ag",   "Ksiega Aggeusza",              2,  "OT"),
    (38, "Za",   "Ksiega Zachariasza",          14,  "OT"),
    (39, "Ml",   "Ksiega Malachiasza",           4,  "OT"),
    # --- New Testament (27 books) ---
    (40, "Mt",   "Ewangelia wg sw. Mateusza",   28,  "NT"),
    (41, "Mk",   "Ewangelia wg sw. Marka",      16,  "NT"),
    (42, "Lk",   "Ewangelia wg sw. Lukasza",    24,  "NT"),
    (43, "J",    "Ewangelia wg sw. Jana",        21,  "NT"),
    (44, "Dz",   "Dzieje Apostolskie",          28,  "NT"),
    (45, "Rz",   "List do Rzymian",             16,  "NT"),
    (46, "1Kor", "I List do Koryntian",         16,  "NT"),
    (47, "2Kor", "II List do Koryntian",        13,  "NT"),
    (48, "Ga",   "List do Galatow",              6,  "NT"),
    (49, "Ef",   "List do Efezjan",              6,  "NT"),
    (50, "Flp",  "List do Filipian",             4,  "NT"),
    (51, "Kol",  "List do Kolosan",              4,  "NT"),
    (52, "1Tes", "I List do Tesaloniczan",       5,  "NT"),
    (53, "2Tes", "II List do Tesaloniczan",      3,  "NT"),
    (54, "1Tm",  "I List do Tymoteusza",         6,  "NT"),
    (55, "2Tm",  "II List do Tymoteusza",        4,  "NT"),
    (56, "Tt",   "List do Tytusa",               3,  "NT"),
    (57, "Flm",  "List do Filemona",             1,  "NT"),
    (58, "Hbr",  "List do Hebrajczykow",        13,  "NT"),
    (59, "Jk",   "List sw. Jakuba",              5,  "NT"),
    (60, "1P",   "1 List sw. Piotra",            5,  "NT"),
    (61, "2P",   "2 List sw. Piotra",            3,  "NT"),
    (62, "1J",   "1 List sw. Jana",              5,  "NT"),
    (63, "2J",   "2 List sw. Jana",              1,  "NT"),
    (64, "3J",   "3 List sw. Jana",              1,  "NT"),
    (65, "Jud",  "List sw. Judy",                1,  "NT"),
    (66, "Ap",   "Apokalipsa sw. Jana",         22,  "NT"),
]

BOOK_BY_ID = {b[0]: b for b in BOOKS}

# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

def fetch_chapter(book_id: int, chapter: int) -> dict:
    """
    Fetch one chapter from bolls.life BG translation.
    Returns dict: {verse_num: {"text": str, "words": list, "word_count": int}}
    """
    url = BASE_URL.format(translation=TRANSLATION, book=book_id, chapter=chapter)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html, */*",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    ERROR fetching {url}: {e}", file=sys.stderr)
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {url}: {e}", file=sys.stderr)
        return {}

    if not isinstance(data, list) or not data:
        return {}

    result = {}
    for entry in data:
        v_num = entry.get("verse")
        text = entry.get("text", "").strip()
        if v_num is None or not text:
            continue
        words = tokenize(text)
        result[v_num] = {
            "text": text,
            "words": words,
            "word_count": len(words),
        }
    return result


# ---------------------------------------------------------------------------
# Tokenizer - Polish words
# ---------------------------------------------------------------------------

# Match sequences of Polish letters (including diacritics)
WORD_RE = re.compile(r"[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]+(?:['-][A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]+)*")


def tokenize(text: str) -> list:
    """Extract word tokens from Polish text."""
    return WORD_RE.findall(text)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_corpus(book_filter=None, resume_from=None, dry_run=False):
    """
    Fetch all books and return (verses_dict, total_fetched, errors).

    verses_dict keys: "ABBREV:chapter:verse" e.g. "Rdz:1:1"
    """
    verses = resume_from or {}
    total_fetched = 0
    errors = 0

    books_to_fetch = [b for b in BOOKS if (book_filter is None or b[0] in book_filter)]

    for book_id, abbrev, name, num_chapters, testament in books_to_fetch:
        chapters = 1 if dry_run else num_chapters
        print(f"\n[{testament} {abbrev}] {name} ({chapters} chapter{'s' if chapters != 1 else ''})")

        for chapter in range(1, chapters + 1):
            key_check = f"{abbrev}:{chapter}:1"
            if resume_from and key_check in verses:
                print(f"  Ch.{chapter:3d}: already in corpus, skipping")
                continue

            print(f"  Ch.{chapter:3d}: fetching... ", end="", flush=True)
            chapter_data = fetch_chapter(book_id, chapter)

            if not chapter_data:
                print("NO DATA")
                errors += 1
            else:
                for verse_num, data in sorted(chapter_data.items()):
                    ref = f"{abbrev}:{chapter}:{verse_num}"
                    verses[ref] = data
                total_fetched += len(chapter_data)
                sample = next(iter(chapter_data.values()))["text"][:50]
                print(f"{len(chapter_data)} verses | {sample}...")

            if chapter < chapters and not dry_run:
                time.sleep(REQUEST_DELAY)

        if dry_run:
            break

    return verses, total_fetched, errors


def main():
    args = sys.argv[1:]
    dry_run  = "--dry-run" in args
    resume   = "--resume" in args

    book_filter = None
    if "--book" in args:
        idx = args.index("--book")
        try:
            book_filter = [int(args[idx + 1])]
        except (IndexError, ValueError):
            print("ERROR: --book requires a number 1-66", file=sys.stderr)
            sys.exit(1)

    print("=" * 65)
    print("POLISH BIBLE CORPUS FETCHER")
    print(f"Source : bolls.life | Translation: Biblia Gdanska 1632 (BG)")
    print(f"Output : {OUTPUT_PATH}")
    if dry_run:
        print("MODE   : DRY RUN (Genesis ch.1 only)")
    if resume:
        print("MODE   : RESUME (skipping existing verses)")
    print("=" * 65)

    # Load existing corpus if resuming
    existing_verses = {}
    if resume and OUTPUT_PATH.exists():
        print(f"\nLoading existing corpus from {OUTPUT_PATH}...")
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        existing_verses = existing.get("verses", {})
        print(f"  Found {len(existing_verses)} existing verses")

    # Fetch
    print(f"\nStarting fetch at {date.today()}...")
    start_time = time.time()
    verses, total_fetched, errors = build_corpus(
        book_filter=book_filter,
        resume_from=existing_verses,
        dry_run=dry_run,
    )
    elapsed = time.time() - start_time

    print(f"\n{'=' * 65}")
    print(f"Fetch complete: {total_fetched} new verses in {elapsed:.1f}s")
    print(f"Total verses in corpus: {len(verses)}")
    if errors:
        print(f"WARNING: {errors} chapters had errors")

    if dry_run:
        print("\nDRY RUN - first 5 verses:")
        for ref, data in list(verses.items())[:5]:
            print(f"  {ref}: {data['text']}")
            print(f"         words={data['words'][:6]}...")
        print("\n(Not saving - dry run mode)")
        return

    # Build output structure matching existing corpora pattern
    ot_abbrevs = {b[1] for b in BOOKS if b[4] == "OT"}
    nt_abbrevs = {b[1] for b in BOOKS if b[4] == "NT"}
    books_ot_present = len({ref.split(":")[0] for ref in verses if ref.split(":")[0] in ot_abbrevs})
    books_nt_present = len({ref.split(":")[0] for ref in verses if ref.split(":")[0] in nt_abbrevs})

    total_words = sum(d["word_count"] for d in verses.values())

    output = {
        "meta": {
            "source": "bolls.life (Biblia Gdanska 1632, public domain)",
            "translation": "Biblia Gdanska 1632 (BG)",
            "books_ot": books_ot_present,
            "books_nt": books_nt_present,
            "total_verses": len(verses),
            "total_words": total_words,
            "language": "Polish",
            "date_fetched": str(date.today()),
        },
        "verses": dict(
            sorted(
                verses.items(),
                key=lambda x: _sort_key(x[0]),
            )
        ),
    }

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")

    # Spot-check key verses
    print("\nVerification spot-checks:")
    checks = [
        ("Rdz:1:1",    "Na początku"),
        ("Ps:23:1",    "Pan"),
        ("Iz:53:5",    "zraniony"),
        ("Mt:1:1",     "Jezusa"),
        ("J:1:1",      "Słowo"),
        ("Ap:22:21",   None),   # last verse in Bible
    ]
    for ref, expected_word in checks:
        if ref in verses:
            text = verses[ref]["text"]
            if expected_word:
                ok = expected_word.lower() in text.lower()
                status = "OK" if ok else "CHECK"
            else:
                status = "PRESENT"
            print(f"  [{status:7s}] {ref}: {text[:70]}")
        else:
            print(f"  [MISSING] {ref}")

    # Corpus statistics
    unique_words = len(set(
        w.lower() for d in verses.values() for w in d["words"]
    ))
    print(f"\nCorpus statistics:")
    print(f"  Books (OT):        {books_ot_present}/39")
    print(f"  Books (NT):        {books_nt_present}/27")
    print(f"  Total verses:      {len(verses):,}")
    print(f"  Total word tokens: {total_words:,}")
    print(f"  Unique word forms: {unique_words:,}")
    print(f"  File size:         {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")


def _sort_key(ref: str):
    """Sort verse refs by canonical Bible book order then chapter:verse."""
    abbrev, chapter, verse = ref.split(":")
    # Find book position in BOOKS list
    for i, (book_id, babbrev, *_) in enumerate(BOOKS):
        if babbrev == abbrev:
            return (i, int(chapter), int(verse))
    return (999, int(chapter), int(verse))


if __name__ == "__main__":
    main()
