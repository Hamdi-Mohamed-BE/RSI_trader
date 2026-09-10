from __future__ import annotations

import unittest
from datetime import date

from news_pulse_calendar import CalendarCoverageError, _assert_complete_coverage, _calendar_include


def payload(*, cutoff: str | None = None) -> dict:
    result = {
        "requested_window_has_data": True,
        "data_quality": {
            "is_official": True,
            "is_proxy": False,
            "is_fallback": False,
            "is_stale": False,
            "has_announcement_datetime": True,
            "point_in_time_safe": True,
            "missing_announcement_datetime_count": 0,
            "latest_available_date": "2026-09-10",
        },
    }
    if cutoff:
        result["freemium_window"] = {"applied": True, "cutoff_date": cutoff}
    return result


class NewsPulseCalendarTests(unittest.TestCase):
    def test_complete_window_is_accepted(self) -> None:
        calendar = payload()
        indicators = {kind: payload(cutoff="2026-06-12") for kind in ("NFP", "CPI", "FOMC")}
        _assert_complete_coverage(date(2026, 6, 12), date(2026, 9, 10), calendar, indicators)

    def test_window_before_anonymous_cutoff_fails_closed(self) -> None:
        calendar = payload()
        indicators = {kind: payload(cutoff="2026-06-12") for kind in ("NFP", "CPI", "FOMC")}
        with self.assertRaises(CalendarCoverageError):
            _assert_complete_coverage(date(2026, 6, 11), date(2026, 9, 10), calendar, indicators)

    def test_include_contains_exact_epoch_and_provenance(self) -> None:
        manifest = {
            "coverage": {"start_date_key": 20260612, "end_date_key": 20260910},
            "event_count": 1,
            "calendar_sha256": "abc123",
            "generated_at_utc": "2026-09-10T00:00:00+00:00",
            "events": [{"kind": "NFP", "epoch": 1788525000}],
        }
        include = _calendar_include(manifest)
        self.assertIn("1788525000", include)
        self.assertIn('"NFP"', include)
        self.assertIn("abc123", include)


if __name__ == "__main__":
    unittest.main()
