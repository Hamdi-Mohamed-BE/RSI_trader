"""Offline statistical overlays. No MT5 imports or order interface."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, math, sys, time
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import fisher_exact
from numba import njit
import prop_engine as pe
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'FTMO vs Stellar Instant Study 2026-09-28'
CFG=json.loads((ROOT/'run-config.json').read_text())
NAMES=CFG['risk_overlays']
def save(name,obj): (ROOT/name).write_text(json.dumps(pe.clean(obj),indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(s):return int(pd.Timestamp(s,tz='UTC').timestamp())

@njit(cache=True)
def variance_path(e,p):
    w,a,b=p;v=max(np.var(e),1e-8);cost=0.
    for x in e:
        cost+=math.log(v)+x*x/v
        v=w+a*x*x+b*v
    return cost/len(e),v

def garch_forecasts(frame):
    """At bar i's OPEN use closes through i-1 only; refit monthly."""
    times=frame['time'].to_numpy(np.int64);cl=frame['close'].to_numpy(float)
    y=np.diff(np.log(cl))*100;result=[];fits=[];past=[];month=None;params=None;mu=0.;v=0.
    for i in range(253,len(cl)):
        date=datetime.fromtimestamp(int(times[i]),timezone.utc);key=(date.year,date.month)
        if key!=month:
            hist=y[max(0,i-1-756):i-1];mu=float(np.mean(hist));e=hist-mu;vr=max(float(np.var(e)),1e-6)
            sol=minimize(lambda p:variance_path(e,p)[0],np.array([vr*.1,.1,.8]),method='SLSQP',
                bounds=[(1e-9,max(1.,vr*10)),(0.,.998),(0.,.998)],constraints=[{'type':'ineq','fun':lambda p:.999-p[1]-p[2]}],
                options={'maxiter':300,'ftol':1e-10})
            if not sol.success or not np.isfinite(sol.fun) or sum(sol.x[1:])>.9990001:
                # No fitted signal on failure; do not silently use future/full-sample parameters.
                fits.append(dict(time=int(times[i]),ok=False,message=str(sol.message)));params=None;month=key
            else:
                params=sol.x.copy();v=float(variance_path(e,params)[1]);month=key
                fits.append(dict(time=int(times[i]),ok=True,history=len(hist),last_known_close_bar=int(times[i-1]),
                                 omega=params[0],alpha=params[1],beta=params[2],mean=mu))
        elif params is not None:
            v=params[0]+params[1]*(y[i-2]-mu)**2+params[2]*v
        if params is None:
            result.append([int(times[i]),np.nan,1.,-1]);continue
        vol=math.sqrt(max(v,1e-10));cap=1.;bucket=-1
        if len(past)>=60:
            sample=np.array(past[-756:]);cap=float(np.clip(np.median(sample)/vol,.5,1.))
            bucket=int(np.searchsorted(np.quantile(sample,[.25,.5,.9]),vol,side='right'))
        result.append([int(times[i]),vol,cap,bucket]);past.append(vol)
    return np.array(result,dtype=float),fits

def prepare_garch():
    arrays={};audit={}
    for sym in ['XAUUSD','USTEC','USDJPY']:
        path=ROOT/'data'/f'{sym}-D1.csv.gz';f=pd.read_csv(path)
        assert (np.diff(f.time)>0).all() and (f.close>0).all()
        ar,fits=garch_forecasts(f);arrays[sym]=ar
        # Calibration is diagnostic only, not used to select thresholds.
        returns=dict(zip(f.time.to_numpy()[1:],np.diff(np.log(f.close))*100))
        calibration=[]
        for b in range(4):
            a=ar[ar[:,3]==b];vals=[returns[int(x[0])]**2 for x in a if int(x[0]) in returns]
            calibration.append(dict(bucket=b,days=len(vals),mean_predicted_var=float(np.mean(a[:,1]**2)) if len(a) else None,
                                    mean_realized_squared_return=float(np.mean(vals)) if vals else None))
        audit[sym]=dict(rows=len(f),first=int(f.time.iloc[0]),last=int(f.time.iloc[-1]),sha256=sha(path),fits=fits,calibration=calibration)
        print('GARCH',sym,'days',len(f),'forecasts',len(ar),'fit failures',sum(not x['ok'] for x in fits),flush=True)
    np.savez_compressed(ROOT/'garch.npz',**arrays);save('GARCH_AUDIT.json',audit)
    return arrays

