"""Broad, no-lookahead M15 screen for the slow multi-asset trend hypothesis."""
from pathlib import Path
from dataclasses import dataclass
import itertools, json, math
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
SYMBOLS=('XAUUSD','XAGUSD','BTCUSD','ETHUSD','USTEC','US30','EURUSD','GBPJPY')
DEV=(pd.Timestamp('2023-09-01',tz='UTC'),pd.Timestamp('2025-09-01',tz='UTC'))
TEST=(pd.Timestamp('2025-09-01',tz='UTC'),pd.Timestamp('2026-09-01',tz='UTC'))
FULL=(pd.Timestamp('2023-09-01',tz='UTC'),pd.Timestamp('2026-09-01',tz='UTC'))
TF={'H4':('4h',6),'D1':('1D',1),'W1':('W-MON',1)}
HORIZONS={
    '1m':(21,), '3m':(63,), '6m':(126,),
    '1-3-6m':(21,63,126), '3-6-12m':(63,126,252),
}
TREND={'none':(0,False),'ema100':(100,False),'ema200':(200,False),'ema200-rising':(200,True)}
SESSIONS={'all-day':-1,'asia':60,'london':480,'new-york':810,'overlap':840}
STOP_NAMES={0:'atr',1:'swing',2:'chandelier'}
EXIT_NAMES={0:'signal-reversal',1:'fixed-rr',2:'adaptive-rr',3:'timed'}
MANAGE_NAMES={0:'none',1:'breakeven',2:'atr-trail',3:'chandelier-trail',4:'dynamic-m15-50-20'}

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def load(symbol):
    a=np.load(ROOT/'Data'/f'{symbol}-M15.npz')['rates']
    idx=pd.to_datetime(a['time'],unit='s',utc=True)
    frame=pd.DataFrame({k:a[k].astype(float) for k in ('open','high','low','close','tick_volume','spread')},index=idx)
    meta=json.loads((ROOT/'Data'/'metadata.json').read_text())['symbols'][symbol]
    point=float(meta['point'])
    # Recorded zero spreads are unavailable observations, not free execution.
    positive=frame.loc[frame.spread>0,'spread']
    floor=float(positive.quantile(.20)) if len(positive) else 1.0
    frame['spread_price']=np.maximum(frame.spread,floor)*point
    return frame,meta,floor

def annual_bars(tf):
    return {'H4':6*252,'D1':252,'W1':52}[tf]

