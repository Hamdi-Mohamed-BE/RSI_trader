"""Bounded family search on native-exported bid/ask paths, not native optimization."""
import argparse, json, os
from pathlib import Path
os.environ.setdefault('NUMBA_NUM_THREADS','6')
import numpy as np
import pandas as pd
from numba import njit, prange
from research import ROOT, ASSETS, settings, save

@njit(cache=True)
def event(q,epoch,p,point,commission,extra_spread=0.,slip=0.,delay=0.):
 out=np.zeros(10)
 if len(q)==0:return out
 at=np.searchsorted(q[:,0],epoch-p[0]*1000+delay)
 if at>=len(q) or q[at,0]>=epoch:return out
 finish=epoch+p[7]*1000
 bid=q[at,1]-extra_spread/2;ask=q[at,2]+extra_spread/2
 high=ask;low=bid
 if p[1]==1:high=q[at,3]+ask-bid;low=q[at,4]
 if p[1]==2:high=q[at,5]+ask-bid;low=q[at,6]
 pending=np.array([np.round((high+p[2])/point)*point,np.round((low-p[2])/point)*point])
 stops=np.array([np.round((pending[0]-p[3])/point)*point,np.round((pending[1]+p[3])/point)*point])
 targets=np.array([np.round((pending[0]+p[4]*p[3])/point)*point,np.round((pending[1]-p[4]*p[3])/point)*point])
 state=np.zeros(2,np.int64);opened=np.zeros(2);leg=np.zeros(2)
 if pending[0]<=ask:state[0]=3
 if pending[1]>=bid:state[1]=3
 peak=0.;loweq=0.;higheq=0.;drawdown=0.;cash=0.
 for j in range(at+1,len(q)):
  tm=q[j,0];bid=q[j,1]-extra_spread/2;ask=q[j,2]+extra_spread/2
  for side in range(2):
   sign=1 if side==0 else -1
   trigger=ask if side==0 else bid;exitprice=bid if side==0 else ask
   if state[side]==0 and tm<finish and sign*(trigger-pending[side])>=-point*1e-6:
    opened[side]=trigger+sign*slip;state[side]=1;cash-=commission;leg[side]-=commission;out[4]+=1
   if state[side]==1:
    close=False;price=exitprice
    if sign*(exitprice-stops[side])<=point*1e-6:price=exitprice-sign*slip;close=True
    elif p[4]>0 and sign*(exitprice-targets[side])>=-point*1e-6:price=targets[side];close=True
    elif tm>=finish:price=exitprice-sign*slip;close=True
    if close:
     gain=sign*(price-opened[side]);cash+=gain;leg[side]+=gain;state[side]=2
     if leg[side]>0:out[5]+=1;out[6]+=leg[side]
     else:out[7]-=leg[side]
  eq=cash
  for side in range(2):
   if state[side]==1:eq+=(1 if side==0 else -1)*((bid if side==0 else ask)-opened[side])
  peak=max(peak,eq);drawdown=max(drawdown,peak-eq);loweq=min(loweq,eq);higheq=max(higheq,eq)
  if p[5]>0:
   for side in range(2):
    if state[side]!=1:continue
    sign=1 if side==0 else -1;price=bid if side==0 else ask
    if sign*(price-opened[side])+point>=p[5]*p[3]:
     candidate=np.round((price-sign*p[6])/point)*point
     if sign*(candidate-stops[side])>point:stops[side]=candidate
  if tm>=finish:break
 out[0]=cash;out[1]=loweq;out[2]=higheq;out[3]=drawdown;out[8]=leg[0];out[9]=leg[1]
 return out

@njit(parallel=True,cache=True)
def batch(data,offsets,epochs,configs,point,commission,spread=0.,slip=0.,delay=0.):
 result=np.zeros((len(configs),len(epochs),10))
 for c in prange(len(configs)):
  for i in range(len(epochs)):
   result[c,i]=event(data[offsets[i]:offsets[i+1]],epochs[i],configs[c],point,commission,spread,slip,delay)
 return result

