"""Synthetic cash-only fixtures. No real study outcomes or MT5 calls."""
import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cash_only_mc as cash_mc
import native_robustness as nr


class CashOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / "native" / "fixture"
        self.folder.mkdir(parents=True)
        self.candidate = {"entry_minute_ny": 1020, "exit_minute_ny": 1020, "entry_mode": 0, "filter_mode": 0}
        self.start, self.end = "2026-01-02", "2026-01-13"
        self.weeks, _ = nr.weekend_calendar(self.candidate, self.start, self.end)
        self.positions, self.requests, self.decisions = [], [], []
        balance = 10000
        for index, (week, profit) in enumerate(zip(self.weeks, [110, -110])):
            entry, close = week["entry_epoch"], week["scheduled_exit_epoch"]
            request = {"epoch": entry, "time_msc": entry * 1000, "reason": "entry_request",
                       "scheduled_exit_epoch": close, "balance": balance}
            self.requests.append(request)
            self.decisions += [dict(request), dict(request, reason="entry_filled", time_msc=entry * 1000 + 150)]
            self.positions.append({"position_id": str(index + 1), "open_epoch": entry, "open_time_msc": entry * 1000 + 150,
                                   "close_epoch": close, "close_time_msc": close * 1000,
                                   "closed": True, "end_of_test_liquidation": False, "exit_reason": "scheduled/EA",
                                   "gross_profit": profit + 10, "commission": -2, "swap": -7, "fee": -1,
                                   "net_profit": profit, "scheduled_exit_epoch": close})
            balance += profit
        self.result = {"candidate": self.candidate, "start": self.start, "end_exclusive": self.end,
                       "trades": self.positions, "entry_requests": self.requests,
                       "metrics": {"initial_balance": 10000, "net_profit": 0},
                       "native": {"manifest": {"model": 4}}}

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        (self.root / "SELECTION.json").write_text(json.dumps({"unique_configurations": 345}), encoding="utf-8")
        (self.folder / "results.json").write_text(json.dumps(self.result), encoding="utf-8")
        fields = sorted({key for row in self.decisions for key in row}) or ["reason", "epoch", "scheduled_exit_epoch"]
        with gzip.open(self.folder / "decisions.csv.gz", "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.decisions)

    def analyze(self):
        self.save()
        return cash_mc.analyze_cash_only(self.root, "fixture", paths=40)

    def test_known_cash_all_weeks_remains_valid_without_any_m1_file(self):
        value = self.analyze()
        self.assertEqual(value["status"], "complete_closed_balance_cash_diagnostics")
        self.assertEqual(value["coverage"]["scheduled_weeks"], 2)
        self.assertEqual(value["coverage"]["missing_week_ids"], [])
        self.assertFalse(value["coverage"]["m1_equity_read"])
        self.assertAlmostEqual(value["diagnostics"]["summary"]["ending_balance_usd"], 10000)

    def test_costs_once_and_actual_pre_request_cash_and_trial_count(self):
        value = self.analyze()
        a, b = value["normalization_audit"]
        self.assertEqual(a["native_net_profit"], 110)
        self.assertEqual(b["before_entry_request_balance"], 10110)
        self.assertAlmostEqual(b["account_return"], -110 / 10110)
        self.assertEqual(value["diagnostics"]["deflated_sharpe"]["tested_configurations"], 345)
        self.assertEqual(value["cash_reconciliation"]["difference"], 0)

    def test_no_floating_proxy_is_present_anywhere_in_output(self):
        value = self.analyze()
        encoded = json.dumps(value)
        self.assertNotIn('"max_sampled_equity_dd_pct"', encoded)
        self.assertNotIn('"probability_ruin_pct"', encoded)
        self.assertIn('"resampled_closed_cash_exhaustion_pct"', encoded)
        self.assertEqual(value["diagnostics"]["floating_equity_drawdown"]["value"], None)
        self.assertEqual(value["prop_account_probabilities"]["value"], None)
        self.assertFalse(value["methodological_supplement"]["promotion_gate_waiver"])

    def test_mc_joint_return_pf_and_closed_dd_are_available(self):
        value = self.analyze()["diagnostics"]
        for block in ("1", "5", "10"):
            distributions = value["block_bootstrap"][block]["distributions"]
            self.assertIn("return_pct", distributions)
            self.assertIn("pf", distributions)
            self.assertIn("max_closed_dd_pct", distributions)
            self.assertNotIn("max_sampled_equity_dd_pct", distributions)
        self.assertGreater(value["summary"]["max_closed_dd_pct"], 0)

    def test_unknown_week_remains_missing_and_conditional_is_labelled(self):
        self.positions.pop()
        self.requests.pop()
        self.decisions = self.decisions[:2]
        self.result["metrics"]["net_profit"] = 110
        value = self.analyze()
        self.assertEqual(value["status"], "unavailable_incomplete_closed_cash_history")
        self.assertEqual(value["coverage"]["missing_week_ids"], ["2026-01-09"])
        self.assertIn("Conditional", value["conditional_complete_cash_week_sensitivity"]["label"])

    def test_missing_entry_request_endpoint_is_not_guessed(self):
        self.requests.pop(0)
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_forced_test_end_endpoint_is_not_natural_cash_completion(self):
        self.positions[-1]["end_of_test_liquidation"] = True
        value = self.analyze()
        self.assertEqual(value["coverage"]["missing_week_ids"], ["2026-01-09"])

    def test_open_position_endpoint_is_unavailable(self):
        self.positions[-1]["closed"] = False
        self.positions[-1]["close_epoch"] = None
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_documented_filter_zero_is_allowed(self):
        self.positions.pop()
        request = self.requests.pop()
        self.decisions = self.decisions[:2] + [dict(request, reason="skip_signal_not_bullish")]
        self.candidate["entry_mode"] = 1
        self.result["metrics"]["net_profit"] = 110
        value = self.analyze()
        self.assertFalse(value["coverage"]["missing_week_ids"])
        self.assertEqual(value["coverage"]["documented_zero_weeks"], {"2026-01-09": "skip_signal_not_bullish"})

    def test_gap_or_failed_entry_cannot_be_zero(self):
        self.positions.pop()
        request = self.requests.pop()
        self.result["metrics"]["net_profit"] = 110
        for reason in ("skip_missing_entry_minute", "entry_rejected", "skip_entry_feature_warmup_or_incomplete"):
            with self.subTest(reason=reason):
                self.decisions = self.decisions[:2] + [dict(request, reason=reason)]
                self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_cost_or_case_cash_mismatch_stays_missing(self):
        self.positions[0]["swap"] = -100
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])
        self.positions[0]["swap"] = -7
        self.result["metrics"]["net_profit"] = 100
        self.assertTrue(self.analyze()["coverage"]["global_issues"])

    def test_dst_calendar_and_incomplete_last_week(self):
        rows, _ = nr.weekend_calendar(self.candidate, "2026-03-06", "2026-03-10")
        self.assertEqual(rows[0]["duration_hours"], 47)
        rows, censored = nr.weekend_calendar(self.candidate, "2026-10-16", "2026-10-17")
        self.assertEqual(rows, [])
        self.assertEqual(censored[0]["week_id"], "2026-10-16")

    def test_no_intratrade_path_is_passed_to_mc(self):
        self.save()
        original = cash_mc.robustness.analyze_robustness
        calls = []
        def capture(records, **kwargs):
            calls.append(records)
            return original(records, **kwargs)
        with patch.object(cash_mc.robustness, "analyze_robustness", side_effect=capture):
            cash_mc.analyze_cash_only(self.root, "fixture", paths=3)
        self.assertTrue(calls)
        self.assertTrue(all("intratrade_path" not in record for call in calls for record in call))

    def test_reads_only_explicit_tag_and_does_not_write(self):
        self.save()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        cash_mc.analyze_cash_only(self.root, "fixture", paths=3)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        with self.assertRaises(ValueError):
            cash_mc.analyze_cash_only(self.root, "..", paths=3)


if __name__ == "__main__":
    unittest.main()
