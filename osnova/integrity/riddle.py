"""
Einstein Riddle Integrity Module
osnova/integrity/riddle.py

Encodes high-integrity posts as Einstein logic puzzles.
Constraints are stored in ContentEntry.metadata.
Any node can verify integrity: if the unique solution doesn't match
the original content hash, the content has been tampered with.

Self-contained: no dependency on ~/code/zbigniew-protocol/.
Core logic inlined and adapted for content-phrase encoding.
"""

from __future__ import annotations

import hashlib
import random
import string
from typing import Optional


# ---------------------------------------------------------------------------
# THEMED VOCABULARIES (camouflage dimensions)
# ---------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "default": {
        "description": "Classic Einstein riddle (nationalities, colors, drinks, pets)",
        "dimensions": {
            "nationality": [
                "english", "swede", "dane", "norwegian", "german",
                "polish", "french", "italian", "spanish", "dutch",
            ],
            "color": [
                "red", "green", "blue", "yellow", "white",
                "ivory", "amber", "slate", "copper", "silver",
            ],
            "drink": [
                "tea", "coffee", "milk", "beer", "water",
                "wine", "juice", "mead", "cider", "sake",
            ],
            "pet": [
                "dog", "cat", "bird", "fish", "horse",
                "snake", "rabbit", "turtle", "parrot", "hamster",
            ],
        },
        "slot_label": "House",
    },
    "embassy": {
        "description": "Diplomatic gifts and cultural elements",
        "dimensions": {
            "origin": [
                "persia", "poland", "japan", "egypt", "india",
                "china", "turkey", "georgia", "armenia", "morocco",
            ],
            "gift": [
                "amber", "silk", "pottery", "spice", "tea",
                "jade", "linen", "copper", "silver", "wheat",
            ],
            "flower": [
                "lily", "rose", "iris", "tulip", "orchid",
                "jasmine", "lotus", "peony", "dahlia", "poppy",
            ],
            "greeting": [
                "salam", "shalom", "namaste", "peace", "aman",
                "merhaba", "ahlan", "jambo", "hola", "ciao",
            ],
        },
        "slot_label": "Delegation",
    },
    "military": {
        "description": "Intelligence briefing elements",
        "dimensions": {
            "unit": [
                "alpha", "bravo", "charlie", "delta", "echo",
                "foxtrot", "golf", "hotel", "india", "juliet",
            ],
            "terrain": [
                "forest", "mountain", "river", "desert", "coast",
                "marsh", "plains", "valley", "ridge", "canyon",
            ],
            "time": [
                "dawn", "morning", "noon", "dusk", "midnight",
                "sunrise", "sunset", "twilight", "predawn", "midday",
            ],
            "weather": [
                "clear", "fog", "rain", "storm", "snow",
                "wind", "haze", "frost", "mist", "sleet",
            ],
        },
        "slot_label": "Position",
    },
    "masonic": {
        "description": "Masonic symbols and traditions",
        "dimensions": {
            "stone": [
                "ashlar_rough", "ashlar_smooth", "keystone", "cornerstone", "capstone",
                "marble", "granite", "limestone", "sandstone", "basalt",
            ],
            "tool": [
                "square", "compass", "level", "plumb", "trowel",
                "gavel", "chisel", "mallet", "ruler", "pencil",
            ],
            "virtue": [
                "prudence", "temperance", "fortitude", "justice", "faith",
                "hope", "charity", "truth", "wisdom", "beauty",
            ],
            "degree": [
                "entered", "fellow", "master", "mark", "royal_arch",
                "select", "super_excellent", "knight", "prince", "sovereign",
            ],
        },
        "slot_label": "Station",
    },
}


# ---------------------------------------------------------------------------
# INLINE SOLVER (backtracking CSP, no external dependency)
# ---------------------------------------------------------------------------

