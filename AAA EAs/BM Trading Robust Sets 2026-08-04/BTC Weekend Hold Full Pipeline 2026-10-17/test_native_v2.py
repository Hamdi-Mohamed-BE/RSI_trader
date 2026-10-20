"""Offline regression checks for the versioned closed-feature iteration repair."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("weekend_native_v2_under_test", ROOT / "native_v2.py")
n = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(n)


class NativeV2Tests(unittest.TestCase):
    def test_original_frozen_runner_is_unchanged(self):
        self.assertEqual(n.sha(ROOT / "native.py"), n.FROZEN_ORIGINAL_NATIVE_SHA256)

    def test_versioned_source_mapping_and_no_api(self):
        source = (ROOT / "native_v2.py").read_text(encoding="utf-8")
        self.assertIn('_execute_locked("BtcWeekendV2"', source)
        self.assertIn('("Export", "BtcWeekendV2")', source)
        self.assertNotIn('import MetaTrader5', source)
        ea = (ROOT / "EA/BtcWeekendV2.mq5").read_text(encoding="utf-8")
        self.assertIn('!MQLInfoInteger(MQL_TESTER)', ea)
        self.assertIn('last_bar+feature_seconds:InpHistoryFrom', ea)
        self.assertNotIn('last_bar+1:InpHistoryFrom', ea)

    def test_daily_and_hourly_iteration_do_not_request_between_bar_opens(self):
        def bounds(last, seconds, now):
            start, latest = last + seconds, now - seconds
            return None if start > latest else (start, latest)
        day = int(datetime(2024, 10, 16, tzinfo=timezone.utc).timestamp())
        self.assertIsNone(bounds(day, 86400, day + 86400 + 300))
        self.assertEqual(bounds(day, 86400, day + 2*86400), (day + 86400, day + 86400))
        self.assertIsNone(bounds(day, 3600, day + 3600 + 300))
        self.assertEqual(bounds(day, 3600, day + 7200), (day + 3600, day + 3600))

    def test_real_missing_closed_bar_is_explicit_not_a_swallowed_error(self):
        source = (ROOT / "EA/BtcWeekendV2.mq5").read_text(encoding="utf-8")
        self.assertIn('n<0 && GetLastError()!=4401', source)
        self.assertIn('Decision("missing_completed_feature_bar"', source)
        self.assertIn('skip_stale_entry_feature', source)
        self.assertIn('skip_entry_feature_warmup_or_incomplete', source)

    def test_parameters_and_ny_schedule_are_unchanged(self):
        original_spec = importlib.util.spec_from_file_location("original_native_v2_test", ROOT / "native.py")
        old = importlib.util.module_from_spec(original_spec)
        original_spec.loader.exec_module(old)
        cfg = old.CANDIDATE_DEFAULTS | {"timeframe_minutes": 1440, "entry_mode": 1, "exit_minute_ny": 1080}
        self.assertEqual(old.candidate_inputs(cfg, "fixture-v2", "2024-10-17", "2026-10-17"), n.candidate_inputs(cfg, "fixture-v2", "2024-10-17", "2026-10-17"))
        for day in ("2024-03-08", "2024-06-07", "2024-11-01"):
            self.assertEqual(old.ny_weekend_schedule(day), n.ny_weekend_schedule(day))


if __name__ == "__main__":
    unittest.main()
