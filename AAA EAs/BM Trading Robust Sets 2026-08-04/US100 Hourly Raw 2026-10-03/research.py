"""Spread-aware bar-level study. Not a native fill or shared-margin backtest."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
WINDOWS={'5y':('2021-10-02','2026-10-02'),'first3y':('2021-10-02','2024-10-02'),'last2y':('2024-10-02','2026-10-02'),'1y':('2025-10-02','2026-10-02'),'6m':('2026-04-02','2026-10-02'),'3m':('2026-07-02','2026-10-02')}
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def eligible(t):
 # 61 rows must cover exactly 60 minutes; strictly increasing timestamps checked.
 n=len(t);out=np.zeros(n,dtype=bool)
 if n>60:out[:-60]=t[60:]-t[:-60]==3600
 return out
def drawdown(values):
 a=np.asarray(values,dtype=float);peak=np.maximum.accumulate(a)
 return float(np.max((peak-a)/peak)*100)
def streak(v):
 mw=ml=w=l=0
 for x in v:
  w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
 return mw,ml
def stats(trades,bars,cpp,start,end):
 d=trades[(trades.date>=start)&(trades.date<end)].copy();v=d.net_points.to_numpy()*cpp
 eq=np.r_[10000,10000+np.cumsum(v)];win,loss=streak(v)
 gp=v[v>0].sum();gl=-v[v<0].sum();pf=float(gp/gl) if gl else None
 cal=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
 daily=d.assign(pnl=v).groupby('date').pnl.sum().reindex(cal,fill_value=0).to_numpy()
 denom=daily.std(ddof=1);sh=float(daily.mean()/denom*np.sqrt(252)) if denom else None
 floating=[10000.];before=10000.
 for r in d.itertuples():
  i=r.bar_index;entry=r.entry_ask
  floating.append(before+(bars.open.iloc[i]-entry)*cpp)
  floating.extend(before+(bars.close.iloc[i:i+60].to_numpy()-entry)*cpp)
  before+=r.net_points*cpp;floating.append(before)
 n=len(v);months=(pd.Timestamp(end)-pd.Timestamp(start)).days/365.2425*12
 return dict(trades=n,net_cash=float(v.sum()),return_pct=float(v.sum()/100),mean_net_points=float(d.net_points.mean()) if n else None,mean_gross_points=float(d.gross_points.mean()) if n else None,mean_spread_points=float(d.spread_points.mean()) if n else None,mean_abs_gross_points=float(d.gross_points.abs().mean()) if n else None,win_rate_pct=float(100*(v>0).mean()) if n else None,pf=pf,closed_dd_pct=drawdown(eq),m1_close_marked_dd_pct=drawdown(floating),sharpe_daily=sh,max_win_streak=win,max_loss_streak=loss,trades_month=n/months,trades_weekday=n/len(cal),utc_midnight_crossings=int(d.rollover.sum()),capital_exhausted=bool(min(floating)<=0))
def inference(edge,seed=20261003,paths=10000,block=5):
 rng=np.random.default_rng(seed);x=np.asarray(edge,float);m=np.nanmean(x,axis=0);center=x-m;days,hours=x.shape
 sims=[]
 for a in range(0,paths,100):
  n=min(100,paths-a);starts=rng.integers(0,days,(n,(days+block-1)//block));idx=((starts[:,:,None]+np.arange(block))%days).reshape(n,-1)[:,:days]
  sims.append(np.nanmean(center[idx],axis=1))
 null=np.concatenate(sims);se=null.std(axis=0,ddof=1);t=m/se;z=null/se;maximum=z.max(axis=1)
 return [dict(mean_edge_points=float(m[j]),block_se=float(se[j]),ci95_low=float(m[j]+np.quantile(null[:,j],.025)),ci95_high=float(m[j]+np.quantile(null[:,j],.975)),p_raw=float((1+np.sum(z[:,j]>=t[j]))/(paths+1)),p_adjusted_maxT=float((1+np.sum(maximum>=t[j]))/(paths+1)),paired_days=int(np.sum(np.isfinite(x[:,j])))) for j in range(hours)]
def main():
 b=pd.read_csv(ROOT/'data/USTEC-M1.csv.gz');spec=pd.read_csv(ROOT/'data/spec.csv').iloc[0]
 assert b.time.is_monotonic_increasing and not b.time.duplicated().any()
 assert (b.spread>=0).all() and (b.low<=b.open).all() and (b.high>=b.open).all()
 assert spec.tick_size>0 and abs(spec.tick_value_profit-spec.tick_value_loss)<1e-8
 cpp=float(spec.tick_value_profit/spec.tick_size);point=float(spec.point)
 assert cpp>0
 clock=pd.to_datetime(b.time,unit='s',utc=True).dt.tz_convert('America/New_York')
 mask=eligible(b.time.to_numpy())&(clock.dt.dayofweek.to_numpy()<5)
 ids=np.flatnonzero(mask);entry=b.open.to_numpy()[ids]+b.spread.to_numpy()[ids]*point;exit_=b.open.to_numpy()[ids+60]
 utc=b.time.to_numpy()[ids];oututc=b.time.to_numpy()[ids+60]
 allholds=pd.DataFrame(dict(bar_index=ids,epoch=utc,date=clock.iloc[ids].dt.strftime('%Y-%m-%d').to_numpy(),hour=clock.iloc[ids].dt.hour.to_numpy(),minute=clock.iloc[ids].dt.minute.to_numpy(),entry_ask=entry,exit_bid=exit_,gross_points=exit_-b.open.to_numpy()[ids],spread_points=b.spread.to_numpy()[ids]*point,net_points=exit_-entry,rollover=utc//86400!=oututc//86400))
 allholds=allholds[(allholds.date>='2021-10-02')&(allholds.date<'2026-10-02')]
 onhour=allholds[allholds.minute==0].copy();onhour.to_csv(ROOT/'hourly-trades.csv',index=False)
 means=allholds.groupby('date').net_points.mean();onhour['random_mean_points']=onhour.date.map(means);onhour['edge_points']=onhour.net_points-onhour.random_mean_points
 rows=[];infer={}
 for window,(start,end) in WINDOWS.items():
  d=onhour[(onhour.date>=start)&(onhour.date<end)];table=d.pivot(index='date',columns='hour',values='edge_points');hours=[h for h in table.columns if table[h].count()>=100]
  if hours:
   inf=inference(table[hours].to_numpy(),seed=20261003);infer[window]={str(h):a for h,a in zip(hours,inf)}
  for h in sorted(onhour.hour.unique()):
   st=stats(onhour[onhour.hour==h],b,cpp,start,end)
   if st['trades']==0:continue
   match=d[d.hour==h];control=float(match.random_mean_points.mean())
   rows.append(dict(window=window,hour=int(h),random_mean_net_points=control,**st,**infer.get(window,{}).get(str(h),{})))
  print('Window complete:',window,flush=True)
 summary=pd.DataFrame(rows);summary.to_csv(ROOT/'hourly-summary.csv',index=False)
 primary=onhour[onhour.hour==11];rng=np.random.default_rng(20261003)
 pools={date:g.net_points.to_numpy() for date,g in allholds.groupby('date')};paths=np.zeros((2000,len(primary)))
 for j,r in enumerate(primary.itertuples()):p=pools[r.date];paths[:,j]=rng.choice(p,len(paths))
 cumulative=np.cumsum(paths,axis=1)*cpp
 np.savez_compressed(ROOT/'random-curves.npz',dates=primary.date.to_numpy(),q05=np.quantile(cumulative,.05,axis=0),median=np.median(cumulative,axis=0),q95=np.quantile(cumulative,.95,axis=0),observed=primary.net_points.cumsum().to_numpy()*cpp)
 random=dict(paths=2000,median_terminal_cash=float(np.median(cumulative[:,-1])),p05_terminal_cash=float(np.quantile(cumulative[:,-1],.05)),p95_terminal_cash=float(np.quantile(cumulative[:,-1],.95)),observed_terminal_cash=float(primary.net_points.sum()*cpp),fraction_random_ge_observed=float((1+np.sum(cumulative[:,-1]>=primary.net_points.sum()*cpp))/2001))
 audit=dict(bars=len(b),first_utc=str(pd.to_datetime(b.time.iloc[0],unit='s',utc=True)),last_utc=str(pd.to_datetime(b.time.iloc[-1],unit='s',utc=True)),eligible_minute_holds=len(allholds),hour_trades=len(onhour),distinct_dates=int(allholds.date.nunique()),eligible_hours_5y=sorted(infer['5y']),cash_per_index_point_per_lot=cpp,spec=spec.to_dict(),raw_data_sha256=hashlib.sha256((ROOT/'data/USTEC-M1.csv.gz').read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),random_primary=random)
 save(ROOT/'AUDIT.json',audit);save(ROOT/'SUMMARY.json',rows);save(ROOT/'INFERENCE.json',infer)
 print(json.dumps({'audit':audit,'11am':[r for r in rows if r['hour']==11],'rank5y':sorted([r for r in rows if r['window']=='5y'],key=lambda r:r['mean_net_points'],reverse=True)[:5]},indent=2),flush=True)
if __name__=='__main__':main()
