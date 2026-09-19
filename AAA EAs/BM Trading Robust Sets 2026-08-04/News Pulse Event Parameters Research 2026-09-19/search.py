"""Bounded event-family search on exported native MT5 quote paths; not a native optimization."""
import json,os
from pathlib import Path
os.environ.setdefault('NUMBA_NUM_THREADS','6')
import numpy as np
import pandas as pd
from numba import njit,prange
ROOT=Path(__file__).resolve().parent
BASE=np.array([30,0,6,6,0,1.5,15,60],float)

@njit(cache=True)
def event(q,epoch,p,extra_spread=0.,slip=0.,delay=0.,fill_quote=True):
    # Output: net price units, min/max cumulative P/L, local drawdown, trades,
    # wins, gross positive/negative net price units, buy/sell net price units.
    out=np.zeros(10)
    if len(q)==0:return out
    begin=epoch-p[0]*1000;finish=epoch+p[7]*1000
    at=np.searchsorted(q[:,0],begin+delay)
    if at>=len(q) or q[at,0]>=epoch:return out
    bid=q[at,1]-extra_spread/2;ask=q[at,2]+extra_spread/2
    high=ask;low=bid
    if p[1]==1:high=q[at,3]+ask-bid;low=q[at,4]
    if p[1]==2:high=q[at,5]+ask-bid;low=q[at,6]
    pending=np.array([np.round(high+p[2],3),np.round(low-p[2],3)])
    stops=np.array([np.round(pending[0]-p[3],3),np.round(pending[1]+p[3],3)])
    targets=np.array([np.round(pending[0]+p[4]*p[3],3),np.round(pending[1]-p[4]*p[3],3)])
    state=np.zeros(2,np.int64);opened=np.zeros(2);leg=np.zeros(2)
    if pending[0]<=ask:state[0]=3
    if pending[1]>=bid:state[1]=3
    peak=0.;loweq=0.;high_eq=0.;drawdown=0.;cash=0.
    for j in range(at+1,len(q)):
        tm=q[j,0];bid=q[j,1]-extra_spread/2;ask=q[j,2]+extra_spread/2
        for side in range(2):
            sign=1 if side==0 else -1
            trigger=ask if side==0 else bid
            exitprice=bid if side==0 else ask
            if state[side]==0 and tm<finish and sign*(trigger-pending[side])>=0:
                opened[side]=(trigger if fill_quote else pending[side])+sign*slip
                state[side]=1;cash-=.055;leg[side]-=.055;out[4]+=1
            if state[side]==1:
                close=False;price=exitprice
                if sign*(exitprice-stops[side])<=0:
                    price=(exitprice if fill_quote else stops[side])-sign*slip;close=True
                elif p[4]>0 and sign*(exitprice-targets[side])>=0:
                    price=targets[side];close=True
                elif tm>=finish:
                    price=exitprice-sign*slip;close=True
                if close:
                    gain=sign*(price-opened[side]);cash+=gain;leg[side]+=gain;state[side]=2
                    if leg[side]>0:out[5]+=1;out[6]+=leg[side]
                    else:out[7]-=leg[side]
        eq=cash
        for side in range(2):
            if state[side]==1:eq+=(1 if side==0 else -1)*((bid if side==0 else ask)-opened[side])
        peak=max(peak,eq);drawdown=max(drawdown,peak-eq);loweq=min(loweq,eq);high_eq=max(high_eq,eq)
        # Native trailing is applied after broker stop/TP processing on the tick.
        if p[5]>0:
            for side in range(2):
                if state[side]!=1:continue
                sign=1 if side==0 else -1;price=bid if side==0 else ask
                if sign*(price-opened[side])+.001>=p[5]*p[3]:
                    candidate=np.round(price-sign*p[6],3)
                    if sign*(candidate-stops[side])>.001:stops[side]=candidate
        if tm>=finish:break
    out[0]=cash;out[1]=loweq;out[2]=high_eq;out[3]=drawdown;out[8]=leg[0];out[9]=leg[1]
    return out

@njit(parallel=True,cache=True)
def batch(data,offsets,epochs,configs,spread=0.,slip=0.,delay=0.,quote=True):
    result=np.zeros((len(configs),len(epochs),10))
    for c in prange(len(configs)):
        for i in range(len(epochs)):
            result[c,i]=event(data[offsets[i]:offsets[i+1]],epochs[i],configs[c],spread,slip,delay,quote)
    return result

def load():
    events=json.loads((ROOT/'calendar.json').read_text())
    path=ROOT/'quote-arrays.npz'
    if path.exists():
        d=np.load(path);return events,d['data'],d['offsets'],d['epochs']
    q=pd.read_csv(ROOT/'quotes.csv',sep=';')
    offsets=np.r_[0,np.cumsum([int((q.event==i).sum()) for i in range(len(events))])]
    data=q.iloc[:,1:].to_numpy(float)
    epochs=np.array([e['epoch']*1000 for e in events],float)
    assert np.all(np.diff(data[:,0])>=0)
    np.savez_compressed(path,data=data,offsets=offsets,epochs=epochs)
    return events,data,offsets,epochs

