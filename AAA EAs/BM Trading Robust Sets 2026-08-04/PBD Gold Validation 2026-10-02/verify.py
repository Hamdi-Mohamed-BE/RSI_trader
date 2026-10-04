"""Recompute profile/shape, context and every exported native entry independently."""
import gzip,io,json
import numpy as np
import pandas as pd
from native import ROOT,OUT,load,save,ledger,sha
from rules import profile,context,signal

def read(row,suffix):
 return pd.read_csv(io.BytesIO(gzip.decompress((OUT/row['stage']/f"0-{suffix}.csv.gz").read_bytes())))

def check(row):
 assert row['net']['close_fail']==0 and row['net']['bad_risk']==0 and row['stopouts']==0
 b=read(row,'bars');s=read(row,'signals');d=ledger(row);p=read(row,'profiles');inputs=read(row,'profile-inputs')
 assert not p.day.duplicated().any() and not inputs.epoch.duplicated().any()
 dedup=b.drop_duplicates('epoch');assert len(b.drop_duplicates())==len(dedup),'Historical M5 inputs changed during run'
 b=dedup.sort_values('epoch').reset_index(drop=True);lookup={int(x):i for i,x in enumerate(b.epoch)}
 profiles={};counts={'P':0,'b':0,'D':0,'other':0}
 for a in p.itertuples():
  f=inputs[inputs.day==a.day].sort_values('epoch');assert len(f)==60
  assert np.array_equal(f.epoch,np.arange(a.anchor,a.end,60)) and a.epoch>=a.end
  ny=pd.Timestamp(a.anchor,unit='s',tz='UTC').tz_convert('America/New_York');assert ny.hour==9 and ny.minute==30
  q=profile(f)
  for field in ['low','high','poc','val','vah','centroid','net_move','volume']:
   assert np.isclose(q[field],getattr(a,field),rtol=1e-10,atol=1e-7),(row['stage'],a.day,field,q[field],getattr(a,field))
  assert q['shape']==a.shape;profiles[a.day]=q
  counts[{1:'P',-1:'b',0:'D',9:'other'}[a.shape]]+=1
 seen=set()
 for a in s.itertuples():
  stamp=pd.Timestamp(a.epoch,unit='s',tz='UTC').tz_convert('America/New_York');minute=stamp.hour*60+stamp.minute
  day=int(stamp.strftime('%Y%m%d'));key=(day,a.module)
  assert key not in seen and 635<=minute<930;seen.add(key)
  assert a.epoch>=a.signal_bar+300 and a.signal_bar>=p[p.day==day].end.iloc[0]
  ix=lookup[int(a.signal_bar)];history=b.iloc[ix-21:ix+1];atr,v=context(history);r=b.iloc[ix]
  for field in ['open','high','low','close']:
   assert np.isclose(getattr(a,'signal_'+field),r[field],atol=1e-7)
  assert a.signal_volume==r.tick_volume and np.isclose(a.previous_close,history.close.iloc[-2],atol=1e-7)
  assert np.isclose(a.atr,atr,rtol=1e-10,atol=1e-7) and np.isclose(a.prior_volume,v,atol=1e-7)
  q=profiles[day];assert a.shape==q['shape']
  for field in ['poc','val','vah']:assert np.isclose(getattr(a,field),q[field],atol=1e-7)
  assert signal(r.to_dict(),a.previous_close,q,atr,v,a.module)==a.side
  stop=(q['val']-.1*atr if a.side>0 else q['vah']+.1*atr) if a.module==3 else (r.low-.1*atr if a.side>0 else r.high+.1*atr)
  target=a.entry_quote+2*(a.entry_quote-a.initial_sl) if a.module==3 else (q['poc'] if a.module==2 else (q['vah'] if a.side>0 else q['val']))
  # All three current broker CFD symbols quote to cents; rounding audited in native source.
  assert abs(a.initial_sl-stop)<=.006 and abs(a.initial_tp-target)<=.006
  assert a.side*(a.entry_quote-a.initial_sl)>0 and a.side*(a.initial_tp-a.entry_quote)>0
  assert a.quoted_risk<=a.requested_risk+.0050001
 failed=s[s.retcode!=10009]
 assert len(failed)==row['net']['entry_fail'] and len(s)==len(d)+len(failed),'Attempt/position accounting differs'
 assert (failed.retcode==10016).all(),'Unexplained execution failure'
 assert np.allclose(d.net_profit,d.gross_profit+d.commission+d.swap+d.fee,atol=.001)
 if len(d):
  d=d.sort_values('open_epoch');before=10000+np.r_[0,np.cumsum(d.net_profit.to_numpy())[:-1]]
  assert np.allclose(d.requested_risk,before*.01,atol=1e-5)
  assert (d.open_epoch.to_numpy()[1:]>=d.close_epoch.to_numpy()[:-1]).all(),'Overlapping positions'
  assert (abs(d.volume-d.closed_volume)<1e-8).all()
  assert d.open_epoch.min()>=pd.Timestamp(row['start'].replace('.','-'),tz='UTC').timestamp()
 assert abs(d.net_profit.sum()-row['net']['net_profit'])<.02
 return dict(stage=row['stage'],positions=len(d),signals=len(s),failed_entries=len(failed),profile_days=len(p),profile_counts=counts,profile_m1_bars=len(inputs),unique_m5_bars=len(b),real_volume_nonzero_bars=int((inputs.real_volume>0).sum()),max_filled_risk_to_budget=float((d.actual_risk/d.requested_risk).max()) if len(d) else None,carryovers=row['net']['carryovers'],boundary_closes=row['net']['boundary'],source_sha=sha(ROOT/'EA/Main.mqh'))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--asset');args=p.parse_args()
 stem=('SMOKE' if args.smoke else 'SUMMARY')+('-'+args.asset if args.asset else '')
 rows=load(ROOT/(stem+'.json'));out=[check(r) for r in rows]
 save(ROOT/(stem+' VERIFICATION.json'),out);print(json.dumps(out,indent=2))
