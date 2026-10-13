"""Clause store: answers 'which clauses were in force on date X?'.

Effective dating and supersession are encoded by hand in data/clauses.json
(see DECISIONS.md). This module filters and validates; it never interprets text.
The FAQ is kept separate: active() returns policy only, faq() returns FAQ claims.
"""
import json
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "clauses.json"
POLICY_START = date(2026, 1, 1)
AUTHORITY_RANK = {"circular": 0, "master": 1}   # FAQ deliberately has no rank
REQUIRED = {"id", "doc", "clause", "authority", "topic", "text", "values",
            "effective_from", "effective_to", "superseded_by"}


def _d(s):
    return date.fromisoformat(s) if s else None


def _load_and_validate(path):
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    ids = [r.get("id") for r in rows]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate clause ids: {dupes}")
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        missing = REQUIRED - r.keys()
        if missing:
            raise ValueError(f"{r['id']}: missing fields {missing}")
        if r["authority"] not in ("master", "circular", "faq"):
            raise ValueError(f"{r['id']}: unknown authority {r['authority']}")
        start, end = _d(r["effective_from"]), _d(r["effective_to"])
        if end and end < start:
            raise ValueError(f"{r['id']}: effective_to before effective_from")
        for ref in ("superseded_by", "replaces"):
            if r.get(ref) and r[ref] not in by_id:
                raise ValueError(f"{r['id']}: {ref} points to unknown clause {r[ref]}")
        if r["superseded_by"]:
            new = by_id[r["superseded_by"]]
            if end != _d(new["effective_from"]) - timedelta(days=1):
                raise ValueError(f"{r['id']}: ends {end} but replacement starts {new['effective_from']}")
    return by_id


_CLAUSES = _load_and_validate(DATA)


def get(clause_id):
    """Look up by id. Raises KeyError for unknown ids -> no invented citations."""
    return _CLAUSES[clause_id]


def is_active(c, as_of):
    start, end = _d(c["effective_from"]), _d(c["effective_to"])
    return start <= as_of and (end is None or as_of <= end)


def active(as_of, topic=None):
    """Authoritative policy clauses (master + circular) in force on as_of. Never FAQ."""
    return [c for c in _CLAUSES.values()
            if c["authority"] != "faq" and (topic is None or c["topic"] == topic)
            and is_active(c, as_of)]


def faq(topic):
    """FAQ statements on a topic. For quoting/conflict detection only, never as policy."""
    return [c for c in _CLAUSES.values() if c["authority"] == "faq" and c["topic"] == topic]


def value(as_of, key, topic=None):
    """(value, clause) for a field from the policy clause in force on as_of.
    Circular beats master; two equal-rank clauses disagreeing is a data error."""
    hits = [c for c in active(as_of, topic) if key in c["values"]]
    if not hits:
        return None, None
    best = min(AUTHORITY_RANK[c["authority"]] for c in hits)
    top = [c for c in hits if AUTHORITY_RANK[c["authority"]] == best]
    if len({json.dumps(c["values"][key]) for c in top}) > 1:
        raise ValueError(f"conflicting values for {key} on {as_of}: {[c['id'] for c in top]}")
    return top[0]["values"][key], top[0]


def amendment_notes(clauses):
    """Human-readable notes for any circular clause used in an answer."""
    notes, seen = [], set()
    for c in clauses:
        if c and c.get("replaces") and c["id"] not in seen:
            seen.add(c["id"])
            old = _CLAUSES[c["replaces"]]
            verb = "deleted" if c["id"] == "CIRC-D" else "replaced"
            notes.append(f"Master §{old['clause']} {verb} by Circular MS/2026/17 §{c['clause']} "
                         f"effective {c['effective_from']}.")
    return notes


def cite(c):
    return f"{c['doc']} §{c['clause']}"


def policy_exists(as_of):
    return as_of >= POLICY_START