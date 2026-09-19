"""Offline, deterministic saved-ledger study. Never connects to MT5 or trades."""
from __future__ import annotations
import json, math, re, hashlib, random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
import numpy as np

ROOT=Path(__file__).resolve().parent; P=ROOT.parent
G=P/'Gold Overnight Value Area Pipeline 2026-09-19'
X=P/'News Pulse Event Parameters Research 2026-09-19'
S=P/'News Pulse Multi Asset Event Parameters 2026-09-19'
UTC=timezone.utc; PRAGUE=ZoneInfo('Europe/Prague')
START=datetime(2026,7,19,tzinfo=UTC).timestamp()
END=datetime(2026,9,19,tzinfo=UTC).timestamp()
MONDAY=datetime(2026,7,20,tzinfo=UTC).timestamp()
CAPITAL=10000.; DAY=86400.; WEEK=7*DAY
CONTRACT={'raw':100.,'xau':100.,'xag':5000.}
LEVERAGE={'raw':15.,'xau':15.,'xag':15.}

def dt(x):
    d=datetime.fromisoformat(x.replace('Z','+00:00'))
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).timestamp()
def iso(t):return datetime.fromtimestamp(t,UTC).isoformat() if t is not None else None
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def ceil_lot(v):return max(.01,math.ceil((v-1e-10)/.01)*.01)
def business(t,n):
    d=datetime.fromtimestamp(t,UTC)
    while n:
        d+=timedelta(days=1)
        if d.weekday()<5:n-=1
    return d.timestamp()
