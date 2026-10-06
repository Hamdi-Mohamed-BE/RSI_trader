"""Exact-position common audit plus descriptive Monte Carlo; never forecasts payouts."""
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import csv,gzip,hashlib,importlib.util,json,re
import numpy as np
import pandas as pd
import runner as n
R=n.R
s=importlib.util.spec_from_file_location('calyx_common',n.raw.B.parent/'Calyx Research Pipeline/calyx_pipeline.py')
c=importlib.util.module_from_spec(s)
import sys
sys.modules[s.name]=c;s.loader.exec_module(c)
def complete_fixture():
    def row(deal,pos,module,entry,volume,pnl,comm=0):
        return dict(deal=str(deal),position=str(pos),order=str(deal),time=str(1700000000+deal),type='0' if entry==0 else '1',entry=str(entry),module=str(module),volume=str(volume),price='100',profit=str(pnl),commission=str(comm),swap='0',fee='0',comment='fixture')
    ts,ledger=n.position_outcomes([row(2,100,1,0,1,0,-.5),row(3,101,2,0,2,0,-1),row(4,101,2,1,1,-2),row(5,100,1,1,1,1),row(6,101,2,1,1,-2)])
    assert [t['position_id'] for t in ts]==[100,101] and [t['net_profit'] for t in ts]==[.5,-5]
    assert ts[1]['partial_exits']==1 and ledger[-1]['balance']==9995.5
    try:n.position_outcomes([row(4,101,2,1,1,-2)])
    except AssertionError:pass
    else:raise AssertionError('Unmatched close must fail')
def times(r):
    # Index CFD positions can stop out on a Sunday reopening quote. Retain
    # every native cash-flow date, including zero-cash weekends consistently.
    return pd.date_range(r['start'].replace('.','-'),pd.Timestamp(r['end_exclusive'].replace('.','-'))-pd.Timedelta(days=1),freq='D')
def daily(r):
    cash=defaultdict(float)
    for d in r['ledger']:cash[d['time'][:10]]+=d['cash_flow']
    dates=times(r);bal=10000.;rets=[]
    for day in dates:
        x=cash[day.strftime('%Y-%m-%d')];rets.append(x/bal);bal+=x
    assert abs(bal-(10000+r['net_metrics']['net_profit']))<.05
    return dates,np.array(rets)
def enrich(r):
    folder=R/'native'/r['tag'];j=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
    audits={}
    for a in re.findall(r'UKT_ENTRY date=(\d+) module=(\d+) position=(\d+).*?equity=([\d.]+) budget=([\d.]+) requested_stop_cash=([\d.]+) actual_stop_cash=([\d.]+)',j):
        audits[int(a[2])]=dict(module=int(a[1]),equity=float(a[3]),budget=float(a[4]),requested=float(a[5]),actual=float(a[6]))
    assert len(audits)==len(r['trades'])
    for t in r['trades']:
        a=audits[t['position_id']];assert a['module']==t['module'] and abs(a['budget']-a['equity']*float(r['inputs']['InpRiskPercent'])/100)<.001
        assert a['requested']<=a['budget']+.011
    delays=[abs(a['actual']-a['requested']) for a in audits.values()]
    return dict(exact_entry_audits=len(audits),requested_risk_excess_max=max((a['requested']-a['budget'] for a in audits.values()),default=0),observed_fill_stop_cash_difference_p95=float(np.quantile(delays,.95)) if delays else None,risk_rounding_allowance_usd=.011,observed_delay_scope='Cash difference between pre-order executable quote and actual delayed fill, excluding fees; no invented extra spread',positions=audits)
