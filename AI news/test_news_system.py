from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from backtest_gold_direction import prior_probability
from backtest_max_walkforward import DualPolicy, dual_prediction
from economic_context import parse_numeric
from fomc_pipeline import (
    combine_fomc_decision,
    fomc_release_phases,
    pricing_context,
)
from fomc_regime import FomcRegimeStore, PolicySurprise
from gold_direction_rules import (
    event_history_probability,
    live_rule_probability,
    rule_direction,
)
from macro_regime import FRED_SERIES, MacroRegimeStore, SeriesData, feature_names
from news_ensemble import EventPolicy, policy_prediction
from news_v3 import (
    HybridPolicy,
    TwoStagePolicy,
    predict_with_hybrid_policy,
    predict_with_policy,
)
from point_in_time_store import latest_before
from release_intelligence import analyze_fomc_statement_diff


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

    def test_two_stage_impulse_gate_can_abstain(self) -> None:
        policy = TwoStagePolicy(
            event="CPI",
            impulse_strategy="impulse_blend",
            impulse_threshold=0.60,
            direction_strategy="global_tree",
            direction_threshold=0.55,
            require_impulse_agreement=False,
            max_ood_ratio=float("inf"),
            selection_samples=50,
            selected_calls=10,
            selected_wins=7,
            selected_accuracy_pct=70.0,
            selected_coverage_pct=20.0,
            selected_false_impulses=1,
            selected_score=0.5,
        )
        components = {
            "impulse_tree": 0.48,
            "impulse_logistic": 0.52,
            "impulse_blend": 0.496,
            "impulse_agreement": False,
            "ood_ratio": 0.8,
            "direction": {
                "global_tree": 0.80,
                "global_logistic": 0.75,
                "event_tree": 0.80,
                "event_logistic": 0.75,
            },
        }
        result = predict_with_policy(components, policy)
        self.assertEqual(result["prediction"], "NO TRADE")
        self.assertIn("impulse", result["failed_gates"])

    def test_two_stage_regime_gate_can_abstain(self) -> None:
        policy = TwoStagePolicy(
            event="NFP",
            impulse_strategy="impulse_blend",
            impulse_threshold=0.50,
            direction_strategy="global_tree",
            direction_threshold=0.55,
            require_impulse_agreement=False,
            max_ood_ratio=1.0,
            selection_samples=50,
            selected_calls=10,
            selected_wins=7,
            selected_accuracy_pct=70.0,
            selected_coverage_pct=20.0,
            selected_false_impulses=1,
            selected_score=0.5,
        )
        components = {
            "impulse_tree": 0.75,
            "impulse_logistic": 0.70,
            "impulse_blend": 0.73,
            "impulse_agreement": True,
            "ood_ratio": 1.4,
            "direction": {
                "global_tree": 0.70,
                "global_logistic": 0.70,
                "event_tree": 0.70,
                "event_logistic": 0.70,
            },
        }
        result = predict_with_policy(components, policy)
        self.assertEqual(result["prediction"], "NO TRADE")
        self.assertIn("in_distribution", result["failed_gates"])

    def test_hybrid_impulse_layer_cannot_create_direction_call(self) -> None:
        direction_policy = EventPolicy(
            event="PPI",
            strategy="global_tree",
            threshold=0.70,
            calibration_slope=1.0,
            calibration_intercept=0.0,
            calibration_samples=50,
            selection_samples=50,
            selected_calls=10,
            selected_accuracy_pct=60.0,
            selected_coverage_pct=20.0,
            selected_score=0.2,
        )
        policy = HybridPolicy(
            event="PPI",
            direction_policy=direction_policy,
            impulse_strategy="impulse_blend",
            veto_threshold=0.50,
            require_impulse_agreement=False,
            max_ood_ratio=float("inf"),
            selection_samples=50,
            baseline_calls=10,
            baseline_wins=6,
            selected_calls=9,
            selected_wins=6,
            selected_accuracy_pct=66.67,
            selected_coverage_pct=18.0,
            selected_false_impulses=1,
            selected_score=0.3,
        )
        components = {
            "impulse_tree": 0.90,
            "impulse_logistic": 0.90,
            "impulse_blend": 0.90,
            "impulse_agreement": True,
            "ood_ratio": 0.5,
            "direction": {
                "global_tree": 0.60,
                "global_logistic": 0.60,
                "event_tree": 0.60,
                "event_logistic": 0.60,
            },
        }
        result = predict_with_hybrid_policy(components, policy)
        self.assertEqual(result["prediction"], "NO TRADE")
        self.assertIn("direction", result["failed_gates"])


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
        self.assertAlmostEqual(event_history_probability(history), 5 / 9)

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


