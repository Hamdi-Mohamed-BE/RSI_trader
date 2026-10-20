"""Synthetic policy-isolation tests; no outcomes, account access or MT5 calls."""
from datetime import datetime, timezone
import importlib.util
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('audit_top5_prop_comparison',ROOT/'compare.py')
r=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def broker():
    def spec(minimum,step,maximum,contract,price,margin):
        return dict(volume_min=minimum,volume_step=step,volume_max=maximum,
                    trade_contract_size=contract,bid=price,ask=price,
                    quote_spread=0.,buy_margin_one_lot=margin,sell_margin_one_lot=margin)
    return dict(symbols={
        'USTEC':spec(.05,.01,500.,1.,20000.,50.),
        'XAUUSD':spec(.01,.01,200.,100.,4000.,200.),
        'USDJPY':spec(.01,.01,300.,100000.,150.,50.),
    })


def row(key='a',symbol='USTEC',t=None,duration=60,unit=100.,gross=100.,
        commission=0.,swap=0.,entry_cost=0.,ea=None):
    t=r.base.START+3600 if t is None else t
    price={'USTEC':20000.,'XAUUSD':4000.,'USDJPY':150.}[symbol]
    return dict(id=key,ea=ea or key,symbol=symbol,position_id=key,op=t,
                cl=None if duration is None else t+duration,
                side='buy',open_price=price,close_price=price+1.,sl=price-1.,tp=price+1.,
                unit_risk=unit,source_mode='fixed50',source_volume=.01,
                entry_unit_cost=entry_cost,unit_gross=gross,unit_commission=commission,
                unit_swap=swap,marks=[],end_censored=duration is None)


def scenario(portfolio='top5',view='as_packaged',name='compound5'):
    return next(dict(s) for s in r.SCENARIOS if (s['portfolio'],s['view'],s['id'])==(portfolio,view,name))


def client(name='compound5',b=None):
    return r.ClientReplay(scenario(name=name),broker() if b is None else b)


class ProtocolAndSizing(unittest.TestCase):
    def test_eight_prespecified_scenarios_times_two_costs(self):
        keys={(s['portfolio'],s['view'],s['id']) for s in r.SCENARIOS}
        self.assertEqual(len(r.SCENARIOS),8)
        self.assertEqual(len(keys),8)
        self.assertEqual(len({(*k,cost) for k in keys for cost in (False,True)}),16)

    def test_common_view_is_genuinely_shared_equity_sizing_and_guards(self):
        for portfolio in ('top5','prop_ready'):
            s=scenario(portfolio,'common_research')
            self.assertEqual((s['mode'],s['value'],s['guard_policy']),('percent',5.,'research_10daily_20total'))
            self.assertEqual(scenario(portfolio,'common_research','fixed50')['mode'],'fixed')

    def test_exact_calendar_window_and_prague_day(self):
        iso=lambda t:datetime.fromtimestamp(t,timezone.utc).isoformat()
        self.assertEqual(iso(r.base.START),'2026-08-17T00:00:00+00:00')
        self.assertEqual(iso(r.base.END),'2026-10-17T00:00:00+00:00')
        self.assertEqual((r.base.END-r.base.START)//86400,61)
        stamp=int(datetime.fromisoformat('2026-08-17T22:00:00+00:00').timestamp())
        self.assertEqual(r.base.day(stamp),'2026-08-18')

    def test_both_asks_start_at_fifty_dollars(self):
        spec=broker()['symbols']['USTEC']
        for name in ('fixed50','compound5'):
            self.assertEqual(r.client_lots(1000.,100.,spec,scenario(name=name)),(.5,50.,False))

    def test_floors_above_minimum_and_clamps_below_it(self):
        spec=broker()['symbols']['USTEC']
        self.assertEqual(r.client_lots(1000.,103.,spec,scenario()),(.48,50.,False))
        self.assertEqual(r.client_lots(1000.,1001.,spec,scenario()),(.05,50.,True))
        self.assertAlmostEqual(.05*1001.,50.05)

    def test_shared_research_skips_the_same_oversized_minimum(self):
        spec=broker()['symbols']['USTEC']
        s=scenario(view='common_research')
        self.assertEqual(r.engine.true_lots(1000.,1001.,spec,s),(0.,50.))

    def test_current_balance_percentage_grows_and_shrinks(self):
        spec=broker()['symbols']['USTEC']
        self.assertEqual(r.client_lots(1200.,100.,spec,scenario()),(.6,60.,False))
        self.assertEqual(r.client_lots(800.,100.,spec,scenario()),(.4,40.,False))
        self.assertEqual(r.client_lots(800.,100.,spec,scenario(name='fixed50')),(.5,50.,False))

    def test_broker_maximum_is_still_a_limit(self):
        spec=dict(broker()['symbols']['USTEC'],volume_max=.1)
        self.assertEqual(r.client_lots(1000.,100.,spec,scenario()),(.1,50.,False))

    def test_invalid_cash_or_risk_geometry_fails_closed(self):
        for cash,unit in ((0.,100.),(-1.,100.),(math.nan,100.),(1000.,0.),(1000.,math.inf)):
            self.assertEqual(r.client_lots(cash,unit,broker()['symbols']['USTEC'],scenario()),(0.,0.,False))

    def test_client_budget_uses_balance_not_open_floating_equity(self):
        m=client()
        q=row(duration=1000)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,400.,0.],q['op']+1)
        self.assertEqual((m.balance,m.equity,m.budget()),(1000.,1200.,50.))
        other=row('b',symbol='XAUUSD',t=q['op']+2)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['budget'],50.)
        self.assertEqual(m.decisions[-1]['volume'],.5)

    def test_common_research_budget_uses_past_equity_instead(self):
        m=r.engine.ResearchReplay(scenario(view='common_research'),broker())
        q=row(duration=1000)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,400.,0.],q['op']+1)
        self.assertEqual(m.budget(),60.)


