import copy
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import run as e


def context(side=1, later=None, first=None):
    # Bid OHLC, with 1.00 point spread, and a 10-point initial stop.
    start=e.utc('2020-01-02','09:30')
    opening=[[95,100,90,99,100,1] for _ in range(5)]
    opening[0][0]=95
    opening[-1][3]=99 if side==1 else 91
    if side==-1:opening[0][0]=95
    first=first or ([98,101,88,100,100,1] if side==1 else [92,105,89,89,100,1])
    rows=opening+[first]+(later or [])
    frame=pd.DataFrame(rows,columns=['open','high','low','close','tick_volume','used_spread'],
                       index=pd.date_range(start,periods=len(rows),freq='min'))
    end=e.utc('2020-01-02','16:00')
    close=pd.Series(dict(open=110 if side==1 else 80,used_spread=1.))
    return dict(date='2020-01-02',start=start,end=end,bars=frame,close_row=close,close_time=end,
                opening_high=100.,opening_low=90.,opening_open=95.,opening_close=99. if side==1 else 91.,
                atr14=100.,rvol=2.,opening_volume=500.,avg_previous_volume=250.,data_skip=None)


class EngineTests(unittest.TestCase):
    def test_long_ambiguous_entry(self):
        c=context()
        a=e.simulate_trade(c); b=e.simulate_trade(c,True)
        self.assertEqual(a['r'],-1)
        self.assertEqual(b['r'],1)
        self.assertTrue(a['ambiguous_entry_bar'])
        self.assertEqual(a['entry'],100)

    def test_short_ambiguous_entry(self):
        a=e.simulate_trade(context(-1)); b=e.simulate_trade(context(-1),True)
        self.assertEqual(a['r'],-1)
        self.assertAlmostEqual(b['r'],.9) # Ask close includes spread.

    def test_entry_gap_is_worse_and_stop_is_from_fill(self):
        c=context(first=[103,105,98,104,100,1])
        t=e.simulate_trade(c)
        self.assertEqual(t['entry'],104)
        self.assertEqual(t['stop'],94)
        self.assertTrue(t['entry_open_gap'])

    def test_later_stop_gap_exceeds_one_r(self):
        c=context(first=[100,103,97,102,100,1],later=[[80,85,78,82,100,1]])
        t=e.simulate_trade(c)
        self.assertEqual(t['entry'],101)
        self.assertAlmostEqual(t['r'],-2.1)

    def test_pre_entry_low_is_not_a_stop_gap_fill(self):
        t=e.simulate_trade(context(first=[80,101,75,100,100,1]))
        self.assertEqual(t['entry'],100)
        self.assertEqual(t['exit'],90)

    def test_close_below_stop_cannot_be_optimistically_ignored(self):
        c=context(first=[98,101,80,85,100,1])
        self.assertEqual(e.simulate_trade(c,True)['r'],-1)

    def test_threshold_exactly_two_passes(self):
        c=context(); self.assertEqual(e.run([c])['summary']['trades'],1)
        c['rvol']=1.999999
        self.assertEqual(e.run([c])['summary']['trades'],0)

    def test_doji_skipped(self):
        c=context();c['opening_close']=c['opening_open']
        self.assertEqual(e.run([c])['summary']['session_statuses'],{'doji':1})

    def test_no_fill_and_no_second_entry(self):
        c=context(first=[95,97,91,94,100,1])
        self.assertIsNone(e.simulate_trade(c))
        c=context(later=[[100,110,95,108,100,1]])
        self.assertEqual(e.run([c])['summary']['trades'],1)

    def test_risk_rounds_down_and_cost_reconciles(self):
        c=context();c['atr14']=123.456
        t=e.run([c])['trades'][0]
        self.assertLessEqual(t['planned_risk_usd'],100.+1e-10)
        cost=e.run([c],extra_cost=2.)['trades'][0]
        self.assertAlmostEqual(t['net_usd']-cost['net_usd'],2*t['lots'])

    def test_holidays_early_close_and_dst(self):
        cal={d:(s,end) for d,s,end in e.cash_sessions()}
        self.assertIn('2021-06-18',cal)
        self.assertNotIn('2022-06-20',cal)
        self.assertIn('2021-12-31',cal)
        self.assertEqual(cal['2020-11-27'][1],e.utc('2020-11-27','13:00'))
        self.assertEqual(e.utc('2020-01-02','09:30').hour,14)
        self.assertEqual(e.utc('2020-07-02','09:30').hour,13)

    def test_lagged_average_not_median_and_no_current_day_atr(self):
        days=[];frames=[]
        for i,d in enumerate(pd.bdate_range('2020-01-02',periods=18)):
            day=d.strftime('%Y-%m-%d');start=e.utc(day,'09:30');end=start+pd.Timedelta(minutes=6)
            days.append((day,start,end))
            row=[100+i,105+i,95+i,101+i,100 if i!=16 else 10000,1.]
            f=pd.DataFrame([row]*7,index=pd.date_range(start,periods=7,freq='min'),
                           columns=['open','high','low','close','tick_volume','used_spread'])
            frames.append(f)
        data=pd.concat(frames)
        with patch.object(e,'cash_sessions',return_value=days):
            cs=e.contexts(data)
        self.assertEqual(cs[16]['avg_previous_volume'],500)
        self.assertEqual(cs[16]['rvol'],100)
        self.assertAlmostEqual(cs[16]['atr14'],10)
        # Current day's giant range must not alter today's lagged ATR.
        changed=data.copy();changed.loc[days[16][1]+pd.Timedelta(minutes=5),'high']=10000
        with patch.object(e,'cash_sessions',return_value=days):
            altered=e.contexts(changed)
        self.assertEqual(altered[16]['atr14'],cs[16]['atr14'])
        self.assertGreater(altered[17]['atr14'],cs[17]['atr14'])
        self.assertGreater(altered[17]['avg_previous_volume'],500)

    def test_metrics_peak_drawdown_and_reconciliation(self):
        ts=[dict(starting_balance=10000,ending_balance=11000,net_usd=1000,net_r=10,side=1,exit_reason='Cash close',ambiguous_entry_bar=False,notional_leverage=2),
            dict(starting_balance=11000,ending_balance=9900,net_usd=-1100,net_r=-1,side=-1,exit_reason='SL',ambiguous_entry_bar=False,notional_leverage=2),
            dict(starting_balance=9900,ending_balance=12000,net_usd=2100,net_r=20,side=1,exit_reason='Cash close',ambiguous_entry_bar=False,notional_leverage=2)]
        ss=[dict(balance=t['ending_balance'],status='trade') for t in ts]
        m=e.metrics(ts,ss)
        self.assertAlmostEqual(m['max_closed_dd_pct'],10)
        self.assertAlmostEqual(m['profit_factor'],3100/1100)
        self.assertAlmostEqual(m['net_usd'],sum(t['net_usd'] for t in ts))


if __name__=='__main__':
    unittest.main(verbosity=2)
