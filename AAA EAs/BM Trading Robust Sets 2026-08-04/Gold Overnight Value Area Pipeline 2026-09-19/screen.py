"""Frozen-family, causal bar approximation. Native ticks decide the final verdict.

This is NOT the MT5 result. Unknown intraminute paths are stop-first. Management
uses observations available at the minute open; fills/spreads are approximated.
"""
import itertools,json,math
from datetime import datetime,timezone
import numpy as np
from numba import njit
from data import ROOT,load,features,save,sha
from native import DEFAULT,WINDOWS,ident

@njit(cache=True)
def engine(m1,m5,days,start,end,stop_mode,min_r,entry_end,exit_min,target_r,be,trail,risk_percent=1.):
    # time, side, entry, exit, lots, net, cash risk, drawdown, close time,
    # initial stop, target, balance, ambiguity flag
    out=np.zeros((len(days),13));n=0;balance=10000.;peak=10000.;dd=0.;free_after=0.
    for d in days:
        midnight,opening,hi,lo,val,vah,poc,begin,finish=d
        if opening<start or opening>=end:continue
        deadline=midnight+entry_end*60;cutoff=midnight+exit_min*60
        for k in range(int(begin),int(finish)):
            t=m5[k,0]+300
            if t>=deadline or t>=cutoff:break
            if t<free_after:continue
            close=m5[k,4];side=1 if close>vah else (-1 if close<val else 0)
            if not side:continue
            j=np.searchsorted(m1[:,0],t)
            if j>=len(m1) or m1[j,0]>=cutoff:break
            ask=m1[j,1]+m1[j,6]*.001;bid=m1[j,1]
            entry=ask if side==1 else bid
            anchor=poc if stop_mode==1 else (val if side==1 else vah)
            sl=np.floor((anchor-side*.001)/.001+.5)*.001
            distance=side*(entry-sl)
            tp=hi if side==1 else lo
            if target_r>0:tp=entry+side*target_r*abs(entry-sl)
            tp=np.floor(tp/.001+.5)*.001
            valid=(sl<bid and tp>entry) if side==1 else (sl>ask and tp<entry)
            if not valid or distance<=0 or side*(tp-entry)/distance<min_r:break
            lots=min(200.,max(.01,math.ceil(balance*risk_percent/100/(distance*100)/.01-1e-10)*.01))
            cashrisk=distance*100*lots;initial_sl=sl;commission=5.5*lots
            entered=m1[j,0];exit_price=entry;exit_time=entered;ambiguous=0;trail_bar=-1
            for z in range(j,len(m1)):
                now=m1[z,0];spread=m1[z,6]*.001
                market=m1[z,1]+(spread if side==-1 else 0)
                # Gaps through the existing stop precede any management change.
                if side*(market-sl)<=0:
                    exit_price=market;exit_time=now;break
                if side*(market-tp)>=0:
                    exit_price=tp;exit_time=now;break
                if now>=cutoff or now>=end:
                    exit_price=market;exit_time=now;break
                progress=side*(market-entry)/distance
                candidate=sl
                if be>0 and progress>=be:
                    candidate=max(candidate,entry) if side==1 else min(candidate,entry)
                if trail>0 and progress>=1:
                    bar=np.searchsorted(m5[:,0],now,side='right')-1
                    if bar>0 and bar!=trail_bar:
                        trail_bar=bar
                        level=m5[bar-1,4]-side*trail*distance
                        candidate=max(candidate,level) if side==1 else min(candidate,level)
                candidate=np.floor(candidate/.001+.5)*.001
                if side*(candidate-sl)>0 and side*(market-candidate)>0:sl=candidate
                high=m1[z,2]+(spread if side==-1 else 0)
                low=m1[z,3]+(spread if side==-1 else 0)
                stop_hit=(low<=sl) if side==1 else (high>=sl)
                target_hit=(high>=tp) if side==1 else (low<=tp)
                if stop_hit:
                    exit_price=sl;exit_time=now+59;ambiguous=int(target_hit);break
                if target_hit:
                    # Mark adverse excursion before the TP; do not include prices after exit.
                    adverse=low if side==1 else high
                    eq=balance+side*(adverse-entry)*100*lots-commission
                    dd=max(dd,100*(peak-eq)/peak)
                    exit_price=tp;exit_time=now+59;break
                adverse=low if side==1 else high
                favorable=high if side==1 else low
                eq=balance+side*(adverse-entry)*100*lots-commission
                dd=max(dd,100*(peak-eq)/peak)
                peak=max(peak,balance+side*(favorable-entry)*100*lots-commission)
                exit_price=m1[z,4]+(spread if side==-1 else 0);exit_time=now+59
            net=side*(exit_price-entry)*100*lots-commission
            balance+=net;dd=max(dd,100*(peak-balance)/peak);peak=max(peak,balance)
            out[n]=np.array([entered,side,entry,exit_price,lots,net,cashrisk,dd,exit_time,initial_sl,tp,balance,ambiguous])
            n+=1;free_after=exit_time
            break # One consumed signal per NY day, including invalid geometry.
    return out[:n]

