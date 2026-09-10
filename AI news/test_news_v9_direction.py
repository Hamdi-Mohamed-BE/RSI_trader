import unittest
from unittest.mock import patch

from news_v9_direction import SUPPORTED_EVENTS, artifact_prediction


class V9DirectionTests(unittest.TestCase):
    @staticmethod
    def _base(prediction: str, bias: str) -> dict:
        return {
            "prediction": prediction,
            "bias": bias,
            "confidence": 0.61,
            "probability_positive": 0.61 if bias == "POSITIVE" else 0.39,
            "probability_negative": 0.39 if bias == "POSITIVE" else 0.61,
            "strategy": "candidate",
            "gates": {},
            "failed_gates": [],
        }

    @patch("news_v9_direction.v5_artifact_prediction")
    def test_promotes_shadow_bias_at_full_coverage(self, mocked):
        mocked.return_value = self._base("NO CALL", "NEGATIVE")
        result = artifact_prediction({}, "NFP", 15, [], [])
        self.assertEqual(result["prediction"], "NEGATIVE")
        self.assertEqual(result["action_tier"], "LOW_CONFIDENCE")
        self.assertFalse(result["active_call_allowed"])

    @patch("news_v9_direction.v5_artifact_prediction")
    def test_preserves_validated_trade_tier(self, mocked):
        mocked.return_value = self._base("POSITIVE", "POSITIVE")
        result = artifact_prediction({}, "CPI", 15, [], [])
        self.assertEqual(result["prediction"], "POSITIVE")
        self.assertEqual(result["action_tier"], "TRADE")
        self.assertTrue(result["active_call_allowed"])

    def test_live_scope_is_only_the_three_validated_events(self):
        self.assertEqual(SUPPORTED_EVENTS, ("NFP", "CPI", "FOMC"))
        self.assertNotIn("PPI", SUPPORTED_EVENTS)
        self.assertNotIn("GDP", SUPPORTED_EVENTS)


if __name__ == "__main__":
    unittest.main()
