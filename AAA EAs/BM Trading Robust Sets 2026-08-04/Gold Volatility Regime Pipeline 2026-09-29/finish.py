"""Frozen comparisons and uncertainty audit. Never modifies or selects trading rules."""
import collections, csv, gzip, importlib.util, io, json, math, statistics, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import search as s
spec=importlib.util.spec_from_file_location('calyx_pipeline',s.BASE.parent/'Calyx Research Pipeline/calyx_pipeline.py')
cp=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cp;spec.loader.exec_module(cp)

def load(name):return json.loads((s.OUT/name/'results.json').read_text())[0]
def all_rows():return [r for p in s.OUT.glob('*/results.json') for r in json.loads(p.read_text())]
def confirm():
    verdict=json.loads((s.ROOT/'VERDICT.json').read_text());assert verdict['status']=='QUALIFIED_FOR_ROBUSTNESS',verdict['status']
    b=json.loads((s.ROOT/'FROZEN FINAL.json').read_text())['parameters']
    for label,start in [('6m','2026.03.27'),('3y','2023.09.27'),('5y','2021.09.27')]:s.batch('confirmation-'+label,[b],start,'2026.09.27',4,False)
    s.batch('direction-control-5y',[b],'2021.09.27','2026.09.27',4,False,True)
    s.batch('baseline-validation',[s.DEFAULT],*s.VAL,4,False)
    s.batch('baseline-older',[s.DEFAULT],'2019.09.27','2021.09.27',4,False)

def day_returns(trades,start,end):
    days=np.arange(np.datetime64(start.replace('.','-')),np.datetime64(end.replace('.','-')));days=days[np.is_busday(days)]
    pnl=collections.defaultdict(float)
    for t in trades:pnl[datetime.fromtimestamp(t['close_epoch'],timezone.utc).date().isoformat()]+=t['net_profit']
    balance=10000.;a=[]
    for d in days:
        v=pnl.get(str(d),0.);a.append(v/balance if balance>0 else -1.);balance+=v
    assert abs(balance-10000-sum(t['net_profit'] for t in trades))<1e-6,'Weekday aggregation dropped a trade'
    return np.array(a)

def empirical_dsr(returns,trial_srs,n):
    sr=float(returns.mean()/returns.std(ddof=1));skew,kurt=cp.moments(list(returns));se=math.sqrt(max(1e-12,1-skew*sr+(kurt-1)*sr*sr/4)/(len(returns)-1))
    normal=statistics.NormalDist();g=.5772156649015329
    benchmark=statistics.stdev(trial_srs)*((1-g)*normal.inv_cdf(1-1/n)+g*normal.inv_cdf(1-1/(n*math.e)))
    return dict(probability_pct=100*normal.cdf((sr-benchmark)/se),daily_benchmark=benchmark,trial_sr_sd=statistics.stdev(trial_srs),trials=n,
                assumption='Expected maximum Sharpe uses observed development trial-Sharpe dispersion and treats all passes as independent; correlated trials make this conservative. Daily closed-P&L, not intratrade returns.')