def r_values(tr):return (tr[:,6]+tr[:,7]+tr[:,8])/tr[:,4]
def feature_table(tr,forecasts,base_risk):
    """Shadow outcomes are observable only strictly before entry minute."""
    out=np.ones((len(tr),len(NAMES)));details=[];hist=[[] for _ in range(13)];pending=sorted(range(len(tr)),key=lambda i:(tr[i,1],i));q=0
    rv=r_values(tr)
    for i,t in enumerate(tr):
        while q<len(pending) and tr[pending[q],1]<t[0]:
            k=pending[q];ea=int(tr[k,2]);seq=hist[ea];previous=seq[-1][0] if seq else 0.
            streak=0
            for x in reversed(seq):
                if x[0]>=0:break
                streak+=1
            seq.append((float(rv[k]),int(np.sign(previous)),streak));q+=1
        seq=hist[int(t[2])];last=int(np.sign(seq[-1][0])) if seq else 0
        streak=0
        for x in reversed(seq):
            if x[0]>=0:break
            streak+=1
        out[i,1]=.5 if last<0 else 1.
        state=np.array([x[0] for x in seq[1:] if x[1]==last])
        trained=len(seq)>=100 and len(state)>=30 and (state>0).any() and (state<0).any()
        kelly=None
        if trained:
            unconditional=np.mean([x[0]>0 for x in seq]);p=(sum(state>0)+20*unconditional)/(len(state)+20)
            b=float(np.mean(state[state>0])/-np.mean(state[state<0]));kelly=float(p-(1-p)/b)
            out[i,2]=float(np.clip(.25*max(0.,kelly)/base_risk,.5,1.25))
        sym=['XAUUSD','USTEC','USDJPY'][int(t[3])];ar=forecasts[sym];pos=np.searchsorted(ar[:,0],t[0]*60,side='right')-1
        bucket=-1
        if pos>=0:
            out[i,3]=ar[pos,2];bucket=int(ar[pos,3])
        out[i,4]=out[i,2]*out[i,3]
        state7=np.array([x[0] for x in seq if x[2]>=7]);lcb=None
        if len(state7)>=30:
            lcb=float(np.mean(state7)-1.645*np.std(state7,ddof=1)/np.sqrt(len(state7)))
            if streak>=7 and lcb>0:out[i,5]=1.25
        details.append(dict(row=i,ea=int(t[2]),prior_closed=len(seq),last=last,streak=streak,state_n=len(state),kelly_trained=trained,
                            kelly=kelly,streak7_n=len(state7),streak7_lcb=lcb,bucket=bucket,multipliers=out[i].tolist()))
    return out,details

def stats(v,days):
    v=np.array(v,float);pos=v[v>0];neg=v[v<0];equity=np.r_[0.,np.cumsum(v)];draw=np.maximum.accumulate(equity)-equity
    mw=ml=w=l=0
    for x in v:
        w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
    gross=float(sum(pos));loss=-float(sum(neg))
    return dict(trades=len(v),trades_month=len(v)/max(days/30.4375,1e-9),trades_weekday=len(v)/max(days*5/7,1),net_r=float(sum(v)),
                expectancy=float(np.mean(v)) if len(v) else None,pf=gross/loss if loss else None,
                pf_without_best=(gross-max(pos))/loss if loss and len(pos) else None,win_rate=100*len(pos)/len(v) if len(v) else None,
                closed_cash_dd_r=float(max(draw)),max_win_streak=mw,max_loss_streak=ml)

def wilson(w,n):
    if not n:return None
    p=w/n;z=1.96;c=(p+z*z/(2*n))/(1+z*z/n);h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [c-h,c+h]

