from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import app
import predict_news


class EaApiTests(unittest.TestCase):
    def test_next_event_is_utc_and_deduplicates_calendar_rows(self):
        release = datetime.now(timezone.utc) + timedelta(days=1)
        payload = {
            "status": "ok",
            "provider": "test",
            "events": [
                {
                    "event": "CPI",
                    "provider_name": "CPI y/y",
                    "release_time": release.isoformat(),
                    "forecast": "3.4%",
                    "previous": "3.4%",
                },
                {
                    "event": "CPI",
                    "provider_name": "Core CPI m/m",
                    "release_time": release.isoformat(),
                    "forecast": "0.3%",
                    "previous": "0.3%",
                },
            ],
        }
        with patch.object(app, "upcoming_us_events", return_value=payload):
            result = app.ea_next_event(2)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["event"], "CPI")
        self.assertEqual(result["provider_name"], "CPI y/y")
        self.assertTrue(result["release_utc"].endswith("+00:00"))

    def test_signal_endpoint_flattens_prediction_for_mql5(self):
        release = datetime.now(timezone.utc) + timedelta(minutes=15)
        prediction = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "event": "NFP",
            "release_time_utc": release.isoformat(),
            "symbol": "XAUUSD",
            "gold_impact": "NEGATIVE",
            "confidence_pct": 69.3,
            "confidence_tier": "medium",
            "action_tier": "TRADE",
            "model": {
                "active_call_allowed": True,
                "artifact_version": 9,
            },
            "expected_impulse_range_usd": {
                "minimum_absolute_move": 8.0,
                "median_absolute_move": 15.0,
                "maximum_absolute_move": 30.0,
            },
            "reused_locked_prediction": False,
        }
        with patch.object(app, "make_prediction", return_value=prediction):
            result = app.ea_signal("NFP", release.isoformat(), None, None)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["direction"], "NEGATIVE")
        self.assertEqual(result["confidence_pct"], 69.3)
        self.assertEqual(result["artifact_version"], 9)

    def test_locked_prediction_is_reused_without_recomputing(self):
        release = datetime.now(timezone.utc) + timedelta(minutes=15)
        filename = f"{release.strftime('%Y%m%dT%H%M%SZ')}-nfp.json"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            locked = {
                "event": "NFP",
                "release_time_utc": release.isoformat(),
                "gold_impact": "POSITIVE",
                "confidence_pct": 65.0,
            }
            (directory / filename).write_text(
                json.dumps(locked), encoding="utf-8"
            )
            with patch.object(predict_news, "PREDICTION_DIR", directory):
                result = predict_news.make_prediction("NFP", release)
        self.assertTrue(result["reused_locked_prediction"])
        self.assertEqual(result["gold_impact"], "POSITIVE")


if __name__ == "__main__":
    unittest.main()