def common(r,extra_cost,count):
    outcomes=[c.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit'],t['commission']+t.get('fee',0),t['swap']) for t in r['trades']]
    native=r['native']
    meta=dict(source_report='native report.htm.gz + exact native position-ID deal exports',initial_balance=10000,reported_net_profit=native['net_profit'],reported_profit_factor=native['profit_factor'],reported_win_rate_pct=native['win_rate_pct'],reported_max_drawdown_pct=native['equity_dd_pct'],reported_trades=native['trades'],reported_sharpe=native['sharpe_ratio'],reported_recovery=native['recovery_factor'],history_quality=native['history_quality'])
    c.parse_mt5_report=lambda _: (meta,outcomes)
    dates,rets=daily(r)
    c.daily_returns=lambda _,initial:(list(dates.date),list(rets),[])
    result=c.audit_report(Path('exact-position-native'),label=r['phase']+' exact-position diagnostic',paths=10000,block=5,tested_configurations=count,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=extra_cost,seed=20261004)
    result['notes']='Daily returns use the full-window actual native deal cash-flow ledger, including entry fees and partial exits. Complete-position PF/WR use exact position IDs. Reported native equity DD is distinct from closed-balance bootstrap DD. Common daily/total-loss values are descriptive proxy, not FTMO pass odds.'
    return c.json_safe(result)
def simulation(r,count):
    dates,rets=daily(r);rng=np.random.default_rng(20261004);paths=10000;length=len(rets);width=min(5,length)
    starts=rng.integers(0,length,(paths,(length+width-1)//width))
    indices=(starts[:,:,None]+np.arange(width))%length;draw=rets[indices.reshape(paths,-1)[:,:length]]
    balance=10000*np.cumprod(1+draw,axis=1);balance=np.column_stack([np.full(paths,10000.),balance])
    peak=np.maximum.accumulate(balance,axis=1);dd=np.max(1-balance/peak,axis=1)*100
    end=(balance[:,-1]/10000-1)*100
    qs=np.quantile(balance,[.05,.5,.95],axis=0)
    pnl=np.array([t['net_profit'] for t in r['trades']])
    reshuffle=[];longest=[]
    for _ in range(paths):
        order=rng.permutation(pnl);curve=np.r_[10000,10000+np.cumsum(order)];pk=np.maximum.accumulate(curve);reshuffle.append(np.max((pk-curve)/pk)*100)
        longest.append(c.streaks(list(order))[1])
    removals=[]
    for fraction in [.1,.2]:
        countkeep=max(1,int(round(len(pnl)*(1-fraction))));ends=[]
        for _ in range(paths):ends.append(float(rng.choice(pnl,countkeep,replace=False).sum()/100))
        removals.append(dict(skip_pct=int(fraction*100),paths=paths,return_p05_pct=float(np.quantile(ends,.05)),return_median_pct=float(np.median(ends)),probability_profit_pct=float(np.mean(np.array(ends)>0)*100)))
    return dict(paths=paths,block_length=5,scope='Closed-balance daily five-day block bootstrap; empirical cash-flow timing, no floating equity/broker resimulation. Trade shuffle and missed-fill scenarios resample fixed cash outcomes, not account-aware sizing.',probability_profit_pct=float(np.mean(end>0)*100),return_p05_pct=float(np.quantile(end,.05)),return_median_pct=float(np.median(end)),return_p95_pct=float(np.quantile(end,.95)),max_closed_dd_median_pct=float(np.median(dd)),max_closed_dd_p95_pct=float(np.quantile(dd,.95)),shuffle_dd_median_pct=float(np.median(reshuffle)),shuffle_dd_p95_pct=float(np.quantile(reshuffle,.95)),shuffle_loss_streak_p95=float(np.quantile(longest,.95)),missed_trades=removals,fan=dict(step=list(range(length+1)),p05=qs[0].tolist(),p50=qs[1].tolist(),p95=qs[2].tolist()),returns=end[::20].tolist())
def main():
    complete_fixture()
    final=json.loads((R/'FINAL RESULTS.json').read_text());frozen=json.loads((R/'FROZEN FINAL.json').read_text());searchrows=json.loads((R/'SEARCH RESULTS.json').read_text())
    validation=json.loads((R/'VALIDATION RESULTS.json').read_text());risk=json.loads((R/'RISK COMPARISON.json').read_text());controls=json.loads((R/'CONTROLS.json').read_text())
    trio=json.loads((R/'OPTIMISED TRIO DIAGNOSTIC.json').read_text())
    configs={r['id'] for r in searchrows}
    for r in list(final.values())+risk+controls+sum(([v['development'],v['validation']] for v in validation),[]):configs.add(r['id'])
    count=len(configs);receipts={};checks=[]
    for r in list(final.values())+list(trio.values())+risk+controls+sum(([v['development'],v['validation']] for v in validation),[]):
        folder=R/'native'/r['tag'];assert r['source_sha256']==n.sha(n.SOURCE)==frozen['source_sha256'] and r['binary_sha256']==n.sha(n.EXPERT)==frozen['binary_sha256']
        assert n.sha(folder/'manifest.json') and n.sha(folder/'stats.csv') and n.sha(folder/'deals.csv')
        assert hashlib.sha256(gzip.decompress((folder/'report.htm.gz').read_bytes())).hexdigest()==r['report_sha256']
        ts,ledger=n.position_outcomes(list(csv.DictReader((folder/'deals.csv').open())))
        assert ts==r['trades'] and ledger==r['ledger']
        receipt=enrich(r);receipts[r['tag']]=receipt
        checks.append(dict(tag=r['tag'],positions=len(ts),costs_pnl_balance_reconciled=True,entry_risk_verified=True,source_hash_verified=True))
    # The measured diagnostic stresses another copy of the observed P95 quote-to-fill
    # cash difference. It is not a measured extra-spread scenario.
    cost=receipts[final['1Y']['tag']]['observed_fill_stop_cash_difference_p95']
    audits={phase:common(final[phase],cost,count) for phase in ['HOLD','1Y','3M','5Y']}
    mc={phase:simulation(final[phase],count) for phase in ['HOLD','1Y','3M']}
    native_years=[];five=final['5Y']
    for year in range(2021,2027):
        ts=[t for t in five['trades'] if t['close_time'].startswith(str(year))]
        native_years.append(dict(year=year,scope='Complete-position contribution inside the one five-year native shared account, not a fresh annual backtest',**n.raw.metrics(ts)))
    report=dict(exploratory=True,pipeline_verdict='REJECT_NO_DEPLOYMENT',unique_configurations=count,development_search_configurations=len(searchrows),native_verification=checks,risk_receipts=receipts,common_audits=audits,monte_carlo=mc,calendar_years=native_years,measured_cost_stress=dict(extra_usd_per_position=cost,method='P95 absolute pre-order-quote vs delayed-fill cash difference on frozen latest-year run. Applied again as extra execution-cost sensitivity.',coverage='Observed execution delay only; independent wider-spread/commission stress missing'),gates=dict(raw_3y_5y=False,minimum_validation_trades=all(v['validation']['net_metrics']['trades']>=30 for v in validation),earlier_holdout_positive=final['HOLD']['net_metrics']['net_profit']>0,earlier_holdout_real_ticks=final['HOLD']['native']['history_quality']=='100% real ticks',latest_year_minimum30=final['1Y']['net_metrics']['trades']>=30,latest_year_pf_115=(final['1Y']['net_metrics']['net_pf'] or 0)>=1.15,latest_quarter_positive=final['3M']['net_metrics']['net_profit']>0,native_floating_equity_path=False,independent_extra_spread_stress=False),deferred=dict(nested_walk_forward='No qualifying native validation/holdout result; fixed-final yearly slices provided instead, NOT claimed as unbiased walk-forward',FTMO_pass_payout_simulation='Rejected prerequisites, insufficient sample and no native intraday floating-equity path; no credible pass/payout odds generated',portfolio_overlap='Rejected standalone candidate; no portfolio addition evaluated',production_website_BAT='Not authorised and candidate rejected'))
    def plain(value):
        if isinstance(value,np.generic):return plain(value.item())
        if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
        if isinstance(value,list):return [plain(v) for v in value]
        return value
    report=plain(report)
    report['optimised_trio_monte_carlo']=simulation(trio['1Y'],count)
    report['optimised_trio_common_audit']=common(trio['1Y'],cost,count)
    report=plain(report)
    n.save(R/'AUDIT.json',report)
    rows=[]
    for phase,r in final.items():rows.append(dict(symbol=r['symbol'],phase=phase,start=r['start'],end_exclusive=r['end_exclusive'],**r['net_metrics'],equity_dd_pct=r['native']['equity_dd_pct'],history_quality=r['native']['history_quality']))
    with (R/'FINAL SUMMARY.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(verdict=report['pipeline_verdict'],unique_configurations=count,year_mc={k:v for k,v in mc['1Y'].items() if k not in ['fan','returns']},cost=cost,gates=report['gates']),indent=2))
if __name__=='__main__':main()
