#!/usr/bin/env python3
"""
Parse Zoroastrian eschatological texts from avesta.org HTML files:
- Zand-i Vohuman Yasht (Bahman Yasht) - apocalyptic vision
- Bundahishn - creation and eschatology (chapters on resurrection/renovation)
- Zamyad Yasht (Yasht 19) - Saoshyant prophecy

Produces avesta_corpus.json in osnova corpus format.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from html.parser import HTMLParser

OUTPUT = Path("/Users/mj/code/osnova/data/corpus/avesta_corpus.json")

VOHUMAN_PATH = "/tmp/vohuman_raw.html"
BUNDAHIS_PATH = "/tmp/bundahis_raw.html"
ZAMYAD_PATH = "/tmp/zamyad2_raw.html"


class TextExtractor(HTMLParser):
    """Simple HTML to text extractor."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head'}
        self.current_skip = []
        self.in_menu = False

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.current_skip.append(tag_lower)
        # Skip nav menu
        attrs_dict = dict(attrs)
        if attrs_dict.get('id') == 'menu':
            self.in_menu = True
        if tag_lower in ('br', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'tr', 'li'):
            self.text_parts.append('\n')
        if tag_lower in ('h1', 'h2', 'h3', 'h4'):
            self.text_parts.append('\n### ')

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags and self.current_skip:
            self.current_skip.pop()
        if tag_lower == 'div':
            self.in_menu = False
        if tag_lower in ('h1', 'h2', 'h3', 'h4'):
            self.text_parts.append('\n')

    def handle_data(self, data):
        if not self.current_skip and not self.in_menu:
            self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)


def html_to_text(html_content):
    # Handle ISO-8859-1 encoded content
    if isinstance(html_content, bytes):
        html_content = html_content.decode('iso-8859-1', errors='replace')
    # Decode HTML entities
    html_content = html_content.replace('&nbsp;', ' ')
    html_content = html_content.replace('&amp;', '&')
    html_content = html_content.replace('&lt;', '<')
    html_content = html_content.replace('&gt;', '>')
    html_content = html_content.replace('&icirc;', 'i')
    html_content = html_content.replace('&yacute;', 'y')
    html_content = html_content.replace('&atilde;', 'a')
    html_content = html_content.replace('&ocirc;', 'o')
    html_content = html_content.replace('&ucirc;', 'u')
    html_content = html_content.replace('&acirc;', 'a')
    html_content = html_content.replace('&quot;', '"')
    extractor = TextExtractor()
    extractor.feed(html_content)
    text = extractor.get_text()
    # Normalize whitespace but preserve paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def parse_vohuman(html_path):
    """Parse Zand-i Vohuman Yasht (Bahman Yasht)."""
    raw = Path(html_path).read_bytes()
    text = html_to_text(raw)

    verses = {}
    current_chapter = 0

    # Pattern: CHAPTER I. or chapter headings, then numbered verses
    lines = text.split('\n')

    chapter_pat = re.compile(r'CHAPTER\s+([IVX]+)\.?', re.IGNORECASE)
    # Verse lines: "N. text" or "N. (N) text"
    verse_pat = re.compile(r'^\s*(\d+)\.\s+(.+)', re.DOTALL)

    i = 0
    verse_buffer = []
    cur_verse_num = None

    def flush_verse():
        nonlocal cur_verse_num, verse_buffer, current_chapter
        if cur_verse_num is not None and verse_buffer and current_chapter > 0:
            text_joined = ' '.join(' '.join(verse_buffer).split())
            # Clean up
            text_joined = re.sub(r'\s+', ' ', text_joined).strip()
            words = text_joined.split()
            if len(words) >= 2:  # Skip empty/noise verses
                key = f"{current_chapter}:{cur_verse_num}"
                verses[key] = {
                    "text": text_joined,
                    "words": words,
                    "word_count": len(words)
                }
        verse_buffer = []
        cur_verse_num = None

    for line in lines:
        line_stripped = line.strip()

        # Chapter heading
        ch_match = chapter_pat.search(line_stripped)
        if ch_match and '###' in line:
            flush_verse()
            roman = ch_match.group(1)
            current_chapter = roman_to_int(roman)
            continue

        # Verse line
        v_match = verse_pat.match(line_stripped)
        if v_match and current_chapter > 0:
            flush_verse()
            cur_verse_num = int(v_match.group(1))
            verse_text = v_match.group(2).strip()
            # Remove inline (N) citations
            verse_text = re.sub(r'\(\d+\)\s*', '', verse_text)
            verse_buffer = [verse_text]
        elif cur_verse_num is not None and line_stripped:
            # Continuation of current verse
            cleaned_line = re.sub(r'\(\d+\)\s*', '', line_stripped)
            if cleaned_line:
                verse_buffer.append(cleaned_line)

    flush_verse()
    return verses


