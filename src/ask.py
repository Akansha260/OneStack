"""ask(question, as_of_date) -> {as_of, status, answer, citations, resolution}

Pipeline: router.parse -> pick topic handler -> handler reads clauses in force on
as_of from store -> arithmetic in calc -> result. Citations are built only from
clause rows actually used, and every id is re-checked against the store.
"""
import argparse
import json
import sys
from datetime import date, timedelta
from decimal import Decimal

from src import calc, store
from src import calendar_utils as cal
from src.router import parse

DEFAULT_AS_OF = date(2026, 8, 15)
ANSWERED, CONFLICT, CANNOT = "ANSWERED", "CONFLICT_RESOLVED", "CANNOT_ANSWER"
ENHANCED = ("insurance", "capital markets")


def _result(status, answer, clauses, resolution, as_of):
    seen, cites = set(), []
    for c in clauses:
        if c is None or c["id"] in seen:
            continue
        store.get(c["id"])                       # raises on a non-existent clause
        seen.add(c["id"])
        cites.append({"document": c["doc"], "clause": c["clause"]})
    return {"as_of": as_of.isoformat(), "status": status, "answer": answer,
            "citations": cites, "resolution": resolution}


def _status(clauses, extra=None):
    notes = store.amendment_notes(clauses) + ([extra] if extra else [])
    return (CONFLICT, " ".join(notes)) if notes else (ANSWERED, None)


def _pct(rate):
    return f"{Decimal(rate) * 100:.2f}%"


def _holiday_note(*days):
    out = []
    for d in days:
        r = cal.non_working_reason(d)
        if r and r.startswith("bank holiday"):
            out.append(f"{cal.fmt(d)} is treated as a {r}")
    if not out:
        return ""
    return (" Note: " + "; ".join(out) + ". The documents give no holiday calendar, "
            "so this uses an assumed national-holiday list.")


# ---------------- settlement ----------------
def h_settlement(p, d):
    c13 = store.get("MASTER-1.3")
    if p["method"] == "card":
        days, c12 = store.value(d, "card_days")
        on = cal.add_working_days(d, int(days))
        hol = _holiday_note(d)
        if p["same_day"]:
            cites, extra = [c12, c13], ""
            ca = store.get("CIRC-A")
            if store.is_active(ca, d):
                cites.insert(1, ca)
                extra = (" The same-day (T+0) option in Circular A §A applies only to UPI, "
                         "for merchants with the Instant Settlement add-on.")
            return _result(ANSWERED,
                           f"No. Card transactions settle T+2 (§1.2) and no clause allows same-day "
                           f"card settlement.{extra} A card payment on {cal.fmt(d)} settles on "
                           f"{cal.fmt(on)}.{hol}",
                           cites, "False premise: the policy has no same-day settlement for cards.", d)
        return _result(ANSWERED, f"Card transactions settle T+2: a payment on {cal.fmt(d)} "
                                 f"settles on {cal.fmt(on)}.{hol}", [c12, c13], None, d)

    days, src = store.value(d, "upi_days", "settlement")
    t1 = cal.add_working_days(d, int(days))
    if src["id"] == "MASTER-1.1":
        return _result(ANSWERED, f"UPI settles T+1 (next working day): a payment on {cal.fmt(d)} "
                                 f"settles on {cal.fmt(t1)}.{_holiday_note(d)}", [src, c13], None, d)
    t0 = cal.add_working_days(d, 0)
    parts = []
    if p["instant"] in (True, None):
        moved = " (same day is not a working day, so it moves to the next working day under §1.3)" \
            if t0 != d else ""
        parts.append(f"with the Instant Settlement add-on: T+0, i.e. {cal.fmt(t0)}{moved}")
    if p["instant"] in (False, None):
        parts.append(f"without the add-on: T+1, i.e. {cal.fmt(t1)}")
    lead = "Merchant size does not affect settlement. " if p["size"] else ""
    ans = f"{lead}For a UPI payment received on {cal.fmt(d)}: " + "; ".join(parts) + "." + _holiday_note(d)
    status, res = _status([src], "The FAQ's 'next working day' is incomplete since then: it ignores Instant Settlement.")
    return _result(status, ans, [src, c13], res, d)


