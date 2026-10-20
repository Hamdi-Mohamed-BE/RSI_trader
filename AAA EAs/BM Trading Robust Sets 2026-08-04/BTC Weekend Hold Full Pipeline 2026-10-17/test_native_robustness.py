"""Synthetic fixtures only: no real native outcomes, prices, terminal or network."""
import csv
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import native_robustness as nr


def epoch(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


class NativeRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case = self.root / "native" / "fixture"
        self.case.mkdir(parents=True)
        self.candidate = {"entry_minute_ny": 1020, "exit_minute_ny": 1020, "filter_mode": 0, "entry_mode": 0}
        self.start, self.end = "2026-01-02", "2026-01-06"
        self.schedule, _ = nr.weekend_calendar(self.candidate, self.start, self.end)
        self.entry = self.schedule[0]["entry_epoch"]
        self.sunday = self.schedule[0]["scheduled_exit_epoch"]
        self.close = self.entry + 121
        self.position = {"position_id": "77", "open_epoch": self.entry, "open_time_msc": self.entry * 1000 + 150,
                         "close_epoch": self.close, "close_time_msc": self.close * 1000,
                         "closed": True, "end_of_test_liquidation": False, "exit_reason": "SL",
                         "gross_profit": 120, "commission": -2, "swap": -7, "fee": -1,
                         "net_profit": 110, "scheduled_exit_epoch": self.sunday}
        self.request = {"epoch": self.entry, "time_msc": self.entry * 1000, "reason": "entry_request",
                        "scheduled_exit_epoch": self.sunday, "balance": 10000, "equity": 10000}
        self.decisions = [dict(self.request), {"epoch": self.entry, "time_msc": self.entry * 1000 + 150,
                          "reason": "entry_filled", "scheduled_exit_epoch": self.sunday}]
        self.equity = [{"epoch": self.entry, "time_msc": self.entry * 1000 + 150,
                        "position_id": "77", "equity": 9998},
                       {"epoch": self.entry + 60, "time_msc": (self.entry + 60) * 1000,
                        "position_id": "77", "equity": 9700},
                       {"epoch": self.entry + 120, "time_msc": (self.entry + 120) * 1000,
                        "position_id": "77", "equity": 10050}]
        self.result = {"tag": "fixture", "candidate": self.candidate, "start": self.start,
                       "end_exclusive": self.end, "trades": [self.position], "entry_requests": [self.request],
                       "metrics": {"initial_balance": 10000, "net_profit": 110},
                       "native": {"manifest": {"model": 4}}}
        self.selection = {"unique_configurations": 321}

    def tearDown(self):
        self.tmp.cleanup()

    def csv_gz(self, path, rows):
        fields = sorted({key for row in rows for key in row}) or ["epoch", "reason", "scheduled_exit_epoch"]
        with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def save(self):
        (self.root / "SELECTION.json").write_text(json.dumps(self.selection), encoding="utf-8")
        (self.case / "results.json").write_text(json.dumps(self.result), encoding="utf-8")
        self.csv_gz(self.case / "decisions.csv.gz", self.decisions)
        self.csv_gz(self.case / "equity-m1.csv.gz", self.equity)

    def analyze(self):
        self.save()
        return nr.analyze_native_case(self.root, "fixture", paths=30)

    def test_native_cash_costs_counted_once_and_request_balance(self):
        value = self.analyze()
        self.assertEqual(value["status"], "complete_native_diagnostics")
        self.assertAlmostEqual(value["normalization_audit"][0]["account_return"], .011)
        self.assertAlmostEqual(value["diagnostics"]["summary"]["return_pct"], 1.1)
        self.assertEqual(value["tested_unique_configurations"], 321)
        self.assertEqual(value["diagnostics"]["deflated_sharpe"]["tested_configurations"], 321)
        self.assertEqual(value["cash_reconciliation"]["difference"], 0)

    def test_sampled_equity_drawdown_uses_owned_account_cash(self):
        self.equity.append({"epoch": self.entry + 70, "time_msc": (self.entry + 70) * 1000,
                            "position_id": "999", "equity": 1})
        value = self.analyze()
        self.assertAlmostEqual(value["diagnostics"]["summary"]["max_sampled_equity_dd_pct"], 3)
        self.assertEqual(value["normalization_audit"][0]["owned_equity_samples"], 3)

    def test_missing_owned_held_minute_blocks_primary_not_zero(self):
        self.equity.pop(1)
        value = self.analyze()
        self.assertEqual(value["diagnostics"]["status"], "unavailable_incomplete_history")
        self.assertEqual(value["normalization_audit"][0]["missing_fully_held_minutes"], 1)
        self.assertEqual(value["coverage"]["documented_zero_weeks"], {})

    def test_unexplained_no_trade_week_is_missing(self):
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = []
        self.equity = []
        value = self.analyze()
        self.assertEqual(value["coverage"]["missing_week_ids"], ["2026-01-02"])

    def test_applicable_signal_skip_is_documented_zero(self):
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.candidate["entry_mode"] = 1
        self.decisions = [dict(self.request, reason="skip_signal_not_bullish")]
        value = self.analyze()
        self.assertEqual(value["coverage"]["missing_week_ids"], [])
        self.assertEqual(value["coverage"]["documented_zero_weeks"], {"2026-01-02": "skip_signal_not_bullish"})
        self.assertEqual(value["diagnostics"]["summary"]["trades"], 0)

    def test_wrong_filter_reason_cannot_be_zero(self):
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = [dict(self.request, reason="skip_ema50")]
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_ambiguous_warmup_is_missing(self):
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = [dict(self.request, reason="skip_entry_feature_warmup_or_incomplete")]
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_new_receipt_proves_initial_warmup_but_not_gaps(self):
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = [dict(self.request, reason="skip_entry_feature_warmup_or_incomplete",
                               processed_feature_bars=10, required_entry_lookback=50, entry_lookback_valid=0)]
        self.assertFalse(self.analyze()["coverage"]["missing_week_ids"])
        self.decisions[0]["processed_feature_bars"] = 100
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_proven_percentile_warmup_is_zero(self):
        self.candidate["filter_mode"] = 6
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = [dict(self.request, reason="skip_percentile_warmup", valid_atr_ratios=20)]
        self.assertFalse(self.analyze()["coverage"]["missing_week_ids"])
        self.decisions[0]["valid_atr_ratios"] = 100
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_unknown_spread_and_rejected_entries_never_zero(self):
        for reason in ("skip_unknown_nonpositive_spread", "entry_rejected", "skip_insufficient_native_margin"):
            with self.subTest(reason=reason):
                self.result["trades"] = []
                self.result["entry_requests"] = []
                self.result["metrics"]["net_profit"] = 0
                self.decisions = [dict(self.request, reason=reason)]
                self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_duplicate_request_is_not_guessed(self):
        self.result["entry_requests"].append(dict(self.request))
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_after_fill_balance_not_used_as_request_cash(self):
        self.request["balance"] = 9998
        value = self.analyze()
        self.assertTrue(value["coverage"]["missing_week_ids"])
        self.assertEqual(value["normalization_audit"], [])

    def test_cost_component_mismatch_blocks(self):
        self.position["commission"] = -100
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_case_cash_mismatch_blocks(self):
        self.result["metrics"]["net_profit"] = 100
        self.assertTrue(self.analyze()["coverage"]["global_issues"])

    def test_decision_receipt_counts_must_reconcile(self):
        self.result["decision_counts"] = {"entry_request": 2, "entry_filled": 1}
        self.assertTrue(self.analyze()["coverage"]["global_issues"])

    def test_sequential_before_entry_balances_reproduce_native_compounding(self):
        self.result["end_exclusive"] = "2026-01-13"
        second = {key: value for key, value in self.position.items()}
        shift = 7 * 86400
        for key in ("open_epoch", "close_epoch", "scheduled_exit_epoch"):
            second[key] += shift
        for key in ("open_time_msc", "close_time_msc"):
            second[key] += shift * 1000
        second.update(position_id="88", gross_profit=-100, commission=-2, swap=-7, fee=-1, net_profit=-110)
        request = dict(self.request, epoch=self.entry + shift, time_msc=(self.entry + shift) * 1000,
                       balance=10110, scheduled_exit_epoch=self.sunday + shift)
        self.result["trades"] = [second, self.position]  # Do not trust input ordering.
        self.result["entry_requests"].append(request)
        self.result["metrics"]["net_profit"] = 0
        self.decisions += [request, dict(request, reason="entry_filled")]
        self.equity += [dict(row, epoch=row["epoch"] + shift, time_msc=row["time_msc"] + shift * 1000,
                             position_id="88", equity=float(row["equity"]) + 110) for row in self.equity.copy()]
        value = self.analyze()
        self.assertEqual(value["coverage"]["missing_week_ids"], [])
        self.assertAlmostEqual(value["diagnostics"]["summary"]["ending_balance_usd"], 10000)
        self.assertEqual(value["normalization_audit"][1]["before_entry_request_balance"], 10110)

    def test_forced_close_and_open_position_do_not_certify_complete_week(self):
        self.position["end_of_test_liquidation"] = True
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])
        self.position["end_of_test_liquidation"] = False
        self.position["closed"] = False
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_dst_47_and_49_hours(self):
        spring, _ = nr.weekend_calendar(self.candidate, "2026-03-06", "2026-03-10")
        fall, _ = nr.weekend_calendar(self.candidate, "2026-10-30", "2026-11-03")
        self.assertEqual(spring[0]["duration_hours"], 47)
        self.assertEqual(fall[0]["duration_hours"], 49)

    def test_administratively_censored_week_not_missing_or_zero(self):
        rows, censored = nr.weekend_calendar(self.candidate, "2026-10-16", "2026-10-17")
        self.assertEqual(rows, [])
        self.assertEqual(censored[0]["week_id"], "2026-10-16")

    def test_sunday_exit_equal_end_is_censored_as_native_ea(self):
        rows, censored = nr.weekend_calendar(self.candidate, "2026-01-02", "2026-01-04T22:00:00+00:00")
        self.assertEqual(rows, [])
        self.assertEqual(len(censored), 1)

    def test_skip_in_wrong_minute_is_not_zero(self):
        self.candidate["entry_mode"] = 1
        self.result["trades"] = []
        self.result["entry_requests"] = []
        self.result["metrics"]["net_profit"] = 0
        self.decisions = [dict(self.request, reason="skip_signal_not_bullish", epoch=self.entry + 60)]
        self.assertTrue(self.analyze()["coverage"]["missing_week_ids"])

    def test_rejected_or_duplicate_ids_and_invalid_selection(self):
        self.selection["unique_configurations"] = 0
        self.save()
        with self.assertRaises(ValueError):
            nr.analyze_native_case(self.root, "fixture", paths=2)
        with self.assertRaises(ValueError):
            nr.analyze_native_case(self.root, "../fixture", paths=2)
        with self.assertRaises(ValueError):
            nr.analyze_native_case(self.root, "..", paths=2)

    def test_audit_never_saves_or_modifies_inputs(self):
        self.save()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        nr.analyze_native_case(self.root, "fixture", paths=5)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
