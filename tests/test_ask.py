"""Integration tests on the final answer for the 8 spec questions."""
import unittest
from src.ask import ask


def clauses(r):
    return {c["clause"] for c in r["citations"]}


class TestSpecQuestions(unittest.TestCase):
    def test_q1_settlement_both_branches(self):
        r = ask("When does a small merchant receive UPI money?")
        self.assertEqual(r["status"], "CONFLICT_RESOLVED")
        self.assertIn("Mon 17 Aug 2026", r["answer"])
        self.assertIn("Instant Settlement", r["answer"])
        self.assertTrue({"A", "1.3"} <= clauses(r))

    def test_q2_large_4000(self):
        r = ask("A large merchant (above Rs.10 lakh monthly) receives a Rs.4,000 UPI payment. What MDR and GST do they pay?")
        self.assertIn("₹20.00", r["answer"]); self.assertIn("₹3.60", r["answer"]); self.assertIn("₹23.60", r["answer"])
        self.assertTrue({"2.2", "C", "2.4"} <= clauses(r))

    def test_q3_over_limit_not_approved(self):
        r = ask("Same merchant, a Rs.1,50,000 payment. What do they pay?")
        self.assertIn("exceeds", r["answer"]); self.assertIn("₹29.50", r["answer"])
        self.assertTrue({"4.1", "4.2", "4.4", "E", "C"} <= clauses(r))

    def test_q4_refund_flips_on_1_sep(self):
        q = "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?"
        a, b = ask(q, "2026-08-20"), ask(q, "2026-09-05")
        self.assertTrue(a["answer"].startswith("Yes")); self.assertIn("3.3", clauses(a))
        self.assertTrue(b["answer"].startswith("No")); self.assertEqual(clauses(b), {"3.2", "D"})
        self.assertTrue(ask(q, "2026-08-31")["answer"].startswith("Yes"))
        self.assertTrue(ask(q, "2026-09-01")["answer"].startswith("No"))

    def test_q5_faq_wrong_about_cap(self):
        r = ask("What does the FAQ say about the MDR cap, and is the FAQ right?")
        self.assertEqual(r["status"], "CONFLICT_RESOLVED")
        self.assertIn("wrong about the cap", r["answer"])
        self.assertTrue({"2.3", "C"} <= clauses(r))

    def test_q6_daily_limit(self):
        r = ask("Can a customer pay Rs.1,00,000 twice in one day to a merchant?")
        self.assertTrue(r["answer"].startswith("No")); self.assertIn("E", clauses(r))

    def test_q7_closure(self):
        r = ask("I closed my account yesterday. When will I get my money?")
        self.assertIn("Thu 27 Aug 2026", r["answer"]); self.assertIn("5.2", clauses(r))

    def test_q8_false_premise(self):
        r = ask("Does the policy allow me to settle card payments same day?")
        self.assertTrue(r["answer"].startswith("No")); self.assertIn("1.2", clauses(r))

    def test_before_policy_and_unknown(self):
        self.assertEqual(ask("What is the UPI MDR?", "2025-12-01")["status"], "CANNOT_ANSWER")
        self.assertEqual(ask("Do you support international wallets?")["status"], "CANNOT_ANSWER")

    def test_citations_are_real(self):
        from src import store
        real = {(c["doc"], c["clause"]) for c in store._CLAUSES.values()}
        for q in ["When does a small merchant receive UPI money?", "What does the FAQ say about refunds?",
                  "Can a customer pay Rs.1,00,000 twice in one day to a merchant?"]:
            for c in ask(q)["citations"]:
                self.assertIn((c["document"], c["clause"]), real)


if __name__ == "__main__":
    unittest.main()
