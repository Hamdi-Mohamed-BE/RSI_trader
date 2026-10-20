"""Offline native-infrastructure fixtures. No MT5 process or API is invoked."""
import importlib.util
from pathlib import Path
import struct
import csv
import tempfile
import unittest
from unittest import mock

import numpy as np

SPEC = importlib.util.spec_from_file_location("weekend_native_under_test", Path(__file__).with_name("native.py"))
n = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(n)


class NativeInfrastructureTests(unittest.TestCase):
    def test_packed_little_endian_rate_schema_is52_bytes(self):
        self.assertEqual(n.RATE_DTYPE.itemsize, 52)
        data = struct.pack("<qddddqi", 1514764800, 14000., 14200., 13900., 14100., 123, 2500)
        row = np.frombuffer(data, dtype=n.RATE_DTYPE)[0]
        self.assertEqual(int(row["time"]), 1514764800)
        self.assertEqual(float(row["open"]), 14000.)
        self.assertEqual(int(row["tick_volume"]), 123)
        self.assertEqual(int(row["spread"]), 2500)

    def test_tag_rejects_paths_and_command_fragments(self):
        for value in ("", "../x", "a/b", "a\\b", 'x"', "x y", ".hidden"):
            with self.assertRaises(ValueError):
                n.valid_tag(value)
        self.assertEqual(n.valid_tag("raw-model4-20261017"), "raw-model4-20261017")

    def test_inputs_accept_native_datetime_and_bool_formatting(self):
        self.assertTrue(n._input_equal("2018.01.01 00:00:00", "2018.01.01 00:00"))
        self.assertTrue(n._input_equal("true", "1"))
        self.assertTrue(n._input_equal(150, "150.0"))
        self.assertFalse(n._input_equal(150, "151"))
        self.assertTrue(n._input_equal("2018.01.01 00:00:00", "1514764800"))
        self.assertFalse(n._input_equal("2018.01.01 00:00:00", "1514764801"))

    def test_runtime_private_header_only_accepts_isolated_trial16(self):
        with mock.patch.object(n, "text", return_value="[Common]\nLogin=12345\nServer=Exness-MT5Trial16\n[Experts]\nEnabled=0\n"):
            header = n._private_header()
            self.assertIn("Server=Exness-MT5Trial16", header)
        with mock.patch.object(n, "text", return_value="[Common]\nLogin=12345\nServer=OtherServer\n[Experts]\n"):
            with self.assertRaises(RuntimeError):
                n._private_header()

    def test_no_import_or_exporter_trading_api(self):
        source = Path(n.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import MetaTrader5", source)
        ea = (Path(n.__file__).parent / "EA/Export.mq5").read_text(encoding="utf-8")
        self.assertIn("MQL_TESTER", ea)
        self.assertIn("double OnTester()", ea)
        self.assertNotIn("OrderSend(", ea)
        self.assertNotIn("CTrade", ea)

    def test_date_inputs_and_npz_roundtrip(self):
        self.assertEqual(n.date_input("2026-10-17"), "2026.10.17 00:00:00")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rates.npz"
            array = np.array([(1514764800, 1., 2., .5, 1.5, 10, 25)], dtype=n.RATE_DTYPE)
            np.savez_compressed(path, rates=array)
            with np.load(path, allow_pickle=False) as saved:
                np.testing.assert_array_equal(saved["rates"], array)

    def test_ny_weekend_has_dst_47_48_and49_hour_holds(self):
        for date, hours in (("2024-03-08", 47), ("2024-06-07", 48), ("2024-11-01", 49)):
            start, end = n.ny_weekend_schedule(date)
            self.assertEqual(end - start, hours * 3600)
        with self.assertRaises(ValueError):
            n.ny_weekend_schedule("2024-03-09")

    def test_cash_notional_default_is_not_stop_risk(self):
        p, inputs = n.candidate_inputs({}, "raw", "2024-10-17", "2026-10-17")
        self.assertEqual(p["stop_mode"], 0)
        self.assertEqual(inputs["InpSizingMode"], 0)
        self.assertEqual(inputs["InpNotionalMultiple"], 1)
        for override in ({"target_rr": 1}, {"management_mode": 1}):
            with self.assertRaises(ValueError):
                n.candidate_inputs(override, "raw", "2024-10-17", "2026-10-17")
        with self.assertRaises(ValueError):
            n.candidate_inputs({}, "raw", "2024-10-17", "2026-10-17", sizing_mode=1)

    def test_unknown_fields_do_not_silently_change_native_rules(self):
        with self.assertRaises(ValueError):
            n.candidate_inputs({"pullback": True}, "raw", "2024-10-17", "2026-10-17")
        p, inputs = n.candidate_inputs({"timeframe_minutes": 3, "entry_minute_ny": 1005}, "raw", "2024-10-17", "2026-10-17")
        self.assertEqual(inputs["InpTimeframeMinutes"], 3)
        self.assertEqual(p["entry_minute_ny"], 1005)

    def test_equity_audit_streams_and_retains_initial_peak(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "equity.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["epoch", "equity"])
                writer.writeheader()
                writer.writerows([{"epoch": 1, "equity": 9900}, {"epoch": 2, "equity": 11000}, {"epoch": 3, "equity": 10000}])
            result = n._equity_audit(path)
            self.assertEqual(result["snapshots"], 3)
            self.assertEqual(result["cash"], 1000)
            self.assertAlmostEqual(result["pct"], 1000 / 11000 * 100)

    def test_strategy_is_tester_only_and_causal_management_has_millisecond_guard(self):
        source = (Path(n.__file__).parent / "EA/BtcWeekend.mq5").read_text(encoding="utf-8")
        self.assertIn('!MQLInfoInteger(MQL_TESTER)', source)
        self.assertIn('(long)feature_end*1000<=actual_entry_msc', source)
        self.assertIn('(long)b.time*1000>=actual_entry_msc', source)
        self.assertIn('MathFloor(MathMin(raw,maximum)/step', source)
        self.assertIn('scheduled_exit>=InpTo', source)
        self.assertNotIn('MathCeil(MathMin(raw,maximum)/step', source)
        self.assertIn('expected=(datetime)((long)tick.time/300*300-300)', source)
        self.assertIn('filter_spread_points*_Point/filter_spread_close*100', source)
        self.assertNotIn('spread/tick.bid*100>InpFilterValue', source)

    def test_position_id_ledger_includes_opening_costs_fee_and_weighted_partials(self):
        def deal(ticket, entry, volume, price, at, profit=0, commission=0, swap=0, fee=0, reason=3):
            return {"ticket": str(ticket), "order": "10" if entry == 0 else str(ticket), "position_id": "100", "epoch": str(at), "time_msc": str(at*1000), "symbol": "BTCUSD", "type": "0" if entry == 0 else "1", "entry": str(entry), "reason": str(reason), "magic": "86701701", "volume": str(volume), "price": str(price), "profit": str(profit), "commission": str(commission), "swap": str(swap), "fee": str(fee), "comment": "research"}
        deals = [deal(10, 0, .1, 100000, 100, commission=-1, fee=-.1), deal(11, 1, .04, 101000, 200, profit=40, commission=-.4, swap=-.2), deal(12, 1, .06, 102000, 300, profit=120, commission=-.6, swap=-.3)]
        orders = [{"ticket": "10", "sl": "99000", "tp": "103000"}]
        rows = n._positions_from_deals(deals, orders, [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["closed"])
        self.assertEqual(rows[0]["exit_fills"], 2)
        self.assertAlmostEqual(rows[0]["close_price"], 101600)
        self.assertAlmostEqual(rows[0]["net_profit"], 157.4)
        self.assertEqual(rows[0]["initial_r_points"], 1000)

    def test_feature_prefix_truncates_before_aggregation_and_preserves_missing_constituents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data_dir = root / "data"
            data_dir.mkdir()
            first = n.epoch("2018-01-01")
            source = np.array([(first+i*60, 100., 101. if i<6 else 99999., 99., 100., 10, 2) for i in (0,2,3,4,5,6,7,8)], dtype=n.RATE_DTYPE)
            path = data_dir / "BTCUSD-M1.npz"
            np.savez_compressed(path, rates=source)
            n.save(root / "DATA.json", {"requested_start": "2018-01-01", "coverage": [{"timeframe": "M1", "path": "data/BTCUSD-M1.npz", "sha256": n.sha(path)}]})
            candidate = n.CANDIDATE_DEFAULTS | {"timeframe_minutes": 3, "entry_mode": 1}
            with mock.patch.object(n, "ROOT", root), mock.patch.object(n, "_common", return_value=root / "common"):
                inputs, receipt = n.prepare_feature_prefix(candidate, "prefix-fixture", "2018-01-01T00:06:00")
                packed = np.fromfile(root / "common/feature-prefix.bin", dtype=n.PREFIX_DTYPE)
            self.assertEqual(n.PREFIX_DTYPE.itemsize, 56)
            self.assertEqual(inputs["InpWarmRows"], 2)
            self.assertEqual(list(packed["complete"]), [0, 1])
            self.assertEqual(float(np.max(packed["high"])), 101.)
            self.assertTrue(receipt["all_bars_end_at_or_before_case_start"])
            self.assertEqual(receipt["last_bar_end_epoch"], first + 360)

    def test_no_feature_raw_does_not_read_any_historical_prefix(self):
        with mock.patch.object(n, "read", side_effect=AssertionError("No historical input should be read")):
            inputs, receipt = n.prepare_feature_prefix(dict(n.CANDIDATE_DEFAULTS), "raw", "2024-10-17")
        self.assertFalse(receipt["needed"])
        self.assertEqual(inputs["InpWarmRows"], 0)


if __name__ == "__main__":
    unittest.main()
