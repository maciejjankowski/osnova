#!/usr/bin/env python3
"""
Fetch the complete Tanakh (Hebrew Bible, 39 books) from Mechon Mamre.
Starts from existing torah_corpus.json (books 1-5) and fetches the
remaining 34 books (Nevi'im + Ketuvim), saving to tanakh_corpus.json.

Source: https://mechon-mamre.org/p/pt/pt0601.htm (Joshua ch.1) etc.
HTML structure is identical to Torah pages: <TD class=h> for Hebrew text.

Verified book codes (2026-04-05):
  Nevi'im:  pt06-pt24  (Joshua through Malachi, with pt08a/b, pt09a/b splits)
  Ketuvim:  pt25a/b, pt26-pt35a/b  (Chronicles, Psalms through Nehemiah)

Usage:
    python3 scripts/fetch_tanakh.py [--dry-run] [--book N] [--resume] [--section nevi|ket]

Options:
    --dry-run        Fetch only Joshua ch.1 and Psalms ch.1, don't save
    --book N         Fetch only book number N (1-39)
    --resume         Skip verses already in output file
    --section nevi   Fetch only Nevi'im (books 6-26)
    --section ket    Fetch only Ketuvim (books 27-39)
"""

import json
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Book registry - corrected from live verification on Mechon Mamre 2026-04-05
# ---------------------------------------------------------------------------
#
# Format: book_number -> (mechon_mamre_code, book_name, num_chapters)
#
# Book numbers 1-5 = Torah (loaded from torah_corpus.json, not re-fetched)
# Book numbers 6-39 = Nevi'im + Ketuvim (fetched here)

BOOK_REGISTRY = {
    # Torah (reference only - loaded from existing file)
    1:  ("pt01",  "Genesis",        50),
    2:  ("pt02",  "Exodus",         40),
    3:  ("pt03",  "Leviticus",      27),
    4:  ("pt04",  "Numbers",        36),
    5:  ("pt05",  "Deuteronomy",    34),

    # Nevi'im Rishonim (Former Prophets)
    6:  ("pt06",  "Joshua",         24),
    7:  ("pt07",  "Judges",         21),
    8:  ("pt08a", "1 Samuel",       31),
    9:  ("pt08b", "2 Samuel",       24),
    10: ("pt09a", "1 Kings",        22),
    11: ("pt09b", "2 Kings",        25),

    # Nevi'im Aharonim (Latter Prophets)
    12: ("pt10",  "Isaiah",         66),
    13: ("pt11",  "Jeremiah",       52),
    14: ("pt12",  "Ezekiel",        48),

    # Trei Asar (Twelve Minor Prophets)
    15: ("pt13",  "Hosea",          14),
    16: ("pt14",  "Joel",            4),
    17: ("pt15",  "Amos",            9),
    18: ("pt16",  "Obadiah",         1),
    19: ("pt17",  "Jonah",           4),
    20: ("pt18",  "Micah",           7),
    21: ("pt19",  "Nahum",           3),
    22: ("pt20",  "Habakkuk",        3),
    23: ("pt21",  "Zephaniah",       3),
    24: ("pt22",  "Haggai",          2),
    25: ("pt23",  "Zechariah",      14),
    26: ("pt24",  "Malachi",         3),

    # Ketuvim (Writings)
    27: ("pt26",  "Psalms",        150),
    28: ("pt27",  "Job",            42),
    29: ("pt28",  "Proverbs",       31),
    30: ("pt29",  "Ruth",            4),
    31: ("pt30",  "Song of Songs",   8),
    32: ("pt31",  "Ecclesiastes",   12),
    33: ("pt32",  "Lamentations",    5),
    34: ("pt33",  "Esther",         10),
    35: ("pt34",  "Daniel",         12),
    36: ("pt35a", "Ezra",           10),
    37: ("pt35b", "Nehemiah",       13),
    38: ("pt25a", "1 Chronicles",   29),
    39: ("pt25b", "2 Chronicles",   36),
}

TORAH_BOOKS     = list(range(1, 6))
NEVI_IM_BOOKS   = list(range(6, 27))
KETUVIM_BOOKS   = list(range(27, 40))
ALL_BOOKS       = list(range(1, 40))

BASE_URL      = "https://mechon-mamre.org/p/pt/{code}{chapter_str}.htm"
REQUEST_DELAY = 1.0  # seconds between requests

TORAH_INPUT   = Path(__file__).parent.parent / "data" / "corpus" / "torah_corpus.json"
OUTPUT_PATH   = Path(__file__).parent.parent / "data" / "corpus" / "tanakh_corpus.json"

# ---------------------------------------------------------------------------
# Gematria (self-contained, identical to fetch_torah.py)
# ---------------------------------------------------------------------------