class _Solver:
    """
    Minimal backtracking CSP solver.
    Dimensions: {dim_name: [instance, ...]}
    Constraints: list of callables (assignment: dict) -> bool
    Assignment: {(dim, instance): slot_int}
    """

    def __init__(self, dimensions: dict, size: int):
        self.size = size
        self.dimensions = dimensions
        self.variables: dict[tuple, set] = {
            (d, i): set(range(1, size + 1))
            for d in dimensions
            for i in dimensions[d]
        }

    def _consistent(self, assignment: dict, constraints: list) -> bool:
        # Uniqueness within each dimension
        for d in self.dimensions:
            vals = [v for (dd, _), v in assignment.items() if dd == d]
            if len(vals) != len(set(vals)):
                return False
        # User constraints
        for fn in constraints:
            if not fn(assignment):
                return False
        return True

    def _backtrack(self, assignment: dict, constraints: list) -> Optional[dict]:
        if len(assignment) == len(self.variables):
            return dict(assignment)
        unassigned = [v for v in self.variables if v not in assignment]
        var = min(unassigned, key=lambda v: len(self.variables[v]))
        for value in sorted(self.variables[var]):
            assignment[var] = value
            if self._consistent(assignment, constraints):
                result = self._backtrack(assignment, constraints)
                if result is not None:
                    return result
            del assignment[var]
        return None

    def solve(self, constraints: list) -> Optional[dict]:
        return self._backtrack({}, constraints)

    def solve_all(self, constraints: list, max_solutions: int = 10) -> list:
        solutions: list = []
        self._backtrack_all({}, constraints, solutions, max_solutions)
        return solutions

    def _backtrack_all(self, assignment: dict, constraints: list,
                       solutions: list, max_solutions: int) -> None:
        if len(solutions) >= max_solutions:
            return
        if len(assignment) == len(self.variables):
            solutions.append(dict(assignment))
            return
        unassigned = [v for v in self.variables if v not in assignment]
        var = min(unassigned, key=lambda v: len(self.variables[v]))
        for value in sorted(self.variables[var]):
            assignment[var] = value
            if self._consistent(assignment, constraints):
                self._backtrack_all(assignment, constraints, solutions, max_solutions)
            del assignment[var]


# ---------------------------------------------------------------------------
# CONSTRAINT HELPERS (pure functions over assignment dicts)
# ---------------------------------------------------------------------------

def _same_slot(dim_a: str, inst_a: str, dim_b: str, inst_b: str):
    def fn(a):
        ka, kb = (dim_a, inst_a), (dim_b, inst_b)
        if ka in a and kb in a:
            return a[ka] == a[kb]
        return True
    return fn


def _fixed_slot(dim: str, inst: str, slot: int):
    def fn(a):
        k = (dim, inst)
        if k in a:
            return a[k] == slot
        return True
    return fn


def _adjacent_slots(dim_a: str, inst_a: str, dim_b: str, inst_b: str):
    def fn(a):
        ka, kb = (dim_a, inst_a), (dim_b, inst_b)
        if ka in a and kb in a:
            return abs(a[ka] - a[kb]) == 1
        return True
    return fn


def _ordered(dim_a: str, inst_a: str, dim_b: str, inst_b: str):
    def fn(a):
        ka, kb = (dim_a, inst_a), (dim_b, inst_b)
        if ka in a and kb in a:
            return a[ka] < a[kb]
        return True
    return fn


def _slot_range(dim: str, inst: str, lo: int, hi: int):
    def fn(a):
        k = (dim, inst)
        if k in a:
            return lo <= a[k] <= hi
        return True
    return fn


# ---------------------------------------------------------------------------
# CONSTRAINT SERIALIZATION
# ---------------------------------------------------------------------------

def _constraints_to_fns(constraints_data: list) -> list:
    fns = []
    for c in constraints_data:
        t = c["type"]
        if t == "same_slot":
            fns.append(_same_slot(c["dim_a"], c["inst_a"], c["dim_b"], c["inst_b"]))
        elif t == "fixed":
            fns.append(_fixed_slot(c["dim"], c["inst"], c["slot"]))
        elif t == "adjacent":
            fns.append(_adjacent_slots(c["dim_a"], c["inst_a"], c["dim_b"], c["inst_b"]))
        elif t == "ordered":
            fns.append(_ordered(c["dim_a"], c["inst_a"], c["dim_b"], c["inst_b"]))
        elif t == "range":
            fns.append(_slot_range(c["dim"], c["inst"], c["min"], c["max"]))
    return fns


# ---------------------------------------------------------------------------
# CONTENT -> RIDDLE ENCODING
# ---------------------------------------------------------------------------

