"""Working-day arithmetic. Policy 1.1: working days exclude Sundays and bank holidays.

ASSUMPTION: the documents do not list bank holidays. We use national holidays
for 2026 only (see DECISIONS.md). Saturdays ARE working days per the policy text.
"""
from datetime import date, timedelta

BANK_HOLIDAYS = {
    date(2026, 1, 26): "Republic Day",
    date(2026, 8, 15): "Independence Day",
    date(2026, 10, 2): "Gandhi Jayanti",
    date(2026, 12, 25): "Christmas",
}


def non_working_reason(d):
    if d in BANK_HOLIDAYS:
        return f"bank holiday ({BANK_HOLIDAYS[d]})"
    if d.weekday() == 6:
        return "Sunday"
    return None


def is_working(d):
    return non_working_reason(d) is None


def add_working_days(d, n):
    """n=0 -> same day if working, else next working day (clause 1.3).
    n>0 -> the n-th working day strictly after d."""
    if n == 0:
        while not is_working(d):
            d += timedelta(days=1)
        return d
    count = 0
    while count < n:
        d += timedelta(days=1)
        if is_working(d):
            count += 1
    return d


def fmt(d):
    return d.strftime("%a %d %b %Y")
