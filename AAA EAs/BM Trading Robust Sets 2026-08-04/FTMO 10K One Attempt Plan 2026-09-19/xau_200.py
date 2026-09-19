"""XAU News Pulse alone, fixed $100 initial-stop risk per side.

Research-only saved-deal replay. No order placement or production changes.
No portfolio/adaptive taper: requested fixed risk remains through all stages.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, time
from statistics import median
import hashlib
import json
import random
from simulate import (OUT, START, END, UTC, PRAGUE, SPEC, ACCOUNT, load, read,
                      dt, costs, stats, business_days, windows, save)
from news_compare import calendar, CALENDAR

LOT=.25
STOP=4.
CONTRACT=100.
PRICE=4348.
LEVERAGE=15.
MARGIN_ONE=LOT*CONTRACT*PRICE/LEVERAGE
KEY='news-pulse-xau/standard'

def chronology(rows, releases, start, end):
    out=[]
    for e in releases:
        p=e-timedelta(seconds=15)
        if start<=p<end:
            out.append((p,1.5,e.isoformat(),dict(release=e)))
            if e+timedelta(seconds=60)<=end:out.append((e+timedelta(seconds=60),2.5,e.isoformat(),None))
    for r in rows:
        if start<=r['op']<end:
            out.append((r['op'],2,r['uid'],r))
            if r['cl']<=end:out.append((r['cl'],1,r['uid'],r))
    day=start.astimezone(PRAGUE).date()
    while True:
        stamp=datetime.combine(day,time(),PRAGUE).astimezone(UTC)
        if stamp>end:break
        if stamp>=start:out.append((stamp,0,'',None))
        day+=timedelta(days=1)
    out.append((end,3,'',None))
    return sorted(out,key=lambda x:x[:3])

def performance(rows,start,end,severity):
    rr=[r for r in rows if start<=r['op']<end and r['cl']<=end]
    cash=peak=anchor=ACCOUNT;max_dd=dd_usd=daily_loss=0.;day=None
    events=[];values=[];evnet=Counter();comm=swap=gross=extra=0.
    for r in rr:
        g,c,s,x=costs(r,LOT,severity)
        values.append(g+c+s-x);evnet[r['news_event_utc']]+=g+c+s-x
        gross+=g;comm+=c;swap+=s;extra+=x
        events.extend([(r['op'],c/2),(r['cl'],g+c/2+s-x)])
    for at,change in sorted(events):
        date=at.astimezone(PRAGUE).date()
        if day!=date:day=date;anchor=cash
        cash+=change;peak=max(peak,cash)
        dd_usd=max(dd_usd,peak-cash)
        max_dd=max(max_dd,(peak-cash)/peak*100)
        daily_loss=max(daily_loss,anchor-cash)
    metrics=stats(values)
    metrics['sum_net_usd']=metrics.pop('sum_r')
    metrics['mean_trade_net_usd']=metrics.pop('mean_r')
    return dict(start=start,end=end,severity=severity,**metrics,net=cash-ACCOUNT,balance=cash,
                return_pct=(cash/ACCOUNT-1)*100,max_closed_dd_pct=max_dd,max_closed_dd_usd=dd_usd,
                worst_closed_day=daily_loss,worst_event_net=min(evnet.values(),default=0),
                events_with_fills=len(evnet),commission=comm,swap=swap,extra_execution=extra,gross=gross,
                worst_trade=min(values,default=0))

def challenge(rows,releases,start,end,severity='stress',margin_mode='paper',max_events_day=None):
    balance=peak=anchor=ACCOUNT
    phase=1;ready=start;last_entry=start;first_funded=None;funded=None;payout=None;payout_day=None
    days=set();active={};reserved={};day_key=None;day_events=0
    counts=Counter();phases=[];breach=None;breach_reason=None;inactivity=None
    maxdd=maxdaily=0.;net_all=0.;accepted_event_times=[]
    for at,kind,uid,r in chronology(rows,releases,start,end):
        date=at.astimezone(PRAGUE).date()
        if date!=day_key:
            day_key=date;anchor=balance;day_events=0
        reserved={k:v for k,v in reserved.items() if at<v['until']}
        if phase<3 and at>=ready and at-last_entry>=timedelta(days=30):
            inactivity=(last_entry-start).total_seconds()/86400+30;break
        if kind==1 and uid in active:
            g,c,s,x=active.pop(uid)
            balance+=g+c/2+s-x;net_all+=g+c/2+s-x
            counts['closed']+=1;counts['win']+=g+c+s-x>0
            counts['positive']+=max(0,g+c+s-x);counts['negative']+=max(0,-g-c-s+x)
        elif kind==1.5:
            counts['scheduled']+=1
            target=ACCOUNT+(1000 if phase==1 else 500 if phase==2 else 225)
            if at<ready or (balance>=target and (phase==3 or len(days)>=4)):
                counts['phase_or_target']+=1;continue
            if max_events_day and day_events>=max_events_day:
                counts['day_quota']+=1;continue
            # Fixed current-price feasibility scenarios, NOT verified server rules.
            # No old 60%/150-dollar portfolio caps silently applied to this request.
            required=2*MARGIN_ONE if margin_mode=='gross_reservation' else 0
            if required>balance:
                counts['margin_blocked']+=1;continue
            until=r['release']+timedelta(seconds=60)
            for side in ['Long','Short']:reserved[(r['release'],side)]=dict(until=until)
            counts['events_admitted']+=1;day_events+=1;accepted_event_times.append(at)
        elif kind==2:
            token=(dt(r['news_event_utc']),r['side'])
            if token not in reserved:
                counts['unreserved_fills']+=1;continue
            reserved.pop(token)
            if margin_mode=='on_fill' and MARGIN_ONE*(len(active)+1)>balance:
                counts['activation_margin_rejected']+=1;continue
            g,c,s,x=costs(r,LOT,severity)
            balance+=c/2;net_all+=c/2
            active[uid]=(g,c,s,x)
            days.add(date);last_entry=at;counts['opened']+=1
            if phase==3 and first_funded is None:first_funded=at
        peak=max(peak,balance)
        maxdd=max(maxdd,(peak-balance)/peak*100);maxdaily=max(maxdaily,anchor-balance)
        if balance<9000 or anchor-balance>500:
            breach=(at-start).total_seconds()/86400
            breach_reason='total' if balance<9000 else 'daily';break
        if phase<3 and not active and not reserved and len(days)>=4 and balance>=ACCOUNT+(1000 if phase==1 else 500):
            phases.append(dict(phase=phase,days=(at-start).total_seconds()/86400,entry_days=len(days),balance=balance))
            phase+=1;ready=business_days(at,2 if phase==2 else 5)
            last_entry=ready;balance=peak=anchor=ACCOUNT;days=set()
            if phase==3:funded=ready
        if phase==3 and first_funded and not active and not reserved and balance>=10225 and at>=first_funded+timedelta(days=14):
            payout=.8*(balance-10100);payout_day=business_days(at,4);break
    elapsed=lambda x:(x-start).total_seconds()/86400 if x else None
    return dict(balance=balance,total_net_across_stages=net_all,phase=phase,phases=phases,
                phase1_day=phases[0]['days'] if phases else None,funded_day=elapsed(funded),
                payout_day=elapsed(payout_day),payout=payout,breach_day=breach,breach_reason=breach_reason,
                inactivity_day=inactivity,counts=dict(counts),max_closed_dd_pct=maxdd,
                max_closed_daily_loss=maxdaily,open_positions=len(active))

def summarize(vals,horizon):
    count=lambda key,limit:sum(v[key] is not None and v[key]<=limit for v in vals)
    pct=lambda key,limit:100*count(key,limit)/len(vals)
    return dict(n=len(vals),phase1_by30=pct('phase1_day',30),funded_by30=pct('funded_day',30),
                funded_by_horizon=pct('funded_day',horizon),payout_by_horizon=pct('payout_day',horizon),
                breach_by_horizon=pct('breach_day',horizon),inactivity_by_horizon=pct('inactivity_day',horizon),
                median_trades=median(v['counts'].get('closed',0) for v in vals),
                median_balance=median(v['balance'] for v in vals),
                median_net_all_stages=median(v['total_net_across_stages'] for v in vals),
                max_closed_dd=max(v['max_closed_dd_pct'] for v in vals),
                max_closed_daily_loss=max(v['max_closed_daily_loss'] for v in vals),
                counts={key:count(key,horizon) for key in ['funded_day','payout_day','breach_day','inactivity_day']})

def main():
    bykey,audit,_=load();rows=bykey[KEY];cal=calendar()
    periods=[('6 months',dt('2026-03-01T00:00:00Z')),('1 year',dt('2025-09-01T00:00:00Z')),
             ('3 years',dt('2023-09-01T00:00:00Z')),('~5 years',START)]
    perf=[dict(period=label,**performance(rows,start,END,sev)) for label,start in periods for sev in ['source','stress','severe']]
    yearly=[dict(year=year,**performance(rows,max(START,datetime(year,1,1,tzinfo=UTC)),min(END,datetime(year+1,1,1,tzinfo=UTC)),sev))
            for year in range(2021,2027) for sev in ['source','stress','severe']]
    result=[];paths=[]
    for horizon in [60,180,365]:
        starts=windows(START,END,horizon)
        unique_days=[len({e.astimezone(PRAGUE).date() for e in cal if s<=e<s+timedelta(days=horizon)}) for s in starts]
        for severity in ['source','stress','severe']:
            vals=[challenge(rows,cal,s,s+timedelta(days=horizon),severity) for s in starts]
            a=dict(horizon=horizon,severity=severity,margin_mode='paper',max_news_days=max(unique_days),
                   **summarize(vals,horizon))
            if horizon==60:
                rng=random.Random(20260919)
                a['bootstrap1000']=summarize([rng.choice(vals) for _ in range(1000)],horizon)
            result.append(a)
            paths.append(dict(horizon=horizon,severity=severity,paths=[dict(start=s,**v) for s,v in zip(starts,vals)]))
            print('CHALLENGE',json.dumps(a),flush=True)
    starts=windows(START,END,60)
    for mode in ['gross_reservation','on_fill']:
        vals=[challenge(rows,cal,s,s+timedelta(days=60),'stress',mode) for s in starts]
        result.append(dict(horizon=60,severity='stress',margin_mode=mode,**summarize(vals,60)))
    max_days_30=max(len({e.astimezone(PRAGUE).date() for e in cal if s<=e<s+timedelta(days=30)}) for s in starts)
    grouped=defaultdict(list)
    for r in rows:grouped[r['news_event_utc']].append(r)
    doubles=[v for v in grouped.values() if len(v)>1]
    strict_overlaps=sum(max(r['op'] for r in v)<min(r['cl'] for r in v) for v in doubles)
    same_second=sum(max(r['op'] for r in v)==min(r['cl'] for r in v) for v in doubles)
    data=dict(account=ACCOUNT,lot=LOT,initial_stop=STOP,risk_per_side=100,event_planned_stop_risk=200,
              model_price=PRICE,leverage=LEVERAGE,margin_one=MARGIN_ONE,margin_gross=2*MARGIN_ONE,
              double_fill_events=len(doubles),strict_overlap_events=strict_overlaps,same_second_handoffs=same_second,
              max_news_days_30=max_days_30,calendar=str(CALENDAR),
              provenance=next(a for a in audit if a['key']==KEY),performance=perf,yearly=yearly,challenges=result)
    save('xau-200-results.json',data);save('xau-200-paths.json',paths)
    write_report(data)
    for r in perf:print('PERFORMANCE',json.dumps(r,default=str),flush=True)

def write_report(d):
    lines=['# XAU News Pulse alone: $100 per order / $200 per event','',
           'Research only. $10,000 initial account; fixed 0.25 lot on each pending side, with a $4 initial gold stop and 100 oz/lot assumption. No compounding, adaptive taper or funded-stage size reduction. Both directions remain armed. Fees, slippage and gaps are ADDITIONAL to the $100 initial-stop risk, not included within it.', '',
           '## Scope and limitations','',
           '- Same saved Exness v2.16 XAU deal evidence as the preceding comparisons. FTMO tick probe returned no data again. No fresh native FTMO tester run, no live orders, no BAT or production changes.',
           '- Both source and stressed results use historical recorded fills, not newly simulated entry paths. Source fill prices contain the broker spread; commission and swap scale with lots. Source history reports 13% real ticks and 1 ms tester delay: historical news fills are especially uncertain.',
           '- Source: unchanged recorded gross P/L, commission and swap. Stress: gross winners x0.65, losers x1.25, minus 0.15R additional execution cost, commission at least $7/lot round trip. Severe: winners x0.40, losers x2, minus 0.50R, same commission floor. These are hypothetical sensitivities, not measured FTMO slippage.',
           '- No change to entry/exit geometry: T-15, live Ask/Bid +/− $4 offsets, $4 initial SL, no TP/trailing, cleanup T+60. All scheduled eligible CPI/NFP/FOMC releases can trade, including two releases on the same day. No old $100 metals cap, $150 portfolio cap, $200 daily safeguard or 60% margin cap is silently retained.',
           '- Performance tables are fixed-size paper replays with no challenge loss halt, phase reset or margin rejection. They answer the trading idea, NOT whether a prop account survives the full period. Drawdown uses closed balance, not tick equity.',
           '- Challenge replay has separate 10%/5% phases, four Prague-calendar entry days each, equity-rule proxies checked only at recorded cash endpoints, 30-day inactivity termination scenario, and 2/5 business-day transition assumptions. No retries. Funded size remains 0.25 lot as requested. First modeled reward requires $225 profit after costs, leaves $100, pays 80% remainder after >=14 days from first funded entry and 4 business days processing.',
           '- Overlapping weekly-start windows and 1,000 whole-window resamples are descriptive historical frequencies, not independent observations or reliable future pass probabilities. Each horizon has a different eligible starting-date cohort: the 180/365-day percentages must not be read as a cumulative probability curve. Longer horizons exclude more of the newest, strongest starting dates. Numerical completion does not model KYC or discretionary acceptance.',
           '', '## Fixed-risk performance', '',
           '| Period | Costs | Trades | Win rate | PF | Net USD | Ending balance | Return | Closed-balance DD | Worst closed day |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in d['performance']:
        lines.append(f"| {r['period']} | {r['severity']} | {r['trades']} | {r['win_rate']:.2f}% | {r['pf']:.2f} | ${r['net']:+,.2f} | ${r['balance']:,.2f} | {r['return_pct']:+.2f}% | {r['max_closed_dd_pct']:.2f}% | ${r['worst_closed_day']:,.2f} |")
    lines += ['', 'All periods end 31 August 2026 exclusive. Starts: 1 March 2026, 1 September 2025, 1 September 2023, and 7 September 2021. The last interval is approximately five years, matching the preceding portfolio comparison.',
              '', '## One-attempt challenge outcomes', '',
              '| Days | Cost scenario | Margin scenario | Windows | Phase 1 by 30d | Funded by 30d | Funded by horizon | >=$100 payout by horizon | Recorded-close breach | Inactivity stop | Median closed trades |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in d['challenges']:
        lines.append(f"| {r['horizon']} | {r['severity']} | {r['margin_mode']} | {r['n']} | {r['phase1_by30']:.1f}% | {r['funded_by30']:.1f}% | {r['funded_by_horizon']:.1f}% | {r['payout_by_horizon']:.1f}% | {r['breach_by_horizon']:.1f}% | {r['inactivity_by_horizon']:.1f}% | {r['median_trades']:g} |")
    lines += ['', 'The paper rows ignore broker margin eligibility. gross_reservation is OUR conservative policy requiring full funding of both sides before placement; its zero trades do NOT prove MT5 would reject all pending orders. on_fill instead tests gross margin at each cached fill, with exits processed before entries at equal second timestamps and no continuous floating-equity check. Actual server pending-order margin rates remain unverified. Endpoint breach rates are LOWER-INFORMATION proxies, not certified equity-rule failure rates.',
              '', '## Margin and deadline checks', '',
              f"At assumed gold ${PRICE:,.0f}/oz, 100 oz/lot and 1:{LEVERAGE:g}: one side needs ${MARGIN_ONE:,.2f}; both gross need ${2*MARGIN_ONE:,.2f}. Full simultaneous gross exposure exceeds $10K. Even one side exceeds the previous 60% usage policy. FTMO's 22 August 2024 update states that OPEN hedged positions use the sum of both margins. Pending-stop placement/activation requirements still need verification on the actual Swing product.",
              f"There are {d['double_fill_events']} saved events with both directions filled: {d['strict_overlap_events']} strictly overlap in recorded open/close times, and {d['same_second_handoffs']} has a same-second handoff whose tick ordering is unknown. Both pending orders staying armed does not mean both positions remain open simultaneously. Therefore neither guaranteed rejection nor guaranteed execution is claimed.",
              f"The sampled calendar has at most {d['max_news_days_30']} distinct eligible news days in a 30-day window and seven in a tested 60-day window. Each phase requires four separate entry dates. With OUR modeled two-business-day handover, these require eight distinct calendar dates across the two phases; this is not a separate FTMO eight-day rule. The assumed handover and sparse calendar create a structural 60-day completion bottleneck, independent of profit sizing.",
              '', '## Calendar-year paper results', '', '| Year | Costs | Trades | Net USD | Win rate | PF | Closed-balance DD |', '|---|---|---:|---:|---:|---:|---:|']
    for r in d['yearly']:
        lines.append(f"| {r['year']} | {r['severity']} | {r['trades']} | ${r['net']:+,.2f} | {r['win_rate']:.1f}% | {r['pf']:.2f} | {r['max_closed_dd_pct']:.2f}% |")
    lines += ['', '2021 and 2026 are partial years. Each yearly row starts from a fresh $10K for its drawdown calculation.', '',
              '[FTMO gold Swing leverage](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/) | [Hedged margin](https://ftmo.com/en/blog/trading-updates/trading-update-22-aug-2024/) | [Pending-order activation](https://www.metatrader5.com/en/terminal/help/trading/general_concept) | [2-Step objectives](https://ftmo.com/en/trading-objectives/) | [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/)', '']
    (OUT/'XAU-200-PER-EVENT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
