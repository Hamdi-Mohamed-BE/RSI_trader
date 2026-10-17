"""Synthetic paired DI-version statistics; no historical outcome reads."""
import copy
import unittest

import di_comparison_verify as d
from test_statistics_protocol import trial


class DIComparisonTests(unittest.TestCase):
    def test_equal_timing_has_zero_delta(self):
        result = d.paired_group([trial()], [trial()])
        self.assertEqual(result["median_off_minus_on_calendar_days_among_joint_completers"], 0)
        self.assertEqual(result["same_calendar_day_pairs"], 1)

    def test_missing_date_rejected(self):
        with self.assertRaises(AssertionError):
            d.paired_group([trial()], [trial(start="2025-10-07")])

    def test_changed_cost_rejected(self):
        a, b = trial(), trial()
        b["cost"] = "fixed_cost_stress"
        with self.assertRaises(AssertionError):
            d.paired_group([a], [b])

    def test_no_joint_completers_has_no_median(self):
        result = d.paired_group([trial(p1="failed")], [trial()])
        self.assertEqual(result["off_only_complete"], 1)
        self.assertIsNone(result["median_off_minus_on_calendar_days_among_joint_completers"])

    def test_failed_and_pending_remain_distinct(self):
        result = d.paired_group([trial(p1="failed")], [trial(p1="pending")])
        self.assertEqual(result["neither_complete"], 1)
        self.assertEqual(next(x["n"] for x in result["outcome_matrix"] if x["di_on"] == "failed_phase1" and x["di_off"] == "pending_phase1"), 1)

    def test_paired_median_not_difference_of_marginal_medians(self):
        starts = ["2025-10-06", "2025-10-07", "2025-10-08"]
        on = [trial(start=s, p1_day=4, p2_day=x) for s, x in zip(starts, [6, 16, 26])]
        off = [trial(start=s, p1_day=4, p2_day=x) for s, x in zip(starts, [16, 26, 6])]
        result = d.paired_group(on, off)
        self.assertEqual(result["median_off_minus_on_calendar_days_among_joint_completers"], 10)
        self.assertEqual(result["off_earlier_pairs"], 1)
        self.assertEqual(result["on_earlier_pairs"], 2)


if __name__ == "__main__":
    unittest.main()
