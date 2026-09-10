from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fxmacrodata import FXMacroDataClient


class StubClient(FXMacroDataClient):
    def __init__(self) -> None:
        super().__init__(base_url="https://example.invalid")

    def announcements(self, event: str, *, limit: int = 100) -> dict:
        return {
            "data_quality": {
                "is_official": True,
                "point_in_time_safe": True,
                "has_assumed_release_times": False,
            },
            "freemium_window": {"cutoff_date": "2026-06-01"},
            "data": [
                {
                    "announcement_id": "prior",
                    "announcement_datetime": 1_780_000_000,
                    "val": 3.2,
                },
                {
                    "announcement_id": "target",
                    "announcement_datetime": 1_781_000_000,
                    "val": 9.9,
                    "source_url": "https://example.invalid/release",
                },
            ],
        }

    def calendar(self, event: str) -> dict:
        return {"data": [{"announcement_datetime": 1_781_000_000}]}


class FXMacroDataTests(unittest.TestCase):
    def test_target_actual_is_never_a_pre_release_feature(self) -> None:
        release = datetime.fromtimestamp(1_781_000_000, timezone.utc)
        cutoff = datetime.fromtimestamp(1_780_999_100, timezone.utc)
        context = StubClient().context("CPI", release, cutoff)
        self.assertEqual(context["event_time_verification"], "verified")
        self.assertTrue(context["target_actual_excluded"])
        self.assertEqual(context["known_release_count"], 1)
        self.assertEqual(context["latest_known_value"], 3.2)
        self.assertNotIn(9.9, context["recent_known_values"])
        self.assertEqual(context["decision_weight"], 0.0)

    def test_unauthenticated_forecasts_are_not_implied(self) -> None:
        release = datetime.fromtimestamp(1_781_000_000, timezone.utc)
        cutoff = datetime.fromtimestamp(1_780_999_100, timezone.utc)
        context = StubClient().context("CPI", release, cutoff)
        self.assertEqual(context["forecast_access"], "api_key_required")
        self.assertIsNone(context["stored_pre_release_forecast"])


if __name__ == "__main__":
    unittest.main()

