"""Independent quote, clock, cash, daily Sharpe, cost and null reconciliation."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd
import run as e

ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'RESULTS.json').read_text())
assert hashlib.sha256((ROOT/'run.py').read_bytes()).hexdigest()==r['engine_sha256']
assert hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest()==r['protocol_sha256']
f,meta=e.load()
checks=json.loads((ROOT/'API-SPOT-CHECKS.json').read_text())
spots=0
for sample in checks.values():
    assert sample is not None
    for b in sample:
        cached=f.loc[pd.Timestamp(b['time'])]
        for field in ['open','high','low','close','tick_volume','spread']:
            assert abs(float(cached[field])-b[field])<1e-8
        spots+=1

def independent(records,start,end,extra=0.,gross=False):
    pnl=[];dates=[]
    for t in records:
        if t.get('gross_points') is None or (not gross and t['net_points'] is None):continue
        entry=pd.Timestamp(t['entry_utc']);exit=pd.Timestamp(t['exit_utc'])
        local=entry.tz_convert('America/New_York')
        assert local.weekday()==3
        assert local.hour==10 and local.minute==10
        assert exit-entry==pd.Timedelta(minutes=5)
        assert abs(float(f.loc[entry,'open'])-t['entry_bid'])<1e-8
        assert abs(float(f.loc[exit,'open'])-t['exit_bid'])<1e-8
        sp=float(f.loc[entry,'used_spread'])
        assert abs(sp-t['entry_spread'])<1e-8
        assert abs(t['entry_ask']-t['entry_bid']-sp)<1e-8
        cash=(float(f.loc[exit,'open'])-float(f.loc[entry,'open'])-(0 if gross else sp)-extra)*r['cash_per_point']
        pnl.append(cash);dates.append(t['date'])
        assert t['mae_points']<=min(0.,t['net_points'])+1e-8
        assert t['mfe_points']>=max(0.,t['net_points'])-1e-8
    pnl=np.array(pnl)
    index=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1),freq='B')
    day={d.strftime('%Y-%m-%d'):0. for d in index}
    for d,p in zip(dates,pnl):day[d]+=p
    unknown={t['date'] for t in records if t['date'] not in dates}
    daily=np.array([p for d,p in day.items() if d not in unknown])
    balances=np.r_[10000.,10000.+pnl.cumsum()]
    win=sum(p for p in pnl if p>1e-9);loss=-sum(p for p in pnl if p<-1e-9)
    return dict(trades=len(pnl),net_usd=float(pnl.sum()),
                profit_factor=win/loss,return_pct=float(pnl.sum()/10000*100),
                sharpe_daily_cash_252=float(daily.mean()/daily.std(ddof=1)*math.sqrt(252)),
                max_closed_dd_pct=float((1-balances/np.maximum.accumulate(balances)).max()*100))

for name,cost,gross in [('gross',0,True),('baseline',0,False),('cost_stress',.6,False),('severe_stress',1.1,False)]:
    q=independent(r['primary_records'],e.START,e.END,cost,gross)
    for k,v in q.items():assert abs(v-r['cases'][name][k])<1e-8,(name,k)
    assert q['trades']==209
for year in range(2020,2024):
    ts=[t for t in r['primary_records'] if t['date'].startswith(str(year))]
    q=independent(ts,f'{year}-01-01',f'{year+1}-01-01')
    for k,v in q.items():assert abs(v-r['yearly'][str(year)][k])<1e-8,(year,k)
assert abs(sum(v['net_points'] for v in r['yearly'].values())-r['cases']['baseline']['net_points'])<1e-8
assert len(r['neighbors'])==25
assert r['neighbors']['Thursday 10:10']==r['cases']['baseline']

null=r['null_test'];candidate=np.array(null['primary_null_sharpes']);maximum=np.array(null['family_max_null_sharpes'])
assert len(candidate)==len(maximum)==5000
assert np.all(maximum>=candidate-1e-10)
assert abs(null['fixed_candidate_one_sided_p']-(1+(candidate>=null['matched_primary_weekly_sharpe']).sum())/5001)<1e-12
assert abs(null['family_maximum_one_sided_p']-(1+(maximum>=null['matched_primary_weekly_sharpe']).sum())/5001)<1e-12
assert null['neighborhood_configurations']==25
doc=(ROOT/'Results.html').read_text(encoding='utf-8')
assert '<b>not CME ES futures</b>' in doc
assert '2020-01-01' in doc and '2024-01-01' in doc
assert '25 predeclared neighboring rules, not 8,500' in doc
receipt=dict(passed=True,synthetic_tests=14,independent_quote_spot_bars=spots,
             eligible_thursdays=209,unavailable_primary_windows=0,
             independent_cash_and_daily_sharpe_reconciled=True,
             all_four_requested_years_present=True,null_pvalues_reconciled=True,
             result_sha256=hashlib.sha256((ROOT/'RESULTS.json').read_bytes()).hexdigest(),
             html_sha256=hashlib.sha256((ROOT/'Results.html').read_bytes()).hexdigest())
e.save('VALIDATION.json',receipt)
print(json.dumps(receipt,indent=2))