class DistinctAdmissionPolicies(unittest.TestCase):
    def test_source_volume_is_not_a_new_client_ceiling(self):
        m=client()
        q=row()
        m.opening(q,q['op'])
        self.assertEqual(q['source_volume'],.01)
        self.assertEqual(m.active[q['id']]['lots'],.5)
        self.assertIsNone(m.decisions[-1]['source_volume_ceiling'])

    def test_minimum_lot_override_is_recorded_and_can_exceed_risk(self):
        m=client()
        q=row(unit=2000.)
        m.opening(q,q['op'])
        self.assertEqual(m.decisions[-1]['reason'],'opened')
        self.assertTrue(m.decisions[-1]['minimum_lot_override'])
        self.assertEqual(m.decisions[-1]['stop_risk'],100.)
        self.assertEqual(m.result()['metrics']['min_lot_override_entries'],1)

    def test_no_borrowed_seven_entry_or_three_loser_caps(self):
        m=client()
        t=r.base.START+3600
        m.observe(t)
        m.daily_entries,m.daily_losses=7,3
        q=row(t=t)
        m.opening(q,t)
        self.assertEqual(m.decisions[-1]['reason'],'opened')
        self.assertEqual(m.daily_entries,8)

    def test_no_borrowed_same_symbol_cap_or_three_second_wait(self):
        m=client()
        q=row(duration=1000)
        m.opening(q,q['op'])
        other=row('b',t=q['op'],duration=1000)
        m.opening(other,other['op'])
        self.assertEqual([d['reason'] for d in m.decisions],['opened','opened'])
        self.assertEqual(sum(p['risk'] for p in m.active.values()),100.)

    def test_same_ea_cannot_have_two_simultaneous_owned_positions(self):
        m=client()
        q=row(duration=1000,ea='nasdaq')
        m.opening(q,q['op'])
        other=row('b',ea='nasdaq',t=q['op']+10)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['reason'],'same_ea_exposure')

    def test_client_has_no_invented_daily_or_total_loss_latch(self):
        m=client()
        q=row(duration=1000)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,-500.,0.],q['op']+1)
        self.assertEqual(m.equity,750.)
        self.assertFalse(m.day_stopped)
        self.assertFalse(m.breached)
        other=row('b',symbol='XAUUSD',t=q['op']+10)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['reason'],'opened')
        self.assertEqual(m.budget(),50.)

    def test_client_free_margin_is_not_research_eighty_percent_cap(self):
        b=broker()
        b['symbols']['USTEC']['buy_margin_one_lot']=1800.
        m=client(b=b)
        q=row()
        m.opening(q,q['op'])
        self.assertEqual(m.active[q['id']]['margin'],900.)
        self.assertEqual(m.decisions[-1]['reason'],'opened')
        other=row('b',t=q['op']+10)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['reason'],'margin_proxy')

    def test_capital_exhaustion_is_flagged_without_forced_liquidation(self):
        m=client()
        q=row(duration=1000)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,-2200.,0.],q['op']+1)
        self.assertEqual(m.equity,-100.)
        self.assertEqual(m.capital_exhaustion_epoch,q['op']+1)
        self.assertIn(q['id'],m.active)
        self.assertEqual(m.minimum_sampled_margin_level,-400.)
        m.mark(q,[q['op']+2,0.,0.],q['op']+2)
        other=row('b',t=q['op']+10)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['reason'],'capital_exhaustion_unresolved')
        result=m.result()
        self.assertTrue(result['metrics']['historical_path_executable_uncertainty'])
        self.assertFalse(result['metrics']['broker_stopout_reconstructed'])

    def test_prop_ready_as_packaged_preserves_five_dollar_cap(self):
        for name in ('fixed50','compound5'):
            s=scenario('prop_ready','as_packaged',name)
            self.assertEqual(s['guard_policy'],'current')
            m=r.base.Replay(s,broker())
            q=row()
            m.opening(q,q['op'])
            self.assertEqual(m.decisions[-1]['budget'],5.)
            self.assertEqual(m.active[q['id']]['risk'],5.)

    def test_prop_ready_minimum_lot_is_skipped_not_overridden(self):
        m=r.base.Replay(scenario('prop_ready'),broker())
        q=row(unit=101.)
        m.opening(q,q['op'])
        self.assertEqual(m.decisions[-1]['reason'],'minimum_lot_over_budget')
        self.assertEqual(m.active,{})

    def test_common_research_retains_announced_reserve_guards(self):
        m=r.engine.ResearchReplay(scenario(view='common_research'),broker())
        q=row(duration=1000)
        m.opening(q,q['op'])
        other=row('b',symbol='XAUUSD',t=q['op']+10)
        m.opening(other,other['op'])
        self.assertEqual(m.decisions[-1]['reason'],'daily_reserved_loss')


