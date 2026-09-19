"""Read-only broker cache and independently calculated closed-bar indicators."""
import json,hashlib
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from numba import njit
from params import ROOT,RAW,SPACE,DEFAULT,save

@njit(cache=True)
def ema(x,p):
    a=np.empty(len(x));a[0]=x[0];alpha=2./(p+1)
    for i in range(1,len(x)):a[i]=a[i-1]+alpha*(x[i]-a[i-1])
    return a

@njit(cache=True)
def indicators(h,p):
    n=len(h);tr=np.zeros(n);pos=np.zeros(n);neg=np.zeros(n);up=0.;down=0.;rsi=np.zeros(n)
    for i in range(1,n):
        tr[i]=max(h[i,2]-h[i,3],abs(h[i,2]-h[i-1,4]),abs(h[i,3]-h[i-1,4]))
        u=max(0.,h[i,2]-h[i-1,2]);d=max(0.,h[i-1,3]-h[i,3])
        if tr[i]>0:
            if u>d:pos[i]=100*u/tr[i]
            elif d>u:neg[i]=100*d/tr[i]
        delta=h[i,4]-h[i-1,4]
        if i<=p:
            up+=max(0.,delta)/p;down+=max(0.,-delta)/p
        else:
            up=(up*(p-1)+max(0.,delta))/p;down=(down*(p-1)+max(0.,-delta))/p
        rsi[i]=100-100/(1+up/down) if down>0 else (100. if up>0 else 50.)
    pd=ema(pos,p);nd=ema(neg,p);dx=np.zeros(n);atr=np.zeros(n);total=0.
    for i in range(n):
        if pd[i]+nd[i]>0:dx[i]=100*abs(pd[i]-nd[i])/(pd[i]+nd[i])
        total+=tr[i]
        if i>=p:total-=tr[i-p];atr[i]=total/p
    return atr,ema(dx,p),pd,nd,rsi,tr

def cache():
    folder=ROOT.parent/'3 way gold Full Optimization 2026-09-13'/'Data';folder.mkdir(exist_ok=True)
    if (folder/'prices.npz').exists():return
    import MetaTrader5 as mt
    assert mt.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe')
    a=mt.account_info();s=mt.symbol_info('XAUUSD')
    assert a.server=='Exness-MT5Trial16' and a.login==472334559 and s.path.startswith('Zero\\')
    arrays={}
    for name,tf in [('h1',mt.TIMEFRAME_H1),('m1',mt.TIMEFRAME_M1)]:
        chunks=[]
        for year in range(2018,2027):
            end=datetime(year+1,1,1,tzinfo=timezone.utc) if year<2026 else datetime(2026,9,5,tzinfo=timezone.utc)
            b=mt.copy_rates_range('XAUUSD',tf,datetime(year,1,1,tzinfo=timezone.utc),end)
            assert b is not None and len(b)>100,(name,year,mt.last_error())
            chunks.append(b);print('CACHE',name,year,len(b),flush=True)
        b=np.concatenate(chunks);_,idx=np.unique(b['time'],return_index=True);b=b[np.sort(idx)]
        b=b[b['time']<datetime(2026,9,5,tzinfo=timezone.utc).timestamp()]
        arrays[name]=np.column_stack([b[k] for k in ('time','open','high','low','close','spread')]).astype(np.float64)
    # Preserve actual broker minimum, contract and current swap snapshot, not credentials.
    save(folder/'provenance.json',dict(server=a.server,symbol='XAUUSD',path=s.path,contract=s.trade_contract_size,point=s.point,
        min_lot=s.volume_min,lot_step=s.volume_step,max_lot=s.volume_max,swap_long=s.swap_long,swap_short=s.swap_short,
        swap_mode=s.swap_mode,triple_day=s.swap_rollover3days,leverage=a.leverage,cache_date='2026-09-13',
        rows={k:len(v) for k,v in arrays.items()},utc_epoch=True))
    assert s.trade_contract_size==100 and s.volume_min==.01 and s.volume_step==.01
    np.savez(folder/'prices.npz',**arrays)
    save(folder/'hashes.json',{'prices.npz':hashlib.sha256((folder/'prices.npz').read_bytes()).hexdigest()})

