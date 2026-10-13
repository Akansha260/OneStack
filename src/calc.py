"""All money arithmetic. Decimal only, never float. Rounding: half-up to the paisa."""
from decimal import Decimal, ROUND_HALF_UP

PAISA = Decimal("0.01")


def money(x):
    return Decimal(x).quantize(PAISA, rounding=ROUND_HALF_UP)


def mdr(amount, rate, cap):
    """Returns (charged_mdr, uncapped_mdr, was_capped). Cap applied before rounding."""
    raw = Decimal(amount) * Decimal(rate)
    cap = Decimal(cap)
    return money(min(raw, cap)), money(raw), raw > cap


def gst(mdr_amount, rate):
    """Policy 2.4: GST on the MDR amount, outside the cap."""
    return money(Decimal(mdr_amount) * Decimal(rate))


def inr(x, paise=True):
    """Indian digit grouping: 150000 -> ₹1,50,000."""
    x = money(x)
    whole, frac = f"{x:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"₹{whole}.{frac}" if paise else f"₹{whole}"
