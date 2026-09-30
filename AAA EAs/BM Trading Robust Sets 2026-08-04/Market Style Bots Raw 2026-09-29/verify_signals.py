"""Independent pandas/numpy signal oracle from the prior native-exported M5 archive."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent/'Intraday Bias Discovery 2026-09-29/data'

def hash32(x):
 x&=0xffffffff;x^=x>>16;x=(x*0x7feb352d)&0xffffffff;x^=x>>15;x=(x*0x846ca68b)&0xffffffff;x^=x>>16;return x
def oracle(frame,mode):
 assert len(frame)==400
 o,h,l,c=[frame[k].to_numpy(float) for k in ['open','high','low','close']]
 tr=np.maximum(h-l,np.maximum(abs(h-np.r_[c[0],c[:-1]]),abs(l-np.r_[c[0],c[:-1]])))
 e20,e50,e200=[pd.Series(c).ewm(span=s,adjust=False).mean().to_numpy() for s in [20,50,200]]
 atr=tr[-14:].mean();side=0;target=ratio=prob=0.;count=0
 if mode==0:
  if e50[-1]>e200[-1] and e50[-1]>e50[-6] and l[-2]<=e20[-2] and c[-1]>h[-2] and c[-1]>e20[-1]:side=1
  if e50[-1]<e200[-1] and e50[-1]<e50[-6] and h[-2]>=e20[-2] and c[-1]<l[-2] and c[-1]<e20[-1]:side=-1
 elif mode==1:
  shock=c[-2]-o[-2];prior=tr[-16:-2].mean()
  if abs(shock)>=2*prior:
   if shock>0 and c[-1]<o[-1] and c[-1]>e20[-1]:side=-1
   if shock<0 and c[-1]>o[-1] and c[-1]<e20[-1]:side=1
 elif mode==2:
  a=pd.Series(tr).rolling(14).mean()/pd.Series(tr).rolling(100).mean()
  state=np.where(a<.8,0,np.where(a>1.2,2,1));counts=np.zeros((3,3),int)
  for j in range(147,399):counts[state[j-1],state[j]]+=1
  count=int(counts[2].sum());prob=(counts[2,2]+1)/(count+3);ratio=float(a.iloc[-1])
  if state[-1]==2 and count>=20 and prob>=.55:
   if c[-1]>e50[-1] and e50[-1]>e50[-6] and c[-1]>h[-2]:side=1
   if c[-1]<e50[-1] and e50[-1]<e50[-6] and c[-1]<l[-2]:side=-1
 elif mode==3:
  mean=c[-22:-2].mean();sd=c[-22:-2].std(ddof=0);path=abs(np.diff(c[-21:])).sum();target=mean
  if sd>0 and path>0 and abs(c[-1]-c[-21])/path<.3 and abs(e50[-1]-e50[-6])<.25*atr:
   if c[-2]<mean-2*sd and mean-2*sd<=c[-1]<=mean+2*sd:side=1
   if c[-2]>mean+2*sd and mean-2*sd<=c[-1]<=mean+2*sd:side=-1
 return dict(side=side,atr=atr,target=target,ratio=ratio,prob=prob,count=count)

def main():
 cache={};checks=[];bad=[];n=0
 for path in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(path.read_text());symbol=r['bot']['symbol'];mode=r['bot']['mode']
  if symbol not in cache:
   native=ROOT/'data'/f'{symbol}-H1.csv.gz'
   if native.exists():cache[symbol]=pd.read_csv(native).set_index('time')
   else:
    f=SOURCE/f'{symbol}_M5.csv.gz';d=pd.read_csv(f);d['hour']=d.time//3600*3600
    cache[symbol]=d.groupby('hour').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
  bars=cache[symbol];sig=pd.read_csv(path.parent/'signals.csv.gz')
  for s in sig.itertuples():
   # 400 bars ending at the completed signal hour; no future row can enter this slice.
   i=bars.index.get_indexer([int(s.signal_time)])[0]
   if i<399:continue  # archival warmup absent for early 2021 entries; explicitly counted below
   v=oracle(bars.iloc[i-399:i+1],mode);n+=1
   side=1 if hash32(int(s.fill_time)//86400+290929)&1 else -1
   errs=[]
   if v['side']!=int(s.raw_side):errs.append('side')
   if not np.isclose(v['atr'],s.atr,rtol=1e-8,atol=1e-8):errs.append('ATR')
   if mode==2 and (not np.isclose(v['ratio'],s.vol_ratio,atol=1e-8) or not np.isclose(v['prob'],s.hot_probability,atol=1e-8) or v['count']!=s.hot_count):errs.append('regime')
   if mode==3 and not np.isclose(v['target'],s.mean_target,rtol=1e-8,atol=1e-8):errs.append('mean')
   if int(s.actual_side)!=(side if r['control'] else int(s.raw_side)):errs.append('control_direction')
   if not 3600<=int(s.fill_time)-int(s.signal_time)<3901:errs.append('completed_bar_timing')
   if errs:bad.append(dict(tag=r['tag'],time=int(s.signal_time),errors=errs,oracle=v,native=dict(side=s.raw_side,atr=s.atr,ratio=s.vol_ratio,prob=s.hot_probability,count=s.hot_count)))
  checks.append(dict(tag=r['tag'],signals=len(sig),oracle_checked=sum(bars.index.get_indexer([int(t)])[0]>=399 for t in sig.signal_time)))
 out=dict(checked=n,mismatches=bad,runs=checks,sources={s:hashlib.sha256(((ROOT/'data'/f'{s}-H1.csv.gz') if (ROOT/'data'/f'{s}-H1.csv.gz').exists() else SOURCE/f'{s}_M5.csv.gz').read_bytes()).hexdigest() for s in cache},note='Independent Python signal algorithm on native H1 data when available, otherwise prior M5 aggregation. Missing warmup is explicitly counted. No strategy parameters are fitted.')
 (ROOT/'SIGNAL_VERIFICATION.json').write_text(json.dumps(out,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
 print(json.dumps(dict(checked=n,mismatches=len(bad),first_mismatches=bad[:3]),default=str,indent=2))
 assert not bad,'Signal mismatch requires inspection before publishing results'

if __name__=='__main__':main()
