"""Independent deterministic guard, sizing, cash and clock fixtures.

No account access or native terminal launch. Expected cash is calculated in
the fixtures rather than by a second copy of the replay implementation.
"""
import importlib.util
import math
from pathlib import Path
import re
import unittest
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('prop_ready_1k_replay', ROOT/'replay.py')
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


def row(key='a', ea='example', symbol='USTEC', t=None, duration=60,
        unit=100., gross=100., commission=0., swap=0., entry_cost=0.,
        source_mode='fixed50'):
    t = r.START+3600 if t is None else t
    price = {'USTEC': 20000., 'XAUUSD': 4000., 'USDJPY': 150.}[symbol]
    distance = unit/({'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000./price}[symbol])
    return dict(id=key, ea=ea, symbol=symbol, position_id=key, op=t,
                cl=None if duration is None else t+duration,
                side='buy', open_price=price, close_price=price+distance,
                sl=price-distance, tp=price+distance, unit_risk=unit,
                source_mode=source_mode, source_volume=.5,
                entry_unit_cost=entry_cost, unit_gross=gross,
                unit_commission=commission, unit_swap=swap,
                marks=[], end_censored=duration is None)


FIXED5 = dict(id='fixed5', mode='fixed', value=5.)


class SizingFixtures(unittest.TestCase):
    def setUp(self):
        self.spec = broker()['symbols']['USTEC']

    def test_five_risk_scenarios_are_predeclared(self):
        self.assertEqual([(x['mode'], x['value']) for x in r.SCENARIOS],
                         [('fixed', 2.5), ('percent', .25), ('fixed', 5.),
                          ('percent', .5), ('percent', 1.)])

    def test_fixed50_source_and_true_percent_source_differ(self):
        a = r.risk_lots(1000., 100., self.spec, FIXED5, 'fixed50')
        b = r.risk_lots(1000., 100., self.spec, FIXED5, 'percent0p5')
        self.assertAlmostEqual(a[1], .5)
        self.assertAlmostEqual(b[1], .05)
        self.assertEqual(a[0], b[0])

    def test_exact_source_membership(self):
        self.assertEqual(r.PERCENT_SOURCES, {
            'us100-orb-new-york-m30', 'xau-orb-new-york-m30',
            'us100-selective-orb-v3'})

    def test_percent_compounds_but_static_reference_cap_does_not(self):
        quarter = dict(mode='percent', value=.25)
        with self.subTest('initial'):
            self.assertEqual(r.risk_lots(1000, 10, self.spec, quarter)[2], 2.5)
        with self.subTest('growth'):
            self.assertEqual(r.risk_lots(1200, 10, self.spec, quarter)[2], 3.)
        with self.subTest('ceiling'):
            self.assertEqual(r.risk_lots(3000, 10, self.spec, quarter)[2], 5.)
        half = dict(mode='percent', value=.5)
        self.assertEqual(r.risk_lots(1200, 10, self.spec, half)[2], 5.)
        self.assertEqual(r.risk_lots(900, 10, self.spec, half)[2], 4.5)

    def test_one_percent_still_has_five_dollar_cap(self):
        percent = dict(mode='percent', value=1.)
        self.assertEqual(r.risk_lots(1000, 10, self.spec, percent)[2], 5.)
        self.assertEqual(r.risk_lots(1500, 10, self.spec, percent)[2], 5.)

    def test_fixed_allocation_does_not_compound(self):
        fixed = dict(mode='fixed', value=2.5)
        for equity in (900, 1000, 1500):
            self.assertEqual(r.risk_lots(equity, 10, self.spec, fixed)[2], 2.5)

    def test_guard_downward_rounding_follows_source_upward_rounding(self):
        # $4.50 source risk -> 0.045 lots -> source 0.05. A $5 allocation
        # can admit it, whereas a 0.5% allocation at $900 cannot.
        fixed = r.risk_lots(900, 100, self.spec, FIXED5, 'percent0p5')
        percent = r.risk_lots(900, 100, self.spec,
                              dict(mode='percent', value=.5), 'percent0p5')
        self.assertAlmostEqual(fixed[0], .05)
        self.assertEqual(percent[0], 0.)
        self.assertAlmostEqual(fixed[1], .05)

    def test_minimum_lot_never_overrides_budget(self):
        for scenario in r.SCENARIOS:
            self.assertEqual(r.risk_lots(1000, 200, self.spec, scenario)[0], 0.)

    def test_current_nasdaq_stop_cannot_fit_five_dollars(self):
        distance = 29213.33*.006
        self.assertAlmostEqual(distance*.05, 8.763999)
        self.assertEqual(r.risk_lots(1000, distance, self.spec, FIXED5)[0], 0.)

    def test_gold_wide_stop_cannot_fit_five_dollars(self):
        spec = broker()['symbols']['XAUUSD']
        self.assertEqual(r.risk_lots(1000, 6.*100., spec, FIXED5)[0], 0.)
        self.assertAlmostEqual(r.risk_lots(1000, 5.*100., spec, FIXED5)[0], .01)

    def test_volume_max_and_reference_scale(self):
        smallmax = dict(self.spec, volume_max=.1)
        lots, source, budget = r.risk_lots(1000, 1, smallmax, FIXED5)
        self.assertEqual(lots, .1)
        self.assertEqual(source, .1)
        self.assertEqual(budget, 5.)
        self.assertEqual(r.risk_lots(2000, 10, self.spec,
            dict(mode='percent', value=1), reference=2000)[2], 10.)

    def test_invalid_capital_or_risk_is_rejected(self):
        for equity, unit in ((0., 1.), (-1., 1.), (1000., 0.),
                             (math.nan, 1.), (1000., math.inf)):
            self.assertEqual(r.risk_lots(equity, unit, self.spec, FIXED5),
                             (0., 0., 0.))


class GuardFixtures(unittest.TestCase):
    def setUp(self):
        self.broker = broker()
        self.model = r.Replay(FIXED5, self.broker)
        self.t = r.START+3600

    def open(self, key='a', symbol='USTEC', t=None, **kw):
        q = row(key=key, ea=key, symbol=symbol, t=self.t if t is None else t, **kw)
        self.model.opening(q, q['op'])
        return q

    def test_legal_entry_and_initial_stop_risk(self):
        q = self.open()
        self.assertEqual(self.model.active[q['id']]['lots'], .05)
        self.assertAlmostEqual(self.model.active[q['id']]['risk'], 5.)

    def test_same_ea_cannot_open_a_second_position(self):
        q = self.open()
        duplicate = dict(q, id='other', op=self.t+10)
        self.model.opening(duplicate, duplicate['op'])
        self.assertEqual(self.model.decisions[-1]['reason'], 'same_ea_exposure')

    def test_three_second_reconciliation_wait(self):
        self.open()
        self.open('b', t=self.t+2)
        self.assertEqual(self.model.decisions[-1]['reason'], 'three_second_wait')
        self.open('c', t=self.t+3)
        self.assertEqual(self.model.decisions[-1]['reason'], 'opened')

    def test_same_symbol_fifteen_dollar_limit(self):
        for n in range(4):
            self.open(str(n), t=self.t+10*n)
        self.assertEqual(len(self.model.active), 3)
        self.assertEqual(self.model.decisions[-1]['reason'], 'same_symbol_risk')

    def test_combined_twenty_two_fifty_limit(self):
        for n, symbol in enumerate(('USTEC', 'XAUUSD', 'USDJPY', 'USTEC', 'XAUUSD')):
            self.open(str(n), symbol=symbol, t=self.t+10*n)
        self.assertEqual(len(self.model.active), 4)
        self.assertEqual(self.model.decisions[-1]['reason'], 'aggregate_risk')

    def test_profitable_marks_do_not_release_initial_risk(self):
        for n in range(3):
            q = self.open(str(n), t=self.t+10*n, duration=1000)
            self.model.mark(q, [q['op']+1, 1000., 0.], q['op']+1)
        self.open('b', t=self.t+60)
        self.assertEqual(self.model.decisions[-1]['reason'], 'same_symbol_risk')

    def test_open_swap_reserve_can_block_admission(self):
        q = self.open(duration=1000)
        # .05 lot * -400/lot swap = -$20; unchanged mark is intentionally
        # generous so the fixture isolates the EXTRA reserve in admission.
        self.model.mark(q, [q['op']+1, 0., -400.], q['op']+1)
        self.open('b', t=self.t+10)
        self.assertEqual(self.model.decisions[-1]['reason'], 'daily_reserved_loss')

    def test_eight_percent_entry_buffer_is_not_permanent_breach(self):
        self.model.balance = 925.
        self.model.observe(self.t)
        self.model.anchor = 925.
        self.assertEqual(self.model.reject(row(), 5., 1.), 'equity_buffer')
        self.assertFalse(self.model.breached)

    def test_daily_loss_latch_blocks_entries_not_management(self):
        q = self.open(gross=200., duration=1000)
        self.model.mark(q, [self.t+1, -600., 0.], self.t+1)
        self.assertTrue(self.model.day_stopped)
        self.assertFalse(self.model.breached)
        self.open('b', t=self.t+5)
        self.assertEqual(self.model.decisions[-1]['reason'], 'daily_loss_latch')
        self.model.closing(q, q['cl'])
        self.assertEqual(len(self.model.trades), 1)
        self.assertEqual(self.model.balance, 1010.)
        self.assertTrue(self.model.day_stopped)

    def test_hard_daily_latch_survives_recovery_and_date_reset(self):
        q = self.open(gross=100., duration=1000)
        self.model.mark(q, [self.t+1, -1000., 0.], self.t+1)
        self.assertTrue(self.model.breached)
        self.model.closing(q, q['cl'])
        self.model.observe(self.t+86400)
        self.assertTrue(self.model.breached)
        self.assertEqual(self.model.reject(row(t=self.t+86400), 5., 1.),
                         'permanent_loss_latch')

    def test_static_floor_latches_at_equality(self):
        self.model.balance = 900.
        self.model.observe(self.t)
        self.assertTrue(self.model.breached)

    def test_three_net_losers_not_three_consecutive_losers(self):
        # L,W,L,W,L -> reject sixth opportunity; wins do not reset count.
        for n, pnl in enumerate((-1., 1., -1., 1., -1.)):
            q = self.open(str(n), t=self.t+100*n, gross=pnl/.05)
            self.model.closing(q, q['cl'])
        self.assertEqual(self.model.daily_losses, 3)
        self.open('blocked', t=self.t+600)
        self.assertEqual(self.model.decisions[-1]['reason'], 'daily_three_net_losers')

    def test_seven_entry_limit(self):
        for n in range(7):
            q = self.open(str(n), t=self.t+100*n, gross=0.)
            self.model.closing(q, q['cl'])
        self.open('blocked', t=self.t+800)
        self.assertEqual(self.model.decisions[-1]['reason'], 'daily_seven_entries')

    def test_daily_reset_clears_daily_not_permanent_state(self):
        self.model.observe(self.t)
        self.model.daily_entries = 7
        self.model.daily_losses = 3
        self.model.day_stopped = True
        self.model.observe(self.t+86400)
        self.assertEqual(self.model.daily_entries, 0)
        self.assertEqual(self.model.daily_losses, 0)
        self.assertFalse(self.model.day_stopped)

    def test_continuous_mode_does_not_stop_at_challenge_target(self):
        self.model.balance = 1200.
        self.model.observe(self.t)
        self.open()
        self.assertEqual(self.model.decisions[-1]['reason'], 'opened')

    def test_broker_margin_blocks_excessive_gross_exposure(self):
        self.broker['symbols']['USTEC']['buy_margin_one_lot'] = 20000.
        self.open()
        self.assertEqual(self.model.decisions[-1]['reason'], 'margin_proxy')

    def test_reference_limits_scale_without_rebasing_on_profit(self):
        model = r.Replay(dict(mode='fixed', value=10), self.broker, reference=2000)
        q = row()
        model.opening(q, q['op'])
        self.assertEqual(model.active[q['id']]['risk'], 10.)
        model.balance = 2500.
        self.assertEqual(model.reference, 2000.)


class AccountingAndClockFixtures(unittest.TestCase):
    def test_entry_and_exit_costs_reconcile_exactly_once(self):
        model = r.Replay(FIXED5, broker())
        q = row(gross=100., commission=-10., swap=-4., entry_cost=-3.)
        model.opening(q, q['op'])
        self.assertEqual(model.balance, 999.85)
        model.closing(q, q['cl'])
        self.assertEqual(model.trades[0]['entry_cash'], -.15)
        self.assertEqual(model.trades[0]['exit_cash'], 4.45)
        self.assertEqual(model.trades[0]['net'], 4.3)
        self.assertEqual(model.balance, 1004.3)

    def test_stress_extra_spread_each_side_and_negative_swap_double(self):
        b = broker()
        b['symbols']['USTEC']['quote_spread'] = 2.
        model = r.Replay(FIXED5, b, stress=True)
        q = row(gross=100., commission=-10., swap=-4., entry_cost=-3.)
        model.opening(q, q['op'])
        model.closing(q, q['cl'])
        self.assertEqual(model.trades[0]['entry_cash'], -.25)
        self.assertEqual(model.trades[0]['exit_cash'], 4.15)
        self.assertEqual(model.trades[0]['net'], 3.9)

    def test_positive_swap_not_doubled_under_stress(self):
        model = r.Replay(FIXED5, broker(), stress=True)
        q = row(gross=0., swap=20.)
        model.opening(q, q['op'])
        model.closing(q, q['cl'])
        self.assertEqual(model.trades[0]['net'], 1.)

    def test_unowned_exit_or_mark_does_not_create_cash(self):
        model = r.Replay(FIXED5, broker())
        q = row()
        model.closing(q, q['cl'])
        model.mark(q, [q['op']+1, 1000., 0.], q['op']+1)
        self.assertEqual(model.balance, 1000.)
        self.assertEqual(model.active, {})

    def test_no_future_mark_permitted(self):
        model = r.Replay(FIXED5, broker())
        q = row()
        model.opening(q, q['op'])
        with self.assertRaises(AssertionError):
            model.mark(q, [q['op']+10, 1., 0.], q['op']+1)

    def test_missing_swap_is_explicitly_counted(self):
        model = r.Replay(FIXED5, broker())
        q = row()
        model.opening(q, q['op'])
        model.mark(q, [q['op']+1, 0., None], q['op']+1)
        self.assertEqual(model.mark_quality['missing_open_swap_marks'], 1)

    def test_margin_conversion_uses_current_per_lot_receipt(self):
        b = broker()
        q = row()
        q['open_price'] = 30000.
        self.assertEqual(r.margin_unit(q, b['symbols']['USTEC']), 75.)
        fx = row(symbol='USDJPY')
        fx['open_price'] = 100.
        self.assertEqual(r.margin_unit(fx, b['symbols']['USDJPY']), 50.)

    def test_prague_clock_including_dst(self):
        def epoch(value):
            return datetime.fromisoformat(value).timestamp()
        self.assertEqual(r.day(epoch('2026-07-01T22:00:00+00:00')), '2026-07-02')
        self.assertEqual(r.day(epoch('2026-01-01T22:30:00+00:00')), '2026-01-01')
        self.assertEqual(r.day(epoch('2026-01-01T23:00:00+00:00')), '2026-01-02')
        self.assertEqual(r.day(epoch('2026-10-25T22:30:00+00:00')), '2026-10-25')
        self.assertEqual(r.day(epoch('2026-10-25T23:00:00+00:00')), '2026-10-26')

    def test_same_timestamp_ordering_releases_prior_position_first(self):
        a = row('a', 'one', t=r.START+100, duration=100)
        b = row('b', 'two', t=r.START+200, duration=0)
        a['marks'] = [[r.START+150, 1., 0.]]
        events = r.events_for(dict(priority=['one', 'two']), dict(candidates=[a, b]))
        tied = [(kind, key) for t, kind, _, key, _, _ in events if t == r.START+200]
        self.assertEqual(tied, [(1, 'a'), (3, 'b'), (4, 'b')])

    def test_end_censored_position_not_forcibly_liquidated(self):
        model = r.Replay(FIXED5, broker())
        q = row(duration=None)
        model.opening(q, q['op'])
        result = model.result()
        self.assertEqual(result['metrics']['open_positions'], 1)
        self.assertEqual(result['metrics']['trades'], 0)

    def test_streaks_use_net_whole_position_cash(self):
        data = [dict(net=x) for x in (1., 2., -1., 0., -1., -2., 4.)]
        m = r.cash_metrics(data)
        self.assertEqual(m['max_win_streak'], 2)
        self.assertEqual(m['max_loss_streak'], 2)
        self.assertEqual(m['win_rate_pct'], 3/7*100)
        self.assertEqual(m['profit_factor'], 7/4)


class ProductionSourceMappingFixtures(unittest.TestCase):
    def test_production_include_chain_reproduces_sizing_mode_map(self):
        manifest = r.read(r.PACKAGE/'PACKAGE.json')
        folder = r.PACKAGE/'package'

        def includes(file, seen):
            if file in seen:
                return {}
            seen.add(file)
            text = file.read_text(encoding='utf-8-sig')
            result = {file.name: text}
            for name in re.findall(r'^#include\s+"([^\"]+)"', text, re.M):
                result.update(includes(folder/name, seen))
            return result

        found_percent = set()
        found_fixed = set()
        for ea in manifest['entries']:
            with self.subTest(ea=ea['slug']):
                chain = includes(folder/ea['expert'].replace('.ex5', '.mq5'), set())
                helper_names = [x for x in chain if x in (
                    'src_75fa4ea168c0.mqh', 'src_orb05_75fa4ea168c0.mqh')]
                self.assertEqual(len(helper_names), 1)
                helper = helper_names[0]
                self.assertEqual(float(ea['inputs']['InpRiskPercent']), .5)
                self.assertEqual(ea['inputs']['InpAdaptivePortfolioControls'], 'false')
                if helper == 'src_75fa4ea168c0.mqh':
                    self.assertIn('return equity>0 ? 10000.0/equity : 0.0;', chain[helper])
                    found_fixed.add(ea['slug'])
                else:
                    self.assertIn('if(!enabled) return 1.0;', chain[helper])
                    found_percent.add(ea['slug'])
                self.assertTrue(any('OrderCalcProfit(' in s for s in chain.values()))
        self.assertEqual(found_percent, set(r.PERCENT_SOURCES))
        self.assertEqual(len(found_fixed), 6)

    def test_guard_literal_caps_match_replay_protocol(self):
        guard = (r.PACKAGE/'CalyxFTMOGuard.mqh').read_text(encoding='utf-8-sig')
        for literal in (
            'FTMOReferenceBalance*0.005', 'FTMOReferenceBalance*0.0225',
            'FTMOReferenceBalance*0.015', 'FTMOReferenceBalance*0.03',
            'FTMOReferenceBalance*0.92', 'FTMOReferenceBalance*0.90',
            'FTMOReferenceBalance*0.05', 'ftmo_entries>=7 || losses>=3',
            'MathFloor(desired/step+1e-9)', 'TimeLocal()+3',
            'loss*1.25', 'FTMOReferenceBalance*0.0005',
        ):
            with self.subTest(literal=literal):
                self.assertIn(literal, guard)
        self.assertNotIn('close_position', guard)
        self.assertNotIn('PositionClose(', guard)


if __name__ == '__main__':
    unittest.main(verbosity=2)