def audit(name,trials,trial_srs):
    row=load(name);trades=s.read_trades(name);trades.sort(key=lambda t:(t['close_epoch'],t['position_id']));pnl=np.array([t['net_profit'] for t in trades]);ret=day_returns(trades,row['start'],row['end'])
    outcomes=[cp.TradeOutcome(datetime.fromtimestamp(t['close_epoch'],timezone.utc),t['net_profit'],t['commission'],t['swap']) for t in trades]
    boot=cp.bootstrap(list(pnl),list(ret),paths=10000,block=5,daily_loss_limit_pct=5,total_loss_limit_pct=10,seed=290929)
    sh=cp.sharpe_statistics(list(ret),trials,252);dsr=empirical_dsr(ret,trial_srs,trials)
    signals={int(x['position_id']):x for x in csv.DictReader(io.StringIO(gzip.decompress((s.OUT/name/'0-signals.csv.gz').read_bytes()).decode()))}
    costs=[]
    for t in trades:
        q=signals[int(t['position_id'])];spread=float(q['spread']);slip=max(0,t['side']*(t['open_price']-float(q['quote'])))
        assert spread>=0 and float(q['quote'])>0
        costs.append((spread+slip)*100*t['volume'])
    cost=np.array(costs);stress=[]
    for factor in [1,2]:
        p=pnl-factor*cost;stress.append(dict(extra_cost_multiple=factor,extra_cost_total=float(factor*cost.sum()),return_pct=float(p.sum()/100),profit_factor=cp.profit_factor(p)))
    rng=np.random.default_rng(290929);missed=[]
    for fraction in [.1,.2]:
        total=[];factors=[]
        for _ in range(10000):
            take=rng.choice(len(pnl),size=max(1,int(len(pnl)*(1-fraction))),replace=False);p=pnl[take];total.append(float(p.sum()/100));factors.append(cp.profit_factor(p))
        missed.append(dict(fraction=fraction,return_p05_pct=float(np.quantile(total,.05)),median_return_pct=float(np.median(total)),pf_p05=float(np.quantile(factors,.05))))
    dd=[]
    for _ in range(10000):
        path=np.r_[10000,10000+np.cumsum(rng.permutation(pnl))];peak=np.maximum.accumulate(path);dd.append(float(np.max((peak-path)/peak)*100))
    thirds=cp.subperiods(outcomes);recent_pf=cp.profit_factor(pnl[len(pnl)//2:]);wins=sum(pnl>0);ci=cp.wilson_interval(int(wins),len(pnl))
    gates=dict(positive_p05_return=boot['return_p05_pct']>0,p05_pf_above_one=boot['profit_factor_p05']>1,
               conservative_dsr_95=dsr['probability_pct']>=95,pipeline_dsr_95=sh['deflated_sharpe_pct']>=95,
               two_profitable_thirds=sum(x['net_profit']>0 for x in thirds)>=2,recent_half_pf_above_one=recent_pf>1,
               measured_cost_stress=stress[0]['profit_factor']>1 and stress[0]['return_pct']>0,native_execution_clean=row['clean'])
    result=dict(period=name,dates=[row['start'],row['end']],native=row['net'],trials=trials,win_rate_wilson_pct=[100*x for x in ci],
                block_bootstrap=boot,pipeline_dsr=sh,empirical_dispersion_dsr=dsr,thirds=thirds,recent_half_pf=recent_pf,cost_stress=stress,
                cost_method='Additional entry-spread equivalent plus observed adverse entry fill/stop-price displacement, per trade, contract=100. Original costs already retained. Fixed-ledger sensitivity, not native changed-spread execution; exit slippage not measured.',
                missed_trades=missed,reshuffle_dd_p50_pct=float(np.median(dd)),reshuffle_dd_p95_pct=float(np.quantile(dd,.95)),
                resampling_caveat='Resamples observed trades/days; not a guarantee, not future probabilities. Reshuffling fixes dollar P&L and endpoint. Bootstrap blocks preserve short local dependence, not unseen regimes.',gates=gates)
    s.save(s.ROOT/('ROBUSTNESS-'+name+'.json'),cp.json_safe(result));return result

def robust():
    verdict=json.loads((s.ROOT/'VERDICT.json').read_text());assert verdict['status']=='QUALIFIED_FOR_ROBUSTNESS'
    rows=all_rows();search_rows=[r for r in rows if (r['start'],r['end'])==s.DEV and r['model']==1]
    trial_srs=[]
    for r in search_rows:
        x=day_returns(s.read_trades(r['stage'],r['index']),r['start'],r['end']);trial_srs.append(float(x.mean()/x.std(ddof=1)) if x.std(ddof=1)>0 else 0.)
    trials=len(rows)+64 # Include retired/duplicate native passes and prior 64-run raw screen.
    results=[audit('confirmation-5y',trials,trial_srs),audit('recent-frozen',trials,trial_srs)]
    passed=all(all(x['gates'].values()) for x in results)
    verdict.update(status='QUALIFIED_FOR_PROP_SCENARIOS' if passed else 'REJECTED_ROBUSTNESS',robustness_periods=[x['period'] for x in results],
                   trial_accounting=dict(current_native_passes=len(rows),prior_raw_passes=64,total_used=trials,development_passes=len(search_rows),unique_current_parameter_vectors=len({r['parameters_sha'] for r in rows})),
                   failed_gates={x['period']:[k for k,v in x['gates'].items() if not v] for x in results})
    s.save(s.ROOT/'VERDICT.json',verdict);s.status('ROBUSTNESS COMPLETE',verdict=verdict['status'],failed=verdict['failed_gates'])

if __name__=='__main__':
    if sys.argv[1]=='confirm':confirm()
    elif sys.argv[1]=='robust':robust()
    elif sys.argv[1]=='all':confirm();robust()
    else:raise ValueError(sys.argv[1])