# ---------------- limits ----------------
def limit_check(p, d, amount, count):
    per, c41 = store.value(d, "per_txn")
    enh, c42 = store.value(d, "per_txn_enhanced")
    daily, cday = store.value(d, "daily")
    c44 = store.get("MASTER-4.4")
    per, enh, daily = Decimal(per), Decimal(enh), Decimal(daily)
    bank = cday["values"].get("bank_limit_applies", False)
    inr = lambda x: calc.inr(x, paise=False)
    lines, cites, res, ok = [], [c41], None, True
    eligible = p["category"] in ENHANCED and p["kyc"] is True

    if amount > enh:
        ok = False
        cites.append(c42)
        lines.append(f"{inr(amount)} exceeds even the enhanced per-transaction limit of {inr(enh)} (§4.2), so it cannot be accepted.")
    elif amount > per:
        cites += [c42, c44]
        if eligible:
            lines.append(f"{inr(amount)} is above the standard {inr(per)} limit (§4.1) but within the {inr(enh)} limit for {p['category']} merchants with enhanced KYC (§4.2, §4.4).")
        elif (p["category"] and p["category"] not in ENHANCED) or p["kyc"] is False:
            ok = False
            lines.append(f"{inr(amount)} exceeds the {inr(per)} per-transaction limit (§4.1); the {inr(enh)} exception needs a Capital Markets/Insurance merchant with enhanced KYC (§4.2, §4.4), which this is not.")
        else:
            ok = None
            lines.append(f"{inr(amount)} exceeds the standard {inr(per)} per-transaction limit (§4.1). Only Capital Markets or Insurance merchants with completed enhanced KYC may accept up to {inr(enh)} (§4.2, §4.4); the question doesn't say, and Annexure C (the KYC criteria) is not provided.")
    else:
        each = "Each" if count > 1 else "The"
        lines.append(f"{each} {inr(amount)} payment is within the {inr(per)} per-transaction limit (§4.1).")

    total = amount * count
    cap_txt = f"{inr(daily)}, or less if the customer's own bank sets a lower limit" if bank else inr(daily)
    src = "§4.3 as amended by Circular §E" if bank else "§4.3"
    cites.append(cday)
    if total > daily:
        ok = False
        if count > 1:
            lines.append(f"But one customer can pay at most {cap_txt}, per day across all UPI payments ({src}); {count} × {inr(amount)} = {inr(total)} exceeds that, so the second payment would be declined.")
        else:
            lines.append(f"Separately, one customer can pay at most {cap_txt}, per day across all UPI payments ({src}), so a single {inr(total)} payment from one customer cannot go through.")
        if per < amount <= enh:
            res = ("§4.2 allows up to ₹2,00,000 per transaction for eligible merchants, but the "
                   "customer daily limit (§4.3/§E) is ₹1,00,000. The documents don't reconcile this; "
                   "the daily limit is treated as binding because it applies 'across all UPI transactions' "
                   "and §4.2 only raises the per-transaction ceiling.")
    elif bank:
        lines.append(f"The day's total of {inr(total)} is within ₹1,00,000, but under Circular §E the customer's bank may set a lower limit, which the documents can't tell us.")
    return ok, lines, cites, res


def h_limits(p, d):
    if p["amount"] is None:
        per, c41 = store.value(d, "per_txn")
        daily, cday = store.value(d, "daily")
        bank = cday["values"].get("bank_limit_applies", False)
        ans = (f"Per transaction: {calc.inr(per, False)} (§4.1); Capital Markets and Insurance merchants "
               f"with enhanced KYC: ₹2,00,000 (§4.2, §4.4). Per customer per day across all UPI: "
               f"{calc.inr(daily, False)}" + (", or the customer's bank limit if lower (§E)." if bank else " (§4.3)."))
        cl = [c41, store.get("MASTER-4.2"), store.get("MASTER-4.4"), cday]
        status, res = _status(cl)
        return _result(status, ans, cl, res, d)
    ok, lines, cites, extra = limit_check(p, d, p["amount"], p["count"])
    verdict = {True: "Yes.", False: "No.", None: "Only conditionally."}[ok]
    status, res = _status(cites, extra)
    return _result(status, verdict + " " + " ".join(lines), cites, res, d)


