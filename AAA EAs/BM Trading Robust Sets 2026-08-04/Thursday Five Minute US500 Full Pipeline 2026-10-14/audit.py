"""Independent cash reconciliation, native timing checks and pre-OOS walk-forward diagnostic."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,json,math
import numpy as np
import pandas as pd
import research as r
R=r.R
def walkforward():
    z=np.load(R/'DEVELOPMENT-MATRIX.npz',allow_pickle=False);days=pd.DatetimeIndex(pd.to_datetime(z['dates']));out=[];pnl=[]
    for start in pd.date_range('2022-01-01','2023-07-01',freq='QS'):
        end=start+pd.DateOffset(months=3);train=days<start;test=(days>=start)&(days<end)
        p=dict(days=days[train],net=z['net'][train],gross=z['gross'][train],cost=z['cost'][train],applicable=z['applicable'][train],start='2020-01-01',end=str(start.date()))
        st=r.matrix_stats(p);stress=r.matrix_stats(p,.6);near=[r.neighbors(c) for c in r.CONFIGS];score=np.array([np.quantile(st['sharpe'][a],.25) for a in near]);plateau=np.array([np.mean(st['net'][a]>0) for a in near])
        qualified=(st['trades']>=100)&(st['coverage']>=.99)&(st['pf']>=1.15)&(stress['pf']>1)&(plateau>=.6)
        ranking=sorted(range(8500),key=lambda i:(-score[i],-st['sharpe'][i],r.CONFIGS[i]['hold_minutes'],i));ok=[i for i in ranking if qualified[i]];i=ok[0] if ok else ranking[0]
        q=dict(days=days[test],net=z['net'][test],gross=z['gross'][test],cost=z['cost'][test],applicable=z['applicable'][test],start=str(start.date()),end=str(end.date()))
        m=r.chosen_stats(q,i);out.append(dict(train_end_exclusive=str(start.date()),parameters=r.CONFIGS[i],qualified_train=bool(ok),test=m));a=q['net'][:,i];mask=q['applicable'][:,i]&np.isfinite(a);pnl.extend(a[mask].tolist())
    pnl=np.array(pnl);gain=np.maximum(pnl,0).sum();loss=-np.minimum(pnl,0).sum()
    return dict(scope='Additional post-freeze diagnostic of the selection method; seven expanding-development quarterly folds, all end before validation/OOS. Not used to replace the frozen final candidate. No trades overlap between day-grouped train/test folds.',folds=out,aggregate=dict(trades=len(pnl),net_points=float(pnl.sum()),return_pct=float(pnl.sum()/100),pf=float(gain/loss),win_rate_pct=float((pnl>1e-9).mean()*100)))
def main():
    res=r.load_json('RESULTS.json');lock=r.load_json('FINAL-CANDIDATE.json');native=r.load_json('NATIVE.json');checks=[];native_checks={}
    assert lock['engine_sha256']==r.sha(R/'research.py') and lock['protocol_sha256']==r.sha(R/'PROTOCOL.json')
    assert lock['selection_uses_oos'] is False and res['split']['oos']['start']=='2024-10-14' and res['split']['oos']['end_exclusive']=='2026-10-14'
    assert lock['utc']<res['created_utc'];checks.append('Final candidate hash/time and exact two-year holdout boundaries')
    isf=r.source('IS');oos=r.source('OOS');f=pd.concat([isf,oos]);meta=r.load_json('DATA.json');spots=r.load_json('API-SPOT-CHECKS.json');spotn=0
    for stamp,quotes in spots.items():
        assert quotes
        for q in quotes:
            actual=f.loc[pd.Timestamp(q['time'])]
            for k in ['open','high','low','close','spread']:assert actual[k]==q[k]
            spotn+=1
    checks.append(f'{spotn} direct API quote samples reconcile with immutable sources')
    for name,variant in res['variants'].items():
        cid=r.ORIGINAL if name=='original' else lock['selected_id'];actual=r.records(f,r.CONFIGS[cid],*r.PROTO['oos']);assert actual==variant['trades']
        valid=[t for t in actual if t['status']=='available'];p=np.array([t['net_points'] for t in valid]);m=variant['oos'];assert len(p)==m['trades'] and abs(math.fsum(p)-m['net_usd'])<1e-7
        assert abs(np.maximum(p,0).sum()/-np.minimum(p,0).sum()-m['profit_factor'])<1e-9
        equity=np.r_[10000,10000+p.cumsum()];dd=(1-equity/np.maximum.accumulate(equity)).max()*100;assert abs(dd-m['max_closed_dd_pct'])<1e-9
        assert abs(sum(v['net_usd'] for v in variant['yearly'])-variant['full_history']['net_usd'])<1e-7
        nt=next(t for t in native if t['name']==name+'-OOS');nm=nt['metadata'];ns=nt['stats'];assert ns['failures']==0 and ns['open_positions']==0 and ns['contract']==1 and ns['tick_value']==.01
        cash=math.fsum(t['net_usd'] for t in nt['trades']);assert abs(cash-nm['net_profit'])<.05
        timings=[]
        by_date={t['date']:t for t in actual};different=[]
        for t in nt['trades']:
            day=pd.Timestamp(t['open_epoch'],unit='s',tz='UTC').tz_convert('America/New_York');d=str(day.date());assert day.weekday()==r.CONFIGS[cid]['weekday'] and t['side']==r.CONFIGS[cid]['side']
            rec=by_date[d];entry=pd.Timestamp(rec['entry_utc']).timestamp();exit=pd.Timestamp(rec['exit_utc']).timestamp();assert 0<=t['open_epoch']-entry<60 and 0<=t['close_epoch']-exit<60
            timings.append(dict(date=d,entry_delay_seconds=t['open_epoch']-entry,exit_delay_seconds=t['close_epoch']-exit))
            if rec['status']=='available':different.append(dict(date=d,native_net=t['net_usd'],api_bar_net=rec['net_points'],difference=t['net_usd']-rec['net_points']))
        native_dates={str(pd.Timestamp(t['open_epoch'],unit='s',tz='UTC').date()) for t in nt['trades']}
        missing_native=[t['date'] for t in valid if t['date'] not in native_dates]
        samples=[json.loads(line) for line in gzip.decompress((R/'native'/nt['name']/'equity.jsonl.gz').read_bytes()).decode().splitlines() if line.strip()]
        ev=np.array([t['equity'] for t in samples]);sampledd=(1-ev/np.maximum.accumulate(ev)).max()*100;assert sampledd<=ns['equity_dd_pct']+.03
        nm['comparable_daily_cash_sharpe']=native_sharpe(nt);nm['closed_dd_pct']=float((1-(10000+np.r_[0,np.cumsum([t['net_usd'] for t in nt['trades']])])/np.maximum.accumulate(10000+np.r_[0,np.cumsum([t['net_usd'] for t in nt['trades']])])).max()*100)
        nt['metadata']=nm;native_checks[name]=dict(native_actual_trade_count=nm['trades'],bar_trade_count=len(valid),missing_native_dates=missing_native,fill_cash_differences=different,timing_checks=timings,minute_sampled_equity_dd_pct=float(sampledd),tick_sampled_equity_dd_pct=ns['equity_dd_pct'],all_timing_and_cash_checks_pass=True,exact_pnl_parity=False,reason='Different Exness trial-server history, variable real/simulated tick spreads and 150ms execution. Discrepancies are disclosed, not substituted/cherry-picked.')
    # Reconcile previously shown 2020-2023 original, no silent change to its rules.
    baseline=r.chosen_stats(r.panel(isf,'2020-01-01','2024-01-01'),r.ORIGINAL)
    assert baseline['trades']==209 and abs(baseline['net_usd']-35.21)<1e-7 and abs(baseline['profit_factor']-1.103686907)<1e-8
    checks.append('Prior 2020-2023 original raw results reproduced exactly')
    assert len(r.CONFIGS)==8500 and len(set(tuple(c[k] for k in r.KEYS) for c in r.CONFIGS))==8500
    fake=r.load_json('FAKE-MARKETS.json');assert len(fake['family_maximum'])==5000 and fake['configurations']==8500
    for i,info in fake['candidates'].items():assert abs((1+sum(v>=info['observed_development_sharpe'] for v in fake['family_maximum']))/5001-info['family_max_p'])<1e-12
    checks.append('8500 unique recorded trials; joint-null family p-values independently reconciled')
    # Explicit weekday displacement from the video, diagnostic after freeze only.
    q=r.panel(oos,*r.PROTO['oos']);weekday_rows=[]
    for name,cid in [('original',r.ORIGINAL),('candidate',lock['selected_id'])]:
        c=r.CONFIGS[cid]
        for day in [c['weekday']-1,c['weekday']+1]:
            if not 0<=day<=4:continue
            j=r.LOOKUP[(day,c['entry_minute_et'],c['hold_minutes'],c['side'])]
            weekday_rows.append(dict(reference=name,parameters=r.CONFIGS[j],metrics=r.chosen_stats(q,j)))
    res['weekday_neighbors']=weekday_rows
    wf=walkforward();r.save('WALK-FORWARD.json',wf);r.save('NATIVE.json',native)
    # Measured execution evidence cannot be fabricated from an assumed slippage stress.
    res['gates']['native_equity_path']=True;res['gates']['full_real_tick_coverage']=False;res['gates']['measured_extra_slippage']=False
    res['verdict']='REJECT_FOR_LIVE_RESEARCH_COMPLETE';res['native']=native;res['walkforward_summary']=wf['aggregate'];res['audit']=dict(checks=checks,native_reconciliation=native_checks,full_real_ticks=False,live_changes=False)
    r.save('RESULTS.json',res);r.save('VALIDATION.json',dict(passed=True,checked_utc=r.utcnow(),checks=checks,native_reconciliation=native_checks,results_sha256=r.sha(R/'RESULTS.json'),final_candidate_sha256=r.sha(R/'FINAL-CANDIDATE.json'),no_live_changes=True))
    print(json.dumps(dict(passed=True,checks=checks,walkforward=wf['aggregate'],verdict=res['verdict']),indent=2))
def native_sharpe(nt):
    days=pd.date_range(nt['start'],pd.Timestamp(nt['end_exclusive'])-pd.Timedelta(days=1),freq='B');p=np.zeros(len(days));lookup={str(x.date()):i for i,x in enumerate(days)}
    for t in nt['trades']:p[lookup[str(pd.Timestamp(t['close_epoch'],unit='s',tz='UTC').date())]]+=t['net_usd']
    return float(p.mean()/p.std(ddof=1)*np.sqrt(252))
if __name__=='__main__':main()