def resampled(frame,tf):
    rule=TF[tf][0]
    b=frame.resample(rule,label='right',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('tick_volume','sum')).dropna()
    prev=b.close.shift(1)
    tr=pd.concat([(b.high-b.low),(b.high-prev).abs(),(b.low-prev).abs()],axis=1).max(axis=1)
    b['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    return b

def make_signal(frame,tf,horizon_name,trend_name,direction):
    b=resampled(frame,tf)
    scale=annual_bars(tf)/252.0
    hs=tuple(max(1,int(round(x*scale))) for x in HORIZONS[horizon_name])
    signs=[]
    for h in hs:
        signs.append(np.sign(b.close/b.close.shift(h)-1))
    signed=pd.concat(signs,axis=1)
    vote=signed.mean(axis=1)
    sig=np.sign(vote).fillna(0).astype(np.int8)
    strength=vote.abs().fillna(0)
    ema_len,rising=TREND[trend_name]
    if ema_len:
        n=max(2,int(round(ema_len*scale)))
        ema=b.close.ewm(span=n,adjust=False,min_periods=n).mean()
        sig[((sig>0)&(b.close<=ema))|((sig<0)&(b.close>=ema))]=0
        if rising:
            slope=ema-ema.shift(max(1,int(round(21*scale))))
            sig[((sig>0)&(slope<=0))|((sig<0)&(slope>=0))]=0
    if direction=='long-only': sig[sig<0]=0
    look=max(3,int(round(10*scale)))
    rolling_low=b.low.rolling(look).min(); rolling_high=b.high.rolling(look).max()
    chand_long=b.high.rolling(max(5,int(round(20*scale)))).max()-3*b.atr
    chand_short=b.low.rolling(max(5,int(round(20*scale)))).min()+3*b.atr
    values=pd.DataFrame({'signal':sig,'strength':strength,'atr':b.atr,'swing_low':rolling_low,'swing_high':rolling_high,'chand_long':chand_long,'chand_short':chand_short},index=b.index)
    # Values become available at the resample label; forward filling uses completed bars only.
    out=values.reindex(frame.index,method='ffill')
    stamp=pd.Series(np.arange(1,len(values)+1,dtype=np.int64),index=values.index).reindex(frame.index,method='ffill').fillna(0)
    return out,stamp.to_numpy(np.int64)

@njit(cache=True)
def simulate_numba(ts,op,hi,lo,cl,spr,sig,strength,atr,swing_lo,swing_hi,chand_lo,chand_hi,stamp,
                   start_ts,end_ts,session_minute,stop_mode,stop_atr,exit_mode,rr,max_hold_days,manage,tf_code):
    # Fixed-size output is safe because at most one trade closes per input bar.
    n=len(ts); entries=np.empty(n,np.int64); exits=np.empty(n,np.int64); rs=np.empty(n,np.float64); sides=np.empty(n,np.int8)
    count=0; pos=0; entry=0.; initial=0.; stop=0.; target=0.; entry_i=0; last_stamp=-1
    realized=1.0;peak=1.0;max_dd=0.0
    cooldown=96 if tf_code<2 else 672
    for i in range(1,n):
        if ts[i] < start_ts or ts[i] >= end_ts: continue
        s=int(sig[i]); minute=int((ts[i]%86400)//60)
        # Signal reversal/neutral exits are evaluated at the next tradable bar open.
        if pos!=0 and exit_mode==0 and (s==0 or s==-pos):
            px=op[i] if pos>0 else op[i]+spr[i]
            r=pos*(px-entry)/initial-0.02-0.0015*((ts[i]-ts[entry_i])/86400.0)
            entries[count]=ts[entry_i];exits[count]=ts[i];rs[count]=r;sides[count]=pos;count+=1;realized*=1.0+.01*r;peak=max(peak,realized);max_dd=max(max_dd,1.0-realized/peak);pos=0
        if pos!=0 and max_hold_days>0 and ts[i]-ts[entry_i]>=max_hold_days*86400:
            px=op[i] if pos>0 else op[i]+spr[i]
            r=pos*(px-entry)/initial-0.02-0.0015*((ts[i]-ts[entry_i])/86400.0)
            entries[count]=ts[entry_i];exits[count]=ts[i];rs[count]=r;sides[count]=pos;count+=1;realized*=1.0+.01*r;peak=max(peak,realized);max_dd=max(max_dd,1.0-realized/peak);pos=0
        if pos!=0:
            # Conservative same-bar convention: stop is checked before target.
            hit=False; px=0.
            if pos>0:
                if op[i]<=stop: px=op[i];hit=True
                elif lo[i]<=stop: px=stop;hit=True
                elif target>0 and hi[i]>=target: px=target;hit=True
            else:
                ask_open=op[i]+spr[i];ask_hi=hi[i]+spr[i];ask_lo=lo[i]+spr[i]
                if ask_open>=stop: px=ask_open;hit=True
                elif ask_hi>=stop: px=stop;hit=True
                elif target>0 and ask_lo<=target: px=target;hit=True
            if hit:
                r=pos*(px-entry)/initial-0.02-0.0015*((ts[i]-ts[entry_i])/86400.0)
                entries[count]=ts[entry_i];exits[count]=ts[i];rs[count]=r;sides[count]=pos;count+=1;realized*=1.0+.01*r;peak=max(peak,realized);max_dd=max(max_dd,1.0-realized/peak);pos=0
            else:
                # Conservative intrabar mark-to-market: favorable extreme updates
                # the equity peak before the adverse extreme is measured.
                held=(ts[i]-ts[entry_i])/86400.0
                best_r=((hi[i]-entry)/initial if pos>0 else (entry-(lo[i]+spr[i]))/initial)-0.02-0.0015*held
                worst_r=((lo[i]-entry)/initial if pos>0 else (entry-(hi[i]+spr[i]))/initial)-0.02-0.0015*held
                best_eq=realized*(1.0+.01*best_r);worst_eq=realized*(1.0+.01*worst_r)
                peak=max(peak,best_eq)
                if peak>0.0:max_dd=max(max_dd,1.0-worst_eq/peak)
                progress=(cl[i]-entry)/initial if pos>0 else (entry-(cl[i]+spr[i]))/initial
                if manage==1 and progress>=1.0:
                    stop=max(stop,entry) if pos>0 else min(stop,entry)
                elif manage==2 and progress>=1.0:
                    candidate=cl[i]-2.5*atr[i] if pos>0 else cl[i]+spr[i]+2.5*atr[i]
                    stop=max(stop,candidate) if pos>0 else min(stop,candidate)
                elif manage==3 and progress>=1.0:
                    candidate=chand_lo[i] if pos>0 else chand_hi[i]+spr[i]
                    # A stop cannot be modified through the current market price.
                    candidate=min(candidate,cl[i]) if pos>0 else max(candidate,cl[i]+spr[i])
                    stop=max(stop,candidate) if pos>0 else min(stop,candidate)
                elif manage==4 and progress>=0.5:
                    candidate=entry+pos*0.2*initial
                    stop=max(stop,candidate) if pos>0 else min(stop,candidate)
        allowed=(session_minute<0 or minute==session_minute)
        if pos==0 and s!=0 and allowed and stamp[i]>last_stamp and (i-entry_i>=cooldown or entry_i==0):
            ent=op[i]+spr[i] if s>0 else op[i]
            a=atr[i]
            if not np.isfinite(a) or a<=0: continue
            dist=stop_atr*a
            if stop_mode==1:
                raw=ent-swing_lo[i] if s>0 else swing_hi[i]+spr[i]-ent
                if np.isfinite(raw): dist=max(.75*a,min(5*a,raw+.15*a))
            elif stop_mode==2:
                raw=ent-chand_lo[i] if s>0 else chand_hi[i]+spr[i]-ent
                if np.isfinite(raw): dist=max(.75*a,min(5*a,raw))
            if dist<=spr[i]*1.5: continue
            pos=s;entry=ent;initial=dist;stop=entry-s*dist;entry_i=i;last_stamp=stamp[i]
            effective_rr=rr
            if exit_mode==2: effective_rr=4.0 if strength[i]>=.99 else 1.5
            target=entry+s*effective_rr*dist if exit_mode in (1,2) else 0.
    if pos!=0:
        i=n-1;px=cl[i] if pos>0 else cl[i]+spr[i]
        r=pos*(px-entry)/initial-0.02-0.0015*((ts[i]-ts[entry_i])/86400.0)
        entries[count]=ts[entry_i];exits[count]=ts[i];rs[count]=r;sides[count]=pos;count+=1;realized*=1.0+.01*r;peak=max(peak,realized);max_dd=max(max_dd,1.0-realized/peak)
    return entries[:count],exits[:count],rs[:count],sides[:count],max_dd*100.0

def metrics(entries,exits,rs,sides,equity_dd_override=None,risk=1.0):
    if not len(rs):
        return dict(return_pct=0.,profit_factor=0.,win_rate=0.,max_dd_pct=0.,trades=0,sharpe=0.,recovery=0.,expectancy_r=0.,avg_win_r=0.,avg_loss_r=0.,longs=0,shorts=0,first_half_return=0.,second_half_return=0.)
    fr=rs*risk/100.0
    balances=10000*np.cumprod(1+fr);curve=np.r_[10000.,balances]
    pnl=np.diff(curve);gain=pnl[pnl>0].sum();loss=-pnl[pnl<0].sum();pf=gain/loss if loss else 99.
    dd=np.max(1-curve/np.maximum.accumulate(curve))*100
    if equity_dd_override is not None: dd=max(dd,float(equity_dd_override))
    daily=pd.Series(fr,index=pd.to_datetime(exits,unit='s',utc=True)).groupby(level=0).sum().resample('1D').sum()
    sharpe=float(daily.mean()/daily.std(ddof=1)*math.sqrt(252)) if daily.std(ddof=1)>0 else 0.
    mid=len(fr)//2
    first=(np.prod(1+fr[:mid])-1)*100 if mid else 0.;second=(np.prod(1+fr[mid:])-1)*100
    ret=(curve[-1]/10000-1)*100
    return dict(return_pct=float(ret),profit_factor=float(min(pf,99)),win_rate=float(np.mean(rs>0)*100),max_dd_pct=float(dd),trades=int(len(rs)),sharpe=sharpe,recovery=float(ret/dd if dd else 0),expectancy_r=float(rs.mean()),avg_win_r=float(rs[rs>0].mean() if np.any(rs>0) else 0),avg_loss_r=float(rs[rs<0].mean() if np.any(rs<0) else 0),longs=int(np.sum(sides>0)),shorts=int(np.sum(sides<0)),first_half_return=float(first),second_half_return=float(second))

@dataclass(frozen=True)
class Config:
    tf:str='D1';horizon:str='1-3-6m';trend:str='ema200-rising';direction:str='both';session:str='all-day'
    stop_mode:int=0;stop_atr:float=2.5;exit_mode:int=0;rr:float=2.;max_hold_days:int=0;manage:int=0
    def asdict(self): return self.__dict__

def run(frame,config,start,end):
    ind,stamp=make_signal(frame,config.tf,config.horizon,config.trend,config.direction)
    a=frame
    args=[a.index.as_unit('s').asi8.astype(np.int64),a.open.to_numpy(),a.high.to_numpy(),a.low.to_numpy(),a.close.to_numpy(),a.spread_price.to_numpy(),ind.signal.fillna(0).to_numpy(np.int8),ind.strength.fillna(0).to_numpy(),ind.atr.to_numpy(),ind.swing_low.to_numpy(),ind.swing_high.to_numpy(),ind.chand_long.to_numpy(),ind.chand_short.to_numpy(),stamp]
    out=simulate_numba(*args,int(start.timestamp()),int(end.timestamp()),SESSIONS[config.session],config.stop_mode,config.stop_atr,config.exit_mode,config.rr,config.max_hold_days,config.manage,{'H4':0,'D1':1,'W1':2}[config.tf])
    entries,exits,rs,sides,mtm_dd=out
    m=metrics(entries,exits,rs,sides,mtm_dd);m['trades_data']=[dict(entry=pd.Timestamp(int(e),unit='s',tz='UTC').isoformat(),exit=pd.Timestamp(int(x),unit='s',tz='UTC').isoformat(),r=float(r),side='long' if s>0 else 'short') for e,x,r,s in zip(entries,exits,rs,sides)]
    return m

def score(m):
    if m['trades']<10: return -10000+m['trades']
    if m['return_pct']<=0: return -100-m['max_dd_pct']
    # Selection is deliberately risk-adjusted. Log return prevents an explosive
    # development trend from overwhelming drawdown, consistency and recovery.
    pf=max(.01,min(m['profit_factor'],3.0));recovery=max(-5,min(10,m['recovery']))
    consistency=max(-20,min(20,min(m['first_half_return'],m['second_half_return'])))
    return (5*math.log1p(m['return_pct'])+5*math.log(pf)+3*recovery+
            2*max(-3,min(3,m['sharpe']))+.02*m['win_rate']-.25*m['max_dd_pct']+.08*consistency)

def with_change(c,**changes):
    d=c.asdict();d.update(changes);return Config(**d)

def research():
    all_rows=[];selections={}
    for symbol in SYMBOLS:
        frame,meta,floor=load(symbol);print('SCREEN',symbol,len(frame),flush=True)
        baseline=Config()
        signal_rows=[]
        directions=('both','long-only') if symbol in ('USTEC','US30','BTCUSD','ETHUSD') else ('both',)
        for tf,horizon,trend,direction in itertools.product(TF,HORIZONS,TREND,directions):
            c=Config(tf=tf,horizon=horizon,trend=trend,direction=direction)
            m=run(frame,c,*DEV);row=dict(symbol=symbol,stage='development',phase='signal',name=f'{tf}-{horizon}-{trend}-{direction}',config=c.asdict(),**{k:v for k,v in m.items() if k!='trades_data'});row['score']=score(row);signal_rows.append(row);all_rows.append(row)
        chosen=max(signal_rows,key=lambda x:x['score']);c=Config(**chosen['config'])
        session_rows=[]
        for session in SESSIONS:
            x=with_change(c,session=session);m=run(frame,x,*DEV);row=dict(symbol=symbol,stage='development',phase='session',name=session,config=x.asdict(),**{k:v for k,v in m.items() if k!='trades_data'});row['score']=score(row);session_rows.append(row);all_rows.append(row)
        chosen=max(session_rows+[chosen],key=lambda x:x['score']);c=Config(**chosen['config'])
        exit_rows=[]
        for stop_mode,stop_atr in itertools.product(STOP_NAMES,(1.5,2.5,3.5)):
            variants=[(0,2.,0,'reversal')]+[(1,rr,0,f'{rr:g}R') for rr in (.5,1.,1.5,2.,3.,4.,6.)]+[(2,2.,0,'adaptive'),(3,2.,20,'time20'),(3,2.,60,'time60'),(3,2.,120,'time120')]
            for exit_mode,rr,days,label in variants:
                x=with_change(c,stop_mode=stop_mode,stop_atr=stop_atr,exit_mode=exit_mode,rr=rr,max_hold_days=days)
                m=run(frame,x,*DEV);row=dict(symbol=symbol,stage='development',phase='stop-exit',name=f'{STOP_NAMES[stop_mode]}-{stop_atr:g}-{label}',config=x.asdict(),**{k:v for k,v in m.items() if k!='trades_data'});row['score']=score(row);exit_rows.append(row);all_rows.append(row)
        chosen=max(exit_rows+[chosen],key=lambda x:x['score']);c=Config(**chosen['config'])
        manage_rows=[]
        for manage,name in MANAGE_NAMES.items():
            x=with_change(c,manage=manage);m=run(frame,x,*DEV);row=dict(symbol=symbol,stage='development',phase='management',name=name,config=x.asdict(),**{k:v for k,v in m.items() if k!='trades_data'});row['score']=score(row);manage_rows.append(row);all_rows.append(row)
        chosen=max(manage_rows+[chosen],key=lambda x:x['score']);c=Config(**chosen['config'])
        base_dev=run(frame,baseline,*DEV);sel_dev=run(frame,c,*DEV)
        selections[symbol]=dict(config=c.asdict(),development={k:v for k,v in sel_dev.items() if k!='trades_data'},baseline_development={k:v for k,v in base_dev.items() if k!='trades_data'},spread_floor_points=floor,data_first=frame.index[0].isoformat(),data_last=frame.index[-1].isoformat())
        dump(ROOT/'selection-lock.json',selections)
        print('LOCKED',symbol,c,sel_dev['return_pct'],sel_dev['profit_factor'],sel_dev['trades'],flush=True)
    # Only now is the untouched year evaluated.
    final={}
    for symbol in SYMBOLS:
        frame,_,_=load(symbol);c=Config(**selections[symbol]['config']);base=Config()
        final[symbol]={}
        for period,dates in [('test',TEST),('full',FULL)]:
            for label,x in [('baseline',base),('selected',c)]:
                m=run(frame,x,*dates)
                final[symbol][f'{period}_{label}']=m
                all_rows.append(dict(symbol=symbol,stage=period,phase='final',name=label,config=x.asdict(),**{k:v for k,v in m.items() if k!='trades_data'},score=score(m)))
        print('TEST',symbol,final[symbol]['test_selected']['return_pct'],final[symbol]['test_selected']['profit_factor'],final[symbol]['test_selected']['trades'],flush=True)
    dump(ROOT/'screen-final.json',final);dump(ROOT/'selection-lock.json',selections)
    pd.DataFrame([{k:v for k,v in r.items() if k!='config'}|{'config':json.dumps(r['config'],sort_keys=True)} for r in all_rows]).to_csv(ROOT/'all-screen-results.csv',index=False)
    print('SCREEN COMPLETE',len(all_rows),flush=True)

if __name__=='__main__': research()