LETTER_VALUES = {
    'א': 1,  'ב': 2,  'ג': 3,  'ד': 4,  'ה': 5,
    'ו': 6,  'ז': 7,  'ח': 8,  'ט': 9,  'י': 10,
    'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40,
    'נ': 50, 'ן': 50, 'ס': 60, 'ע': 70, 'פ': 80,
    'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100,'ר': 200,
    'ש': 300,'ת': 400,
}


def gematria(word: str) -> int:
    return sum(LETTER_VALUES.get(c, 0) for c in word)


# ---------------------------------------------------------------------------
# Hebrew text cleaning (identical to fetch_torah.py)
# ---------------------------------------------------------------------------

NIKUD_RANGE     = re.compile(r'[\u0591-\u05C7]')
MAQAF           = '\u05BE'
HEBREW_LETTERS  = set('אבגדהוזחטיכךלמםנןסעפףצץקרשת')
PARASHA_MARKERS = re.compile(r'\{[פסש]\}|\{P\}|\{S\}')


def strip_nikud(text: str) -> str:
    return NIKUD_RANGE.sub('', text)


def clean_verse_text(raw: str) -> str:
    """
    Clean raw Hebrew verse text extracted from HTML.
    Steps are identical to fetch_torah.py; handles Psalms poetry line breaks
    (BR tags produce whitespace via handle_data, so no extra work needed).
    """
    text = strip_nikud(raw)
    text = PARASHA_MARKERS.sub('', text)
    text = text.replace(MAQAF, ' ')
    # Remove ASCII punctuation used as syntactic markers
    text = re.sub(r'[,;:.()\[\]{}]', '', text)
    text = text.strip()

    # Remove leading Hebrew verse-number token (1-3 Hebrew letters at start)
    parts = text.split(None, 1)
    if parts and all(c in HEBREW_LETTERS for c in parts[0]):
        text = parts[1] if len(parts) > 1 else ''

    text = ' '.join(text.split())
    return text


def extract_words(verse_text: str) -> list:
    tokens = verse_text.split()
    return [tok for tok in tokens if any(c in HEBREW_LETTERS for c in tok)]


# ---------------------------------------------------------------------------
# HTML Parser (identical to fetch_torah.py)
# ---------------------------------------------------------------------------

class HebrewVerseParser(HTMLParser):
    """
    Parse Mechon Mamre Tanakh pages.

    Structure we care about:
        <TD class=h>
          <A NAME="N"></A>
          <B>hebrew_letter</B>  (verse number)
          actual hebrew text with nikud
          [<BR> for Psalms poetry line breaks]
          [<span class='big'>X</span> for decorative first letter in some books]
        </TD>

    We collect all text data inside TD class=h blocks.
    The span/BR/B tags produce no special handling - their text content
    flows through handle_data normally. Verse numbers come from A NAME="N".
    """

    def __init__(self):
        super().__init__()
        self.verses = {}
        self._in_hebrew_td = False
        self._current_verse_num = None
        self._buffer = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'td':
            cls = attrs_dict.get('class', '')
            if 'h' in cls.split():
                self._in_hebrew_td = True
                self._current_verse_num = None
                self._buffer = []
                self._depth = 1
                return
            if self._in_hebrew_td:
                self._depth += 1

        elif tag == 'a' and self._in_hebrew_td:
            name = attrs_dict.get('name', '')
            if name.isdigit():
                self._current_verse_num = int(name)

    def handle_endtag(self, tag):
        if tag == 'td' and self._in_hebrew_td:
            self._depth -= 1
            if self._depth <= 0:
                if self._current_verse_num is not None:
                    raw = ''.join(self._buffer)
                    self.verses[self._current_verse_num] = raw
                self._in_hebrew_td = False
                self._current_verse_num = None
                self._buffer = []
                self._depth = 0

    def handle_data(self, data):
        if self._in_hebrew_td:
            self._buffer.append(data)

    def handle_entityref(self, name):
        if self._in_hebrew_td:
            if name == 'amp':
                self._buffer.append('&')
            elif name == 'nbsp':
                self._buffer.append(' ')

    def handle_charref(self, name):
        if self._in_hebrew_td:
            try:
                c = chr(int(name[1:], 16) if name.startswith('x') else int(name))
                self._buffer.append(c)
            except (ValueError, OverflowError):
                pass


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

