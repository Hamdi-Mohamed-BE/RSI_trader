"""Synthetic-only fixtures. No archived prices/OOS, network or MT5 access."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location("weekend_robustness", Path(__file__).with_name("robustness.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def records(returns, paths=None):
    start = datetime(2020, 1, 3, 22, tzinfo=timezone.utc)
    result = []
    for i, value in enumerate(returns):
        a = start + timedelta(weeks=i)
        row = {"week_id": a.date().isoformat(), "entry_epoch": int(a.timestamp()),
               "exit_epoch": int((a + timedelta(days=2)).timestamp()),
               "return_per_notional": value, "cost_basis": "synthetic"}
        if paths is not None:
            row["intratrade_path"] = [{"epoch": int(a.timestamp()) + j * 60,
                                      "equity_factor": v} for j, v in enumerate(paths[i])]
        result.append(row)
    return result


def weeks(rows):
    return [x["week_id"] for x in rows]


class RobustnessTests(unittest.TestCase):
    def test_one_percent_up_down_compounds_not_adds(self):
        x = r.summarize_trades(records([.01, -.01]))
        self.assertAlmostEqual(x["ending_balance_usd"], 9999)
        self.assertAlmostEqual(x["profit_factor"], 100 / 101)
        self.assertAlmostEqual(x["return_pct"], -.01)

    def test_exact_plus_one_minus_one_ruins_without_negative_cash(self):
        x = r.summarize_trades(records([1, -1, .5]))
        self.assertEqual(x["ending_balance_usd"], 0)
        self.assertEqual(x["trades"], 2)
        self.assertEqual(x["profit_factor"], .5)
        self.assertEqual(x["max_closed_dd_pct"], 100)

    def test_joint_resample_constant_loss_has_matching_return_pf_dd(self):
        rows = records([-.1] * 5)
        x = r.joint_bootstrap(rows, weeks(rows), paths=17, block_weeks=5)
        self.assertAlmostEqual(x["distributions"]["return_pct"]["p50"], (1 - .9 ** 5) * -100)
        self.assertEqual(x["distributions"]["pf"]["p50"], 0)
        self.assertAlmostEqual(x["distributions"]["max_closed_dd_pct"]["p50"], (1 - .9 ** 5) * 100)
        self.assertEqual(x["paths"], 17)

    def test_intratrade_dd_summary_equals_full_concatenated_path(self):
        rows = records([.1, -.1, .05], [[1, 1.2, .8, 1.1], [1, .6, 1.3, .9], [1, 1.2, .9, 1.05]])
        cash = 10000
        full = [cash]
        for row in rows:
            full.extend(cash * p["equity_factor"] for p in row["intratrade_path"])
            cash *= 1 + row["return_per_notional"]
            full.append(cash)
        a = np.asarray(full)
        expected = (1 - a / np.maximum.accumulate(a)).max() * 100
        self.assertAlmostEqual(r.summarize_trades(rows)["max_sampled_equity_dd_pct"], expected)

    def test_intratrade_samples_are_not_discarded_in_bootstrap(self):
        rows = records([.01] * 3, [[1, .5, 1.01]] * 3)
        x = r.joint_bootstrap(rows, weeks(rows), paths=20)
        self.assertEqual(x["distributions"]["max_closed_dd_pct"]["p50"], 0)
        self.assertEqual(x["distributions"]["max_sampled_equity_dd_pct"]["p50"], 50)

    def test_endpoints_alone_are_not_counted_as_interior_marks(self):
        rows = records([.01])
        rows[0]["intratrade_path"] = [{"epoch": rows[0]["entry_epoch"], "equity_factor": 1},
                                      {"epoch": rows[0]["exit_epoch"], "equity_factor": 1.01}]
        x = r.summarize_trades(rows)
        self.assertEqual(x["trades_with_intratrade_samples"], 0)
        self.assertEqual(x["trades_closed_only"], 1)

    def test_valid_no_trade_weeks_do_not_reset_position_streak(self):
        rows = records([-.01, -.01, -.01])
        rows.pop(1)
        ids = ["2020-01-03", "2020-01-10", "2020-01-17"]
        x = r.summarize_trades(rows, ids)
        self.assertEqual(x["valid_no_trade_weeks"], 1)
        self.assertEqual(x["max_loss_streak"], 2)

    def test_real_breakeven_resets_streak(self):
        self.assertEqual(r.summarize_trades(records([-.01, 0, -.01]))["max_loss_streak"], 1)

    def test_missing_data_never_zero_filled(self):
        rows = records([.01, -.01])
        x = r.joint_bootstrap(rows, weeks(rows), missing_week_ids=["2020-01-17"], paths=5)
        self.assertEqual(x["status"], "unavailable_incomplete_history")
        self.assertEqual(x["paths"], 0)
        self.assertEqual(r.joint_bootstrap(rows, paths=5)["status"], "unavailable_calendar")
        incomplete = r.analyze_robustness(rows, tested_configurations=9,
                                          scheduled_week_ids=weeks(rows),
                                          missing_week_ids=["2020-01-17"], paths=3)
        self.assertNotIn("summary", incomplete)

    def test_removing_every_trade_removes_paths_costs_and_losses(self):
        rows = records([.1, -.5], [[1, .9, 1.1], [1, .2, .5]])
        x = r.trade_removal(rows, weeks(rows), fraction=1, paths=15)
        self.assertEqual(x["distributions"]["return_pct"]["p50"], 0)
        self.assertEqual(x["distributions"]["max_sampled_equity_dd_pct"]["p50"], 0)
        self.assertEqual(x["distributions"]["trades"]["p50"], 0)
        self.assertEqual(x["distributions"]["pf"]["undefined_paths"], 15)

    def test_reshuffle_keeps_product_return_not_additive_pnl(self):
        rows = records([.1, -.2, .3, -.05])
        x = r.trade_order_reshuffle(rows, weeks(rows), paths=101)
        expected = (1.1 * .8 * 1.3 * .95 - 1) * 100
        for k in ["p05", "p50", "p95"]:
            self.assertAlmostEqual(x["distributions"]["return_pct"][k], expected)

    def test_seed_determinism_non_multiple_batch(self):
        rows = records([.1, -.1, .2, -.3, .1, .01])
        a = r.joint_bootstrap(rows, weeks(rows), paths=203, seed=42)
        b = r.joint_bootstrap(rows, weeks(rows), paths=203, seed=42)
        self.assertEqual(a, b)

    def test_wilson_zero_and_all_wins(self):
        self.assertIsNone(r.wilson_interval(0, 0)["lower_pct"])
        x = r.wilson_interval(10, 10)
        self.assertGreater(x["lower_pct"], 70)
        self.assertAlmostEqual(x["upper_pct"], 100)

    def test_daily_sharpe_includes_all_calendar_zero_days_365(self):
        rows = records([.01])
        start = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())
        end = int(datetime(2020, 1, 8, tzinfo=timezone.utc).timestamp())
        x = r.daily_closed_balance_statistics(rows, start, end)
        daily = np.array([0, 0, 0, 0, .01, 0, 0])
        self.assertEqual(x["calendar_days"], 7)
        self.assertEqual(x["zero_exit_days"], 6)
        self.assertAlmostEqual(x["daily_closed_balance_sharpe"], daily.mean() / daily.std(ddof=1) * np.sqrt(365))

    def test_dsr_actual_trial_count_penalizes_more_search(self):
        a = np.array([.01, -.005, .02, -.001, .008, -.004] * 10)
        one = r.deflated_sharpe(a, 1, trial_sharpe_std=.1)
        many = r.deflated_sharpe(a, 123, trial_sharpe_std=.1)
        self.assertEqual(many["tested_configurations"], 123)
        self.assertLess(many["dsr_pct"], one["dsr_pct"])
        with self.assertRaises(ValueError):
            r.deflated_sharpe(a, 0)

    def test_family_bootstrap_preserves_duplicate_columns_exactly(self):
        x = np.array([.01, -.005, .02, -.01, -.002, .006] * 2)
        one = r.family_null(x[:, None], ["a"], "a", paths=103, seed=42)
        duplicate = r.family_null(np.c_[x, x], ["a", "b"], "a", paths=103, seed=42)
        self.assertEqual(one["family_max_p_value"], duplicate["family_max_p_value"])
        self.assertEqual(duplicate["fixed_rule_p_value"], duplicate["family_max_p_value"])

    def test_family_missing_is_unavailable_and_costs_never_flip(self):
        x = np.array([.01, -.01, .02, -.02])[:, None]
        bad = x.copy(); bad[0] = np.nan
        self.assertEqual(r.family_null(bad, ["a"], "a", paths=3)["status"], "unavailable_incomplete_matrix")
        v = r.family_null(x, ["a"], "a", paths=7, cost_matrix=np.full_like(x, .001))
        self.assertIn("unchanged-signed cost", v["method"])
        with self.assertRaises(ValueError):
            r.family_null(np.c_[x, x], ["a", "a"], "a", paths=3)

    def test_chronological_thirds_and_half_do_not_select(self):
        rows = records([.01, .02, -.03, -.02, .04, .01])
        x = r.chronological_checks(rows, weeks(rows))
        self.assertEqual(x["profitable_thirds"], 2)
        self.assertEqual(x["recent_half"]["trades"], 3)

    def test_bad_paths_overlaps_and_below_minus_one_rejected(self):
        with self.assertRaises(ValueError):
            r.summarize_trades(records([-1.01]))
        rows = records([.1, .1]); rows[1]["entry_epoch"] = rows[0]["entry_epoch"] + 1
        with self.assertRaises(ValueError):
            r.summarize_trades(rows)
        rows = records([.1]); rows[0]["intratrade_path"] = [{"epoch": rows[0]["exit_epoch"] + 1, "equity_factor": .9}]
        with self.assertRaises(ValueError):
            r.summarize_trades(rows)

    def test_neighborhood_missing_is_not_success(self):
        x = r.neighborhood_summary([{"return_pct": 1}, {"return_pct": 2}, {"return_pct": None}])
        self.assertFalse(x["plateau_gate"])
        self.assertAlmostEqual(x["profitable_share"], 2 / 3)

    def test_high_level_marks_promotion_gaps_unavailable(self):
        rows = records([.01, -.01, .02, .01, -.005, .02])
        x = r.analyze_robustness(rows, tested_configurations=9, scheduled_week_ids=weeks(rows), paths=11)
        self.assertFalse(x["promotion_complete"])
        self.assertIsNone(x["cost_stress"]["gate"])
        self.assertIsNone(x["prop_simulation"]["gate"])
        self.assertEqual(set(x["block_bootstrap"]), {"1", "5", "10"})


if __name__ == "__main__":
    unittest.main()
