"""Shared-cash FTMO research. Stop-envelope approximation, not native FTMO equity."""
from __future__ import annotations
import argparse,math,random,statistics
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from prepare import ROOT,read,save,END,DAY,WEEK,RAW,SPECS,costs,iso
PRAGUE=ZoneInfo('Europe/Prague');NY=ZoneInfo('America/New_York')
CAPITAL=10000.;RISK=500/7
NEWS=['news-pulse-xau/standard','news-pulse-xag/standard']
def business(t,n):
    d=datetime.fromtimestamp(t,timezone.utc)
    while n:
        d+=timedelta(days=1)
        if d.weekday()<5:n-=1
    return d.timestamp()
def rounded(v):return max(.01,math.ceil(v/.01-1e-10)*.01)
def margin(sym,lot,price):
    contract,lev=SPECS[sym];return lot*contract*(1 if sym=='USDJPY' else price)/lev
def shifted_data(data,keys,start,end,sample=None,block_weeks=1):
    rr=[r for k in keys for r in data['rows'][k]]
    pp=[p for p in data['placements'] if p['key'] in keys]
    if sample is None:return [dict(r) for r in rr if start<=r['op']<end],[dict(p) for p in pp if start<=p['op']<end]
    anchor=datetime.fromtimestamp(start,timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    anchor=(anchor-timedelta(days=anchor.weekday())).timestamp()
    source=datetime(2026,3,9,tzinfo=timezone.utc).timestamp();out=[];places=[]
    for i,j in enumerate(sample):
        src=source+j*WEEK;target=anchor+i*block_weeks*WEEK
        so=datetime.fromtimestamp(src+2*DAY+43200,NY).utcoffset().total_seconds()
        to=datetime.fromtimestamp(target+2*DAY+43200,NY).utcoffset().total_seconds()
        offset=target-src+so-to
        for r in rr:
            if src<=r['op']<src+block_weeks*WEEK and start<=r['op']+offset<end:
                out.append(dict(r,op=r['op']+offset,cl=r['cl']+offset,event=r.get('event',0)+offset))
        for p in pp:
            if src<=p['op']<src+block_weeks*WEEK and start<=p['op']+offset<end:
                places.append(dict(p,op=p['op']+offset,until=p['until']+offset,epoch=p['epoch']+offset))
    return out,places
def replay(rows,places,start,end,*,news_risk=10.,stress=False,guards=True,challenge=True,detail=False):
    events=[]
    for i,r in enumerate(rows):
        r['_costs']=costs(r,stress)
        events.append((r['op'],1,i))
        if r['cl']<end:events.append((r['cl'],2,i))
    pi={(p['key'],p['epoch']):i for i,p in enumerate(places)}
    for i,p in enumerate(places):
        events.append((p['op'],0,i))
        if p['until']<end:events.append((p['until'],3,i))
    day=datetime.fromtimestamp(start,PRAGUE).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    while day.timestamp()<end:events.append((day.timestamp(),-1,0));day+=timedelta(days=1)
    events.append((end-.001,4,0));events.sort()
    bal=peak=anchor=CAPITAL;phase=1 if challenge else 3;ready=start
    active={};pending={};days=set();counts=Counter();by=defaultdict(Counter);log=[];passes=[]
    first=funded=request=receipt=breach=None;reward=dd=daily=closeddd=maxmargin=maxrisk=0.
    today_count=0;today_losses=0;ws=ls=mw=ml=0;last_entry=start;expired=None
    def held():return list(active.values())+list(pending.values())
    def envelope():return sum(p['env'] for p in active.values())
    def gate(t):
        if t<ready:return 'phase_wait'
        if challenge and phase<3 and bal>=CAPITAL*(1.10 if phase==1 else 1.05) and len(days)>=4:return 'target_wait'
        if guards and today_count>=7:return 'daily_trade_limit'
        if guards and today_losses>=3:return 'three_losses_stop'
        return None
    def admit(sym,marg,risk,entryfee,env):
        current=held();totalrisk=sum(p['risk'] for p in current);totalmargin=sum(p['margin'] for p in current)
        if totalmargin+marg>(bal-envelope())*(.8 if guards else 1.):return 'margin'
        if guards:
            if totalrisk+risk>225:return 'open_risk'
            group='metals' if sym in ('XAUUSD','XAGUSD') else sym
            if sum(p['risk'] for p in current if p['group']==group)+risk>150:return 'correlated_risk'
            # Reserve the entire new risk, costs, and all existing positions/pending sides.
            if anchor-bal+sum(p['env'] for p in current)+env-entryfee>300:return 'daily_budget'
            if bal-sum(p['env'] for p in current)-env+entryfee<9200:return 'total_loss_buffer'
        return None
    for t,kind,i in events:
        if kind==-1:anchor=bal;today_count=today_losses=0
        elif kind==0:
            p=places[i];reason=gate(t)
            if reason:counts[reason]+=1;continue
            sym=p['symbol'];contract=SPECS[sym][0];riskunit=p['sl']*contract
            lot=rounded(news_risk/riskunit);risk=lot*riskunit
            marg=margin(sym,lot,max(p['buy'],p['sell']))
            fee=(47.5 if sym=='XAGUSD' else 7.)*lot
            if sym=='BTCUSD':fee=.000325*lot*(p['buy']+p['sell'])
            env=risk*(2 if stress else 1.25)
            reason=admit(sym,2*marg,2*risk,-fee,2*env)
            if reason:counts['news_'+reason+'_rejected']+=1;continue
            for side in ('Long','Short'):
                pending[i,side]=dict(lot=lot,risk=risk,margin=marg,env=env,key=p['key'],group='metals' if sym in ('XAUUSD','XAGUSD') else sym)
            counts['news_baskets']+=1
        elif kind==1:
            r=rows[i];key=r['key'];g,c,s,x=r['_costs'];sym=r['symbol']
            if r['news']:
                pidx=pi.get((key,r['event']));p=pending.pop((pidx,r['side']),None)
                if p is None:counts['news_not_admitted_fills']+=1;continue
            else:
                reason=gate(t)
                if reason:counts[reason]+=1;continue
                if any(p['key']==key for p in active.values()):counts['same_ea_overlap']+=1;continue
                lot=rounded(RISK/r['unit_risk']);risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])
                env=risk*(1.25 if stress else 1.)
                reason=admit(sym,marg,risk,(c-x)/2*lot,env)
                if reason:counts[reason+'_rejected']+=1;continue
                p=dict(lot=lot,risk=risk,margin=marg,env=env,key=key,group='metals' if sym in ('XAUUSD','XAGUSD') else sym)
            fee=(c-x)/2*p['lot'];bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)
            active[i]=p;today_count+=1;last_entry=t;counts['opened']+=1;by[key]['opened']+=1;days.add(datetime.fromtimestamp(t,PRAGUE).date())
            if phase==3 and first is None:first=t
        elif kind==2 and i in active:
            p=active.pop(i);r=rows[i];g,c,s,x=r['_costs'];lot=p['lot'];delta=(g+s+(c-x)/2)*lot;bal+=delta
            net=delta+p['entryfee'];counts['closed']+=1;by[r['key']]['trades']+=1;by[r['key']]['net']+=net;by[r['key']]['wins']+=net>0
            by[r['key']]['positive']+=max(0,net);by[r['key']]['negative']+=max(0,-net);today_losses+=net<0
            ws=ws+1 if net>0 else 0;ls=ls+1 if net<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
            if detail:log.append(dict(ea=r['key'],phase=p['phase'],open=iso(p['opened']),close=iso(t),lots=lot,initial_risk=p['risk'],gross_profit=g*lot,commission=c*lot,swap=s*lot,stress_cost=x*lot,net_profit=net,balance=bal))
        elif kind==3:
            for side in ('Long','Short'):pending.pop((i,side),None)
        eq=bal-envelope();peak=max(peak,bal);dd=max(dd,100*(peak-eq)/peak);closeddd=max(closeddd,100*(peak-bal)/peak);daily=max(daily,anchor-eq)
        maxmargin=max(maxmargin,sum(p['margin'] for p in held()));maxrisk=max(maxrisk,sum(p['risk'] for p in held()))
        if eq<9000-1e-8 or eq<anchor-500-1e-8:breach=t;break
        if challenge and phase<3 and not active and not pending and len(days)>=4 and bal>=CAPITAL*(1.1 if phase==1 else 1.05):
            passes.append(dict(phase=phase,time=iso(t),balance=bal,trading_days=len(days)));phase+=1;ready=business(t,2 if phase==2 else 5)
            if phase==3:funded=ready
            bal=peak=anchor=CAPITAL;days=set();last_entry=ready
        if challenge and phase==3 and first is not None and not active and not pending and t>=first+14*DAY and bal>=10025:
            request=t;receipt=business(t,4);reward=.8*(bal-CAPITAL);break
        if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:
            expired=t;break # conservative inactivity outcome, not fabricated losing trade
    wins=sum(v['wins'] for v in by.values());trades=counts['closed'];pos=sum(v['positive'] for v in by.values());neg=sum(v['negative'] for v in by.values())
    return dict(funded=funded is not None and funded<end,payout=receipt is not None and receipt<end,eligible=request is not None and request<end,breach=breach is not None,inactive=expired is not None,
                funded_at=iso(funded),request_at=iso(request),receipt_at=iso(receipt),breach_at=iso(breach),reward=reward,balance=bal,phase=phase,passes=passes,trades=trades,win_rate=100*wins/trades if trades else 0,pf=pos/neg if neg else None,
                model_dd_pct=dd,closed_dd_pct=closeddd,worst_daily_usd=daily,max_margin=maxmargin,max_open_risk=maxrisk,max_win_streak=mw,max_loss_streak=ml,counts=dict(counts),by_ea=dict(by),log=log)
