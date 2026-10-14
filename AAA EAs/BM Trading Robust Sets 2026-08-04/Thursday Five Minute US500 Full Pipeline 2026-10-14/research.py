"""Predeclared clock search and leakage-controlled holdout evaluation. No trading API."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
from statistics import NormalDist
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import argparse,hashlib,html,importlib.util,itertools,json,math
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent;P=B.parent/'Calyx Research Pipeline'
PROTO=json.loads((R/'PROTOCOL.json').read_text());GRID=PROTO['grid'];WD=['Monday','Tuesday','Wednesday','Thursday','Friday']
CONFIGS=[dict(id=i,weekday=w,entry_minute_et=t,hold_minutes=h,side=s) for i,(w,t,h,s) in enumerate(itertools.product(GRID['weekdays'],GRID['entry_minutes_et'],GRID['hold_minutes'],GRID['sides']))]
KEYS=['weekday','entry_minute_et','hold_minutes','side'];LOOKUP={tuple(c[k] for k in KEYS):c['id'] for c in CONFIGS}
ORIGINAL=LOOKUP[tuple(PROTO['original'][k] for k in KEYS)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(x):
    if isinstance(x,dict):return {k:safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)):return [safe(v) for v in x]
    if isinstance(x,np.generic):return safe(x.item())
    if isinstance(x,float) and not math.isfinite(x):return None
    return x
def save(name,obj):
    p=R/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(safe(obj),indent=2,allow_nan=False),encoding='utf-8')
def load_json(name):return json.loads((R/name).read_text())
def utcnow():return datetime.now(timezone.utc).isoformat()
def status(msg):print(msg,flush=True);save('STATUS.json',dict(message=msg,utc=utcnow()))
def label(c):
    t=c['entry_minute_et'];h=c['hold_minutes'];return f"{WD[c['weekday']]} {t//60:02d}:{t%60:02d} ET / {h} min / {'long' if c['side']==1 else 'short'}"
def module(name,path):
    import sys
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
PIPE=module('clock_pipeline',P/'calyx_pipeline.py')
def source(kind):
    if kind=='OOS':
        assert (R/'FINAL-CANDIDATE.json').exists(),'Holdout forbidden before final freeze'
        frozen=load_json('FINAL-CANDIDATE.json');assert frozen['protocol_sha256']==sha(R/'PROTOCOL.json') and frozen['engine_sha256']==sha(Path(__file__)),'Frozen specification changed'
    meta=load_json('DATA.json');p=R/meta['files'][kind]['filename'];assert sha(p)==meta['files'][kind]['sha256']
    f=pd.DataFrame(np.load(p,allow_pickle=False)['rates']);f.index=pd.DatetimeIndex(pd.to_datetime(f.time,unit='s',utc=True)).as_unit('us')
    assert f.index.is_unique and f.index.is_monotonic_increasing
    assert ((f.high>=f[['open','low','close']].max(axis=1))&(f.low<=f[['open','high','close']].min(axis=1))).all()
    f['used_spread']=f.spread.where(f.spread>0).ffill()*meta['specification']['point']
    # Any initial unknown OOS spread can only inherit the last historical IS quote.
    if kind=='OOS' and f.used_spread.isna().any():
        q=np.load(R/meta['files']['IS']['filename'],allow_pickle=False)['rates'];sp=q['spread'][q['spread']>0]
        if len(sp):f.used_spread=f.used_spread.fillna(float(sp[-1])*meta['specification']['point'])
    return f
def panel(f,start,end,configs=CONFIGS):
    days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1),freq='B')
    startmin=min(c['entry_minute_et'] for c in configs);last=max(c['entry_minute_et']+c['hold_minutes'] for c in configs)
    n=last-startmin+1
    starts=pd.DatetimeIndex([pd.Timestamp(f'{d:%Y-%m-%d} {startmin//60:02d}:{startmin%60:02d}',tz='America/New_York').tz_convert('UTC') for d in days]).as_unit('us')
    stamps=(starts.asi8[:,None]+np.arange(n)[None,:]*60_000_000).ravel()
    bars=f.reindex(pd.DatetimeIndex(pd.to_datetime(stamps,unit='us',utc=True)))
    op=bars.open.to_numpy().reshape(len(days),n);sp=bars.used_spread.to_numpy().reshape(len(days),n)
    missing=np.c_[np.zeros(len(days)),np.cumsum(~np.isfinite(op),axis=1)]
    gross=np.zeros((len(days),len(configs)));cost=np.zeros_like(gross);applicable=np.zeros_like(gross,dtype=bool)
    for j,c in enumerate(configs):
        a=c['entry_minute_et']-startmin;z=a+c['hold_minutes'];mask=np.asarray(days.weekday)==c['weekday']
        ok=(missing[:,z+1]-missing[:,a]==0)&np.isfinite(sp[:,a if c['side']==1 else z]);active=mask&ok
        applicable[:,j]=mask;gross[active,j]=c['side']*(op[active,z]-op[active,a]);cost[active,j]=sp[active,a if c['side']==1 else z]
        gross[mask&~ok,j]=np.nan;cost[mask&~ok,j]=np.nan
    return dict(days=days,gross=gross,cost=cost,net=gross-cost,applicable=applicable,start=start,end=end)
def matrix_stats(p,extra=0):
    x=p['net']-np.where(p['applicable'],extra,0);valid=np.isfinite(x);z=np.nan_to_num(x);n=valid.sum(axis=0);s=z.sum(axis=0);v=(z*z).sum(axis=0)
    sd=np.sqrt(np.maximum(0,(v-s*s/n)/(n-1)));sr=np.divide(s/n,sd,out=np.zeros_like(s),where=sd>0)*np.sqrt(252)
    gp=np.maximum(z,0).sum(axis=0);gl=-np.minimum(z,0).sum(axis=0);pf=np.divide(gp,gl,out=np.full_like(s,np.nan),where=gl>0)
    tr=(p['applicable']&valid).sum(axis=0);scheduled=p['applicable'].sum(axis=0);wr=(z>1e-9).sum(axis=0)/np.maximum(tr,1)*100
    return dict(trades=tr,scheduled=scheduled,missing=scheduled-tr,coverage=tr/np.maximum(scheduled,1),pf=pf,sharpe=sr,net=s,win_rate=wr)
def neighbors(c):
    out=[]
    for d in [-10,-5,5,10]:
        key=(c['weekday'],c['entry_minute_et']+d,c['hold_minutes'],c['side'])
        if key in LOOKUP:out.append(LOOKUP[key])
    j=GRID['hold_minutes'].index(c['hold_minutes'])
    for k in [j-1,j+1]:
        if 0<=k<len(GRID['hold_minutes']):out.append(LOOKUP[(c['weekday'],c['entry_minute_et'],GRID['hold_minutes'][k],c['side'])])
    return sorted(set(out))
def chosen_stats(p,i,extra=0,gross=False):
    c=CONFIGS[i];active=p['applicable'][:,i];known=np.isfinite(p['net'][:,i]);x=(p['gross'][:,i] if gross else p['net'][:,i]).copy();x[active]-=extra
    trades=x[active&known];daily=x[known];times=p['days'][active&known];n=len(trades);s=float(trades.sum())
    balance=np.r_[10000,10000+trades.cumsum()];dd=float((1-balance/np.maximum.accumulate(balance)).max()*100)
    gp=trades[trades>1e-9];gl=trades[trades<-1e-9];wins=len(gp);mw,ml=PIPE.streaks(trades.tolist());lo,hi=PIPE.wilson_interval(wins,n)
    return dict(label=label(c),start=p['start'],end_exclusive=p['end'],scheduled=int(active.sum()),trades=n,missing=int((active&~known).sum()),
                profit_factor=float(gp.sum()/-gl.sum()) if len(gl) else None,win_rate_pct=wins/n*100 if n else None,
                net_usd=s,return_pct=s/100,final_balance_usd=10000+s,sharpe=float(daily.mean()/daily.std(ddof=1)*np.sqrt(252)) if daily.std(ddof=1)>0 else None,
                max_closed_dd_pct=dd,max_win_streak=mw,max_loss_streak=ml,mean_win_points=float(gp.mean()) if len(gp) else None,
                mean_loss_points=float(gl.mean()) if len(gl) else None,mean_trade_points=float(trades.mean()) if n else None,
                wilson95_pct=[lo*100,hi*100],extra_points=extra,gross_only=gross,daily_observations=len(daily),
                max_loss_points=float(trades.min()) if n else None,first_trade=str(times[0].date()) if n else None,last_trade=str(times[-1].date()) if n else None)
def select():
    assert not (R/'FINAL-CANDIDATE.json').exists(),'Selection already frozen; no reranking'
    status('Building development-only 8500-rule matrix')
    f=source('IS');dev=panel(f,*PROTO['development']);d=matrix_stats(dev);stress=matrix_stats(dev,.6)
    neigh=[neighbors(c) for c in CONFIGS];plateau=np.array([np.mean(d['net'][v]>0) for v in neigh]);score=np.array([np.quantile(d['sharpe'][v],.25) for v in neigh])
    thirds=np.array([matrix_stats(dict(dev,days=dev['days'][k],net=dev['net'][k],gross=dev['gross'][k],cost=dev['cost'][k],applicable=dev['applicable'][k]))['net']>0 for k in np.array_split(np.arange(len(dev['days'])),3)]).sum(axis=0)
    gate=(d['trades']>=100)&(d['coverage']>=.99)&(d['pf']>=1.15)&(stress['pf']>1)&(thirds>=2)&(plateau>=.6)
    rank=sorted(range(len(CONFIGS)),key=lambda i:(-score[i],-d['sharpe'][i],CONFIGS[i]['hold_minutes'],i))
    # Prefer qualifying development rules; otherwise retain clearly marked exploration.
    preferred=[i for i in rank if gate[i]];shortlist=(preferred+[i for i in rank if not gate[i]])[:100]
    status(f'Development complete: {int(gate.sum())} qualified rules; validating fixed shortlist')
    val=panel(f,*PROTO['validation']);v=matrix_stats(val);vs=matrix_stats(val,.6)
    vp=np.array([np.mean(v['net'][a]>0) for a in neigh]);vg=(v['trades']>=30)&(v['coverage']>=.99)&(v['pf']>1)&(vs['pf']>1)&(vp>=.5)
    balanced=np.minimum(score,v['sharpe']);order=sorted(shortlist,key=lambda i:(-balanced[i],-score[i],CONFIGS[i]['hold_minutes'],i));eligible=[i for i in order if gate[i] and vg[i]]
    selected=eligible[0] if eligible else order[0]
    records=[]
    for i,c in enumerate(CONFIGS):records.append(dict(c,development={k:a[i] for k,a in d.items()},dev_neighbor_p25_sharpe=score[i],dev_neighbor_positive_share=plateau[i],development_gate=bool(gate[i]),profitable_thirds=int(thirds[i]),
        validation={k:a[i] for k,a in v.items()} if i in shortlist or i==ORIGINAL else None,validation_neighbor_positive_share=vp[i] if i in shortlist else None,validation_gate=bool(vg[i]) if i in shortlist else None,balanced_score=balanced[i] if i in shortlist else None))
    save('SEARCH.json',dict(configurations=records,shortlist=shortlist,rank_by_development=rank,qualified_development=int(gate.sum()),qualified_validation_shortlist=len(eligible),original_id=ORIGINAL))
    frozen=dict(utc=utcnow(),protocol_sha256=sha(R/'PROTOCOL.json'),engine_sha256=sha(Path(__file__)),data_is_sha256=load_json('DATA.json')['files']['IS']['sha256'],search_sha256=sha(R/'SEARCH.json'),selected_id=selected,parameters=CONFIGS[selected],label=label(CONFIGS[selected]),exploratory=not bool(eligible),selection_uses_oos=False,shortlist_for_diagnostics_only=shortlist,
        development=chosen_stats(dev,selected),validation=chosen_stats(val,selected),original_development=chosen_stats(dev,ORIGINAL),original_validation=chosen_stats(val,ORIGINAL),dev_trials_sr_std=float(np.std(d['sharpe']/np.sqrt(252),ddof=1)))
    save('FINAL-CANDIDATE.json',frozen)
    np.savez_compressed(R/'DEVELOPMENT-MATRIX.npz',gross=dev['gross'],cost=dev['cost'],net=dev['net'],applicable=dev['applicable'],dates=np.array([str(x.date()) for x in dev['days']]))
    save('BASELINE-ONE-FACTOR.json',[records[i] for i,c in enumerate(CONFIGS) if sum(c[k]!=PROTO['original'][k] for k in KEYS)<=1])
    status('FINAL FROZEN: '+frozen['label']+(' — exploratory' if frozen['exploratory'] else ' — pre-OOS qualified'))
    print(json.dumps(safe(frozen),indent=2),flush=True)
def pbo(net):
    blocks=np.array_split(np.arange(len(net)),10);rows=[]
    sums=np.array([np.nan_to_num(net[k]).sum(axis=0) for k in blocks]);sq=np.array([(np.nan_to_num(net[k])**2).sum(axis=0) for k in blocks]);ns=np.array([np.isfinite(net[k]).sum(axis=0) for k in blocks])
    def sr(k):
        s=sums[k].sum(axis=0);q=sq[k].sum(axis=0);n=ns[k].sum(axis=0);mean=s/n;sd=np.sqrt(np.maximum(0,(q-s*s/n)/(n-1)));return np.divide(mean,sd,out=np.zeros_like(mean),where=sd>0)
    for train in itertools.combinations(range(10),5):
        test=sorted(set(range(10))-set(train));a=sr(list(train));b=sr(test);winner=int(np.argmax(a));pct=(np.sum(b<b[winner])+.5*np.sum(b==b[winner]))/len(b);rows.append(dict(train_blocks=train,winner_id=winner,train_sharpe=a[winner]*np.sqrt(252),test_sharpe=b[winner]*np.sqrt(252),test_rank_percentile=pct,overfit=pct<=.5))
    return dict(method='CSCV full 8500-rule search; 10 chronological day-grouped blocks, 252 symmetric partitions',pbo_pct=np.mean([x['overfit'] for x in rows])*100,splits=rows)
def joint_fake(g,c,days,ids):
    # Gross returns of all rules share the same calendar-week sign. Friction never flips.
    weeks=pd.DatetimeIndex(days).to_period('W-SUN').astype(str);uniq,inv=np.unique(weeks,return_inverse=True);G=np.nan_to_num(g);C=np.nan_to_num(c);n=np.isfinite(g).sum(axis=0);cost=C.sum(axis=0)
    wg=np.zeros((len(uniq),len(CONFIGS)));wgc=np.zeros_like(wg)
    np.add.at(wg,inv,G);np.add.at(wgc,inv,G*C);q=(G*G+C*C).sum(axis=0)
    actual=(G-C).sum(axis=0);mean=actual/n;sd=np.sqrt(np.maximum(0,(q-2*(G*C).sum(axis=0)-actual*actual/n)/(n-1)));obs=np.divide(mean,sd,out=np.zeros_like(mean),where=sd>0)*np.sqrt(252)
    rng=np.random.default_rng(2026101401);maximum=[];fixed={i:[] for i in ids}
    for offset in range(0,5000,100):
        signs=rng.choice([-1.,1.],size=(100,len(uniq)));s=signs@wg-cost;qf=q[None,:]-2*(signs@wgc);means=s/n;dev=np.sqrt(np.maximum(0,(qf-s*s/n)/(n-1)))
        scores=np.divide(means,dev,out=np.zeros_like(means),where=dev>0)*np.sqrt(252);maximum.extend(scores.max(axis=1))
        for i in ids:fixed[i].extend(scores[:,i])
        if offset%1000==0:status(f'Joint fake-market worlds {offset+100}/5000 — all 8500 rules in each')
    mx=np.array(maximum)
    return dict(worlds=5000,configurations=8500,seed=2026101401,assumption='Symmetric zero-drift week-level signs conditional on observed magnitudes; not every possible null market',fake_best_sharpe_p50=float(np.quantile(mx,.5)),fake_best_sharpe_p95=float(np.quantile(mx,.95)),
      observed_best_sharpe=float(obs.max()),best_observed_id=int(np.argmax(obs)),best_search_family_p=float((1+(mx>=obs.max()).sum())/5001),
      candidates={str(i):dict(observed_development_sharpe=float(obs[i]),fixed_rule_p=float((1+(np.array(fixed[i])>=obs[i]).sum())/5001),family_max_p=float((1+(mx>=obs[i]).sum())/5001)) for i in ids},family_maximum=maximum)
def bootstrap(p,i,block=5,paths=10000):
    # One shared resampled daily-cash series drives every metric, unlike separate PF/PnL resamples.
    if np.any(p['applicable'][:,i]&~np.isfinite(p['net'][:,i])):return dict(status='incomplete eligible history; bootstrap not substituted',paths=0)
    daily=p['net'][:,i];weeks=p['days'].to_period('W-SUN').astype(str);uniq,inv=np.unique(weeks,return_inverse=True)
    w=np.zeros((len(uniq),5));w[inv,p['days'].weekday]=daily;L=len(w)
    rng=np.random.default_rng(2026101402+block);returns=[];drawdowns=[];factors=[];daily_breach=[];total_breach=[]
    for batch in range(0,paths,200):
        starts=rng.integers(L,size=(200,math.ceil(L/block)));indices=(starts[:,:,None]+np.arange(block)[None,None,:])%L;idx=indices.reshape(200,-1)[:,:L];cash=w[idx].reshape(200,-1)
        # Drop weekdays that are outside the original start/end range, not interior non-trading days.
        cash=cash[:,:len(daily)];bal=np.c_[np.full(200,10000.),10000+np.cumsum(cash,axis=1)];peak=np.maximum.accumulate(bal,axis=1);dd=(1-bal/peak).max(axis=1)*100
        gains=np.maximum(cash,0).sum(axis=1);loss=-np.minimum(cash,0).sum(axis=1);pf=np.divide(gains,loss,out=np.full(200,np.inf),where=loss>0)
        returns.extend(cash.sum(axis=1)/100);drawdowns.extend(dd);factors.extend(pf);daily_breach.extend((cash<=-500).any(axis=1));total_breach.extend((bal<=9000).any(axis=1))
    returns=np.array(returns);factors=np.array(factors);dd=np.array(drawdowns)
    return dict(paths=paths,block_calendar_weeks=block,probability_profit_pct=float((returns>0).mean()*100),return_p05_pct=float(np.quantile(returns,.05)),return_p50_pct=float(np.quantile(returns,.5)),return_p95_pct=float(np.quantile(returns,.95)),pf_p05=float(np.quantile(factors,.05)),pf_p50=float(np.quantile(factors,.5)),pf_p95=float(np.quantile(factors,.95)),dd_p50_pct=float(np.quantile(dd,.5)),dd_p95_pct=float(np.quantile(dd,.95)),closed_daily_5pct_breach_pct=float(np.mean(daily_breach)*100),closed_total_10pct_breach_pct=float(np.mean(total_breach)*100),scope='Fixed 1-lot cash replay, closed-PnL only. No funding/pass claim, no stop-defined percent risk.')
def dsr(daily,dispersion):
    x=np.array(daily);x=x[np.isfinite(x)];sr=x.mean()/x.std(ddof=1);sk,ku=PIPE.moments(x.tolist());se=np.sqrt(max(1e-12,1-sk*sr+(ku-1)/4*sr*sr)/(len(x)-1));N=8500;normal=NormalDist();gamma=.5772156649015329
    benchmark=dispersion*((1-gamma)*normal.inv_cdf(1-1/N)+gamma*normal.inv_cdf(1-1/(N*math.e)))
    return dict(dsr_pct=normal.cdf((sr-benchmark)/se)*100,benchmark_annualized=benchmark*np.sqrt(252),nominal_trials=N,trial_sr_std=dispersion,conservative_independence_assumption=True,saved_pipeline=PIPE.sharpe_statistics(x.tolist(),N,252))
def records(f,c,start,end):
    result=[]
    for d in pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1),freq='B'):
        if d.weekday()!=c['weekday']:continue
        t=c['entry_minute_et'];a=pd.Timestamp(f'{d:%Y-%m-%d} {t//60:02d}:{t%60:02d}',tz='America/New_York').tz_convert('UTC');z=a+pd.Timedelta(minutes=c['hold_minutes']);bars=f.reindex(pd.date_range(a,z,freq='min'))
        r=dict(date=str(d.date()),entry_utc=a.isoformat(),exit_utc=z.isoformat(),side=c['side'],status='missing minute')
        if bars.open.isna().any() or bars.used_spread.isna().any():result.append(r);continue
        entry=float(bars.open.iloc[0]+(bars.used_spread.iloc[0] if c['side']==1 else 0));exit=float(bars.open.iloc[-1]+(bars.used_spread.iloc[-1] if c['side']==-1 else 0));net=c['side']*(exit-entry)
        if c['side']==1:
            pathlo=bars.low.iloc[:-1].to_numpy()-entry;pathhi=bars.high.iloc[:-1].to_numpy()-entry
        else:
            pathlo=entry-bars.high.iloc[:-1].to_numpy()-bars.used_spread.iloc[:-1].to_numpy();pathhi=entry-bars.low.iloc[:-1].to_numpy()-bars.used_spread.iloc[:-1].to_numpy()
        r.update(status='available',entry=entry,exit=exit,net_points=net,entry_bid=float(bars.open.iloc[0]),exit_bid=float(bars.open.iloc[-1]),spread_points=float(bars.used_spread.iloc[0 if c['side']==1 else -1]),mae_points=float(min(0,pathlo.min(),net)),mfe_points=float(max(0,pathhi.max(),net)));result.append(r)
    return result
def final():
    lock=load_json('FINAL-CANDIDATE.json');i=lock['selected_id'];status('Opening two-year holdout for locked candidate only; selection is closed')
    f=source('OOS');oos=panel(f,*PROTO['oos']);m=matrix_stats(oos);shortlist=lock['shortlist_for_diagnostics_only']
    diagnostic=[dict(id=j,parameters=CONFIGS[j],metrics=chosen_stats(oos,j)) for j in shortlist]
    rows={}
    for name,cid in [('original',ORIGINAL),('candidate',i)]:
        rows[name]=dict(oos=chosen_stats(oos,cid),costs=[chosen_stats(oos,cid,x) for x in [0,.6,1.1]],bootstrap=[bootstrap(oos,cid,b) for b in [1,5,10]],trades=records(f,CONFIGS[cid],*PROTO['oos']),recent={},yearly=[])
        for months in [3,6,12]:
            st=str((pd.Timestamp(PROTO['end_exclusive'])-pd.DateOffset(months=months)).date());rows[name]['recent'][str(months)+'m']=chosen_stats(panel(f,st,PROTO['end_exclusive']),cid)
        thirds=[]
        for bounds in np.array_split(np.arange(len(oos['days'])),3):
            pp={k:(v[bounds] if k in ['days','gross','cost','net','applicable'] else v) for k,v in oos.items()};pp['start']=str(pp['days'][0].date());pp['end']=str((pp['days'][-1]+pd.Timedelta(days=1)).date());thirds.append(chosen_stats(pp,cid))
        rows[name]['thirds']=thirds
        half=oos['days'][len(oos['days'])//2];rows[name]['recent_half']=chosen_stats(panel(f,str(half.date()),PROTO['end_exclusive']),cid)
        daily=oos['net'][:,cid];rows[name]['dsr']=dsr(daily,lock['dev_trials_sr_std']);finite=daily[np.isfinite(daily)];q=np.quantile(finite,.05);rows[name]['daily_es95_pct']=float(-finite[finite<=q].mean()/100)
    isf=source('IS');allf=pd.concat([isf,f]);whole=panel(allf,PROTO['history_start'],PROTO['end_exclusive'])
    for name,cid in [('original',ORIGINAL),('candidate',i)]:
        rows[name]['full_history']=chosen_stats(whole,cid)
        for y in range(2020,2027):
            a=f'{y}-01-01';z=min(f'{y+1}-01-01',PROTO['end_exclusive']);rows[name]['yearly'].append(chosen_stats(panel(allf,a,z),cid))
        rows[name]['windows']={}
        for yrs in [3,5]:
            a=str((pd.Timestamp(PROTO['end_exclusive'])-pd.DateOffset(years=yrs)).date());rows[name]['windows'][str(yrs)+'y']=chosen_stats(panel(allf,a,PROTO['end_exclusive']),cid)
        rows[name]['full_trades']=records(allf,CONFIGS[cid],PROTO['history_start'],PROTO['end_exclusive'])
    raw=np.load(R/'DEVELOPMENT-MATRIX.npz',allow_pickle=False);status('Measuring 8500-search overfitting and joint fake-market significance')
    pb=pbo(raw['net']);save('PBO.json',pb);fake=joint_fake(raw['gross'],raw['cost'],pd.to_datetime(raw['dates']),[ORIGINAL,i]);save('FAKE-MARKETS.json',fake)
    rows['candidate']['development_dsr']=dsr(raw['net'][:,i],lock['dev_trials_sr_std'])
    rows['original']['development_dsr']=dsr(raw['net'][:,ORIGINAL],lock['dev_trials_sr_std'])
    devneighbors=neighbors(CONFIGS[i]);on=[dict(id=j,parameters=CONFIGS[j],metrics=chosen_stats(oos,j)) for j in devneighbors]
    base=rows['candidate']['oos'];boot=rows['candidate']['bootstrap'][1];stress=rows['candidate']['costs'][1]
    gates=dict(development_validation_preferred=not lock['exploratory'],minimum_30_oos_trades=base['trades']>=30,oos_pf_above_1=(base['profit_factor'] or 0)>1,oos_return_positive=base['return_pct']>0,
               bootstrap_profit_95pct=boot.get('probability_profit_pct',0)>=95,bootstrap_return_p05_positive=boot.get('return_p05_pct',-1)>0,bootstrap_pf_p05_above_1=boot.get('pf_p05',0)>1,
               deflated_sharpe_95pct=rows['candidate']['development_dsr']['dsr_pct']>=95,recent_half_pf_above_1=(rows['candidate']['recent_half']['profit_factor'] or 0)>1,two_of_three_oos_thirds_profitable=sum(r['net_usd']>0 for r in rows['candidate']['thirds'])>=2,
               oos_assumed_cost_stress_pf_above_1=(stress['profit_factor'] or 0)>1,family_maximum_fake_market_p_le_05=fake['candidates'][str(i)]['family_max_p']<=.05,pbo_below_50pct=pb['pbo_pct']<50,oos_profitable_neighbor_share_ge_60pct=np.mean([r['metrics']['net_usd']>0 for r in on])>=.6,
               closed_total_breach_under_5pct=boot.get('closed_total_10pct_breach_pct',100)<5,native_equity_path=False,measured_extra_slippage=False)
    result=dict(created_utc=utcnow(),split=load_json('data-split.json'),final_candidate=lock,variants=rows,holdout_shortlist_diagnostic=diagnostic,holdout_shortlist_profitable=sum(r['metrics']['net_usd']>0 for r in diagnostic),oos_neighbors=on,pbo_pct=pb['pbo_pct'],fake_market_summary={k:v for k,v in fake.items() if k!='family_maximum'},gates=gates,verdict='RESEARCH_ONLY_NOT_VALIDATED',limitations=PROTO['provenance'])
    save('RESULTS.json',result);status('Statistical pipeline complete; preparing isolated native replay and final audit')
    print(json.dumps(safe(dict(label=lock['label'],candidate=rows['candidate']['oos'],original=rows['original']['oos'],gates=gates)),indent=2),flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['select','final']);args=a.parse_args();select() if args.stage=='select' else final()
