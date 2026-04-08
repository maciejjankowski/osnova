#!/usr/bin/env python3
"""
Fetch the complete Torah text (5 Books of Moses) from Mechon Mamre.
Produces a verse-addressed JSON corpus at data/corpus/torah_corpus.json.

Source: https://mechon-mamre.org/p/pt/pt0101.htm (Genesis ch.1) etc.
HTML structure: <TD class=h> contains Hebrew text with nikud.
  - Verse number is a Hebrew letter in <B> tag (e.g. <B>א</B>)
  - Actual verse text follows, with nikud vowel marks
  - Maqaf (U+05BE) joins words like hyphens in English
  - Paragraph markers {פ} and {ס} appear as links at end of some verses

Usage:
    python3 scripts/fetch_torah.py [--dry-run] [--book N] [--resume]

Options:
    --dry-run   Parse only first chapter of Genesis, don't save
    --book N    Fetch only book N (1-5)
    --resume    Skip verses already in output file
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
# Config
# ---------------------------------------------------------------------------

BOOK_CODES = {
    1: "pt01",  # Genesis
    2: "pt02",  # Exodus
    3: "pt03",  # Leviticus
    4: "pt04",  # Numbers
    5: "pt05",  # Deuteronomy
}

BOOK_CHAPTERS = {
    1: 50,  # Genesis
    2: 40,  # Exodus
    3: 27,  # Leviticus
    4: 36,  # Numbers
    5: 34,  # Deuteronomy
}

BOOK_NAMES = {
    1: "Genesis",
    2: "Exodus",
    3: "Leviticus",
    4: "Numbers",
    5: "Deuteronomy",
}

BASE_URL = "https://mechon-mamre.org/p/pt/{code}{chapter:02d}.htm"
REQUEST_DELAY = 1.0  # seconds between requests (be respectful)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "torah_corpus.json"

# ---------------------------------------------------------------------------
# Gematria (self-contained, matches gematria.py)
# ---------------------------------------------------------------------------

LETTER_VALUES = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5,
    'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9, 'י': 10,
    'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40,
    'נ': 50, 'ן': 50, 'ס': 60, 'ע': 70, 'פ': 80,
    'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100, 'ר': 200,
    'ש': 300, 'ת': 400,
}


def gematria(word: str) -> int:
    return sum(LETTER_VALUES.get(c, 0) for c in word)


# ---------------------------------------------------------------------------
# Hebrew text cleaning
# ---------------------------------------------------------------------------

# Unicode ranges for Hebrew nikud (vowel marks / cantillation)
# U+0591-U+05C7: Hebrew cantillation marks and vowel points
# U+FB1D-U+FB4E: Hebrew presentation forms (not usually in Mechon Mamre)
NIKUD_RANGE = re.compile(r'[\u0591-\u05C7]')

# Maqaf (Hebrew hyphen U+05BE) - treated as word separator
MAQAF = '\u05BE'

# Hebrew letter set (for filtering verse number prefix)
HEBREW_LETTERS = set('אבגדהוזחטיכךלמםנןסעפףצץקרשת')

# Paragraph/section markers that appear in text
PARASHA_MARKERS = re.compile(r'\{[פסש]\}|\{P\}|\{S\}')


def strip_nikud(text: str) -> str:
    """Remove nikud (vowel points and cantillation marks) from Hebrew text."""
    return NIKUD_RANGE.sub('', text)


def clean_verse_text(raw: str) -> str:
    """
    Clean raw Hebrew verse text extracted from HTML:
    1. Strip nikud (vowel/cantillation marks U+0591-U+05C7)
    2. Replace Unicode maqaf (U+05BE) with space
    3. Remove paragraph markers {פ} {ס}
    4. Remove ASCII punctuation (commas, periods, semicolons, colons)
       that Mechon Mamre adds as syntactic markers
    5. Remove the verse number prefix (Hebrew letter(s) at start of text)
    6. Normalize whitespace
    """
    text = strip_nikud(raw)
    text = PARASHA_MARKERS.sub('', text)
    # Replace Unicode maqaf with space
    text = text.replace(MAQAF, ' ')
    # Remove ASCII punctuation used as syntactic markers in the text
    # Keep hyphens (regular ASCII -) since they join words like maqaf in plain text
    text = re.sub(r'[,;:.()\[\]{}]', '', text)
    text = text.strip()

    # Remove leading Hebrew letter(s) that are the verse number.
    # The verse number appears as 1-3 Hebrew letters at the very start
    # followed by whitespace. We detect by checking if first token is
    # purely Hebrew letters.
    parts = text.split(None, 1)
    if parts and all(c in HEBREW_LETTERS for c in parts[0]):
        text = parts[1] if len(parts) > 1 else ''

    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def extract_words(verse_text: str) -> list:
    """
    Split cleaned verse text into words.
    Only keeps tokens that contain at least one Hebrew letter.
    Punctuation has already been stripped by clean_verse_text.
    Hyphens (ASCII -) are kept as they join words in plain-text Torah
    (equivalent to maqaf in nikud text).
    """
    tokens = verse_text.split()
    return [tok for tok in tokens if any(c in HEBREW_LETTERS for c in tok)]


# ---------------------------------------------------------------------------
# HTML Parser
# ---------------------------------------------------------------------------

class HebrewVerseParser(HTMLParser):
    """
    Parse Mechon Mamre Torah pages.

    Structure we care about:
        <TR>
          <TD class=h>
            <A NAME="N"></A>
            <B>hebrew_letter</B>  (verse number)
            actual hebrew text with nikud...
          </TD>
          <TD> english translation (ignored) </TD>
        </TR>

    We extract all <TD class=h> blocks and parse verse numbers from
    the <A NAME="N"> anchor inside each block.
    """

    def __init__(self):
        super().__init__()
        self.verses = {}       # verse_num (int) -> raw hebrew text
        self._in_hebrew_td = False
        self._current_verse_num = None
        self._buffer = []
        self._depth = 0        # nesting depth inside the TD

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'td':
            cls = attrs_dict.get('class', '')
            # class=h or class='h' - Mechon Mamre uses class=h for Hebrew column
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

        elif tag in ('b', 'span', 'a', 'br') and self._in_hebrew_td:
            pass  # handled via handle_data / handle_endtag

    def handle_endtag(self, tag):
        if tag == 'td' and self._in_hebrew_td:
            self._depth -= 1
            if self._depth <= 0:
                # End of Hebrew TD - save the verse
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
            # Common HTML entities
            if name == 'amp':
                self._buffer.append('&')
            elif name == 'nbsp':
                self._buffer.append(' ')

    def handle_charref(self, name):
        if self._in_hebrew_td:
            try:
                if name.startswith('x'):
                    c = chr(int(name[1:], 16))
                else:
                    c = chr(int(name))
                self._buffer.append(c)
            except (ValueError, OverflowError):
                pass


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

def fetch_chapter(book: int, chapter: int) -> dict:
    """
    Fetch one chapter from Mechon Mamre.
    Returns dict: {verse_num: {"hebrew": str, "words": list, ...}}
    """
    code = BOOK_CODES[book]
    url = BASE_URL.format(code=code, chapter=chapter)

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

def build_corpus(books_to_fetch=None, resume_from=None, dry_run=False):
    """
    Fetch Torah corpus and return as dict ready for JSON serialization.

    books_to_fetch: list of book numbers (1-5), None = all
    resume_from:    existing corpus dict to resume into
    dry_run:        only fetch Genesis ch.1 for testing
    """
    verses = resume_from or {}
    total_fetched = 0
    errors = 0

    if books_to_fetch is None:
        books_to_fetch = [1, 2, 3, 4, 5]

    for book in books_to_fetch:
        num_chapters = BOOK_CHAPTERS[book]
        if dry_run:
            num_chapters = 1

        print(f"\n[Book {book}: {BOOK_NAMES[book]}] ({num_chapters} chapters)")

        for chapter in range(1, num_chapters + 1):
            # Check if already fetched (resume mode)
            # Look for the first verse of this chapter
            ref_check = f"{book}:{chapter}:1"
            if resume_from and ref_check in verses:
                print(f"  Ch.{chapter:2d}: already in corpus, skipping")
                continue

            print(f"  Ch.{chapter:2d}: fetching... ", end='', flush=True)
            chapter_verses = fetch_chapter(book, chapter)

            if not chapter_verses:
                print("NO DATA (error or empty)")
                errors += 1
            else:
                for verse_num, data in chapter_verses.items():
                    ref = f"{book}:{chapter}:{verse_num}"
                    verses[ref] = data
                total_fetched += len(chapter_verses)
                print(f"{len(chapter_verses)} verses (sample: {next(iter(chapter_verses.values()))['hebrew'][:30]}...)")

            if chapter < num_chapters and not dry_run:
                time.sleep(REQUEST_DELAY)

        if dry_run:
            break

    return verses, total_fetched, errors


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    resume = '--resume' in args

    # --book N option
    book_filter = None
    if '--book' in args:
        idx = args.index('--book')
        try:
            book_filter = [int(args[idx + 1])]
        except (IndexError, ValueError):
            print("ERROR: --book requires a number 1-5", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    print("TORAH CORPUS FETCHER - Mechon Mamre")
    print(f"Output: {OUTPUT_PATH}")
    if dry_run:
        print("MODE: DRY RUN (Genesis ch.1 only)")
    if resume:
        print("MODE: RESUME (skipping existing verses)")
    print("=" * 60)

    # Load existing corpus if resuming
    existing_verses = {}
    if resume and OUTPUT_PATH.exists():
        print(f"\nLoading existing corpus from {OUTPUT_PATH}...")
        with open(OUTPUT_PATH, encoding='utf-8') as f:
            existing = json.load(f)
        existing_verses = existing.get('verses', {})
        print(f"  Found {len(existing_verses)} existing verses")

    # Fetch
    print(f"\nStarting fetch at {date.today()}...")
    start_time = time.time()
    verses, total_fetched, errors = build_corpus(
        books_to_fetch=book_filter,
        resume_from=existing_verses,
        dry_run=dry_run,
    )
    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print(f"Fetch complete: {total_fetched} new verses in {elapsed:.1f}s")
    print(f"Total verses in corpus: {len(verses)}")
    if errors:
        print(f"WARNING: {errors} chapters had errors")

    if dry_run:
        print("\nDRY RUN - showing first 3 verses:")
        for i, (ref, data) in enumerate(sorted(verses.items())[:3]):
            print(f"  {ref}: {data['hebrew']}")
            print(f"       words={data['words']}")
            print(f"       gematria={data['verse_gematria']}")
        print("\n(Not saving - dry run mode)")
        return

    # Build output
    output = {
        "meta": {
            "source": "Mechon Mamre (mechon-mamre.org)",
            "books": len(set(int(ref.split(':')[0]) for ref in verses)),
            "verses": len(verses),
            "date_fetched": str(date.today()),
        },
        "verses": dict(sorted(verses.items(), key=lambda x: [int(n) for n in x[0].split(':')])),
    }

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {size_kb:.0f} KB")

    # Verify key verses
    print("\nVerification:")
    checks = [
        ("1:1:1", "בראשית"),   # "In the beginning"
        ("2:3:14", "אהיה"),    # "I AM THAT I AM"
        ("5:6:4", "שמע"),      # Shema
    ]
    for ref, expected_word in checks:
        if ref in verses:
            text = verses[ref]['hebrew']
            found = expected_word in text
            status = "OK" if found else "MISMATCH"
            print(f"  [{status}] {ref}: {text[:60]}...")
        else:
            print(f"  [MISSING] {ref}")

    # Stats
    total_words = sum(d['word_count'] for d in verses.values())
    unique_words = len(set(w for d in verses.values() for w in d['words']))
    print(f"\nCorpus stats:")
    print(f"  Verses: {len(verses)}")
    print(f"  Total word tokens: {total_words}")
    print(f"  Unique words: {unique_words}")
    print(f"  Genesis 1:1 gematria: {verses.get('1:1:1', {}).get('verse_gematria', 'N/A')}")


if __name__ == '__main__':
    main()
