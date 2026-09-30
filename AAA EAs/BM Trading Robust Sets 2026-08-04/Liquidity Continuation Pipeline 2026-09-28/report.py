"""Build a transparent research report from completed native evidence only."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import gzip,json
import search
from verify import streaks

ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def trades(folder):return json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
def frequency(n,start,end,asset):
    a=datetime.strptime(start,'%Y.%m.%d');b=datetime.strptime(end,'%Y.%m.%d');days=(b-a).days
    trading=sum(asset=='BTC' or (a+timedelta(days=i)).weekday()<5 for i in range(days))
    return n/(days/365.25*12),n/max(1,trading)

def description(c):
    tf='M'+str(c['tf']) if c['tf']<60 else {60:'H1',240:'H4',1440:'D1'}[c['tf']]
    entry=['original','bar confirmation','ATR limit','price limit','stop continuation'][int(c['entry'])]
    stop=['ATR','price %','price distance','signal extreme','swing5','structure'][int(c['stop'])]
    trail=['none','breakeven','ATR','price %','EMA20','swing5','chandelier','M15 step'][int(c['trail'])]
    exit_name=[f"{c['rr']:g}R",'no TP','next level','NY 16:00','partial 1R + trail'][int(c['exit'])]
    sess=['all','Asia','London','NY','London/NY overlap','NY open'][int(c['session'])]
    side=['both','long','short'][int(c['direction'])]
    filt=['none','EMA50 slope','H1 EMA50','ADX20','DI14','ATR percentile','spread cap'][int(c['filter'])]
    return f"{tf}; {entry}; SL {stop} {c['sl']:g}; trail {trail}; exit {exit_name}; {sess}; {side}; filter {filt}"

def native_row(folder):
    m=load(folder/'manifest.json');r=load(folder/'results.json')[0];n=r['net'];t=trades(folder)
    mo,day=frequency(n['trades'],m['start'],m['end'],m['asset']);s=streaks([x['net_profit'] for x in t])
    return dict(asset=m['asset'],label=m['name'],start=m['start'],end=m['end'],model=m['model'],
        trades=n['trades'],per_month=mo,per_day=day,return_pct=n['net_profit']/100,profit_factor=n['profit_factor'],
        win_rate_pct=n['win_rate_pct'],equity_dd_pct=n['equity_dd_pct'],streaks=s,folder=str(folder),parameters=r['parameters'],
        planned_risk_per_position_pct=1/(2 if m['strategy']==2 else 1)/r['parameters']['max_pos'])

def table(rows):
    out=['| Asset / test | Dates | Planned risk/position | Return | Trades (month / day) | Win | PF | Equity DD | Max W/L; avg W/L streak |',
         '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        s=r['streaks'];out.append(f"| {r['asset']} {r['label']} | {r['start']}–{r['end']} | {r['planned_risk_per_position_pct']:.2f}% | {r['return_pct']:+.2f}% | {r['trades']:,} ({r['per_month']:.1f} / {r['per_day']:.2f}) | {r['win_rate_pct']:.2f}% | {r['profit_factor']:.2f} | {r['equity_dd_pct']:.2f}% | {s['max_win']}/{s['max_loss']}; {s['average_win']:.2f}/{s['average_loss']:.2f} |")
    return out

def main():
    status=load(ROOT/'status.json') if (ROOT/'status.json').exists() else {}
    finals=load(ROOT/'FINALISTS.json') if (ROOT/'FINALISTS.json').exists() else []
    ledger=load(ROOT/'SEARCH RESULTS.json') if (ROOT/'SEARCH RESULTS.json').exists() else []
    completed=status.get('message') in ['SEARCH COMPLETE','BASELINE COMPARISONS COMPLETE'] or (ROOT/'SEARCH COMPLETION.json').exists()
    native=[native_row(f.parent) for f in sorted(search.OUT.glob('*/results.json')) if not load(f.parent/'manifest.json')['optimize']]
    lines=['# Liquidity continuation — exploratory full parameter pipeline','',
        f"Generated {datetime.now(timezone.utc).isoformat()}. Search: **{'complete' if completed else 'IN PROGRESS'}**.",'',
        'Requested: Gold first-touch + retest as one EA; BTC first-touch; US30 first-touch. No changes to the live system, BATs or website for these research candidates. The separate Nasdaq DI + wider stop + ATR deployment was pushed in commit `bae7aefb9`.',
        '', '## Verdicts','',
        '| Asset | Research gate |','|---|---|']
    for asset,_,_ in search.TARGETS:
        f=next((f for f in finals if f['asset']==asset),None)
        lines.append(f"| {asset} | {f['status'] if f else 'PENDING'} |")
    assessment=[];paired=[]
    for f in finals:
        candidates=f.get('development',f.get('best',[]))
        if not candidates:continue
        leader=candidates[0]
        val=next((r for r in native if r['asset']==f['asset'] and r['label'].startswith('validation-')
            and search.digest(r['parameters'])==search.digest(leader['parameters'])),None)
        raw=next((r for r in native if r['asset']==f['asset'] and r['label']=='raw-validation'),None)
        assessment.append(dict(asset=f['asset'],status=f['status'],development_leader=leader,validation=val,raw_validation=raw))
        if raw:paired.append(raw|dict(label='raw, same validation window'))
        if val:paired.append(val|dict(label='development leader, validation'))
    if completed and finals and all(f['status'].startswith('REJECTED') for f in finals):
        lines += ['', '**Terminal decision: all three research candidates rejected.** The conditional older holdout, Monte Carlo, FTMO and production stages were not started because no finalist passed validation. This is a completed rejection decision, not a pending deployment.']
    if paired:
        lines += ['', '## Same-date, same-model raw vs optimized comparison','',
            'Native Model 4, 150 ms, 2024-03-27–2025-09-27. The candidate shown is the first-ranked DEVELOPMENT leader, not whichever lost least in validation. All three validation alternatives per asset are retained below. Per-position risk can differ when the chosen position cap reserves capacity; that is explicitly shown.','']
        lines+=table(paired)
    lines += ['', '**No candidate is approved for deployment by this report.** A search-stage pass is not a full robustness/FTMO pass.',
        '', '## Data and selection limitations','',
        '- $10,000 research account, 1:2000 research leverage, native broker symbol costs. This is not an FTMO account simulation.',
        '- Development: 2021-09-27–2024-03-27, Model 1. Validation: 2024-03-27–2025-09-27, Model 4 and 150 ms.',
        '- Recent year: 2025-09-27–2026-09-27, already viewed; retrospective only. Earlier 2019-09-27–2021-09-27 history is checked once if available, not described as future-forward validation.',
        '- Real ticks start January 2026; earlier ticks are generated. Native history-quality percentages also include the 300-day no-trade warmup.',
        '- Gold defaults allocate 0.5% planned equity risk to each of two independent entry engines. Single-engine baselines allocate 1%. Lots round UP, preserving the raw study; minimum lots, costs and gaps can exceed planned risk.',
        '- A two-position-cap candidate divides its engine allocation by two. This lowers per-position exposure if its additional capacity is unused; lower dollar drawdown is not credited solely to better entries. Every confirmation table states planned per-position risk.',
        '- These are price-only CFD rules, not the source author’s private futures/order-flow strategy. No claim to reproduce the 8× volume or 70% aggressor measurements.',
        '- All original raw candidates failed the 3y/5y gate. This search is an explicitly requested exploratory exception, not a reversal of that finding.',
        '- Trades/month annualizes the stated calendar window; trades/day uses weekdays for XAU/US30 and calendar days for BTC, not only days on which a trade happened. Streaks use completed position net P&L; zero breaks a streak. Equity DD comes from native floating-equity statistics.',
        '', '## Exact baseline parity and raw combined Gold','']
    lines+=table([r for r in native if r['label'].startswith(('parity','combined-raw'))])
    lines += ['', '## Search coverage and dimension leaders','',
        f"Completed search cases: {len(ledger):,}; unique asset/settings combinations: {len({r['asset']+search.digest(r['parameters']) for r in ledger}):,}. Repeated settings across stages remain counted as tests. Original raw testing and pre-search smoke/parity runs are additional research exposure.",
        '', 'Top-three beam search, not a Cartesian exhaustive global optimum. Negative intermediate leaders are retained so later exit/filter stages can be explored, but final development eligibility still requires positive return, PF ≥ 1.15 and ≥60 trades.',
        '', '| Asset / stage | Return | N (month / day) | Win | PF | Equity DD | W/L streaks | Leader settings (Model 1 screening only) |',
        '|---|---:|---:|---:|---:|---:|---|---|']
    for asset,_,_ in search.TARGETS:
        stages=list(dict.fromkeys(r['stage'] for r in ledger if r['asset']==asset))
        for stage in stages:
            r=max((r for r in ledger if r['asset']==asset and r['stage']==stage),key=lambda r:r['net']['score']);n=r['net']
            mo,day=frequency(n['trades'],'2021.09.27','2024.03.27',asset)
            lines.append(f"| {asset} / {stage} | {n['net_profit']/100:+.2f}% | {n['trades']} ({mo:.1f} / {day:.2f}) | {n['win_rate_pct']:.2f}% | {n['profit_factor']:.2f} | {n['equity_dd_pct']:.2f}% | not recorded in optimization XML | {description(r['parameters'])} |")
    lines += ['', 'Screening XML/net summaries do not contain the closed-position sequence, so no screening streaks are fabricated. Full sequence metrics appear for each native confirmation below.',
        '', '## Model 4 confirmation / control results','']
    lines+=table([r for r in native if not r['label'].startswith(('parity','combined-raw'))])
    if (ROOT/'CHARTS.json').exists():
        plots=load(ROOT/'CHARTS.json')
        if plots:
            lines += ['', '## Development sensitivity plots','',
                'Green/profitable development neighborhoods are not evidence of a validation pass. The verdicts above take precedence.','']
            for p in plots:lines += [f'![{p[:-4]}]({p})','']
    lines += ['', '## Conditional downstream gates','',
        'Only candidates surviving development, plateau and frozen confirmation proceed to 10,000-path block bootstrap, trade-order reshuffle, missed-fill tests, measured execution-cost stress and FTMO/portfolio overlays. Rejected candidates stop; unavailable history or measured-cost/equity evidence blocks readiness claims. No pass-rate or payout forecast is inferred from a native return.',
        '', '## Evidence','',
        '- `PROTOCOL.md`: pre-search rules and review correction.',
        '- `PARITY.json`: original vs extension entries, exits, volumes and net P&L.',
        '- `SEARCH RESULTS.json`: every completed screening case.',
        '- `FINALISTS.json` and asset frozen final files: selection/gate evidence.',
        '- `native-v2/`: authoritative per-batch source, binary, hashes, exact cases, inputs, native reports, compressed journals and position-ID ledgers.',
        '- `native/`: retained pre-review attempts, not current optimization evidence.',
        '- `VERIFICATION.json`: completed-batch checks; `verify.py` has independent boundary, stage-space, streak and ledger checks.',
        '', 'No production promotion or public-site deployment is performed by this research runner.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    search.save(ROOT/'REPORT DATA.json',dict(search_complete=completed,status=status,finalists=finals,native=native,cases=len(ledger)))
    search.save(ROOT/'ASSESSMENT.json',assessment)
    print(f"Report saved: search_complete={completed}, native_confirmations={len(native)}, search_cases={len(ledger)}")

if __name__=='__main__':main()
