#!/usr/bin/env python3
"""
Parse Book of Enoch (R.H. Charles 1917 translation) from Project Gutenberg text.
Produces enoch_corpus.json in osnova corpus format.

Structure:
  Chapter: "VI. 1. First verse text. 2. Second verse..."
  Verses are inline with numbers like "2." "3." embedded in prose paragraphs.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

INPUT = "/tmp/enoch_raw.txt"
OUTPUT = Path("/Users/mj/code/osnova/data/corpus/enoch_corpus.json")

# Roman numeral to int
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

ROMAN_PAT = r'(?:M{0,4})(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'

def clean_text(t):
    """Clean verse text of editorial marks and normalize whitespace."""
    # Remove special editorial brackets/marks
    t = re.sub(r'[〚〛⌜⌝]', '', t)
    t = re.sub(r'[†‹›=]', '', t)
    # Remove footnote markers like [1]
    t = re.sub(r'\[\d+\]', '', t)
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def parse_enoch(raw_text):
    # Strip gutenberg header/footer
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK THE BOOK OF ENOCH ***"
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK THE BOOK OF ENOCH ***"
    start_idx = raw_text.find(start_marker)
    end_idx = raw_text.find(end_marker)
    if start_idx != -1:
        body = raw_text[start_idx + len(start_marker):end_idx if end_idx != -1 else None]
    else:
        body = raw_text

    # Find the actual content start: first "I. 1." line
    match = re.search(r'^I\.\s+1\.', body, re.MULTILINE)
    if match:
        body = body[match.start():]

    # Collapse the whole body to a single stream for easier parsing
    # But we need to handle multi-line chapters
    # Strategy: find all chapter starts (Roman numeral at line start)
    # then find all verse numbers within each chapter

    # Step 1: Split into chapter blocks
    # Chapter boundary: line starting with (optional whitespace) Roman numeral followed by ". N. "
    # Some chapters are indented with spaces (e.g. "    XLVIII. 1. ...")
    chapter_start_pat = re.compile(
        r'^\s*(' + ROMAN_PAT + r')\.\s+(\d+)\.\s+',
        re.MULTILINE
    )

    # Also handle chapters with NO inline verse numbers: "III. Observe..." (no "1.")
    # Pattern: Roman numeral at line start (with optional indent) followed directly by text
    # NOT followed by a digit+period (that's handled above)
    unnumbered_chapter_pat = re.compile(
        r'^\s*(' + ROMAN_PAT + r')\.\s+(?!\d+\.\s)([A-Z][^\n]{5,})',
        re.MULTILINE
    )

    # Find all potential chapter starts
    chapter_starts = list(chapter_start_pat.finditer(body))
    print(f"Found {len(chapter_starts)} numbered-verse chapter starts", file=sys.stderr)

    # Add unnumbered chapters
    unnumbered = list(unnumbered_chapter_pat.finditer(body))
    print(f"Found {len(unnumbered)} unnumbered chapter starts", file=sys.stderr)

    # Merge and sort all chapter starts by position
    all_chapter_starts = []
    for m in chapter_starts:
        roman_str = m.group(1)
        ch_num = roman_to_int(roman_str)
        all_chapter_starts.append(('numbered', ch_num, m.start(), m.end(), m))
    for m in unnumbered:
        roman_str = m.group(1)
        ch_num = roman_to_int(roman_str)
        # Only add if not already covered by numbered pattern
        pos = m.start()
        already_covered = any(abs(pos - s[2]) < 5 for s in all_chapter_starts)
        if not already_covered and 0 < ch_num <= 108:
            all_chapter_starts.append(('unnumbered', ch_num, pos, m.end(), m))

    # Sort by position in document
    all_chapter_starts.sort(key=lambda x: x[2])
    print(f"Total chapter starts (merged): {len(all_chapter_starts)}", file=sys.stderr)

    verses = {}

    for ch_idx, ch_entry in enumerate(all_chapter_starts):
        ch_type, chapter_num, pos_start, pos_end, ch_match = ch_entry
        if chapter_num == 0 or chapter_num > 108:
            continue

        # Get chapter block text: from this chapter start to next chapter start
        next_pos = all_chapter_starts[ch_idx + 1][2] if ch_idx + 1 < len(all_chapter_starts) else len(body)
        block_text = body[pos_start:next_pos]

        # Remove the leading "ROMAN. [N. ]" prefix
        block_text = re.sub(r'^\s*' + ROMAN_PAT + r'\.\s+', '', block_text, count=1)

        # Strip section annotation lines like "LXXXIX. 51-67. _The Two Kingdoms..."
        block_text = re.sub(r'\n\s*' + ROMAN_PAT + r'\.\s+\d+[-\d]+\.\s+_[^\n]*\n', '\n', block_text)

        if ch_type == 'unnumbered':
            # Chapter has no verse numbers - entire text is verse 1
            cleaned = clean_text(block_text)
            if cleaned and len(cleaned.split()) >= 3:
                key = f"{chapter_num}:1"
                words = cleaned.split()
                verses[key] = {"text": cleaned, "words": words, "word_count": len(words)}
            continue

        # Numbered chapter: parse inline verse markers "N. text"
        inline_verse_pat = re.compile(r'(?:^|\s+)(\d+)\.\s+')
        positions = []
        for m in inline_verse_pat.finditer(block_text):
            vn = int(m.group(1))
            if 1 <= vn <= 200:
                positions.append((vn, m.start(), m.end()))

        if not positions:
            # Fallback: treat whole block as verse 1
            cleaned = clean_text(block_text)
            if cleaned and len(cleaned.split()) >= 3:
                key = f"{chapter_num}:1"
                words = cleaned.split()
                verses[key] = {"text": cleaned, "words": words, "word_count": len(words)}
            continue

        for p_idx, (vn, v_pos_start, v_pos_end) in enumerate(positions):
            next_v_start = positions[p_idx + 1][1] if p_idx + 1 < len(positions) else len(block_text)
            verse_text = block_text[v_pos_end:next_v_start]
            cleaned = clean_text(verse_text)

            if cleaned and len(cleaned.split()) >= 2:
                key = f"{chapter_num}:{vn}"
                words = cleaned.split()
                verses[key] = {"text": cleaned, "words": words, "word_count": len(words)}

    return verses


def classify_section(chapter_num):
    if 1 <= chapter_num <= 5:
        return "Prologue"
    elif 6 <= chapter_num <= 36:
        return "Book of Watchers"
    elif 37 <= chapter_num <= 71:
        return "Book of Parables (Similitudes)"
    elif 72 <= chapter_num <= 82:
        return "Astronomical Book (Book of Luminaries)"
    elif 83 <= chapter_num <= 90:
        return "Book of Dream Visions"
    elif 91 <= chapter_num <= 108:
        return "Epistle of Enoch"
    else:
        return "Unknown"


def main():
    raw = Path(INPUT).read_text(encoding='utf-8', errors='replace')
    print(f"Raw text size: {len(raw)} bytes", file=sys.stderr)

    verses = parse_enoch(raw)
    print(f"Total verses parsed: {len(verses)}", file=sys.stderr)

    chapters = set()
    for key in verses:
        ch = int(key.split(':')[0])
        chapters.add(ch)
    print(f"Chapters found: {len(chapters)}, range {min(chapters)}-{max(chapters)}", file=sys.stderr)

    section_counts = {}
    for key in verses:
        ch = int(key.split(':')[0])
        sec = classify_section(ch)
        section_counts[sec] = section_counts.get(sec, 0) + 1

    # Sample a few verses for sanity check
    sample_keys = ["1:1", "6:1", "6:2", "10:1", "37:1", "48:1", "108:1"]
    for sk in sample_keys:
        if sk in verses:
            preview = verses[sk]["text"][:80]
            print(f"  Sample {sk}: {preview}...", file=sys.stderr)

    corpus = {
        "meta": {
            "title": "The Book of Enoch (1 Enoch)",
            "translator": "R. H. Charles, D.Litt., D.D.",
            "contributor": "W. O. E. Oesterley, D.D. (Introduction)",
            "source": "Project Gutenberg eBook #77935 / Originally: Society for Promoting Christian Knowledge, London, 1917",
            "original_language": "Ethiopic (Ge'ez), with Aramaic and Hebrew fragments (Dead Sea Scrolls)",
            "approximate_date": "~300 BCE compiled; oldest sections (Book of Luminaries) ~4th century BCE",
            "canonical_in": "Ethiopian Orthodox Tewahedo Church; Dead Sea Scrolls confirm pre-Christian circulation",
            "not_canonical_in": "Most Protestant, Catholic, and Eastern Orthodox traditions (deuterocanonical/pseudepigraphical)",
            "historical_significance": (
                "Directly quoted in Jude 1:14-15 (NT). Profoundly influenced NT Christology (Son of Man). "
                "Contains fullest development of angelology/demonology in Second Temple Judaism. "
                "The Watchers narrative (fallen angels) became foundational for all subsequent demonology."
            ),
            "eschatological_themes": [
                "Watchers / fallen angels (Shemhazah, Azazel) - origin of evil on earth",
                "Nephilim - hybrid giants offspring of angels and human women",
                "Heavenly tablets and divine judgment pre-ordained",
                "Son of Man - pre-existent messianic figure (antecedent of NT Son of Man)",
                "Final judgment of the wicked, vindication of the righteous",
                "Resurrection of the dead",
                "New Jerusalem / new creation after judgment",
                "Astronomical order as divine covenant (364-day solar calendar)",
                "Weeks Apocalypse (93:1-10) - 10-week history of the world",
                "Descent to Sheol and the four compartments of the dead",
                "Enoch as heavenly scribe / mediator / intercessor",
                "The Great Flood as type of final judgment",
                "Binding of Azazel under the desert until judgment day"
            ],
            "sections": {
                "Prologue": {
                    "chapters": "1-5",
                    "theme": "Introduction; cosmic order preserved; judgment announced against the wicked"
                },
                "Book of Watchers": {
                    "chapters": "6-36",
                    "theme": "Fall of Watchers; Enoch's intercession; heavenly journeys; cosmic geography"
                },
                "Book of Parables (Similitudes)": {
                    "chapters": "37-71",
                    "theme": "Three parables on judgment; Son of Man; heavenly throne room; final judgment"
                },
                "Astronomical Book (Book of Luminaries)": {
                    "chapters": "72-82",
                    "theme": "364-day solar calendar; heavenly luminaries governed by Uriel; cosmic covenant"
                },
                "Book of Dream Visions": {
                    "chapters": "83-90",
                    "theme": "Animal apocalypse: full history of Israel from Adam through Maccabean revolt"
                },
                "Epistle of Enoch": {
                    "chapters": "91-108",
                    "theme": "Woes against oppressors; Apocalypse of Weeks; resurrection; Noah birth narrative"
                }
            },
            "total_chapters": len(chapters),
            "total_verses": len(verses),
            "section_verse_counts": section_counts,
            "date_fetched": str(date.today()),
            "license": "Public domain (1917 translation; Project Gutenberg eBook #77935)"
        },
        "verses": verses
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT.stat().st_size // 1024
    print(f"\nSaved: {OUTPUT}", file=sys.stderr)
    print(f"Size: {size_kb} KB", file=sys.stderr)
    print(f"Chapters: {len(chapters)}", file=sys.stderr)
    print(f"Verses: {len(verses)}", file=sys.stderr)
    print(json.dumps({"chapters": len(chapters), "verses": len(verses), "size_kb": size_kb}))

if __name__ == "__main__":
    main()
