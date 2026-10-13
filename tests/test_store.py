import unittest
from datetime import date
from src import store


class TestStore(unittest.TestCase):
    def test_refund_reversal_flips_on_1_sep(self):
        ids = lambda d: {c["id"] for c in store.active(d, "refund")}
        self.assertIn("MASTER-3.3", ids(date(2026, 8, 20)))
        self.assertNotIn("MASTER-3.3", ids(date(2026, 9, 5)))
        self.assertIn("CIRC-D", ids(date(2026, 9, 5)))
        self.assertIn("MASTER-3.3", ids(date(2026, 8, 31)))   # boundary
        self.assertNotIn("MASTER-3.3", ids(date(2026, 9, 1)))

    def test_mdr_cap_by_date(self):
        self.assertEqual(store.value(date(2026, 7, 31), "cap_large")[0], "15")
        self.assertEqual(store.value(date(2026, 8, 15), "cap_large")[0], "25")

    def test_small_rate_changes_on_1_aug(self):
        # circular issued 20 Jul but effective 1 Aug
        self.assertEqual(store.value(date(2026, 7, 25), "rate_small")[0], "0.0030")
        self.assertEqual(store.value(date(2026, 8, 1), "rate_small")[0], "0.0025")

    def test_faq_never_authoritative(self):
        self.assertFalse(any(c["authority"] == "faq" for c in store.active(date(2026, 8, 15))))

    def test_before_policy(self):
        self.assertEqual(store.active(date(2025, 12, 31)), [])

    def test_unknown_clause_raises(self):
        with self.assertRaises(KeyError):
            store.get("MASTER-9.9")


if __name__ == "__main__":
    unittest.main()
