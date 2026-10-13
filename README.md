# Policy QA: grounded answers over conflicting merchant policy documents

`ask(question, as_of_date)` returns `{as_of, status, answer, citations, resolution}`.

- `status` is `ANSWERED`, `CONFLICT_RESOLVED` or `CANNOT_ANSWER`.
- `citations` are `{document, clause}` pairs.
- `resolution` says how a conflict was resolved; it is `null` otherwise.

## Run

Python 3.9+, standard library only. No install, no API key, no network.

```
python -m unittest discover -v        # 23 unit + integration tests
python eval/run_eval.py               # 21-case eval (8 adversarial), prints a score table
python -m src.ask "Can a customer pay Rs.1,00,000 twice in one day to a merchant?"
python -m src.ask "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?" --as-of 2026-09-05
```

From Python:

```python
from src.ask import ask
ask("When does a small merchant receive UPI money?", "2026-08-15")
```

The date used is chosen in this order: the `as_of_date` argument, then a date written in the question, then 15 Aug 2026.

Current results: 23/23 tests pass, and the eval scores 21/21 (8/8 adversarial).

## Layout

```
ai-2-data/             the three source documents, unchanged
data/clauses.json      every clause hand-transcribed with effective_from/to, superseded_by, numeric values
src/store.py           validates the data at load; returns the policy clauses in force on a date;
                       FAQ rows are only reachable through a separate faq() call
src/router.py          keyword/regex parsing: topic + parameters (amount, merchant size, hours, count, date)
src/ask.py             one handler per topic (settlement, fees, limits, refunds, closure, FAQ, ...)
src/calc.py            Decimal MDR/GST/cap arithmetic, rounded half-up to the paisa
src/calendar_utils.py  working days: Sundays and an assumed bank-holiday list are excluded
tests/                 store, calculator/calendar, and end-to-end tests on all 8 spec questions
eval/                  eval.json + run_eval.py
```

## Design

There is no LLM anywhere in the answer path.

- **Data.** The three documents are short. The hard part is effective dates and supersession, not reading the text. For example, Circular §D deletes 3.3 only from 1 Sep, while the rest of the circular applies from 1 Aug. So the clauses are transcribed by hand into reviewed data, and the code stays deterministic. At scale I would have an LLM draft the clause rows and a human review the dates; the store, handlers and calculators would not change.
- **Precedence.** Circular MS/2026/17 overrides Master v1.0, which overrides the FAQ. The FAQ is never authoritative. It is quoted when asked about, and flagged when it contradicts policy in a way that changes the answer.
- **Grounding.** Citations are built only from the clause rows a handler actually used, and each one is re-checked against the store. A clause number cannot be invented.
- **Arithmetic.** All of it is done with `Decimal` in code: MDR, cap, GST, limits and working days.
- **Status.** `CONFLICT_RESOLVED` means the answer depended on choosing between sources that disagree: master vs circular, FAQ vs policy, or 4.2 vs 4.3. `ANSWERED` means a single consistent source. `CANNOT_ANSWER` means no clause covers the question.

## Examples

- **Plain answer.** Q4 asked for 20 Aug 2026 returns `ANSWERED`: "Yes ... the MDR is reversed in full (§3.3)".
- **Conflict.** Q2 returns `CONFLICT_RESOLVED`: MDR ₹20.00 + GST ₹3.60 = ₹23.60. The resolution says Master §2.3 (₹15 cap) was replaced by Circular §C (₹25 cap for large merchants).
- **Date dependence.** The same refund question flips from Yes on 31 Aug to No on 1 Sep (Circular §D).
- **Abstention.** "What MDR do I pay on a card payment?" returns `CANNOT_ANSWER`, because the documents have no card MDR clause.

## What works

- All 8 spec questions, including the traps:
  - 15 Aug 2026 is a Saturday and a holiday.
  - The FAQ is wrong about the cap.
  - Q3 exceeds both the per-transaction and the daily limit.
  - Same-day card settlement is a false premise.
  - Closure counts 10 working days, minus dues.
- The 1 Aug and 1 Sep effective-date boundaries, plus the gap between the circular's issue date (20 Jul) and its effective date.
- Exactly ₹10,00,000 of monthly volume is treated as the small-merchant bracket.
- Abstention on missing information: Annexure C, card MDR, dates before 1 Jan 2026, and unknown topics.

## What doesn't

These are covered in detail in WHERE_IT_BREAKS.md:

- Keyword routing gives confident answers to some out-of-scope questions.
- Each call handles one date and has no conversation memory.
- The bank-holiday calendar is assumed.
- Amounts written in words are not parsed.

Every ambiguity and the choice made for it is in DECISIONS.md.
