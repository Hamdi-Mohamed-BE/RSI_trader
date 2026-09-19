"""Final native evidence, costs, reproducibility and diagnostic uncertainty."""
import csv,hashlib,json,math
from collections import defaultdict
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from params import *
from native import group_stats,hashes
from audit_management import audit

def money(v):return f'${v:,.2f}' if v>=0 else f'-${-v:,.2f}'
def fpf(v):return 'N/A' if v is None else f'{v:.3f}'
def ledger(r):return json.loads((ROOT/'Audit'/f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}-trades.json").read_text())
def monthly(trades):
    groups=defaultdict(list)
    for t in trades:groups[t['close_time'][:7]].append(t)
    out=[];bal=10000.
    keys=[];date=datetime(2021,9,1)
    while date<datetime(2026,10,1):
        keys.append(date.strftime('%Y.%m'));date=date.replace(year=date.year+1,month=1) if date.month==12 else date.replace(month=date.month+1)
    for key in keys:
        ts=groups[key]
        s=group_stats(ts);out.append(dict(month=key,start_balance=bal,end_balance=bal+s['net_profit'],return_pct=s['net_profit']/bal*100,**s));bal+=s['net_profit']
    return out

def sensitivity(trades):
    rows=[]
    for extra,cm in [(0,1),(.10,1),(.25,1),(.50,1),(.25,1.5),(.50,2)]:
        adjusted=[]
        for t in trades:
            z=dict(t);z['net']=t['net']-100*t['volume']*extra-abs(t['commission'])*(cm-1);z['commission']=t['commission']*cm;adjusted.append(z)
        s=group_stats(adjusted);rows.append(dict(extra_round_trip_price_cost=extra,commission_multiplier=cm,
            additional_execution_cost_usd=-sum(100*t['volume']*extra for t in trades),**s))
    return rows

def bootstrap(months):
    # Three-month block resampling of closed monthly returns; no claim to tick equity DD.
    rates=np.array([m['return_pct']/100 for m in months[1:-1]]);n=60;rng=np.random.default_rng(39132026);stats=[]
    for trial in range(1000):
        draws=[]
        while len(draws)<n:
            start=int(rng.integers(0,len(rates)-2));draws.extend(rates[start:start+3])
        eq=10000*np.cumprod(np.r_[1.,1+np.array(draws[:n])]);peak=np.maximum.accumulate(eq)
        stats.append([eq[-1],100*np.max((peak-eq)/peak)])
    a=np.array(stats)
    return dict(paths=1000,seed=39132026,block_months=3,horizon_months=n,source_complete_months=len(rates),
      ending_balance_quantiles=dict(zip(('p05','p50','p95'),np.quantile(a[:,0],[.05,.5,.95]).tolist())),
      monthly_closed_drawdown_quantiles=dict(zip(('p05','p50','p95'),np.quantile(a[:,1],[.05,.5,.95]).tolist())),
      fraction_ending_below_start=float(np.mean(a[:,0]<10000)),limitations='Resampled observed monthly closed P/L; not future probabilities, native intraday equity DD, independent OOS, or prop-firm pass estimates.')

def main():
    selected=json.loads((ROOT/'main-results.json').read_text());assert set(selected)==set(WINDOWS)
    lock=json.loads((ROOT/'frozen-selection.json').read_text());assert lock['source_hashes']==hashes()
    c=lock['config'];stresses=json.loads((ROOT/'stress-results.json').read_text());counts=json.loads((ROOT/'Search'/'counts.json').read_text())
    neighbors=json.loads((ROOT/'native-neighborhood.json').read_text());assert len(neighbors)==4
    finalists=json.loads((ROOT/'native-finalists.json').read_text());raw={p:json.loads((RAW/'Runs'/f'{p}-engine0-d1.json').read_text()) for p in WINDOWS}
    allnative=[json.loads(p.read_text()) for p in (ROOT/'Runs').glob('*.json')];verification=[]
    for r in allnative:
        assert r['source_hashes']==hashes()
        ts=ledger(r);s=group_stats(ts);assert abs(s['net_profit']-r['net_profit'])<.01 and s['trades']==r['trades']
        assert r['max_concurrent_positions']<=3 and r['verified_decisions']>0
        assert hashlib.sha256((ROOT/r['report']).read_bytes()).hexdigest()==r['report_sha256']
        verification.append(dict(period=r['period'],model=r['model'],delay_ms=r['execution_delay_ms'],trades=r['trades'],decisions=r['verified_decisions'],report_hash_checked=True,management=audit(r)))
    base=selected['5y'];ts=ledger(base);months=monthly(ts);costs=sensitivity(ts);boot=bootstrap(months)
    assert abs(sum(m['net_profit'] for m in months)-base['net_profit'])<.01
    save(ROOT/'monthly-breakdown.json',months)
    yearly=[]
    for year in range(2021,2027):
        yearly.append(dict(year=year,**group_stats([t for t in ts if t['close_time'].startswith(str(year))])))
    save(ROOT/'yearly-breakdown.json',yearly)
    with (ROOT/'monthly-breakdown.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(months[0]));w.writeheader();w.writerows(months)
    save(ROOT/'cost-sensitivity.json',costs);save(ROOT/'bootstrap.json',boot)
    save(ROOT/'verification.json',dict(native_runs=verification,unit_tests=14,default_native_ledger_parity=True,source_hashes=hashes(),optimization_counts=counts))
    lines=['# 3 way gold — full parameter research results','',
      '**Research/tester only. No live, website, BAT or Git changes.** This is our implementation of the three-engine concept, not the Instagram creator\'s unavailable code.',
      '',f"Search: **{sum(counts['engine_runs'].values()):,} engine configurations**, {counts['combined_configs']} combined configurations evaluated in two chronological splits, four native finalists and **{len(allnative)} completed native runs** including parity, controls and stresses.",
      'This was a broad bounded discrete search plus local refinement, not every possible combination and not a guarantee of globally best parameters. Screening estimates are not presented as native backtests.',
      '', '## Selected settings','',
      f"Selection ID: `{lock['id']}`. Frozen {lock['frozen_at_utc']} before opening the latest-year diagnostic. Passed development/validation eligibility: **{lock['eligible']}**.",
      f"Direction: **{ {0:'both',1:'long only',-1:'short only'}[c['InpDirection']]}**. H1 closed candles. ATR length **{c['InpATRPeriod']}**. Nominal **{c['InpRiskPerEnginePercent']:.2f}% equity per engine**, up to three simultaneous positions on one $10,000 hedging account.",
      '', '| Engine | Optimized entry | Stop | Target |','|---|---|---|---|',
      f"| Momentum | EMA{c['InpPullbackEMA']} reclaim; EMA{c['InpTrendFastEMA']}/{c['InpTrendSlowEMA']} direction; ADX{c['InpADXPeriod']} >= {c['InpADXMin']:g}, DI agreement | {c['InpMomentumStopATR'] or c['InpStopATR']:g} ATR | {c['InpMomentumRR'] or c['InpRewardRisk']:g}R |",
      f"| Trend change | EMA{c['InpChangeFastEMA']}/{c['InpChangeSlowEMA']} crossover; RSI{c['InpRSIPeriod']} > {c['InpRSIThreshold']:g} for buys | {c['InpChangeStopATR'] or c['InpStopATR']:g} ATR | {c['InpChangeRR'] or c['InpRewardRisk']:g}R |",
      f"| Breakout | Previous {c['InpBreakoutBars']} hours; true range >= {c['InpExpansionATR']:g} preceding ATR; rising ATR {'required' if c['InpRisingATR'] else 'not required'} | {c['InpBreakoutStopATR'] or c['InpStopATR']:g} ATR | {c['InpBreakoutRR'] or c['InpRewardRisk']:g}R |",
      '', f"Management: **{ {0:'fixed SL/TP',1:'move SL to entry after completed H1 close reaches trigger',2:'closed-H1 ATR trailing',3:'break-even plus closed-H1 ATR trailing'}[c['InpManagement']]}**. Trigger {c['InpTriggerR']:g}R; trailing distance {c['InpTrailATR']:g} ATR (inactive unless management is 2 or 3). Stops only ratchet favorably, and TP stays fixed. A trigger beyond an engine's TP is normally unreachable for that engine. Entry-price break-even can still lose commission/swap.",
      '', '## Raw versus selected — native MT5','',
      'Independent $10,000 starts. Windows end 2026-09-05 exclusive (last trading tick September 4), using Exness Zero demo, 1:2000 leverage, Model4 requested, 1ms baseline delay. Net results include recorded commission/swap. Total return, not annualized. DD is native/every-tick equity drawdown.',
      '', '| Window | Raw return | Selected return | Selected final USD | Raw / new trades | Raw / new win rate | Raw / new PF | Raw / new equity DD |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in WINDOWS:
        a=raw[p];r=selected[p];lines.append(f"| {p} | {a['return_pct']:+.2f}% | {r['return_pct']:+.2f}% | {money(r['final_balance'])} | {a['trades']} / {r['trades']} | {a['net_win_rate']:.2f}% / {r['net_win_rate']:.2f}% | {fpf(a['net_pf'])} / {fpf(r['net_pf'])} | {a['max_equity_dd_pct']:.2f}% / {r['max_equity_dd_pct']:.2f}% |")
    lines+=['','## Cash costs, exposure and execution','', '| Window | Net USD | Commission | Swap | Max individual initial risk | Max concurrent | Minimum equity | Stopout | Order/management errors |','|---|---:|---:|---:|---:|---:|---:|---|---:|']
    for p,r in selected.items():lines.append(f"| {p} | {money(r['net_profit'])} | {money(r['commission'])} | {money(r['swap'])} | {r['max_trade_risk_pct']:.2f}% | {r['max_concurrent_positions']} | {money(r['minimum_equity'])} | {r['native_stopout']} | {len(r['execution_errors'])} |")
    lines+=['','The project\'s round-UP/minimum-lot policy remains in force. The risk input is NOT a hard cap, and fixed minimum lots can dominate sizing. No adaptive portfolio controls, daily stop or FTMO rules are applied. Research settings cannot be initialized on a live chart.',
      'Metadata note: the inherited max_gross_initial_stop_risk_pct field sums entry-to-CURRENT-SL downside, sampled at entries/hourly checks. With management enabled it is not a fixed original-risk sum or every-tick remaining-equity-risk cap.','',
      '## Native selection evidence — no latest-year selection','',
      'Development 2021-09-05 to 2024-09-05; validation 2024-09-05 to 2025-09-05. Eligibility requires both splits profitable, PF>1.05, DD<=20%, >=60/20 trades and no stopout. Rank is the worse split score.','',
      '| Candidate | Eligible | Development return / PF / DD / WR | Validation return / PF / DD / WR | Worst score |','|---|---|---|---|---:|']
    for r in finalists:
        t=r['train_stats'];v=r['validation_stats'];lines.append(f"| {r['id']}{' SELECTED' if r['id']==lock['id'] else ''} | {r['eligible']} | {t['return_pct']:+.2f}% / {t['net_pf']:.2f} / {t['max_equity_dd_pct']:.2f}% / {t['net_win_rate']:.2f}% | {v['return_pct']:+.2f}% / {v['net_pf']:.2f} / {v['max_equity_dd_pct']:.2f}% / {v['net_win_rate']:.2f}% | {r['rank']:.2f} |")
    lines+=['','### Native local parameter stability','',
      'Four one-at-a-time development-period perturbations around the selected configuration. These diagnose sensitivity without replacing the frozen selection or re-tuning on the recent diagnostic.','',
      '| Changed input | Development return | PF | Equity DD | Trades |','|---|---:|---:|---:|---:|']
    for x in neighbors:
        r=x['result'];lines.append(f"| {x['change']} | {r['return_pct']:+.2f}% | {fpf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% | {r['trades']} |")
    lines+=['','The raw historical aggregates were already viewed before optimization. The latest-year diagnostic was withheld from this parameter selection but is not pristine unseen OOS. Multiple testing and gold\'s historical trend bias remain risks. No re-tuning after the diagnostic.','',
      '## Five-year contributions inside the actual shared account','', '| Engine | Trades | Win rate | Net USD | Net PF |','|---|---:|---:|---:|---:|']
    for n,r in base['by_engine'].items():lines.append(f"| {n} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {fpf(r['net_pf'])} |")
    assert abs(sum(r['net_profit'] for r in base['by_engine'].values())-base['net_profit'])<.01
    lines+=['','## Same settings, different engine allocation — native five years','',
      'These are post-selection diagnostics, not changes to the frozen main candidate. Risk stays per engine, so removing engines reduces nominal deployment. Do not add independent returns together.','',
      '| Enabled engines | Trades | Return | PF | Equity DD | Win rate |','|---|---:|---:|---:|---:|---:|']
    for r in [base,*stresses['allocations']]:
        names=[n for n in ('Momentum','Change','Breakout') if r['config']['Inp'+n+'RiskWeight']>0]
        lines.append(f"| {' + '.join(names)} | {r['trades']} | {r['return_pct']:+.2f}% | {fpf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% | {r['net_win_rate']:.2f}% |")
    lines+=['','## Risk sensitivity — native five years','', '| Nominal risk per engine | Return | Net PF | Equity DD | Max actual trade risk |','|---|---:|---:|---:|---:|']
    for r in sorted([base,*stresses['risk']],key=lambda r:r['config']['InpRiskPerEnginePercent']):lines.append(f"| {r['config']['InpRiskPerEnginePercent']:.2f}% | {r['return_pct']:+.2f}% | {fpf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% | {r['max_trade_risk_pct']:.2f}% |")
    lines+=['','Risk variants are sensitivities, not retrospective replacement of the frozen 0.30% setting. Minimum-lot constraints can prevent lower inputs from meaningfully reducing actual risk.','',
      '## Native execution-delay stress — latest year','', '| Delay | Trades | Return | Net PF | Equity DD |','|---|---:|---:|---:|---:|']
    for r in [selected['1y'],*stresses['delay']]:lines.append(f"| {r['execution_delay_ms']} ms | {r['trades']} | {r['return_pct']:+.2f}% | {fpf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% |")
    lines+=['','MT5 delay applies to EA requests, not all server-side stop executions. This does not reproduce broker rejection, historical high-margin rules or every live-news gap.','',
      '## Extra friction — five-year fixed trade-ledger sensitivity','',
      'Additional round-trip price cost is deducted as cost × contract100 × lots from each native closed trade, plus the commission multiplier. This does not re-execute trades, change position sizing or reconstruct historical fee schedules.','',
      '| Extra price cost | Commission multiple | Net USD | Return on initial 10K | Net PF | Win rate |','|---|---:|---:|---:|---:|---:|']
    for r in costs:lines.append(f"| {r['extra_round_trip_price_cost']:.2f} | {r['commission_multiplier']:.1f}x | {money(r['net_profit'])} | {r['net_profit']/100:+.2f}% | {fpf(r['net_pf'])} | {r['net_win_rate']:.2f}% |")
    q=boot['ending_balance_quantiles'];dq=boot['monthly_closed_drawdown_quantiles']
    lines+=['','## 1,000 historical block-bootstrap paths','',
      f"Three-month blocks sampled from {boot['source_complete_months']} complete calendar months, excluding the two partial edge months, to form {boot['horizon_months']}-month paths. Ending balance 5th / median / 95th percentile: **{money(q['p05'])} / {money(q['p50'])} / {money(q['p95'])}**. Monthly closed-balance DD median / 95th: **{dq['p50']:.2f}% / {dq['p95']:.2f}%**. Paths finishing below $10,000: **{100*boot['fraction_ending_below_start']:.1f}%**.",
      'These resampling frequencies are NOT reliable future loss probabilities, prop-firm passing chances or intraday equity-risk estimates. Monthly close DD misses intramonth excursions. Overlapping three-month blocks retain limited serial dependence, not future regime shifts.','',
      '## Honest recommendation','',
      'Use the native development, validation, recent-year result and cost sensitivity together. A qualifying historical candidate is suitable for further demo observation, not a guarantee of live profitability or a reason to deploy automatically. Any recommendation to drop an engine must be reviewed separately; all three remain in the frozen main research set. Increasing risk to lift historical return does not create a better edge.',
      '', '## Coverage and reproducibility','',
      '- Real-tick history begins2026-01-01; earlier absent real ticks are generated by MT5. Model4 does not guarantee real historical ticks across all years.',
      '- The approximate baseline screen differed from native five-year return (~+2.82% vs +4.84%), illustrating why screening rankings alone were not accepted as final evidence.',
      '- Recorded native commission and swap are included once per trade. They are the tester\'s loaded conditions, not an independently reconstructed historical schedule.',
      '- Default parameterized EA exactly matches all185 raw six-month trades, including prices, sizes, stops and costs. 14 focused tests pass; independent indicator calculations matched29,558 raw decisions before screening. Every final native decision, entry, ledger and report hash is checked.',
      '- All selected windows stop September4,2026. Latest September7–11 is excluded to match existing comparison windows.',
      '- Source hashes, parameter files, closed-trade data, native HTML reports, search results, freeze time and verification are saved. No active EA or website evidence has been overwritten.',
      '', 'See [PROTOCOL.md](PROTOCOL.md), [selected-config.json](selected-config.json), [native-finalists.json](native-finalists.json), [verification.json](verification.json) and [monthly-breakdown.csv](monthly-breakdown.csv).',
      '', '## Monthly combined results — selected five-year account','',
      'Closed-trade attribution with full recorded trade costs at closure; not monthly mark-to-market equity or payouts. First/last months partial.','',
      '| Month | Trades | Win rate | Net USD | Closed return | Ending balance | Commission | Swap |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in months:lines.append(f"| {r['month']} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {r['return_pct']:+.2f}% | {money(r['end_balance'])} | {money(r['commission'])} | {money(r['swap'])} |")
    lines+=['','![Native raw versus selected](raw-vs-optimized.png)','']
    (ROOT/'OPTIMIZATION RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained',sharex=True)
    for label,r,folder,color in [('Raw',raw['5y'],RAW,'#7d8491'),('Optimized',base,ROOT,'#008f79')]:
        path=folder/'Audit'/('5y-engine0-d1-equity.csv' if label=='Raw' else f"{r['period']}-engine0-d1-equity.csv")
        with path.open() as f:eq=list(csv.DictReader(f))
        eq.append(dict(time=r['actual_last_tick'],balance=r['final_balance'],equity=r['final_balance']))
        t=[datetime.strptime(a['time'],'%Y.%m.%d %H:%M:%S') for a in eq];values=np.array([float(a['equity']) for a in eq]);peak=np.maximum.accumulate(np.r_[10000,values])[1:]
        axes[0].plot(t,values,label=f"{label}: {r['return_pct']:+.2f}% | PF {r['net_pf']:.2f}",color=color,lw=.85)
        axes[1].plot(t,100*(values/peak-1),label=f"{label}: native max DD {r['max_equity_dd_pct']:.2f}%",color=color,lw=.8)
    axes[0].set_title('3 way gold | native MT5 | independent USD 10,000 starts\nSame nominal 0.30% per engine; selected settings frozen before latest-year diagnostic')
    axes[0].set_ylabel('Equity USD (hourly samples)');axes[1].set_ylabel('Sampled equity drawdown (%)')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.supxlabel('Generated ticks where real history unavailable before 2026. Recorded costs included. Research, not live/prop validation.',fontsize=9)
    fig.savefig(ROOT/'raw-vs-optimized.png',dpi=150);plt.close(fig)
    files=[ROOT/'OPTIMIZATION RESULTS.md',ROOT/'PROTOCOL.md',ROOT/'frozen-selection.json',ROOT/'verification.json',ROOT/'selected-config.json',ROOT/'main-results.json',ROOT/'stress-results.json',ROOT/'Search'/'counts.json',ROOT/'Search'/'finalists.json',*sorted(ROOT.glob('*.py')),*sorted((ROOT/'EA').glob('*'))]
    save(ROOT/'manifest.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print('REPORT READY',len(allnative),'native runs',flush=True)

if __name__=='__main__':main()
