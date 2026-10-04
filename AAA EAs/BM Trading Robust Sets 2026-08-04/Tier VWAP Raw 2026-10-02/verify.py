"""Independent signal reconstruction from exported completed M1 inputs."""
import gzip,io,json
import numpy as np
import pandas as pd
from native import ROOT,OUT,load,save,ledger,sha
def read(row,suffix):return pd.read_csv(io.BytesIO(gzip.decompress((OUT/row['stage']/f"0-{suffix}.csv.gz").read_bytes())))
def check(row):
 assert row['net']['close_fail']==0 and row['net']['bad_risk']==0 and row['stopouts']==0,'Close/risk/stopout failure'
 b=read(row,'bars');s=read(row,'signals');d=ledger(row)
 ny=pd.to_datetime(b.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
 assert not b.epoch.duplicated().any()
 assert ((ny.dt.hour*60+ny.dt.minute)>=570).all()
 b['day']=ny.dt.date;b['p']=(b.high+b.low+b.close)/3
 b['w']=b.tick_volume.astype(float);b['wp']=b.w*b.p
 b['sw']=b.groupby('day').w.cumsum();b['sp']=b.groupby('day').wp.cumsum();b['vwap']=b.sp/b.sw
 # Recompute centered moments per day independently to avoid subtractive cancellation.
 all_sd=[]
 for _,g in b.groupby('day',sort=False):
  origin=float(g.p.iloc[0]);x=g.p.to_numpy()-origin;w=g.w.to_numpy();sw=np.cumsum(w)
  mx=np.cumsum(w*x)/sw;var=np.cumsum(w*x*x)/sw-mx*mx
  all_sd.extend(np.sqrt(np.maximum(0,var)))
 b['sd']=all_sd;lookup=b.set_index('epoch');seen=set()
 for a in s.itertuples():
  close=a.signal_bar+300;bar=lookup.loc[close-60];day=bar.day
  assert day not in seen,'More than one attempt per NY day';seen.add(day)
  assert abs(a.vwap-bar.vwap)<1e-7 and abs(a.sd-bar.sd)<1e-7,'VWAP/SD mismatch'
  m=b[(b.epoch>=a.signal_bar)&(b.epoch<close)]
  assert len(m)>0 and abs(a.signal_high-m.high.max())<1e-7 and abs(a.signal_low-m.low.min())<1e-7 and abs(a.signal_close-m.close.iloc[-1])<1e-7
  stamp=pd.Timestamp(a.epoch,unit='s',tz='UTC').tz_convert('America/New_York');minute=stamp.hour*60+stamp.minute
  assert a.epoch>=close and 600<=minute<900
  if a.side==1:assert a.signal_low<=a.vwap-2*a.sd and a.vwap-2*a.sd<a.signal_close<a.vwap
  else:assert a.signal_high>=a.vwap+2*a.sd and a.vwap<a.signal_close<a.vwap+2*a.sd
  assert abs(abs(a.initial_tp-a.entry_quote)-abs(a.entry_quote-a.initial_sl))<.011
  assert abs(a.initial_tp-a.vwap)<=.006
  # Native OrderCalcProfit returns account-currency cents; a half-cent
  # difference is rounding, not an extra-lot override. Filled risk audited separately.
  assert a.quoted_risk<=a.requested_risk+.00500001
 rejected=s[s.retcode!=10009]
 assert (rejected.retcode==10016).all(),'Unexplained entry failure'
 assert len(rejected)==row['net']['entry_fail'] and len(s)==len(d)+len(rejected),'Missing/rejected attempt accounting'
 assert np.allclose(d.net_profit,d.gross_profit+d.commission+d.swap+d.fee,atol=.001)
 before=10000+np.r_[0,np.cumsum(d.net_profit.to_numpy())[:-1]]
 assert np.allclose(d.requested_risk,before*.01,atol=.00001),'Not 1% current balance'
 assert (abs(d.volume-d.closed_volume)<1e-8).all()
 assert d.open_epoch.min()>=pd.Timestamp(row['start'].replace('.','-'),tz='UTC').timestamp()
 assert abs(d.net_profit.sum()-row['net']['net_profit'])<.02
 return dict(stage=row['stage'],positions=len(d),signals=len(s),rejected_invalid_stops=len(rejected),m1_bars=len(b),max_filled_risk_to_budget=float((d.actual_risk/d.requested_risk).max()),carryovers=row['net']['carryovers'],source_sha=sha(ROOT/'EA/Main.mqh'))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');args=p.parse_args()
 rows=load(ROOT/('SMOKE.json' if args.smoke else 'SUMMARY.json'))
 out=[check(r) for r in rows]
 save(ROOT/('SMOKE VERIFICATION.json' if args.smoke else 'VERIFICATION.json'),out)
 print(json.dumps(out,indent=2))
