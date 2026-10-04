import gzip,io,json
import numpy as np
import pandas as pd
from native import ROOT,OUT,load,save,ledger
def read(r,s):return pd.read_csv(io.BytesIO(gzip.decompress((OUT/r['stage']/f"0-{s}.csv.gz").read_bytes())))
def check(r):
 assert r['clean'] and r['net']['tick_errors']==0,'Execution/tick-copy problem'
 d=ledger(r);s=read(r,'signals');t=read(r,'ticks');ny=pd.to_datetime(s.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
 assert not ny.dt.date.duplicated().any();assert len(d)==len(s)
 assert (s.retcode==10009).all() and (s.side==1).all()
 assert ((ny.dt.hour*60+ny.dt.minute>=545)&(ny.dt.hour*60+ny.dt.minute<840)).all()
 groups={k:g for k,g in t.groupby('signal_bar',sort=False)}
 for a in s.itertuples():
  g=groups[a.signal_bar];bids=np.r_[a.previous_bid_seed,g.bid.to_numpy()];diff=np.diff(bids)
  assert int((diff>0).sum())==a.up_ticks and int((diff<0).sum())==a.down_ticks
  assert a.up_ticks-a.down_ticks>=200
  assert (g.time_msc>=a.signal_bar*1000).all() and (g.time_msc<(a.signal_bar+300)*1000).all()
  assert a.epoch>=a.signal_bar+300 and a.signal_close>a.range_high and a.initial_sl==a.range_low
  assert abs((a.initial_tp-a.entry_quote)-(a.entry_quote-a.initial_sl))<.011
  assert a.quoted_risk<=a.requested_risk+.00500001
 assert np.allclose(d.net_profit,d.gross_profit+d.commission+d.swap+d.fee,atol=.001)
 assert np.allclose(d.requested_risk,(10000+np.r_[0,np.cumsum(d.net_profit.to_numpy())[:-1]])*.01,atol=.00001)
 return {'stage':r['stage'],'positions':len(d),'quote_ticks_recounted':len(t),'max_filled_risk_to_budget':float((d.actual_risk/d.requested_risk).max()) if len(d) else None,'native_history_quality':r['native_metrics']['history_quality'],'opening_range_snapshot_only':True}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');args=p.parse_args()
 out=[check(r) for r in load(ROOT/('SMOKE.json' if args.smoke else 'SUMMARY.json'))];save(ROOT/('SMOKE VERIFICATION.json' if args.smoke else 'VERIFICATION.json'),out);print(json.dumps(out,indent=2))
