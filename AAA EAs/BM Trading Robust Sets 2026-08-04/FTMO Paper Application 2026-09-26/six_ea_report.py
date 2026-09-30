"""Verify saved six-EA results and produce a human-readable research report."""
from collections import Counter,defaultdict
from datetime import datetime
import statistics
import compare as c
import phase_breakdown as ph
import six_ea as s

LABELS={c.RAW:'Gold Overnight Value Area (raw)',c.NEWS[0]:'News Pulse XAU',c.NEWS[1]:'News Pulse XAG',
        s.OVERNIGHT:'Nasdaq Overnight',s.EMA:'EMA3 Full Safe',s.ORB:'ORB Volume Profile 0.75R'}

def f(x,d=1):return '—' if x is None else f'{x:.{d}f}'
def money(x):return '—' if x is None else f'${x:,.2f}'
def net(r):return r['historical_continuous']['balance']-10000
def get(out,sizing,stress,n):
    return next(r for r in out['cases'] if r['sizing']==sizing and r['stress']==stress and r['config']['name']==n)

def verify(out):
    assert len(out['cases'])==8
    horizons=0
    for case in out['cases']:
        assert len(case['paths'])==1000
        ns=s.make_engine(case['sizing'])
        for h in case['summary']['horizons']:
            cutoff=c.START+h['days']*c.DAY
            counts=Counter(ph.classify(ph.marks(r,ns),cutoff) for r in case['paths'])
            assert dict(counts)==h['counts']
            assert sum(counts.values())==1000
            assert 0<=h['payout_pct']<=h['funded_pct']<=h['both_pass_pct']<=h['phase1_pass_pct']<=100
            horizons+=1
        s.reconcile(case['historical_continuous'],case['sizing']=='strict_round_down')
        by=case['historical_continuous']['by_ea']
        assert abs(sum(v['net'] for v in by.values())-net(case))<1e-7
    c.verify_sources()
    return dict(cases=8,path_records=8000,horizon_state_reconciliations=horizons,
                historical_cash_ledgers_reconciled=8,strict_sizing_assertions='passed',
                source_checks=out['checks'])