class CashOwnershipAndDates(unittest.TestCase):
    def test_cash_calendar_zero_month_opening_is_unavailable_not_division(self):
        t=int(datetime.fromisoformat('2026-08-31T12:00:00+00:00').timestamp())
        daily,months,sharpe=r.client_cash_calendar([dict(epoch=t,cash=-1000.)],1000.)
        self.assertEqual(daily[-1]['ending_balance'],0.)
        self.assertEqual(months[0]['return_pct'],-100.)
        self.assertIsNone(months[1]['return_pct'])
        self.assertIsNone(months[2]['return_pct'])
        self.assertIsNone(sharpe)

    def test_cash_calendar_negative_month_opening_keeps_cash_not_return(self):
        t=int(datetime.fromisoformat('2026-08-31T12:00:00+00:00').timestamp())
        daily,months,sharpe=r.client_cash_calendar([dict(epoch=t,cash=-1100.)],1000.)
        self.assertEqual(daily[-1]['ending_balance'],-100.)
        self.assertEqual(months[1]['opening_balance'],-100.)
        self.assertIsNone(months[1]['return_pct'])
        self.assertIsNone(sharpe)

    def test_client_result_handles_exact_cash_exhaustion_after_source_loss(self):
        m=client(name='fixed50')
        q=row(gross=-2000.)
        m.opening(q,q['op'])
        m.closing(q,q['cl'])
        result=m.result()
        self.assertEqual(result['metrics']['ending_balance'],0.)
        self.assertEqual(result['metrics']['return_pct'],-100.)
        self.assertEqual(result['metrics']['capital_exhaustion_epoch'],q['cl'])
        self.assertTrue(result['metrics']['historical_path_executable_uncertainty'])
        self.assertIsNone(result['months'][1]['return_pct'])
        self.assertIsNone(result['metrics']['daily_closed_return_sharpe'])

    def test_censored_entry_fee_is_cash_not_a_closed_trade(self):
        m=client()
        q=row(duration=None,entry_cost=-3.)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,20.,None],q['op']+1)
        result=m.result()
        self.assertEqual(result['metrics']['trades'],0)
        self.assertEqual(result['metrics']['net_profit'],0.)
        self.assertEqual(result['metrics']['ending_balance'],998.5)
        self.assertEqual(result['metrics']['cash_profit'],-1.5)
        self.assertEqual(result['metrics']['ending_sampled_equity'],1008.5)
        self.assertEqual(result['open_positions'][0]['sampled_floating'],10.)
        self.assertEqual(sum(d['net_profit'] for d in result['daily']),-1.5)
        self.assertEqual(sum(d['net_profit'] for d in result['months']),-1.5)
        self.assertEqual(len(result['daily']),61)

    def test_fees_swap_and_stress_are_booked_once(self):
        b=broker()
        b['symbols']['USTEC']['quote_spread']=2.
        m=r.ClientReplay(scenario(),b,stress=True)
        q=row(gross=100.,commission=-10.,swap=-4.,entry_cost=-3.)
        m.opening(q,q['op'])
        m.closing(q,q['cl'])
        self.assertEqual(m.trades[0]['entry_cash'],-2.5)
        self.assertEqual(m.trades[0]['exit_cash'],41.5)
        self.assertEqual(m.trades[0]['net'],39.)
        self.assertEqual(m.balance,1039.)
        self.assertEqual(sum(f['cash'] for f in m.flows),39.)

    def test_unowned_or_duplicate_source_close_is_ignored(self):
        m=client()
        q=row()
        foreign=row('foreign',ea=q['ea'])
        m.opening(q,q['op'])
        m.closing(foreign,foreign['cl'])
        self.assertEqual(m.balance,1000.)
        self.assertEqual(m.flows,[dict(epoch=q['op'],cash=0.,id=q['id'],kind='entry')])
        m.closing(q,q['cl'])
        m.closing(q,q['cl'])
        self.assertEqual(len(m.trades),1)
        self.assertEqual(len(m.flows),2)

    def test_future_or_closed_position_mark_is_rejected(self):
        m=client()
        q=row()
        m.opening(q,q['op'])
        with self.assertRaises(AssertionError):m.mark(q,[q['op']+10,1.,0.],q['op']+1)
        with self.assertRaises(AssertionError):m.mark(q,[q['cl'],1.,0.],q['cl'])

    def test_unowned_marks_are_not_used(self):
        m=client()
        q=row()
        m.mark(q,[q['op']+1,1000.,0.],q['op']+1)
        self.assertEqual(m.equity,1000.)
        self.assertEqual(m.mark_quality,{})

    def test_daily_equity_peak_starts_from_carried_owned_mark(self):
        m=client()
        q=row(duration=100000)
        m.opening(q,q['op'])
        m.mark(q,[q['op']+1,-40.,0.],q['op']+1)
        m.daily_eq_dd=0.
        m.observe(q['op']+86400)
        self.assertEqual(m.day_peak,980.)
        self.assertEqual(m.daily_eq_dd,0.)
        self.assertEqual(m.anchor,1000.)

    def test_same_timestamp_source_close_is_before_new_open(self):
        q=row('a',duration=10)
        other=row('b',t=q['cl'],duration=10)
        events=r.base.events_for(dict(priority=['a','b']),dict(candidates=[q,other]))
        same=[kind for t,kind,*_ in events if t==q['cl']]
        self.assertEqual(same,[1,3])

    def test_zero_duration_source_trade_opens_then_closes(self):
        q=row(duration=0)
        events=r.base.events_for(dict(priority=['a']),dict(candidates=[q]))
        same=[kind for t,kind,*_ in events if t==q['op']]
        self.assertEqual(same,[3,4])

    def test_all_prior_frozen_sources_are_unchanged(self):
        frozen=r.base.read(r.ACTUAL/'FROZEN.json')
        for path,digest in {**frozen['files'],**frozen['source_files']}.items():
            with self.subTest(path=path):self.assertEqual(r.base.sha(path),digest)


if __name__=='__main__':unittest.main(verbosity=2)
