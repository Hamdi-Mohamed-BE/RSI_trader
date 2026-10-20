"""Pre-results causal/boundary fixtures for the DXY conflict screen."""
import copy
import math
import unittest
from datetime import datetime, timezone

import independent_verify as audit
import run as engine


START = 1790985600  # An exact UTC-hour epoch; fixture dates are immaterial.
PLAN = {
    "rules": {"maximum_closed_bar_age_seconds": 3600, "signal_clock_hours": 3,
              "volatility_history_max_calendar_days": 10, "volatility_returns": 120,
              "threshold_sigma_multiplier": 1, "correlation_max_calendar_days": 10,
              "correlation_observations": 120, "correlation_minimum": 100,
              "correlation_maximum_endpoint_age_seconds": 3600},
    "metrics": {"initial_reference_balance": 10000, "fixed_initial_stop_risk": 100},
    "stress": {"extra_per_lot_roundtrip": 20, "double_negative_recorded_swap": True},
}


def candles(count=180, inverse=False):
    result = []
    level = 100.0
    for i in range(count):
        change = (0.0003 if i % 3 == 0 else -0.00015 if i % 3 == 1 else 0.0001)
        if i >= count - 3:
            change = 0.005
        level *= math.exp(change)
        p = 10000.0 / level if inverse else level
        result.append({"time": START + i * audit.HOUR, "close": p})
    return result


