import copy
import unittest
import numpy as np
import pandas as pd
import run as e


def frame(day='2020-01-02',end_open=105.):
    start=e.planned_entry(day,'10:10')
    opens=[100.,101.,102.,101.,103.,end_open]
    return pd.DataFrame(dict(open=opens,high=np.array(opens)+1,low=np.array(opens)-1,
                             close=np.array(opens)+.5,used_spread=np.ones(6)),
                        index=pd.date_range(start,periods=6,freq='min'))


class EngineTests(unittest.TestCase):
    def test_ask_entry_bid_exit(self):
        t=e.window(frame(),'2020-01-02','10:10')
        self.assertEqual(t['entry_ask'],101)
        self.assertEqual(t['exit_bid'],105)
        self.assertEqual(t['gross_points'],5)
        self.assertEqual(t['net_points'],4)

    def test_current_candle_close_not_used_as_fill(self):
        f=frame();f.loc[f.index[0],'close']=9999
        f.loc[f.index[-1],'close']=1
        t=e.window(f,'2020-01-02','10:10')
        self.assertEqual(t['net_points'],4)

    def test_missing_middle_minute_not_interpolated(self):
        f=frame().drop(frame().index[2])
        self.assertEqual(e.window(f,'2020-01-02','10:10')['status'],'missing required quote-minute')

    def test_stale_exit_not_accepted(self):
        f=frame();f.index=list(f.index[:-1])+[f.index[-1]+pd.Timedelta(minutes=1)]
        self.assertEqual(e.window(f,'2020-01-02','10:10')['status'],'missing required quote-minute')

    def test_excursion_includes_exit_quote_not_later_exit_bar_extreme(self):
        t=e.window(frame(end_open=70.),'2020-01-02','10:10')
        self.assertEqual(t['mae_points'],-31.)
        f=frame(end_open=125.)
        f.loc[f.index[-1],'high']=9999
        t=e.window(f,'2020-01-02','10:10')
        self.assertEqual(t['mfe_points'],24.)

    def test_full_requested_calendar_includes_nontrade_edges(self):
        t=e.window(frame(),'2020-01-02','10:10')
        q=e.summarize([t],1,calendar_start='2020-01-01',calendar_end='2020-01-06')
        self.assertEqual(q['daily_sharpe_observations'],3)

    def test_dst_and_chicago_ambiguity(self):
        self.assertEqual(e.planned_entry('2020-01-02','10:10').hour,15)
        self.assertEqual(e.planned_entry('2020-07-02','10:10').hour,14)
        self.assertEqual(e.planned_entry('2020-07-02','10:10','America/Chicago'),e.planned_entry('2020-07-02','11:10'))

    def test_cash_holiday_not_silently_filtered(self):
        t=e.window(frame('2020-11-26'),'2020-11-26','10:10')
        self.assertEqual(t['status'],'available')

    def test_unknown_spread_is_not_zero_cost(self):
        f=frame();f.loc[f.index[0],'used_spread']=np.nan
        t=e.window(f,'2020-01-02','10:10')
        self.assertEqual(t['status'],'unknown entry spread')
        self.assertIsNone(t['net_points'])
        self.assertEqual(t['gross_points'],5)

    def test_costs_and_contract_scaling(self):
        t=e.window(frame(),'2020-01-02','10:10')
        q=e.summarize([t],1,.6)
        self.assertAlmostEqual(q['net_points'],3.4)
        self.assertAlmostEqual(e.summarize([t],50)['net_usd'],200)

    def test_missing_year_unavailable_not_flat_return(self):
        t=dict(date='2020-01-02',status='missing required quote-minute')
        q=e.summarize([t],1)
        self.assertEqual(q['status'],'unavailable')
        self.assertIsNone(q['return_pct'])
        self.assertIsNone(q['trades'])

    def test_daily_sharpe_does_not_impute_missing_eligible_day(self):
        a=e.window(frame(),'2020-01-02','10:10')
        b=e.window(frame('2020-01-16',97),'2020-01-16','10:10')
        missing=dict(date='2020-01-09',status='missing required quote-minute')
        q=e.summarize([a,missing,b],1)
        self.assertEqual(q['trades'],2)
        self.assertEqual(q['scheduled'],3)
        self.assertEqual(q['daily_sharpe_observations'],10)
        self.assertAlmostEqual(q['profit_factor'],1)
        self.assertAlmostEqual(q['net_usd'],0)
        self.assertAlmostEqual(q['max_closed_dd_pct'],4/10004*100)

    def test_primary_calendar_has_209_thursdays(self):
        days=pd.date_range('2020-01-01','2023-12-31',freq='B')
        self.assertEqual(sum(d.weekday()==3 for d in days),209)

    def test_null_uses_25_rules_and_is_reproducible(self):
        windows={}
        for j,d in enumerate(pd.date_range('2020-01-01','2020-01-31',freq='B')):
            windows[d.strftime('%Y-%m-%d')]=[
                dict(status='available',gross_points=float(((j+k*3)%7)-3),entry_spread=.1)
                for k in range(5)]
        a=e.joint_null(windows);b=e.joint_null(windows)
        self.assertEqual(a['neighborhood_configurations'],25)
        self.assertEqual(a['simulations'],5000)
        self.assertEqual(a['family_max_null_sharpes'],b['family_max_null_sharpes'])
        self.assertGreaterEqual(a['family_maximum_one_sided_p'],a['fixed_candidate_one_sided_p'])


if __name__=='__main__':unittest.main()
