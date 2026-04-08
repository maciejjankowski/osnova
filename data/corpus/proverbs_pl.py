#!/usr/bin/env python3
"""
Polish Proverb Corpus for Osnova Steganography
Standard proverbs + variants. Deviation from standard = signal marker.

Usage:
    from data.corpus.proverbs_pl import PROVERBS, is_standard, find_deviation
"""

# Standard Polish proverbs with key words marked
# Format: (id, prefix, key_word, suffix, category)
PROVERBS = [
    (1, "Kto rano wstaje, temu", "Bog", "daje", "religion"),
    (2, "Nie wszystko zloto, co sie", "swieci", "", "appearance"),
    (3, "Nie chwal dnia przed", "zachodem", "slonca", "patience"),
    (4, "Co nagle, to po", "diable", "", "haste"),
    (5, "Gdzie kucharek szesc, tam nie ma co", "jesc", "", "coordination"),
    (6, "Kto pod kim dolki kopie, ten sam w nie", "wpada", "", "karma"),
    (7, "Lepszy wrobel w garsci niz golab na", "dachu", "", "certainty"),
    (8, "Apetyt rosnie w miare", "jedzenia", "", "greed"),
    (9, "Bez pracy nie ma", "kolaczy", "", "work"),
    (10, "Jak sobie poscielesz, tak sie", "wyspisz", "", "consequence"),
    (11, "Kto pyta, nie", "bladzi", "", "inquiry"),
    (12, "Lepiej pozno niz", "wcale", "", "timing"),
    (13, "Nie ma dymu bez", "ognia", "", "cause"),
    (14, "Nie od razu Krakow", "zbudowano", "", "patience"),
    (15, "Cicha woda", "brzegi", "rwie", "deception"),
    (16, "Czym skorupka za mlodu nasiaknie, tym na starosc", "traci", "", "habits"),
    (17, "Darowanemu koniowi nie zaglada sie w", "zeby", "", "gratitude"),
    (18, "Do odwaznych swiat", "nalezy", "", "courage"),
    (19, "Gdzie drwa robia, tam", "wiory", "leca", "consequence"),
    (20, "Gdy sie czlowiek spieszy, to sie diabol", "cieszy", "", "haste"),
    (21, "Jak Kuba Bogu, tak Bog", "Kubie", "", "reciprocity"),
    (22, "Kto pierwszy ten", "lepszy", "", "competition"),
    (23, "Madry Polak po", "szkodzie", "", "learning"),
    (24, "Na bezrybiu i rak", "ryba", "", "compromise"),
    (25, "Nie dziura piekna, ale", "latka", "", "repair"),
    (26, "Nosil wilk razy kilka, poniesli i", "wilka", "", "karma"),
    (27, "O wilku mowa, a wilk tu", "bedzie", "", "coincidence"),
    (28, "Pan Bog nierychliwy, ale", "sprawiedliwy", "", "justice"),
    (29, "Pies, ktory duzo szczeka, nie", "gryzie", "", "threats"),
    (30, "Prawdziwa cnota krytyk sie nie", "boi", "", "virtue"),
    (31, "Strzezonego Pan Bog", "strzeze", "", "caution"),
    (32, "Tonacy brzytwy sie", "chwyta", "", "desperation"),
    (33, "Trafia kosa na", "kamien", "", "resistance"),
    (34, "Wszystkie drogi prowadza do", "Rzymu", "", "convergence"),
    (35, "Z duzej chmury maly", "deszcz", "", "proportion"),
    (36, "Zgoda buduje, niezgoda", "rujnuje", "", "cooperation"),
    (37, "Ziarnko do ziarnka, a zbierze sie", "miarka", "", "accumulation"),
    (38, "Czas to", "pieniadz", "", "time"),
    (39, "Cudze chwalicie, swego nie", "znacie", "", "identity"),
    (40, "Diabla nie ma, jak go", "maluja", "", "appearance"),
]

# Regional variants (non-standard = potential signal)
VARIANTS = {
    2: [
        ("Nie wszystko zloto, co sie blyszczy", "literary variant"),
        ("Nie wszystko zloto, co lsni", "rare/poetic"),
    ],
    7: [
        ("Lepszy wrobel w reku niz golab na dachu", "hand variant"),
    ],
    15: [
        ("Cicha woda brzegi podmywa", "extended form"),
    ],
    23: [
        ("Madry Polak po fakcie", "modern variant"),
    ],
    34: [
        ("Wszystkie drogi prowadza do Krakowa", "Polish nationalist variant"),
    ],
}