class FeatureFixtures(unittest.TestCase):
    def setUp(self):
        self.rows = candles()
        self.dxy = audit.close_map(self.rows)
        self.gold = audit.close_map(candles(inverse=True))
        self.entry = START + len(self.rows) * audit.HOUR + 30

    def test_closed_bar_open_semantics(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        self.assertEqual(feature["latest_close"], self.entry - 30)
        self.assertTrue(feature["valid"])

    def test_naive_calendar_dates_are_utc_not_host_local(self):
        self.assertEqual(audit.epoch("2026-10-01"), audit.epoch("2026-10-01T00:00:00Z"))
        self.assertEqual(engine.epoch("2026-10-01"), audit.epoch("2026-10-01"))
        self.assertEqual(engine.epoch("2026-10-01T01:00:00+01:00"), audit.epoch("2026-10-01"))

    def test_current_unfinished_bar_never_enters(self):
        original = audit.independent_feature(self.entry, self.dxy, self.gold)
        future = dict(self.dxy)
        future[self.entry - 30 + audit.HOUR] = 1e30
        self.assertEqual(original, audit.independent_feature(self.entry, future, self.gold))

    def test_prior_normalizer_excludes_signal_three_returns(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        self.assertEqual(len(feature["volatility_endpoints"]), 120)
        self.assertEqual(max(feature["volatility_endpoints"]), feature["latest_close"] - 3 * audit.HOUR)
        self.assertLess(feature["threshold"], feature["momentum"])

    def test_inverse_returns_correlation(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        self.assertTrue(feature["correlation_valid"])
        self.assertAlmostEqual(feature["correlation"], -1, places=12)

    def test_use_returns_not_index_levels(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        scaled = {t: p * 777 for t, p in self.dxy.items()}
        other = audit.independent_feature(self.entry, scaled, self.gold)
        for key in ("momentum", "threshold", "sigma", "correlation"):
            self.assertAlmostEqual(feature[key], other[key], places=11)

    def test_strong_usd_conflicts_long_not_short(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        self.assertTrue(audit.independent_veto(feature, 1))
        self.assertFalse(audit.independent_veto(feature, -1))

    def test_weak_usd_passes_both(self):
        feature = audit.independent_feature(self.entry, self.dxy, self.gold)
        feature["momentum"] = feature["threshold"] * 0.5
        self.assertFalse(audit.independent_veto(feature, 1))
        self.assertFalse(audit.independent_veto(feature, -1))

    def test_exact_threshold_boundaries_are_inclusive(self):
        f = {"valid": True, "momentum": 0.03, "threshold": 0.03,
             "correlation_valid": True, "correlation": -0.25}
        self.assertTrue(audit.independent_veto(f, 1))
        self.assertTrue(audit.independent_veto(f, 1, gated=True))
        f["momentum"] *= -1
        self.assertTrue(audit.independent_veto(f, -1))
        self.assertFalse(audit.independent_veto(f, 1))

    def test_positive_or_unknown_correlation_does_not_enable_gated_veto(self):
        f = audit.independent_feature(self.entry, self.dxy, self.gold)
        f["correlation"] = 0.5
        self.assertTrue(audit.independent_veto(f, 1))
        self.assertFalse(audit.independent_veto(f, 1, gated=True))
        f["correlation_valid"] = False
        f["correlation"] = None
        self.assertFalse(audit.independent_veto(f, 1, gated=True))

    def test_staleness_is_fail_open(self):
        f = audit.independent_feature(self.entry + audit.HOUR, self.dxy, self.gold)
        self.assertFalse(f["valid"])
        self.assertEqual(f["reason"], "stale_dxy")
        self.assertFalse(audit.independent_veto(f, 1))

    def test_max_age_boundary_is_valid(self):
        f = audit.independent_feature(self.entry + audit.HOUR - 30, self.dxy, self.gold)
        self.assertTrue(f["valid"])

    def test_signal_gap_is_not_treated_as_three_hours(self):
        broken = dict(self.dxy)
        del broken[max(broken) - audit.HOUR]
        f = audit.independent_feature(self.entry, broken, self.gold)
        self.assertFalse(f["valid"])
        self.assertEqual(f["reason"], "signal_hour_gap")

    def test_missing_preceding_hour_does_not_create_hourly_return(self):
        broken = dict(self.dxy)
        t = sorted(broken)[50]
        del broken[t]
        rets = audit.valid_returns(broken)
        self.assertNotIn(t, rets)
        self.assertNotIn(t + audit.HOUR, rets)

    def test_zero_variance_fails_open(self):
        flat = {t: 100.0 for t in self.dxy}
        f = audit.independent_feature(self.entry, flat, self.gold)
        self.assertFalse(f["valid"])
        self.assertFalse(audit.independent_veto(f, 1))

    def test_short_volatility_history_fails_open(self):
        short = dict(list(self.dxy.items())[-100:])
        f = audit.independent_feature(self.entry, short, self.gold)
        self.assertFalse(f["valid"])
        self.assertEqual(f["reason"], "insufficient_volatility_history")

    def test_no_future_gold_close_can_change_correlation(self):
        base = audit.independent_feature(self.entry, self.dxy, self.gold)
        future = dict(self.gold)
        future[max(future) + audit.HOUR] = 1e60
        other = audit.independent_feature(self.entry, self.dxy, future)
        self.assertEqual(base, other)

    def test_insufficient_gold_pairs_preserves_plain_but_disables_gated(self):
        few = dict(list(self.gold.items())[-50:])
        f = audit.independent_feature(self.entry, self.dxy, few)
        self.assertTrue(f["valid"])
        self.assertFalse(f["correlation_valid"])
        self.assertTrue(audit.independent_veto(f, 1))
        self.assertFalse(audit.independent_veto(f, 1, gated=True))

    def test_no_closed_dxy_fails_open(self):
        f = audit.independent_feature(min(self.dxy) - 1, self.dxy, self.gold)
        self.assertFalse(f["valid"])
        self.assertEqual(f["reason"], "no_closed_dxy")

    def test_close_map_rejects_duplicate(self):
        with self.assertRaises(AssertionError):
            audit.close_map(self.rows + self.rows[-1:])

    def test_close_map_rejects_nonpositive_prices(self):
        bad = copy.deepcopy(self.rows)
        bad[3]["close"] = 0
        with self.assertRaises(AssertionError):
            audit.close_map(bad)


class MetricFixtures(unittest.TestCase):
    def rows(self, values):
        return [{"open": START + i, "close": START + 100 + i,
                 "id": str(i), "pnl": p, "net_r": p / 100}
                for i, p in enumerate(values)]

    def test_zero_breaks_both_streaks_and_counts_in_denominator(self):
        m = audit.independent_metrics(self.rows([100, 100, 0, -100, -100, 50]),
                                      START, START + audit.DAY)
        self.assertEqual((m["wins"], m["losses"], m["zeros"]), (3, 2, 1))
        self.assertEqual((m["max_win_streak"], m["max_loss_streak"]), (2, 2))
        self.assertEqual(m["win_rate"], 50)
        self.assertEqual(m["pf"], 1.25)
        self.assertEqual(m["net"], 50)
        self.assertEqual(m["max_closed_dd"], 200)
        self.assertAlmostEqual(m["max_closed_dd_pct"], 200 / 10200 * 100)

    def test_reorders_by_close_not_input_order(self):
        rows = self.rows([100, -50, 100])
        self.assertEqual(audit.independent_metrics(rows, START, START + audit.DAY),
                         audit.independent_metrics(list(reversed(rows)), START, START + audit.DAY))

    def test_empty_sample_is_not_infinite_pf_or_sharpe(self):
        m = audit.independent_metrics([], START, START + audit.DAY)
        self.assertEqual(m["trades"], 0)
        self.assertEqual(m["return_pct"], 0)
        self.assertIsNone(m["pf"])
        self.assertIsNone(m["sharpe"])

    def test_all_winners_pf_unavailable_not_numeric_infinity(self):
        m = audit.independent_metrics(self.rows([10, 10]), START, START + audit.DAY)
        self.assertIsNone(m["pf"])
        self.assertEqual(m["max_win_streak"], 2)

    def test_nonpositive_reference_balance_disables_sharpe(self):
        m = audit.independent_metrics(self.rows([-11000]), START, START + 3 * audit.DAY)
        self.assertIsNone(m["sharpe"])
        self.assertEqual(m["end_balance"], -1000)


class EngineFixtures(unittest.TestCase):
    def compare_feature(self, raw_dxy, raw_gold, entry):
        expected = audit.independent_feature(entry, audit.close_map(raw_dxy), audit.close_map(raw_gold))
        actual = engine.feature_at(entry, engine.HourlySeries(raw_dxy), engine.HourlySeries(raw_gold), PLAN)
        self.assertEqual(actual["valid"], expected["valid"])
        self.assertEqual(actual["correlation_valid"], expected["correlation_valid"])
        if expected["valid"]:
            for root_key, independent_key in (("momentum", "momentum"), ("threshold", "threshold"),
                                               ("volatility", "sigma"), ("correlation", "correlation")):
                if expected[independent_key] is not None:
                    self.assertAlmostEqual(actual[root_key], expected[independent_key], places=11)
            self.assertEqual(actual["normalizer_first_epoch"], expected["volatility_endpoints"][0])
            self.assertEqual(actual["normalizer_last_epoch"], expected["volatility_endpoints"][-1])
            self.assertEqual(actual["veto_long"], audit.independent_veto(expected, 1))
            self.assertEqual(actual["veto_short"], audit.independent_veto(expected, -1))
        return actual

    def test_engine_strong_inverse_case_matches_independent(self):
        raw = candles()
        self.compare_feature(raw, candles(inverse=True), START + len(raw) * audit.HOUR + 30)

    def test_engine_future_mutation_cannot_change_features(self):
        raw = candles()
        entry = START + len(raw) * audit.HOUR + 30
        old = self.compare_feature(raw, candles(inverse=True), entry)
        raw.append({"time": START + len(raw) * audit.HOUR, "close": 1e80})
        new = self.compare_feature(raw, candles(inverse=True), entry)
        self.assertEqual(old, new)

    def test_engine_signal_gap_matches_independent(self):
        raw = candles()
        del raw[-2]
        actual = self.compare_feature(raw, candles(inverse=True), START + 180 * audit.HOUR + 30)
        self.assertFalse(actual["valid"])

    def test_engine_stale_gap_matches_independent(self):
        raw = candles()
        self.compare_feature(raw, candles(inverse=True), START + 181 * audit.HOUR + 30)

    def test_engine_same_level_scalar_is_irrelevant(self):
        raw = candles()
        for row in raw:
            row["close"] *= 13
        self.compare_feature(raw, candles(inverse=True), START + 180 * audit.HOUR + 30)

    def test_engine_short_history_matches_independent(self):
        raw = candles()[-99:]
        self.compare_feature(raw, candles(inverse=True), START + 180 * audit.HOUR + 30)

    def test_engine_zero_variance_fails_open(self):
        raw = [{"time": r["time"], "close": 100} for r in candles()]
        self.compare_feature(raw, candles(inverse=True), START + 180 * audit.HOUR + 30)

    def test_engine_missing_gold_pairs_only_disables_secondary(self):
        raw = candles()
        self.compare_feature(raw, candles(inverse=True)[-50:], START + 180 * audit.HOUR + 30)

    def test_engine_annotate_uses_source_direction_and_passes_invalid(self):
        raw = candles()
        dx, gold = engine.HourlySeries(raw), engine.HourlySeries(candles(inverse=True))
        r = {"key": "ema3", "position_id": 1, "op": START + 180 * audit.HOUR + 30,
             "cl": START + 180 * audit.HOUR + 100, "side": "Long"}
        long = engine.annotate(r, dx, gold, PLAN)
        self.assertTrue(long["primary_veto"])
        r["side"] = "Short"
        self.assertFalse(engine.annotate(r, dx, gold, PLAN)["primary_veto"])
        r["op"] += 3 * audit.HOUR
        r["side"] = "Long"
        self.assertFalse(engine.annotate(r, dx, gold, PLAN)["primary_veto"])

    def test_engine_net_r_cost_sensitivity(self):
        r = {"unit_risk": 200, "unit_gross": 300, "unit_comm": -10, "unit_swap": -20}
        self.assertAlmostEqual(engine.net_r(r, False, PLAN), 1.35)
        self.assertAlmostEqual(engine.net_r(r, True, PLAN), 1.15)
        r["unit_swap"] = 20
        self.assertAlmostEqual(engine.net_r(r, True, PLAN), 1.45)
        r["unit_risk"] = 0
        with self.assertRaises(ValueError):
            engine.net_r(r, False, PLAN)

    def test_engine_metrics_match_independent_fixture(self):
        values = [100, 100, 0, -100, -100, 50]
        rows = [{"key": "ema3", "position_id": i + 1, "op": START + i,
                 "cl": START + 100 + i, "side": "Long", "unit_risk": 100,
                 "unit_gross": v, "unit_comm": 0, "unit_swap": 0} for i, v in enumerate(values)]
        actual = engine.metric_pack(rows, START, START + audit.DAY, False, PLAN)["metrics"]
        expected = audit.independent_metrics(
            [{"id": str(r["position_id"]), "key": r["key"], "position_id": r["position_id"],
              "open": r["op"], "close": r["cl"], "pnl": r["unit_gross"],
              "net_r": r["unit_gross"] / 100} for r in rows], START, START + audit.DAY)
        for root_key, independent_key in (("trades", "trades"), ("wins", "wins"),
              ("losses", "losses"), ("breakevens", "zeros"), ("profit_factor", "pf"),
              ("win_rate_pct", "win_rate"), ("net_profit", "net"),
              ("closed_return_pct", "return_pct"), ("max_closed_dd_cash", "max_closed_dd"),
              ("max_closed_dd_pct", "max_closed_dd_pct"), ("max_winning_streak", "max_win_streak"),
              ("max_losing_streak", "max_loss_streak")):
            self.assertAlmostEqual(actual[root_key], expected[independent_key])

    def test_engine_final_day_insolvency_disables_sharpe(self):
        rows = [{"key": "ema3", "position_id": 1, "op": START,
                 "cl": START + audit.DAY + 1, "side": "Long", "unit_risk": 100,
                 "unit_gross": -11000, "unit_comm": 0, "unit_swap": 0}]
        actual = engine.metric_pack(rows, START, START + 2 * audit.DAY, False, PLAN)["metrics"]
        self.assertIsNone(actual["closed_daily_sharpe"])

    def test_engine_window_membership_and_numeric_close_order(self):
        s = "2026-10-01"
        e = "2026-10-02"
        start, end = engine.epoch(s), engine.epoch(e)
        def row(pid, op, cl):
            return {"key": "ema3", "position_id": pid, "op": op, "cl": cl,
                    "side": "Long", "unit_risk": 100, "unit_gross": 1,
                    "unit_comm": 0, "unit_swap": 0}
        rows = [row(10, start, start + 10), row(2, start, start + 10),
                row(3, start - 1, start + 20), row(4, start, end)]
        features = {engine.trade_id(r): {"valid": False, "correlation_valid": False,
                    "primary_veto": False, "secondary_veto": False, "reason": "missing"} for r in rows}
        result = engine.make_result(rows, features, "ema3", {"id": "fixture", "start": s,
                                    "end_exclusive": e}, "recorded", "baseline", PLAN)
        self.assertEqual(result["selected_ids"], ["ema3:2", "ema3:10"])
        self.assertEqual(result["coverage"]["pre_window_entries_excluded"], 1)


if __name__ == "__main__":
    unittest.main()
