"""Independent synthetic audit of the actual-5% supplemental replay.

These fixtures do not consume risk outcomes, contact an account or launch MT5.
All expected monetary amounts are specified independently of the replay.
"""
from datetime import datetime, timezone
import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('audit_actual_five', ROOT/'run.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def broker():
    def spec(minimum, step, maximum, contract, price, margin):
        return dict(volume_min=minimum, volume_step=step, volume_max=maximum,
                    trade_contract_size=contract, bid=price, ask=price,
                    quote_spread=0., buy_margin_one_lot=margin,
                    sell_margin_one_lot=margin)
    return dict(symbols={
        'USTEC': spec(.05, .01, 500., 1., 20000., 50.),
        'XAUUSD': spec(.01, .01, 200., 100., 4000., 200.),
        'USDJPY': spec(.01, .01, 300., 100000., 150., 50.),
    })


def row(key='a', symbol='USTEC', t=None, duration=60, unit=100.,
        gross=100., commission=0., swap=0., entry_cost=0.):
    t = r.START+3600 if t is None else t
    price = {'USTEC': 20000., 'XAUUSD': 4000., 'USDJPY': 150.}[symbol]
    return dict(id=key, ea=key, symbol=symbol, position_id=key, op=t,
                cl=None if duration is None else t+duration,
                side='buy', open_price=price, close_price=price+1.,
                sl=price-1., tp=price+1., unit_risk=unit,
                source_mode='percent0p5', source_volume=.01,
                entry_unit_cost=entry_cost, unit_gross=gross,
                unit_commission=commission, unit_swap=swap,
                marks=[], end_censored=duration is None)


FIXED = dict(id='fixed50', mode='fixed', value=50., guard_policy='research_10daily_20total')
COMPOUND = dict(id='compound5', mode='percent', value=5., guard_policy='research_10daily_20total')


class TrueSizingFixtures(unittest.TestCase):
    def setUp(self):
        self.s = broker()['symbols']['USTEC']

    def test_predeclared_controls_and_two_research_scenarios(self):
        self.assertEqual([x['id'] for x in r.SCENARIOS], [
            'requested5_current_caps', 'fixed50_old_guards',
            'compound5_old_guards', 'fixed50', 'compound5'])

    def test_initial_fixed_and_percent_identical(self):
        self.assertEqual(r.true_lots(1000., 100., self.s, FIXED), (.5, 50.))
        self.assertEqual(r.true_lots(1000., 100., self.s, COMPOUND), (.5, 50.))

    def test_compound_grows_and_shrinks_without_initial_cash_cap(self):
        self.assertEqual(r.true_lots(1200., 100., self.s, COMPOUND), (.6, 60.))
        self.assertEqual(r.true_lots(800., 100., self.s, COMPOUND), (.4, 40.))
        self.assertEqual(r.true_lots(1200., 100., self.s, FIXED), (.5, 50.))
        self.assertEqual(r.true_lots(800., 100., self.s, FIXED), (.5, 50.))

    def test_floor_to_step_not_round_up(self):
        lots, budget = r.true_lots(1000., 103., self.s, COMPOUND)
        self.assertEqual(lots, .48)
        self.assertAlmostEqual(lots*103., 49.44)
        self.assertLessEqual(lots*103., budget)

    def test_broker_minimum_does_not_override_budget(self):
        self.assertEqual(r.true_lots(1000., 1001., self.s, COMPOUND), (0., 50.))

    def test_maximum_lot_is_still_honored(self):
        small = dict(self.s, volume_max=.1)
        self.assertEqual(r.true_lots(1000., 100., small, COMPOUND), (.1, 50.))

    def test_invalid_equity_or_unit_fails_closed(self):
        for eq, unit in ((0., 100.), (-10., 100.), (math.nan, 100.),
                         (1000., 0.), (1000., math.inf)):
            with self.subTest(eq=eq, unit=unit):
                self.assertEqual(r.true_lots(eq, unit, self.s, COMPOUND), (0., 0.))

    def test_current_literal_five_percent_input_is_still_capped(self):
        m = r.base.Replay(r.SCENARIOS[0], broker())
        q = row()
        m.opening(q, q['op'])
        self.assertEqual(m.decisions[-1]['budget'], 5.)
        self.assertEqual(m.active[q['id']]['risk'], 5.)

    def test_true_five_percent_with_old_other_guards_is_rejected(self):
        m = r.ResearchReplay(r.SCENARIOS[2], broker())
        q = row()
        m.opening(q, q['op'])
        self.assertEqual(m.decisions[-1]['budget'], 50.)
        self.assertEqual(m.decisions[-1]['reason'], 'aggregate_risk')
        self.assertEqual(m.active, {})

    def test_hypothetical_only_bypasses_source_volume(self):
        m = r.ResearchReplay(COMPOUND, broker())
        q = row()
        m.opening(q, q['op'])
        self.assertEqual(q['source_volume'], .01)
        self.assertEqual(m.active[q['id']]['lots'], .5)
        self.assertEqual(m.active[q['id']]['risk'], 50.)
        self.assertTrue(m.decisions[-1]['source_sizing_override_research_only'])


class ResearchGuardFixtures(unittest.TestCase):
    def setUp(self):
        self.m = r.ResearchReplay(COMPOUND, broker())
        self.t = r.START+3600

    def open(self, key='a', **kw):
        q = row(key=key, t=kw.pop('t', self.t), **kw)
        self.m.opening(q, q['op'])
        return q

    def test_daily_ten_percent_pauses_without_permanent_latch(self):
        q = self.open(duration=1000)
        self.m.mark(q, [self.t+1, -200., 0.], self.t+1)
        self.assertEqual(self.m.equity, 900.)
        self.assertTrue(self.m.day_stopped)
        self.assertFalse(self.m.breached)
        self.assertIn(r.base.day(self.t), self.m.paused_days)
        self.assertEqual(len(self.m.active), 1)

    def test_daily_latch_survives_recovery_until_new_prague_day(self):
        q = self.open(duration=100000)
        self.m.mark(q, [self.t+1, -200., 0.], self.t+1)
        self.m.mark(q, [self.t+2, 0., 0.], self.t+2)
        self.assertTrue(self.m.day_stopped)
        self.m.observe(self.t+86400)
        self.assertFalse(self.m.day_stopped)
        self.assertFalse(self.m.breached)

    def test_twenty_percent_initial_floor_latches_at_equality(self):
        q = self.open(duration=1000)
        self.m.mark(q, [self.t+1, -400., 0.], self.t+1)
        self.assertEqual(self.m.equity, 800.)
        self.assertTrue(self.m.breached)
        self.assertEqual(self.m.first_breach_epoch, self.t+1)
        self.assertEqual(len(self.m.active), 1, 'No forced liquidation')
        self.m.mark(q, [self.t+2, 100., 0.], self.t+2)
        self.m.observe(self.t+86400)
        self.assertTrue(self.m.breached)
        self.assertEqual(self.m.first_breach_epoch, self.t+1)

    def test_reserves_block_second_full_size_even_if_aggregate_allows(self):
        self.open(duration=1000)
        self.open('b', symbol='XAUUSD', t=self.t+10)
        self.assertEqual(self.m.decisions[-1]['reason'], 'daily_reserved_loss')

    def test_initial_exposure_is_not_released_by_profit(self):
        q = self.open(duration=1000)
        self.m.mark(q, [self.t+1, 100., 0.], self.t+1)
        self.open('b', t=self.t+10)
        self.assertEqual(self.m.decisions[-1]['reason'], 'same_symbol_risk')

    def test_protective_buffer_prevents_new_trade_before_total_floor(self):
        m = r.ResearchReplay(FIXED, broker())
        m.balance = 850.
        m.observe(self.t)
        self.assertEqual(m.reject(row(), 50., 1.), 'equity_buffer')
        self.assertFalse(m.breached)

    def test_seven_entries_and_three_net_losers_still_apply(self):
        self.m.observe(self.t)
        self.m.daily_entries = 7
        self.assertEqual(self.m.reject(row(), 1., 1.), 'daily_seven_entries')
        self.m.daily_entries = 0
        self.m.daily_losses = 3
        self.assertEqual(self.m.reject(row(), 1., 1.), 'daily_three_net_losers')

    def test_reconciliation_wait_still_applies(self):
        self.m.observe(self.t)
        self.m.last_entry = self.t
        self.assertEqual(self.m.reject(row(t=self.t+2), 1., 1.), 'three_second_wait')
        self.assertIsNone(self.m.reject(row(t=self.t+3), 1., 1.))

    def test_margin_proxy_is_enforced(self):
        self.m.broker['symbols']['USTEC']['buy_margin_one_lot'] = 2000.
        self.open()
        self.assertEqual(self.m.decisions[-1]['reason'], 'margin_proxy')

    def test_midnight_equity_peak_uses_carried_mark_not_cash(self):
        q = self.open(duration=100000)
        self.m.mark(q, [self.t+1, -40., 0.], self.t+1)
        self.m.daily_eq_dd = 0.
        self.m.observe(self.t+86400)
        self.assertEqual(self.m.day_peak, 980.)
        self.assertEqual(self.m.daily_eq_dd, 0.)
        self.assertEqual(self.m.anchor, 1000.)
        self.assertEqual(self.m.daily_anchor_loss, 20.)

    def test_zero_equity_is_logged_without_division_error(self):
        self.m.balance = 0.
        q = self.open()
        self.assertEqual(self.m.active, {})
        self.assertTrue(self.m.breached)
        self.assertIsNone(self.m.decisions[-1]['stop_risk_pct_equity'])


class CashAndCensorFixtures(unittest.TestCase):
    def test_native_fees_swap_and_entry_cash_book_once(self):
        m = r.ResearchReplay(COMPOUND, broker())
        q = row(gross=100., commission=-10., swap=-4., entry_cost=-3.)
        m.opening(q, q['op'])
        self.assertEqual(m.balance, 998.5)
        m.closing(q, q['cl'])
        self.assertEqual(m.trades[0]['entry_cash'], -1.5)
        self.assertEqual(m.trades[0]['exit_cash'], 44.5)
        self.assertEqual(m.trades[0]['net'], 43.)
        self.assertEqual(m.balance, 1043.)
        result = m.result()
        self.assertEqual(sum(f['cash'] for f in result['cash_flows']), 43.)
        self.assertEqual(result['daily'][-1]['ending_balance'], 1043.)

    def test_stress_adds_snapshot_spread_each_side_and_negative_swap_once(self):
        b = broker()
        b['symbols']['USTEC']['quote_spread'] = 2.
        m = r.ResearchReplay(COMPOUND, b, stress=True)
        q = row(gross=100., commission=-10., swap=-4., entry_cost=-3.)
        m.opening(q, q['op'])
        m.closing(q, q['cl'])
        self.assertEqual(m.trades[0]['entry_cash'], -2.5)
        self.assertEqual(m.trades[0]['exit_cash'], 41.5)
        self.assertEqual(m.trades[0]['net'], 39.)
        self.assertEqual(m.balance, 1039.)

    def test_censored_entry_fee_in_daily_monthly_and_cash_not_closed_pf(self):
        m = r.ResearchReplay(COMPOUND, broker())
        q = row(duration=None, entry_cost=-3.)
        m.opening(q, q['op'])
        m.mark(q, [q['op']+1, 20., None], q['op']+1)
        result = m.result()
        self.assertEqual(result['metrics']['trades'], 0)
        self.assertEqual(result['metrics']['net_profit'], 0.)
        self.assertEqual(result['metrics']['ending_balance'], 998.5)
        self.assertEqual(result['metrics']['cash_profit'], -1.5)
        self.assertEqual(result['metrics']['ending_sampled_equity'], 1008.5)
        self.assertEqual(result['metrics']['unrealized_sampled_profit'], 10.)
        self.assertEqual(len(result['open_positions']), 1)
        self.assertEqual(sum(d['net_profit'] for d in result['daily']), -1.5)
        self.assertEqual(sum(x['net_profit'] for x in result['months']), -1.5)
        self.assertEqual(result['daily'][-1]['ending_balance'], 998.5)
        self.assertEqual(result['cash_flows'], [dict(epoch=q['op'], cash=-1.5, id='a', kind='entry')])

    def test_unowned_close_does_not_create_cash_flow(self):
        m = r.ResearchReplay(COMPOUND, broker())
        q = row()
        m.closing(q, q['cl'])
        self.assertEqual(m.flows, [])
        self.assertEqual(m.balance, 1000.)

    def test_future_mark_is_rejected(self):
        m = r.ResearchReplay(COMPOUND, broker())
        q = row()
        m.opening(q, q['op'])
        with self.assertRaises(AssertionError):
            m.mark(q, [q['op']+10, 100., 0.], q['op']+1)

    def test_cross_month_entry_fee_stays_on_entry_day(self):
        stamp = lambda s: int(datetime.fromisoformat(s).timestamp())
        flows = [dict(epoch=stamp('2026-08-31T23:59:00+00:00'), cash=-1.5),
                 dict(epoch=stamp('2026-09-01T00:01:00+00:00'), cash=11.5)]
        days, months, _ = r.cash_calendar(flows, 1000.)
        self.assertEqual([m['net_profit'] for m in months], [-1.5, 11.5, 0.])
        self.assertEqual(days[-1]['ending_balance'], 1010.)

    def test_original_frozen_study_sources_untouched(self):
        frozen = r.base.read(r.PARENT/'FROZEN.json')
        for file, digest in frozen['files'].items():
            with self.subTest(file=file):
                self.assertEqual(r.base.sha(file), digest)


if __name__ == '__main__':
    unittest.main(verbosity=2)