class FomcPipelineTests(unittest.TestCase):
    def test_modal_hold_is_dovish_against_hike_weighted_mean(self) -> None:
        pricing = pricing_context(
            current_lower=3.50,
            current_upper=3.75,
            cut_25_probability=0,
            hold_probability=70,
            hike_25_probability=30,
        )
        self.assertEqual(pricing["modal_outcome"], "hold")
        self.assertAlmostEqual(pricing["weighted_midpoint_pct"], 3.70)
        self.assertAlmostEqual(pricing["modal_surprise_bps"], -7.5)
        self.assertEqual(pricing["gold_direction"], "POSITIVE")

    def test_agreement_is_high_confidence_but_capped(self) -> None:
        result = combine_fomc_decision(
            history_labels=[
                "POSITIVE",
                "POSITIVE",
                "NEGATIVE",
                "POSITIVE",
                "POSITIVE",
            ],
            model_probability_positive_value=0.25,
        )
        self.assertTrue(result["components_agree"])
        self.assertEqual(result["gold_impact"], "NEGATIVE")
        self.assertEqual(result["confidence_tier"], "HIGH")
        self.assertEqual(result["confidence"], 0.65)

    def test_pricing_resolves_history_model_conflict(self) -> None:
        pricing = pricing_context(
            current_lower=3.50,
            current_upper=3.75,
            cut_25_probability=0,
            hold_probability=70,
            hike_25_probability=30,
        )
        result = combine_fomc_decision(
            history_labels=[
                "POSITIVE",
                "POSITIVE",
                "NEGATIVE",
                "POSITIVE",
                "POSITIVE",
            ],
            model_probability_positive_value=0.54,
            pricing=pricing,
        )
        self.assertFalse(result["components_agree"])
        self.assertEqual(result["gold_impact"], "POSITIVE")
        self.assertEqual(result["confidence_tier"], "LOW")
        self.assertLessEqual(result["confidence"], 0.60)

    def test_near_tied_pricing_does_not_resolve_conflict(self) -> None:
        pricing = pricing_context(
            current_lower=3.50,
            current_upper=3.75,
            cut_25_probability=33,
            hold_probability=34,
            hike_25_probability=33,
        )
        self.assertIsNone(pricing["gold_direction"])

    def test_pricing_contradiction_downgrades_component_agreement(self) -> None:
        pricing = pricing_context(
            current_lower=3.50,
            current_upper=3.75,
            cut_25_probability=0,
            hold_probability=70,
            hike_25_probability=30,
        )
        result = combine_fomc_decision(
            history_labels=[
                "POSITIVE",
                "POSITIVE",
                "NEGATIVE",
                "POSITIVE",
                "POSITIVE",
            ],
            model_probability_positive_value=0.25,
            pricing=pricing,
        )
        self.assertTrue(result["components_agree"])
        self.assertEqual(result["gold_impact"], "NEGATIVE")
        self.assertEqual(result["confidence_tier"], "LOW")
        self.assertEqual(
            result["resolver"],
            "agreement_downgraded_by_fedwatch_conflict",
        )

    def test_press_conference_is_a_separate_later_phase(self) -> None:
        release = datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc)
        phases = fomc_release_phases(release)
        self.assertEqual(phases[0]["phase"], "statement")
        self.assertEqual(phases[1]["phase"], "press_conference")
        self.assertEqual(
            phases[1]["starts_at_utc"],
            "2026-07-29T18:30:00+00:00",
        )

    def test_statement_diff_maps_a_rate_cut_to_positive_gold(self) -> None:
        previous = (
            "The Committee decided to maintain the target range for the "
            "federal funds rate at 4.25 to 4.50 percent. Inflation remains "
            "somewhat elevated."
        )
        current = (
            "The Committee decided to lower the target range for the "
            "federal funds rate to 4.00 to 4.25 percent. Inflation has eased."
        )
        result = analyze_fomc_statement_diff(current, previous)
        self.assertEqual(result["gold_impact"], "POSITIVE")
        self.assertEqual(result["rate_change_bps"], -25.0)

    def test_regime_features_never_include_current_meeting(self) -> None:
        previous = PolicySurprise(
            released=date(2026, 6, 17),
            statement=0.02,
            press_conference=-0.01,
            monetary_event=0.01,
        )
        current = PolicySurprise(
            released=date(2026, 7, 29),
            statement=0.08,
            press_conference=0.04,
            monetary_event=0.12,
        )
        store = FomcRegimeStore.__new__(FomcRegimeStore)
        store.rows = (previous, current)
        store.dates = (previous.released, current.released)
        store.by_date = {
            previous.released: previous,
            current.released: current,
        }

        features = store.policy_features(current.released)
        self.assertEqual(features[0], previous.statement)
        self.assertNotEqual(features[0], current.statement)

    def test_hawkish_statement_surprise_maps_to_negative_gold(self) -> None:
        meeting = PolicySurprise(
            released=date(2026, 7, 29),
            statement=0.08,
            press_conference=None,
            monetary_event=0.08,
        )
        store = FomcRegimeStore.__new__(FomcRegimeStore)
        store.rows = (meeting,)
        store.dates = (meeting.released,)
        store.by_date = {meeting.released: meeting}
        self.assertEqual(
            store.statement_gold_label(meeting.released),
            "NEGATIVE",
        )


if __name__ == "__main__":
    unittest.main()
