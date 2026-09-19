import numpy as np
import pandas as pd
import pytest
from research import execute, lots_for, simulate_one, gold_signals, gold_data, stamp

def candles(direction=1):
    t=pd.date_range('2024-01-08 14:00',periods=4,freq='min',tz='UTC')
    a=pd.DataFrame({'time':t.astype('int64')//10**9,'open':[2000,2001,2002,2003],'high':[2001,2002,2003,2004],'low':[1999,2000,2001,2002],'close':[2000,2001,2002,2003],'spread':.3,'fx':1.,'atr':5.},index=t)
    return a,{'t':stamp(t[0]),'until':stamp(t[-1]),'dir':direction,'atr':5.}

def test_bid_ask_fees_and_slippage():
    m,s=candles();r=execute(m,s,'gold')
    assert r['entry']==pytest.approx(2000.4)
    assert r['exit']==pytest.approx(2002.9)
    assert r['unit_net']==pytest.approx(250-7e-6*100*(2000.4+2002.9))
    assert r['unit_slippage']==pytest.approx(20)

def test_short_uses_ask_to_close():
    m,s=candles(-1);r=execute(m,s,'gold')
    assert r['entry']==pytest.approx(1999.9)
    assert r['exit']==pytest.approx(2003.4)

def test_time_exit_does_not_see_exit_bar_low():
    m,s=candles();m.iloc[-1,m.columns.get_loc('low')]=100
    r=execute(m,s,'gold');assert r['reason']=='time'
    assert r['unit_worst']>-500

def test_stop_gap_fills_worse_than_stop():
    m,s=candles();m.iloc[1,m.columns.get_loc('open')]=1980;m.iloc[1,m.columns.get_loc('low')]=1975
    r=execute(m,s,'gold');assert r['reason']=='stop'
    assert r['exit']==pytest.approx(1979.9)
    assert r['unit_net'] < -2000

def test_min_lot_never_rounds_up():
    r={'asset':'gold','unit_risk':6000,'unit_margin':12000}
    assert lots_for(r,10000,50)==0
    assert lots_for(r,10000,100)==.01
    r={'asset':'japan','unit_risk':51,'unit_margin':100}
    assert lots_for(r,10000,50)==.9

def test_margin_cap():
    r={'asset':'gold','unit_risk':10,'unit_margin':20000}
    assert lots_for(r,10000,100)==.25

def fake_trade(t,net,worst=0):
    return {'t':stamp(t),'exit_t':stamp(t)+60,'valid':True,'asset':'gold','unit_risk':50,'unit_margin':1,'unit_net':net,'unit_worst':worst}

def test_two_phases_four_dates_and_handover():
    start=pd.Timestamp('2024-01-01',tz='UTC')
    trades=[fake_trade(t,300) for t in pd.date_range('2024-01-01 14:00',periods=20,freq='B',tz='UTC')]
    r=simulate_one(trades,start,30,50)
    assert r['outcome']=='both_passed' and r['trades']==8
    assert r['days']>10

def test_equity_daily_breach_despite_winning_close():
    t=fake_trade(pd.Timestamp('2024-01-01 14:00',tz='UTC'),100,-501)
    r=simulate_one([t],pd.Timestamp('2024-01-01',tz='UTC'),30,50)
    assert r['outcome']=='breach' and r['reason']=='daily'

def test_overall_floor_static():
    start=pd.Timestamp('2024-01-01',tz='UTC')
    trades=[fake_trade(t,-400,-400) for t in pd.date_range('2024-01-01 14:00',periods=3,freq='B',tz='UTC')]
    assert simulate_one(trades,start,30,50)['reason']=='overall'

def test_missing_data_is_inconclusive_not_loss_or_pass():
    start=pd.Timestamp('2024-01-01',tz='UTC')
    assert simulate_one([{'t':stamp(start)+3600,'valid':False}],start,30,50)['outcome']=='data_inconclusive'

def test_unknown_post_entry_path_irrelevant_if_min_lot_cannot_trade():
    start=pd.Timestamp('2024-01-01',tz='UTC')
    tr={'t':stamp(start)+3600,'valid':False,'asset':'gold','unit_risk':6000,'unit_margin':12000}
    assert simulate_one([tr],start,30,50)['outcome']=='pending'

def test_gold_signals_prefix_invariant():
    m=gold_data();signals=[x for x in gold_signals(m) if x.get('valid') is not False]
    # At the instant of each sampled signal, neither today's final return nor
    # today's final bar count exists. It must nevertheless produce the same signal.
    for s in signals[::max(1,len(signals)//5)]:
        prefix=m[m.time<=s['t']]
        q=[x for x in gold_signals(prefix) if x['t']==s['t']]
        assert len(q)==1 and q[0]==s
