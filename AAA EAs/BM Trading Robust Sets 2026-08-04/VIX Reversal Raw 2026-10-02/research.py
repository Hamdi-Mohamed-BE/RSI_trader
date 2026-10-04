"""Frozen daily VIX/SVXY screen. Never connects to a trading terminal."""
from pathlib import Path
import hashlib, json, math, urllib.request
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
END=pd.Timestamp('2026-10-02')
WINDOWS={'5y':'2021-10-02','3y':'2023-10-02','1y':'2025-10-02','6m':'2026-04-02',
         **{f'annual-{y}':f'{y}-10-02' for y in range(2021,2026)}}

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False,default=str),encoding='utf-8')

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def atr_wilder(h,l,c,n=14):
    prev=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-prev),abs(l-prev)))
    a=np.full(len(c),np.nan)
    if len(c)>=n:
        a[n-1]=tr[:n].mean()
        for i in range(n,len(c)): a[i]=(a[i-1]*(n-1)+tr[i])/n
    return a

def load():
    vp=ROOT/'data/VIX_History_Cboe.csv'
    if not vp.exists():
        request=urllib.request.Request('https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',headers={'User-Agent':'CalyxResearch/1.0'})
        with urllib.request.urlopen(request,timeout=30) as response: vp.write_bytes(response.read())
    ep=ROOT/'data/us_stock/SVXY_2020-01-01_to_2026-10-02.csv'
    yp=ROOT/'data/vix/INDEX_VIX_2020-01-01_to_2026-10-02.csv'
    v=pd.read_csv(vp); v.columns=v.columns.str.lower();v['date']=pd.to_datetime(v.date,format='%m/%d/%Y')
    v=v.set_index('date').sort_index().loc['2020-01-01':].add_prefix('v_')
    e=pd.read_csv(ep,parse_dates=['date']).set_index('date').sort_index()
    y=pd.read_csv(yp,parse_dates=['date']).set_index('date').sort_index()
    missing={}
    for name,frame,cols in [('ETF',e,['open','high','low','close','adj_close']),('Cboe',v,['v_open','v_high','v_low','v_close']),('connector_VIX',y,['open','high','low','close'])]:
        assert frame.index.is_unique, name+' duplicate dates'
        null=frame[cols].isna(); assert not (null.any(axis=1)&~null.all(axis=1)).any(),name+' partially missing OHLC'
        missing[name]=[str(x.date()) for x in frame.index[null.all(axis=1)]]
        frame.drop(frame.index[null.all(axis=1)],inplace=True)
        assert (frame[cols]>0).all().all()
        h=cols[1];l=cols[2];o=cols[0];c=cols[3]
        assert (frame[h]>=frame[[o,l,c]].max(axis=1)-1e-5).all()
        assert (frame[l]<=frame[[o,h,c]].min(axis=1)+1e-5).all()
    e=e[e.index<END];v=v[v.index<END];y=y[y.index<END]
    assert e.index.max()==END-pd.Timedelta(days=1),'ETF incomplete final session'
    assert v.index.max()==END-pd.Timedelta(days=1),'VIX incomplete final session'
    d=e.join(v,how='inner')
    # SVXY total-return factor must be constant in the test; do not lose dividends silently.
    f=d.adj_close/d.close
    assert np.max(abs(f.loc['2021-09-01':]-1))<1e-5,'ETF has actions/dividends needing explicit implementation'
    d['atr']=atr_wilder(d.high.to_numpy(),d.low.to_numpy(),d.close.to_numpy())
    d['v_mean']=d.v_close.shift(1).rolling(20,min_periods=20).mean()
    d['spike']=(d.v_close>=25)&(d.v_close>=1.25*d.v_mean)
    compare=v.join(y.close.rename('connector_close'),how='inner')
    compare['close_delta']=compare.v_close-compare.connector_close
    compare.to_csv(ROOT/'data/VIX-close-source-comparison.csv')
    manifest={'files':{str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in [vp,ep,yp]},
      'signal_source':'Cboe official VIX OHLC','execution_source':'market-data connector SVXY daily OHLC',
      'rows_joined':len(d),'first_joined':str(d.index.min().date()),'last_joined':str(d.index.max().date()),
      'missing_ohlc_rows_removed':missing,'ETF_dates_missing_VIX':[str(x.date()) for x in e.index.difference(v.index)],
      'VIX_dates_without_ETF':[str(x.date()) for x in v.index.difference(e.index)],
      'connector_VIX_vs_Cboe_close_max_abs_delta':float(compare.close_delta.abs().max()),
      'connector_VIX_vs_Cboe_close_over_0_02_count':int((compare.close_delta.abs()>0.02).sum()),
      'svxy_adjustment_factor_max_delta_from_1_test_window':float(np.max(abs(f.loc['2021-09-01':]-1))),
      'protocol_sha256':digest(ROOT/'PROTOCOL.txt'),'script_sha256':digest(Path(__file__))}
    d.to_csv(ROOT/'data/joined.csv');save(ROOT/'DATA LOCK.json',manifest)
    return d

