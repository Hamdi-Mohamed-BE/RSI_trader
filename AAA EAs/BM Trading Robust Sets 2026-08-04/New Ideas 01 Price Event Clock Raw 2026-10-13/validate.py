"""Saved-result cash, risk, quote, threshold and coverage verification."""
from pathlib import Path
import hashlib
import json
import math
from collections import Counter
import numpy as np
import pandas as pd
import run as e

ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'RESULTS.json').read_text())
assert r['engine_sha256']==hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest()
assert r['protocol_sha256']==hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest()
data,meta=e.prepare()
sources={}
for symbol in e.SYMBOLS:
    f=pd.DataFrame(np.load(ROOT/f'{symbol}-M1.npz',allow_pickle=False)['rates'])
    f.index=pd.to_datetime(f.time,unit='s',utc=True)
    sources[symbol]=f
spot=json.loads((ROOT/'MCP-spot-checks.json').read_text())
spot_count=0
for symbol,rows in spot.items():
    for row in rows:
        b=sources[symbol].loc[pd.Timestamp(row['time'])]
        for field in ['open','high','low','close','tick_volume','spread']:
            assert abs(float(b[field])-row[field])<1e-8
        spot_count+=1

# Independent pandas EMA computation, seeded at the exact Wilder SMA14.
for symbol,f in sources.items():
    m=f.resample('5min').agg({'open':'first','high':'max','low':'min','close':'last','time':'count'})
    m=m[m.time==5]
    tr=np.maximum(m.high-m.low,np.maximum((m.high-m.close.shift()).abs().fillna(0),
                                         (m.low-m.close.shift()).abs().fillna(0)))
    seeded=tr.copy();seeded.iloc[:13]=np.nan;seeded.iloc[13]=tr.iloc[:14].mean()
    atr=seeded.ewm(alpha=1/14,adjust=False).mean()
    atr.index+=pd.Timedelta(minutes=5)
    a=data[symbol]
    # The ATR at midnight only uses M5 bars whose CLOSE timestamp <= midnight.
    for day in pd.date_range('2025-10-13','2026-10-12',tz='UTC'):
        expected=float(atr.loc[atr.index<=day].iloc[-1])
        dayrows=a[(a[:,0]>=day.timestamp())&(a[:,0]<(day+pd.Timedelta(days=1)).timestamp())]
        if len(dayrows):assert np.all(np.abs(dayrows[:,6]-expected)<1e-8)

cases=[p for period in r['periods'].values() for p in period.values()]
cases += [r['ordering_sensitivity'],r['cost_stress']]
for p in cases:
    q=p['summary'];ts=p['trades'];counts=Counter();per_asset={}
    profits=[];risk_by_day=Counter()
    for t in ts:
        symbol=t['symbol'];spec=meta['files'][symbol]['specification']
        entry=t['entry_epoch'];exit=t['exit_epoch']
        assert int(pd.Timestamp(p['start'],tz='UTC').timestamp()) <= entry < e.END
        assert entry<=exit<=e.END+120
        assert t['signal_epoch']<=entry<=t['signal_epoch']+60
        assert t['initial_risk_usd']<=t['entry_balance']*.005+1e-7
        assert t['lots']>=spec['volume_min']-1e-10
        assert abs(t['lots']/spec['volume_step']-round(t['lots']/spec['volume_step']))<1e-7
        assert abs(t['initial_risk_usd']-abs(t['entry']-t['stop'])*t['lots']*spec['trade_contract_size'])<1e-7
        pnl=(t['side']*(t['exit']-t['entry'])*t['lots']*spec['trade_contract_size']-
             t['extra_cost_usd']+t['swap_usd'])
        assert abs(pnl-t['net_usd'])<1e-7
        assert abs(t['net_r']-pnl/t['initial_risk_usd'])<1e-7
        assert abs(abs(t['target']-t['entry'])/abs(t['stop']-t['entry'])-1.5)<=spec['trade_tick_size']/abs(t['stop']-t['entry'])+1e-8
        current=data[symbol][np.searchsorted(data[symbol][:,0],entry)]
        assert current[0]==entry
        expected=current[1]+(current[5] if t['side']>0 else 0)
        assert abs(t['entry']-expected)<1e-7
        stop=t['signal_extreme']-spec['trade_tick_size'] if t['side']>0 else t['signal_extreme']+t['signal_spread']+spec['trade_tick_size']
        assert abs(stop-t['stop'])<1e-7
        counts[entry//86400]+=1;risk_by_day[entry//86400]+=t['initial_risk_usd']
        per_asset.setdefault(symbol,[]).append((entry,exit))
        profits.append(pnl)
    assert max(counts.values(),default=0)<=4
    for symbol,spans in per_asset.items():
        spans.sort()
        assert all(b[0]>=a[1] for a,b in zip(spans,spans[1:])),f'Overlapping {symbol}'
    for day in p['daily_risk_audit']:
        assert day['new_entries']==counts[day['utc_day']]
        # Carry reserve may already exceed a newly reduced allowance, but no extra risk is then added.
        if day['spent']>day['budget']+1e-7:assert day['new_entries']==0
        assert risk_by_day[day['utc_day']]<=day['spent']+1e-7
    assert abs(q['final_balance_usd']-(10000+sum(profits)))<1e-6
    wins=sum(x for x in profits if x>0);losses=-sum(x for x in profits if x<0)
    assert abs(q['profit_factor']-wins/losses)<1e-10
    assert q['wins']==sum(x>0 for x in profits)
    assert q['losses']==sum(x<0 for x in profits)
    assert q['positions_left_open']==0
    assert abs(q['return_pct']-(q['final_balance_usd']/10000-1)*100)<1e-8
    closed=np.r_[10000,10000+np.cumsum(profits)]
    # All live cases have no financing, so chronological closed-trade DD must match exactly.
    assert q['financing_usd']==0
    closed_dd=float((1-closed/np.maximum.accumulate(closed)).max()*100)
    assert abs(closed_dd-q['max_closed_dd_pct'])<1e-7

for symbol in e.SYMBOLS:
    q=r['periods']['1y'][symbol]['summary']
    assert q['trades']>0 and q['return_pct']<0
baseline=r['periods']['1y']['shared']['summary']
assert baseline['return_pct']<0
doc=(ROOT/'Results.html').read_text(encoding='utf-8')
assert all(f'id="{period}"' in doc for period in e.STARTS)
assert '2% daily risk budget, not 2% daily profit' in doc
assert 'not tick-perfect worst floating DD' in doc
assert '-18.40%' in doc
receipt=dict(passed=True,synthetic_tests=13,result_cases=len(cases),mcp_spot_bars=spot_count,
             independent_daily_atr_check=True,chronological_cash_reconciled=True,
             daily_risk_limits_and_one_position_per_asset_checked=True,
             result_sha256=hashlib.sha256((ROOT/'RESULTS.json').read_bytes()).hexdigest(),
             html_sha256=hashlib.sha256((ROOT/'Results.html').read_bytes()).hexdigest())
e.save('VALIDATION.json',receipt)
print(json.dumps(receipt,indent=2))