def aggregate(rr):
    n=len(rr);pct=lambda k:100*sum(r[k] for r in rr)/n
    paid=[r['reward'] for r in rr if r['payout']]
    return dict(paths=n,funded_pct=pct('funded'),payout_pct=pct('payout'),eligible_pct=pct('eligible'),breach_pct=pct('breach'),inactive_pct=pct('inactive'),
                unfinished_pct=100*sum(not(r['payout'] or r['breach'] or r['inactive']) for r in rr)/n,
                median_reward_if_paid=statistics.median(paid) if paid else None,median_trades=statistics.median(r['trades'] for r in rr),p95_model_dd_pct=sorted(r['model_dd_pct'] for r in rr)[int(.95*(n-1))])
def window(months):return datetime(2026,9-months,5,tzinfo=timezone.utc).timestamp(),END
def plans(audit):
    ranked=audit['ranked'];high=['xau-rsi-vwap/standard','nasdaq-overnight/standard']
    result=[dict(name='Raw Gold',keys=[RAW],news_risk=RISK),dict(name='Raw + XAU/XAG news, literal risk',keys=[RAW]+NEWS,news_risk=RISK),
            dict(name='Raw + XAU/XAG news, $10/order',keys=[RAW]+NEWS,news_risk=10.),
            dict(name='High-win comparison',keys=[RAW]+high,news_risk=10.),
            dict(name='High-win + news',keys=[RAW]+high+NEWS,news_risk=10.),
            dict(name='Training top 3',keys=ranked[:3],news_risk=10.),
            dict(name='Training top 5',keys=ranked[:5],news_risk=10.),
            dict(name='Training top 3 + raw',keys=ranked[:3]+[RAW],news_risk=10.),
            dict(name='Training top 3 + raw + news',keys=ranked[:3]+[RAW]+NEWS,news_risk=10.),
            dict(name='Raw + USDJPY + news',keys=[RAW,'usdjpy-london-open-momentum/standard']+NEWS,news_risk=10.),
            dict(name='Raw + all four news, literal risk',keys=[RAW]+NEWS+['news-pulse-btc/standard','news-pulse-eurusd/standard'],news_risk=RISK)]
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--paths',type=int,default=1000);args=parser.parse_args()
    data=read(ROOT/'prepared.json');audit=read(ROOT/'audit.json');configs=plans(audit)
    save(ROOT/'plans-frozen.json',configs)
    out=[]
    for config in configs:
        for months in (2,4,6):
            start,end=window(months);rr,pp=shifted_data(data,config['keys'],start,end)
            cases={}
            for stress in (False,True):
                result=replay(rr,pp,start,end,news_risk=config['news_risk'],stress=stress,detail=True)
                continuous=replay(rr,pp,start,end,news_risk=config['news_risk'],stress=stress,challenge=False,detail=True)
                rng=random.Random(20260920);nweeks=math.ceil((end-start)/WEEK)+1
                sims=[]
                for _ in range(args.paths):
                    sample=[rng.randrange(26) for _ in range(nweeks)]
                    sr,sp=shifted_data(data,config['keys'],start,end,sample)
                    sims.append(replay(sr,sp,start,end,news_risk=config['news_risk'],stress=stress))
                cases['stress' if stress else 'reference']=dict(historical=result,continuous=continuous,bootstrap=aggregate(sims))
            out.append(dict(plan=config,months=months,start=iso(start),end_exclusive=iso(end),cases=cases))
            print(config['name'],months,'PAYOUT',cases['reference']['bootstrap']['payout_pct'],cases['stress']['bootstrap']['payout_pct'],'HIST',cases['reference']['historical']['reward'],cases['stress']['historical']['reward'],flush=True)
            save(ROOT/'results.json',dict(results=out,paths=args.paths,seed=20260920,source_weeks=26))
if __name__=='__main__':main()
