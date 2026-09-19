"""Causal proxy-data research. No MT5 calls or production imports."""
from pathlib import Path
from datetime import timedelta
import argparse, hashlib, json, math
import holidays
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
END=pd.Timestamp('2026-09-01',tz='UTC')
START=END-pd.DateOffset(years=5)
GOLD=BASE/'3 way gold Full Optimization 2026-09-13/Data/prices.npz'
FX=BASE/'FX Fixing Reversal Research 2026-09-09/Data/USDJPY-M5.npz'
PERIODS={'6m':END-pd.DateOffset(months=6),'1y':END-pd.DateOffset(years=1),'3y':END-pd.DateOffset(years=3),'5y':START,'2025+':pd.Timestamp('2025-01-01',tz='UTC')}

def stamp(t): return int(pd.Timestamp(t).timestamp())
def iso(t): return pd.Timestamp(t,unit='s',tz='UTC').isoformat()

def atr_series(h):
    prev=h.close.shift(1)
    tr=pd.concat([h.high-h.low,(h.high-prev).abs(),(h.low-prev).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()

def gold_data():
    z=np.load(GOLD)
    m=pd.DataFrame(z['m1'],columns=['time','open','high','low','close','spread'])
    h=pd.DataFrame(z['h1'],columns=['time','open','high','low','close','spread'])
    m.index=pd.to_datetime(m.time,unit='s',utc=True)
    h.index=pd.to_datetime(h.time,unit='s',utc=True)+pd.Timedelta(hours=1)
    m['atr']=atr_series(h).reindex(m.index,method='ffill').to_numpy()
    m['spread']*=.001
    m['fx']=1.
    return m

def gold_signals(m,prose=False):
    days=(m.time.to_numpy().astype('int64')+10800)//86400
    g=m.groupby(days,sort=True)
    daily=g.agg(o=('open','first'),c=('close','last'),n=('time','count'))
    good=daily[daily.n>=1000].copy()
    ret=(good.c/good.o-1)*100
    good['mean']=ret.rolling(60).mean()
    good['sd']=ret.rolling(60).std(ddof=1)
    out=[]
    for day,row in daily.iterrows():
        # Current day's final bar count is unavailable at entry. Eligibility and
        # thresholds depend ONLY on qualified COMPLETED days strictly before it.
        q=good.index.searchsorted(day,side='left')-1
        if q<0:continue
        stats=good.iloc[q]
        if not np.isfinite(stats.sd): continue
        midnight=int(day)*86400
        if midnight < stamp(START) or midnight>=stamp(END): continue
        for hour,direction in ((14,1),(16,-1)) if prose else ((14,-1),(16,1)):
            t=midnight+hour*3600
            p=m.index.searchsorted(pd.Timestamp(t,unit='s',tz='UTC'))
            if p>=len(m) or m.time.iloc[p]!=t: continue
            rr=(m.open.iloc[p]/row.o-1)*100
            qualifies=(direction==1 and rr>max(0,stats['mean']+2*stats.sd)) or (direction==-1 and rr<min(0,stats['mean']-2*stats.sd))
            if qualifies:
                out.append({'t':t,'until':midnight+20*3600+50*60,'dir':direction,'atr':float(m.atr.iloc[p]),'observed_return':float(rr),'threshold_mean':float(stats['mean']),'threshold_sd':float(stats.sd)})
                break
    # Missing quotes cannot be interpreted as a known no-signal day. Recognized
    # exchange holidays explain routine closures; other holes censor challenges.
    closures=holidays.financial_holidays('NYSE',years=range(2021,2027))
    known=set(m.time.astype('int64'));last=float(m.time.iloc[-1])
    for date in pd.date_range(START,END-pd.Timedelta(days=1),freq='B'):
        if date.date() in closures:continue
        for hour in (14,16):
            ts=stamp(date+pd.Timedelta(hours=hour))
            if ts>last or ts in known:continue
            if any(x['t']<=ts and x['t']//86400==ts//86400 for x in out):break
            out.append({'t':ts,'until':stamp(date)+20*3600+50*60,'valid':False,'reason':'unexplained missing entry quote'})
            break
    out.sort(key=lambda x:x['t'])
    return out

def japan_data():
    z=np.load(ROOT/'Data/japan-m1.npz')
    cols=['time','open','high','low','close','volume']
    b=pd.DataFrame(z['BID'],columns=cols).set_index('time')
    a=pd.DataFrame(z['ASK'],columns=cols).set_index('time')
    m=b.join(a,rsuffix='_ask',how='inner')
    m=m[(m.volume>0)&(m.volume_ask>0)].copy()
    m['time']=m.index.astype('int64')
    m.index=pd.to_datetime(m.time,unit='s',utc=True)
    m['spread']=(m.open_ask-m.open).clip(lower=0)
    h=m.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    h.index+=pd.Timedelta(hours=1)
    m['atr']=atr_series(h).reindex(m.index,method='ffill').to_numpy()
    fx=np.load(FX)['rates']
    rate=pd.Series(fx['close'],index=pd.to_datetime(fx['time']+300,unit='s',utc=True))
    m['fx']=rate.reindex(m.index,method='ffill').to_numpy()
    ft=pd.Series(fx['time']+300,index=rate.index)
    m['fx_age']=m.time.to_numpy()-ft.reindex(m.index,method='ffill').to_numpy()
    return m

def japan_signals(m):
    sp=pd.read_csv(ROOT/'Data/SP500.csv',index_col=0,parse_dates=True)
    sp['SP500']=pd.to_numeric(sp.SP500,errors='coerce')
    sp=sp.dropna();sp['ret']=sp.SP500.pct_change()
    jp_holidays=holidays.Japan(years=range(2021,2027))
    out=[]
    for d in pd.date_range(START,END-pd.Timedelta(days=1),freq='B'):
        if d.date() in jp_holidays: continue
        # Previous US weekday, Friday for Monday. A US holiday leaves no signal.
        prior=(d.tz_localize(None)-pd.offsets.BDay(1)).normalize()
        if prior not in sp.index or not np.isfinite(sp.loc[prior,'ret']) or sp.loc[prior,'ret']==0: continue
        t=stamp(d-pd.Timedelta(minutes=15))
        p=m.index.searchsorted(pd.Timestamp(t,unit='s',tz='UTC'))
        if p>=len(m) or m.time.iloc[p]>t+60:
            out.append({'t':t,'until':t+1800,'valid':False,'reason':'missing opening quote'})
            continue
        if not np.isfinite(m.atr.iloc[p]) or not np.isfinite(m.fx.iloc[p]) or m.fx_age.iloc[p]>3600:
            out.append({'t':t,'until':t+1800,'valid':False,'reason':'missing ATR or stale FX'})
            continue
        out.append({'t':int(m.time.iloc[p]),'until':t+1800,'dir':-int(np.sign(sp.loc[prior,'ret'])),'atr':float(m.atr.iloc[p]),'sp_date':str(prior.date()),'sp_return':float(sp.loc[prior,'ret'])})
    return out

def execute(m,s,asset,stress=False,no_stop=False):
    if s.get('valid') is False: return dict(s)
    t=s['t'];until=s['until'];d=s['dir'];dist=2*s['atr']
    i=m.index.searchsorted(pd.Timestamp(t,unit='s',tz='UTC'))
    j=m.index.searchsorted(pd.Timestamp(until,unit='s',tz='UTC'))
    floor=(.6 if stress else .3) if asset=='gold' else (20 if stress else 10)
    slip=(.25 if stress else .1) if asset=='gold' else (5 if stress else 2)
    factor=2 if stress else 1
    contract=100 if asset=='gold' else 10
    comm=7e-6 if asset=='gold' else 0.
    quote=m.iloc[i]
    entry0=quote.open+max(quote.spread*factor,floor)+slip if d==1 else quote.open-slip
    unit_risk=(dist+slip)*contract/quote.fx+2*comm*contract*entry0/quote.fx
    invalid_base=dict(s,valid=False,asset=asset,unit_risk=float(unit_risk),unit_margin=float(entry0*contract/quote.fx/15))
    if j>=len(m) or m.time.iloc[j]>until+120:
        return dict(invalid_base,reason='scheduled exit quote unavailable')
    v=m.iloc[i:j+1]
    bid=v[['open','high','low','close']].to_numpy().copy()
    spr=np.maximum(v.spread.to_numpy()*factor,floor)
    if asset=='gold': ask=bid+spr[:,None]
    else:
        ask=v[['open_ask','high_ask','low_ask','close_ask']].to_numpy().copy()
        ask+=np.maximum(spr-v.spread.to_numpy(),0)[:,None]
    fx=v.fx.to_numpy()
    entry=(ask[0,0]+slip) if d==1 else (bid[0,0]-slip)
    stop=entry-d*dist
    exitidx=len(v)-1; exitreason='time'; exitprice=None
    # Do not inspect the exit minute's high/low; time exit occurs at its OPEN.
    if not no_stop:
        trigger=(bid[:-1,2]<=stop) if d==1 else (ask[:-1,1]>=stop)
        ix=np.flatnonzero(trigger)
        if len(ix):
            exitidx=int(ix[0]);exitreason='stop'
            exitprice=(min(stop,bid[exitidx,0])-slip) if d==1 else (max(stop,ask[exitidx,0])+slip)
    if exitprice is None: exitprice=(bid[exitidx,0]-slip) if d==1 else (ask[exitidx,0]+slip)
    if np.diff(v.time.iloc[:exitidx+1]).max(initial=0)>300:
        return dict(invalid_base,reason='more than five-minute gap in actual trade path')
    entryfee=comm*contract*entry/fx[0]
    exitfee=comm*contract*exitprice/fx[exitidx]
    net=d*(exitprice-entry)*contract/fx[exitidx]-entryfee-exitfee
    op=bid[:,0] if d==1 else ask[:,0]
    lo=bid[:,2] if d==1 else ask[:,1]
    hi=bid[:,1] if d==1 else ask[:,2]
    worst=d*(lo-entry)*contract/fx-entryfee-comm*contract*lo/fx
    best=d*(hi-entry)*contract/fx-entryfee-comm*contract*hi/fx
    worst=worst[:exitidx+1].copy();best=best[:exitidx+1].copy()
    # Exit bar ends at stop fill or timed opening, not its later extremes.
    openp=d*(op[exitidx]-entry)*contract/fx[exitidx]-entryfee-comm*contract*op[exitidx]/fx[exitidx]
    worst[-1]=min(openp,net);best[-1]=max(openp,net)
    lossunit=(dist+slip)*contract/fx[0]+2*entryfee
    return dict(s,valid=True,asset=asset,exit_t=int(v.time.iloc[exitidx]),entry=entry,exit=exitprice,stop=stop,reason=exitreason,unit_net=float(net),unit_commission=float(entryfee+exitfee),unit_slippage=float(slip*contract*(1/fx[0]+1/fx[exitidx])),unit_risk=float(lossunit),unit_margin=float(entry*contract/fx[0]/15),unit_worst=float(worst.min()),unit_best=float(best.max()),worst=worst.tolist(),best=best.tolist(),path_t=v.time.iloc[:exitidx+1].astype('int64').tolist(),fx=float(fx[0]),max_gap_s=float(np.diff(v.time).max(initial=0)))

def lots_for(tr,balance,risk):
    step=.01 if tr['asset']=='gold' else .1
    cap=100 if tr['asset']=='gold' else 200
    lots=min(risk/tr['unit_risk'],max(0,balance)*.5/tr['unit_margin'],cap)
    return math.floor((lots+1e-10)/step)*step

def metrics(trades,risk,start):
    balance=10000.;peak=10000.;dd=0.;rows=[];invalid=0;skips=0;worstday=0.
    for tr in trades:
        if tr['t']<stamp(start) or tr['t']>=stamp(END):continue
        if 'unit_risk' in tr and not lots_for(tr,balance,risk):skips+=1;continue
        if not tr.get('valid',False):invalid+=1;continue
        lot=lots_for(tr,balance,risk)
        if not lot:skips+=1;continue
        for lo,hi in zip(tr['worst'],tr['best']):
            peak=max(peak,balance+hi*lot)
            dd=max(dd,100*(peak-(balance+lo*lot))/peak)
        net=tr['unit_net']*lot
        worstday=max(worstday,-tr['unit_worst']*lot)
        balance+=net
        rows.append({'entry':iso(tr['t']),'exit':iso(tr['exit_t']),'side':tr['dir'],'lots':lot,'net_usd':net,'commission_usd':-tr['unit_commission']*lot,'slippage_usd':-tr['unit_slippage']*lot,'swap_usd':0.,'equity':balance,'exit_reason':tr['reason']})
        if balance<=0:break
    pnl=np.array([r['net_usd'] for r in rows]);wins=pnl[pnl>0].sum();loss=-pnl[pnl<0].sum()
    monthly={}
    for d in pd.date_range(start,END-pd.Timedelta(days=1),freq='MS'):monthly[str(d.date())[:7]]={'trades':0,'net_usd':0.,'commission_usd':0.}
    for r in rows:
        z=monthly.setdefault(r['entry'][:7],{'trades':0,'net_usd':0.,'commission_usd':0.})
        for key in ('net_usd','commission_usd'):z[key]+=r[key]
        z['trades']+=1
    return {'trades':len(rows),'net_usd':float(pnl.sum()),'return_pct':(balance/10000-1)*100,'win_pct':float((pnl>0).mean()*100) if len(pnl) else None,'pf':float(wins/loss) if loss else None,'equity_dd_pct':dd,'worst_day_adverse_usd':worstday,'invalid_signals':invalid,'size_skips':skips,'commission_usd':sum(r['commission_usd'] for r in rows),'monthly':monthly,'ledger':rows}

def simulate_one(trades,start,horizon,risk):
    deadline=start+pd.Timedelta(days=horizon);balance=10000.;phase=1;days=set();ready=stamp(start);phase1=None;last=stamp(start);inactivity=False;count=0
    for tr in trades:
        t=tr['t']
        if t<ready or t>=stamp(deadline):continue
        if t-last>30*86400:inactivity=True
        if 'unit_risk' in tr and not lots_for(tr,balance,risk):continue
        if not tr.get('valid',False):return {'outcome':'data_inconclusive','phase1':phase1 is not None,'inactivity':inactivity,'trades':count}
        lot=lots_for(tr,balance,risk)
        if not lot:continue
        count+=1;last=t
        # Both entries and exits stay inside one Prague trading day by design.
        a=pd.Timestamp(t,unit='s',tz='UTC').tz_convert('Europe/Prague')
        b=pd.Timestamp(tr['exit_t'],unit='s',tz='UTC').tz_convert('Europe/Prague')
        assert a.date()==b.date(), 'Unexpected midnight/rollover position'
        low=balance+tr['unit_worst']*lot
        if low<9000-1e-8 or low<balance-500-1e-8:
            return {'outcome':'breach','reason':'overall' if low<9000 else 'daily','phase1':phase1 is not None,'days':(t-stamp(start))/86400,'inactivity':inactivity,'trades':count}
        balance+=tr['unit_net']*lot;days.add(a.date())
        if balance>=(11000 if phase==1 else 10500) and len(days)>=4:
            if phase==2:return {'outcome':'both_passed','phase1':True,'days':(tr['exit_t']-stamp(start))/86400,'inactivity':inactivity,'trades':count}
            phase1=t;phase=2;balance=10000.;days=set()
            ready=stamp(b.normalize()+pd.offsets.BDay(2))
            last=ready
    if stamp(deadline)-last>=30*86400:inactivity=True
    return {'outcome':'pending','phase1':phase1 is not None,'inactivity':inactivity,'trades':count,'balance':balance}

def challenges(trades,risk):
    result={}
    # SAME complete 180-day cohort for all horizons, avoiding changing denominators.
    starts=pd.date_range(START,END-pd.Timedelta(days=180),freq='W-MON')
    for horizon in (30,60,180):
        outcomes=[simulate_one(trades,s,horizon,risk) for s in starts]
        counts={k:sum(x['outcome']==k for x in outcomes) for k in ('both_passed','breach','pending','data_inconclusive')}
        complete=len(outcomes)-counts['data_inconclusive']
        passed=[x['days'] for x in outcomes if x['outcome']=='both_passed']
        result[str(horizon)]={'starts':len(outcomes),'usable_starts':complete,**counts,'both_pass_pct':counts['both_passed']/complete*100 if complete else None,'breach_pct':counts['breach']/complete*100 if complete else None,'phase1_passed':sum(x['phase1'] for x in outcomes if x['outcome']!='data_inconclusive'),'inactivity_flagged':sum(x['inactivity'] for x in outcomes),'median_pass_days':float(np.median(passed)) if passed else None,'outcomes':[dict(x,start=str(s.date())) for x,s in zip(outcomes,starts)]}
    return result

def compact_metrics(x):return {k:v for k,v in x.items() if k not in ('ledger','monthly')}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gold-only',action='store_true');args=ap.parse_args()
    config=[('gold_tables','gold',False),('gold_prose','gold',True)]
    if not args.gold_only:config.append(('japan_open','japan',False))
    results={'scope':'Proxy research, not native FTMO backtests; frozen raw adaptations','start':str(START.date()),'end_exclusive':str(END.date()),'strategies':{},'source_hashes':{}}
    gm=gold_data();jm=None
    for name,asset,prose in config:
        m=gm if asset=='gold' else japan_data()
        signals=gold_signals(m,prose) if asset=='gold' else japan_signals(m)
        print(name,'signals',len(signals),flush=True)
        variants={}
        for label,stress,no_stop in [('base',False,False),('stress',True,False),('time_exit_only',False,True)]:
            trades=[execute(m,s,asset,stress,no_stop) for s in signals]
            trades.sort(key=lambda t:t['t'])
            periods={p:metrics(trades,50,s) for p,s in PERIODS.items()}
            variants[label]={'periods':periods,'challenges':{str(r):challenges(trades,r) for r in ((25,50,75,100) if label=='base' else (50,))},'invalid':[t for t in trades if not t.get('valid',False)]}
            # Complete per-lot paths retained for independent audit, not just rounded summaries.
            (ROOT/f'{name}-{label}-paths.json').write_text(json.dumps(trades,separators=(',',':')),encoding='utf-8')
            print(label,compact_metrics(periods['5y']),flush=True)
        results['strategies'][name]=variants
    for path in [GOLD,FX,ROOT/'RULES.md']:
        results['source_hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT/('gold-results.json' if args.gold_only else 'results.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')

if __name__=='__main__':main()
