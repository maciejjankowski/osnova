#!/usr/bin/env python3
"""
Fetch the complete Quran text from alquran.cloud API.
Produces a verse-addressed JSON corpus at data/corpus/quran_corpus.json.

Source: https://api.alquran.cloud/v1/quran/quran-uthmani
  - Returns all 114 surahs in a single API call (no auth required)
  - Uthmani script is the canonical manuscript tradition
  - Verse addressing: "surah:ayah" (e.g. "1:1" = Al-Fatiha v1)

Abjad computation uses the consonantal skeleton only - tashkeel (harakat)
are stripped before calculation, matching the Torah corpus pattern of
stripping nikud before computing gematria.

Usage:
    python3 scripts/fetch_quran.py [--dry-run]

Options:
    --dry-run   Fetch and parse, show first 5 verses, don't save
"""

import json
import re
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "https://api.alquran.cloud/v1/quran/quran-uthmani"

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "corpus" / "quran_corpus.json"

# ---------------------------------------------------------------------------
# Abjad engine (self-contained, matches abjad.py)
# ---------------------------------------------------------------------------

LETTER_VALUES = {
    'ا': 1, 'أ': 1, 'إ': 1, 'آ': 1, 'ء': 1, '\u0671': 1,  # Alif variants + wasla
    'ب': 2,
    'ج': 3,
    'د': 4,
    'ه': 5, 'ة': 5,   # Ha and Ta marbuta
    'و': 6, 'ؤ': 6,   # Waw variants
    'ز': 7,
    'ح': 8,
    'ط': 9,
    'ي': 10, 'ى': 10, 'ئ': 10,  # Ya variants
    'ك': 20,
    'ل': 30,
    'م': 40,
    'ن': 50,
    'س': 60,
    'ع': 70,
    'ف': 80,
    'ص': 90,
    'ق': 100,
    'ر': 200,
    'ش': 300,
    'ت': 400,
    'ث': 500,
    'خ': 600,
    'ذ': 700,
    'ض': 800,
    'ظ': 900,
    'غ': 1000,
}

ARABIC_LETTERS = set(LETTER_VALUES.keys())


def strip_tashkeel(text: str) -> str:
    """
    Remove Arabic diacritical marks (tashkeel/harakat) from text.
    Also applies NFKC normalization to decompose ligatures and
    Uthmani-specific presentation forms.

    Stripped ranges:
    - 0x064B-0x065F: harakat (fatha, kasra, damma, shadda, sukun, tanwin, etc.)
    - 0x0670:        superscript alef
    - 0x0610-0x061A: small high letters
    - 0x06D6-0x06DC: Quranic annotation signs
    - 0x06DF-0x06E4: more annotation signs
    - 0x06E7-0x06E8: more annotation signs
    - 0x06EA-0x06ED: more annotation signs
    - 0x0615:        small high tah
    """
    # Normalize Uthmani / presentation forms to standard Arabic
    text = unicodedata.normalize('NFKC', text)

    result = []
    for ch in text:
        cp = ord(ch)
        if (0x0610 <= cp <= 0x061A or
                0x064B <= cp <= 0x065F or
                cp == 0x0670 or
                0x06D6 <= cp <= 0x06DC or
                0x06DF <= cp <= 0x06E4 or
                0x06E7 <= cp <= 0x06E8 or
                0x06EA <= cp <= 0x06ED or
                cp == 0x0615):
            continue
        result.append(ch)

    return ''.join(result)


def compute_abjad(text: str) -> int:
    """Compute Abjad value of Arabic text after stripping tashkeel."""
    stripped = strip_tashkeel(text)
    return sum(LETTER_VALUES.get(c, 0) for c in stripped)


def extract_words(text: str) -> list[str]:
    """
    Extract Arabic word tokens from verse text.
    Strips tashkeel, splits on whitespace, keeps tokens containing
    at least one Arabic letter.
    """
    stripped = strip_tashkeel(text)
    tokens = stripped.split()
    return [tok for tok in tokens if any(c in ARABIC_LETTERS for c in tok)]


# ---------------------------------------------------------------------------
# Surah metadata
# ---------------------------------------------------------------------------

