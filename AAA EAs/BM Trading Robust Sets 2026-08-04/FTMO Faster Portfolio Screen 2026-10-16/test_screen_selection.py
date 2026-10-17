import copy
import unittest

from screen_selection import rank_screen, SCENARIOS


def rows(candidate="A", main=101, recent=54, speed=120, median=110):
    return [dict(portfolio=candidate, cost=cost, handover=wait,
                 all_starts=dict(starts=134, both_completed=main,
                                 overall_time_to50pct_prague_days=speed,
                                 total_median_prague_days_among_completed=median),
                 jan2026_plus=dict(starts=71, both_completed=recent))
            for cost, wait in sorted(SCENARIOS)]


class ScreenSelectionTests(unittest.TestCase):
    def test_exact_integer_dual_threshold_passes(self):
        self.assertEqual(rank_screen(rows(), {"A": ["ea"]})["selected_portfolio"], "A")

    def test_main_100_of134_fails(self):
        self.assertIsNone(rank_screen(rows(main=100), {"A": ["ea"]})["selected_portfolio"])

    def test_jan_53_of71_fails_even_if_main_passes(self):
        self.assertIsNone(rank_screen(rows(recent=53), {"A": ["ea"]})["selected_portfolio"])

    def test_one_failing_scenario_is_not_averaged_away(self):
        data = rows(main=134)
        data[0]["all_starts"]["both_completed"] = 100
        self.assertFalse(rank_screen(data, {"A": ["ea"]})["candidates"][0]["eligible"])

    def test_worst_t50_not_mean_or_best(self):
        a, b = rows("A", speed=100), rows("B", speed=115)
        a[0]["all_starts"]["overall_time_to50pct_prague_days"] = 130
        self.assertEqual(rank_screen(a+b, {"A": ["ea"], "B": ["ea"]})["selected_portfolio"], "B")

    def test_median_only_breaks_t50_tie(self):
        data = rows("A", speed=120, median=90)+rows("B", speed=119, median=118)
        self.assertEqual(rank_screen(data, {"A": ["ea"], "B": ["ea"]})["selected_portfolio"], "B")

    def test_worst_median_breaks_speed_tie(self):
        data = rows("A", median=113)+rows("B", median=111)
        self.assertEqual(rank_screen(data, {"A": ["ea"], "B": ["ea"]})["selected_portfolio"], "B")

    def test_fewer_eas_then_lexical_id(self):
        data = rows("C")+rows("B")+rows("A")
        result = rank_screen(data, {"C": ["ea", "other"], "B": ["ea"], "A": ["ea"]})
        self.assertEqual(result["selection_order"], ["A", "B", "C"])

    def test_null_t50_for_eligible_candidate_rejected(self):
        with self.assertRaises(AssertionError):
            rank_screen(rows(speed=None), {"A": ["ea"]})

    def test_missing_or_duplicate_scenario_rejected(self):
        data = rows()
        data[-1] = copy.deepcopy(data[0])
        with self.assertRaises(AssertionError):
            rank_screen(data, {"A": ["ea"]})

    def test_extra_unregistered_basket_rejected(self):
        with self.assertRaises(AssertionError):
            rank_screen(rows()+rows("B"), {"A": ["ea"]})

    def test_no_eligible_basket_has_no_winner(self):
        result = rank_screen(rows(main=99), {"A": ["ea"]})
        self.assertIsNone(result["selected_portfolio"])
        self.assertEqual(result["selection_order"], [])


if __name__ == "__main__":
    unittest.main()