_bars=None
def bars():
    global _bars
    if _bars is None:
        _bars=tuple(np.column_stack([b[n] for n in ('time','open','high','low','close','tick_volume','spread')]).astype(float) for b in load())
    return _bars

def stamp(s):return int(datetime.strptime(s.replace('-','.'),'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
def metrics(a):
    if not len(a):return dict(trades=0,return_pct=0.,win_rate_pct=0.,profit_factor=0.,max_drawdown_pct=0.,net_profit=0.,ambiguous_minutes=0)
    p=a[:,5];wins=p[p>0].sum();loss=-p[p<0].sum()
    return dict(trades=len(a),return_pct=float(p.sum()/100),win_rate_pct=float(np.mean(p>0)*100),profit_factor=float(wins/loss) if loss else 99.,max_drawdown_pct=float(a[:,7].max()),net_profit=float(p.sum()),ambiguous_minutes=int(a[:,12].sum()))

def simulate(c,window,return_trades=False):
    start,end=WINDOWS[window] if isinstance(window,str) else window
    m1,m5=bars();d=features(c['bins'],c['va'])
    a=engine(m1,m5,d,stamp(start),stamp(end),c['stop'],c['min_r'],c['entry_end'],c['exit'],c['target_r'],c['be'],c['trail'])
    return a if return_trades else metrics(a)

def score(m,minimum=300):
    base=30*math.log(max(.05,min(3.,m['profit_factor'])))+2*m['return_pct']/max(1,m['max_drawdown_pct'])-.5*m['max_drawdown_pct']
    return base-max(0,minimum-m['trades'])*.2

def diverse(rows,count=3):
    selected=[];seen=set()
    for r in sorted(rows,key=lambda r:r['score'],reverse=True):
        # Distinct stop / value-area geometry, not just a different histogram resolution.
        c=r['config'];group=(c['stop'],c['va'])
        if group in seen:continue
        selected.append(r);seen.add(group)
        if len(selected)==count:break
    return selected

def main():
    rows=[];known=set()
    for bins,va,stop,min_r,entry_end in itertools.product((32,64,96),(60,70,80),(0,1),(0.,.25,.5),(660,780,900)):
        c=dict(DEFAULT,bins=bins,va=va,stop=stop,min_r=min_r,entry_end=entry_end,exit=930)
        m=simulate(c,'train');rows.append(dict(stage='A',config=c,id=ident(c),training=m,score=score(m)));known.add(ident(c))
    parents=diverse(rows)
    save(ROOT/'stage-a.json',dict(rows=rows,parents=parents,selection='training only'))
    print('STAGE A',len(rows),'parents',[(r['id'],r['training']) for r in parents],flush=True)
    for parent in parents:
        for target,(be,trail) in itertools.product((0.,.5,1.,1.5),((0.,0.),(.5,0.),(0.,.5))):
            c=dict(parent['config'],target_r=target,be=be,trail=trail)
            if ident(c) in known:continue
            m=simulate(c,'train');rows.append(dict(stage='B',config=c,id=ident(c),training=m,score=score(m)));known.add(ident(c))
    finalists=diverse(rows)
    result=dict(approximation=True,selection='training only; no latest-year selection',rows=sorted(rows,key=lambda r:r['score'],reverse=True),finalists=finalists,raw_training=simulate(DEFAULT,'train'),source_sha256=sha(__import__('pathlib').Path(__file__)),protocol_sha256=sha(ROOT/'PROTOCOL.md'))
    save(ROOT/'screen-results.json',result);save(ROOT/'finalists-frozen.json',dict(finalists=finalists,screen_sha256=sha(ROOT/'screen-results.json'),frozen_utc=datetime.now(timezone.utc).isoformat()))
    print('FINALISTS',json.dumps(finalists,indent=2),flush=True)
    folds=[]
    for origin,end in [('2023.09.19','2024.03.19'),('2024.03.19','2024.09.19'),('2024.09.19','2025.03.19'),('2025.03.19','2025.09.19')]:
        start=str(int(origin[:4])-2)+origin[4:]
        # Only the predetermined Stage-A family: Stage-B parents were selected on later data.
        candidates=[]
        for r in rows:
            if r['stage']!='A':continue
            m=simulate(r['config'],(start,origin));candidates.append((score(m,200),r,m))
        _,best,train=max(candidates,key=lambda x:x[0]);oos=simulate(best['config'],(origin,end))
        folds.append(dict(start=start,origin=origin,end=end,config=best['config'],training=train,subsequent_6m=oos))
        print('WALK FORWARD',origin,oos,flush=True)
    save(ROOT/'walk-forward-screen.json',dict(approximation=True,folds=folds,limitations='Stage-A fixed family only; chronological but final choice of research family informed by prior latest-year raw inspection. Not untouched OOS.'))

if __name__=='__main__':main()
