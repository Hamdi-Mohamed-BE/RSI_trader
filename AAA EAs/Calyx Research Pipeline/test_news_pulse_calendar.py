from __future__ import annotations

import unittest
from datetime import date

from news_pulse_calendar import (
    CalendarCoverageError,
    _assert_complete_coverage,
    _assert_official_event_times,
    _calendar_include,
    _merge_with_base,
)


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
    def test_confirmed_official_event_times_are_sufficient_for_news_pulse(self) -> None:
        calendar = payload()
        calendar["data_quality"]["point_in_time_safe"] = False
        calendar["data"] = [
            {
                "release": "inflation",
                "announcement_datetime": 1789129800,
                "release_date_confirmed": True,
            }
        ]
        _assert_official_event_times(date(2026, 9, 5), date(2026, 9, 10), calendar)

    def test_complete_window_is_accepted(self) -> None:
        calendar = payload()
        indicators = {kind: payload(cutoff="2026-06-12") for kind in ("NFP", "CPI", "FOMC")}
        _assert_complete_coverage(date(2026, 6, 12), date(2026, 9, 10), calendar, indicators)

    def test_verified_base_events_survive_calendar_extension(self) -> None:
        base = {
            "provider": "FXMacroData MCP",
            "coverage": {
                "start_date": "2026-06-12",
                "end_date": "2026-09-10",
                "complete_for_requested_window": True,
            },
            "events": [{"kind": "NFP", "epoch": 1788525000, "source": "BLS"}],
            "receipts": [],
            "calendar_sha256": "old",
        }
        extension = {
            "provider": "FXMacroData MCP",
            "coverage": {
                "start_date": "2026-09-04",
                "end_date": "2026-09-11",
                "complete_for_requested_window": True,
            },
            "events": [{"kind": "CPI", "epoch": 1789129800, "source": "BLS"}],
            "receipts": [],
        }
        merged = _merge_with_base(extension, base)
        self.assertEqual(merged["event_count"], 2)
        self.assertEqual(merged["coverage"]["start_date"], "2026-06-12")
        self.assertEqual(merged["coverage"]["end_date"], "2026-09-11")

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
