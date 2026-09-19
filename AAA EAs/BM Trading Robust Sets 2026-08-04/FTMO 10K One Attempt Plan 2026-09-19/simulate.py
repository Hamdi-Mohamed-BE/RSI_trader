"""Research only. Joint cached-deal replay; NOT a native FTMO tick backtest.

One attempt, no repurchases. Closed results and initial-stop envelopes cannot
reconstruct actual intratrade equity. Output frequencies are conditional on
historical, retrospectively selected EAs, NOT calibrated future probabilities.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone, time
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
CACHE = Path(r'C:\Users\hama101\.codex\.tmp\news-lead-audit-sparse\AAA EAs\EA store\data\evidence-cache\v1\products')
UTC = timezone.utc
PRAGUE = ZoneInfo('Europe/Prague')
NY = ZoneInfo('America/New_York')
START = datetime(2021, 9, 7, tzinfo=UTC)
SPLIT = datetime(2024, 9, 1, tzinfo=UTC)
END = datetime(2026, 8, 31, tzinfo=UTC)
ACCOUNT = 10_000.0
SPEC = {
    'XAUUSD': dict(contract=100, leverage=15, price=4348, carry_long=83, carry_short=8.3, triple=2),
    'XAGUSD': dict(contract=5000, leverage=9, price=64.5, carry_long=74.35, carry_short=0, triple=2),
    'USTEC': dict(contract=1, leverage=15, price=29000, carry_long=6.38, carry_short=0, triple=4),
    'USDJPY': dict(contract=100000, leverage=30, price=1, carry_long=0, carry_short=11, triple=2),
}

def dt(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')

def rollover_units(op, cl, triple):
    day = op.astimezone(NY).date()
    units = 0
    while day <= cl.astimezone(NY).date():
        roll = datetime.combine(day, time(17), NY).astimezone(UTC)
        if op < roll <= cl and day.weekday() < 5:
            units += 3 if day.weekday() == triple else 1
        day += timedelta(days=1)
    return units

def load():
    rows, audit, excluded = {}, [], []
    for p in sorted(CACHE.glob('*/*/5y.json')):
        slug, mode = p.parts[-3:-1]
        key = slug + '/' + mode
        summary = read(p)
        data = read(p.with_name('5y.trades.json'))
        if not data:
            continue
        required = ['gross_profit', 'commission', 'swap', 'estimated_risk_cash', 'configured_risk_pct']
        symbols = {r['symbol'].rstrip('r') for r in data}
        if not symbols <= SPEC.keys() or not all(all(k in r for k in required) for r in data):
            excluded.append(dict(key=key, reason='unsupported asset or incomplete cost/risk fields'))
            continue
        if slug == 'news-pulse-eurusd':
            continue
        out = []
        for j, raw in enumerate(data):
            r = dict(raw)
            r.update(key=key, slug=slug, uid=f'{key}:{j}', news=slug.startswith('news-pulse-'))
            r['op'], r['cl'] = dt(r['open_time']), dt(r['close_time'])
            if r['cl'] <= r['op']:
                r['cl'] = r['op'] + timedelta(microseconds=1)
            r['symbol'] = r['symbol'].rstrip('r')
            if not START <= r['op'] < END:
                continue
            assert r['volume'] > 0 and r['estimated_risk_cash'] > 0
            assert abs(r['gross_profit']+r['commission']+r['swap']-r['net_profit']) < .03
            # News has an explicit fixed initial stop: $4 gold / .08 silver.
            r['risk_per_lot'] = 400.0 if r['news'] else r['estimated_risk_cash']/r['volume']
            r['carry_units'] = rollover_units(r['op'], r['cl'], SPEC[r['symbol']]['triple'])
            out.append(r)
        rows[key] = out
        audit.append(dict(key=key, label=summary['label'], stats=summary.get('stats'),
                          history_quality=summary.get('history_quality'), notice=summary.get('notice'),
                          path=str(p), sha256=hashlib.sha256(p.with_name('5y.trades.json').read_bytes()).hexdigest()))
    return rows, audit, excluded

def costs(r, lots, severity='stress'):
    factor = lots/r['volume']
    risk = lots*r['risk_per_lot']
    gross = r['gross_profit']*factor
    commission = r['commission']*factor
    swap = r['swap']*factor
    extra = 0.0
    if severity != 'source':
        if severity == 'severe':
            positive, negative, slip = (.4, 2., .5) if r['news'] else (.75, 1.3, .10)
        else:
            positive, negative, slip = (.65, 1.25, .15) if r['news'] else (.90, 1.1, .02)
        gross *= positive if gross > 0 else negative
        commission = -max(abs(commission), (0.7 if r['symbol']=='USTEC' else 7.)*lots)
        spec = SPEC[r['symbol']]
        carry = spec['carry_long' if r['side']=='Long' else 'carry_short']*lots*r['carry_units']
        swap = -max(max(0., -swap)*2, carry)
        extra = risk*slip
        if r['symbol']=='USDJPY':
            # Global terms 5.3.4: 0.7% realized P/L conversion adjustment.
            extra += abs(gross)*.007
    return gross, commission, swap, extra

def stats(vals):
    win = sum(v for v in vals if v > 0)
    loss = -sum(v for v in vals if v < 0)
    return dict(trades=len(vals), win_rate=100*sum(v>0 for v in vals)/max(1,len(vals)),
                pf=win/loss if loss else None, sum_r=sum(vals), mean_r=sum(vals)/max(1,len(vals)))

def screen(rows):
    out = []
    for key, rr in rows.items():
        item = dict(key=key)
        for name, lo, hi in [('early', START, SPLIT), ('recent', SPLIT, END), ('full', START, END)]:
            selected = [r for r in rr if lo <= r['op'] and r['cl'] < hi]
            for severity in ['source', 'stress']:
                values=[]
                for r in selected:
                    g,c,s,x=costs(r,r['volume'],severity)
                    values.append((g+c+s-x)/(r['risk_per_lot']*r['volume']))
                item[name+'_'+severity]=stats(values)
        out.append(item)
    return sorted(out,key=lambda r:r['early_stress']['sum_r'],reverse=True)

def business_days(at, n):
    while n:
        at += timedelta(days=1)
        if at.weekday()<5:
            n-=1
    return at

def events_for(rows, start, end):
    events=[]
    for r in rows:
        # Do not throw away trades whose exit lies beyond the test horizon.
        if start <= r['op'] < end:
            events.append((r['op'],2,r['uid'],r))
            if r['cl'] <= end:
                events.append((r['cl'],1,r['uid'],r))
    d=start.astimezone(PRAGUE).date()
    while True:
        t=datetime.combine(d,time(),PRAGUE).astimezone(UTC)
        if t>end: break
        if t>=start: events.append((t,0,'',None))
        d+=timedelta(days=1)
    events.append((end,3,'',None))
    return sorted(events,key=lambda e:e[:3])

def replay(rows, start, end, risk=.5, news_risk=.125, severity='stress', challenge=True, detailed=False,
           news_policy=None, news_calendar=None):
    balance=peak=anchor=ACCOUNT
    active={}
    streak=Counter()
    counts=Counter()
    records=[]
    phase=1 if challenge else 3
    days=set()
    ready=start
    first_funded=None
    funded=None
    passed=[]
    request=None
    payout_at=None
    payout=0
    breach=None
    halt=None
    daily_opens=0
    daily_losses=0
    last_entry=start
    inactivity=None
    day_key=None
    max_dd=max_daily=max_envelope=0.
    max_risk=max_margin=0.
    # An extra opposite-side news reservation stays until event cleanup.
    reserved={}
    news_lots={}
    total_net=0.
    news_events_today=0
    counts_by_ea=defaultdict(Counter)
    event_list=events_for(rows,start,end)
    if news_policy:
        assert news_calendar is not None, 'Use the full calendar, including events with no fills.'
        for release in news_calendar:
            place=release-timedelta(seconds=30)
            if start<=place<end:
                event_list.append((place,1.5,'basket:'+release.isoformat(),{'release':release}))
                if release+timedelta(seconds=60)<=end:
                    event_list.append((release+timedelta(seconds=60),2.5,'expiry',None))
        event_list.sort(key=lambda e:e[:3])
    for at,kind,uid,r in event_list:
        date=at.astimezone(PRAGUE).date()
        if date!=day_key:
            day_key=date
            anchor=balance
            daily_opens=daily_losses=0
            news_events_today=0
        reserved={k:v for k,v in reserved.items() if at<v['until']}
        if payout_at or breach or halt:
            break
        if phase<3 and at>=ready and at-last_entry>=timedelta(days=30):
            # Contract permits termination: do not assume renewal or fake trades.
            inactivity=last_entry+timedelta(days=30)
            break
        if kind==1 and uid in active:
            p=active.pop(uid)
            g,c,s,x=p['costs']
            balance+=g+c/2+s-x
            net=g+c+s-x
            total_net+=g+c/2+s-x
            streak[r['key']] = streak[r['key']]+1 if net<0 else 0
            daily_losses+=net<0
            counts['closed']+=1
            counts_by_ea[r['key']]['closed']+=1
            counts_by_ea[r['key']]['net']+=net
            counts_by_ea[r['key']]['wins']+=net>0
            counts['win']+=net>0
            counts['positive']+=max(0,net)
            counts['negative']+=max(0,-net)
            if detailed:
                records.append(dict(key=r['key'],op=r['op'],cl=at,phase=p['phase'],lots=p['lots'],risk=p['risk'],net=net))
        elif kind==1.5:
            # Reserve BOTH sides of ALL selected metals using the official calendar,
            # before seeing whether any side fills. Current-price margin is a fixed
            # scenario assumption, not an entry price learned from a future fill.
            counts['news_events_checked']+=1
            target=ACCOUNT*(1.10 if phase==1 else 1.05) if phase<3 else ACCOUNT+225
            if at<ready or (balance>=target and (phase==3 or len(days)>=4)):
                counts['news_phase_or_target']+=1;continue
            if news_events_today>=1 or daily_losses>=3 or anchor-balance>=150:
                counts['news_daily_stop']+=1;continue
            proposals={}
            for symbol,pct in news_policy.items():
                key='news-pulse-'+('xau' if symbol=='XAUUSD' else 'xag')+'/standard'
                fraction=min(pct,.15) if phase==3 else pct
                if (peak-balance)/peak>=.04 or streak[key]>=3:fraction*=.5
                commission_allowance=50. if symbol=='XAGUSD' else 7.
                lots=math.floor((min(balance,ACCOUNT)*fraction/100/(600.+commission_allowance))/.01+1e-9)*.01
                if lots<.01:break
                for side in ['Long','Short']:
                    token=('basket',r['release'].isoformat(),symbol,side)
                    proposals[token]=dict(lots=lots,risk=400.*lots,env=(600.+commission_allowance)*lots,
                        margin=lots*SPEC[symbol]['contract']*SPEC[symbol]['price']/SPEC[symbol]['leverage'],
                        group='metals',until=r['release']+timedelta(seconds=60),key=key)
            if len(proposals)!=2*len(news_policy):
                counts['news_minimum_lot']+=1;continue
            held=list(active.values())+list(reserved.values())
            env=sum(v['env'] for v in proposals.values())
            open_env=sum(v['env'] for v in held)
            metal_env=sum(v['env'] for v in held if v['group']=='metals')
            if open_env+env>150+1e-8 or metal_env+env>100+1e-8:
                counts['news_exposure_cap']+=1;continue
            if anchor-balance+open_env+env>200 or balance-open_env-env<9400:
                counts['news_risk_room']+=1;continue
            margin=sum(v['margin'] for v in held)+sum(v['margin'] for v in proposals.values())
            if margin>.60*(balance-open_env):
                counts['news_margin_cap']+=1;continue
            reserved.update(proposals)
            news_events_today+=1
            counts['news_events_admitted']+=1
        elif kind==2 and r['news'] and news_policy:
            release=dt(r['news_event_utc'])
            token=('basket',release.isoformat(),r['symbol'],r['side'])
            p=reserved.pop(token,None)
            if p is None:
                counts['news_unreserved_fill']+=1;continue
            # Do not cancel the opposite side merely because one side filled/lost.
            # Previously reserved fills are conversions of exposure, not new risk.
            g,c,s,x=costs(r,p['lots'],severity)
            balance+=c/2
            p.update(costs=(g,c,s,x),phase=phase)
            active[uid]=p
            days.add(date)
            last_entry=at
            counts['opened']+=1
            counts['news_opened']+=1
            if phase==3 and first_funded is None:first_funded=at
        elif kind==2:
            if at<ready:
                counts['phase_pause']+=1;continue
            # Once a target is banked, wait for natural exits; never fabricate liquidation prices.
            target=ACCOUNT*(1.10 if phase==1 else 1.05) if phase<3 else ACCOUNT+225
            if balance>=target and (phase==3 or len(days)>=4):
                counts['target_lock']+=1;continue
            if daily_opens>=4 or daily_losses>=3 or anchor-balance>=150:
                counts['daily_stop']+=1;continue
            fraction=min(risk,.25) if phase==3 else risk
            if r['news']:fraction=news_risk
            # Exposure is a capped fraction of INITIAL capital or lower current balance.
            dd=(peak-balance)/peak
            fraction*=.5 if dd>=.04 or streak[r['key']]>=3 else 1.
            requested=min(balance,ACCOUNT)*fraction/100
            # Count commissions/adverse-execution allowance inside requested budget.
            reserve_mult=(1.5 if r['news'] else 1.12)
            unit_comm=0.7 if r['symbol']=='USTEC' else 7.
            unit_cost=r['risk_per_lot']*reserve_mult+unit_comm
            lots=math.floor((requested/unit_cost)/.01+1e-9)*.01
            event=None
            if r['news']:
                event=(r['key'],r.get('news_event_utc',r['op'].replace(second=0).isoformat()))
                if event in news_lots:
                    lots=news_lots[event]
            if lots<.01:
                counts['minimum_lot']+=1;continue
            spec=SPEC[r['symbol']]
            required_margin=lots*spec['contract']*(1 if r['symbol']=='USDJPY' else max(spec['price'],r['open_price']))/spec['leverage']
            rc=lots*r['risk_per_lot']
            env=rc*reserve_mult+unit_comm*lots
            g,c,s,x=costs(r,lots,severity)
            # Actual holding duration is not used in admission: future swap is unknown.
            other_res=[v for k,v in reserved.items() if k!=event]
            reserve_extra=1 if r['news'] and event not in news_lots else 0
            open_env=sum(p['env'] for p in active.values())+sum(v['env'] for v in other_res)
            new_env=env*(1+reserve_extra)
            group='metals' if r['symbol'] in ['XAUUSD','XAGUSD'] else r['symbol']
            group_env=sum(p['env'] for p in active.values() if p['group']==group)+sum(v['env'] for v in other_res if v['group']==group)
            margins=sum(p['margin'] for p in active.values())+sum(v['margin'] for v in other_res)
            if open_env+new_env>150+1e-8 or group_env+new_env>100+1e-8:
                counts['exposure_cap']+=1;continue
            if anchor-balance+open_env+new_env>200 or balance-open_env-new_env<9400:
                counts['risk_room']+=1;continue
            if margins+required_margin*(1+reserve_extra)>.60*(balance-open_env):
                counts['margin_cap']+=1;continue
            if event:
                if event not in news_lots:
                    news_lots[event]=lots
                    until=dt(r.get('news_event_utc',r['op'].isoformat()))+timedelta(seconds=60)
                    reserved[event]=dict(env=env,margin=required_margin,until=until,group=group)
                else:
                    reserved.pop(event,None)
            balance+=c/2
            total_net+=c/2
            active[uid]=dict(lots=lots,risk=rc,env=env,margin=required_margin,costs=(g,c,s,x),phase=phase,group=group)
            days.add(date)
            daily_opens+=1
            last_entry=at
            counts['opened']+=1
            if phase==3 and first_funded is None:first_funded=at
        peak=max(peak,balance)
        risk_open=sum(p['env'] for p in active.values())+sum(v['env'] for v in reserved.values())
        eq=balance-risk_open
        max_risk=max(max_risk,risk_open)
        max_margin=max(max_margin,sum(p['margin'] for p in active.values())+sum(v['margin'] for v in reserved.values()))
        max_dd=max(max_dd,(peak-balance)/peak*100)
        max_daily=max(max_daily,anchor-balance)
        max_envelope=max(max_envelope,anchor-eq)
        # Only modeled deal endpoints, NOT a certification of real intratrade limits.
        if balance<9000 or anchor-balance>500:
            breach=at;break
        if balance<9400 and not active:
            halt=at;break
        if phase<3 and not active and not reserved and len(days)>=4 and balance>=ACCOUNT*(1.10 if phase==1 else 1.05):
            passed.append(dict(phase=phase,at=at,days=(at-start).total_seconds()/86400,entry_days=len(days),balance=balance))
            phase+=1
            ready=business_days(at,2 if phase==2 else 5)
            last_entry=ready
            balance=peak=anchor=ACCOUNT
            days=set();streak.clear();daily_opens=daily_losses=0
            if phase==3:funded=ready
        if phase==3 and first_funded and not active and not reserved and balance>=10225 and at>=first_funded+timedelta(days=14):
            request=at
            payout=.8*(balance-10100)
            payout_at=business_days(at,4)
            break
    elapsed=lambda d: (d-start).total_seconds()/86400 if d else None
    result=dict(balance=balance,phase=phase,phase1_day=passed[0]['days'] if passed else None,
                funded_day=elapsed(funded),payout_day=elapsed(payout_at),payout=payout,
                breach_day=elapsed(breach),safety_halt_day=elapsed(halt),open_positions=len(active),
                inactivity_day=elapsed(inactivity),
                max_closed_dd_pct=max_dd,max_closed_daily_loss=max_daily,max_stop_envelope_daily_loss=max_envelope,
                max_open_envelope=max_risk,max_margin=max_margin,counts=dict(counts),phases=passed,
                wins_pct=100*counts['win']/max(1,counts['closed']),
                pf=counts['positive']/counts['negative'] if counts['negative'] else None,
                trades=records if detailed else [])
    result['by_ea']={key:dict(value) for key,value in counts_by_ea.items()}
    return result

def windows(lo,hi,horizon=60):
    first=lo+timedelta(days=(-lo.weekday())%7)
    out=[]
    while first+timedelta(days=horizon)<=hi:
        out.append(first)
        first+=timedelta(days=7)
    return out

def aggregate(results,horizon=60):
    n=len(results)
    count=lambda key,h:sum(r[key] is not None and r[key]<=h for r in results)
    fund=count('funded_day',horizon)
    pay=[r['payout'] for r in results if r['payout_day'] is not None and r['payout_day']<=horizon]
    return dict(n=n,phase1_30=count('phase1_day',30)/n*100,
                funded30=count('funded_day',30)/n*100,funded60=fund/n*100,
                payout60=len(pay)/n*100,breach60=count('breach_day',horizon)/n*100,
                safety_halt60=count('safety_halt_day',horizon)/n*100,
                inactivity60=count('inactivity_day',horizon)/n*100,
                median_trades=median(r['counts'].get('closed',0) for r in results),
                median_balance=median(r['balance'] for r in results),
                payout_if_paid_median=median(pay) if pay else None,
                max_closed_dd=max(r['max_closed_dd_pct'] for r in results),
                max_stop_envelope_daily_loss=max(r['max_stop_envelope_daily_loss'] for r in results))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--screen',action='store_true');args=ap.parse_args()
    bykey,audit,excluded=load()
    screening=screen(bykey)
    save('screen.json',screening);save('data-audit.json',dict(included=audit,excluded=excluded))
    for s in screening:
        print(s['key'], 'early',s['early_stress']['trades'],round(s['early_stress']['sum_r'],1),
              'recent',s['recent_stress']['trades'],round(s['recent_stress']['sum_r'],1),
              'fullWR',round(s['full_source']['win_rate'],1),'PF',round(s['full_stress']['pf'] or 0,2),flush=True)
    if args.screen:return
    # Small declared menu. No entry/exit optimization and no exhaustive hindsight subset search.
    core=['xau-rsi-vwap/standard','ema3/safe','us100-h1-orb-13utc/standard',
          'us100-orb-new-york-m30/standard','usdjpy-london-open-momentum/standard',
          'xau-trend-progression/standard']
    wider=core+['orb-volume-profile-volume-confirmed/standard','xau-squeeze-momentum-standard/standard']
    withnews=wider+['news-pulse-xau/standard','news-pulse-xag/standard']
    # Positive stressed normalized expectancy in BOTH early and recent subsets.
    # This is an ex-post robustness screen, not an untouched out-of-sample test.
    robust=['xau-trend-progression/standard','xau-squeeze-momentum-standard/safe',
            'us100-orb-new-york-m30/standard','us100-selective-orb-v3/standard',
            'xau-elliott-wave-1-2-3/standard']
    robust_active=robust+['us100-h1-orb-13utc/standard','ema3/safe']
    configs=[('Core conservative',core,.25,0),('Core balanced',core,.5,0),
             ('Diversified balanced',wider,.5,0),('Diversified faster',wider,.75,0),
             ('Conditional news balanced',withnews,.5,.125),
             ('Conditional news faster',withnews,.75,.25),
             ('Robust five',robust,.5,0),
             ('Robust seven',robust_active,.5,0),
             ('Robust seven faster',robust_active,.75,0),
             ('Robust seven plus conditional XAU',robust_active+['news-pulse-xau/standard'],.5,.25)]
    allstarts=windows(START,END)
    early=windows(START,SPLIT)
    recent=windows(SPLIT,END)
    rng=random.Random(20260919)
    sample=[rng.choice(allstarts) for _ in range(1000)]
    results=[];paths=[]
    for name,keys,risk,nrisk in configs:
        rr=[r for key in keys for r in bykey[key]]
        for severity in ['source','stress','severe']:
            unique={s:replay(rr,s,s+timedelta(days=60),risk,nrisk,severity) for s in sorted(set(allstarts+early+recent))}
            row=dict(name=name,keys=keys,risk=risk,news_risk=nrisk,severity=severity,
                     full=aggregate([unique[s] for s in allstarts]),
                     early=aggregate([unique[s] for s in early]),
                     recent=aggregate([unique[s] for s in recent]),
                     bootstrap1000=aggregate([unique[s] for s in sample]))
            results.append(row)
            paths.append(dict(name=name,severity=severity,paths=[dict(start=s,**r) for s,r in unique.items()]))
            print('RESULT',name,severity,json.dumps(row['full']),flush=True)
    save('results.json',dict(account=ACCOUNT,start=START,end=END,split=SPLIT,results=results))
    save('paths.json',paths)
    extended=[]
    for name,keys,risk,nrisk in configs[6:]:
        rr=[r for key in keys for r in bykey[key]]
        for horizon in [180,365]:
            for severity in ['source','stress']:
                ss=windows(START,END,horizon)
                vals=[replay(rr,s,s+timedelta(days=horizon),risk,nrisk,severity) for s in ss]
                summary=aggregate(vals,horizon)
                # aggregate uses legacy field labels; rename variable-horizon fields.
                for prefix in ['funded','payout','breach','safety_halt','inactivity']:
                    summary[prefix+'_by_horizon']=summary.pop(prefix+'60')
                timings=[v['funded_day'] for v in vals if v['funded_day'] is not None and v['funded_day']<=horizon]
                summary['median_funded_days_if_funded']=median(timings) if timings else None
                extended.append(dict(name=name,horizon=horizon,severity=severity,**summary))
                print('EXTENDED',name,horizon,severity,json.dumps(summary),flush=True)
    save('extended.json',extended)

if __name__=='__main__':main()
