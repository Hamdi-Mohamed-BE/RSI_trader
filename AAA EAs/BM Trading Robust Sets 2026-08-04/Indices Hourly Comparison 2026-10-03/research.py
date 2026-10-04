"""Full descriptive screen. No live trading, optimisation, or native-fill claims."""
from pathlib import Path
import gzip,hashlib,json,warnings
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
ASSETS={'US30':'US30','US100':'USTEC','SP500':'US500'}
WINDOWS={'1y':('2025-10-03','2026-10-03'),'3m':('2026-07-03','2026-10-03')}
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def eligible(t,hold=60):
 out=np.zeros(len(t),bool)
 if len(t)>hold:out[:-hold]=t[hold:]-t[:-hold]==hold*60
 return out
def streak(v):
 mw=ml=w=l=0
 for x in v:
  w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
 return mw,ml
def stats(d,start,end,cpp):
 v=d.net_points.to_numpy()*cpp;n=len(v)
 cal=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
 if not n:return dict(trades=0,net_cash=None,return_pct=None,mean_net_points=None,mean_spread_points=None,win_rate_pct=None,pf=None,closed_dd_pct=None,sharpe_daily=None,max_win_streak=None,max_loss_streak=None,capital_exhausted=None)
 balance=np.r_[10000.,10000.+np.cumsum(v)];peak=np.maximum.accumulate(balance)
 gp=float(v[v>0].sum());gl=float(-v[v<0].sum())
 daily=d.assign(cash=v).groupby('date').cash.sum().reindex(cal,fill_value=0).to_numpy()
 sd=daily.std(ddof=1);mw,ml=streak(v)
 return dict(trades=n,net_cash=float(v.sum()),return_pct=float(v.sum()/100.),mean_net_points=float(d.net_points.mean()),mean_spread_points=float(d.spread_points.mean()),win_rate_pct=float(100*(v>0).mean()),pf=gp/gl if gl else None,closed_dd_pct=float(np.max((peak-balance)/peak)*100),sharpe_daily=float(daily.mean()/sd*np.sqrt(252)) if sd else None,max_win_streak=mw,max_loss_streak=ml,capital_exhausted=bool(balance.min()<=0))