def get_proverb(proverb_id: int) -> str:
    """Get full standard proverb text."""
    for pid, prefix, key, suffix, _ in PROVERBS:
        if pid == proverb_id:
            parts = [prefix, key, suffix]
            return ' '.join(p for p in parts if p).strip()
    return ""


def get_key_word(proverb_id: int) -> str:
    """Get the key word that can be substituted for steganographic signaling."""
    for pid, _, key, _, _ in PROVERBS:
        if pid == proverb_id:
            return key
    return ""


def substitute_key(proverb_id: int, new_word: str) -> str:
    """Replace key word with signal value. The substitution IS the signal."""
    for pid, prefix, _, suffix, _ in PROVERBS:
        if pid == proverb_id:
            parts = [prefix, new_word, suffix]
            return ' '.join(p for p in parts if p).strip()
    return ""


def is_standard(text: str) -> tuple[bool, int]:
    """Check if text matches a standard proverb. Returns (is_standard, proverb_id).
    If non-standard but close to a known proverb, returns (False, proverb_id).
    """
    text_lower = text.lower().strip()
    for pid, prefix, key, suffix, _ in PROVERBS:
        standard = get_proverb(pid).lower()
        if text_lower == standard:
            return (True, pid)
        # Check if it's a variant (close but not exact)
        if prefix.lower() in text_lower:
            return (False, pid)
    return (True, 0)  # Not a known proverb = not a deviation


def find_deviation(text: str) -> dict:
    """Analyze text for proverb deviations (steganographic markers).

    Returns: {proverb_id, standard_key, found_key, is_signal}
    """
    is_std, pid = is_standard(text)
    if pid == 0 or is_std:
        return {"proverb_id": pid, "is_signal": False}

    standard_key = get_key_word(pid)
    # Try to find what replaced the key word
    standard_text = get_proverb(pid).lower()
    text_lower = text.lower().strip()

    for pid2, prefix, key, suffix, _ in PROVERBS:
        if pid2 == pid:
            # Find the word in the position where key should be
            prefix_lower = prefix.lower()
            if prefix_lower in text_lower:
                remainder = text_lower.split(prefix_lower, 1)[1].strip()
                found_word = remainder.split()[0] if remainder else ""
                if found_word != key.lower():
                    return {
                        "proverb_id": pid,
                        "standard_key": key,
                        "found_key": found_word,
                        "is_signal": True,
                    }

    return {"proverb_id": pid, "is_signal": False}


def by_category(category: str) -> list[tuple[int, str]]:
    """Get all proverbs in a category."""
    return [(pid, get_proverb(pid)) for pid, _, _, _, cat in PROVERBS if cat == category]


if __name__ == "__main__":
    print("=== POLISH PROVERB CORPUS ===\n")
    print(f"Standard proverbs: {len(PROVERBS)}")
    print(f"Variant sets: {len(VARIANTS)}")

    # Show a few
    for pid in [1, 2, 7, 23, 34]:
        print(f"\n  [{pid}] {get_proverb(pid)}")
        print(f"       Key word: '{get_key_word(pid)}'")

    # Test substitution
    print("\n--- STEGANOGRAPHIC SUBSTITUTION ---")
    sig = substitute_key(2, "47")
    print(f"  Signal: {sig}")
    print(f"  Standard: {get_proverb(2)}")

    # Test deviation detection
    print("\n--- DEVIATION DETECTION ---")
    tests = [
        "Nie wszystko zloto, co sie swieci",          # standard
        "Nie wszystko zloto, co sie blyszczy",         # variant
        "Nie wszystko zloto, co sie 47",               # signal
        "Kto rano wstaje, temu Bog daje",              # standard
        "Kto rano wstaje, temu prawda daje",           # signal
    ]
    for t in tests:
        result = find_deviation(t)
        status = "SIGNAL" if result["is_signal"] else "clean"
        print(f"  [{status}] {t}")
        if result["is_signal"]:
            print(f"         Expected '{result['standard_key']}', found '{result['found_key']}'")

    print("\nAll tests complete.")
