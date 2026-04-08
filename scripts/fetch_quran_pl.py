#!/usr/bin/env python3
"""
fetch_quran_pl.py - Fetch Polish Quran (Bielawski translation) from alquran.cloud API

Source: https://api.alquran.cloud/v1/quran/pl.bielawskiego
Translation: Jozef Bielawski (1986) - standard academic Polish translation
Output: /Users/mj/code/osnova/data/corpus/quran_pl_corpus.json
"""

import json
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

API_BASE = "https://api.alquran.cloud/v1"
EDITION = "pl.bielawskiego"
OUTPUT_PATH = Path("/Users/mj/code/osnova/data/corpus/quran_pl_corpus.json")

# Known surah ayah counts (114 surahs, 6236 ayat total)
TOTAL_SURAHS = 114
TOTAL_AYAT = 6236


def fetch_json(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} for {url}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def fetch_full_quran() -> dict:
    """Fetch the full Quran in one request (alquran.cloud supports this)."""
    print(f"Fetching full Quran - edition: {EDITION}")
    url = f"{API_BASE}/quran/{EDITION}"
    data = fetch_json(url)
    if data.get("code") != 200:
        raise RuntimeError(f"API returned code {data.get('code')}: {data.get('status')}")
    return data["data"]


def build_corpus(quran_data: dict) -> dict:
    verses = {}
    total_ayat = 0

    for surah in quran_data["surahs"]:
        surah_num = surah["number"]
        for ayah in surah["ayahs"]:
            ayah_num = ayah["numberInSurah"]
            text = ayah["text"]
            words = text.split()
            key = f"{surah_num}:{ayah_num}"
            verses[key] = {
                "text": text,
                "words": words,
                "word_count": len(words),
            }
            total_ayat += 1

    return {
        "meta": {
            "source": "alquran.cloud API (https://api.alquran.cloud/v1/quran/pl.bielawskiego)",
            "translation": "Jozef Bielawski (1986)",
            "edition": EDITION,
            "surahs": len(quran_data["surahs"]),
            "ayat": total_ayat,
            "language": "Polish",
            "date_fetched": date.today().isoformat(),
        },
        "verses": verses,
    }


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("=== Quran PL Fetcher (Bielawski) ===")

    quran_data = fetch_full_quran()

    print(f"  Received {len(quran_data['surahs'])} surahs from API")

    corpus = build_corpus(quran_data)

    ayat_count = corpus["meta"]["ayat"]
    surah_count = corpus["meta"]["surahs"]
    print(f"  Built corpus: {surah_count} surahs, {ayat_count} ayat")

    OUTPUT_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"  Saved to: {OUTPUT_PATH}")
    print(f"  File size: {size_kb:.1f} KB")
    print(f"  Verse count: {ayat_count}")

    # Sanity check
    if ayat_count != TOTAL_AYAT:
        print(f"  WARNING: expected {TOTAL_AYAT} ayat, got {ayat_count}")
    else:
        print(f"  Verse count matches expected {TOTAL_AYAT} - OK")

    # Show sample verse (Al-Fatiha 1:1)
    sample = corpus["verses"].get("1:1", {})
    print(f"\nSample 1:1 -> {sample.get('text', 'N/A')}")

    return corpus


if __name__ == "__main__":
    main()