def parse_bundahishn(html_path):
    """Parse Bundahishn - uses Arabic chapter numbers (CHAPTER 1.) and verse format 'N.\\ntext'."""
    raw = Path(html_path).read_bytes()
    # Convert HTML entities and extract text from HTML directly
    text = html_to_text(raw)

    verses = {}
    current_chapter = 0

    lines = text.split('\n')

    # Chapter headings: "CHAPTER 1." or "### CHAPTER 1." (from our HTML extractor)
    chapter_pat = re.compile(r'CHAPTER\s+(\d+)', re.IGNORECASE)
    # Verse lines: "N." at start of line (Bundahishn puts verse numbers on their own line)
    # or inline "N. text"
    verse_start_pat = re.compile(r'^\s*(\d+)\.\s*(.*)')

    verse_buffer = []
    cur_verse_num = None

    def flush_verse():
        nonlocal cur_verse_num, verse_buffer, current_chapter
        if cur_verse_num is not None and verse_buffer and current_chapter > 0:
            text_joined = ' '.join(' '.join(verse_buffer).split())
            text_joined = re.sub(r'\s+', ' ', text_joined).strip()
            words = text_joined.split()
            if len(words) >= 2:
                key = f"{current_chapter}:{cur_verse_num}"
                verses[key] = {
                    "text": text_joined,
                    "words": words,
                    "word_count": len(words)
                }
        verse_buffer = []
        cur_verse_num = None

    # Only recognize chapter headings that came from h3/h4 tags (marked with "###")
    # This skips the Table of Contents entries (which are plain "Chapter N." links)
    for line in lines:
        line_stripped = line.strip()

        # Chapter heading: must have "###" prefix (from HTML h3/h4 extractor) AND "CHAPTER N"
        ch_match = chapter_pat.search(line_stripped)
        if ch_match and '###' in line:
            flush_verse()
            new_ch = int(ch_match.group(1))
            if new_ch > 0:
                current_chapter = new_ch
            continue

        v_match = verse_start_pat.match(line_stripped)
        if v_match and current_chapter > 0:
            vn = int(v_match.group(1))
            if 0 <= vn <= 500:  # valid verse range
                flush_verse()
                cur_verse_num = vn
                rest = v_match.group(2).strip()
                verse_buffer = [rest] if rest else []
                continue

        # Continuation line
        if cur_verse_num is not None and line_stripped:
            # Check for inline verse numbers like "2. text" within a paragraph
            inline_match = re.match(r'^(\d+)\.\s+(.+)', line_stripped)
            if inline_match:
                inl_vn = int(inline_match.group(1))
                if 1 <= inl_vn <= 500 and inl_vn != cur_verse_num:
                    flush_verse()
                    cur_verse_num = inl_vn
                    verse_buffer = [inline_match.group(2).strip()]
                    continue
            # Skip navigation/header noise
            if line_stripped in ['Home', 'Contents', 'Prev', 'Next', 'Glossary']:
                continue
            verse_buffer.append(line_stripped)

    flush_verse()
    return verses


def parse_zamyad(html_path):
    """Parse Zamyad Yasht (Yasht 19) - Saoshyant prophecy."""
    raw = Path(html_path).read_bytes()
    text = html_to_text(raw)

    verses = {}
    lines = text.split('\n')

    # Zamyad Yasht has format: "N.\ntext" or "N. text" where N is the strophe number
    verse_pat = re.compile(r'^\s*(\d+)\.\s*(.*)')

    verse_buffer = []
    cur_verse_num = None

    def flush_verse():
        nonlocal cur_verse_num, verse_buffer
        if cur_verse_num is not None and verse_buffer:
            text_joined = ' '.join(' '.join(verse_buffer).split())
            text_joined = re.sub(r'\s+', ' ', text_joined).strip()
            words = text_joined.split()
            if len(words) >= 2:
                key = f"19:{cur_verse_num}"
                verses[key] = {
                    "text": text_joined,
                    "words": words,
                    "word_count": len(words)
                }
        verse_buffer = []
        cur_verse_num = None

    for line in lines:
        line_stripped = line.strip()
        v_match = verse_pat.match(line_stripped)
        if v_match:
            flush_verse()
            cur_verse_num = int(v_match.group(1))
            rest = v_match.group(2).strip()
            verse_buffer = [rest] if rest else []
        elif cur_verse_num is not None and line_stripped:
            verse_buffer.append(line_stripped)

    flush_verse()
    return verses