def portfolio(event_results,params,indices=None):
    balance=peak=10000.;dd=0.;wins=trades=0;positive=negative=0.;riskmax=0.
    for i,r in enumerate(event_results):
        if indices is not None and i not in indices:continue
        p=params[i] if params.ndim==2 else params
        lots=max(.01,np.ceil((balance*.0075/(100*p[3])-1e-12)/.01)*.01)
        mult=lots*100
        dd=max(dd,100*(peak-(balance+r[1]*mult))/peak,100*r[3]*mult/max(peak,balance+r[2]*mult))
        peak=max(peak,balance+r[2]*mult);balance+=r[0]*mult
        wins+=r[5];trades+=r[4];positive+=r[6]*mult;negative+=r[7]*mult
        riskmax=max(riskmax,lots*100*p[3])
    return dict(balance=round(balance,2),return_pct=(balance-10000)/100,dd=dd,trades=int(trades),win_rate=100*wins/trades if trades else 0,pf=positive/negative if negative else None,max_side_risk_usd=riskmax)

def configs(n=6000):
    rng=np.random.default_rng(20260919)
    space=[[5,10,15,30,45,60,90,120],[0,1,2],[1,2,3,4,6,8,10,12,15,20],[2,3,4,6,8,10,12,15,20],[0]+list(np.arange(.5,8.01,.5)),[0,.5,1,1.5,2,3],[2,3,4,6,8,10,15,20],[30,60,120,180,300,600]]
    rows=[BASE.tolist()]
    # Include simple one-coordinate changes around the installed baseline.
    for col,values in enumerate(space):
        for v in values:p=BASE.copy();p[col]=v;rows.append(p.tolist())
    for _ in range(n):rows.append([float(rng.choice(v)) for v in space])
    candidates=np.unique(np.array(rows),axis=0)
    # Native broker rejects sub-minute specified expirations. Keep only
    # event+60s or later, rather than silently accepting unplaceable orders.
    return candidates[candidates[:,7]>=60]

def main():
    events,data,offsets,epochs=load();p=configs()
    (ROOT/'search-space.json').write_text(json.dumps({'columns':['lead_seconds','anchor_0_quote_1_activeM1_2_closedM1','entry_offset_price','stop_price','tp_r_0_none','trail_start_r_0_off','trail_distance_price','hold_seconds'],'candidate_count':len(p),'seed':20260919,'holdout_from':'2026-05-19','risk_per_side_percent':.75,'both_pending_sides_retained':True},indent=2))
    print('SEARCH',len(p),'configs',len(events),'events',len(data),'quotes',flush=True)
    result=batch(data,offsets,epochs,p)
    np.savez_compressed(ROOT/'search-results.npz',configs=p,results=result)
    chosen={};families=np.array([e['kind'] for e in events]);train=np.array([e['release_utc'][:10]<'2026-05-19' for e in events])
    for k in ['NFP','CPI','FOMC']:
        chosen[k]={}
        for label,mask in [('full',families==k),('train',(families==k)&train)]:
            ranking=[]
            for c in range(len(p)):
                stats=portfolio(result[c,mask],p[c]);score=stats['return_pct']-2*stats['dd']
                if stats['trades']<max(3,int(mask.sum()*.6)):score=-1e6
                ranking.append((score,c))
            top=[c for _,c in sorted(ranking,reverse=True)[:100]]
            stressed=batch(data,offsets,epochs,p[top],.25,.25,100)
            robust=[]
            for j,c in enumerate(top):
                stats=portfolio(stressed[j,mask],p[c]);score=stats['return_pct']-2*stats['dd']
                robust.append((score,c,j,stats))
            score,c,j,stressstats=max(robust,key=lambda x:x[0])
            chosen[k][label]={'index':int(c),'params':p[c].tolist(),'selection_score_stressed_return_minus_2DD':score,'base':portfolio(result[c,mask],p[c]),'stress':stressstats,'events':int(mask.sum())}
            print(k,label,chosen[k][label],flush=True)
    (ROOT/'selected.json').write_text(json.dumps(chosen,indent=2))
    comparisons={}
    for name in ['baseline','full','train']:
        ps=np.array([BASE if name=='baseline' else chosen[e['kind']][name]['params'] for e in events])
        paths=np.array([event(data[offsets[i]:offsets[i+1]],epochs[i],ps[i]) for i in range(len(events))])
        comparisons[name]={'full':portfolio(paths,ps),'holdout':portfolio(paths,ps,set(np.flatnonzero(~train)))}
        for label,sp,sl,de in [('stress',.25,.25,100),('severe',.5,.75,250)]:
            paths=np.array([event(data[offsets[i]:offsets[i+1]],epochs[i],ps[i],sp,sl,de) for i in range(len(events))])
            comparisons[name][label]=portfolio(paths,ps)
    (ROOT/'screening-comparison.json').write_text(json.dumps(comparisons,indent=2));print(comparisons,flush=True)
if __name__=='__main__':main()
