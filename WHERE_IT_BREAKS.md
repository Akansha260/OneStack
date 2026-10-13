# Where it breaks

Every case below was run against the final code. The behaviour described is what the code actually does.

## 1. Out-of-scope question that shares a keyword gets a confident wrong answer

**Question:** "Do you charge a fee for international payments?"

**What it does:** the word "fee" routes it to the MDR handler. It returns the domestic UPI rates (0.50%/0.25%, ₹25/₹15 caps) with status `CONFLICT_RESOLVED`.

**What it should do:** return `CANNOT_ANSWER`, because no document mentions international payments.

**Why:** the router is keyword-based. It knows which topic a word belongs to, but not whether the subject of the question is inside the documents' scope. The only payment type it recognises besides UPI is the word "card". Any other payment type that mentions fee, MDR or limit gets a UPI answer.

**Don't trust it with:** questions about payment types, products or channels the documents never mention.

## 2. Questions that need two dates, or memory of an earlier question

**Question:** "Is the refund rule different on 20 Aug 2026 and 5 Sep 2026?"

**What it does:** it uses only the first date (20 Aug) and answers `ANSWERED` for that day. The only sign that 5 Sep differs is a generic heads-up sentence.

**Also:** spec Q3 says "Same merchant, a Rs.1,50,000 payment". `ask()` is stateless, so it cannot know that "same merchant" means the large merchant from Q2. It shows both merchant-size brackets instead. The large-merchant line is the correct one: ₹29.50 if the payment were processed.

**Why:** `ask(question, as_of_date)` evaluates one date per call and keeps no history. A comparison question has to be split into two calls by the caller.

**Don't trust it with:** comparisons across dates, or follow-up questions that rely on an earlier one.

## 3. Settlement and payout dates rely on an assumed holiday calendar

**Question:** "A Mumbai merchant got a UPI payment on 14 Sep 2026 (Ganesh Chaturthi). When is it settled?"

**What it does:** it treats 14 Sep as a working day and answers T+0 = Mon 14 Sep and T+1 = Tue 15 Sep.

**Why:** the policy says working days exclude bank holidays, but no document lists them. The code uses an assumed list of four national holidays (26 Jan, 15 Aug, 2 Oct, 25 Dec) in `src/calendar_utils.py`. Regional bank holidays, such as Ganesh Chaturthi in Maharashtra, are missing. When a date lands on one of the assumed holidays, the answer says it is an assumption. When it silently misses a regional holiday, it cannot warn.

**Don't trust it with:** exact settlement or closure-payout dates near regional holidays.

## Also weak

- **Amounts in words are not parsed.** "Can a customer pay me fifty thousand rupees?" falls back to a generic limits summary instead of a yes/no answer.
- **The 4.2 vs 4.3/E contradiction is a judgement call.** 4.2 allows ₹2,00,000 per transaction, but 4.3 as amended by E caps a customer at ₹1,00,000 per day. The system treats the daily limit as binding. If the business meant 4.2 to override it, those answers are wrong. The choice is flagged in every answer where it matters.
