"""Offline golden-rule fixtures; does not import the native runner or any account API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_ftmo_reference", ROOT / "independent_verify.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def epoch(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


def mql_prague_offset(stamp):
    """Separate translation of the frozen MQL last-Sunday algorithm."""
    now = datetime.fromtimestamp(stamp, timezone.utc)
    boundaries = []
    for month in (3, 10):
        last = datetime(now.year, month, 31, 1, tzinfo=timezone.utc)
        sunday = (last.weekday() + 1) % 7
        boundaries.append((last - timedelta(days=sunday)).timestamp())
    return 7200 if boundaries[0] <= stamp < boundaries[1] else 3600


def deal(ticket, pid, when, entry, volume=1, gross=0, commission=0, swap=0, fee=0, comment=""):
    milliseconds = int(epoch(when) * 1000)
    return dict(deal=str(ticket), position_id=str(pid), epoch=str(milliseconds // 1000),
                time_msc=str(milliseconds), entry=str(entry), type="0" if entry == 0 else "1",
                volume=str(volume), gross=str(gross), commission=str(commission), swap=str(swap),
                fee=str(fee), comment=comment, symbol="XAUUSD", magic="3082026")


class PolicyFixtures(unittest.TestCase):
    def test_mql_dst_algorithm_matches_prague_zoneinfo_including_both_transitions(self):
        for year in range(2020, 2033):
            for month in (3, 10):
                for day in range(24, 32):
                    for hour in (0, 1, 2, 22, 23):
                        stamp = datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp()
                        official = reference.utc(stamp).astimezone(reference.PRAGUE).utcoffset().total_seconds()
                        self.assertEqual(mql_prague_offset(stamp), official, (year, month, day, hour))

    def test_prague_midnight_is_not_utc_midnight(self):
        self.assertEqual(reference.prague_day(epoch("2026-10-14T21:59:59")), "2026-10-14")
        self.assertEqual(reference.prague_day(epoch("2026-10-14T22:00:00")), "2026-10-15")
        self.assertEqual(reference.prague_day(epoch("2026-12-14T22:59:59")), "2026-12-14")
        self.assertEqual(reference.prague_day(epoch("2026-12-14T23:00:00")), "2026-12-15")

    def test_cash_anchor_includes_entry_fees_commission_swap_and_partial_exits(self):
        deals = [deal(1, 1, "2026-10-14T21:00:00", 0, commission=-2),
                 deal(2, 1, "2026-10-14T22:01:00", 1, volume=.5, gross=100, commission=-1, swap=-3, fee=-1)]
        self.assertEqual(reference.day_anchor(Decimal("10093"), deals, epoch("2026-10-14T22:02:00")), Decimal("9998"))

    def test_overnight_floating_loss_can_breach_at_new_midnight(self):
        days = {"2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13"}
        self.assertEqual(reference.policy_status(10300, 10000, 10900, days, positions=1), 0)
        self.assertEqual(reference.policy_status(10300, 10900, 10900, days, positions=1), -1)

    def test_failure_is_permanent_even_after_next_day_recovery(self):
        self.assertEqual(reference.policy_status(12000, 12000, 12000, range(4), prior_status=-1), -1)
        self.assertEqual(reference.policy_status(12000, 12000, 12000, range(4), prior_status=-2), -2)

    def test_floating_target_is_not_flat_closed_target(self):
        self.assertEqual(reference.policy_status(11200, 10000, 10100, range(4), positions=1), 0)
        self.assertEqual(reference.policy_status(11200, 10000, 11200, range(4), orders=1), 0)
        self.assertEqual(reference.policy_status(11000, 10000, 11000, range(4)), 1)

    def test_four_distinct_entry_days_not_deals_or_exit_days(self):
        self.assertEqual(reference.policy_status(11100, 10000, 11100, [1, 1, 2, 3]), 0)
        self.assertEqual(reference.policy_status(11100, 10000, 11100, [1, 2, 3, 4]), 1)

    def test_fresh_phase_two_has_10500_target_not_11550(self):
        self.assertEqual(reference.policy_status(10500, 10000, 10500, range(4), phase=2), 1)
        self.assertEqual(reference.policy_status(10500, 10000, 10500, range(4), phase=1), 0)

    def test_loss_boundary_equality_allowed_but_one_cent_below_fails(self):
        self.assertEqual(reference.policy_status(9500, 10000, 10000, [], positions=1), 0)
        self.assertEqual(reference.policy_status(9499.99, 10000, 10000, [], positions=1), -1)
        self.assertEqual(reference.policy_status(9000, 9500, 9500, [], positions=1), 0)
        self.assertEqual(reference.policy_status(8999.99, 9500, 9500, [], positions=1), -2)

    def test_costs_can_create_breach_without_a_price_loss(self):
        self.assertEqual(reference.policy_status(9500, 10000, 9500, []), 0)
        self.assertEqual(reference.policy_status(9498, 10000, 9498, []), -1)

    def test_end_of_test_liquidation_never_creates_new_terminal_status(self):
        self.assertEqual(reference.policy_status(12000, 10000, 12000, range(4), finalizing=True), 0)
        self.assertEqual(reference.policy_status(8990, 10000, 8990, range(4), finalizing=True), 0)
        self.assertEqual(reference.policy_status(12000, 10000, 12000, range(4), prior_status=-1, finalizing=True), -1)

    def test_gross_margin_does_not_net_opposite_positions_and_no_resize(self):
        allowed, proposed = reference.admission(9000, .04, 100, 4500, 4500, 4501, 10000)
        self.assertAlmostEqual(proposed, 1200.2666666666667)
        self.assertFalse(allowed)
        self.assertTrue(reference.admission(0, 1, 1, 150000, 149999, 150000, 10000)[0])

    def test_broker_round_up_can_exceed_nominal_one_percent(self):
        lots = reference.rounded_lots(.01005, .01, .01, 100)
        self.assertEqual(lots, .02)
        self.assertGreater(lots * 100 * 10, .01005 * 100 * 10)

    def test_position_identity_partials_costs_and_cash_conservation(self):
        deals = [deal(1, 1, "2026-10-14T10:00:00", 0, commission=-2),
                 deal(2, 2, "2026-10-14T10:00:00", 0, commission=-1),
                 deal(3, 1, "2026-10-14T11:00:00", 1, .5, gross=20, commission=-1),
                 deal(4, 2, "2026-10-14T11:00:00", 1, gross=-10, commission=-1, swap=-1),
                 deal(5, 1, "2026-10-15T11:00:00", 1, .5, gross=10, commission=-1, fee=-1)]
        positions = reference.positions_from_deals(deals)
        self.assertEqual(len(positions), 2)
        self.assertEqual(sum(p["exit_fills"] for p in positions), 3)
        self.assertEqual(sum(p["net"] for p in positions), sum(reference.deal_cash(d) for d in deals))
        self.assertEqual(reference.position_metrics(positions)["net_profit"], 12)

    def test_duplicate_tickets_and_incomplete_position_are_rejected(self):
        opened = deal(1, 1, "2026-10-14T10:00:00", 0)
        with self.assertRaises(AssertionError):
            reference.positions_from_deals([opened, opened])
        with self.assertRaises(AssertionError):
            reference.positions_from_deals([opened, deal(2, 1, "2026-10-14T11:00:00", 1, .5)])

    def test_policy_liquidator_magic_zero_is_attributed_to_opening_ea(self):
        opened = deal(1, 1, "2026-10-14T10:00:00", 0)
        closed = deal(2, 1, "2026-10-14T11:00:00", 1, gross=-20)
        closed["magic"] = "0"
        position = reference.positions_from_deals([opened, closed])[0]
        self.assertEqual(position["magic"], 3082026)
        self.assertEqual(position["differently_tagged_exit_fills"], 1)
        self.assertEqual(position["net"], -20)

    def test_no_loss_profit_factor_is_none_and_breakevens_break_streaks(self):
        positions = [dict(net=Decimal(v), exit_fills=1) for v in (10, 0, 10)]
        metrics = reference.position_metrics(positions)
        self.assertIsNone(metrics["profit_factor"])
        self.assertEqual(metrics["max_win_streak"], 1)
        self.assertEqual(metrics["wins"], 2)

    def test_zero_calendar_days_and_cash_drawdown_are_not_trade_only(self):
        empty = reference.cash_metrics([], "2026-08-16", "2026-10-16")
        self.assertEqual(empty["calendar_days"], 61)
        self.assertIsNone(empty["closed_balance_daily_sharpe"])
        deals = [deal(1, 1, "2026-10-14T10:00:00", 0, commission=-2),
                 deal(2, 1, "2026-10-14T11:00:00", 1, gross=12, commission=-1)]
        cash = reference.cash_metrics(deals, "2026-08-16", "2026-10-16")
        self.assertEqual(cash["net_profit"], 9)
        self.assertEqual(cash["max_closed_drawdown_cash"], 2)
        self.assertEqual(sum(day["net_profit"] for day in cash["daily"]), 9)

    def test_native_source_contract_and_current_input_freeze(self):
        self.assertEqual(reference.preflight()["verdict"], "PREFLIGHT_PASS")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyFixtures))
    receipt = dict(generated_at_utc=datetime.now(timezone.utc).isoformat(), tests_run=result.testsRun,
                   successful=result.wasSuccessful(), failures=[dict(test=str(t), error=e) for t, e in result.failures],
                   errors=[dict(test=str(t), error=e) for t, e in result.errors],
                   source_hashes={name: sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ("test_independent_policy.py", "independent_verify.py", "PortfolioHarness.mqh", "SharedPortfolio.mq5", "CONFIG.json", "FROZEN.json")},
                   scope="Independent offline golden-rule fixtures plus frozen source contract checks; no terminal/account/network calls")
    reference.save("INDEPENDENT-FIXTURE-TESTS.json", receipt)
    raise SystemExit(0 if result.wasSuccessful() else 1)