def signal_rows(d):
    armed=None;out=[]
    for i in range(len(d)):
        x=d.iloc[i];prev=d.iloc[i-1] if i else None
        confirm=armed is not None and 1<=i-armed<=5 and x.v_close<prev.v_low and x.v_close<prev.v_close
        out.append({'signal':bool(confirm),'armed_at':armed if confirm else None,'frozen_mean':float(x.v_mean) if confirm else None})
        if confirm: armed=None
        if armed is not None and i-armed>=5: armed=None
        if x.spike and (i==0 or not prev.spike): armed=i
    return out

def bracket(open_,high,low,stop,target):
    if open_<=stop: return float(open_),'gap_stop',False
    if open_>=target: return float(target),'gap_target',False
    both=low<=stop and high>=target
    if low<=stop: return float(stop),'stop',both
    if high>=target: return float(target),'target',both
    return None,None,False

def streaks(p):
    runs={'win':[],'loss':[]};kind=None;n=0
    for x in p:
        k='win' if x>1e-8 else 'loss' if x<-1e-8 else None
        if k==kind and k is not None: n+=1
        else:
            if kind is not None:runs[kind].append(n)
            kind=k;n=1 if k else 0
    if kind is not None:runs[kind].append(n)
    return {f'{prefix}_{k}_streak':float(max(a)) if prefix=='max' and a else float(np.mean(a)) if a else 0. for k,a in runs.items() for prefix in ['max','average']}