def chapter_to_url_str(book: int, chapter: int) -> str:
    """
    Convert chapter number to Mechon Mamre URL suffix.

    Most books: zero-padded 2-digit decimal (e.g. chapter 1 -> '01', 52 -> '52').
    Psalms (book 27, code pt26) chapters 100-150: hex-like encoding
      100-109 -> 'a0'-'a9'
      110-119 -> 'b0'-'b9'
      120-129 -> 'c0'-'c9'
      130-139 -> 'd0'-'d9'
      140-149 -> 'e0'-'e9'
      150     -> 'f0'
    """
    if book == 27 and chapter >= 100:
        # hex-like: tens digit maps a=10, b=11, c=12, d=13, e=14, f=15
        hex_tens = chr(ord('a') + (chapter - 100) // 10)
        units    = (chapter - 100) % 10
        return f"{hex_tens}{units}"
    return f"{chapter:02d}"


def fetch_chapter(book: int, chapter: int) -> dict:
    """
    Fetch one chapter from Mechon Mamre.
    Returns dict: {verse_num: {"hebrew": str, "words": list, ...}}
    """
    code, name, _ = BOOK_REGISTRY[book]
    chapter_str = chapter_to_url_str(book, chapter)
    url = BASE_URL.format(code=code, chapter_str=chapter_str)

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"    ERROR fetching {url}: {e}", file=sys.stderr)
        return {}

    parser = HebrewVerseParser()
    parser.feed(html)

    result = {}
    for verse_num, raw_text in sorted(parser.verses.items()):
        cleaned = clean_verse_text(raw_text)
        if not cleaned:
            continue
        words = extract_words(cleaned)
        verse_gem = sum(gematria(w) for w in words)
        result[verse_num] = {
            "hebrew": cleaned,
            "words": words,
            "word_count": len(words),
            "verse_gematria": verse_gem,
        }

    return result


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_corpus(books_to_fetch, resume_from=None, dry_run=False):
    """
    Fetch specified books and return as dict ready for JSON serialization.

    books_to_fetch: list of book numbers (1-39)
    resume_from:    existing verse dict to resume into
    dry_run:        only fetch Joshua ch.1 and Psalms ch.1
    """
    verses = resume_from or {}
    total_fetched = 0
    errors = 0

    for book in books_to_fetch:
        code, name, num_chapters = BOOK_REGISTRY[book]

        if dry_run:
            num_chapters = 1

        print(f"\n[Book {book}: {name}] ({num_chapters} chapters, code={code})")

        for chapter in range(1, num_chapters + 1):
            ref_check = f"{book}:{chapter}:1"
            if resume_from and ref_check in verses:
                print(f"  Ch.{chapter:3d}: already in corpus, skipping")
                continue

            print(f"  Ch.{chapter:3d}: fetching... ", end='', flush=True)
            chapter_verses = fetch_chapter(book, chapter)

            if not chapter_verses:
                print("NO DATA (error or empty)")
                errors += 1
            else:
                for verse_num, data in chapter_verses.items():
                    ref = f"{book}:{chapter}:{verse_num}"
                    verses[ref] = data
                total_fetched += len(chapter_verses)
                sample = next(iter(chapter_verses.values()))['hebrew'][:30]
                print(f"{len(chapter_verses)} verses (sample: {sample}...)")

            if not dry_run:
                time.sleep(REQUEST_DELAY)

        if dry_run and book == books_to_fetch[0] and len(books_to_fetch) > 1:
            # For dry run, also fetch one Psalms chapter to test Ketuvim
            break

    return verses, total_fetched, errors


