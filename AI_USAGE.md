# AI usage

## Tools

- **Claude (chat assistant):** used throughout the hour as the main coding assistant.
- **A second AI assistant:** used once, to review an early version of the code.

## What Claude did

- **Planning.** Proposed the architecture: rule-based and offline, with no LLM in the answer path, hand-transcribed clause data, and a separate Decimal calculator. Also proposed the four-commit plan.
- **Document analysis.** Listed the conflicts and traps across the three documents, for example:
  - the stale FAQ cap;
  - Circular §D taking effect on 1 Sep while the rest of the circular starts 1 Aug;
  - 15 Aug 2026 being a Saturday and a holiday;
  - the 4.2 vs 4.3 limit contradiction;
  - Circular §A replacing 1.1, which is where "working days" was defined.
- **Code.** Drafted `data/clauses.json`, every module in `src/`, the tests, `eval/eval.json` and `eval/run_eval.py`.
- **Documentation.** Drafted DECISIONS.md, README.md, WHERE_IT_BREAKS.md and this file.

## What I did

- Set up the repository structure and the git workflow, and made the commits.
- Checked the clause rows in `clauses.json` (ids, effective dates, supersession) against the source documents.
- Ran the tests (23/23) and the eval (21/21) locally before each commit.
- Ran the CLI on the spec questions to check the answers, including the refund rule on 31 Aug vs 1 Sep.
- Reviewed the second AI's feedback and decided which points to act on.

## Review feedback: what I adopted and rejected

**Adopted:**
- FAQ rows kept on a separate code path from policy clauses.
- Data validated when the store loads.
- "At most ₹1,00,000, or lower if the customer's bank sets a lower limit" wording for the daily limit.
- Integration tests that check final answers, not just which clauses are active.
- Softer daily-limit wording: the policy sets a limit but doesn't say which payment gets declined.

**Rejected:**
- A full amendment-operation schema (replace/amend/delete). Too much for five amendments.
- Downgrading master-vs-circular answers from `CONFLICT_RESOLVED` to `ANSWERED`. Those are genuine disagreements between documents.
- A reported "canpay" typo. It was terminal line-wrapping; the source text was already correct.

**Bugs the eval caught and I fixed:**
- A ₹4,000 transaction amount was misread as a monthly volume.
- The FAQ cap conflict was flagged even when the cap didn't affect the answer.

## Not verified

- A real bank-holiday calendar. An assumed national list is used; see WHERE_IT_BREAKS.md.
