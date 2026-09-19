"""Generate the raw evidence handoff without changing website/live presets."""
import csv,json,hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_raw import ROOT,LABELS,WINDOWS,group_stats

def money(v):return f'${v:,.2f}' if v>=0 else f'-${-v:,.2f}'
def pf(v):return f'{v:.3f}' if v is not None else 'N/A'
def main():
    rows=[json.loads(p.read_text()) for p in sorted((ROOT/'Runs').glob('*.json'))]
    by={(r['period'],r['engine'],r['execution_delay_ms']):r for r in rows}
    assert all((p,0,1) in by for p in WINDOWS) and all(('5y',e,1) in by for e in (1,2,3))
    mainrows=[by[(p,0,1)] for p in WINDOWS]
    lines=['# 3 way gold — raw MT5 results','',
      'Research-only v0.1. No optimization, live deployment, website changes, installer changes or Git push.',
      'The video is a concept, not an executable rulebook. This is our disclosed H1 implementation; the creator\'s +504% / 13% DD / 1,561 trades / PF 1.44 remains unverified and is not a replication benchmark.',
      '', '## Fixed strategy and risk', '',
      '- Momentum: EMA20 pullback/reclaim aligned with EMA50/200, ADX14 >= 25 and directional DI.',
      '- Trend change: fresh EMA9/21 cross confirmed by RSI14 above/below 50.',
      '- Breakout: close beyond prior 20 H1 bars, true range >= 1.5 previous ATR14 and rising ATR14.',
      '- Every signal uses completed H1 candles. Stops: 2 ATR14; TP: 2R. No trailing or break-even.',
      '- 0.30% nominal equity risk per engine; same shared account, one position per engine, up to three concurrent positions. Opposite-direction engine positions are allowed on the hedging account.',
      '- Current round-up/minimum-lot sizing retained. This is NOT a 0.90% hard portfolio risk cap. Read actual risk below.',
      '', '## Combined account — independent $10,000 starts', '',
      'All periods end **2026-09-05 exclusive**, matching the existing system evidence cutoff. Returns are total-period, not annualized. Costs are included in net P/L, win rate and net PF. DD is the larger of native/every-tick maximum relative EQUITY drawdown.', '',
      '| Window | Start | Trades | Win rate | Net P/L | Return | Final balance | Net PF | Max equity DD | Commission | Swap |',
      '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in mainrows:
        lines.append(f"| {r['period']} | {r['window'][0]} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {r['return_pct']:+.2f}% | {money(r['final_balance'])} | {pf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% | {money(r['commission'])} | {money(r['swap'])} |")
    base=by[('5y',0,1)]
    lines+=['',f"Five-year average net result per completed trade: **{money(base['net_profit']/base['trades'])}**. This is an average expectancy from this sample, not a fixed win or a live-cost guarantee."]
    lines+=['','## What each engine contributed INSIDE the combined 5-year account','',
      'These cash contributions reconcile to the combined result; they are not independent-account returns. All engines share changing equity and can hold positions simultaneously.','',
      '| Engine | Trades | Win rate | Net P/L | Net PF | Average win | Average loss | Worst loss streak | Commission | Swap |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,r in base['by_engine'].items():
        lines.append(f"| {name} | {r['trades']} | {r['net_win_rate']:.2f}% | {money(r['net_profit'])} | {pf(r['net_pf'])} | {money(r['average_win'])} | {money(r['average_loss'])} | {r['max_loss_streak']} | {money(r['commission'])} | {money(r['swap'])} |")
    assert abs(sum(r['net_profit'] for r in base['by_engine'].values())-base['net_profit'])<.05
    lines+=['','## Unchanged standalone diagnostics — 5 years','',
      'Each standalone run also starts at $10,000 with 0.30% nominal risk. The combined account can deploy three engines, so these are not equal-risk or equal-exposure performance contests. This is diagnostic attribution, not an optimization sweep.','',
      '| Run | Trades | Win rate | Return | Net PF | Max equity DD |', '|---|---:|---:|---:|---:|---:|']
    for e in (0,1,2,3):
        r=by[('5y',e,1)];lines.append(f"| {r['label']} | {r['trades']} | {r['net_win_rate']:.2f}% | {r['return_pct']:+.2f}% | {pf(r['net_pf'])} | {r['max_equity_dd_pct']:.2f}% |")
    lines+=['','## Actual sizing and execution','',
      '| Window | Highest trade stop risk / entry equity | Highest gross initial stop risk / observed equity* | Max concurrent | Lowest equity | Stopout | Order errors | Boundary exits |',
      '|---|---:|---:|---:|---:|---|---:|---:|']
    for r in mainrows:
        lines.append(f"| {r['period']} | {r['max_trade_risk_pct']:.2f}% | {r['max_gross_initial_stop_risk_pct']:.2f}% | {r['max_concurrent_positions']} | {money(r['minimum_equity'])} | {'YES' if r['native_stopout'] else 'No'} | {len(r['execution_errors'])} | {r['boundary_exits']} |")
    lines+=['','*Gross initial stop risk sums each open trade\'s original entry-to-SL loss, divided by current equity at entry/hourly checks. It does not offset hedges and is not an every-tick remaining-equity-at-risk guarantee. Per-trade risk excludes extra costs/gap losses. Fixed lot minimums can make the risk input unattainable.',
      '', '## Coverage and cost honesty','',
      '- Native MT5 Strategy Tester, Model 4 requested, fixed 1 ms execution delay; Exness Zero demo feed, 1:2000 leverage. This is not FTMO or live-account evidence.',
      '- Broker logs place real-tick history at 2026-01-01 onward. Earlier periods use generated ticks where real ticks are absent. A native "100%" history label does not turn generated ticks into observed historical ticks.',
      '- Historical broker spreads plus recorded commission/swap/fees are included. They are the tester\'s loaded data, not independently reconstructed historical fee schedules, dynamic leverage or high-margin requirements.',
      '- A 1 ms delay is optimistic and does not reproduce all news gaps, latency or adverse live fills. No full execution stress pipeline has been run.',
      '- Windows overlap and the system was defined after those historical markets occurred. These are exploratory historical results, not unseen out-of-sample evidence.',
      '- Results stop September 4 trading close; the latest September 7–11 trading week is not included, to preserve the project\'s comparison windows.',
      '', '## Verification and native evidence','']
    for r in mainrows:
        reasons=defaultdict(int)
        for error in r['execution_errors']:reasons[error['note']]+=1
        if reasons:lines.append(f"- {r['period']} unfilled order attempts: "+', '.join(f'{reason}: {n}' for reason,n in reasons.items())+'. They remain unfilled; no imaginary replacement trades are added.')
    verification=[]
    for r in rows:
        assert r['verified_decisions']>0 and r['independent_ema_checks']>0
        verification.append({k:r[k] for k in ('period','engine','verified_decisions','independent_ema_checks','source_hashes','report_sha256','max_concurrent_positions')})
    for r in mainrows:
        link=r['report'].replace('\\','/').replace(' ','%20')
        lines.append(f"- {r['period']}: [{r['actual_first_tick']} to {r['actual_last_tick']}]({link}); {r['verified_decisions']:,} closed-bar decisions checked. First/last actual tick, not assumed calendar coverage.")
    lines+=['','Native signal self-tests and Python unit tests cover mirrored long/short rules, equality boundaries, no-trend and no-expansion cases, net-cost classification, tester-only isolation, valid zero-spread quotes and no optimization. Every exported decision is independently recomputed. Channel extrema, OHLC, true range, ATR and warmed-up EMAs are checked against exported H1 history. Each filled entry has a valid engine signal; trade/fee totals reconcile with the native report; a single engine never holds overlapping positions.',
      '', 'The first 6-month preflight is archived under Preflight/. A quote-validation correction permits valid zero spreads; no signal parameters changed. Preflight vs final 6-month trade ledgers are checked for exact equality below.','']
    old=json.loads((ROOT/'Preflight'/'Audit'/'6m-engine0-d1-trades.json').read_text());new=json.loads((ROOT/'Audit'/'6m-engine0-d1-trades.json').read_text())
    equal=old==new;assert equal,'Quote-only correction changed preflight trades; investigate and disclose'
    lines.append('Preflight/final 6-month trade ledger: **identical**.')
    all_monthly=[];all_yearly=[]
    for r in rows:
        tag=f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}"
        trades=json.loads((ROOT/'Audit'/(tag+'-trades.json')).read_text())
        month_groups=defaultdict(list);year_groups=defaultdict(list)
        for t in trades:month_groups[t['close_time'][:7]].append(t);year_groups[t['close_time'][:4]].append(t)
        balance=10000
        start=datetime.strptime(r['window'][0],'%Y.%m.%d');end=datetime.strptime(r['window'][1],'%Y.%m.%d')
        current=start.replace(day=1)
        while current<end:
            key=current.strftime('%Y.%m');g=month_groups[key];s=group_stats(g);net=s['net_profit']
            all_monthly.append(dict(period=r['period'],run=r['label'],month=key,starting_closed_balance=round(balance,2),net_usd=net,
                return_on_month_start_balance_pct=100*net/balance if balance>0 else None,ending_closed_balance=round(balance+net,2),
                trades=s['trades'],win_rate=s['net_win_rate'],net_pf=s['net_pf'],commission=s['commission'],swap=s['swap'],fee=s['fee'],
                **{LABELS[e].lower().replace(' ','_')+'_net_usd':round(sum(t['net'] for t in g if t['engine']==e),2) for e in (1,2,3)}))
            balance+=net;current=current.replace(year=current.year+1,month=1) if current.month==12 else current.replace(month=current.month+1)
        for y,g in sorted(year_groups.items()):all_yearly.append(dict(period=r['period'],run=r['label'],year=y,**group_stats(g)))
    for name,data in [('monthly-breakdown',all_monthly),('yearly-breakdown',all_yearly)]:
        (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        with (ROOT/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    lines+=['','## Monthly closed-trade P/L — combined 5 years','',
      'Cash belongs to the month a trade closes, including its full recorded costs. First/last months are partial. This is not a mark-to-market monthly equity return or a payout simulation. All windows and standalone runs are in monthly-breakdown.csv/json.','',
      '| Month | Trades | Net win rate | Net USD | Closed balance | Momentum USD | Trend change USD | Breakout USD | Commission | Swap |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in all_monthly:
        if r['period']=='5y' and r['run']==LABELS[0]:lines.append(f"| {r['month']} | {r['trades']} | {r['win_rate']:.2f}% | {money(r['net_usd'])} | {money(r['ending_closed_balance'])} | {money(r['momentum_net_usd'])} | {money(r['trend_change_net_usd'])} | {money(r['breakout_net_usd'])} | {money(r['commission'])} | {money(r['swap'])} |")
    lines+=['','## Recommendation','',
      'Do not add this combined raw version to the portfolio. The five-year net PF is only about 1.01, six-month performance is negative, and the 2019–2026 run loses money. Momentum is the strongest five-year standalone candidate; trend change and breakout each lose money in their unchanged standalone runs and reduce the combined five-year profit. This does not establish momentum as a robust winner: the selection is retrospective, and it still needs separate unseen-period and execution-cost validation.',
      '', 'My proposed next step, only if approved: study momentum first; redesign the weak engines from a fresh, predeclared hypothesis before considering a full combined optimization. Address minimum-lot risk overshoot and realistic execution costs before any live or prop-firm deployment. No such optimization, redesign or deployment was performed in this raw experiment. Do not assume three named engines are independent or that a positive long backtest predicts future profits.',
      '', 'See [RULES.md](RULES.md) for engine-by-engine sources and every assumption. The research references justify candidate families, not “best settings.” No performance parameters were tuned.',
      '', '![Combined five-year account](3-way-gold-5y.png)','']
    (ROOT/'3 WAY GOLD RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'verification.json').write_text(json.dumps(dict(runs=verification,preflight_trade_ledger_identical=equal,parameters_optimized=False,deployed=False),indent=2),encoding='utf-8')
    with (ROOT/'Audit'/'5y-engine0-d1-equity.csv').open() as f:eq=list(csv.DictReader(f))
    # Include the audited terminal endpoint, not just the final hourly sample.
    assert base['boundary_exits']==0
    eq.append(dict(time=base['actual_last_tick'],balance=base['final_balance'],equity=base['final_balance']))
    ts=[datetime.strptime(r['time'],'%Y.%m.%d %H:%M:%S') for r in eq]
    fig,axes=plt.subplots(2,1,figsize=(12,7.5),layout='constrained',sharex=True)
    axes[0].plot(ts,[float(r['balance']) for r in eq],label='Closed balance',lw=1.1,color='#00a68c')
    axes[0].plot(ts,[float(r['equity']) for r in eq],label='Equity (hourly samples)',lw=.7,color='#5175ca',alpha=.75)
    axes[0].axhline(10000,color='#777',lw=.7);axes[0].set_ylabel('USD');axes[0].legend(loc='upper left')
    axes[0].set_title(f"3 way gold | USD 10,000 to {base['final_balance']:,.2f} | 5-year raw test\nReturn {base['return_pct']:+.2f}% | net PF {base['net_pf']:.2f} | every-tick max equity DD {base['max_equity_dd_pct']:.2f}%",fontsize=12)
    trades=json.loads((ROOT/'Audit'/'5y-engine0-d1-trades.json').read_text())
    for e,color in [(1,'#d29821'),(2,'#ad5ba8'),(3,'#287caf')]:
        tt=[ts[0]];yy=[0];total=0
        for t in trades:
            if t['engine']==e:total+=t['net'];tt.append(datetime.strptime(t['close_time'],'%Y.%m.%d %H:%M:%S'));yy.append(total)
        axes[1].step(tt,yy,where='post',label=LABELS[e],color=color,lw=1.2)
    axes[1].axhline(0,color='#777',lw=.7);axes[1].set_ylabel('Cumulative realized contribution (USD)');axes[1].legend()
    for ax in axes:ax.grid(alpha=.2)
    fig.supxlabel('Historical simulation: generated ticks before 2026; recorded costs included; not optimized or live/prop validated.',fontsize=9)
    fig.savefig(ROOT/'3-way-gold-5y.png',dpi=150);plt.close(fig)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sorted((ROOT/'EA').glob('*')),ROOT/'RULES.md',ROOT/'3 WAY GOLD RESULTS.md',ROOT/'verification.json']}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('REPORT, CHART, MONTHLY/YEARLY LEDGERS AND HASH MANIFEST READY')
if __name__=='__main__':main()
