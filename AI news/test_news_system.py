from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from backtest_gold_direction import prior_probability
from backtest_max_walkforward import DualPolicy, dual_prediction
from economic_context import parse_numeric
from gold_direction_rules import (
    event_history_probability,
    live_rule_probability,
    rule_direction,
)
from macro_regime import FRED_SERIES, MacroRegimeStore, SeriesData, feature_names
from news_ensemble import EventPolicy, policy_prediction
from point_in_time_store import latest_before


class EnsembleTests(unittest.TestCase):
    def test_identity_calibration_preserves_probability(self) -> None:
        policy = EventPolicy(
            event="CPI",
            strategy="global_tree",
            threshold=0.60,
            calibration_slope=1.0,
            calibration_intercept=0.0,
            calibration_samples=100,
            selection_samples=100,
            selected_calls=20,
            selected_accuracy_pct=65.0,
            selected_coverage_pct=20.0,
            selected_score=0.5,
        )
        result = policy_prediction(
            {
                "global_tree": 0.64,
                "global_logistic": 0.50,
                "event_tree": 0.50,
                "event_logistic": 0.50,
            },
            policy,
        )
        self.assertEqual(result["prediction"], "BUY")
        self.assertAlmostEqual(result["probability_buy"], 0.64)

    def test_cross_horizon_blend_cannot_manufacture_call(self) -> None:
        no_trade_15 = {
            "prediction": "NO TRADE",
            "bias": "SELL",
            "confidence": 0.599,
            "probability_buy": 0.401,
            "probability_sell": 0.599,
            "threshold": 0.60,
        }
        no_trade_30 = {
            "prediction": "NO TRADE",
            "bias": "SELL",
            "confidence": 0.619,
            "probability_buy": 0.381,
            "probability_sell": 0.619,
            "threshold": 0.625,
        }
        dual = DualPolicy(
            event="NFP",
            weight_15m=0.5,
            threshold=0.60,
            require_agreement=False,
            selection_samples=50,
            selected_calls=10,
            selected_accuracy_pct=70.0,
            selected_coverage_pct=20.0,
            selected_score=0.5,
        )
        result = dual_prediction(no_trade_15, no_trade_30, dual)
        self.assertEqual(result["prediction"], "NO TRADE")
        self.assertGreater(result["shadow_blend_confidence_pct"], 60)


class PointInTimeStoreTests(unittest.TestCase):
    def test_latest_record_never_reads_after_cutoff(self) -> None:
        directory = Path(tempfile.mkdtemp())
        release = "2026-07-30T12:30:00+00:00"
        early = {
            "release_utc": release,
            "observed_at_utc": "2026-07-30T12:00:00+00:00",
            "forecast": "2.1%",
        }
        late = {
            "release_utc": release,
            "observed_at_utc": "2026-07-30T12:20:00+00:00",
            "forecast": "2.2%",
        }
        (directory / "20260730T123000Z-20260730T120000Z.json").write_text(
            json.dumps(early),
            encoding="utf-8",
        )
        (directory / "20260730T123000Z-20260730T122000Z.json").write_text(
            json.dumps(late),
            encoding="utf-8",
        )
        selected = latest_before(
            directory,
            release,
            "2026-07-30T12:15:00+00:00",
        )
        self.assertEqual(selected["forecast"], "2.1%")


class GoldDirectionTests(unittest.TestCase):
    def test_event_prior_is_shrunk_and_binary(self) -> None:
        rows = [
            {"event": "CPI", "target": "POSITIVE"},
            {"event": "CPI", "target": "POSITIVE"},
            {"event": "CPI", "target": "NEGATIVE"},
        ]
        self.assertAlmostEqual(prior_probability(rows, "CPI"), 4 / 7)
        self.assertEqual(prior_probability([], "CPI"), 0.5)

    def test_macro_features_never_use_release_day_value(self) -> None:
        store = object.__new__(MacroRegimeStore)
        series = SeriesData(
            dates=(date(2026, 7, 28), date(2026, 7, 29), date(2026, 7, 30)),
            values=(1.0, 2.0, 99.0),
        )
        store.series = {label: series for label in FRED_SERIES}
        values = store.features("2026-07-30T12:30:00+00:00")
        stride = 3 + 3
        for index in range(len(FRED_SERIES)):
            self.assertEqual(values[index * stride], 2.0)
        self.assertEqual(len(values), len(feature_names()))

    def test_direction_rules_use_history_only(self) -> None:
        history = ["POSITIVE", "NEGATIVE", "POSITIVE", "POSITIVE", "NEGATIVE"]
        self.assertEqual(rule_direction("inverse_last", history), "POSITIVE")
        self.assertEqual(
            rule_direction("inverse_majority_5", history),
            "NEGATIVE",
        )
        self.assertAlmostEqual(event_history_probability(history), 4 / 9)

    def test_live_rule_probability_is_bounded(self) -> None:
        probability = live_rule_probability(
            "inverse_last",
            ["NEGATIVE"],
            0.9,
        )
        self.assertEqual(probability, 0.75)

    def test_economic_numbers_preserve_units(self) -> None:
        self.assertEqual(parse_numeric("225K"), 225_000)
        self.assertEqual(parse_numeric("2.1%"), 2.1)
        self.assertIsNone(parse_numeric(""))


if __name__ == "__main__":
    unittest.main()
