"""Synthetic statistical fixtures only: never consumes portfolio outcomes."""
import copy
from datetime import date, timedelta
import unittest

import statistical_verify as s


def trial(p1="passed", p2="passed", p1_day=5, p2_day=10, start="2025-10-06"):
    d = date.fromisoformat(start)
    begin = s.midnight_epoch(d)
    finish = s.midnight_epoch(d + timedelta(days=180))
    p1event = s.midnight_epoch(d + timedelta(days=p1_day - 1)) + 3600
    activation = s.midnight_epoch(d + timedelta(days=p1_day)) if p1 == "passed" else None
    p2event = activation + (p2_day - 1) * 86400 + 3600 if activation is not None else None
    p1phase = dict(status=p1, pass_epoch=p1event if p1 == "passed" else None,
                   fail_epoch=p1event if p1 == "failed" else None,
                   first_trade_epoch=begin + 3600, entry_days=4)
    p2phase = dict(activation_epoch=activation, status=p2 if activation else "not_started",
                   pass_epoch=p2event if p2 == "passed" and activation else None,
                   fail_epoch=p2event if p2 == "failed" and activation else None,
                   first_trade_epoch=activation + 1800 if activation else None, entry_days=4)
    outcome = "failed_phase1" if p1 == "failed" else "pending_phase1" if p1 == "pending" else "failed_phase2" if p2 == "failed" else "pending_phase2" if p2 == "pending" else "horizon_completed_both"
    return dict(portfolio="CORE3", start_date=start, start_epoch=begin,
                horizon_date=(d + timedelta(days=180)).isoformat(), horizon_epoch=finish,
                cost="recorded_exness", handover="next_prague_midnight",
                phase1=p1phase, phase2=p2phase, outcome=outcome,
                both_pass_epoch=p2event if outcome == "horizon_completed_both" else None,
                access_5bd_illustration_epoch=None)


class StatisticsProtocolTests(unittest.TestCase):
    def test_complete_date_denominators(self):
        all_days, eligible = s.eligible_starts("2025-10-06", "2026-10-06")
        self.assertEqual((len(all_days), len(eligible)), (261, 134))
        self.assertEqual(eligible[-1], "2026-04-09")
        self.assertEqual(sum(d >= "2026-01-01" for d in eligible), 71)

    def test_holiday_weekdays_not_removed(self):
        self.assertIn("2025-12-25", s.eligible_starts("2025-10-06", "2026-10-06")[1])

    def test_civil_day_dst_not_fixed_24h(self):
        begin = date(2026, 1, 1)
        self.assertEqual((s.midnight_epoch(begin + timedelta(days=180)) - s.midnight_epoch(begin)) / 3600, 180 * 24 - 1)

    def test_weekday_wait_is_not_calendar_wait(self):
        self.assertEqual(s.weekday_advance("2026-01-02", 2).isoformat(), "2026-01-06")

    def test_zero_passes_null_medians_and_conditional_rate(self):
        result = s.summarize_trials([trial(p1="failed")])
        self.assertEqual(result["phase2_started"], 0)
        self.assertIsNone(result["phase2_pass_pct_started"])
        self.assertIsNone(result["total_median_calendar_days_among_both_passes"])
        self.assertIsNone(result["first_calendar_day_with_50pct_of_all_starts_completed"])

    def test_pending_is_not_failed(self):
        result = s.summarize_trials([trial(p1="pending")])
        self.assertEqual((result["pending"], result["failed"]), (1, 0))

    def test_active_phase2_without_fills_stays_in_denominator(self):
        t = trial(p2="pending")
        t["phase2"].update(first_trade_epoch=None, entry_days=0)
        result = s.summarize_trials([t])
        self.assertEqual(result["phase2_started"], 1)
        self.assertEqual(result["phase2_pass_pct_started"], 0)

    def test_handover_at_horizon_not_started(self):
        t = trial(p1_day=180, p2="pending")
        t["phase2"].update(first_trade_epoch=None, entry_days=0)
        t["outcome"] = "phase2_not_started_wait"
        result = s.summarize_trials([t])
        self.assertEqual(result["phase1_passed"], 1)
        self.assertEqual(result["phase2_started"], 0)
        self.assertEqual(result["pending"], 1)

    def test_eligible_phase2_activation_cannot_be_omitted(self):
        t = trial(p2="pending")
        t["phase2"].update(activation_epoch=None, first_trade_epoch=None, entry_days=0)
        t["outcome"] = "phase2_not_started_wait"
        with self.assertRaises(AssertionError):
            s.normalized_trial(t)

    def test_pass_at_exclusive_horizon_rejected(self):
        t = trial()
        t["phase2"]["pass_epoch"] = t["both_pass_epoch"] = t["horizon_epoch"]
        with self.assertRaises(AssertionError):
            s.normalized_trial(t)

    def test_phase2_conditional_denominator_and_all_start_rate(self):
        rows = [trial(), trial(start="2025-10-07", p2="failed"), trial(start="2025-10-08", p1="failed"), trial(start="2025-10-09", p1="pending")]
        result = s.summarize_trials(rows)
        self.assertEqual(result["phase2_pass_pct_started"], 50)
        self.assertEqual(result["phase2_pass_pct_all_starts"], 25)
        self.assertIsNone(result["first_calendar_day_with_50pct_of_all_starts_completed"])

    def test_total_median_is_not_sum_of_phase_medians(self):
        result = s.summarize_trials([trial(p1_day=4, p2_day=10), trial(start="2025-10-07", p1_day=6, p2_day=6), trial(start="2025-10-08", p1_day=10, p2_day=4)])
        self.assertEqual(result["total_median_calendar_days_among_both_passes"], 14)
        self.assertEqual(result["phase1_median_calendar_days_among_passes"] + result["phase2_median_calendar_days_among_passes"], 12)

    def test_failure_and_pass_mutually_exclusive(self):
        t = trial()
        t["phase1"]["fail_epoch"] = t["phase1"]["pass_epoch"]
        with self.assertRaises(AssertionError):
            s.normalized_trial(t)

    def test_duplicate_start_in_same_scenario_rejected(self):
        with self.assertRaises(AssertionError):
            s.summarize_trials([trial(), trial()])

    def test_paired_date_sets_must_match(self):
        with self.assertRaises(AssertionError):
            s.paired_statistics([trial()], [trial(start="2025-10-07")])

    def test_paired_timing_uses_only_joint_completers(self):
        a = [trial(start="2025-10-06"), trial(start="2025-10-07")]
        b = [trial(start="2025-10-06", p2_day=12), trial(start="2025-10-07", p1="failed")]
        result = s.paired_statistics(a, b)
        self.assertEqual(result["both_portfolios_complete"], 1)
        self.assertEqual(result["median_core4_minus_core3_calendar_days_among_paired_completers"], 2)

    def test_minimum_four_entry_days_per_passed_phase(self):
        t = trial()
        t["phase2"]["entry_days"] = 3
        with self.assertRaises(AssertionError):
            s.normalized_trial(t)


if __name__ == "__main__":
    unittest.main()