def load_torah_verses() -> dict:
    """Load existing Torah corpus as the starting point."""
    if not TORAH_INPUT.exists():
        print(f"WARNING: Torah corpus not found at {TORAH_INPUT}")
        print("Starting with empty corpus (Torah will be missing)")
        return {}

    print(f"Loading Torah corpus from {TORAH_INPUT}...")
    with open(TORAH_INPUT, encoding='utf-8') as f:
        data = json.load(f)
    verses = data.get('verses', {})
    print(f"  Loaded {len(verses)} Torah verses (books 1-5)")
    return verses


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    resume  = '--resume'  in args

    # --book N
    book_filter = None
    if '--book' in args:
        idx = args.index('--book')
        try:
            book_filter = [int(args[idx + 1])]
        except (IndexError, ValueError):
            print("ERROR: --book requires a number 1-39", file=sys.stderr)
            sys.exit(1)

    # --section nevi|ket
    section_filter = None
    if '--section' in args:
        idx = args.index('--section')
        try:
            sec = args[idx + 1].lower()
            if sec in ('nevi', "nevi'im"):
                section_filter = NEVI_IM_BOOKS
            elif sec in ('ket', 'ketuvim'):
                section_filter = KETUVIM_BOOKS
            else:
                print(f"ERROR: --section must be 'nevi' or 'ket', got {sec!r}", file=sys.stderr)
                sys.exit(1)
        except IndexError:
            print("ERROR: --section requires an argument", file=sys.stderr)
            sys.exit(1)

    # Determine which books to fetch (non-Torah only unless --book specifies Torah)
    if book_filter:
        books_to_fetch = book_filter
    elif section_filter:
        books_to_fetch = section_filter
    else:
        books_to_fetch = NEVI_IM_BOOKS + KETUVIM_BOOKS  # skip Torah (already have it)

    print("=" * 65)
    print("TANAKH CORPUS FETCHER - Mechon Mamre")
    print(f"Output: {OUTPUT_PATH}")
    if dry_run:
        print("MODE: DRY RUN (Joshua ch.1 only)")
    if resume:
        print("MODE: RESUME (skipping existing verses)")
    print(f"Books to fetch: {[BOOK_REGISTRY[b][1] for b in books_to_fetch[:5]]}{'...' if len(books_to_fetch) > 5 else ''}")
    print("=" * 65)

    # Start with Torah verses
    all_verses = load_torah_verses()

    # Load existing output for resume
    if resume and OUTPUT_PATH.exists():
        print(f"\nLoading existing tanakh corpus from {OUTPUT_PATH}...")
        with open(OUTPUT_PATH, encoding='utf-8') as f:
            existing = json.load(f)
        all_verses.update(existing.get('verses', {}))
        print(f"  Total verses after merge: {len(all_verses)}")

    # Fetch
    print(f"\nStarting fetch at {date.today()}...")
    start_time = time.time()
    all_verses, total_fetched, errors = build_corpus(
        books_to_fetch=books_to_fetch,
        resume_from=all_verses,
        dry_run=dry_run,
    )
    elapsed = time.time() - start_time

    print(f"\n{'=' * 65}")
    print(f"Fetch complete: {total_fetched} new verses in {elapsed:.1f}s")
    print(f"Total verses in corpus: {len(all_verses)}")
    if errors:
        print(f"WARNING: {errors} chapters had errors")

    if dry_run:
        print("\nDRY RUN - showing fetched verses:")
        shown = 0
        for ref, data in sorted(all_verses.items(),
                                 key=lambda x: [int(n) for n in x[0].split(':')]):
            book_n = int(ref.split(':')[0])
            if book_n in books_to_fetch:
                print(f"  {ref}: {data['hebrew'][:60]}")
                shown += 1
                if shown >= 5:
                    break
        print("\n(Not saving - dry run mode)")
        return

    # Sort by book:chapter:verse
    sorted_verses = dict(sorted(
        all_verses.items(),
        key=lambda x: [int(n) for n in x[0].split(':')]
    ))

    # Compute book coverage
    book_nums = sorted(set(int(r.split(':')[0]) for r in sorted_verses))
    books_meta = {
        str(b): BOOK_REGISTRY[b][1] for b in book_nums if b in BOOK_REGISTRY
    }

    output = {
        "meta": {
            "source": "Mechon Mamre (mechon-mamre.org)",
            "books_count": len(book_nums),
            "books": books_meta,
            "verses_total": len(sorted_verses),
            "date_fetched": str(date.today()),
            "note": (
                "Hebrew text without nikud (vowel points stripped). "
                "Maqaf replaced with space. Gematria uses standard values."
            ),
        },
        "verses": sorted_verses,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {size_kb:.0f} KB ({size_kb / 1024:.2f} MB)")

    # Spot checks
    print("\nSpot-check verification:")
    checks = [
        ("1:1:1",   "בראשית", "Genesis 1:1"),
        ("6:1:1",   "אחרי",   "Joshua 1:1"),
        ("12:1:1",  "חזון",   "Isaiah 1:1"),
        ("27:1:1",  "אשרי",   "Psalms 1:1"),
        ("28:1:1",  "איוב",   "Job 1:1"),
        ("29:1:1",  "משלי",   "Proverbs 1:1"),
        ("39:1:1",  "שלמה",   "2 Chronicles 1:1"),
    ]
    for ref, expected_word, label in checks:
        if ref in sorted_verses:
            text = sorted_verses[ref]['hebrew']
            found = expected_word in text
            status = "OK" if found else f"MISMATCH (expected '{expected_word}')"
            print(f"  [{status:30}] {label}: {text[:55]}...")
        else:
            print(f"  [MISSING                       ] {label} ({ref})")

    # Stats
    total_words  = sum(d['word_count'] for d in sorted_verses.values())
    unique_words = len(set(w for d in sorted_verses.values() for w in d['words']))
    print(f"\nCorpus stats:")
    print(f"  Books:            {len(book_nums)}")
    print(f"  Verses:           {len(sorted_verses):,}")
    print(f"  Total word tokens:{total_words:,}")
    print(f"  Unique word forms:{unique_words:,}")
    print(f"  File size:        {size_kb:.0f} KB")

    # Per-book breakdown
    print("\nPer-book verse counts:")
    from collections import Counter
    book_counts = Counter(int(r.split(':')[0]) for r in sorted_verses)
    for b in sorted(book_counts):
        name = BOOK_REGISTRY.get(b, (None, f"Book {b}", None))[1]
        print(f"  {b:2d}. {name:20s}: {book_counts[b]:5d} verses")


if __name__ == '__main__':
    main()