def diagnostics(tr,audit):
    ans=[]
    for ea,key in enumerate(audit['keys']):
        sub=tr[tr[:,2]==ea];sub=sub[np.argsort(sub[:,1],kind='stable')];v=r_values(sub);win=v>0;states=np.sign(v)
        # Zero/breakeven observations are not relabelled as losses.
        ll=sum((states[:-1]<0)&(states[1:]<0));lw=sum((states[:-1]<0)&(states[1:]>0));wl=sum((states[:-1]>0)&(states[1:]<0));ww=sum((states[:-1]>0)&(states[1:]>0))
        p=float(np.mean(win));pl=lw/(lw+ll) if lw+ll else None;pw=ww/(ww+wl) if ww+wl else None
        rho=float(np.corrcoef(win[:-1],win[1:])[0,1]) if len(win)>2 and np.std(win[:-1]) and np.std(win[1:]) else None
        pvalue=float(fisher_exact([[ll,lw],[wl,ww]])[1])
        ans.append(dict(key=key,**stats(v,(audit['end']-audit['start'])/86400),p_win=p,p_win_after_loss=pl,p_win_after_win=pw,
                        delta_percentage_points=100*(p-pl) if pl is not None else None,rho_lag1=rho,after_loss_n=int(ll+lw),after_win_n=int(wl+ww),
                        after_loss_ci=wilson(lw,lw+ll),after_win_ci=wilson(ww,ww+wl),fisher_p=pvalue))
    ordered=sorted(range(len(ans)),key=lambda j:ans[j]['fisher_p']);adj=0
    for rank,j in enumerate(ordered):adj=max(adj,min(1.,ans[j]['fisher_p']*(len(ans)-rank)));ans[j]['holm_p']=adj
    order=np.argsort(tr[:,1],kind='stable');chunks=[]
    for n,ids in enumerate(np.array_split(order,10)):
        days=max(1,(tr[ids,1].max()-tr[ids,0].min())/1440);chunks.append(dict(chunk=n+1,**stats(r_values(tr[ids]),days)))
    save('DIAGNOSTICS.json',dict(eas=ans,chunks=chunks,warning='Descriptive tests of a previously selected portfolio; no untouched validation and multiple dependencies.'))