def family_inference(rows,ledgers,window):
 start,end=WINDOWS[window];cal=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
 active=[r for r in rows if r['window']==window and r['trades']>1]
 x=np.column_stack([ledgers[(r['asset'],r['hour'],r['side'])].set_index('date').net_points.reindex(cal).to_numpy() for r in active])
 m=np.nanmean(x,axis=0);center=x-m;days=len(cal);rng=np.random.default_rng(20261003);null=[]
 for i in range(100):
  starts=rng.integers(0,days,(100,(days+4)//5));idx=((starts[:,:,None]+np.arange(5))%days).reshape(100,-1)[:,:days]
  with warnings.catch_warnings():
   warnings.simplefilter('ignore',RuntimeWarning);null.append(np.nanmean(center[idx],axis=1))
 null=np.concatenate(null);se=np.nanstd(null,axis=0,ddof=1);valid=(se>0)&np.isfinite(se)
 z=np.zeros_like(null);z[:,valid]=np.abs(null[:,valid]/se[valid]);maximum=np.nanmax(z[:,valid],axis=1)
 for j,r in enumerate(active):
  if not valid[j]:continue
  obs=abs(m[j]/se[j]);r.update(ci95_low=float(m[j]+np.nanquantile(null[:,j],.025)),ci95_high=float(m[j]+np.nanquantile(null[:,j],.975)),p_raw=float((1+np.sum(z[:,j]>=obs))/10001),p_adjusted_maxT=float((1+np.sum(maximum>=obs))/10001),tested_family=len(active))
def main():
 rows=[];ledgers={};audit=[];overnight=[];alltrades=[]
 for asset,symbol in ASSETS.items():
  p=R/'data'/f'{symbol}-M1.csv.gz';b=pd.read_csv(p);s=pd.read_csv(R/'data'/f'{symbol}-spec.csv').iloc[0]
  tailpath=R/'data'/f'{symbol}-API-tail.json';tail=pd.DataFrame(json.loads(tailpath.read_text())['bars'])
  tail['time']=pd.to_datetime(tail.time,utc=True).dt.as_unit('s').astype('int64')
  assert tail.time.iloc[0]==int(pd.Timestamp('2026-10-02',tz='UTC').timestamp())
  overlap=b.merge(tail,on='time');assert len(overlap)==1
  # Tester-generated M1 history can differ from the terminal's live bid bar
  # (e.g. midpoint vs spread-adjusted bid). Keep this discrepancy in the audit;
  # the final headline statistics use native deals, not this price splice.
  boundary_delta=float(np.max(np.abs(overlap.open_x-overlap.open_y)))
  b=pd.concat([b,tail[b.columns]],ignore_index=True).drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
  assert b.time.is_monotonic_increasing and not b.time.duplicated().any()
  assert b.time.min()>=int(pd.Timestamp('2025-10-03',tz='UTC').timestamp())
  assert b.time.max()==int(pd.Timestamp('2026-10-02 20:54',tz='UTC').timestamp())
  assert (b.spread>=0).all() and (b.low<=b.open).all() and (b.high>=b.open).all()
  assert s.tick_size>0 and abs(s.tick_value_profit-s.tick_value_loss)<1e-10
  cpp=float(s.tick_value_profit/s.tick_size);point=float(s.point);assert cpp>0
  t=b.time.to_numpy();clock=pd.to_datetime(t,unit='s',utc=True).tz_convert('America/New_York');o=b.open.to_numpy();sp=b.spread.to_numpy()*point
  mask=eligible(t)&(clock.dayofweek<5)&(clock.minute==0);ids=np.flatnonzero(mask)
  base=pd.DataFrame(dict(date=clock[ids].strftime('%Y-%m-%d'),hour=clock[ids].hour,epoch=t[ids],exit_epoch=t[ids+60],gross_points=o[ids+60]-o[ids],entry_spread=sp[ids],exit_spread=sp[ids+60]))
  for h in range(24):
   for side,sign in [('buy',1),('sell',-1)]:
    d=base[base.hour==h].copy();d['side']=side;d['asset']=asset;d['spread_points']=d.entry_spread if sign==1 else d.exit_spread;d['net_points']=sign*d.gross_points-d.spread_points
    ledgers[(asset,h,side)]=d;alltrades.extend(d.to_dict('records'))
    for w,(a,z) in WINDOWS.items():
     cut=d[(d.date>=a)&(d.date<z)];rows.append(dict(asset=asset,symbol=symbol,window=w,start=a,end_exclusive=z,hour=h,central_hour=(h-1)%24,side=side,**stats(cut,a,z,cpp)))
  audit.append(dict(asset=asset,symbol=symbol,bars=len(b),first_utc=str(pd.to_datetime(t[0],unit='s',utc=True)),last_utc=str(pd.to_datetime(t[-1],unit='s',utc=True)),cpp=cpp,spec={k:float(v) for k,v in s.to_dict().items()},data_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),api_tail_sha256=hashlib.sha256(tailpath.read_bytes()).hexdigest(),api_tail_bars=len(tail),boundary_bid_open_difference=boundary_delta))
  if asset=='SP500':
   ids=np.flatnonzero(eligible(t,660)&(clock.dayofweek<5)&(clock.hour==19)&(clock.minute==0))
   d=pd.DataFrame(dict(date=clock[ids].strftime('%Y-%m-%d'),epoch=t[ids],exit_epoch=t[ids+660],net_points=o[ids+660]-o[ids]-sp[ids],spread_points=sp[ids]))
   # Next NY local day at 06:00, never bridge a missing minute or weekend.
   assert np.all(clock[ids+660].hour==6)
   for w,(a,z) in WINDOWS.items():overnight.append(dict(asset=asset,window=w,entry_ct='18:00',exit_ct='05:00 next day',entry_ny='19:00',exit_ny='06:00 next day',funding_modeled=False,**stats(d[(d.date>=a)&(d.date<z)],a,z,cpp)))
   (R/'overnight-ledger.json.gz').write_bytes(gzip.compress(json.dumps(d.to_dict('records')).encode(),mtime=0))
  print('CALCULATED',asset,flush=True)
 for w in WINDOWS:family_inference(rows,ledgers,w);print('INFERENCE',w,flush=True)
 save(R/'SUMMARY.json',rows);save(R/'OVERNIGHT.json',overnight)
 (R/'hourly-ledgers.json.gz').write_bytes(gzip.compress(json.dumps(alltrades).encode(),mtime=0))
 save(R/'AUDIT.json',dict(protocol_sha256=hashlib.sha256((R/'PROTOCOL.txt').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),assets=audit,rows=len(rows),windows=WINDOWS,bootstrap_seed=20261003,bootstrap_paths=10000,block_dates=5,primary_inference='two-sided family max-T vs zero mean net points',not_native_fills=True))
 for asset in ASSETS:
  for w in WINDOWS:
   ranked=sorted([r for r in rows if r['asset']==asset and r['window']==w and r['trades']>=30 and r['pf'] is not None],key=lambda r:r['sharpe_daily'],reverse=True)
   print(json.dumps({'asset':asset,'window':w,'top_by_sharpe':ranked[:3]}),flush=True)
 print('OVERNIGHT',json.dumps(overnight),flush=True)
if __name__=='__main__':main()