def _extract_phrases(body: str, max_phrases: int = 6) -> list[str]:
    """
    Split body into key phrases (lines or sentences).
    Cap at max_phrases to keep riddle tractable.
    Returns at least 2 phrases (padded with hash-derived sentinels if needed).
    """
    # Try lines first
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    if len(lines) >= 2:
        phrases = lines[:max_phrases]
    else:
        # Fall back to sentence splitting on ". "
        sentences = [s.strip() for s in body.replace("? ", ". ").replace("! ", ". ").split(". ") if s.strip()]
        phrases = sentences[:max_phrases]

    if len(phrases) < 2:
        # Pad: split body into char chunks as last resort
        chunk = max(1, len(body) // 2)
        phrases = [body[i:i + chunk] for i in range(0, len(body), chunk)][:max_phrases]

    if len(phrases) < 2:
        phrases = [body, hashlib.sha256(body.encode()).hexdigest()[:8]]

    return phrases


def _phrase_to_signal_token(phrase: str, idx: int, vocab: list) -> str:
    """
    Map a phrase to a vocab token deterministically via sha256.
    Uses idx as a salt so identical phrases at different positions differ.
    """
    digest = hashlib.sha256(f"{idx}:{phrase}".encode()).hexdigest()
    token_idx = int(digest[:8], 16) % len(vocab)
    return vocab[token_idx]


def _all_constraints(assignment: dict, dim_names: list, size: int) -> list:
    """Generate all valid constraints from a known full assignment."""
    constraints = []
    assigned: dict[str, list] = {}
    for (dim, inst), slot in assignment.items():
        assigned.setdefault(dim, []).append((inst, slot))

    # same_slot (cross-dimension co-location)
    for i, da in enumerate(dim_names):
        for db in dim_names[i + 1:]:
            for inst_a, sa in assigned.get(da, []):
                for inst_b, sb in assigned.get(db, []):
                    if sa == sb:
                        constraints.append({
                            "type": "same_slot",
                            "dim_a": da, "inst_a": inst_a,
                            "dim_b": db, "inst_b": inst_b,
                        })

    # adjacent
    for i, da in enumerate(dim_names):
        for db in dim_names[i + 1:]:
            for inst_a, sa in assigned.get(da, []):
                for inst_b, sb in assigned.get(db, []):
                    if abs(sa - sb) == 1:
                        constraints.append({
                            "type": "adjacent",
                            "dim_a": da, "inst_a": inst_a,
                            "dim_b": db, "inst_b": inst_b,
                        })

    # ordered (within same dimension)
    for dim in dim_names:
        instances = assigned.get(dim, [])
        for j, (ia, sa) in enumerate(instances):
            for ib, sb in instances[j + 1:]:
                if sa < sb:
                    constraints.append({"type": "ordered", "dim_a": dim, "inst_a": ia, "dim_b": dim, "inst_b": ib})
                elif sb < sa:
                    constraints.append({"type": "ordered", "dim_a": dim, "inst_a": ib, "dim_b": dim, "inst_b": ia})

    # fixed_slot (pins exact position)
    for dim in dim_names:
        for inst, slot in assigned.get(dim, []):
            constraints.append({"type": "fixed", "dim": dim, "inst": inst, "slot": slot})

    # range (looser than fixed)
    for dim in dim_names:
        for inst, slot in assigned.get(dim, []):
            if slot > 1:
                constraints.append({
                    "type": "range", "dim": dim, "inst": inst,
                    "min": max(1, slot - 1), "max": min(size, slot + 1),
                })

    return constraints


def encode_content(body: str, theme: str = "default", seed: Optional[int] = None) -> dict:
    """
    Encode a post body as an Einstein riddle.

    Extracts key phrases from body, maps each to a position in the riddle,
    generates a constraint set with a unique solution, and returns a metadata
    dict suitable for ContentEntry.metadata.

    Returns:
        {
            "riddle_constraints": [...],   # serializable list of constraint dicts
            "riddle_instances": {...},      # {dim: [instance, ...]} for solver reconstruction
            "riddle_size": int,             # number of slots = number of phrases
            "theme": str,
            "expected_solution_hash": str, # sha256 of canonical solution string
            "phrase_order_hash": str,       # sha256(joined phrases) - integrity anchor
            "encoded": True,
        }
    """
    if seed is not None:
        random.seed(seed)
    else:
        # Deterministic seed derived from content so same body -> same riddle
        random.seed(int(hashlib.sha256(body.encode()).hexdigest()[:8], 16))

    theme_data = THEMES.get(theme)
    if theme_data is None:
        raise ValueError(f"Unknown theme '{theme}'. Available: {list(THEMES.keys())}")

    phrases = _extract_phrases(body)
    size = len(phrases)

    dim_names = list(theme_data["dimensions"].keys())
    # First dimension = signal (carries phrase position mapping)
    signal_dim = dim_names[0]
    signal_vocab = theme_data["dimensions"][signal_dim]

    # Build full assignment
    # Signal dimension: phrase i -> deterministic token -> slot (i+1)
    assignment: dict[tuple, int] = {}
    signal_instances: list[str] = []
    used_tokens: set[str] = set()

    for i, phrase in enumerate(phrases):
        # Find a unique token for this phrase
        vocab_copy = signal_vocab[:]
        token = _phrase_to_signal_token(phrase, i, vocab_copy)
        # Guarantee uniqueness within signal dim
        attempts = 0
        while token in used_tokens and attempts < len(vocab_copy):
            token = vocab_copy[(vocab_copy.index(token) + 1) % len(vocab_copy)]
            attempts += 1
        used_tokens.add(token)
        signal_instances.append(token)
        assignment[(signal_dim, token)] = i + 1  # slot is 1-indexed

    # Camouflage dimensions: random permutations
    for dim in dim_names[1:]:
        pool = theme_data["dimensions"][dim][:size]
        shuffled = pool[:]
        random.shuffle(shuffled)
        for j, inst in enumerate(shuffled):
            assignment[(dim, inst)] = j + 1

    # Build solver dimensions dict (only instances we actually use)
    solver_dims: dict[str, list] = {}
    solver_dims[signal_dim] = signal_instances[:]
    for dim in dim_names[1:]:
        solver_dims[dim] = [inst for (d, inst) in assignment if d == dim]

    # Generate constraints, then solve to verify uniqueness
    all_c = _all_constraints(assignment, dim_names, size)
    random.shuffle(all_c)

    # Start with ~50% of constraints (medium difficulty)
    target = max(size, len(all_c) // 2)
    working_constraints = all_c[:target]

    solver = _Solver(solver_dims, size)
    fns = _constraints_to_fns(working_constraints)
    solutions = solver.solve_all(fns, max_solutions=2)

    # Add constraints until unique
    extra_idx = target
    attempts = 0
    while len(solutions) != 1 and extra_idx < len(all_c) and attempts < 200:
        c = all_c[extra_idx]
        extra_idx += 1
        if c not in working_constraints:
            working_constraints.append(c)
            fns = _constraints_to_fns(working_constraints)
            solutions = solver.solve_all(fns, max_solutions=2)
            attempts += 1

    if len(solutions) != 1:
        raise RuntimeError(
            f"Could not generate a unique-solution riddle for this content "
            f"(got {len(solutions)} solutions after {attempts} attempts). "
            f"Try a different theme or content."
        )

    solution = solutions[0]

    # Canonical solution string: "dim:inst=slot," sorted by key
    solution_str = ",".join(
        f"{d}:{i}={s}"
        for (d, i), s in sorted(solution.items(), key=lambda x: (x[0][0], x[0][1]))
    )
    expected_solution_hash = hashlib.sha256(solution_str.encode()).hexdigest()

    # Phrase order anchor: what we're actually protecting
    phrase_order_hash = hashlib.sha256("\n".join(phrases).encode()).hexdigest()

    return {
        "riddle_constraints": working_constraints,
        "riddle_instances": solver_dims,
        "riddle_size": size,
        "theme": theme,
        "expected_solution_hash": expected_solution_hash,
        "phrase_order_hash": phrase_order_hash,
        "encoded": True,
    }


# ---------------------------------------------------------------------------
# VERIFICATION
# ---------------------------------------------------------------------------

def verify_content_integrity(body: str, metadata: dict) -> bool:
    """
    Verify that body matches the riddle constraints stored in metadata.

    Returns True if:
    - metadata does not have "encoded": True  (unencoded content is always valid)
    - the riddle has a unique solution AND the solution hash matches expected

    Returns False if content has been tampered with.
    """
    if not metadata.get("encoded", False):
        return True

    constraints_data = metadata.get("riddle_constraints")
    instances = metadata.get("riddle_instances")
    size = metadata.get("riddle_size")
    expected_hash = metadata.get("expected_solution_hash")
    phrase_order_hash = metadata.get("phrase_order_hash")

    if not all([constraints_data, instances, size, expected_hash, phrase_order_hash]):
        # Malformed metadata - treat as tampered
        return False

    # Re-derive phrases from body and check phrase_order_hash
    phrases = _extract_phrases(body, max_phrases=size)
    # Trim/pad to stored size
    phrases = phrases[:size]
    actual_phrase_hash = hashlib.sha256("\n".join(phrases).encode()).hexdigest()
    if actual_phrase_hash != phrase_order_hash:
        return False

    # Run the solver
    solver = _Solver(instances, size)
    fns = _constraints_to_fns(constraints_data)
    solutions = solver.solve_all(fns, max_solutions=2)

    if len(solutions) != 1:
        return False

    solution = solutions[0]
    solution_str = ",".join(
        f"{d}:{i}={s}"
        for (d, i), s in sorted(solution.items(), key=lambda x: (x[0][0], x[0][1]))
    )
    actual_hash = hashlib.sha256(solution_str.encode()).hexdigest()
    return actual_hash == expected_hash


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def list_themes() -> list[str]:
    """Return available theme names."""
    return list(THEMES.keys())