# ---------------- fees ----------------
def h_fees(p, d):
    if p["method"] == "card":
        return _result(CANNOT, "The documents set MDR only for UPI transactions; there is no clause on card MDR.", [], None, d)
    gst_rate, c24 = store.value(d, "gst_rate")
    sizes = [p["size"]] if p["size"] else ["large", "small"]
    lines, cites, extra, any_capped = [], [], None, False
    if not p["size"]:
        lines.append("Merchant size isn't stated in this question, so both brackets are shown.")
    amt = p["amount"]
    if amt is not None:
        ok, llines, lcites, extra = limit_check(p, d, amt, 1)
        if ok is not True:
            lines += llines
            cites += lcites
            lines.append("If it were processed anyway:")
    for s in sizes:
        rate, crate = store.value(d, f"rate_{s}")
        cap, ccap = store.value(d, f"cap_{s}")
        cites += [crate, ccap]
        label = "Large merchant (above ₹10 lakh/month)" if s == "large" else "Small merchant (up to ₹10 lakh/month)"
        if amt is None:
            lines.append(f"{label}: MDR {_pct(rate)} of the transaction, capped at {calc.inr(cap, False)} per transaction, plus 18% GST on the MDR.")
            continue
        m, raw, capped = calc.mdr(amt, rate, cap)
        any_capped = any_capped or capped
        g = calc.gst(m, gst_rate)
        why = (f"{_pct(rate)} would be {calc.inr(raw)}, capped at {calc.inr(cap, False)}" if capped
               else f"{_pct(rate)} of {calc.inr(amt, False)}, under the {calc.inr(cap, False)} cap")
        lines.append(f"{label}: MDR {calc.inr(m)} ({why}) + GST {calc.inr(g)} (18% of MDR) = {calc.inr(m + g)} total.")
    cites.append(c24)
    if p["size"] == "large":
        cites.insert(0, store.get("MASTER-2.2"))
    # FAQ conflict is reported only when the cap actually changed the result
    faq_note = "The FAQ (Mar 2026) says there is no upper limit on the fee; that is wrong, the cap applies."
    status, res = _status(cites, " ".join(x for x in (extra, faq_note if any_capped else None) if x) or None)
    return _result(status, " ".join(lines), cites, res, d)


# ---------------- refunds ----------------
def h_refund(p, d):
    c31, c32, c33, cd = (store.get(i) for i in ("MASTER-3.1", "MASTER-3.2", "MASTER-3.3", "CIRC-D"))
    h = p["hours"]
    if h is not None and h > 90 * 24:
        return _result(ANSWERED, "A refund can only be initiated within 90 days of the transaction (§3.1).", [c31], None, d)
    if store.is_active(cd, d):
        return _result(CONFLICT,
                       "No. From 01 Sep 2026 Circular §D deleted clause 3.3, so MDR on a refunded "
                       "transaction is not returned, however soon the refund is made (§3.2 now applies without exception).",
                       [c32, cd],
                       "Master §3.3 (24-hour MDR reversal) deleted by Circular MS/2026/17 §D effective 2026-09-01. "
                       "The FAQ (Mar 2026) still says the fee is reversed within 24 hours, which is stale.", d)
    if h is None:
        ans = "MDR is reversed in full only if the refund is initiated within 24 hours of the transaction (§3.3); otherwise it is not returned (§3.2)."
    elif h <= 24:
        ans = f"Yes. The refund is initiated {h.normalize()} hours after the sale, within 24 hours, so the MDR is reversed in full (§3.3)."
    else:
        ans = f"No. The refund comes {h.normalize()} hours after the sale, outside the 24-hour window, so the MDR is not returned (§3.2)."
    ans += " Heads-up: Circular MS/2026/17 §D removes this 24-hour exception from 01 Sep 2026."
    return _result(ANSWERED, ans, [c33, c32], None, d)


# ---------------- closure ----------------
def h_closure(p, d):
    c51, c52 = store.get("MASTER-5.1"), store.get("MASTER-5.2")
    n = c52["values"]["release_working_days"]
    res = ("The FAQ (Mar 2026) says 'within 10 days'; the Master Document says 10 working days "
           "and deducts outstanding dues first. The Master Document governs.")
    if p["closure_offset"] is None:
        ans = (f"Pending settlements are released within {n} working days of closure, after deducting "
               f"outstanding dues (§5.2). Closing requires 30 days' written notice (§5.1).")
        return _result(CONFLICT, ans, [c52, c51], res, d)
    closed = d - timedelta(days=p["closure_offset"])
    by = cal.add_working_days(closed, n)
    span = [closed + timedelta(days=i) for i in range(1, (by - closed).days)]
    ans = (f"Taking the closure date as {cal.fmt(closed)}: pending settlements will be released by "
           f"{cal.fmt(by)} at the latest ({n} working days; Sundays and bank holidays don't count), after "
           f"deducting any outstanding dues (§5.2). The amount can't be stated: it depends on your pending "
           f"settlements and dues. If you only gave notice yesterday, the account closes after 30 days' "
           f"written notice (§5.1) and the 10 working days run from then." + _holiday_note(*span))
    return _result(CONFLICT, ans, [c52, c51], res, d)


