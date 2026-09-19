"""Research-only XAU/XAG news allocation comparison. No native FTMO runs."""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from statistics import median, quantiles
from simulate import (OUT, CACHE, START, END, UTC, SPEC, load, read, dt, save,
                      replay, aggregate, windows, screen, costs, stats)

CALENDAR = CACHE.parents[4]/'BM Trading Robust Sets 2026-08-04'/'News Pulse Full Coverage 2026-09-12'/'NewsPulseTesterCalendar.mqh'

def calendar():
    source=CALENDAR.read_text(encoding='utf-8-sig')
    match=re.search(r'NP_GENERATED_EVENT_UTC_EPOCHS\[\]=\{([^}]+)',source)
    return sorted({datetime.fromtimestamp(int(x),UTC) for x in match[1].split(',')})

def main():
    bykey,audit,_=load()
    keys=next(x['keys'] for x in read(OUT/'results.json')['results'] if x['name']=='Robust seven')
    releases=calendar()
    assert len(releases)==158
    newskeys=['news-pulse-xau/standard','news-pulse-xag/standard']
    seen=Counter()
    for key in newskeys:
        for r in bykey[key]:
            e=dt(r['news_event_utc'])
            assert e in releases
            assert e-timedelta(seconds=30)<=r['op']<=e+timedelta(seconds=60)
            seen[(key,e,r['side'])]+=1
    assert max(seen.values())==1, 'Each side must have only one fill per event.'
    # Percent of capped initial/current balance PER SIDE, includes stress reserve.
    configs=[('Seven only',{}),
             ('Gold only',{'XAUUSD':.25}),
             ('Silver only',{'XAGUSD':.25}),
             ('Both small',{'XAUUSD':.125,'XAGUSD':.125}),
             ('Both 15',{'XAUUSD':.15,'XAGUSD':.15}),
             ('Gold weighted',{'XAUUSD':.25,'XAGUSD':.125}),
             ('Gold 25 silver 15',{'XAUUSD':.25,'XAGUSD':.15}),
             ('Silver weighted',{'XAUUSD':.125,'XAGUSD':.25}),
             ('Both larger',{'XAUUSD':.25,'XAGUSD':.25})]
    results=[];saved_paths=[]
    for horizon in [60,365]:
        starts=windows(START,END,horizon)
        for severity in ['source','stress','severe']:
            baseline=None
            for name,policy in configs:
                extra=[newskeys[0] if sym=='XAUUSD' else newskeys[1] for sym in policy]
                rr=[r for key in keys+extra for r in bykey[key]]
                outcomes=[replay(rr,s,s+timedelta(days=horizon),risk=.5,severity=severity,
                                 news_policy=policy,news_calendar=releases) for s in starts]
                if not policy:baseline=outcomes
                a=aggregate(outcomes,horizon)
                for prefix in ['funded','payout','breach','safety_halt','inactivity']:
                    a[prefix+'_by_horizon']=a.pop(prefix+'60')
                a.update(name=name,severity=severity,horizon=horizon,risk_per_side_pct=policy,
                         median_news_fills=median(r['counts'].get('news_opened',0) for r in outcomes),
                         median_win_rate=median(r['wins_pct'] for r in outcomes),
                         median_pf=median(r['pf'] for r in outcomes if r['pf'] is not None),
                         delta_vs_baseline_median=median(r['balance']-b['balance'] for r,b in zip(outcomes,baseline)),
                         positive_balance_pct=100*sum(r['balance']>10000 for r in outcomes)/len(outcomes),
                         per_ea_median_net={key:median(r['by_ea'].get(key,{}).get('net',0) for r in outcomes) for key in keys+extra})
                pooled=Counter()
                for r in outcomes:pooled.update(r['counts'])
                a['pooled_diagnostics']=dict(pooled)
                results.append(a)
                if horizon==60:
                    saved_paths.append(dict(name=name,severity=severity,paths=[dict(start=s,**r) for s,r in zip(starts,outcomes)]))
                print(name,severity,horizon,json.dumps({k:a[k] for k in ['median_balance','median_trades','median_news_fills','max_closed_dd','funded30','funded_by_horizon','payout_by_horizon']}),flush=True)
    events=[e for e in releases if START<=e<END]
    news_stats={}
    for key in newskeys:
        news_stats[key]={}
        for severity in ['source','stress','severe']:
            vals=[]
            event_r=Counter()
            for r in bykey[key]:
                g,c,s,x=costs(r,r['volume'],severity)
                value=(g+c+s-x)/(400*r['volume'])
                vals.append(value)
                event_r[dt(r['news_event_utc'])]+=value
            news_stats[key][severity]=stats(vals)
            news_stats[key][severity]['event_r']=[event_r[e] for e in events]
    policy_geometry={}
    for name,policy in configs:
        pos={}
        for symbol,pct in policy.items():
            import math
            unit=650 if symbol=='XAGUSD' else 607
            lots=math.floor((10000*pct/100/unit)/.01+1e-9)*.01
            pos[symbol]=dict(lots_per_side=lots,initial_stop_usd_per_side=400*lots,
                             stress_budget_per_side=lots*unit,
                             reserved_margin_both_sides=2*lots*SPEC[symbol]['contract']*SPEC[symbol]['price']/SPEC[symbol]['leverage'])
        policy_geometry[name]=pos
    save('news-comparison.json',dict(calendar=str(CALENDAR),calendar_sha256=hashlib.sha256(CALENDAR.read_bytes()).hexdigest(),
                                    keys=keys,start=START,end=END,events=len(events),news_stats=news_stats,
                                    policy_geometry=policy_geometry,results=results))
    save('news-paths.json',saved_paths)
    write_report(results,news_stats,policy_geometry,len(events))

