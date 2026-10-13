import unittest
from datetime import date
from decimal import Decimal
from src import calc
from src import calendar_utils as cal


class TestCalc(unittest.TestCase):
    def test_q2_large_4000(self):
        m, raw, capped = calc.mdr(4000, "0.0050", "25")
        self.assertEqual((m, calc.gst(m, "0.18"), capped), (Decimal("20.00"), Decimal("3.60"), False))

    def test_cap_and_gst_outside_cap(self):
        m, raw, capped = calc.mdr(150000, "0.0050", "25")
        self.assertEqual((m, raw, capped), (Decimal("25.00"), Decimal("750.00"), True))
        self.assertEqual(calc.gst(m, "0.18"), Decimal("4.50"))     # GST on top of capped MDR

    def test_half_up_rounding(self):
        m, _, _ = calc.mdr(1, "0.0025", "15")          # 0.0025 -> 0.00
        self.assertEqual(m, Decimal("0.00"))
        self.assertEqual(calc.gst(Decimal("0.25"), "0.18"), Decimal("0.05"))  # 0.045 -> 0.05

    def test_indian_grouping(self):
        self.assertEqual(calc.inr(150000, False), "₹1,50,000")
        self.assertEqual(calc.inr(10000000, False), "₹1,00,00,000")


class TestCalendar(unittest.TestCase):
    def test_t1_from_holiday_saturday(self):          # 15 Aug 2026 = Sat + holiday
        self.assertEqual(cal.add_working_days(date(2026, 8, 15), 1), date(2026, 8, 17))
        self.assertEqual(cal.add_working_days(date(2026, 8, 15), 0), date(2026, 8, 17))

    def test_saturday_is_working_day(self):
        self.assertTrue(cal.is_working(date(2026, 8, 22)))

    def test_ten_working_days_from_14_aug(self):
        self.assertEqual(cal.add_working_days(date(2026, 8, 14), 10), date(2026, 8, 27))


if __name__ == "__main__":
    unittest.main()
