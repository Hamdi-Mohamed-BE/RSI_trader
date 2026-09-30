"""Independent reconstruction from pre-existing M1 archive, not EA diagnostic variables."""
from pathlib import Path
import pandas as pd
import numpy as np
import json
import study as s
from verify_signals import rows
ROOT=Path(__file__).resolve().parent
def main():
 base=ROOT.parent
 paths=[base/'AAA Final EAs/AAA Final US100 Asia London Continuation EA/Research/data/Exness-USTEC-M1-2026.csv.gz',base/'Stock Auction Market Research Exness 2026-08-14/Data/Exness-SP500-US500-M1-2026.csv.gz']
 data=[]
 for p in paths:
  f=pd.read_csv(p);f.index=pd.to_datetime(f.pop('time'),utc=True)
  data.append(f[['open','high','low','close']].resample('3min',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna())
 n,sp=data;end=min(n.index.max(),sp.index.max());out=[];checked=0;miss=[]
 for path in sorted((ROOT/'native').glob('*/signals.csv.gz')):
  if not (path.parent/'run.json').exists():continue
  for raw in rows(path):
   x={k:float(v) for k,v in raw.items()};tm=pd.Timestamp(x['end'],unit='s',tz='UTC');hr=pd.Timestamp(x['hour_start'],unit='s',tz='UTC');h4=pd.Timestamp(x['h4_start'],unit='s',tz='UTC')
   if tm-pd.Timedelta(minutes=3)>end or tm<n.index.min()+pd.Timedelta(days=2):continue
   ns=n.loc[(n.index>=hr)&(n.index<tm)];ss=sp.loc[(sp.index>=hr)&(sp.index<tm)]
   prior=n.loc[(n.index>=hr-pd.Timedelta(hours=1))&(n.index<hr)]
   sprior=sp.loc[(sp.index>=hr-pd.Timedelta(hours=1))&(sp.index<hr)]
   p4=n.loc[(n.index>=h4-pd.Timedelta(hours=4))&(n.index<h4)]
   sp4=sp.loc[(sp.index>=h4-pd.Timedelta(hours=4))&(sp.index<h4)]
   current=n.loc[(n.index>=h4)&(n.index<tm)];scurrent=sp.loc[(sp.index>=h4)&(sp.index<tm)]
   expected=dict(close=ns.close.iloc[-1],nh=prior.high.max(),nl=prior.low.min(),sh=sprior.high.max(),sl=sprior.low.min(),
    ch=ns.high.max(),cl=ns.low.min(),csh=ss.high.max(),csl=ss.low.min(),n4h=p4.high.max(),n4l=p4.low.min(),s4h=sp4.high.max(),s4l=sp4.low.min(),
    c4h=current.high.max(),c4l=current.low.min(),cs4h=scurrent.high.max(),cs4l=scurrent.low.min())
   gt=pd.Timestamp(x['gap_time'],unit='s',tz='UTC')-pd.Timedelta(minutes=3);ga=n.loc[gt];gb=n.loc[gt-pd.Timedelta(minutes=6)]
   expected.update(gap_lo=gb.high if x['side']<0 else ga.high,gap_hi=ga.low if x['side']<0 else gb.low)
   bad={k:[float(v),x[k]] for k,v in expected.items() if abs(v-x[k])>.011}
   out.append(dict(case=path.parent.name,group=int(x['group']),time=tm.isoformat(),differences=bad));checked+=len(expected)
   if bad:miss.append(out[-1])
 result=dict(independent_archive_sha={p.name:s.sha(p) for p in paths},latest_common_bar=end.isoformat(),decisions=len(out),numeric_comparisons=checked,mismatching_decisions=len(miss),mismatches=miss)
 s.save('HISTORY_AUDIT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('mismatches','independent_archive_sha')},indent=2))
 if miss:print(json.dumps(miss[:3],indent=2))
if __name__=='__main__':main()