def boot_difference(tr,mults,cut,end):
    # One common daily index for all overlays; zero-trade days retained.
    startday=cut//1440;nd=(end-cut)//1440;daily=np.zeros((nd,len(NAMES)));rv=r_values(tr)
    for i,t in enumerate(tr):
        d=int(t[1]//1440)-startday
        if 0<=d<nd and t[0]>=cut:daily[d]+=rv[i]*mults[i]
    rng=np.random.default_rng(CFG['seed']);block=28;idx=(rng.integers(0,nd,size=(10000,math.ceil(nd/block),1))+np.arange(block))%nd
    idx=idx.reshape(10000,-1)[:,:nd];diff=daily-daily[:,[0]];sums=diff[idx].sum(axis=1)
    result=[dict(model=name,observed_net_r_difference=float(diff[:,j].sum()),bootstrap_difference_p05=float(np.quantile(sums[:,j],.05)),
                 bootstrap_difference_p95=float(np.quantile(sums[:,j],.95))) for j,name in enumerate(NAMES)]
    return result

def shadow_accounting():
    # Interview's noncompounded illustration; inactive accounts do not take trades.
    weekly=np.array([-7.,3.,-4.,4.])/100;small=50000.;large=4*small
    gross=small*weekly;withdraw=np.maximum(gross,0);ending=large+sum(np.minimum(gross,0));cash=.8*sum(withdraw)
    save('SHIELD.json',dict(weeks_pct=weekly*100,quarter_account_size=small,single_size=large,
      four_gross_pnl=float(sum(gross)),four_residual_balance=float(ending),four_gross_withdrawal=float(sum(withdraw)),four_cash=float(cash),four_balance_plus_cash=float(ending+cash),
      single_same_percentage_risk_end=float(large*(1+sum(weekly))),single_equal_dollar_risk_end=float(large+sum(gross)),
      nominal_ledger_difference_after_split=float(ending+cash-large),trader_cash_before_fees=float(cash),
      warning='Prop balances are simulated buying capacity, not trader-owned cash. Balance plus payout is an accounting illustration, NOT investor wealth or an actual $2700 cash loss.',
      fee_formula='Actual trader cash P&L = $2800 minus all acquisition/reset/EA-addon fees and other paid costs. Compare single-account fees separately.',
      status='Counterfactual accounting, not an authorized account-rolling programme; no purchases, transfers or live rotation.'))

def main():
    z=np.load(SOURCE/'prepared.npz');tr=z['trades'].copy();pc=z['close'];pl=z['low'];audit=json.loads((SOURCE/'AUDIT.json').read_text());rows=json.loads((SOURCE/'rows.json').read_text())
    assert len(tr)==len(rows)==972
    # Avoid depending on pre-rounded source quick flags. Exact native timestamps available.
    for i,r in enumerate(rows):
        assert abs(tr[i,5]-r['open_price'])<1e-6 and int(tr[i,2])==audit['keys'].index(r['key'])
        tr[i,13]=float(r['cl']-r['op']<=30)
    save('INPUTS.json',dict(source_files={n:sha(SOURCE/n) for n in ['prepared.npz','rows.json','AUDIT.json']},protocol_sha256=sha(ROOT/'RULES.md'),config_sha256=sha(ROOT/'run-config.json'),
                           data_limitations=audit,source='Existing Exness native opportunity ledger, not a new execution backtest.'))
    forecasts=prepare_garch();diagnostics(tr,audit);shadow_accounting()
    begin=audit['start']//60;end=audit['end']//60;cut=stamp(CFG['overlay_validation_start'])//60;first=stamp(CFG['overlay_rolling_start'])//60
    clock=pe.clocks(begin,end);results=[]
    pe.HORIZONS=np.array(CFG['overlay_horizons'],np.int64)
    for firm,capital in [('FTMO',10000),('Instant',5000)]:
        risk=CFG['overlay_base_risks'][firm];m,detail=feature_table(tr,forecasts,risk);save(f'FEATURES-{firm}.json',detail)
        save(f'BOOTSTRAP-{firm}.json',boot_difference(tr,m,cut,end))
        for j,name in enumerate(NAMES):
            tt=np.column_stack([tr,m[:,j]])
            cfg=dict(name=name,firm=firm,capital=capital,risk=risk,core=False,existing=False,withdraw_all=False)
            for stress in [False,True]:
                paths=[]
                for start in range(first,end-30*1440+1,7*1440):
                    en=min(start+180*1440,end)
                    r=pe.invoke(tt,pc,pl,start,en,clock[start-begin:en-begin+1],cfg,stress,horizons=pe.HORIZONS)
                    paths.append(dict(start=start,snapshots=r[0]))
                historical={}
                for label,start in [('full',begin),('validation',cut)]:
                    days=(end-start)//1440
                    r=pe.invoke(tt,pc,pl,start,end,clock[start-begin:],cfg,stress,lifecycle=False,horizons=np.array([days],np.int64))
                    historical[label]=dict(snapshot=dict(zip(pe.FIELDS,r[0][0])),accepted=r[1],rejected=r[2],trades=r[3])
                result=dict(firm=firm,model=name,stress=stress,rolling=pe.summarize([p['snapshots'] for p in paths]),paths=paths,historical=historical)
                results.append(result);save('OVERLAYS.json',results)
                print(json.dumps(dict(firm=firm,model=name,stress=stress,rolling=[{k:r[k] for k in ['days','starts','payout','breach_before','breach_after','compliance_blocked','mean_cash']} for r in result['rolling']])),flush=True)
    save('COMPLETE.json',dict(overlay_cases=len(results),rows=len(tr),code_sha256={n:sha(ROOT/n) for n in ['study.py','prop_engine.py']},completed_utc=datetime.now(timezone.utc).isoformat()))

if __name__=='__main__':main()