def simulate(d,start,end=END,bps=0,signals=None,schedule=None,fast=False):
    """OHLC path convention low-before-high; next-open causal signals."""
    s=signal_rows(d) if signals is None else signals
    records=list(d.itertuples())
    ids=np.flatnonzero((d.index>=pd.Timestamp(start))&(d.index<pd.Timestamp(end)))
    assert len(ids)>0
    cash=10000.;pos=None;pending=None;trades=[];eq=[];ambiguous=skipped=gap_losses=0
    peak=10000.;dd_intraday=0.;fee=bps/10000
    def mark(value):
        nonlocal peak,dd_intraday
        peak=max(peak,value);dd_intraday=max(dd_intraday,(peak-value)/peak*100)
    for i in ids:
        date=d.index[i];x=records[i]
        closed_today=False
        if pos:
            # Scheduled exits are known from yesterday's completed close, not today's high/low.
            exit_price,reason,both=bracket(x.open,x.open,x.open,pos['stop'],pos['target'])
            if reason is None and pending:exit_price=float(x.open);reason=pending
            if reason is None:exit_price,reason,both=bracket(x.open,x.high,x.low,pos['stop'],pos['target'])
            ambiguous+=int(both)
            mark(cash+pos['qty']*x.open)
            if reason in ['stop','gap_stop','gap_target','time','vix_mean']:
                mark(cash+pos['qty']*exit_price*(1-fee))
            elif reason:
                mark(cash+pos['qty']*min(x.low,exit_price))
                mark(cash+pos['qty']*exit_price*(1-fee))
            else:
                mark(cash+pos['qty']*x.low);mark(cash+pos['qty']*x.high)
            if reason:
                cash+=pos['qty']*exit_price*(1-fee)
                t=pos|{'exit_date':str(date.date()),'exit_index':int(i),'exit_price':exit_price,'exit_reason':reason,'exit_fee':pos['qty']*exit_price*fee,'net_profit':cash-pos['balance_before'],'balance_after':cash,'held_sessions':int(i-pos['entry_index']+1),'boundary_exit':False}
                gap_losses+=int(t['net_profit']<-pos['requested_risk']-1e-7)
                trades.append(t);pos=None;pending=None;closed_today=True
        enter=False;horizon=10
        if not pos and not closed_today and i>0:
            if schedule is not None:
                enter=i in schedule
                if enter:horizon=max(0,int(schedule[i])-1)
            else:enter=s[i-1]['signal'] and i-1>=ids[0]
        if enter:
            before=cash;risk=before*.01;dist=2*records[i-1].atr
            if np.isfinite(dist) and dist>0:
                qty=int(min(math.floor(risk/dist+1e-10),math.floor(cash/(x.open*(1+fee))+1e-10)))
            else:qty=0
            if qty<1:skipped+=1
            else:
                entry=float(x.open);cash-=qty*entry*(1+fee)
                pos={'entry_date':str(date.date()),'entry_index':int(i),'signal_date':str(d.index[i-1].date()),'entry_price':entry,'qty':qty,'requested_risk':risk,'initial_risk':qty*dist,'stop_distance':float(dist),'stop':entry-dist,'target':entry+2*dist,'balance_before':before,'entry_fee':qty*entry*fee,'frozen_mean':float(records[i-1].v_mean),'horizon':horizon,'mode':'random' if schedule is not None else 'signal'}
                assert cash>=-1e-7 and pos['initial_risk']<=risk+1e-7
                mark(cash+qty*entry)
                exit_price,reason,both=bracket(x.open,x.high,x.low,pos['stop'],pos['target'])
                ambiguous+=int(both)
                if reason=='stop':mark(cash+qty*exit_price*(1-fee))
                elif reason:mark(cash+qty*min(x.low,exit_price));mark(cash+qty*exit_price*(1-fee))
                else:mark(cash+qty*x.low);mark(cash+qty*x.high)
                if reason:
                    cash+=qty*exit_price*(1-fee)
                    trades.append(pos|{'exit_date':str(date.date()),'exit_index':int(i),'exit_price':exit_price,'exit_reason':reason,'exit_fee':qty*exit_price*fee,'net_profit':cash-before,'balance_after':cash,'held_sessions':1,'boundary_exit':False})
                    pos=None
        # Control horizon includes the exit session, as baseline held_sessions does.
        # A one-session control closes at its close unless a bracket already fired.
        if pos and schedule is not None and pos['horizon']==0:
            price=float(x.close);cash+=pos['qty']*price*(1-fee)
            trades.append(pos|{'exit_date':str(date.date()),'exit_index':int(i),'exit_price':price,'exit_reason':'matched_time_close','exit_fee':pos['qty']*price*fee,'net_profit':cash-pos['balance_before'],'balance_after':cash,'held_sessions':1,'boundary_exit':False})
            pos=None
        if pos:
            if i-pos['entry_index']+1>=pos['horizon']:pending='time'
            elif schedule is None and x.v_close<=pos['frozen_mean']:pending='vix_mean'
        equity=cash+(pos['qty']*x.close if pos else 0);mark(equity)
        eq.append({'date':str(date.date()),'equity':float(equity),'cash':float(cash),'qty':pos['qty'] if pos else 0,'vix':float(x.v_close),'svxy':float(x.close)})
    e=np.array([r['equity'] for r in eq]);p=np.array([t['net_profit'] for t in trades]);gp=p[p>0].sum();gl=-p[p<0].sum()
    close_peak=np.maximum.accumulate(np.r_[10000,e])[1:];daily=np.r_[e[0]/10000-1,e[1:]/e[:-1]-1]
    duration=(pd.Timestamp(end)-pd.Timestamp(start)).days/365.2425
    stats={'start':str(pd.Timestamp(start).date()),'end_exclusive':str(pd.Timestamp(end).date()),'return_pct':float(100*(e[-1]/10000-1)),'final_equity':float(e[-1]),'net_profit_closed':float(p.sum()),'pf':float(gp/gl) if gl>0 else None,'win_rate_pct':float(100*(p>1e-8).mean()) if len(p) else None,'trades':len(p),'trades_per_month':float(len(p)/(duration*12)),'trades_per_session':float(len(p)/len(ids)),'sessions':len(ids),'max_close_equity_dd_pct':float(np.max(100*(close_peak-e)/close_peak)),'assumed_path_intraday_dd_pct':float(dd_intraday),'sharpe_daily_252':float(np.mean(daily)/np.std(daily,ddof=1)*np.sqrt(252)) if np.std(daily,ddof=1)>0 else None,'ambiguous_both_touch_days':ambiguous,'risk_budget_exceeded_losses':gap_losses,'skipped_sizing':skipped,'final_open_position':pos,'execution_bps_each_side':bps,'exposure_pct':float(np.mean([x['qty']>0 for x in eq])*100),**streaks(p)}
    if not fast:
        assert abs(10000+p.sum()+(e[-1]-cash-(pos['balance_before']-cash) if pos else 0)-e[-1])<1e-6
        assert all(t['signal_date']<t['entry_date'] for t in trades)
    return stats,pd.DataFrame(eq),pd.DataFrame(trades)

