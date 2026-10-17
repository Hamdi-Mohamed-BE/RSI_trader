"""Generic screen-pair fixtures; no historical outcomes are loaded."""
import unittest

from statistical_verify import paired_to_baseline, summarize_trials
from test_statistics_protocol import trial


class ScreenPairingTests(unittest.TestCase):
    def test_extra_completion_separate_from_joint_timing(self):
        baseline = [trial(start="2025-10-06"), trial(start="2025-10-07", p2="pending")]
        candidate = [trial(start="2025-10-06"), trial(start="2025-10-07")]
        result = paired_to_baseline(baseline, candidate)
        self.assertEqual((result["joint_completers"], result["candidate_only_complete"],
                          result["baseline_only_complete"], result["neither_complete"]), (1, 1, 0, 0))
        self.assertEqual(result["median_candidate_minus_baseline_days"], 0)

    def test_cost_mismatch_rejected(self):
        a, b = trial(), trial()
        b["cost"] = "fixed_cost_stress"
        with self.assertRaises(AssertionError):
            paired_to_baseline([a], [b])

    def test_no_joint_success_has_undefined_timing(self):
        result = paired_to_baseline([trial()], [trial(p1="failed")])
        self.assertIsNone(result["median_candidate_minus_baseline_days"])
        self.assertEqual(result["baseline_only_complete"], 1)

    def test_paired_median_not_marginal_median_difference(self):
        dates = ["2025-10-06", "2025-10-07", "2025-10-08"]
        baseline = [trial(start=d, p2_day=n) for d, n in zip(dates, [5, 10, 15])]
        candidate = [trial(start=d, p2_day=n) for d, n in zip(dates, [15, 5, 10])]
        self.assertEqual(summarize_trials(baseline)["total_median_calendar_days_among_both_passes"],
                         summarize_trials(candidate)["total_median_calendar_days_among_both_passes"])
        self.assertEqual(paired_to_baseline(baseline, candidate)["median_candidate_minus_baseline_days"], -5)


if __name__ == "__main__":
    unittest.main()
