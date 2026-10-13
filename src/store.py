"""Clause store: answers 'which clauses were in force on date X?'.

Effective dating and supersession are encoded by hand in data/clauses.json
(see DECISIONS.md). This module only filters; it never interprets text.
"""
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "clauses.json"
POLICY_START = date(2026, 1, 1)

with open(DATA, encoding="utf-8") as f:
    _CLAUSES = {c["id"]: c for c in json.load(f)}


def _d(s):
    return date.fromisoformat(s) if s else None


def get(clause_id):
    """Look up by id. Raises KeyError for unknown ids -> no invented citations."""
    return _CLAUSES[clause_id]


def is_active(c, as_of):
    start, end = _d(c["effective_from"]), _d(c["effective_to"])
    return start <= as_of and (end is None or as_of <= end)


def active(as_of, topic=None, include_faq=False):
    """Authoritative clauses in force on as_of (FAQ excluded unless asked)."""
    out = []
    for c in _CLAUSES.values():
        if topic and c["topic"] != topic:
            continue
        if c["authority"] == "faq" and not include_faq:
            continue
        if is_active(c, as_of):
            out.append(c)
    return out


def value(as_of, key, topic=None):
    """Return (value, clause) for a numeric field from the clause in force.
    Circular beats master if both carry the key on the same date."""
    rank = {"circular": 0, "master": 1}
    hits = [c for c in active(as_of, topic) if key in c["values"]]
    if not hits:
        return None, None
    hits.sort(key=lambda c: rank[c["authority"]])
    return hits[0]["values"][key], hits[0]


def superseded_note(as_of, topic):
    """Master clauses on this topic replaced/deleted on or before as_of."""
    notes = []
    for c in _CLAUSES.values():
        if c["topic"] == topic and c["superseded_by"] and not is_active(c, as_of) \
                and _d(c["effective_from"]) <= as_of:
            new = _CLAUSES[c["superseded_by"]]
            notes.append(f"{cite(c)} superseded by {cite(new)} from {new['effective_from']}")
    return notes


def cite(c):
    return f"{c['doc']} §{c['clause']}"


def policy_exists(as_of):
    return as_of >= POLICY_START
