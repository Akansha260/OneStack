"""Rule-based question understanding: topic + parameters. No ML.
Anything it cannot place goes to 'unknown' -> CANNOT_ANSWER."""
import re
from datetime import date
from decimal import Decimal

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})\b", re.I)
ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
AMOUNT_RE = re.compile(r"(?P<cur>rs\.?|₹|inr)?\s*(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>lakhs?|lacs?|crores?)?", re.I)
LAKH = Decimal(100000)


def parse_date(text):
    m = ISO_RE.search(text)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = DATE_RE.search(text)
    if m:
        return date(int(m[3]), MONTHS[m[2].lower()[:3]], int(m[1]))
    return None


def _amounts(text):
    """Split money mentions into transaction amounts and monthly-volume mentions."""
    txn, size = [], None
    clean = ISO_RE.sub(" ", DATE_RE.sub(" ", text))
    for m in AMOUNT_RE.finditer(clean):
        if not (m["cur"] or m["unit"]):
            continue                                   # bare numbers: hours, counts
        v = Decimal(m["num"].replace(",", ""))
        unit = (m["unit"] or "").lower()
        if unit.startswith(("lakh", "lac")):
            v *= LAKH
        elif unit.startswith("crore"):
            v *= 100 * LAKH
        before = clean[max(0, m.start() - 30):m.start()].lower()
        after = clean[m.end():m.end() + 20].lower()
        # volume only if the money phrase is directly tied to monthly/volume wording
        if re.match(r"\s*\)?\s*(monthly|per month|a month|/month|in monthly|of monthly|monthly volume|volume|turnover)", after) \
                or re.search(r"(monthly volume|volume|turnover)\s*(of|is)?\s*(exactly\s+)?(above|over|more than|exceed\w*|up to|upto|below|under|less than|at most)?\s*$", before):
            q_above = re.search(r"(above|over|more than|exceed\w*)\s*$", before)
            q_below = re.search(r"(up to|upto|below|under|less than|at most)\s*$", before)
            ten = 10 * LAKH
            if q_above and v >= ten:
                size = "large"
            elif q_below and v <= ten:
                size = "small"
            elif not q_above and not q_below:
                size = "large" if v > ten else "small"   # "up to 10 lakh" inclusive
        else:
            txn.append(v)
    return txn, size


def parse(question):
    q = question.lower()
    txn, size = _amounts(question)
    if size is None:
        if re.search(r"\b(large|big)\s+merchant", q):
            size = "large"
        elif re.search(r"\bsmall\s+merchant", q):
            size = "small"

    hours = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?)\b", q)
    if m:
        hours = Decimal(m[1])
    elif (m := re.search(r"(\d+)\s*minutes?\b", q)):
        hours = Decimal(m[1]) / 60
    elif (m := re.search(r"(\d+)\s*days?\s+(after|later)", q)):
        hours = Decimal(m[1]) * 24
    elif re.search(r"same day|immediately|right away", q):
        hours = Decimal(0)

    count = 1
    if re.search(r"\btwice\b", q):
        count = 2
    elif re.search(r"\bthrice\b", q):
        count = 3
    elif (m := re.search(r"\b(\d+|two|three|four|five)\s+(times|payments|transactions)\b", q)):
        count = {"two": 2, "three": 3, "four": 4, "five": 5}.get(m[1], None) or int(m[1])

    instant = None
    if re.search(r"(no|not|without|don'?t have|doesn'?t have)\b[^.]{0,25}instant", q):
        instant = False
    elif "instant settlement" in q or "instant add-on" in q:
        instant = True

    kyc = None
    if re.search(r"(no|not|without|haven'?t|hasn'?t)\b[^.]{0,25}(enhanced )?kyc", q):
        kyc = False
    elif "enhanced kyc" in q:
        kyc = True

    category = None
    if "insurance" in q:
        category = "insurance"
    elif "capital market" in q:
        category = "capital markets"
    elif (m := re.search(r"\b(grocery|restaurant|retail|kirana|shop|ecommerce|e-commerce)\b", q)):
        category = m[1]

    closure_offset = None
    if "yesterday" in q:
        closure_offset = 1
    elif "today" in q:
        closure_offset = 0

    return {
        "topic": _topic(q),
        "faq": "faq" in q,
        "amount": txn[0] if txn else None,
        "size": size,
        "hours": hours,
        "count": count,
        "method": "card" if re.search(r"\bcards?\b", q) else "upi",
        "same_day": bool(re.search(r"same[- ]day|t\s*\+\s*0|instant", q)),
        "instant": instant,
        "kyc": kyc,
        "category": category,
        "closure_offset": closure_offset,
        "date_in_question": parse_date(question),
    }


def _topic(q):
    rules = [
        ("annexure", r"annexure|how (do i|to) (complete|get|do) .*kyc|kyc (documents|process|requirements)"),
        ("closure", r"\bclos(e|ed|ing|ure)\b.{0,30}account|account.{0,30}\bclos"),
        ("refund", r"\brefund"),
        ("chargeback", r"chargeback|dispute"),
        ("mdr", r"\bmdr\b|\bgst\b|\bfees?\b|discount rate|\bcap\b"),
        ("settlement", r"settle|settlement|receive\w*\b.{0,20}money|get\b.{0,15}money|credited|payout|\bt\s*\+\s*\d"),
        ("limits", r"twice|thrice|daily|per day|in one day|a day\b|\blimit|maximum|\bmax\b|how much can|can (a|the|my)? ?customer pay|accept"),
        ("mdr", r"\bpay\b|\bcost\b|\bcharged?\b"),
    ]
    for topic, pat in rules:
        if re.search(pat, q):
            return topic
    return "unknown"
