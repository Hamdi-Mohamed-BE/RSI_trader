"""Reconcile evidence and produce review-only tables and ledger risk diagnostics."""
import json,math
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timedelta,timezone
import numpy as np
from data import ROOT,save,sha,load,NY

def read(name):return json.loads((ROOT/name).read_text())
def ledger(stats):return json.loads((Path(stats['directory'])/'trades.json').read_text())
def pnl_stats(p):
    p=np.asarray(p,float);balance=10000+np.r_[0,np.cumsum(p)];peaks=np.maximum.accumulate(balance)
    wins=p[p>0].sum();loss=-p[p<0].sum()
    return dict(net_profit=float(p.sum()),return_pct=float(p.sum()/100),profit_factor=float(wins/loss) if loss else None,
                closed_balance_dd_pct=float(np.max((peaks-balance)/peaks)*100),win_rate_pct=float(np.mean(p>0)*100) if len(p) else 0.)

def costs(ts):
    p=np.array([t['net_profit'] for t in ts]);lots=np.array([t['volume'] for t in ts]);comm=np.array([abs(t['commission']) for t in ts])
    return [dict(extra_roundtrip_usd_per_ounce=v,commission_multiplier=1.5,**pnl_stats(p-v*100*lots-.5*comm)) for v in (.1,.25,.5)]

def bootstrap(ts,seed=9192026,paths=5000):
    weekly=defaultdict(list)
    for t in ts:
        date=datetime.fromisoformat(t['close_time']).date();monday=date-timedelta(days=date.weekday())
        before=t['balance_after']-t['net_profit'];weekly[monday].append(t['net_profit']/before)
    # Use the same whole-week grid for both ledgers, including leading/trailing
    # weeks without a candidate trade. Do not inflate sparse-strategy frequency.
    first=datetime(2021,9,20).date();last=datetime(2026,9,14).date();blocks=[];day=first
    while day<=last:blocks.append(weekly[day]);day+=timedelta(days=7)
    rng=np.random.default_rng(seed);returns=[];dds=[]
    for _ in range(paths):
        factors=[1+r for k in rng.integers(0,len(blocks),52) for r in blocks[k]]
        equity=10000*np.r_[1,np.cumprod(factors)];peak=np.maximum.accumulate(equity)
        returns.append((equity[-1]/10000-1)*100);dds.append(max((peak-equity)/peak)*100)
    return dict(paths=paths,seed=seed,weeks_per_path=52,blocks=len(blocks),probability_negative_sample_pct=float(np.mean(np.array(returns)<0)*100),
                return_percentiles=dict(zip(('p05','p50','p95'),np.percentile(returns,[5,50,95]).tolist())),
                closed_balance_dd_percentiles=dict(zip(('p05','p50','p95'),np.percentile(dds,[5,50,95]).tolist())),
                limitation='Historical weekly block resampling; not future pass/profit probability. Preserves within-week trade order, not longer regimes or floating equity. Uses realized percentage returns, not re-sized broker lots. Includes research/selection bias.')

def missed_winners(ts):
    rng=np.random.default_rng(20260919);p=np.array([t['net_profit'] for t in ts]);win=np.flatnonzero(p>0);rows=[]
    for fraction in (.05,.1):
        returns=[];dds=[]
        for _ in range(1000):
            altered=p.copy();missed=rng.choice(win,max(1,math.ceil(len(win)*fraction)),replace=False);altered[missed]=0
            s=pnl_stats(altered);returns.append(s['return_pct']);dds.append(s['closed_balance_dd_pct'])
        rows.append(dict(missed_winner_fraction=fraction,paths=1000,return_percentiles=np.percentile(returns,[5,50,95]).tolist(),closed_balance_dd_p95=float(np.percentile(dds,95))))
    return rows

