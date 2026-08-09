from __future__ import annotations

import unittest

from news_v5 import CPI_POLICY, cpi_regime_prediction


class CpiRegimeTests(unittest.TestCase):
    def test_calls_positive_when_both_regime_gates_pass(self) -> None:
        history = ["SELL"] * 10 + ["BUY"] * 30
        result = cpi_regime_prediction(history)
        self.assertEqual(result["prediction"], "BUY")
        self.assertEqual(result["bias"], "BUY")
        self.assertEqual(result["failed_gates"], [])

    def test_short_history_abstains(self) -> None:
        result = cpi_regime_prediction(["BUY"] * 20)
        self.assertEqual(result["prediction"], "NO CALL")
        self.assertIn("minimum_history", result["failed_gates"])

    def test_recent_regime_failure_abstains(self) -> None:
        history = ["BUY"] * 36 + ["SELL"] * CPI_POLICY["recent_window"]
        result = cpi_regime_prediction(history)
        self.assertEqual(result["prediction"], "NO CALL")
        self.assertIn("recent_regime", result["failed_gates"])

    def test_confidence_is_capped(self) -> None:
        result = cpi_regime_prediction(["BUY"] * 60)
        self.assertLessEqual(result["confidence"], CPI_POLICY["confidence_cap"])


if __name__ == "__main__":
    unittest.main()