# ---------------- FAQ questions ----------------
def h_faq(p, d):
    t = p["topic"]
    faq = store.faq(t)
    if not faq:
        return _result(CANNOT, "The FAQ has no entry on this topic.", [], None, d)
    fc = faq[0]
    said = f"The FAQ (last updated 12 Mar 2026) says: \"{fc['text']}\""
    if t == "mdr":
        rs, crs = store.value(d, "rate_small")
        rl, crl = store.value(d, "rate_large")
        cs, ccs = store.value(d, "cap_small")
        cl, ccl = store.value(d, "cap_large")
        gst_rate, c24 = store.value(d, "gst_rate")
        c23 = store.get("MASTER-2.3")
        if ccl["id"] == "CIRC-C":
            cap = (f"The policy has always capped MDR per transaction: ₹15 under Master §2.3 from 01 Jan 2026, "
                   f"and since 01 Aug 2026 ₹{cs} for merchants up to ₹10 lakh/month and ₹{cl} above (Circular §C).")
        else:
            cap = "Master §2.3 caps MDR at ₹15 per transaction."
        issues = [f"It is wrong about the cap. {cap}"]
        if Decimal(rs) != Decimal("0.0030"):
            issues.append(f"It is also out of date on the small-merchant rate: {_pct(rs)} since 01 Aug 2026 (Circular §B), not 0.30%.")
        issues.append(f"The {_pct(rl)} large-merchant rate is still correct (§2.2). It also omits the 18% GST charged on top of the MDR (§2.4).")
        cl_ = [fc, c23, ccs, ccl, crs, store.get("MASTER-2.2"), c24]
        return _result(CONFLICT, said + " " + " ".join(issues), cl_,
                       "FAQ is not authoritative; Master Document and Circular MS/2026/17 govern.", d)
    if t == "refund":
        cd = store.get("CIRC-D")
        if store.is_active(cd, d):
            return _result(CONFLICT, said + " That is stale: Circular §D deleted the 24-hour reversal (§3.3) from 01 Sep 2026.",
                           [fc, cd, store.get("MASTER-3.2")], "FAQ is not authoritative.", d)
        return _result(ANSWERED, said + " That matches §3.3, which is in force until 31 Aug 2026.", [fc, store.get("MASTER-3.3")], None, d)
    if t == "settlement":
        days, src = store.value(d, "upi_days", "settlement")
        if src["id"] == "CIRC-A":
            return _result(CONFLICT, said + " That is incomplete since 01 Aug 2026: merchants with the Instant Settlement add-on get T+0 (Circular §A). Card T+2 is correct (§1.2).",
                           [fc, src, store.get("MASTER-1.2")], "FAQ is not authoritative.", d)
        return _result(ANSWERED, said + " That matches §1.1 and §1.2.", [fc, src, store.get("MASTER-1.2")], None, d)
    if t == "limits":
        daily, cday = store.value(d, "daily")
        return _result(CONFLICT, said + " That is incomplete: the ₹2,00,000 limit also requires enhanced KYC (§4.4), and there is a per-customer daily limit of ₹1,00,000" + (" or the bank's lower limit (Circular §E)." if cday["id"] == "CIRC-E" else " (§4.3)."),
                       [fc, store.get("MASTER-4.2"), store.get("MASTER-4.4"), cday], "FAQ is not authoritative.", d)
    if t == "closure":
        return _result(CONFLICT, said + " The Master Document says 10 working days, not 10 days, and deducts outstanding dues first (§5.2).",
                       [fc, store.get("MASTER-5.2")], "FAQ is not authoritative.", d)
    return _result(CANNOT, "The FAQ has no entry on this topic.", [], None, d)


def h_chargeback(p, d):
    c = store.get("MASTER-3.4")
    return _result(ANSWERED, "Chargeback disputes must be raised by the customer's bank within 120 days (§3.4).", [c], None, d)


def h_annexure(p, d):
    return _result(CANNOT, "Enhanced KYC is defined in Annexure C, which §4.4 references but which is not among the documents provided.", [], None, d)


def h_unknown(p, d):
    return _result(CANNOT, "None of the three policy documents covers this question.", [], None, d)


HANDLERS = {"settlement": h_settlement, "mdr": h_fees, "limits": h_limits, "refund": h_refund,
            "closure": h_closure, "chargeback": h_chargeback, "annexure": h_annexure}


def ask(question, as_of_date=None):
    """as_of_date: explicit argument > date written in the question > 15 Aug 2026."""
    p = parse(question)
    if as_of_date is None:
        as_of = p["date_in_question"] or DEFAULT_AS_OF
    else:
        as_of = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date
    if not store.policy_exists(as_of):
        return _result(CANNOT, f"No policy document was in force on {as_of}; the Master Document starts 01 Jan 2026.", [], None, as_of)
    if p["faq"]:
        return h_faq(p, as_of)
    return HANDLERS.get(p["topic"], h_unknown)(p, as_of)


def main():
    sys.stdout.reconfigure(encoding="utf-8")       # ₹ on Windows consoles
    ap = argparse.ArgumentParser(description="Ask the merchant policy assistant.")
    ap.add_argument("question")
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD (default: date in question, else 2026-08-15)")
    a = ap.parse_args()
    print(json.dumps(ask(a.question, a.as_of), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