SURAH_NAMES = {
    1: "Al-Fatiha", 2: "Al-Baqara", 3: "Ali Imran", 4: "An-Nisa",
    5: "Al-Maida", 6: "Al-Anam", 7: "Al-Araf", 8: "Al-Anfal",
    9: "At-Tawba", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Rad", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Muminun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shuara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajda",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
    45: "Al-Jathiya", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
    53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqia",
    57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahana",
    61: "As-Saf", 62: "Al-Jumuah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqa", 70: "Al-Maarij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyama", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Naziat", 80: "Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "At-Tariq", 87: "Al-Ala", 88: "Al-Ghashiya",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
    93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-Alaq",
    97: "Al-Qadr", 98: "Al-Bayyina", 99: "Az-Zalzala", 100: "Al-Adiyat",
    101: "Al-Qaria", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humaza",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Maun", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_quran() -> dict:
    """
    Fetch full Quran from alquran.cloud API in a single call.
    Returns the parsed JSON data dict.
    """
    print(f"Fetching from {API_URL} ...")
    req = urllib.request.Request(
        API_URL,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json',
        }
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode('utf-8')

    # Strip BOM if present (API sometimes prepends U+FEFF to the response)
    raw = raw.lstrip('\ufeff')
    data = json.loads(raw)

    if data.get('code') != 200 or data.get('status') != 'OK':
        raise RuntimeError(f"API error: {data.get('status')} / {data.get('code')}")

    return data['data']


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def parse_quran(api_data: dict) -> tuple[dict, dict]:
    """
    Parse API response into:
    - verses dict: {"surah:ayah": {...}}
    - surahs_meta dict: {surah_num: {...}}

    Returns (verses, surahs_meta).
    """
    verses = {}
    surahs_meta = {}

    for surah in api_data['surahs']:
        surah_num = surah['number']
        surahs_meta[surah_num] = {
            "name_arabic": surah['name'],
            "name_english": surah['englishName'],
            "name_translation": surah['englishNameTranslation'],
            "revelation_type": surah['revelationType'],
            "ayah_count": len(surah['ayahs']),
        }

        for ayah in surah['ayahs']:
            ayah_num = ayah['numberInSurah']
            ref = f"{surah_num}:{ayah_num}"

            arabic_text = ayah['text'].lstrip('\ufeff').strip()
            words = extract_words(arabic_text)
            abjad_val = compute_abjad(arabic_text)

            verses[ref] = {
                "arabic": arabic_text,
                "words": words,
                "word_count": len(words),
                "abjad": abjad_val,
            }

    return verses, surahs_meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args

    print("=" * 60)
    print("QURAN CORPUS FETCHER - alquran.cloud")
    print(f"Output: {OUTPUT_PATH}")
    if dry_run:
        print("MODE: DRY RUN (fetch all, show 5 verses, don't save)")
    print("=" * 60)

    # Fetch
    api_data = fetch_quran()
    surah_count = len(api_data['surahs'])
    print(f"Received {surah_count} surahs from API")

    # Parse
    print("Parsing verses...")
    verses, surahs_meta = parse_quran(api_data)
    total_ayat = len(verses)
    print(f"Parsed {total_ayat} ayat")

    if dry_run:
        print("\nDRY RUN - first 5 verses:")
        for ref, data in list(verses.items())[:5]:
            print(f"  {ref}: {data['arabic']}")
            print(f"       words={data['words'][:4]}{'...' if len(data['words'])>4 else ''}")
            print(f"       abjad={data['abjad']}")
        print("\n(Not saving - dry run mode)")
        return

    # Build corpus
    output = {
        "meta": {
            "source": "alquran.cloud API",
            "edition": "quran-uthmani",
            "surahs": surah_count,
            "ayat": total_ayat,
            "script": "uthmani",
            "date_fetched": str(date.today()),
        },
        "verses": verses,
    }

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Saved: {size_kb:.0f} KB")

    # Verification
    print("\nVerification:")
    # Verification: check that the words list for each ref contains the expected
    # root token (after strip_tashkeel, which handles Uthmani U+0671 alif wasla).
    # We match against stripped words[], not the raw arabic string, so U+0671
    # vs U+0627 alif variants don't cause false mismatches.
    checks = [
        ("1:1",   "بسم",       "Al-Fatiha 1:1 - Bismillah"),
        ("1:2",   "لله",       "Al-Fatiha 1:2 - Alhamdulillah"),
        ("2:255", "هو",        "Ayat al-Kursi (Throne Verse)"),
        ("112:1", "قل",        "Al-Ikhlas 112:1 - Qul"),
        ("36:1",  "يس",        "Ya-Sin 36:1 - Muqatta'at"),
    ]

    all_ok = True
    for ref, expected_word, label in checks:
        if ref in verses:
            words = verses[ref]['words']
            found = any(expected_word in w for w in words)
            status = "OK" if found else "MISMATCH"
            if not found:
                all_ok = False
            print(f"  [{status}] {ref} ({label}): {verses[ref]['arabic'][:50]}...")
        else:
            print(f"  [MISSING] {ref} ({label})")
            all_ok = False

    # Key numerological checks
    print("\nNumerological checks:")
    al_fatiha_1_1 = verses.get("1:1", {})
    print(f"  1:1 abjad = {al_fatiha_1_1.get('abjad')} (Bismillah)")
    print(f"  1:1 word_count = {al_fatiha_1_1.get('word_count')}")

    # Stats
    total_words = sum(d['word_count'] for d in verses.values())
    unique_words = len(set(w for d in verses.values() for w in d['words']))
    abjad_values = [d['abjad'] for d in verses.values()]
    max_abjad = max(abjad_values)
    min_abjad = min(v for v in abjad_values if v > 0)

    print(f"\nCorpus stats:")
    print(f"  Surahs: {surah_count}")
    print(f"  Ayat: {total_ayat}")
    print(f"  Total word tokens: {total_words}")
    print(f"  Unique word forms: {unique_words}")
    print(f"  Abjad range: {min_abjad} - {max_abjad}")
    print(f"  Avg abjad/verse: {sum(abjad_values)/len(abjad_values):.0f}")
    print(f"  File size: {size_kb:.0f} KB")

    if not all_ok:
        print("\nWARNING: some verification checks failed - review output")
        sys.exit(1)

    print("\nDone.")


if __name__ == '__main__':
    main()