def load(asset):
 folder=ROOT/asset;events=json.loads((ROOT/'calendar.json').read_text());spec=json.loads((folder/'spec.json').read_text())
 spec={k:(v if k=='currency' else float(v)) for k,v in spec.items()}
 assert spec['currency']=='USD' and spec['contract']>0
 path=folder/'quote-arrays.npz'
 if path.exists():
  d=np.load(path);data,offsets,epochs=d['data'],d['offsets'],d['epochs']
 else:
  q=pd.read_csv(folder/'quotes.csv',sep=';')
  counts=q.groupby('event').size().reindex(range(len(events)),fill_value=0).to_numpy()
  offsets=np.r_[0,np.cumsum(counts)]
  data=q.iloc[:,1:].to_numpy(float);epochs=np.array([e['epoch']*1000 for e in events],float)
  assert np.all(np.diff(q.event)>=0) and np.all(np.diff(data[:,0])>=0)
  assert np.all(data[:,2]>=data[:,1]) and np.all(data[:,1:3]>0)
  np.savez_compressed(path,data=data,offsets=offsets,epochs=epochs)
 native=json.loads((ROOT/'native'/(asset+'Baseline')/'trades.json').read_text())
 assert native,'No native baseline fills to calibrate costs'
 fees=np.array([abs(t['commission'])/t['volume']/spec['contract'] for t in native])
 spec['commission_price_units']=float(np.median(fees))
 spec['commission_range_price_units']=[float(min(fees)),float(max(fees))]
 assert all(abs(t['swap'])<.001 for t in native),'Nonzero swaps need additional model'
 save(folder/'cost-model.json',spec)
 return events,data,offsets,epochs,spec

def baseline(asset):
 s=settings(asset)
 return np.array([float(s['InpPlacementLeadSeconds']),0,float(s['InpEntryOffsetPrice']),float(s['InpStopLossPrice']),0,float(s['InpTrailStartR']),float(s['InpTrailDistancePrice']),float(s['InpForceCloseSecondsAfterEvent'])])

def portfolio(results,params,spec,indices=None):
 balance=peak=10000.;dd=0.;wins=trades=0;positive=negative=0.;riskmax=0.
 for i,r in enumerate(results):
  if indices is not None and i not in indices:continue
  p=params[i] if params.ndim==2 else params
  raw=balance*.0075/(spec['contract']*p[3])
  lots=max(spec['lot_min'],min(spec['lot_max'],np.ceil((min(raw,spec['lot_max'])-1e-12)/spec['lot_step'])*spec['lot_step']))
  mult=lots*spec['contract']
  # Intrabar envelope approximation; native MT5 equity drawdown is authoritative.
  dd=max(dd,100*(peak-(balance+r[1]*mult))/peak,100*r[3]*mult/max(peak,balance+r[2]*mult))
  peak=max(peak,balance+r[2]*mult);balance+=r[0]*mult
  wins+=r[5];trades+=r[4];positive+=r[6]*mult;negative+=r[7]*mult
  riskmax=max(riskmax,lots*spec['contract']*p[3])
  if balance<=0:break
 return dict(balance=round(balance,2),return_pct=(balance-10000)/100,dd=dd,trades=int(trades),win_rate=100*wins/trades if trades else 0,pf=positive/negative if negative else None,max_side_risk_usd=riskmax)

def configs(asset,n=6000):
 rng=np.random.default_rng(20260919);base=baseline(asset);u=ASSETS[asset]['unit']
 space=[[5,10,15,30,45,60,90,120],[0,1,2],[u*x for x in [.5,1,2,3,4,6,8,10,12,15,20]],[u*x for x in [1,2,3,4,6,8,10,12,15,20]],[0]+list(np.arange(.5,8.01,.5)),[0,.5,1,1.5,2,3],[u*x for x in [1,2,3,4,6,8,10,15,20]],[60,120,180,300,600]]
 rows=[base.tolist()]
 for col,values in enumerate(space):
  for v in values:p=base.copy();p[col]=v;rows.append(p.tolist())
 for _ in range(n):rows.append([float(rng.choice(v)) for v in space])
 candidates=np.unique(np.array(rows),axis=0)
 return candidates,space

def quality(asset,events,data,offsets,spec):
 rows=[];worst=0.
 for i,(a,b) in enumerate(zip(offsets[:-1],offsets[1:])):
  q=data[a:b]
  row=dict(kind=events[i]['kind'],release_utc=events[i]['release_utc'],quotes=len(q))
  if len(q):
   row.update(first_msc=q[0,0],last_msc=q[-1,0],max_gap_ms=float(np.max(np.diff(q[:,0]))) if len(q)>1 else 0,median_spread=float(np.median(q[:,2]-q[:,1])),p99_spread=float(np.quantile(q[:,2]-q[:,1],.99)))
   minute=q[:,0]//60000
   for m in np.unique(minute)[1:]:
    r=q[minute==m]
    worst=max(worst,float(np.max(np.abs(np.maximum.accumulate(r[:,1])-r[:,3]))),float(np.max(np.abs(np.minimum.accumulate(r[:,1])-r[:,4]))))
  rows.append(row)
 result=dict(events=rows,max_active_candle_discrepancy=worst,point=spec['point'],causal_active_candle_pass=worst<=spec['point']*1.1)
 save(ROOT/asset/'data-quality.json',result)
 assert result['causal_active_candle_pass'],result

