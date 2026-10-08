"""Independent cached-M1 reconstruction of the frozen pre-release features."""
from pathlib import Path
import pandas as pd,numpy as np
import runner as r
R=r.R;D=R.parent/'AAA Final EAs/AAA Final US100 Asia London Continuation EA/Research/data'

def main():
 files=sorted(D.glob('Exness-USTEC-M1-*.csv.gz'))
 dec=pd.read_csv(R/'native/raw-5y/0-decisions.csv.gz');dec=dec[dec.reason=='event_start']
 comparisons=[]
 used=[]
 for path in files:
  year=int(path.name.split('-')[-1].split('.')[0])
  annual=dec[pd.to_datetime(dec.event_epoch,unit='s').dt.year==year]
  if annual.empty:continue
  m1=pd.read_csv(path,usecols=['time','open','high','low','close'])
  m1['time']=pd.to_datetime(m1.time,utc=True);m1=m1.drop_duplicates('time').sort_values('time').set_index('time')
  m5=m1.resample('5min').agg(dict(open='first',high='max',low='min',close='last')).dropna()
  prev=m5.close.shift(1)
  tr=pd.concat([m5.high-m5.low,(m5.high-prev).abs(),(m5.low-prev).abs()],axis=1).max(axis=1)
  atr=tr.rolling(14).mean();used.append(path)
  for x in annual.itertuples():
   before=pd.Timestamp(x.event_epoch-60,unit='s',tz='UTC')
   aindex=pd.Timestamp(x.event_epoch-300,unit='s',tz='UTC')
   if before not in m1.index or aindex not in atr.index:continue
   fair=float(m1.loc[before,'close']);av=float(atr.loc[aindex])
   comparisons.append(dict(event_epoch=int(x.event_epoch),fair_native=float(x.fair),fair_cached=fair,
    atr_native=float(x.pre_atr),atr_cached=av,fair_match=abs(x.fair-fair)<.011,atr_match=abs(x.pre_atr-av)<.002))
 result=dict(scope='Independent reconstruction from the existing Exness UTC M1 cache: exact pre-news M1 close and simple 14-bar M5 true-range average. This verifies features where cache and native historical archive overlap, not tick fills.',
  observations=len(comparisons),fair_matches=sum(x['fair_match'] for x in comparisons),atr_matches=sum(x['atr_match'] for x in comparisons),
  comparisons=comparisons,sources=[dict(path=str(p),sha256=r.sha(p)) for p in used])
 r.save(R/'FEATURE-VERIFICATION.json',result)
 print({k:v for k,v in result.items() if k not in ['comparisons','sources']})
 return result

if __name__=='__main__':main()