def roman_to_int(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    prev = 0
    for ch in reversed(s.upper()):
        cur = vals.get(ch, 0)
        if cur < prev:
            result -= cur
        else:
            result += cur
        prev = cur
    return result


def bundahishn_chapter_label(ch):
    """Label eschatological chapters of Bundahishn."""
    eschat_chapters = {
        1: "Ohrmazd's original creation; endless light",
        2: "Antagonism of the evil spirit; assault on creation",
        3: "Spiritual versus material creation",
        4: "Struggle between good and evil; cosmic battle",
        30: "On the resurrection and future existence (Frashokereti)",
        31: "On the great bundahishn - final renovation",
        32: "On the Saoshyant and renovation",
        33: "On righteous men and their reward",
        34: "The renovation of the universe (Frashokereti complete)"
    }
    return eschat_chapters.get(ch)


def main():
    print("Parsing Zand-i Vohuman Yasht...", file=sys.stderr)
    vohuman_verses = parse_vohuman(VOHUMAN_PATH)
    chapters_voh = set(int(k.split(':')[0]) for k in vohuman_verses)
    print(f"  Chapters: {len(chapters_voh)}, Verses: {len(vohuman_verses)}", file=sys.stderr)

    print("Parsing Bundahishn...", file=sys.stderr)
    bundahis_verses = parse_bundahishn(BUNDAHIS_PATH)
    chapters_bun = set(int(k.split(':')[0]) for k in bundahis_verses)
    print(f"  Chapters: {len(chapters_bun)}, Verses: {len(bundahis_verses)}", file=sys.stderr)

    print("Parsing Zamyad Yasht...", file=sys.stderr)
    zamyad_verses = parse_zamyad(ZAMYAD_PATH)
    strophes_zam = len(zamyad_verses)
    print(f"  Strophes: {strophes_zam}", file=sys.stderr)

    # Prefix keys by source to avoid collisions
    def prefix_verses(verses_dict, prefix):
        return {f"{prefix}:{k}": v for k, v in verses_dict.items()}

    all_verses = {}
    all_verses.update(prefix_verses(vohuman_verses, "vohuman"))
    all_verses.update(prefix_verses(bundahis_verses, "bundahishn"))
    all_verses.update(prefix_verses(zamyad_verses, "zamyad"))

    corpus = {
        "meta": {
            "title": "Zoroastrian Eschatological Corpus",
            "texts_included": [
                {
                    "id": "vohuman",
                    "title": "Zand-i Vohuman Yasht (Bahman Yasht / Commentary on the Vohuman Yasn)",
                    "translator": "Behramgore Tehmurasp Anklesaria (1957)",
                    "digital_edition": "Joseph H. Peterson, avesta.org, 1995 (updated 2022)",
                    "source_url": "https://avesta.org/mp/vohuman.html",
                    "original_language": "Middle Persian (Pahlavi)",
                    "approximate_date": "Pahlavi text ~9th century CE, reflecting traditions ~3rd-7th century CE",
                    "chapters": len(chapters_voh),
                    "verses": len(vohuman_verses),
                    "eschatological_themes": [
                        "Vision of the tree with four branches (gold, silver, steel, iron) = four world ages",
                        "Millennia of Zoroaster, Husedar, Husedar-mah, Soshyant",
                        "Demonic invasions and the darkening of the world",
                        "Rise of daevas and foreign dominion",
                        "The Soshyant (Saoshyant) as final savior",
                        "Frashokereti: renovation/making wonderful of the world",
                        "Defeat of Ahriman and final judgment",
                        "Resurrection of all the dead"
                    ]
                },
                {
                    "id": "bundahishn",
                    "title": "Bundahishn (Creation / Knowledge from the Zand)",
                    "translator": "E. W. West (Sacred Books of the East, vol. 5, 1897)",
                    "digital_edition": "Joseph H. Peterson, avesta.org, 1995 (updated 2022)",
                    "source_url": "https://avesta.org/mp/bundahis.html",
                    "original_language": "Middle Persian (Pahlavi)",
                    "approximate_date": "Compiled ~9th century CE, preserving much older Avestan material",
                    "chapters": len(chapters_bun),
                    "verses": len(bundahis_verses),
                    "eschatological_themes": [
                        "Ohrmazd vs Angra Mainyu (Ahriman): eternal dualism",
                        "Cosmic creation in spiritual and material forms",
                        "Six creation periods (Bundahishn = primordial creation)",
                        "The assault of evil on the good creation",
                        "Gaokerna (white haoma) tree - elixir of immortality at renovation",
                        "Frashokereti chapters (30-34): full eschatological program",
                        "Saoshyant born from seed of Zoroaster preserved in Lake Kasaoya",
                        "Resurrection of the dead (tan-i pasin = future body)",
                        "Molten metal trial - purification of all souls",
                        "Final defeat of Ahriman and the daevas",
                        "Renovation: earth becomes flat, no valleys/mountains, all dwell in joy"
                    ]
                },
                {
                    "id": "zamyad",
                    "title": "Zamyad Yasht (Yasht 19) - Hymn to the Earth / Saoshyant Prophecy",
                    "translator": "Based on Karl F. Geldner edition (Avesta: Sacred Books of the Parsis, Stuttgart, 1896)",
                    "digital_edition": "Joseph H. Peterson, avesta.org",
                    "source_url": "https://avesta.org/ka/yt19.htm",
                    "original_language": "Avestan (Old Iranian, closely related to Vedic Sanskrit)",
                    "approximate_date": "~1000-600 BCE (Younger Avestan period)",
                    "strophes": strophes_zam,
                    "eschatological_themes": [
                        "Xvarenah (divine glory/fortune) - cosmic election principle",
                        "Saoshyant (Astват-эрэta) - the future savior born of a virgin",
                        "Three Saoshyants: Ukhshyat-ereta, Ukhshyat-nemah, Astваt-эрэta",
                        "Final defeat of the Druj (lie/evil)",
                        "Earth as sacred eschatological locus - the Zamyad",
                        "Kavi Vishtaspa and the Kayanian glory",
                        "Restoration of righteous kingdom"
                    ]
                }
            ],
            "total_texts": 3,
            "total_verses": len(all_verses),
            "eschatological_significance": (
                "Zoroastrianism is the direct origin of Jewish/Christian/Islamic eschatology. "
                "Concepts of heaven and hell, resurrection of the dead, final judgment, "
                "a messianic savior (Saoshyant->Messiah->Christ->Mahdi), cosmic dualism "
                "(Ahura Mazda/Angra Mainyu -> God/Satan), and the renovation of the world "
                "(Frashokereti -> Kingdom of God -> Jannah) ALL originate here, transmitted "
                "via Jewish contact with Persian Zoroastrianism during Babylonian captivity (538 BCE+)."
            ),
            "key_eschatological_concepts": {
                "Frashokereti": "Making wonderful / renovation of the world; evil eliminated, dead resurrected, world perfected",
                "Saoshyant": "Future savior/benefactor; three in sequence; final Saoshyant Astват-эрэta makes world perfect",
                "Xvarenah": "Divine glory/kingly fortune; cosmic principle of righteous authority",
                "Asha": "Truth/righteousness/cosmic order (cf. Hebrew Emet, Sanskrit Rta)",
                "Druj": "Lie/falsehood; principle of evil; opposite of Asha",
                "Ahura Mazda": "Wise Lord; supreme good deity; cf. Hebrew El Elyon",
                "Angra Mainyu": "Destructive spirit; cf. Satan/Shaitan",
                "Ahriman": "Pahlavi form of Angra Mainyu"
            },
            "date_fetched": str(date.today()),
            "license": "Translations are public domain or freely available; digital editions by Joseph H. Peterson (avesta.org)"
        },
        "verses": all_verses
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT.stat().st_size // 1024
    print(f"\nSaved: {OUTPUT}", file=sys.stderr)
    print(f"Size: {size_kb} KB", file=sys.stderr)
    print(f"Total verses: {len(all_verses)}", file=sys.stderr)

    result = {
        "vohuman_chapters": len(chapters_voh),
        "vohuman_verses": len(vohuman_verses),
        "bundahishn_chapters": len(chapters_bun),
        "bundahishn_verses": len(bundahis_verses),
        "zamyad_strophes": strophes_zam,
        "total_verses": len(all_verses),
        "size_kb": size_kb
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