def breakdown(ts):
    monthly=defaultdict(list);yearly=defaultdict(list);sides=defaultdict(list)
    for t in ts:
        local=datetime.fromisoformat(t['close_time']).astimezone(NY)
        monthly[local.strftime('%Y-%m')].append(t);yearly[local.strftime('%Y')].append(t);sides[t['side']].append(t)
    def rows(groups):
        result=[]
        for key,trades in sorted(groups.items()):
            p=np.array([t['net_profit'] for t in trades]);before=trades[0]['balance_after']-trades[0]['net_profit']
            s=pnl_stats(p)
            result.append(dict(label=key,trades=len(trades),net_profit=round(float(p.sum()),2),return_on_period_start_pct=float(p.sum()/before*100),win_rate_pct=s['win_rate_pct'],profit_factor=s['profit_factor'],commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),ending_balance=trades[-1]['balance_after']))
        return result
    directions=rows(sides)
    for r in directions:
        # Sides share one account; their last trade balance is not an independent
        # side portfolio and their first-entry balance is not allocated capital.
        r.pop('return_on_period_start_pct');r.pop('ending_balance')
    return dict(monthly=rows(monthly),yearly=rows(yearly),direction=directions)

def diagnostics(stats):
    ts=ledger(stats);risk=np.array([t['initial_risk_pct'] for t in ts]);rr=np.array([t['initial_rr'] for t in ts]);p=np.array([t['net_profit'] for t in ts]);volume=np.array([t['volume'] for t in ts])
    best=sorted(ts,key=lambda t:t['net_profit'],reverse=True)[:5]
    return dict(cost_overlays=costs(ts),weekly_bootstrap=bootstrap(ts),missed_winners=missed_winners(ts),breakdown=breakdown(ts),
        initial_risk_percentiles=dict(zip(('min','p50','p95','max'),np.percentile(risk,[0,50,95,100]).tolist())),
        initial_rr_percentiles=dict(zip(('min','p50','p95','max'),np.percentile(rr,[0,50,95,100]).tolist())),
        minimum_lot_trades=int(sum(volume==.01)),risk_over_1_1_pct_trades=int(sum(risk>1.1)),
        gross_breakeven_net_loss_count=sum(abs(t['gross_profit'])<.011 and t['net_profit']<0 for t in ts),
        top_five_net_profit=sum(t['net_profit'] for t in best),without_best_five=pnl_stats([t['net_profit'] for t in ts if t not in best]),
        average_win_usd=float(p[p>0].mean()) if any(p>0) else 0.,average_loss_usd=float(p[p<0].mean()) if any(p<0) else 0.,
        median_entry_slippage_price=float(np.median([t['entry_slippage_price'] for t in ts])),
        p95_absolute_entry_slippage_price=float(np.percentile([abs(t['entry_slippage_price']) for t in ts],95)))

