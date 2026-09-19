"""Approximate conservative M1 screening. Final evidence is always native MT5."""
import argparse,itertools,json,math,random,time
from datetime import datetime,timezone
import numpy as np
from numba import njit
from params import *
from data import load,signals,verify_raw

@njit(cache=True)
def simulate(h,m,starts,ends,roll,sig,atr,first,last,risk,weights,stops,rr,management,trigger,trail,commission,swaplot,extra=0.):
    balance=10000.;peak=balance;dd=0.;minimum=balance;count=0;wins=0;gp=0.;gl=0.;fees=0.;swaps=0.;overshoot=0.;concurrent=0
    side=np.zeros(3,np.int64);entry=np.zeros(3);sl=np.zeros(3);tp=np.zeros(3);vol=np.zeros(3);initialrisk=np.zeros(3);tradecost=np.zeros(3)
    years=np.zeros(10);last_close=0.;last_spread=0.;maxmargin=0.
    for i in range(first,last):
        a=starts[i];b=ends[i]
        if a>=b:continue
        for j in range(a,b):
            bid=m[j,1];spread=m[j,5]*.001+extra;ask=bid+spread;last_close=m[j,4];last_spread=spread
            # Rollover belongs only to positions already open before this minute.
            for e in range(3):
                if side[e]>0 and roll[j]>0:
                    charge=math.floor(swaplot*vol[e]*roll[j]*100+.5)/100;balance-=charge;tradecost[e]-=charge;swaps-=charge
            # Existing stops can gap at the first quote before any new H1 management.
            for e in range(3):
                if side[e]==0:continue
                price=bid if side[e]>0 else ask;reason=0
                if side[e]*(price-sl[e])<=0:reason=1
                elif side[e]*(price-tp[e])>=0:reason=2
                if reason:
                    gross=side[e]*(price-entry[e])*100*vol[e];fee=math.floor(commission*.5*vol[e]*100+.5)/100
                    net=gross+tradecost[e]-fee;balance+=gross-fee;fees-=fee;count+=1
                    if net>0:wins+=1;gp+=net
                    else:gl-=net
                    yr=max(0,min(9,int(h[i,6])));years[yr]+=net;side[e]=0
            if j==a:
                # Closed-H1 management only; no intra-minute lookahead trailing.
                for e in range(3):
                    if side[e]==0 or management==0:continue
                    if side[e]*(h[i-1,4]-entry[e])<trigger*initialrisk[e]:continue
                    nxt=sl[e]
                    if management==1 or management==3:
                        nxt=max(nxt,entry[e]) if side[e]>0 else min(nxt,entry[e])
                    if management==2 or management==3:
                        cand=h[i-1,4]-side[e]*trail*atr[i-1]
                        nxt=max(nxt,cand) if side[e]>0 else min(nxt,cand)
                    nxt=(math.floor(nxt*1000+1e-9) if side[e]>0 else math.ceil(nxt*1000-1e-9))/1000
                    price=bid if side[e]>0 else ask
                    if side[e]*(price-nxt)>.002:sl[e]=nxt
                for e in range(3):
                    direction=sig[i-1,e]
                    if side[e]!=0 or direction==0 or weights[e]<=0:continue
                    eq=balance
                    for k in range(3):
                        if side[k]!=0:eq+=side[k]*((bid if side[k]>0 else ask)-entry[k])*100*vol[k]
                    if eq<=0:continue
                    price=ask if direction>0 else bid;distance=max(stops[e]*atr[i-1],.002+spread)
                    stop=price-direction*distance
                    stop=(math.floor(stop*1000+1e-9) if direction>0 else math.ceil(stop*1000-1e-9))/1000
                    distance=abs(price-stop);lots=max(.01,math.ceil(eq*risk*weights[e]/100/(100*distance)/.01-1e-9)*.01);lots=min(200.,lots)
                    margin=0.
                    for k in range(3):
                        if side[k]!=0:margin+=vol[k]*100*price/2000
                    margin+=lots*100*price/2000;maxmargin=max(maxmargin,margin)
                    if margin>eq:continue
                    side[e]=direction;entry[e]=price;sl[e]=stop;initialrisk[e]=distance;vol[e]=lots
                    target=price+direction*distance*rr[e]
                    tp[e]=(math.ceil(target*1000-1e-9) if direction>0 else math.floor(target*1000+1e-9))/1000
                    fee=math.floor(commission*.5*lots*100+.5)/100;balance-=fee;fees-=fee;tradecost[e]=-fee
                    overshoot=max(overshoot,100*lots*100*distance/eq)
                concurrent=max(concurrent,np.count_nonzero(side))
            # Worst/best simultaneous portfolio equity at this bar's bid extrema.
            eqlo=balance;eqhi=balance
            for e in range(3):
                if side[e]!=0:
                    flo=min(sl[e],tp[e]);ceil=max(sl[e],tp[e])
                    plo=max(flo,min(ceil,m[j,3]+(spread if side[e]<0 else 0)))
                    phi=max(flo,min(ceil,m[j,2]+(spread if side[e]<0 else 0)))
                    eqlo+=side[e]*(plo-entry[e])*100*vol[e]
                    eqhi+=side[e]*(phi-entry[e])*100*vol[e]
            loweq=min(eqlo,eqhi);higheq=max(eqlo,eqhi);minimum=min(minimum,loweq)
            peak=max(peak,higheq)
            if peak>0:dd=max(dd,100*(peak-loweq)/peak)
            for e in range(3):
                if side[e]==0:continue
                stop_hit=(m[j,3]<=sl[e]) if side[e]>0 else (m[j,2]+spread>=sl[e])
                target_hit=(m[j,2]>=tp[e]) if side[e]>0 else (m[j,3]+spread<=tp[e])
                if not stop_hit and not target_hit:continue
                price=sl[e] if stop_hit else tp[e] # deliberately pessimistic same-minute order
                gross=side[e]*(price-entry[e])*100*vol[e];fee=math.floor(commission*.5*vol[e]*100+.5)/100
                net=gross+tradecost[e]-fee;balance+=gross-fee;fees-=fee;count+=1
                if net>0:wins+=1;gp+=net
                else:gl-=net
                yr=max(0,min(9,int(h[i,6])));years[yr]+=net;side[e]=0
    for e in range(3):
        if side[e]!=0:
            price=last_close+(last_spread if side[e]<0 else 0);gross=side[e]*(price-entry[e])*100*vol[e];fee=math.floor(commission*.5*vol[e]*100+.5)/100
            net=gross+tradecost[e]-fee;balance+=gross-fee;fees-=fee;count+=1
            if net>0:wins+=1;gp+=net
            else:gl-=net
    return np.array([balance-10000,count,100*wins/count if count else 0,gp/gl if gl>0 else 0,dd,minimum,fees,swaps,overshoot,concurrent,np.count_nonzero(years>0),np.min(years),maxmargin])

