"""Offline synthetic accounting tests; never imports or calls any trading API."""
from __future__ import annotations

import ast
import csv
import gzip
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fresh_offline_analyzer_tested", ROOT / "analyze.py")
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)

# Exercise only the pure grouping function; do not import a native runner.
group_source = ROOT.parent / "ORB and Range Breakout RR05 Comparison 2026-10-08" / "run.py"
tree = ast.parse(group_source.read_text(encoding="utf-8-sig"))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "trades_from_deals")
namespace = {}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(group_source) + "::pure-grouping-only", "exec"), namespace)
group_positions = namespace["trades_from_deals"]


def epoch(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp())


def deal(ticket, position, timestamp, entry, volume, gross=0, commission=0, swap=0, fee=0, comment=""):
    stamp = int(timestamp)
    return dict(
        deal=str(ticket), position_id=str(position), epoch=str(stamp // 1000),
        time_msc=str(stamp), entry=str(entry), type="0" if entry == 0 else "1",
        volume=str(volume), price="100.0", gross=str(gross), commission=str(commission),
        swap=str(swap), fee=str(fee), sl="95", tp="110", order=str(ticket), magic="123",
        reason="0", comment=comment, order_price_open="100", order_type="0",
    )


def minimal_position(net):
    return dict(net=net, exit_legs=1, partial=False, commission=0, swap=0, fee=0,
                open_epoch=1, close_epoch=61)


class IndependentAccountingTests(unittest.TestCase):
    def test_all_61_calendar_cash_days_and_zero_activity(self):
        metrics, daily, curve = analyzer.account_cash_metrics([], "2026-08-16", "2026-10-16")
        self.assertEqual(len(daily), 61)
        self.assertEqual(daily[0]["date"], "2026-08-16")
        self.assertEqual(daily[-1]["date"], "2026-10-15")
        self.assertTrue(all(day["net_profit"] == 0 for day in daily))
        self.assertEqual(metrics["final_balance"], 10000)
        self.assertEqual(metrics["max_closed_drawdown_cash"], 0)
        self.assertIsNone(metrics["closed_balance_daily_sharpe"])

    def test_entry_cost_partial_exit_costs_and_actual_cash_drawdown(self):
        opening = epoch("2026-08-17T09:00:00") * 1000
        rows = [
            deal(1, 101, opening, 0, 1, commission=-2, fee=-0.5),
            deal(2, 101, opening + 86400000, 1, 0.5, gross=10, commission=-0.25, swap=-0.5),
            deal(3, 101, opening + 172800000, 1, 0.5, gross=-4, commission=-0.25, fee=-0.5),
        ]
        positions, cash = group_positions([dict(d) for d in rows])
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["exit_legs"], 2)
        self.assertTrue(positions[0]["partial"])
        self.assertAlmostEqual(positions[0]["net"], 2)
        self.assertAlmostEqual(positions[0]["commission"], -2.5)
        self.assertAlmostEqual(positions[0]["swap"], -0.5)
        self.assertAlmostEqual(positions[0]["fee"], -1)
        stats = analyzer.position_metrics(positions)
        self.assertEqual(stats["positions"], 1)
        self.assertEqual(stats["exit_fills"], 2)
        self.assertEqual(stats["partial_positions"], 1)
        metrics, daily, curve = analyzer.account_cash_metrics(list(reversed(rows)), "2026-08-16", "2026-10-16")
        self.assertAlmostEqual(metrics["final_balance"], 10002)
        self.assertAlmostEqual(metrics["max_closed_drawdown_cash"], 4.75)
        self.assertEqual(stats["position_recognition_drawdown_cash"], 0)
        values = {day["date"]: day["net_profit"] for day in daily}
        self.assertEqual(values["2026-08-17"], -2.5)
        self.assertEqual(values["2026-08-18"], 9.25)
        self.assertEqual(values["2026-08-19"], -4.75)

    def test_breakevens_reset_both_streak_types(self):
        stats = analyzer.position_metrics([minimal_position(n) for n in [1, 2, 0, 3, -1, -1, 0, -1]])
        self.assertEqual(stats["max_win_streak"], 2)
        self.assertEqual(stats["max_loss_streak"], 2)
        self.assertEqual(stats["breakeven"], 2)
        self.assertEqual(stats["positions"], 8)

    def test_no_losses_pf_is_undefined_not_infinite_or_zero(self):
        stats = analyzer.position_metrics([minimal_position(n) for n in [1, 0, 2]])
        self.assertIsNone(stats["profit_factor"])
        self.assertEqual(stats["profit_factor_status"], "no_losing_positions")
        self.assertAlmostEqual(stats["win_rate_pct"], 200 / 3)
        empty = analyzer.position_metrics([])
        self.assertIsNone(empty["profit_factor"])
        self.assertIsNone(empty["win_rate_pct"])

    def test_distinct_position_ids_at_identical_open_time_do_not_merge(self):
        moment = epoch("2026-09-01T09:00:00") * 1000
        rows = [
            deal(10, 500, moment, 0, 1),
            deal(11, 501, moment, 0, 1),
            deal(12, 501, moment + 1000, 1, 1, gross=-3),
            deal(13, 500, moment + 2000, 1, 1, gross=5),
        ]
        positions, _ = group_positions(rows)
        self.assertEqual([p["position_id"] for p in positions], [501, 500])
        self.assertEqual([p["net"] for p in positions], [-3, 5])

    def test_duplicate_deal_ticket_is_rejected(self):
        moment = epoch("2026-09-01T09:00:00") * 1000
        a = deal(10, 500, moment, 0, 1)
        with self.assertRaises(AssertionError):
            group_positions([dict(a), dict(a)])

    def test_incomplete_exit_volume_is_rejected_not_called_closed(self):
        moment = epoch("2026-09-01T09:00:00") * 1000
        with self.assertRaises(AssertionError):
            group_positions([deal(1, 9, moment, 0, 1), deal(2, 9, moment + 1, 1, 0.5)])

    def test_forced_close_primary_natural_subset_and_millisecond_sort(self):
        op = epoch("2026-09-01T09:00:00") * 1000
        cl = epoch("2026-09-01T12:00:00") * 1000
        finish = epoch("2026-10-15T23:59:58") * 1000
        rows = [
            deal(1, 1, op, 0, 1, commission=-1),
            deal(2, 2, op, 0, 1, commission=-1),
            deal(3, 2, cl + 100, 1, 1, gross=-8),
            deal(4, 1, cl + 900, 1, 1, gross=5),
            deal(5, 3, op + 86400000, 0, 1),
            deal(6, 3, finish, 1, 1, gross=20, comment="end of test"),
        ]
        positions, cash = group_positions([dict(d) for d in rows])
        # Analyzer must establish true close order from CSV milliseconds itself.
        result = dict(
            tag="fixture", trades=list(reversed(positions)), inputs={}, seconds=0,
            native=dict(net_profit=15, equity_dd_pct=7.5, balance_dd_pct=1.5,
                        history_quality="synthetic fixture only"),
            flags={}, report_sha256="synthetic", binary_sha256="synthetic",
        )
        row = dict(slug="fixture", label="Synthetic fixture", symbol="FIXTURE", period="M1",
                   safe_by_design=False, dynamic_by_design=False, selected_risk_percent=1,
                   news=False, historical_loss_sizing=False, source="fixture", preset="fixture")
        with tempfile.TemporaryDirectory(prefix="calyx-accounting-fixture-") as temporary:
            folder = Path(temporary) / "native" / "fixture"
            folder.mkdir(parents=True)
            (folder / "journal.txt.gz").write_bytes(gzip.compress(b"Synthetic offline fixture; no trading API used."))
            with (folder / "deals.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with (folder / "equity.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["epoch", "balance", "equity"])
                writer.writerow([epoch("2026-08-16T00:00:00"), 10000, 10000])
                writer.writerow([finish // 1000, 10015, 10015])
            with patch.object(analyzer, "ROOT", Path(temporary)):
                member = analyzer.build_member(row, result, "2026-08-16", "2026-10-16")
        self.assertEqual([p["position_id"] for p in member["trades"]], [2, 1, 3])
        self.assertEqual(member["metrics"]["net_profit"], 15)
        self.assertEqual(member["natural_close_only_metrics"]["net_profit"], -5)
        self.assertEqual(member["quality"]["boundary_position_count"], 1)
        self.assertEqual(member["metrics"]["native_equity_drawdown_pct"], 7.5)
        self.assertAlmostEqual(member["metrics"]["max_closed_drawdown_cash"], 10)
        self.assertEqual(member["metrics"]["max_win_streak"], 2)
        self.assertEqual(member["quality"]["last_captured_native_snapshot_utc"], "2026-10-15T23:59:58+00:00")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentAccountingTests))
    receipt = dict(
        generated_at_utc=datetime.now(timezone.utc).isoformat(), tests_run=result.testsRun,
        successful=result.wasSuccessful(),
        failures=[dict(test=str(test), error=message) for test, message in result.failures],
        errors=[dict(test=str(test), error=message) for test, message in result.errors],
        source_hashes={name: sha256((ROOT / name).read_bytes()).hexdigest()
                       for name in ("analyze.py", "test_independent_accounting.py")},
        scope="Offline synthetic fixtures only; no terminal, account or network calls",
    )
    (ROOT / "INDEPENDENT-FIXTURE-TESTS.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)