def coverage():
    m1,m5=load();counts=defaultdict(int)
    # NY dates, aggregated by UTC hour to avoid millions of timezone conversions.
    hour,nums=np.unique(m1['time']//3600,return_counts=True)
    for h,n in zip(hour,nums):counts[datetime.fromtimestamp(int(h*3600),NY).strftime('%Y-%m-%d')]+=int(n)
    missing=[];sparse=[];d=datetime(2021,9,20).date();last=datetime(2026,9,19).date()
    while d<last:
        if d.weekday()<5:
            n=counts[d.isoformat()]
            if n==0:missing.append(d.isoformat())
            elif n<600:sparse.append(dict(date=d.isoformat(),m1_bars=n))
        d+=timedelta(days=1)
    return dict(ny_weekdays_with_no_bars=missing,ny_weekdays_under_600_bars=sparse,
        caveat='Unclassified holiday/closure/data-gap candidates, not automatically missing history. No bars were fabricated. Native profile/signal checks reconcile downloaded bars against tester profiles.')

def main():
    raw=read('raw-results.json');selected=read('selected-results.json');selection=read('selection-frozen.json');native_stress=read('native-stress.json');verification=read('verification.json')
    complete=list((ROOT/'native').glob('*/summary.json'))
    assert len(verification['cases'])==len(complete) and verification['all_passed'],'Run complete verification before final report'
    assert read('unit-tests.json')['passed'] and read('history-gap-probe.json')['passed_cache_consistency']
    diagnostics_all={'raw':diagnostics(raw['5y']),'selected':diagnostics(selected['5y'])}
    save(ROOT/'risk-diagnostics.json',diagnostics_all);save(ROOT/'coverage-details.json',coverage())
    data=dict(raw=raw,selected=selected,selection=selection,native_stress=native_stress,diagnostics=diagnostics_all,verification=verification,
        guardrails=dict(live_deployment=False,website_changed=False,bats_changed=False,sp500_pipeline_started=False),
        evidence_window='2021-09-19 <= time < 2026-09-19; independent $10,000 starts for 6m/1y/3y/5y',
        limitations=['Not full real-tick history; broker real ticks begin 2026-01-01.','Repeated broker API checks confirm no June 20, 2025 NY session in available history; unresolved gap/closure.','Latest-year raw result was previously inspected; not untouched holdout.','Current broker contract/fees/session conventions do not prove historical/live conditions.','All candidate discovery is in-sample; validation reused to select among three finalists.','No guarantee of profitability or prop-firm performance.'])
    save(ROOT/'RESULTS.json',data)
    c=selection['selected']['config'];eligible=selection['any_eligible'];screen=read('screen-results.json');wf=read('walk-forward-screen.json')
    lines=['# Gold Overnight Value Area — full research pipeline',
        '', '**Review only: nothing deployed. S&P 500 pipelines have not been started.**','',
        ('The predeclared training/validation gates passed for at least one candidate. This is still research evidence, not approval for live use.' if eligible else '**NO PROMOTION. None of the three native finalists passed all predeclared training/validation gates. Do not add this version to the active system on this evidence.**'),
        '', '## Native MT5 comparison', '',
        'Independent $10,000 starts, 1% requested equity stop-risk, same Exness Zero XAUUSD contract, 150 ms simulated execution delay. Commissions and swaps are the actual values recorded in each tester Deals ledger. Native equity drawdown includes floating P/L. Ends 2026-09-19 exclusive; six months starts 2026-03-19, one year 2025-09-19, three years 2023-09-19, five years 2021-09-19.', '',
        '| Period | Version | Return | Net USD | Trades | Win rate | PF | Equity DD | Commission | Swap | Real tick quality |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for period in ('6m','1y','3y','5y'):
        for label,group in [('Raw',raw),('Research candidate',selected)]:
            r=group[period]
            lines.append(f"| {period} | {label} | {r['return_pct']:+.2f}% | ${r['net_profit']:+,.2f} | {r['trades']} | {r['win_rate_pct']:.2f}% | {r['profit_factor']:.2f} | {r['max_drawdown_pct']:.2f}% | ${r['commission']:,.2f} | ${r['swap']:,.2f} | {r['history_quality']} |")
    lines+=['','## Frozen candidate settings','',f"- {c['bins']} histogram bins; {c['va']}% contiguous value area; profile NY 18:00 previous calendar day to 09:30 today.",
        '- First completed M5 close above VAH buys, below VAL sells; market execution on the next tick. One signal attempt per NY day; invalid price geometry consumes it.',
        f"- Stop: {'POC' if c['stop']==1 else 'opposite value-area edge'} plus one broker tick beyond it. Minimum initial reward/risk: {c['min_r']:.2f}R.",
        f"- TP: {str(c['target_r'])+'R' if c['target_r'] else 'overnight high for buys / low for sells'}.",
        f"- Breakeven trigger: {c['be']}R (0=off); trailing distance: {c['trail']}R (0=off, otherwise activates after 1R using completed M5 closes).",
        f"- Last entry before {c['entry_end']//60:02d}:{c['entry_end']%60:02d} NY; time exit {c['exit']//60:02d}:{c['exit']%60:02d} NY, clamped to known broker session end; retries if market closed.",
        '- Requested risk 1% equity, rounded UP to broker lot step with 0.01-lot floor. This is not a strict 1% cap. Native 0.5% sensitivity is reported below.',
        '', '## Selection, not a latest-year winner search','',
        f"Tested {sum(r['stage']=='A' for r in screen['rows'])} Stage-A configurations plus {sum(r['stage']=='B' for r in screen['rows'])} additional management/target configurations, with the unchanged raw baseline separately. Discovery used an explicitly approximate M1/M5 bid/ask bar engine. Native MT5 checked three diverse finalists.",
        '', 'Training: 2021-09-19–2024-09-19. Validation: 2024-09-19–2025-09-19. Candidate selection was frozen before evaluating its latest year. The latest-year **raw** result had already been seen, so this is not a virgin holdout.',
        '', '| Candidate | Train return / trades / PF / DD | Validation return / trades / PF / DD | Gate |', '|---|---|---|---|']
    for r in selection['all_finalists']:
        def compact(m):return f"{m['return_pct']:+.2f}% / {m['trades']} / {m['profit_factor']:.2f} / {m['max_drawdown_pct']:.2f}%"
        cfg=r['config'];name=f"{cfg['va']}% VA / {cfg['bins']} bins / {'POC' if cfg['stop'] else 'opposite VA'} stop / "+(f"{cfg['target_r']}R TP" if cfg['target_r'] else 'overnight TP')+(f" / BE {cfg['be']}R" if cfg['be'] else '')
        lines.append(f"| {name} | {compact(r['train'])} | {compact(r['validation'])} | {'PASS' if r['eligible'] else '; '.join(r['reasons'])} |")
    lines+=['','Gates: at least 300 training and 60 validation trades; both periods net-positive, PF ≥1.10 and equity DD ≤20%. The gates were not relaxed after seeing results. The displayed research candidate is the best eligible candidate, or the least-bad training/validation score if none qualifies. These thresholds are research safeguards, not statistical proof that 300 trades are sufficient or 249 are worthless.',
        '', 'The fixed-R target finalist can accept first signals that the overnight-extreme TP would reject because its target is already behind the entry price. Its changed trade count therefore reflects changed entry eligibility as well as exit behavior; it is not a pure exit-only comparison. The selected configuration is specified explicitly above.','',
        '## Chronological walk-forward diagnostic — bar approximation','',
        'For each origin, select from the same 162 Stage-A family using only the preceding two years, then evaluate the following six months. Stage B is excluded because its parent choice used later training data. Each fold starts with $10,000; these returns must not be added as one live portfolio.', '',
        '| Test start | Test end (exclusive) | Return | Trades | WR | PF | Approx. DD |','|---|---|---:|---:|---:|---:|---:|']
    for f in wf['folds']:
        m=f['subsequent_6m'];lines.append(f"| {f['origin']} | {f['end']} | {m['return_pct']:+.2f}% | {m['trades']} | {m['win_rate_pct']:.2f}% | {m['profit_factor']:.2f} | {m['max_drawdown_pct']:.2f}% |")
    lines+=['','## Native execution / sizing stress','',
        '| Scenario | Period | Return | Trades | WR | PF | Equity DD | Max actual initial risk |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in native_stress:
        lines.append(f"| {r['delay']} ms, {r['risk_percent']}% requested | {r['period']} | {r['return_pct']:+.2f}% | {r['trades']} | {r['win_rate_pct']:.2f}% | {r['profit_factor']:.2f} | {r['max_drawdown_pct']:.2f}% | {r['max_initial_risk_pct']:.2f}% |")
    lines+=['','These delay runs use MT5 fixed delay and its recorded spreads. They do not model every live rejection, queue position, spread burst, disconnection or historical liquidity change.','',
        '## Extra-cost overlay on fixed five-year native ledgers','',
        'Add the stated dollar price cost per ounce per round trip, plus 50% extra commission. Existing spreads and recorded fees are already present. **This is a fixed-trade cash overlay, not a re-execution or a re-compounded native test. DD below is closed-balance only.**','',
        '| Version | Added $/oz | Return | PF | Closed-balance DD |','|---|---:|---:|---:|---:|']
    for name,d in diagnostics_all.items():
        for s in d['cost_overlays']:lines.append(f"| {name} | {s['extra_roundtrip_usd_per_ounce']:.2f} | {s['return_pct']:+.2f}% | {s['profit_factor']:.2f} | {s['closed_balance_dd_pct']:.2f}% |")
    lines+=['','## Sizing and operational audit (five years)','',
        '| Version | Median / max initial risk | Minimum-lot trades | Exits >1 minute late | Held into another NY day | Average initial RR | Gross breakeven but net loss |','|---|---|---:|---:|---:|---:|---:|']
    for name,g in [('raw',raw),('selected',selected)]:
        d=diagnostics_all[name];r=g['5y'];lines.append(f"| {name} | {d['initial_risk_percentiles']['p50']:.3f}% / {d['initial_risk_percentiles']['max']:.3f}% | {d['minimum_lot_trades']} | {r['exits_over_one_minute_late']} | {r['overnight_holdings']} | {r['average_rr']:.3f}R | {d['gross_breakeven_net_loss_count']} |")
    lines+=['','| Version | Average win / loss | Win / loss streak maximum | Long trades / net USD | Short trades / net USD | Net profit without best five winners |', '|---|---|---|---|---|---:|']
    for name,g in [('raw',raw),('selected',selected)]:
        d=diagnostics_all[name];r=g['5y'];sides={x['label']:x for x in d['breakdown']['direction']};long=sides.get('Long',dict(trades=0,net_profit=0));short=sides.get('Short',dict(trades=0,net_profit=0))
        lines.append(f"| {name} | ${d['average_win_usd']:.2f} / ${d['average_loss_usd']:.2f} | {r['max_win_streak']} / {r['max_loss_streak']} | {long['trades']} / ${long['net_profit']:+,.2f} | {short['trades']} / ${short['net_profit']:+,.2f} | ${d['without_best_five']['net_profit']:+,.2f} |")
    lines+=['','Gross breakeven trades still pay costs and are correctly counted as net losses. Moving the time exit earlier is not a guarantee of same-day execution on every historical holiday.','',
        '## Monte Carlo sensitivity, not a promise','',
        '5,000 paths, each 52 randomly sampled historical week blocks (including empty weeks), seed 9192026. Uses realized percentage returns and ignores intratrade floating DD and longer regime dependence. It does not estimate FTMO passing probabilities and does not remove parameter-selection bias.','',
        '| Ledger | Negative sampled year | Return p05 / median / p95 | Closed-balance DD p95 |','|---|---:|---|---:|']
    for name,d in diagnostics_all.items():
        b=d['weekly_bootstrap'];p=b['return_percentiles'];lines.append(f"| {name} | {b['probability_negative_sample_pct']:.1f}% | {p['p05']:+.2f}% / {p['p50']:+.2f}% / {p['p95']:+.2f}% | {b['closed_balance_dd_percentiles']['p95']:.2f}% |")
    lines+=['','Missed-winner tests remove 5% or 10% of winners at random from the fixed ledger, 1,000 draws. No replacement trades or compounding changes are invented.','',
        '| Ledger | Missing winners | Five-year return p05 / median / p95 |','|---|---:|---|']
    for name,d in diagnostics_all.items():
        for s in d['missed_winners']:
            lines.append(f"| {name} | {100*s['missed_winner_fraction']:.0f}% | "+' / '.join(f'{x:+.2f}%' for x in s['return_percentiles'])+' |')
    lines+=['','## Local parameter stability','',
        'Neighbor settings are sensitivity checks, not replacements selected after looking at the latest year. Full bar-based training/validation neighbors are in neighbor-screen.json. Two nearest geometry neighbors were checked in native MT5 on validation.','',
        '| Neighbor change | Validation return | Trades | PF | Equity DD |','|---|---:|---:|---:|---:|']
    for n in read('native-neighbors.json'):
        r=n['result'];lines.append(f"| {n['parameter']}={n['value']} | {r['return_pct']:+.2f}% | {r['trades']} | {r['profit_factor']:.2f} | {r['max_drawdown_pct']:.2f}% |")
    lines+=['','## Annual and monthly breakdown — five-year continuous runs','',
        'These are cash flows from each continuous five-year run, not independent restarts. First and last months/years are partial. Return is on that period’s opening balance.','',
        '| Year | Raw USD | Raw trades | Candidate USD | Candidate trades |','|---|---:|---:|---:|---:|']
    a={r['label']:r for r in diagnostics_all['raw']['breakdown']['yearly']};b={r['label']:r for r in diagnostics_all['selected']['breakdown']['yearly']}
    for k in sorted(a.keys()|b.keys()):lines.append(f"| {k} | {a.get(k,{}).get('net_profit',0):+,.2f} | {a.get(k,{}).get('trades',0)} | {b.get(k,{}).get('net_profit',0):+,.2f} | {b.get(k,{}).get('trades',0)} |")
    lines+=['','| Month | Raw USD | Raw trades | Candidate USD | Candidate trades | Candidate return |','|---|---:|---:|---:|---:|---:|']
    a={r['label']:r for r in diagnostics_all['raw']['breakdown']['monthly']};b={r['label']:r for r in diagnostics_all['selected']['breakdown']['monthly']}
    for k in sorted(a.keys()|b.keys()):lines.append(f"| {k} | {a.get(k,{}).get('net_profit',0):+,.2f} | {a.get(k,{}).get('trades',0)} | {b.get(k,{}).get('net_profit',0):+,.2f} | {b.get(k,{}).get('trades',0)} | {b.get(k,{}).get('return_on_period_start_pct',0):+.2f}% |")
    lines+=['','## Verification and limits','',
        f"- {len(verification['cases'])} native reports independently reconciled to their trade/fee ledgers; {verification['unique_profiles_checked']} distinct day/parameter profiles checked against M1 history. All completed M5 signal, initial SL/TP, cash-total, source-hash and profile checks passed.",
        '- Ten unit tests cover DST, Monday boundaries, profile geometry, tester-only/account guard, raw ledger parity, minimum lot rounding, conservative intraminute stop-first ordering, invalid-signal consumption and short ask-side exits.',
        '- The modified source exactly reproduces all 200 prior one-year raw trades with default parameters, including timestamps, prices, size, net costs and initial levels.',
        '- Broker real ticks begin 2026-01-01. Older data uses generated ticks even in real-tick tester mode. Tick volume is broker activity, not centralized traded gold volume.',
        '- Holiday/closure candidates and monthly bar counts are saved; no missing bars were synthesized by the research scripts. The MT5 tester itself generates ticks for missing real-tick history.',
        '- A specific coverage gap remains: repeated broker M1/M5 API re-queries match the frozen cache, but on 2025-06-20 the M1 history ends at 07:17 UTC, before NY open. No trade is invented for the absent NY session. These are five-year available-history results, not a claim of complete market coverage.',
        '- During the work an external Git operation left website catalog conflict markers. The research report parser was mechanically isolated from website imports and checked against all then-completed native ledgers with identical outputs; the website conflicts were not modified.',
        '- Fee snapshots, 1:2000 leverage and native account conditions are Exness demo assumptions, not FTMO Swing conditions. This is not an FTMO pass simulation.',
        '- No second broker or forward demo validation was manufactured. Actual live execution remains unverified.',
        '', '**Stop here for user review. Do not deploy Gold or start the five S&P 500 optimization pipelines automatically.**','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    case_hashes={}
    for summary in complete:
        folder=summary.parent
        paths=[folder/n for n in ('summary.json','run.json','trades.json','audit.csv','tester.ini')]+list(folder.glob('*.set'))+list(folder.glob('*.htm'))
        case_hashes[folder.name]={p.name:sha(p) for p in paths}
    save(ROOT/'evidence-index.json',dict(files={p.name:sha(p) for p in ROOT.iterdir() if p.is_file() and p.name!='evidence-index.json'},native_cases=case_hashes))
    print('REPORT READY',ROOT/'RESULTS.md',flush=True)

if __name__=='__main__':main()
