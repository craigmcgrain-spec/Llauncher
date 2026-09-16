"""Tiny fuzzy matcher: subsequence scoring with bonuses."""
from __future__ import annotations

from llauncher.models import AppEntry


def score(query: str, target: str) -> float | None:
    """Return score or None if query is not a subsequence of target.

    Scoring: start-of-string bonus, word-boundary bonus, consecutive bonus,
    shorter targets win ties.
    """
    q = query.strip().lower()
    t = target.lower()
    if not q:
        return 0.0
    if q == t:
        return 1_000.0
    if t.startswith(q):
        # strong prefix bonus, shorter name wins
        return 500.0 - len(t)
    # subsequence scan
    ti = 0
    last_match = -2
    s = 0.0
    for ch in q:
        found = t.find(ch, ti)
        if found == -1:
            return None
        if found == 0:
            s += 20.0
        elif t[found - 1] in (" ", "-", "_", "/", "."):
            s += 10.0
        if found == last_match + 1:
            s += 5.0
        else:
            s -= found * 0.1  # prefer early matches
        last_match = found
        ti = found + 1
    s -= len(t) * 0.05
    # also reward name containing query contiguously
    if q in t:
        s += 50.0
    return s


def filter_entries(query: str, entries: list[AppEntry], limit: int = 9) -> list[AppEntry]:
    q = query.strip().lower()
    if not q:
        return entries[:limit]
    scored: list[tuple[float, AppEntry]] = []
    for e in entries:
        best: float | None = None
        for cand in (e.name, e.exec_cmd):
            sc = score(q, cand)
            if sc is not None and (best is None or sc > best):
                best = sc
        if best is not None:
            scored.append((best, e))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    return [e for _, e in scored[:limit]]