def random_control(d,start,end,baseline,count=1000):
    rng=np.random.default_rng(20261002);ids=np.flatnonzero((d.index>=pd.Timestamp(start))&(d.index<pd.Timestamp(end)))
    entries=baseline.entry_index.to_numpy(dtype=int);horizons=baseline.held_sessions.to_numpy(dtype=int)
    observed_weekdays=[d.index[i].weekday() for i in entries]
    out=[];signals=signal_rows(d);attempts=0
    # Cached weekday pools avoid repeatedly recomputing calendar properties.
    pools={(w,int(n)):[int(i) for i in ids if i+int(n)-1<=ids[-1] and d.index[i].weekday()==w] for w,n in zip(observed_weekdays,horizons)}
    while len(out)<count and attempts<count*30:
        attempts+=1;busy=set();schedule={};valid=True
        for j in rng.permutation(len(entries)):
            n=int(horizons[j]);w=observed_weekdays[j]
            possible=[i for i in pools[(w,n)] if not any(k in busy for k in range(i-1,i+n+1))]
            if not possible:valid=False;break
            i=int(rng.choice(possible));schedule[i]=n;busy.update(range(i,i+n+1))
        if not valid:continue
        st,_,tr=simulate(d,start,end,signals=signals,schedule=schedule,fast=True)
        if len(tr)!=len(baseline):continue
        assert (tr.held_sessions.to_numpy()<=np.array([schedule[int(i)] for i in tr.entry_index])).all()
        out.append({'return_pct':st['return_pct'],'pf':st['pf'],'win_rate_pct':st['win_rate_pct'],'trades':st['trades'],'close_dd_pct':st['max_close_equity_dd_pct']})
    assert len(out)==count,'Could not build requested exact-trade-count controls'
    a=pd.DataFrame(out)
    return {'paths':count,'attempts':attempts,'matching':'closed count, entry weekday mix, allocated held-session horizons; risk/ATR/brackets','random_return_p05':float(a.return_pct.quantile(.05)),'random_return_median':float(a.return_pct.median()),'random_return_p95':float(a.return_pct.quantile(.95))},a