def write_report(results,news_stats,geometry,n_events):
    lines=['# Gold + Silver News Pulse: $10K Swing research comparison','',
           'Research only, 19 September 2026. No BAT, live orders, EA settings or website changes.', '',
           '## What was tested','',
           '- Same seven-EA portfolio and source window as the prior plan: 7 September 2021 to 31 August 2026, end exclusive. 251 overlapping 60-day windows, plus 207 one-year windows. These are retrospectively selected historical replays, not calibrated future probabilities.',
           '- The FTMO XAUUSD tick probe again returned no ticks. Results use saved Exness trades with fixed Swing margin assumptions; not fresh FTMO native tick backtests.',
           '- Both news caches report only 13% real ticks. Older generated ticks and the 1 ms source tester delay are particularly weak evidence for news execution. No claims of deployment readiness.',
           f'- Full official-source calendar: {n_events} releases in the common interval, including releases that produced no fills. Reserve BOTH sides of every enabled symbol at T-30; gold still uses its recorded T-15 entry/fill behavior. Reservations expire at T+60. No assumption that only the winning side needs margin.',
           '- Shared admission is all-or-none across the selected metals. No removal of the opposite order merely because one side fills or loses. Previously reserved fills keep their original volume. No margin hedging relief is assumed.',
           '- Reserve $7/lot gold and $50/lot silver commission plus 1.5x initial-stop risk for news sizing. Silver\'s cached commission was materially higher than the earlier generic allowance. Commission stress still uses the greater of recorded charges and the model minimum; budgets are allowances, not guaranteed loss caps.',
           '- Up to four ordinary entries and ONE news release per Prague day (up to four news fills, eight total). Stop admitting new risk after three losing closes or $150 closed daily loss. Both news sides already reserved can still fill. Maximum shared risk $150, metals $100, prospective daily loss $200; margin <=60% of conservative equity.',
           '- Ordinary per-trade budget .50% in evaluation and .25% funded. News budgets halve on 4% drawdown/three EA losses, and are capped at .15% per side funded. Round lots DOWN and skip the whole basket if any minimum lot exceeds its budget. The $12.50-side plans can become untradeable after taper; $15 per side remains above both minimum-lot allowances after halving, down to the model safety floor.',
           '- This changes news admission versus the previous exploratory replay: reservations happen BEFORE release, use a full calendar, share metals limits, include higher silver commission allowance, and use a separate one-release daily quota. Baseline and gold-only are rerun for fair comparisons.',
           '- Source scenario retains saved fills/commission/swap. Stress reduces normal winners 10%, expands losses 10%, adds .02R; news winners -35%, losers +25%, plus .15R. Severe normal -25%/+30%/.10R; news -60%/+100%/.50R. Carry assumptions and phase/payout timing are unchanged from PLAN.md.',
           '- No continuous floating-equity path, actual pre-event quote/spread checks, or new broker rejection/fill modeling is available. Native missed/changed entries cannot be recovered from saved deals. Calendar reservations assume a valid setup at each scheduled event and can conservatively block trades that production would not place. Source and stressed columns are hypothetical sensitivities.',
           '', '## Risk allocations (planned per side, before rounding)', '',
           '| Plan | Gold per side | Silver per side | All four-side budget | Reserved news margin at modeled current prices |',
           '|---|---:|---:|---:|---:|']
    for r in results:
        if r['horizon']!=60 or r['severity']!='stress':continue
        p=r['risk_per_side_pct'];g=geometry[r['name']]
        lines.append(f"| {r['name']} | ${p.get('XAUUSD',0)*100:.2f} | ${p.get('XAGUSD',0)*100:.2f} | ${sum(p.values())*200:.2f} | ${sum(x['reserved_margin_both_sides'] for x in g.values()):,.0f} |")
    lines += ['', '## 60-day results', '',
              '| Plan | Cost scenario | Median closed trades | Median news fills | Median ending balance | Paired median balance difference vs seven | Worst closed-balance DD | Funded by 30d | Funded by 60d | Reward >=$100 by 60d |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        if r['horizon']!=60:continue
        lines.append(f"| {r['name']} | {r['severity']} | {r['median_trades']:g} | {r['median_news_fills']:g} | ${r['median_balance']:,.2f} | ${r['delta_vs_baseline_median']:+,.2f} | {r['max_closed_dd']:.2f}% | {r['funded30']:.1f}% | {r['funded_by_horizon']:.1f}% | {r['payout_by_horizon']:.1f}% |")
    lines += ['', 'Balance is simulated account capital, not withdrawable income; phase resets can affect it. Drawdown is closed-balance only. Zero endpoint breaches cannot certify FTMO equity compliance.',
              '', '## One-year context (stressed)', '',
              '| Plan | Funded by 365 days | Reward >=$100 by 365 days | Closed-balance safety halt | Inactivity stop |',
              '|---|---:|---:|---:|---:|']
    for r in results:
        if r['horizon']!=365 or r['severity']!='stress':continue
        lines.append(f"| {r['name']} | {r['funded_by_horizon']:.1f}% | {r['payout_by_horizon']:.1f}% | {r['safety_halt_by_horizon']:.1f}% | {r['inactivity_by_horizon']:.1f}% |")
    lines += ['', '## News standalone stress screen', '', '| EA | Trades | Source net win rate | Stressed net win rate | Stressed equal-risk PF |', '|---|---:|---:|---:|---:|']
    for key,a in news_stats.items():
        lines.append(f"| {key} | {a['source']['trades']} | {a['source']['win_rate']:.1f}% | {a['stress']['win_rate']:.1f}% | {a['stress']['pf']:.2f} |")
    lines += ['', '## Interpretation', '',
              'Gold-only is the first candidate to validate, not a statistically established winner. If both metals are required, start research/forward validation at $15 planned per side, $60 maximum budget per release, with shared guards. This retains room for risk taper and avoids the $12.50 minimum-lot trap. Increasing both to $25 raises margin consumption and blocks more release baskets without producing short-deadline passes.',
              'Do not interpret the difference between two portfolio median balances as the typical improvement on the same starting date. Under stress, both at $15 has a paired median 60-day change of -$4.14 versus the seven-EA baseline even though its unpaired median balance is higher. This is not evidence that adding silver reliably improves the portfolio. All compared 60-day variants have zero modeled funding/payout successes; real-world probabilities remain unknown.',
              '', '## Conditions before any deployment', '',
              'Keep both pending directions, but share account-level risk limits. No adaptive bypass. Confirm exact news-straddle permission with FTMO: Swing permits news, but prohibited gap-trading and abusive execution rules still apply. Validate real FTMO event ticks, spreads, commission, symbol contract sizes/leverage, stop/freeze levels, and margin before treating this shortlist as executable. No live equity safety claim is made.',
              '', '[Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/) | [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)', '']
    (OUT/'NEWS-COMPARISON.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