def main(asset,n=6000):
 folder=ROOT/asset;events,data,offsets,epochs,spec=load(asset);quality(asset,events,data,offsets,spec)
 p,space=configs(asset,n);base=baseline(asset);u=ASSETS[asset]['unit']
 save(folder/'search-space.json',dict(columns=['lead_seconds','anchor_0_quote_1_activeM1_2_closedM1','entry_offset_price','stop_price','tp_r_0_none','trail_start_r_0_off','trail_distance_price','close_seconds_after_event'],values=space,candidate_count=len(p),seed=20260919,risk_per_side_percent=.75,holdout_from='2026-05-19',selection='Top 100 raw return minus twice approximate DD, reranked with moderate cost stress',stress=dict(extra_spread=u*.25,adverse_slippage=u*.25,delay_ms=100),severe=dict(extra_spread=u*.5,adverse_slippage=u*.75,delay_ms=250)))
 print('SEARCH',asset,len(p),'configs',len(events),'events',len(data),'quotes',flush=True)
 rawbase=batch(data,offsets,epochs,np.array([base]),spec['point'],spec['commission_price_units'])[0]
 native=json.loads((ROOT/'native'/(asset+'Baseline')/'stats.json').read_text())
 sim=portfolio(rawbase,base,spec)
 parity=dict(simulated=sim,native=native,trade_count_difference=sim['trades']-native['trades'],cash_difference=sim['balance']-native['final_balance'])
 save(folder/'baseline-parity.json',parity);print('BASELINE PARITY',asset,json.dumps(parity),flush=True)
 result=batch(data,offsets,epochs,p,spec['point'],spec['commission_price_units'])
 np.savez_compressed(folder/'search-results.npz',configs=p,results=result)
 families=np.array([e['kind'] for e in events]);train=np.array([e['release_utc'][:10]<'2026-05-19' for e in events]);chosen={}
 for family in ('NFP','CPI','FOMC'):
  chosen[family]={}
  for label,mask in [('full',families==family),('train',(families==family)&train)]:
   ranking=[]
   for c in range(len(p)):
    stats=portfolio(result[c,mask],p[c],spec);score=stats['return_pct']-2*stats['dd']
    if stats['trades']<max(3,int(mask.sum()*.6)):score=-1e6
    ranking.append((score,c))
   top=[c for _,c in sorted(ranking,reverse=True)[:100]]
   stressed=batch(data,offsets,epochs,p[top],spec['point'],spec['commission_price_units'],u*.25,u*.25,100)
   robust=[]
   for j,c in enumerate(top):
    stats=portfolio(stressed[j,mask],p[c],spec);score=stats['return_pct']-2*stats['dd']
    if stats['trades']<max(3,int(mask.sum()*.6)):score=-1e6
    robust.append((score,c,stats))
   score,c,stressstats=max(robust,key=lambda x:x[0])
   chosen[family][label]=dict(index=int(c),params_price=p[c].tolist(),selection_score=score,base=portfolio(result[c,mask],p[c],spec),stress=stressstats,events=int(mask.sum()))
   leaderboard=[dict(score=s,index=int(i),params_price=p[i].tolist(),stress=st) for s,i,st in sorted(robust,key=lambda x:x[0],reverse=True)]
   save(folder/f'{family}-{label}-top100.json',leaderboard)
   print('SELECTED',asset,family,label,json.dumps(chosen[family][label]),flush=True)
 save(folder/'selected.json',chosen)
 comparisons={}
 for name in ('baseline','full','train'):
  ps=np.array([base if name=='baseline' else chosen[e['kind']][name]['params_price'] for e in events])
  paths=np.array([event(data[offsets[i]:offsets[i+1]],epochs[i],ps[i],spec['point'],spec['commission_price_units']) for i in range(len(events))])
  comparisons[name]=dict(full=portfolio(paths,ps,spec),holdout=portfolio(paths,ps,spec,set(np.flatnonzero(~train))));np.savez_compressed(folder/f'{name}-paths.npz',params=ps,paths=paths)
  for label,sp,sl,de in [('stress',u*.25,u*.25,100),('severe',u*.5,u*.75,250)]:
   paths=np.array([event(data[offsets[i]:offsets[i+1]],epochs[i],ps[i],spec['point'],spec['commission_price_units'],sp,sl,de) for i in range(len(events))])
   comparisons[name][label]=portfolio(paths,ps,spec)
 save(folder/'screening-comparison.json',comparisons);print('COMPLETE',asset,json.dumps(comparisons),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--assets',default=','.join(ASSETS));ap.add_argument('--samples',type=int,default=6000);args=ap.parse_args()
 for a in args.assets.split(','):main(a,args.samples)
