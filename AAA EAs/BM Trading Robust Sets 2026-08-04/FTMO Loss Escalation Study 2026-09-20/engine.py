"""Shared-cash FTMO research. Stop-envelope approximation, not native FTMO equity."""
from __future__ import annotations
import argparse,math,random,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'FTMO Combination Study 2026-09-19'))
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

def entry_charge(r,commission,extra):
    # The admission decision must not depend on a future crypto exit price.
    if r['symbol'] in ('BTCUSD','ETHUSD'):
        return -.000325*SPECS[r['symbol']][0]*r['open_price']-extra/2
    return (commission-extra)/2
def shifted_data(data,keys,start,end,sample=None,block_weeks=1):
    rr=[r for k in keys for r in data['rows'][k]]
    pp=[p for p in data['placements'] if p['key'] in keys]
    if sample is None:return [dict(r) for r in rr if start<=r['op']<end],[dict(p) for p in pp if start<=p['op']<end]
    anchor=datetime.fromtimestamp(start,timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    anchor=(anchor-timedelta(days=anchor.weekday())).timestamp()
    source=datetime(2026,3,2,tzinfo=timezone.utc).timestamp();out=[];places=[]
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
def replay(rows,places,start,end,*,news_risk=10.,stress=False,guards=True,challenge=True,detail=False,risk_profile='flat',base_risk=RISK,risk_scope='portfolio'):
    if risk_profile not in ('flat','loss_1_5x','fixed_1_5_after_loss'):raise ValueError(risk_profile)
    if risk_scope not in ('portfolio','ea'):raise ValueError(risk_scope)
    loss_state=defaultdict(int)
    max_requested=max_admitted=max_factor=0.
    rejection_log=[]
    def state_key(key):return key if risk_scope=='ea' else 'portfolio'
    def requested(key,news=False):
        losses=loss_state[state_key(key)]
        factor=1. if risk_profile=='flat' else 1.5**losses if risk_profile=='loss_1_5x' else 1.5 if losses else 1.
        return (news_risk if news else base_risk)*factor,factor
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
    today_count=0;max_daily_entries=0;today_losses=0;ws=ls=mw=ml=0;last_entry=start;expired=None
    def held():return list(active.values())+list(pending.values())
    def envelope():return sum(p['env'] for p in active.values())
    def gate(t,slots=1):
        if t<ready:return 'phase_wait'
        if challenge and phase<3 and bal>=CAPITAL*(1.10 if phase==1 else 1.05) and len(days)>=4:return 'target_wait'
        if guards and today_count+len(pending)+slots>7:return 'daily_trade_limit'
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
            p=places[i];reason=gate(t,2)
            if reason:counts[reason]+=1;continue
            sym=p['symbol'];contract=SPECS[sym][0];riskunit=p['sl']*contract
            desired,factor=requested(p['key'],True);max_requested=max(max_requested,desired)
            lot=rounded(desired/riskunit);risk=lot*riskunit
            marg=margin(sym,lot,max(p['buy'],p['sell']))
            fee=(47.5 if sym=='XAGUSD' else 7.)*lot
            if sym=='BTCUSD':fee=.000325*lot*(p['buy']+p['sell'])
            env=risk*(2 if stress else 1.25)
            reason=admit(sym,2*marg,2*risk,-fee,2*env)
            if reason:
                counts['news_'+reason+'_rejected']+=1
                if factor>1:counts['escalated_rejections']+=1
                if detail:rejection_log.append(dict(time=iso(t),ea=p['key'],news=True,reason=reason,requested_risk_per_side=desired,actual_risk_per_side=risk,multiplier=factor))
                continue
            for side in ('Long','Short'):
                pending[i,side]=dict(lot=lot,risk=risk,requested_risk=desired,risk_factor=factor,margin=marg,env=env,key=p['key'],group='metals' if sym in ('XAUUSD','XAGUSD') else sym)
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
                desired,factor=requested(key);max_requested=max(max_requested,desired)
                lot=rounded(desired/r['unit_risk']);risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])
                env=risk*(1.25 if stress else 1.)
                reason=admit(sym,marg,risk,entry_charge(r,c,x)*lot,env)
                if reason:
                    counts[reason+'_rejected']+=1
                    if factor>1:counts['escalated_rejections']+=1
                    if detail:rejection_log.append(dict(time=iso(t),ea=key,news=False,reason=reason,requested_risk_per_side=desired,actual_risk_per_side=risk,multiplier=factor))
                    continue
                p=dict(lot=lot,risk=risk,requested_risk=desired,risk_factor=factor,margin=marg,env=env,key=key,group='metals' if sym in ('XAUUSD','XAGUSD') else sym)
            fee=entry_charge(r,c,x)*p['lot'];bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)
            max_admitted=max(max_admitted,p['risk']);max_factor=max(max_factor,p['risk_factor'])
            active[i]=p;today_count+=1;last_entry=t;counts['opened']+=1;by[key]['opened']+=1;days.add(datetime.fromtimestamp(t,PRAGUE).date())
            max_daily_entries=max(max_daily_entries,today_count)
            if phase==3 and first is None:first=t
        elif kind==2 and i in active:
            p=active.pop(i);r=rows[i];g,c,s,x=r['_costs'];lot=p['lot'];delta=(g+s+c-x)*lot-p['entryfee'];bal+=delta
            net=delta+p['entryfee'];counts['closed']+=1;by[r['key']]['trades']+=1;by[r['key']]['net']+=net;by[r['key']]['wins']+=net>0
            by[r['key']]['positive']+=max(0,net);by[r['key']]['negative']+=max(0,-net);today_losses+=net<0
            before_losses=loss_state[state_key(r['key'])]
            if net>1e-9:loss_state[state_key(r['key'])]=0
            elif net < -1e-9:loss_state[state_key(r['key'])]+=1
            ws=ws+1 if net>0 else 0;ls=ls+1 if net<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
            if detail:log.append(dict(ea=r['key'],phase=p['phase'],open=iso(p['opened']),close=iso(t),lots=lot,initial_risk=p['risk'],requested_risk=p['requested_risk'],risk_factor=p['risk_factor'],losses_before_close=before_losses,losses_after_close=loss_state[state_key(r['key'])],gross_profit=g*lot,commission=c*lot,swap=s*lot,stress_cost=x*lot,net_profit=net,balance=bal))
        elif kind==3:
            for side in ('Long','Short'):pending.pop((i,side),None)
        eq=bal-envelope();peak=max(peak,bal);dd=max(dd,100*(peak-eq)/peak);closeddd=max(closeddd,100*(peak-bal)/peak);daily=max(daily,anchor-eq)
        maxmargin=max(maxmargin,sum(p['margin'] for p in held()));maxrisk=max(maxrisk,sum(p['risk'] for p in held()))
        if eq<9000-1e-8 or eq<anchor-500-1e-8:breach=t;break
        if challenge and phase<3 and not active and not pending and len(days)>=4 and bal>=CAPITAL*(1.1 if phase==1 else 1.05):
            passes.append(dict(phase=phase,time=iso(t),balance=bal,trading_days=len(days)));phase+=1;ready=business(t,2 if phase==2 else 5)
            if phase==3:funded=ready
            bal=peak=anchor=CAPITAL;days=set();last_entry=ready;loss_state.clear()
        if challenge and phase==3 and first is not None and not active and not pending and t>=first+14*DAY and bal>=10025:
            request=t;receipt=business(t,4);reward=.8*(bal-CAPITAL);break
        if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:
            expired=t;break # conservative inactivity outcome, not fabricated losing trade
    wins=sum(v['wins'] for v in by.values());trades=counts['closed'];pos=sum(v['positive'] for v in by.values());neg=sum(v['negative'] for v in by.values())
    return dict(risk_profile=risk_profile,risk_scope=risk_scope,base_risk=base_risk,news_base_risk=news_risk,
                max_requested_risk=max_requested,max_admitted_single_risk=max_admitted,max_admitted_multiplier=max_factor,
                final_loss_state=dict(loss_state),rejections=rejection_log,
                funded=funded is not None and funded<end,payout=receipt is not None and receipt<end,eligible=request is not None and request<end,breach=breach is not None,inactive=expired is not None,
                funded_at=iso(funded),request_at=iso(request),receipt_at=iso(receipt),breach_at=iso(breach),reward=reward,balance=bal,phase=phase,passes=passes,trades=trades,win_rate=100*wins/trades if trades else 0,pf=pos/neg if neg else None,
                model_dd_pct=dd,closed_dd_pct=closeddd,worst_daily_usd=daily,max_margin=maxmargin,max_open_risk=maxrisk,max_daily_entries=max_daily_entries,max_win_streak=mw,max_loss_streak=ml,counts=dict(counts),by_ea=dict(by),log=log)
def aggregate(rr):
    n=len(rr);pct=lambda k:100*sum(r[k] for r in rr)/n
    paid=[r['reward'] for r in rr if r['payout']]
    return dict(paths=n,funded_pct=pct('funded'),payout_pct=pct('payout'),eligible_pct=pct('eligible'),breach_pct=pct('breach'),inactive_pct=pct('inactive'),
                unfinished_pct=100*sum(not(r['payout'] or r['breach'] or r['inactive']) for r in rr)/n,
                median_reward_if_paid=statistics.median(paid) if paid else None,median_trades=statistics.median(r['trades'] for r in rr),p95_model_dd_pct=sorted(r['model_dd_pct'] for r in rr)[int(.95*(n-1))])
def window(months):
    import calendar
    d=datetime.fromtimestamp(END,timezone.utc);m=d.month-months
    y=d.year+(m-1)//12;m=(m-1)%12+1
    return d.replace(year=y,month=m,day=min(d.day,calendar.monthrange(y,m)[1])).timestamp(),END
