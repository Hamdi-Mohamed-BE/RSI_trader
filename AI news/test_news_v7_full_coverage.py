from __future__ import annotations

import unittest

from news_v7_full_coverage import full_coverage_decision


class FullCoverageDecisionTests(unittest.TestCase):
    def test_nfp_inverts_previous_release(self) -> None:
        result = full_coverage_decision("NFP", ["POSITIVE"], 0.61)
        self.assertEqual(result["prediction"], "NEGATIVE")

    def test_cpi_uses_expanding_majority(self) -> None:
        result = full_coverage_decision(
            "CPI",
            ["POSITIVE", "NEGATIVE", "POSITIVE"],
            0.64,
        )
        self.assertEqual(result["prediction"], "POSITIVE")

    def test_fomc_inverts_recent_five_meeting_majority(self) -> None:
        result = full_coverage_decision(
            "FOMC",
            ["POSITIVE", "POSITIVE", "NEGATIVE", "POSITIVE", "NEGATIVE"],
            0.62,
        )
        self.assertEqual(result["prediction"], "NEGATIVE")

    def test_never_abstains_when_confirmation_conflicts(self) -> None:
        result = full_coverage_decision(
            "NFP",
            ["POSITIVE"],
            0.61,
            [
                {"direction": "POSITIVE", "lead_minutes": 15},
                {"direction": "POSITIVE", "lead_minutes": 30},
            ],
        )
        self.assertEqual(result["prediction"], "NEGATIVE")
        self.assertEqual(result["coverage_mode"], "FULL")
        self.assertEqual(result["failed_gates"], [])

    def test_confidence_is_bounded(self) -> None:
        high = full_coverage_decision("CPI", ["POSITIVE"] * 5, 0.99)
        low = full_coverage_decision("CPI", ["NEGATIVE"] * 5, 0.20)
        self.assertLessEqual(high["confidence"], 0.68)
        self.assertGreaterEqual(low["confidence"], 0.50)


if __name__ == "__main__":
    unittest.main()
