import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import data_split as d


class DataSplitTests(unittest.TestCase):
    def test_current_example(self):
        m = d.research_split("2019-10-06", "2026-10-06")
        self.assertEqual(m["oos"], dict(start="2024-10-06", end_exclusive="2026-10-06", calendar_years=2))
        self.assertEqual(m["validation"], dict(start="2023-10-06", end_exclusive="2024-10-06"))
        self.assertEqual(m["development"]["end_exclusive"], "2023-10-06")
        d.validate_split(m)
        d.validate_report_window(m, "2024.10.06", "2026.10.06")

    def test_five_year_history(self):
        m = d.research_split("2021-10-06", "2026-10-06")
        self.assertEqual(m["development"], dict(start="2021-10-06", end_exclusive="2023-10-06"))

    def test_leap_day_calendar_anniversary(self):
        m = d.research_split("2018-01-01", "2024-02-29")
        self.assertEqual(m["oos"]["start"], "2022-02-28")
        self.assertNotEqual((date(2024, 2, 29) - date(2022, 2, 28)).days, 730)

    def test_insufficient_history_rejected(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            d.research_split("2023-10-06", "2026-10-06")

    def test_short_report_and_overlap_rejected(self):
        m = d.research_split("2019-10-06", "2026-10-06")
        with self.assertRaisesRegex(ValueError, "TWO"):
            d.validate_report_window(m, "2025-10-06", "2026-10-06")
        bad = copy.deepcopy(m)
        bad["validation"]["end_exclusive"] = "2025-10-06"
        with self.assertRaisesRegex(ValueError, "validation"):
            d.validate_split(bad)

    def test_policy_cannot_silently_reduce_oos(self):
        policy = json.loads(d.POLICY.read_text())
        policy["data_split"]["final_out_of_sample_years"] = 1
        with TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            path.write_text(json.dumps(policy))
            with patch.object(d, "POLICY", path), self.assertRaisesRegex(ValueError, "TWO"):
                d.research_split("2019-10-06", "2026-10-06")

    def test_default_end_is_today_utc(self):
        m = d.research_split("2019-01-01")
        self.assertEqual(m["oos"]["end_exclusive"], datetime.now(timezone.utc).date().isoformat())

    def test_frozen_manifest_is_idempotent_and_cannot_be_overwritten(self):
        with TemporaryDirectory() as folder:
            output = Path(folder) / "data-split.json"
            argv = ["data_split.py", "--history-start", "2021-10-06", "--end-exclusive", "2026-10-06", "--output", str(output)]
            with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                d.main()
            original = output.read_bytes()
            with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                d.main()
            self.assertEqual(output.read_bytes(), original)
            changed = argv.copy()
            changed[changed.index("2026-10-06")] = "2026-10-07"
            with patch("sys.argv", changed), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                d.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
