"""Build a readable research report and static figure from the completed run."""
from __future__ import annotations
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['text.parse_math'] = False
from compare import ROOT, SOURCE, CONFIGS, NEWS, RAW, DAY, END, START, read, save, engine, pool, sample_rows

def f(x, digits=1):
    return '—' if x is None else f'{x:,.{digits}f}'

def main():
    all_results = read(ROOT/'RESULTS.json')
    rr = all_results['results']
    assert len(rr)==28
    assert all(len(r['outcomes'])==4 for r in rr)
    for r in rr:
        for o in r['outcomes']:
            assert o['breach_pct']==0
            assert o['payout_pct']<=o['funded_pct']+1e-9
            assert abs(o['payout_pct']+o['breach_pct']+o['unfinished_pct']-100)<1e-8
            assert abs(o['mean_first_reward_per_purchase']-100*(1-o['payout_pct']/100)-o['illustrative_net_cash_at_100_fee'])<1e-8
        assert [o['payout_pct'] for o in r['outcomes']]==sorted(o['payout_pct'] for o in r['outcomes'])
        h=r['historical_continuous']
        assert abs(sum(v['net_profit'] for v in h['log'])-(h['balance']-10000))<.01
    recent=[r for r in rr if r['pool']=='recent26' and r['stress']]
    lines=['# Which paper works best for our FTMO case?', '',
           '26 September 2026 — $10,000, one FTMO 2-Step Swing account. Research only.', '',
           '## Conclusion', '',
           '**Paper 3 is the best modeling foundation, not a proven trading strategy.** Combine its contract-specific barriers with fixed dollar risk (a useful lesson from paper 1), and report both funding and actual cash receipts (paper 2). We did not replicate all three papers as if they were EAs.', '',
           'These tests do not establish a reliable one-month funded / two-month paid plan. The news portfolios win on fitted history, but that is not independent evidence of an 80% future payout chance. Non-news rankings change with the source period and costs.', '',
           '## What was actually run', '',
           '112,000 path-horizon evaluations: 28 portfolio/pool/cost cases × 4 calendar horizons × 1,000 jointly resampled paths. These are correlated comparisons sharing random draws, NOT 112,000 independent historical samples. Original MT5 ledgers end 30 August 2026. No new MT5 tester runs or live-account queries were made.', '',
           'Recent pool: 26 weeks (2 March–30 August 2026). Longer non-news pool: 101 weeks (23 September 2024–30 August 2026). Both have previously researched strategies; neither is a pristine untouched holdout.', '',
           '## Paper fit', '',
           '| Paper | Useful contribution | Why its headline result is not our forecast |',
           '|---|---|---|',
           '| 1. Inherent Value / fixed-size | Consistent sizing and full fee/payout cash accounting | Random-direction MNQ, Topstep rules, repeated purchases over ten years; not our one FTMO account. A code-review concern was that its entry minute is skipped when checking exits. |',
           '| 2. Price of a Funded Account | Separates passing, first payout and contract value | Gaussian daily P&L and daily-close checks do not capture our intraday/news gaps. Its illustrative evaluation deadlines differ from unlimited FTMO evaluation. Daily volatility of 2% is not risk of 2% per trade. |',
           '| 3. Valuing evaluation contracts | Models static vs trailing barriers, timing, daily limits and economic value | Best framework, but still needs our actual fills, dependence, contract and costs; its published pass probabilities are not our EA probabilities. |', '',
           '## First payout receipt: matched recent pool, stressed execution', '',
           'All percentages below are conditional simulation frequencies, not validated real-world probabilities. Ordinary risk is fixed initial dollars; news always $10 per side. Both pending news orders are retained.', '',
           '| Portfolio | 30d paid | 60d paid | 120d paid | 180d paid | 180d funded | 180d unfinished |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in recent:
        oo=r['outcomes'];last=oo[-1]
        lines.append('| '+r['config']['name']+' | '+' | '.join(f(o['payout_pct'])+'%' for o in oo)+f" | {f(last['funded_pct'])}% | {f(last['unfinished_pct'])}% |")
    lines += ['', 'Unfinished is not breached: it includes evaluation still running and funded accounts that have not received their first reward. All cells produced zero hard breaches under the modeled gates. That is not evidence of zero real breach risk: floating equity is only a stop-loss reserve, and gaps/platform failures are not bounded by it.', '',
              '## Source-period and cost sensitivity: first payout by 180 days', '',
              '| Portfolio | Recent reference | Recent stress | Longer reference | Longer stress |',
              '|---|---:|---:|---:|---:|']
    lookup={(r['config']['name'],r['pool'],r['stress']):r for r in rr}
    for c in CONFIGS:
        values=[]
        for p,s in [('recent26',False),('recent26',True),('long101',False),('long101',True)]:
            r=lookup.get((c['name'],p,s));values.append(f(r['outcomes'][-1]['payout_pct'])+'%' if r else 'Not enough news coverage')
        lines.append('| '+c['name']+' | '+' | '.join(values)+' |')
    lines += ['', 'The news combinations cannot be assigned comparable longer-pool estimates without inventing missing events. Adding more EAs or increasing risk does not reliably improve the result.', '',
              '## Actual chronology: 4 March–30 August 2026, stressed, continuous account', '',
              'A fixed $10K account without evaluation phase resets or payouts. Shared risk/margin gates still apply. This is a saved-ledger replay, not a new native FTMO backtest. Return is not cash income.', '',
              '| Portfolio | Closed trades | Trades/week | Net return | Win rate | PF | Closed-balance DD | Stop-reserve DD | Max W/L streak |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in recent:
        h=r['historical_continuous']
        lines.append(f"| {r['config']['name']} | {h['trades']} | {f(h['trades']/(180/7),2)} | {f(100*(h['balance']/10000-1),2)}% | {f(h['win_rate'])}% | {f(h['pf'],2)} | {f(h['closed_dd_pct'],2)}% | {f(h['model_dd_pct'],2)}% | {h['max_win_streak']}/{h['max_loss_streak']} |")
    lines += ['', 'Peak-to-trough drawdown can exceed 10% without violating a static 10%-of-initial-capital loss floor; do not conflate these quantities. The stop-reserve drawdown is not measured tick-equity drawdown.', '',
              '## Cash economics: 180 days, recent pool, stress', '',
              'First reward only; 80% trader share already applied. $100 fee is an illustration, NOT an FTMO checkout quote. Assume fee refunded with first reward. Net cash = mean received reward − fee × (1 − payout probability). Unfinished accounts retain possible future value; taxes, VPS and currency conversion are excluded.', '',
              '| Portfolio | Median reward if paid | Mean reward per initial purchase | Net cash using $100 fee | Fee break-even by this horizon | 95% MC interval for receipt |',
              '|---|---:|---:|---:|---:|---:|']
    for r in recent:
        o=r['outcomes'][-1];lo,hi=o['payout_mc_interval']
        lines.append(f"| {r['config']['name']} | ${f(o['median_first_reward_if_paid'],2)} | ${f(o['mean_first_reward_per_purchase'],2)} | ${f(o['illustrative_net_cash_at_100_fee'],2)} | ${f(o['breakeven_fee_by_horizon'],2)} | {f(lo)}–{f(hi)}% |")
    lines += ['', 'Monte Carlo intervals describe randomness in drawing paths from the same small dataset only. They do not cover parameter fitting, future market behavior, missing intraday equity or payout eligibility. Zero observed outcomes in 1,000 paths does not establish mathematical impossibility.', '',
              '## Actual chronological challenge outcome', '',
              '| Portfolio | Funded | First reward received | Reward amount | Request date | Receipt date |',
              '|---|---|---|---:|---|---|']
    for r in recent:
        h=r['historical_challenge']
        lines.append(f"| {r['config']['name']} | {h['funded']} | {h['payout']} | ${f(h['reward'] if h['payout'] else 0,2)} | {h['request_at'] or '—'} | {h['receipt_at'] or '—'} |")
    lines += ['', '## Portfolio membership', '']
    for c in CONFIGS:
        lines += ['### '+c['name'], '', ', '.join(c['keys']), '']
    lines += ['## Coverage by EA, recent joint pool', '', '| EA | Observed entries |', '|---|---:|']
    data=read(SOURCE/'prepared.json')
    pool_start=datetime.fromisoformat(recent[0]['pool_start']).timestamp()
    for k in sorted({k for c in CONFIGS for k in c['keys']}):
        n=sum(pool_start<=r['op']<END and r['cl']<END for r in data['rows'][k])
        lines.append(f'| {k} | {n} |')
    lines += ['', '## Risk controls and limitations', '',
              'Internal settings tested: $300 daily admission budget, $225 simultaneous initial risk, $150 correlated-metal/per-symbol cap, $9,200 internal total buffer, at most seven entries/day and no new entries after three closed losses. Lot sizes round up in 0.01 steps, so actual initial risk can exceed the nominal setting. These are scenario choices, not optimized recommendations.', '',
              'The simulation includes shared margin and reserves both news sides. It does not re-run skipped-trade effects on every EA state, replay historical bid/ask ticks, model emergency close failure, estimate account disqualification likelihood, or establish long-run funded-account survival after the first reward.', '',
              'FTMO Swing permits news trading generally, but FTMO also forbids specified gap-trading practices around scheduled news. The exact pre-event two-sided News Pulse method needs written confirmation from FTMO before treating payout eligibility as established. Do not deploy it based on this table.', '',
              '## Verification', '',
              'Source hashes match the existing manifest; nine original deterministic engine tests pass, seven additional assertions pass, and eight saved historical result fields reproduce exactly. All 112 outcome cells reconcile, funded probability is at least payout probability, and historical ledgers reconcile to final cash balances. No production imports or MT5 connections were made.', '',
              '## Sources and complete assumptions', '',
              '- [FTMO 2-Step comparison](https://ftmo.com/en/comparison-table/)',
              '- [Reward timing and share](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)',
              '- [Forbidden trading practices](https://ftmo.com/en/forbidden-trading-practices/)',
              '- [Paper 1](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7514219)',
              '- [Paper 2](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7178078)',
              '- [Paper 3](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7260819)',
              '- PROTOCOL.md contains full costs, margin assumptions, delays and caveats.',
              '- RESULTS.json contains every outcome, historical trade record and admission counter.', '']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    save(ROOT/'REPORT_CHECKS.json',dict(cells=112, source_cases=28, outcome_accounting='passed',
                                      historical_cash_reconciliation='passed', monotonic_receipts='passed'))
    # Plot the actual generated model results, not illustration or invented equity.
    fig,axes=plt.subplots(1,2,figsize=(13,6.8),sharex=True)
    fig.patch.set_facecolor('#f7f9fc')
    wanted=[('Five EAs / $71.43','#2263aa'),('Eight EAs / $71.43','#6f57ad'),
            ('Eight EAs / $100','#d46427'),('Raw Gold / $71.43','#61797d')]
    for ax,p,subtitle in zip(axes,['recent26','long101'],['Recent 26 weeks','Longer 101 weeks — no news data']):
        for name,color in wanted:
            r=lookup[name,p,True]
            ax.plot([o['horizon_days'] for o in r['outcomes']],[o['payout_pct'] for o in r['outcomes']],
                    marker='o',lw=2,label=name,color=color)
        if p=='recent26':
            for name,color in [('Raw Gold + news / $71.43 + $10','#aa3151'),('High-win + news / $71.43 + $10','#168875')]:
                r=lookup[name,p,True]
                ax.plot([o['horizon_days'] for o in r['outcomes']],[o['payout_pct'] for o in r['outcomes']],
                        marker='s',ls='--',lw=2,color=color,label=name+' *')
        ax.set_title(subtitle,fontsize=13,loc='left',pad=14)
        ax.set_xticks([30,60,120,180]);ax.set_xlabel('Calendar days from purchase')
        ax.set_ylim(0,100 if p=='recent26' else 25)
        ax.set_ylabel('Paths receiving first reward (%)')
        ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.08),ncol=2,frameon=False,fontsize=9)
    fig.suptitle('$10K FTMO Swing: reaching a first payout, with stressed costs',fontsize=17,x=.05,ha='left',y=.97)
    fig.text(.05,.025,'* News presets fitted to this history; eligibility unresolved. 1,000 paths/case, not validated future probabilities.\nSaved-ledger simulation; no new FTMO tick test. Different panel scales.',fontsize=9,color='#4c5665')
    fig.subplots_adjust(left=.07,right=.98,top=.83,bottom=.31,wspace=.28)
    fig.savefig(ROOT/'payout_comparison.png',dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)
    print('Report, chart and all-cell validation complete.')

if __name__=='__main__':
    main()