def main():
    out=c.read(c.ROOT/'SIX_EA_RESULTS.json')
    validation=verify(out)
    c.save(c.ROOT/'SIX_EA_CHECKS.json',validation)
    core=get(out,'strict_round_down',True,'Three-EA core')
    six=get(out,'strict_round_down',True,'Six EAs together')
    h0=core['summary']['horizons'][-1];h1=six['summary']['horizons'][-1]
    lines=['# FTMO $10K Swing — all three additions together', '',
        'Research report: 27 September 2026. Simulation only. No live account, EA, BAT, website or production risk policy changed.', '',
        '## Outcome', '',
        f"With strict round-down sizing and stressed execution, the modeled six-month funding rate is {h1['funded_pct']:.1f}% versus {h0['funded_pct']:.1f}% for the core; first-reward receipt is {h1['payout_pct']:.1f}% versus {h0['payout_pct']:.1f}%. These are fitted-history scenario frequencies, NOT calibrated real-world probabilities.", '',
        f"Historical continuous-account P&L increases by {money(net(six)-net(core))}, from {money(net(core))} to {money(net(six))}. Admitted trades increase from {core['historical_continuous']['trades']} to {six['historical_continuous']['trades']}; win rate falls from {core['historical_continuous']['win_rate']:.2f}% to {six['historical_continuous']['win_rate']:.2f}% and reserve-based drawdown rises from {core['historical_continuous']['model_dd_pct']:.2f}% to {six['historical_continuous']['model_dd_pct']:.2f}%.", '',
        '## Six-EA basket', '', '| EA | Role | Planned stop-risk sizing |', '|---|---|---|']
    for k in s.SIX:
        lines.append(f"| {LABELS[k]} | {'Existing core' if k in s.CORE else 'Added in this simulation'} | {'$10 per pending side' if k in c.NEWS else '$71.43 per entry'} |")
    lines += ['', 'The new Nasdaq addition is **Nasdaq Overnight**, not Nasdaq 5M DI. Neither RSI VWAP nor Gold News V9 is included. ORB uses the saved 0.75R / Dynamic 50-20 configuration; it has not been restored to the launcher.', '',
        'Strict sizing rounds DOWN to 0.01 lots. Skip a signal if its minimum lot exceeds the planned stop-risk budget. This caps initial price-to-stop risk, NOT realized loss including gaps, commission and slippage. The reference calculation uses the exact $500/7 amount before rounding.', '',
        'Both news sides remain enabled, but all pending/open positions share account risk and margin. Limits are unchanged: $300 daily admission budget, $225 aggregate simultaneous initial risk, $150 combined metals/per-symbol initial risk, $9,200 internal projected-equity buffer, seven entries/day, no new entries after three closed losses, maximum 80% reserved margin.', '',
        '## Method and evidence', '',
        '- 1,000 paired paths per portfolio/sizing/cost case; eight cases, 8,000 paths total. Seed 20260926. The same 26 weekly draws are used across every combination.',
        '- Source pool: 2 March–30 August 2026. Synthetic evaluation purchase: 28 September 2026. Historical replay: 4 March–30 August 2026. September trades are not included, preserving the prior comparison window.',
        '- Existing native broker trade ledgers, resampled jointly by week; no fresh FTMO tick backtest. Within-week relationships are preserved, not multi-week dependence; spanning trades and holiday schedules can be distorted by resampling.',
        '- ORB recovered directly from its native MT5 Orders/Deals tables: all 304 five-year trades match the cached timing, side, lot, prices and net P&L; commission/swap/gross P&L and initial stops reconstructed. Total native net reconciles to $1,204.05. Only the matching study-period trades are used.',
        '- News parameters were fitted to overlapping history; added EAs were shortlisted after seeing historical results. The source has only 20 XAU and 17 XAG news trades. Repeated sampling cannot create independent evidence.',
        '- Reference retains native fills and spread with commission floors. Stress reduces gross wins 10%, enlarges gross losses 10%, adds adverse slippage ($0.20 ordinary gold/$1 news gold, $0.04 silver, two Nasdaq points), doubles negative swaps and reserves additional carry.',
        '- Floating equity is approximated by full-stop reserves (ordinary 1R/reference or 1.25R/stress; news 1.25R/reference or 2R/stress). This is NOT tick-measured equity and is NOT a guaranteed bound on gap losses.', '',
        'FTMO assumptions: $10,000 2-Step Swing; +$1,000 then +$500, four trading days per phase, $500 daily and $1,000 static total-loss limits, Prague midnight reset; no evaluation time limit or 2-Step Best Day Rule. See [FTMO comparison](https://ftmo.com/en/comparison-table/).', '',
        'Administrative assumptions: two business days between evaluations, five until funded activation, first request after at least 14 calendar days from first funded trade and while flat, four business days for receipt; 80% reward share. Minimum modeled closed profit for request is $25. Actual administration can differ. See [reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/). Simulation stops at first request or day 180; it does not model later funded-account survival.', '',
        '## Strict planned-risk cap — stressed execution', '',
        '| Calendar days | Core funded | Six-EA funded | Core first payout received | Six-EA first payout received |',
        '|---|---:|---:|---:|---:|']
    for x,y in zip(core['summary']['horizons'],six['summary']['horizons']):
        lines.append(f"| {x['days']} | {x['funded_pct']:.1f}% | {y['funded_pct']:.1f}% | {x['payout_pct']:.1f}% | {y['payout_pct']:.1f}% |")
    lines += ['', '### Six-EA phase progression', '',
        '| Days | Phase 1 passed | Both phases passed | Funded/activated | First payout received | Hard breaches before first reward | Still evaluating |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for h in six['summary']['horizons']:
        vals=[h[k] for k in ('phase1_pass_pct','both_pass_pct','funded_pct','payout_pct','breach_before_first_reward_pct','unfinished_evaluation_pct')]
        lines.append(f"| {h['days']} | "+' | '.join(f'{v:.1f}%' for v in vals)+' |')
    lines += ['', '### Timing, conditional on completion by day 180', '',
        '| Milestone | Core median days | Six-EA median days | Six-EA 10th–90th percentile | Six-EA completed paths |',
        '|---|---:|---:|---:|---:|']
    for k,label in [('phase1_days_among_phase1_passers','Phase 1 from purchase'),
        ('phase2_days_from_availability_among_phase2_passers','Phase 2 from availability'),
        ('funded_days_from_purchase','Funded including review waits'),('payout_days_from_purchase','First reward received')]:
        x=core['summary']['timing'][k];y=six['summary']['timing'][k]
        lines.append(f"| {label} | {f(x['median'])} | {f(y['median'])} | {f(y['p10'])}–{f(y['p90'])} | {y['n']} |")
    lines += ['', 'These are different conditional cohorts; do not add separate medians. Unfinished accounts are censored, not assigned zero days or called breached.', '',
        '### Paired-path comparison at day 180', '']
    for label,p in six['paired180'].items():
        ci=p['paired_mc_only_interval']
        lines.append(f"- {label.title()}: {p['delta_percentage_points']:+.1f} percentage points; {p['new_only']} paths succeed only with six EAs, {p['core_only']} only with the core. Paired 95% Monte Carlo-only interval: {ci[0]:+.1f} to {ci[1]:+.1f} pp.")
    lines += ['', 'Monte Carlo intervals exclude selection bias, small-history uncertainty, model error and changing execution. They are not real-world confidence bounds.', '',
        '## Historical continuous account — strict sizing and stressed costs', '',
        'No withdrawals or phase resets in this comparison. P&L is hypothetical account trading profit, not payout income.', '',
        '| Metric | Three-EA core | Six EAs together |', '|---|---:|---:|']
    x=core['historical_continuous'];y=six['historical_continuous']
    metrics=[('Trades',str(x['trades']),str(y['trades'])),('Net P&L',money(net(core)),money(net(six))),
        ('Win rate',f(x['win_rate'],2)+'%',f(y['win_rate'],2)+'%'),('Profit factor',f(x['pf'],2),f(y['pf'],2)),
        ('Closed-balance DD',f(x['closed_dd_pct'],2)+'%',f(y['closed_dd_pct'],2)+'%'),
        ('Stop-reserve equity DD proxy',f(x['model_dd_pct'],2)+'%',f(y['model_dd_pct'],2)+'%'),
        ('Worst modeled daily loss',money(x['worst_daily_usd']),money(y['worst_daily_usd'])),
        ('Longest winning/losing streak',f"{x['max_win_streak']}/{x['max_loss_streak']}",f"{y['max_win_streak']}/{y['max_loss_streak']}"),
        ('Average trades per seven calendar days',f(x['trades']/(180/7),2),f(y['trades']/(180/7),2)),
        ('News baskets admitted',str(x['counts'].get('news_baskets',0)),str(y['counts'].get('news_baskets',0))),
        ('Minimum-lot signals skipped',str(x['counts'].get('min_lot_over_budget',0)),str(y['counts'].get('min_lot_over_budget',0)))]
    for label,xv,yv in metrics:lines.append(f'| {label} | {xv} | {yv} |')
    lines += ['', '### Per-EA contribution in the six-EA account', '',
        '| EA | Trades | Wins | Win rate | Net P&L | Largest planned initial risk |', '|---|---:|---:|---:|---:|---:|']
    for k in s.SIX:
        v=y['by_ea'].get(k,{});tr=v.get('trades',0)
        mx=max((t['initial_risk'] for t in y['log'] if t['ea']==k),default=0)
        lines.append(f"| {LABELS[k]} | {tr} | {v.get('wins',0)} | {f(100*v.get('wins',0)/tr if tr else None,2)}% | {money(v.get('net',0))} | {money(mx)} |")
    lines += ['', 'EMA3 is not hidden by the combined result: at this risk cap it admitted only six historical trades and lost money. Nasdaq Overnight and 0.75R ORB contributed positively. Strict sizing allowed the core trades and news baskets to remain unchanged in this historical sequence; the legacy round-up basket crowded some out.', '',
        '### Monthly closed-trade P&L (continuous account, not payouts)', '',
        '| Month | Trades | Core P&L | Six-EA P&L |', '|---|---:|---:|---:|']
    months=defaultdict(lambda:dict(trades=0,core=0.,six=0.))
    for tag,rr in [('core',x),('six',y)]:
        for t in rr['log']:
            month=t['close'][:7];months[month][tag]+=t['net_profit']
            if tag=='six':months[month]['trades']+=1
    for month,m in sorted(months.items()):lines.append(f"| {month} | {m['trades']} | {money(m['core'])} | {money(m['six'])} |")
    assert abs(sum(m['six'] for m in months.values())-net(six))<1e-7
    lines += ['', 'March starts on March 4; August ends on August 30. P&L uses UTC exit months.', '',
        '## One historical challenge path — strict sizing and stressed costs', '',
        '| Milestone | Core | Six EAs |', '|---|---|---|']
    hc=core['historical_challenge'];hn=six['historical_challenge']
    for p in (1,2):
        xv=next((r['time'] for r in hc['passes'] if r['phase']==p),'Not passed')
        yv=next((r['time'] for r in hn['passes'] if r['phase']==p),'Not passed')
        lines.append(f'| Phase {p} passed | {xv} | {yv} |')
    for k,label in [('funded_at','Funded activation'),('receipt_at','First reward received')]:lines.append(f"| {label} | {hc[k]} | {hn[k]} |")
    lines += [f"| First profit reward | {money(hc['reward'])} | {money(hn['reward'])} |", '',
        'One path only, not an expected payout. Earlier funding changes which trades fall in the funded phase, so earlier first reward can be smaller. Amounts exclude fee refund, tax, FX, VPS and other expenses.', '',
        '## Sensitivity to costs and inherited sizing', '',
        '| Sizing | Costs | Portfolio | Funded 180d | Paid 180d | Historical net P&L | Reserve DD |',
        '|---|---|---|---:|---:|---:|---:|']
    for r in out['cases']:
        h=r['summary']['horizons'][-1];hh=r['historical_continuous']
        lines.append(f"| {'Strict DOWN' if r['sizing']=='strict_round_down' else 'Legacy UP'} | {'Stress' if r['stress'] else 'Reference'} | {r['config']['name']} | {h['funded_pct']:.1f}% | {h['payout_pct']:.1f}% | {money(net(r))} | {hh['model_dd_pct']:.2f}% |")
    lines += ['', 'Legacy UP is retained only to reproduce the preceding reports: it can exceed the nominal risk target. It is not a hard-$71.43-risk recommendation. Compare portfolios within the same sizing and cost row family, not across changed assumptions.', '',
        '## Breaches, internal buffer, and decision', '',
        '| Case | Hard breaches before first reward/180d | Paths touching $9,200 admission buffer | 95th percentile reserve DD |',
        '|---|---:|---:|---:|']
    for r in out['cases']:
        if not r['stress']:continue
        h=r['summary']['horizons'][-1]
        lines.append(f"| {r['sizing']} / {r['config']['name']} | {h['breach_before_first_reward_pct']:.1f}% | {r['summary']['paths_touching_internal_total_buffer']}/1000 | {r['aggregate180']['p95_stop_envelope_dd_pct']:.2f}% |")
    lines += ['', 'Zero simulated breaches is conditional on the admission rules and equity approximation. It does not establish zero live breach risk. Peak-to-trough DD differs from FTMO\'s static initial-balance limit. The $300 gate reserves modeled risk; it is not a guaranteed realized-loss stop, as the legacy daily loss exceeding $300 demonstrates.', '',
        'This six-EA basket is a stronger modeled medium-term candidate with strict sizing, but it does NOT provide a high modeled probability of funding in one month or a payout in two months. It also does not improve historical win rate or longest winning streak. No claim that all three additions are necessary is established: an ablation comparison excluding EMA3 has not been run in this request.', '',
        'Deployment remains separate. Exact News Pulse pre-event two-sided behavior must satisfy FTMO contract/practice rules; Swing news permission alone is not specific approval. Existing production news builds have a different hard-locked risk policy. [FTMO forbidden practices](https://ftmo.com/en/forbidden-trading-practices/).', '',
        '## Verification', '',
        f"Native ORB stop/cost reconstruction verified; all source hashes unchanged. Nine original engine tests, seven adapter checks, eight historical parity fields, eleven phase tests and fourteen strict-sizing checks passed. Verified {validation['horizon_state_reconciliations']} deadline state counts, 8,000 path records, and all eight historical cash ledgers. The legacy core reproduces the prior funded/payout rates at every horizon.", '',
        'Machine-readable evidence: SIX_EA_FROZEN.json, SIX_EA_RESULTS.json, SIX_EA_CHECKS.json. No MT5 trading API was initialized.', '']
    (c.ROOT/'SIX_EA_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('VERIFIED',validation['cases'],'cases;',validation['horizon_state_reconciliations'],'horizons')
    print('STRICT STRESS PAIRED',six['paired180'])
    print('MONTHS',dict(months))

if __name__=='__main__':main()