def bootstrap(trades,count=10000):
    r=trades.net_profit.to_numpy()/trades.requested_risk.to_numpy();n=len(r)
    rng=np.random.default_rng(20261002);starts=rng.integers(n,size=(count,int(np.ceil(n/5))))
    idx=((starts[:,:,None]+np.arange(5))%n).reshape(count,-1)[:,:n];z=r[idx]
    returns=(np.prod(1+.01*z,axis=1)-1)*100;loss=(-np.minimum(z,0)).sum(axis=1);profit=np.maximum(z,0).sum(axis=1)
    pf=np.divide(profit,loss,out=np.full(count,np.inf),where=loss>0)
    return {'paths':count,'block':5,'return_p05_pct':float(np.quantile(returns,.05)),'return_median_pct':float(np.median(returns)),'return_p95_pct':float(np.quantile(returns,.95)),'pf_p05':float(np.quantile(pf,.05)),'historical_resample_positive_pct':float(np.mean(returns>0)*100),'warning':'Historical risk-unit diagnostic only; not future success probability, integer-share/gap states not regenerated.'}

def main():
    d=load();s=signal_rows(d);rows=[];controls={};boot={}
    for label,start in WINDOWS.items():
        end=pd.Timestamp(f'{int(start[:4])+1}-10-02') if label.startswith('annual') else END
        for bps in ([0,5,10] if label in ['5y','3y','1y','6m'] else [0]):
            key=f'{label}-gross' if bps==0 else f'{label}-illustrative-{bps}bps'
            st,eq,tr=simulate(d,start,end,bps,signals=s);st.update(key=key,window=label)
            folder=ROOT/'runs'/key;folder.mkdir(parents=True,exist_ok=True)
            eq.to_csv(folder/'equity.csv',index=False);tr.to_csv(folder/'trades.csv',index=False);save(folder/'stats.json',st);rows.append(st)
            if bps==0 and label in ['3y','5y']:
                c,a=random_control(d,start,end,tr);c['observed_return_pct']=st['return_pct'];c['observed_above_random_p95']=st['return_pct']>c['random_return_p95'];c['random_ge_observed_fraction_plus_one']=(int((a.return_pct>=st['return_pct']).sum())+1)/(len(a)+1)
                controls[label]=c;a.to_csv(ROOT/f'CONTROL-{label}.csv',index=False)
                boot[label]=bootstrap(tr)
        print(label+' completed',flush=True)
    save(ROOT/'SUMMARY.json',rows);save(ROOT/'CONTROLS.json',controls);save(ROOT/'BOOTSTRAP.json',boot)
    gates={}
    for label in ['3y','5y']:
        st=next(x for x in rows if x['key']==label+'-gross')
        gates[label]={'positive':st['return_pct']>0,'PF_at_least_1_15':st['pf'] is not None and st['pf']>=1.15,'at_least_30_trades':st['trades']>=30,'beats_matched_control_p95':controls[label]['observed_above_random_p95']}
    passed=all(all(g.values()) for g in gates.values())
    save(ROOT/'DECISION.json',{'status':'RAW SCREEN PASS ONLY' if passed else 'RAW GATE FAILED','gates':gates,'promotion_allowed':False,'native_MT5_test':False,'measured_incremental_cost_gate_satisfied':False,'prospective_holdout':False,'optimisation_started':False,'active_eas_changed':False,'configurations_tested':1,'cost_sensitivity_scenarios':2,'stop_reason':'Daily ETF screen cannot satisfy native executable tick data and measured-cost gates; stop for review.' if passed else 'Frozen raw gate failure; do not optimise.'})
    print(json.dumps({'baseline':[x for x in rows if x['key'].endswith('gross')],'controls':controls,'bootstrap':boot},indent=2),flush=True)

if __name__=='__main__':main()
