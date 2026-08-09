from __future__ import annotations

import unittest

from news_v4 import (
    SUPPORTED_EVENTS,
    SelectivePolicy,
    fomc_agreement_prediction,
    selective_prediction,
)


def policy(*, threshold: float = 0.60) -> SelectivePolicy:
    return SelectivePolicy(
        event="NFP",
        strategy="global_tree",
        invert_probability=False,
        threshold=threshold,
        history_rule="inverse_last",
        require_history_agreement=True,
        development_samples=100,
        development_calls=20,
        development_wins=15,
        development_accuracy_pct=75.0,
        guard_samples=30,
        guard_calls=8,
        guard_wins=6,
        guard_accuracy_pct=75.0,
        selection_score=0.7,
    )


class SelectivePredictionTests(unittest.TestCase):
    def test_only_three_events_are_live(self) -> None:
        self.assertEqual(SUPPORTED_EVENTS, ("NFP", "CPI", "FOMC"))

    def test_weak_probability_abstains(self) -> None:
        result = selective_prediction(
            {
                "global_tree": 0.56,
                "global_logistic": 0.56,
                "event_tree": 0.56,
                "event_logistic": 0.56,
            },
            policy(),
            ["BUY"],
        )
        self.assertEqual(result["bias"], "BUY")
        self.assertEqual(result["prediction"], "NO CALL")
        self.assertIn("confidence", result["failed_gates"])

    def test_history_disagreement_abstains(self) -> None:
        result = selective_prediction(
            {
                "global_tree": 0.72,
                "global_logistic": 0.72,
                "event_tree": 0.72,
                "event_logistic": 0.72,
            },
            policy(),
            ["BUY"],
        )
        self.assertEqual(result["history_bias"], "SELL")
        self.assertEqual(result["prediction"], "NO CALL")
        self.assertIn("history_agreement", result["failed_gates"])

    def test_full_gate_can_call(self) -> None:
        result = selective_prediction(
            {
                "global_tree": 0.72,
                "global_logistic": 0.72,
                "event_tree": 0.72,
                "event_logistic": 0.72,
            },
            policy(),
            ["SELL"],
        )
        self.assertEqual(result["history_bias"], "BUY")
        self.assertEqual(result["prediction"], "BUY")

    def test_fomc_requires_component_agreement(self) -> None:
        no_call = fomc_agreement_prediction(
            ["BUY", "BUY", "SELL", "BUY", "BUY"],
            0.70,
        )
        self.assertEqual(no_call["history_bias"], "SELL")
        self.assertEqual(no_call["bias"], "BUY")
        self.assertEqual(no_call["prediction"], "NO CALL")

        called = fomc_agreement_prediction(
            ["BUY", "BUY", "SELL", "BUY", "BUY"],
            0.30,
        )
        self.assertEqual(called["prediction"], "SELL")


if __name__ == "__main__":
    unittest.main()