def load():
    cache();d=np.load(ROOT.parent/'3 way gold Full Optimization 2026-09-13'/'Data'/'prices.npz');h=d['h1'];m=d['m1']
    h=np.column_stack((h,pd.to_datetime(h[:,0],unit='s').year.to_numpy()-2019))
    eperiods=sorted(set(sum([SPACE[k] for k in ('InpPullbackEMA','InpTrendFastEMA','InpTrendSlowEMA','InpChangeFastEMA','InpChangeSlowEMA')],[])))
    iperiods=sorted(set(SPACE['InpATRPeriod']+SPACE['InpADXPeriod']+SPACE['InpRSIPeriod']))
    es={p:ema(h[:,4],p) for p in eperiods};inds={p:indicators(h,p) for p in iperiods}
    hi={p:pd.Series(h[:,2]).rolling(p).max().shift(1).to_numpy() for p in SPACE['InpBreakoutBars']}
    lo={p:pd.Series(h[:,3]).rolling(p).min().shift(1).to_numpy() for p in SPACE['InpBreakoutBars']}
    starts=np.searchsorted(m[:,0],h[:,0]);ends=np.searchsorted(m[:,0],h[:,0]+3600)
    # Mark charged rollover minutes using 17:00 New York, Wed triple. Approximate screening only.
    roll=np.zeros(len(m));dt=datetime(2018,1,1);ny=ZoneInfo('America/New_York')
    while dt<datetime(2026,9,5):
        if dt.weekday()<5:
            epoch=dt.replace(hour=17,tzinfo=ny).timestamp();j=np.searchsorted(m[:,0],epoch)
            if j<len(m):roll[j]+=3 if dt.weekday()==2 else 1
        dt+=timedelta(days=1)
    return dict(h=h,m=m,ema=es,ind=inds,high=hi,low=lo,starts=starts,ends=ends,roll=roll)

def signals(d,c):
    h=d['h'];e=d['ema'];ind=d['ind'];n=len(h);out=np.zeros((n,3),dtype=np.int8);close=h[:,4]
    pb=e[c['InpPullbackEMA']];fast=e[c['InpTrendFastEMA']];slow=e[c['InpTrendSlowEMA']]
    atr=ind[c['InpATRPeriod']][0];_,adx,plus,minus,_,tr=ind[c['InpADXPeriod']]
    prev=lambda x:np.r_[x[0],x[:-1]]
    long=(fast>slow)&(close>fast)&(adx>=c['InpADXMin'])&(plus>minus)&(prev(close)<=prev(pb))&(close>pb)
    short=(fast<slow)&(close<fast)&(adx>=c['InpADXMin'])&(plus<minus)&(prev(close)>=prev(pb))&(close<pb)
    out[long,0]=1;out[short,0]=-1
    f=e[c['InpChangeFastEMA']];s=e[c['InpChangeSlowEMA']];rsi=ind[c['InpRSIPeriod']][4]
    out[(prev(f)<=prev(s))&(f>s)&(rsi>c['InpRSIThreshold']),1]=1
    out[(prev(f)>=prev(s))&(f<s)&(rsi<100-c['InpRSIThreshold']),1]=-1
    expanding=(tr>=c['InpExpansionATR']*prev(atr))&(prev(atr)>0)
    if c['InpRisingATR']:expanding &= atr>prev(atr)
    out[expanding&(close>d['high'][c['InpBreakoutBars']]),2]=1
    out[expanding&(close<d['low'][c['InpBreakoutBars']]),2]=-1
    if c['InpDirection']:out[out!=c['InpDirection']]=0
    if c['InpEngine']:
        for eng in range(3):
            if eng!=c['InpEngine']-1:out[:,eng]=0
    out[:1000]=0
    return out,atr

def verify_raw(d):
    rows=pd.read_csv(RAW/'Audit'/'5y-engine0-d1-decisions.csv');times=pd.to_datetime(rows.closed_bar).astype('datetime64[ns]').astype('int64').to_numpy()//10**9
    ix=np.searchsorted(d['h'][:,0],times);assert np.all(d['h'][ix,0]==times)
    expected,_=signals(d,DEFAULT);actual=rows[['momentum','change','breakout']].to_numpy()
    assert np.array_equal(expected[ix],actual),'Independent signal mismatch'
    checks={}
    for column,values in [('adx',d['ind'][14][1]),('plus',d['ind'][14][2]),('minus',d['ind'][14][3]),('rsi',d['ind'][14][4]),('atr1',d['ind'][14][0]),('e200',d['ema'][200])]:
        diff=float(np.max(np.abs(rows[column].to_numpy()-values[ix])));assert diff<.002,(column,diff);checks[column]=diff
    assert np.all(d['starts']<=d['ends'])
    # H1 and M1 must describe the same price feed. Missing hours fail closed.
    z=ix[(ix%100)==0];m=d['m'];h=d['h']
    for i in z:
        a,b=d['starts'][i],d['ends'][i];assert b>a
        assert abs(m[a,1]-h[i,1])<.002 and abs(m[b-1,4]-h[i,4])<.002
    save(ROOT.parent/'3 way gold Full Optimization 2026-09-13'/'Data'/'independent-verification.json',dict(decisions=len(rows),signal_exact=True,max_indicator_difference=checks,sampled_m1_h1_checks=len(z)))
    print('INDEPENDENT BROKER SIGNAL PARITY',len(rows),'decisions',flush=True)

if __name__=='__main__':
    d=load();verify_raw(d)
