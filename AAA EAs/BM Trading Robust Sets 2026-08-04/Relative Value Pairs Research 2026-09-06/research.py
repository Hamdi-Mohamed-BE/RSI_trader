"""Causal synchronized-bar screen. Results are NOT native tick backtests."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, itertools, json, math, time
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
PAIRS={'BTC-ETH':('BTCUSD','ETHUSD'),'XAU-XAG':('XAUUSD','XAGUSD')}
SESSIONS=['all_day','asia','london','new_york','overlap','london_or_new_york']
PERIODS={'train':('2023-09-01','2024-09-01'),'validation':('2024-09-01','2025-09-01'),'test':('2025-09-01','2026-09-01'),'full':('2023-09-01','2026-09-01')}
BASE=dict(tf=15,window=64,model=0,entry=2.,session=0,stop=0,exit=7,rr=1.,manage=0,direction=0,hold=24)
EXIT_NAMES=['fixed_RR']*7+['entry_mean','rolling_mean','time_only']
MANAGE_NAMES=['none','BE_0.5R','BE_1R','M15_0.5_to_0.2R','trail_0.5R','trail_1R','volatility_trail']

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def stamp(s): return pd.Timestamp(s,tz='UTC').timestamp()
def key(c): return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:12]

def load_pair(pair):
    meta=json.loads((ROOT/'Data'/'metadata.json').read_text())['symbols']
    symbols=PAIRS[pair]; frames=[]; costs=[]
    for sym in symbols:
        a=np.load(ROOT/'Data'/f'{sym}-M5.npz')['rates']
        d=pd.DataFrame(a).set_index('time');d.index=pd.to_datetime(d.index,unit='s',utc=True)
        train=d.loc['2023-06-01':'2024-08-31','spread'];floor=float(train[train>0].median())
        d['spread']=np.maximum(d['spread'],floor)*meta[sym]['point']
        frames.append(d)
        costs.append(dict(symbol=sym,zero_spread_floor_points=floor,commission_bps_per_side=1.,swap_source='current broker snapshot applied to history, not historical schedule'))
    # Inner join only. No forward-filled candles.
    d=frames[0].join(frames[1],lsuffix='_a',rsuffix='_b',how='inner').sort_index()
    d['ts']=d.index.as_unit('s').asi8
    utc=d.index;lon=utc.tz_convert('Europe/London');ny=utc.tz_convert('America/New_York')
    london=(lon.hour>=8)&(lon.hour<17);newyork=(ny.hour>=8)&(ny.hour<17)
    d['sessions']=1+((utc.hour<8).astype(int)<<1)+(london.astype(int)<<2)+(newyork.astype(int)<<3)+((london&newyork).astype(int)<<4)+((london|newyork).astype(int)<<5)
    d['roll_a']=0.;d['roll_b']=0.
    for i,sym in enumerate(symbols):
        # Rollover at UTC midnight. Triple day maps MQL Sunday=0 convention.
        day=utc.normalize();prev=day.to_series().shift(1).values
        changed=np.r_[False,(day[1:]!=day[:-1])]
        wd=(utc.dayofweek+1)%7
        mult=np.where(wd==meta[sym]['swap_rollover3days'],3.,1.)
        mult=np.where((wd==0)|(wd==6),0.,mult)
        d['roll_'+('a' if i==0 else 'b')]=changed*mult
    cols=['ts','open_a','open_b','close_a','close_b','spread_a','spread_b','sessions','roll_a','roll_b']
    market=d[cols].to_numpy(dtype=float)
    specs=np.array([[meta[s][f] for f in ('trade_contract_size','volume_min','volume_step','volume_max','swap_long','swap_short','point')] for s in symbols],dtype=float)
    dump(ROOT/'Data'/f'{pair}-quality.json',dict(synchronized_bars=len(d),unmatched_bars=[len(f)-len(d) for f in frames],start=str(d.index[0]),end=str(d.index[-1]),costs=costs,execution='M5 bid opens with historical spread floored at training positive median; 1bp per side per leg; M5 marked equity; broker lot rounding; no forward fill'))
    return d,market,specs

@njit(cache=True)
def feature_loop(closes,window,model):
    # Row i is an entry boundary. Fit excludes the last completed signal candle.
    n=len(closes);out=np.full((n,9),np.nan)
    for i in range(window+1,n):
        ya=np.log(closes[i-window-1:i-1,0]);xb=np.log(closes[i-window-1:i-1,1])
        beta=1.
        if model==1:
            xv=xb-xb.mean();den=(xv*xv).sum()
            if den<=1e-14:continue
            beta=(xv*(ya-ya.mean())).sum()/den
            if beta<0.1 or beta>3.:continue
        residual=ya-beta*xb;mu=residual.mean();sd=np.sqrt(((residual-mu)**2).mean())
        if sd<=1e-8:continue
        last=np.log(closes[i-1,0])-beta*np.log(closes[i-1,1]);z=(last-mu)/sd
        atr=np.abs(residual[1:]-residual[:-1])[-14:].mean()
        out[i]=np.array([z,beta,mu,sd,atr,residual[-8:].min(),residual[-8:].max(),last,xb.mean()])
    return out

def features(d,tf,window,model):
    rule=f'{tf}min'
    # Keep only complete TF candles. A partial broker opening bar is not accepted.
    agg=d[['close_a','close_b']].resample(rule).last()
    counts=d['close_a'].resample(rule).count()
    agg=agg[counts==tf//5].dropna()
    # Feature row belongs to next boundary; previous completed candles are causal.
    closes=np.vstack((agg.to_numpy(),agg.to_numpy()[-1]))
    val=feature_loop(closes,window,model)[1:]
    # Timestamp each observation at the close of its signal candle. Do not require
    # a future candle to be complete/exist to authorize the present signal.
    x=pd.DataFrame(val,index=agg.index+pd.Timedelta(minutes=tf)).reindex(d.index).to_numpy()
    return np.ascontiguousarray(x)

@njit(cache=True)
def simulate(m,f,spec,start,end,c,extra=0.):
    # Returns a complete basket ledger plus daily marked equity for diagnostics.
    threshold,session,stopmode,exitmode,rr,manage,direction,hold,risk=c
    cash=10000.;peak=10000.;dd=0.;maxddcash=0.;n=0;wins=0;gp=0.;gl=0.
    active=False;side=0;last_entry=-100000;floor=-1e100;highr=0.;swap=0.
    qa=qb=ea=eb=budget=entrycash=entryts=mu=beta=initialrr=entryfee=0.
    ledger=np.zeros((len(m)//2+1,15));daily=np.zeros((len(m)//200+2000,2));nd=0;lastday=-1
    rejected=0;unhedged=0
    for i in range(len(m)):
        ts=m[i,0]
        if ts<start or ts>=end:continue
        day=int(ts//86400);a=m[i,1];b=m[i,2];sa=m[i,5];sb=m[i,6]
        closed=False
        if active:
            # New bar executable prices; commission on both legs and both fills.
            xa=a+(sa if side<0 else 0.);xb=b+(sb if side>0 else 0.)
            swap+=qa/spec[0,0]*spec[0,4 if side>0 else 5]*spec[0,6]*spec[0,0]*m[i,8]
            swap+=qb/spec[1,0]*spec[1,4 if side<0 else 5]*spec[1,6]*spec[1,0]*m[i,9]
            ga=side*qa*(xa-ea);gb=-side*qb*(xb-eb)
            exitfee=(qa*xa+qb*xb)*(0.0001+extra)
            pnl=ga+gb+swap-entryfee-exitfee
            r=pnl/budget
            # M15 close triggers use both prices from the previous completed M5 candle.
            if manage==3 and ts%900==0 and ts-entryts>=900 and m[i-1,0]==ts-300:
                ca=m[i-1,3]+(m[i-1,5] if side<0 else 0.);cb=m[i-1,4]+(m[i-1,6] if side>0 else 0.)
                cr=(side*qa*(ca-ea)-side*qb*(cb-eb)+swap-entryfee-(qa*ca+qb*cb)*(0.0001+extra))/budget
                if cr>=.5:floor=max(floor,.2)
            reason=0
            if ga<=-budget*.5+2*qa*ea*(.0001+extra) or gb<=-budget*.5+2*qb*eb*(.0001+extra):reason=1
            elif r<=max(-1.,floor):reason=2
            elif exitmode<7 and r>=rr:reason=3
            elif exitmode==7 and side*(np.log(a)-beta*np.log(b)-mu)>=0:reason=4
            elif exitmode==8 and np.isfinite(f[i,2]):
                # Dynamic mean calculated with the frozen entry hedge beta from the
                # latest formation means is supplied separately below by native engine;
                # here f's current beta is not used to rehedge an open trade.
                target=f[i,2]+(f[i,1]-beta)*f[i,8]
                if side*(np.log(a)-beta*np.log(b)-target)>=0:reason=5
            if ts-entryts>=hold*3600:reason=6
            if i==len(m)-1 or (i+1<len(m) and m[i+1,0]>=end):reason=7
            if reason:
                cash+=pnl;n+=1;wins+=pnl>0;gp+=max(0.,pnl);gl+=max(0.,-pnl)
                ledger[n-1]=np.array([entryts,ts,side,ea,eb,xa,xb,qa/spec[0,0],qb/spec[1,0],pnl,pnl/entrycash,r,reason,swap,initialrr])
                active=False;closed=True;last_entry=i
            else:
                highr=max(highr,r)
                if manage==1 and r>=.5:floor=max(floor,0.)
                if manage==2 and r>=1.:floor=max(floor,0.)
                if manage==4 and r>=1.:floor=max(floor,highr-.5)
                if manage==5 and r>=1.:floor=max(floor,highr-1.)
                if manage==6 and r>=1. and np.isfinite(f[i,4]):floor=max(floor,r-max(.25,(qa*a)*f[i,4]*2.5/budget))
        equity=cash
        if active:equity=cash+pnl
        peak=max(peak,equity);dd=max(dd,1-equity/peak);maxddcash=max(maxddcash,peak-equity)
        if day!=lastday:
            daily[nd]=np.array([ts,equity]);nd+=1;lastday=day
        else:daily[nd-1,1]=equity
        if active or closed or i-last_entry<2 or cash<=100. or not np.isfinite(f[i,0]):continue
        if int(m[i,7]) & (1<<int(session))==0:continue
        z=f[i,0]
        if abs(z)<threshold:continue
        side=-1 if z>0 else 1
        if direction!=0 and side!=direction:continue
        beta=f[i,1];mu=f[i,2];sd=f[i,3];s=f[i,7]
        distance=sd
        if stopmode==1:distance=2.5*f[i,4]
        if stopmode==2:distance=(s-f[i,5] if side>0 else f[i,6]-s)+.25*sd
        if distance<=0:continue
        costs=sa/a+beta*sb/b+2*(1+beta)*(.0001+extra)
        distance=max(distance,costs*4)
        budget=cash*risk/100.;notional=budget/(distance+costs)
        la=math.floor(notional/(a*spec[0,0])/spec[0,2]+1e-9)*spec[0,2]
        lb=math.floor(beta*notional/(b*spec[1,0])/spec[1,2]+1e-9)*spec[1,2]
        if la<spec[0,1] or lb<spec[1,1] or la>spec[0,3] or lb>spec[1,3]:rejected+=1;continue
        # Require the rounded hedge notional to remain within 15% of the model.
        qa=la*spec[0,0];qb=lb*spec[1,0]
        if abs((qb*b)/(qa*a)/beta-1)>.15:rejected+=1;continue
        ea=a+(sa if side>0 else 0.);eb=b+(sb if side<0 else 0.)
        entryfee=(qa*ea+qb*eb)*(.0001+extra);swap=0.;entrycash=cash;entryts=ts
        initialrr=abs(mu-s)*notional/budget
        active=True;floor=-1e100;highr=0.
    pf=gp/gl if gl else (100. if gp else 0.)
    recovery=(cash-10000.)/maxddcash if maxddcash else 0.
    rets=(daily[1:nd,1]-daily[:nd-1,1])/daily[:nd-1,1]
    sharpe=rets.mean()/rets.std()*np.sqrt(365.) if len(rets)>1 and rets.std()>0 else 0.
    return np.array([(cash/10000-1)*100,pf,100*wins/n if n else 0.,dd*100,n,sharpe,recovery,rejected]),ledger[:n],daily[:nd]

METRICS=['return_pct','profit_factor','win_rate','dd_pct','trades','sharpe','recovery','skipped_min_lot_or_hedge']
def params(c):return np.array([c['entry'],c['session'],c['stop'],c['exit'],c['rr'],c['manage'],c['direction'],c['hold'],1.])

def run_config(m,f,spec,c,stage,extra=0.):
    a,b=PERIODS[stage];metrics,trades,equity=simulate(m,f,spec,stamp(a),stamp(b),params(c),extra)
    row=dict(zip(METRICS,map(float,metrics)));row['trades']=int(row['trades'])
    row.update(id=key(c),config=c,stage=stage)
    return row,trades,equity

def score(r):
    if r['trades']<30:return -10000+r['trades']
    return r['return_pct']-2*r['dd_pct']+3*(min(r['profit_factor'],3)-1)

def broad_configs():
    for tf,session,stop,ex in itertools.product((5,15,30,60,240),range(6),range(3),range(10)):
        rr=(.5,1.,1.5,2.,3.,4.,6.)[ex] if ex<7 else 1.
        yield dict(BASE,tf=tf,session=session,stop=stop,exit=ex,rr=rr)

def research():
    allrows=[];selections={};t0=time.monotonic()
    for pair in PAIRS:
        d,m,spec=load_pair(pair);cache={};seen={};rows=[]
        def feat(c):
            k=(c['tf'],c['window'],c['model'])
            if k not in cache:cache[k]=features(d,*k)
            return cache[k]
        def run(c):
            k=key(c)
            if k in seen:return seen[k]
            row,_,_=run_config(m,feat(c),spec,c,'train');row['pair']=pair
            seen[k]=row;rows.append(row)
            if len(rows)%100==0:print(pair,'TRAIN',len(rows),'elapsed',round(time.monotonic()-t0),flush=True)
            return row
        for c in broad_configs():run(c)
        # Signal sweep around each session's strongest broad configuration.
        anchors=[max([r for r in rows if r['config']['session']==s],key=score) for s in range(6)]
        for a in anchors:
            for window,model,entry,direction in itertools.product((32,64,128),(0,1),(1.5,2.,2.5,3.),(0,1,-1)):
                run(dict(a['config'],window=window,model=model,entry=entry,direction=direction))
        # Management and holding interactions around top two per session.
        anchors=[]
        for s in range(6):anchors.extend(sorted([r for r in rows if r['config']['session']==s],key=score,reverse=True)[:2])
        for a in anchors:
            for manage,hold in itertools.product(range(7),(6,24,72)):
                run(dict(a['config'],manage=manage,hold=hold))
        finalists=[]
        for s in range(6):finalists.extend(sorted([r for r in rows if r['config']['session']==s],key=score,reverse=True)[:3])
        # Baseline always included, regardless of training score.
        finalists.append(run(BASE))
        unique={r['id']:r for r in finalists}
        validation=[]
        for r in unique.values():
            vr,_,_=run_config(m,feat(r['config']),spec,r['config'],'validation');vr['pair']=pair
            vr['train_score']=score(r);vr['selection_score']=min(score(r),score(vr))
            validation.append(vr)
        winner=max(validation,key=lambda r:r['selection_score'])
        selections[pair]=dict(config=winner['config'],id=winner['id'],selection_score=winner['selection_score'],eligible=winner['selection_score']>-1000,
            selection_method='best minimum train/validation drawdown-penalized score; at least 30 baskets per year required',screen_configs=len(rows))
        allrows+=rows+validation
        dump(ROOT/'screen-results.json',allrows);dump(ROOT/'selection.json',selections)
        print('LOCKED',pair,selections[pair],flush=True)
    # Both configurations frozen before reading either final year performance.
    dump(ROOT/'selection-lock.json',dict(locked_utc=datetime.now(timezone.utc).isoformat(),selections=selections,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    for pair in PAIRS:
        d,m,spec=load_pair(pair)
        for label,c in [('baseline',BASE),('selected',selections[pair]['config'])]:
            f=features(d,c['tf'],c['window'],c['model'])
            for stage in ('test','full'):
                row,trades,eq=run_config(m,f,spec,c,stage);row.update(pair=pair,label=label);allrows.append(row)
                np.savez_compressed(ROOT/f'{pair}-{stage}-{label}.npz',trades=trades,equity=eq)
                print('FINAL',pair,label,stage,{k:row[k] for k in METRICS},flush=True)
            # Cost-stress is sensitivity only, never used to reselect a winner.
            for cost in (.0001,.00025):
                row,_,_=run_config(m,f,spec,c,'test',cost);row.update(pair=pair,label=label,extra_commission_bps_per_side=cost*10000);allrows.append(row)
    dump(ROOT/'screen-results.json',allrows)
    print('SCREEN COMPLETE',len(allrows),'rows',round(time.monotonic()-t0),'seconds',flush=True)

if __name__=='__main__':research()
