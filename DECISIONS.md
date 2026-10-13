# Decisions

## Approach
- No LLM. Clauses hand-transcribed into `data/clauses.json` with effective dates and
  supersession links. 3 docs / ~27 entries: reviewing dates by hand is faster and more
  reliable than automated extraction. Citations can only come from ids in this file.

## Precedence
- Circular MS/2026/17 > Master v1.0 > FAQ. The FAQ is never used as a source of an
  answer; it is only quoted when it disagrees with live policy (reported as conflict).

## Effective dates
- Circular issued 20 Jul 2026 but effective 01 Aug 2026: dates 20–31 Jul use the master.
- Clause D's "(Effective 01 September 2026)" applies to all of D (deletion of 3.3).
  So 3.3 is in force up to and including 31 Aug 2026.
- Superseded master clauses get `effective_to` = day before the replacement starts.
- as_of before 01 Jan 2026: no policy existed -> CANNOT_ANSWER.
- FAQ dated 12 Mar 2026; treated as published then.

## Interpretation
- "Up to ₹10 lakh" includes exactly ₹10,00,000 (small merchant); "above" is strictly greater.
- 3.2 remains in force after 1 Sep; Circular D only removes its exception.

## Amendment semantics
- Original clause text is kept verbatim for citation; amendments are applied by the answer layer.
- 3.2 still literally says "except as provided in 3.3". From 1 Sep, refund answers cite 3.2
  together with Circular D, which together give the operative rule: no reversal, no exception.
- Circular A "replaces" 1.1, and 1.1 was where "working days exclude Sundays and bank holidays"
  was defined. A doesn't restate it, but 1.3 still uses "working day", so the definition is
  treated as carried over.
- Superseded clauses: `effective_to` = day before replacement starts; checked at load time.

## Dates
- as_of = the date of the event in the question: the payment date (settlement), the refund
  initiation date (refunds), or "today" (closure; "yesterday" = as_of - 1).
- Priority: explicit as_of argument > a date written in the question > 15 Aug 2026.
- Refund near the boundary: the rule in force on the refund date governs (sale 31 Aug 23:00,
  refund 1 Sep 02:00 -> no reversal), because the refund is the act the clause regulates.
- Bank holidays: the docs give no calendar. Assumed 2026 national holidays (26 Jan, 15 Aug,
  2 Oct, 25 Dec). Answers give a concrete date AND say it rests on this assumption, because a
  rule-only answer to "when do I get paid" is unhelpful. Saturdays are working days (policy
  excludes only Sundays and holidays).
- 15 Aug 2026 is a Saturday and Independence Day: T+0 and T+1 both land on Mon 17 Aug.

## Limits
- 4.2 allows ₹2,00,000 per transaction for eligible merchants, but 4.3/E caps a customer at
  ₹1,00,000 per day "across all UPI transactions". Unreconciled in the docs; the daily limit is
  treated as binding (4.2 only raises the per-transaction ceiling). Flagged in every such answer.
- Above ₹1,00,000 with category or KYC unknown -> not approved; the answer states the condition.
- Circular E: the bank's own limit is unknown, so answers say "at most ₹1,00,000, or less".

## Arithmetic
- Decimal only; cap applied to the exact MDR, then rounded half-up to the paisa; GST computed
  on the rounded MDR and rounded half-up. GST is outside the cap (2.4).
- Card MDR: no clause exists -> CANNOT_ANSWER, not an extrapolation from UPI rates.
- Merchant size not stated -> both brackets shown rather than guessing.

## Status definitions
- CONFLICT_RESOLVED: the answer relies on a circular clause that replaced/deleted a master
  clause, or a document disagreement had to be resolved (FAQ vs policy, 4.2 vs 4.3).
  `resolution` says which and how.
- A conflict is reported only when it changes the answer (e.g. the FAQ's 'no cap' is flagged on
  fee answers only when the cap actually binds).
- ANSWERED: single consistent source in force on as_of.
- CANNOT_ANSWER: no clause covers it (card MDR, Annexure C, dates before 1 Jan 2026, unknown topics).