def measure(d,c,window):
    c=normalize(c);sig,atr=signals(d,c);start,end=[datetime.strptime(t,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp() for t in window]
    a,b=np.searchsorted(d['h'][:,0],[start,end]);names=['Momentum','Change','Breakout']
    weights=np.array([c['Inp'+n+'RiskWeight'] for n in names]);stops=np.array([c['Inp'+n+'StopATR'] or c['InpStopATR'] for n in names]);rr=np.array([c['Inp'+n+'RR'] or c['InpRewardRisk'] for n in names])
    x=simulate(d['h'],d['m'],d['starts'],d['ends'],d['roll'],sig,atr,int(a),int(b),c['InpRiskPerEnginePercent'],weights,stops,rr,c['InpManagement'],c['InpTriggerR'],c['InpTrailATR'],5.5,53.49)
    keys=['net_profit','trades','win_rate','net_pf','dd_pct','minimum_equity','commission','swap','max_trade_risk_pct','max_concurrent','positive_years','worst_year_net','max_margin']
    r=dict(zip(keys,map(float,x)));r['return_pct']=r['net_profit']/100;r['config']=c;r['id']=ident(c);r['window']=window;r['source']='approximate M1 screening'
    r['score']=score(r,window==VALID);return r

def score(r,validation=False):
    n=r['trades'];minimum=15 if validation else 45
    if n<minimum:return -10000+n
    pf=max(.01,min(4,r['net_pf'] or .01));ret=r['return_pct'];dd=max(1,r['dd_pct'])
    return 30*math.log(pf)+2*ret/dd+.12*ret-.55*dd+.9*r['positive_years']-.2*max(0,(30 if validation else 90)-n)

def stage_engine(d,e):
    path=ROOT/'Search'/f'engine{e}.json'
    if path.exists():return json.loads(path.read_text())
    rng=random.Random(3091300+e);keys=COMMON+ENGINE[e];configs={}
    while len(configs)<1536:
        c=normalize({**{k:rng.choice(SPACE[k]) for k in keys},'InpEngine':e});configs[ident(c)]=c
    c=normalize({'InpEngine':e});configs[ident(c)]=c
    rows=[];done=set();started=time.time()
    for i,c in enumerate(configs.values()):
        r=measure(d,c,TRAIN);rows.append(r);done.add(r['id'])
        if i%100==0:print('SCREEN',e,i,len(configs),'elapsed',round(time.time()-started),flush=True)
    # Neighborhood refinement is train-only and deterministically defined.
    leaders=sorted(rows,key=lambda r:r['score'],reverse=True)[:6]
    for lead in leaders:
        for key in keys:
            for value in SPACE[key]:
                c={**lead['config'],key:value};keyid=ident(c)
                if keyid not in done:rows.append(measure(d,c,TRAIN));done.add(keyid)
    save(path,rows);print('ENGINE COMPLETE',e,len(rows),'best',max(r['score'] for r in rows),flush=True)
    return rows

def search():
    d=load();verify_raw(d);allrows={e:stage_engine(d,e) for e in (1,2,3)};candidates={}
    # Combine independently selected legs with shared ATR/direction/management configuration.
    for atr,direction,management in itertools.product(SPACE['InpATRPeriod'],SPACE['InpDirection'],SPACE['InpManagement']):
        selected=[]
        for e in (1,2,3):
            pool=[r for r in allrows[e] if r['config']['InpATRPeriod']==atr and r['config']['InpDirection']==direction and r['config']['InpManagement']==management]
            selected.append(max(pool,key=lambda r:r['score']))
        c=normalize(dict(InpATRPeriod=atr,InpDirection=direction,InpManagement=management))
        # Use momentum's trigger/trailing common controls, evaluate the actual combination afresh.
        c['InpTriggerR']=selected[0]['config']['InpTriggerR'];c['InpTrailATR']=selected[0]['config']['InpTrailATR']
        for e,n,r in zip((1,2,3),('Momentum','Change','Breakout'),selected):
            for k in ENGINE[e]:c[k]=r['config'][k]
            c['Inp'+n+'StopATR']=r['config']['InpStopATR'];c['Inp'+n+'RR']=r['config']['InpRewardRisk']
        candidates[ident(c)]=c
    candidates[ident(DEFAULT)]=dict(DEFAULT)
    ranked=[]
    for i,c in enumerate(candidates.values()):
        t=measure(d,c,TRAIN);v=measure(d,c,VALID);rank=min(t['score'],v['score'])
        eligible=t['net_profit']>0 and v['net_profit']>0 and t['net_pf']>1.05 and v['net_pf']>1.05 and t['trades']>=60 and v['trades']>=20 and max(t['dd_pct'],v['dd_pct'])<=20
        ranked.append(dict(config=c,id=ident(c),train=t,validation=v,rank=rank,eligible=eligible))
        print('COMBINED SCREEN',i+1,len(candidates),'PF',round(t['net_pf'],2),round(v['net_pf'],2),flush=True)
    ranked.sort(key=lambda r:(r['eligible'],r['rank']),reverse=True)
    # Distinct signal structures, not four near-identical management settings.
    finalists=[];seen=set()
    for r in ranked:
        signature=tuple(r['config'][k] for e in (1,2,3) for k in ENGINE[e])+(r['config']['InpDirection'],r['config']['InpATRPeriod'])
        if signature in seen:continue
        seen.add(signature);finalists.append(r)
        if len(finalists)==4:break
    save(ROOT/'Search'/'combined.json',ranked);save(ROOT/'Search'/'finalists.json',finalists)
    save(ROOT/'Search'/'counts.json',dict(engine_runs={e:len(r) for e,r in allrows.items()},combined_configs=len(ranked),split_runs=2*len(ranked),seed=3091300,holdout_used=False))
    print('SEARCH FINISHED. FOUR NATIVE FINALISTS FROZEN.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');a=p.parse_args()
    if a.baseline:
        d=load();print(json.dumps(measure(d,DEFAULT,WINDOWS['5y']),indent=2))
    else:search()