def fingerprint(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def week_anchor(start):
    if start==START:return MONDAY  # retain the original nine-week experiment
    d=datetime.fromtimestamp(start,UTC).replace(hour=0,minute=0,second=0,microsecond=0)
    return (d-timedelta(days=d.weekday())).timestamp()

def load(stress=False,start=START,end=END):
    """Read whole-window raw native records and exact logged news placements."""
    source={
      'raw':G/'native'/'gva-raw-959d9253ab-5y-d150-r1-m4',
      'xau':X/'native'/('NativeFullBestDelay250V2' if stress else 'NativeFullBestV2'),
      'xag':S/'native'/('XAGFittedDelay250' if stress else 'XAGFitted')}
    trades=[];placements=[];audit={};qcache={}
    m1=np.load(G/'data'/'M1.npz')['rates']
    for key,folder in source.items():
        allrows=read(folder/'trades.json')
        rows=[r for r in allrows if start<=dt(r['open_time'])<end]
        if key!='raw':
            q=np.load((X if key=='xau' else S/'XAG')/'quote-arrays.npz')['data']
            qcache[key]=q
            journal=(folder/'journal.txt').read_text(encoding='utf-8')
            pat=r'News Pulse: (NFP|CPI|FOMC) two-sided orders placed\. Buy ([\d.]+), sell ([\d.]+), SL distance \$([\d.]+),.*?Server placement=([\d.]+ [\d:]+), event=([\d.]+ [\d:]+), lead=(\d+)s'
            for hit in re.finditer(pat,journal):
                kind,buy,sell,sl,at,event,lead=hit.groups()
                parse=lambda s:datetime.strptime(s,'%Y.%m.%d %H:%M:%S').replace(tzinfo=UTC).timestamp()
                at=parse(at);epoch=parse(event)
                if not start<=epoch<end:continue
                record=dict(key=key,epoch=epoch,t=at,kind=kind,buy=float(buy),sell=float(sell),sl=float(sl),until=epoch+(300 if key=='xau' and kind=='CPI' else 120 if key=='xau' and kind=='FOMC' else 60))
                prior=[v for v in placements if v['key']==key and v['epoch']==epoch]
                if prior:
                    assert prior==[record],(prior,record)
                    continue  # tester journal contains repeated identical saved lines
                placements.append(record)
        for r in rows:
            r=dict(r,key=key,op=dt(r['open_time']),cl=dt(r['close_time']))
            r['id']=len(trades);r['unit_gross']=r['gross_profit']/r['volume']
            r['unit_comm']=r['commission']/r['volume']
            r['unit_swap']=r['swap']/r['volume']
            if key=='raw':
                # Initial fill-to-stop distance, not a trailing stop or website estimated R.
                r['unit_risk']=abs(r['open_price']-r['stop'])*100
                sign=1 if r['side']=='Long' else -1
                request=r['open_price']-r['entry_slippage_price']*sign
                r['unit_sizing_risk']=abs(request-r['stop'])*100
                r['event']=None
            else:
                r['event']=int(r['entry_comment'].split('|')[1])
                pp=next(p for p in placements if p['key']==key and p['epoch']==r['event'])
                r['unit_risk']=pp['sl']*CONTRACT[key]
                assert pp['t']<=r['op']<=pp['until']
            # Remaining additional execution costs are charged half on entry and exit.
            slip=(.1 if key=='raw' else .5 if key=='xau' else .02) if stress else 0.
            r['unit_extra']=2*slip*CONTRACT[key]
            if stress:r['unit_comm']=min(r['unit_comm'],-(47.5 if key=='xag' else 7.))
            r['marks']=[]
            direction=1 if r['side']=='Long' else -1
            if key=='raw':
                # Only full bars wholly inside the life of this position.
                a,z=np.searchsorted(m1['time'],[r['op'],r['cl']-60],side='right')
                for b in m1[a:z]:
                    px=float(b['low'] if direction==1 else b['high']+b['spread']*.001)
                    r['marks'].append((float(b['time'])+59,(px-r['open_price'])*100*direction))
            else:
                # Unambiguous interior seconds; native timestamps have second resolution.
                a,z=np.searchsorted(q[:,0],[(r['op']+1)*1000,r['cl']*1000])
                sub=q[a:z]
                if len(sub):
                    secs=(sub[:,0]//1000).astype(np.int64)
                    starts=np.r_[0,np.flatnonzero(np.diff(secs))+1]
                    px=sub[:,1] if direction==1 else sub[:,2]
                    values=(np.minimum.reduceat(px,starts) if direction==1 else np.maximum.reduceat(px,starts))
                    r['marks']=[(float(secs[i])+.999,float(v-r['open_price'])*CONTRACT[key]*direction) for i,v in zip(starts,values)]
            trades.append(r)
        audit[key]=dict(path=str(folder/'trades.json'),sha256=fingerprint(folder/'trades.json'),trades=len(rows),wins=sum(r['net_profit']>0 for r in rows),source_start=iso(min(dt(r['open_time']) for r in rows)),source_end=iso(max(dt(r['close_time']) for r in rows)))
    if start==START and end==END:
        assert len(trades)==51 and len(placements)==12,(len(trades),len(placements))
    assert all(r['cl']<end for r in trades),'A source position crosses the window endpoint'
    # Events reference trade / placement indexes. Entries precede same-second exits.
    events=[]
    for i,p in enumerate(placements):
        events.extend([(p['t'],0,i,0.),(p['until']+1,4,i,0.)])
    for r in trades:
        events.extend([(r['op'],1,r['id'],0.),(r['cl'],3,r['id'],0.)])
        events.extend((t,2,r['id'],v) for t,v in r['marks'])
    events.sort()
    weekly=[];anchor=week_anchor(start)
    for i in range(math.ceil((end-anchor)/WEEK)):
        begin=anchor+i*WEEK
        weekly.append([(t-begin,k,idx,value) for t,k,idx,value in events if begin<=t<begin+WEEK])
    assert sum(map(len,weekly))==len(events)
    return trades,placements,events,weekly,audit

def replay(data,news_pct=.05,stress=False,challenge=True,sample=None,detail=False,start=START,end=END,preserve_ny_clock=False):
    trades,placements,events,weekly,_=data
    if sample is not None:
        anchor=week_anchor(start)
        if preserve_ny_clock:
            ny=ZoneInfo('America/New_York');events=[]
            for i,j in enumerate(sample):
                # All source positions close inside Monday-Friday. Use midweek
                # offsets to retain NY wall-clock schedules when crossing DST.
                source_offset=datetime.fromtimestamp(anchor+j*WEEK+2*DAY+12*3600,ny).utcoffset().total_seconds()
                target_offset=datetime.fromtimestamp(anchor+i*WEEK+2*DAY+12*3600,ny).utcoffset().total_seconds()
                shifted=anchor+i*WEEK+source_offset-target_offset
                events.extend((shifted+t,k,idx,v) for t,k,idx,v in weekly[j] if start<=shifted+t<end)
        else:
            events=[(anchor+i*WEEK+t,k,idx,v) for i,j in enumerate(sample) for t,k,idx,v in weekly[j] if start<=anchor+i*WEEK+t<end]
    # Refresh Prague midnight anchor even when source positions are carried.
    d=datetime.fromtimestamp(start,PRAGUE).replace(hour=0,minute=0,second=0)+timedelta(days=1)
    midnight=[]
    while d.timestamp()<end:
        midnight.append((d.timestamp(),-1,-1,0.));d+=timedelta(days=1)
    events=sorted(events+midnight+[(end-1,5,-1,0.)])
    balance=peak=anchor=CAPITAL;phase=1;ready=start
    active={};reserved={};entry_days=set();counts=Counter();by=defaultdict(lambda:Counter())
    log=[];passes=[];first_funded=funded=request=receipt=breach=None
    reward=0.;worst_daily=worst_dd=worst_closed_dd=max_margin=0.
    margin_limit=1. if news_pct==.75 else .8
    reduced=news_pct!=.75
    def equity():return balance+sum(p['mark'] for p in active.values())
    def room(margin,risk):
        held=list(active.values())+list(reserved.values())
        if sum(v['margin'] for v in held)+margin>max(0,equity())*margin_limit:return 'margin_rejected'
        if reduced and (anchor-balance>=200 or sum(v['risk'] for v in held)+risk>200):return 'research_guard'
        return None
    def gate():
        if breach is not None or request is not None:return True
        if t<ready:return True
        if challenge and phase<3 and balance>=CAPITAL*(1.1 if phase==1 else 1.05) and len(entry_days)>=4:return True
        return False
    for t,kind,idx,val in events:
        if kind==-1:anchor=balance
        elif kind==0:
            p=placements[idx]
            if gate():counts['news_phase_paused']+=1;continue
            if news_pct==0:continue
            lot=ceil_lot(CAPITAL*news_pct/100/(p['sl']*CONTRACT[p['key']]))
            marg=lot*CONTRACT[p['key']]*max(p['buy'],p['sell'])/LEVERAGE[p['key']]
            risk=lot*p['sl']*CONTRACT[p['key']]
            reject=room(2*marg,2*risk)
            if reject:
                counts['news_'+reject]+=1;continue
            for side in ('Long','Short'):
                reserved[(idx,side)]=dict(lots=lot,margin=marg,risk=risk,key=p['key'])
            counts['news_baskets_accepted']+=1
        elif kind==4:
            for side in ('Long','Short'):reserved.pop((idx,side),None)
        elif kind==1:
            r=trades[idx];key=r['key']
            if key=='raw':
                if gate():counts['raw_phase_paused']+=1;continue
                lot=ceil_lot(100/r.get('unit_sizing_risk',r['unit_risk']))
                margin=lot*100*r['open_price']/15;risk=lot*r['unit_risk']
                reject=room(margin,risk)
                if reject:counts['raw_'+reject]+=1;continue
                p=dict(lots=lot,margin=margin,risk=risk,key=key)
            else:
                pi=next(i for i,p in enumerate(placements) if p['key']==key and p['epoch']==r['event'])
                p=reserved.pop((pi,r['side']),None)
                if p is None:counts['news_unreserved_fill']+=1;continue
            lot=p['lots'];cost=(r['unit_comm']-r['unit_extra'])/2*lot
            balance+=cost;p.update(mark=0.,phase=phase,opened=t,entry_cost=cost)
            active[idx]=p;counts['opened']+=1;by[key]['opened']+=1
            entry_days.add(datetime.fromtimestamp(t,PRAGUE).date())
            if phase==3 and first_funded is None:first_funded=t
        elif kind==2 and idx in active:
            active[idx]['mark']=val*active[idx]['lots']
        elif kind==3 and idx in active:
            p=active.pop(idx);r=trades[idx];lot=p['lots']
            close_net=(r['unit_gross']+r['unit_swap']+(r['unit_comm']-r['unit_extra'])/2)*lot
            balance+=close_net;net=close_net+p['entry_cost']
            counts['closed']+=1;by[r['key']]['closed']+=1;by[r['key']]['wins']+=net>0;by[r['key']]['net']+=net
            by[r['key']]['positive']+=max(0,net);by[r['key']]['negative']+=max(0,-net)
            if detail:log.append(dict(ea=r['key'],phase=p['phase'],open=iso(p['opened']),close=iso(t),lots=round(lot,2),initial_risk=p['risk'],net=net,balance=balance))
        eq=equity();peak=max(peak,eq,balance)
        worst_daily=max(worst_daily,anchor-eq)
        worst_dd=max(worst_dd,(peak-eq)/peak*100)
        worst_closed_dd=max(worst_closed_dd,(peak-balance)/peak*100)
        max_margin=max(max_margin,sum(p['margin'] for p in active.values())+sum(p['margin'] for p in reserved.values()))
        if eq<9000-1e-8 or eq<anchor-500-1e-8:
            breach=t;break
        if challenge and phase<3 and not active and not reserved and len(entry_days)>=4 and balance>=CAPITAL*(1.1 if phase==1 else 1.05):
            passes.append(dict(phase=phase,time=iso(t),balance=balance,trading_days=len(entry_days)))
            phase+=1;ready=business(t,2 if phase==2 else 5)
            if phase==3:funded=ready
            balance=peak=anchor=CAPITAL;entry_days=set()
        if challenge and phase==3 and first_funded and not active and not reserved and t>=first_funded+14*DAY and balance>=10025:
            request=t;reward=.8*(balance-10000);receipt=business(t,4);break
    return dict(phase=phase,balance=balance,closed_trades=counts['closed'],by_ea=dict(by),counts=dict(counts),passes=passes,funded=iso(funded),funded_by30=funded is not None and funded<=start+30*DAY,funded_by_end=funded is not None and funded<end,payout_requested=iso(request),payout_received_assumption=iso(receipt),reward=reward,payout_eligible_by_end=request is not None and request<end,payout_received_by_end=receipt is not None and receipt<end,proxy_breach=iso(breach),worst_daily_equity_proxy_usd=worst_daily,max_equity_proxy_dd_pct=worst_dd,max_reserved_margin=max_margin,log=log)

def aggregate(rows):
    n=len(rows)
    pct=lambda k:100*sum(bool(r[k]) for r in rows)/n
    return dict(paths=n,funded_by30_pct=pct('funded_by30'),funded_by_end_pct=pct('funded_by_end'),payout_eligible_pct=pct('payout_eligible_by_end'),payout_received_pct=pct('payout_received_by_end'),proxy_breach_pct=pct('proxy_breach'),median_closed_trades=float(np.median([r['closed_trades'] for r in rows])),median_reward_if_received=float(np.median([r['reward'] for r in rows if r['payout_received_by_end']])) if any(r['payout_received_by_end'] for r in rows) else None)

def main():
    rng=random.Random(20260919);samples=[[rng.randrange(9) for _ in range(9)] for _ in range(1000)]
    results=[]
    for stress in (False,True):
        data=load(stress)
        print('LOADED',stress,data[-1],flush=True)
        for name,risk in [('Unchanged news sizing',.75),('Reduced news sizing',.05),('Margin-compatible news sizing',.10),('Raw without news',0.)]:
            hist=replay(data,risk,stress,detail=True)
            continuous=replay(data,risk,stress,challenge=False,detail=True)
            sims=[replay(data,risk,stress,sample=s) for s in samples]
            row=dict(name=name,news_risk_percent_per_order=risk,stress=stress,historical=hist,continuous=continuous,bootstrap=aggregate(sims),audit=data[-1])
            results.append(row)
            print('RESULT',name,stress,json.dumps({k:v for k,v in hist.items() if k not in ('log','by_ea')}),json.dumps(row['bootstrap']),flush=True)
    save(ROOT/'results.json',dict(start=iso(START),end_exclusive=iso(END),results=results,protocol_sha256=fingerprint(ROOT/'PROTOCOL.md')))
    print('SAVED',ROOT/'results.json',flush=True)
if __name__=='__main__':main()
