from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json

ROOT=Path(__file__).resolve().parent
j=json.loads((ROOT/'RESULTS.json').read_text())
checks=json.loads((ROOT/'CHECKS.json').read_text())
names={'Prior benchmark':'0.5% / -2% / +4%', 'Requested':'1.5% / -5% / +8%',
       'Requested with buffer':'1.5% / -4% / +8%', 'Middle-risk diagnostic':'1.0% / -3% / +8%',
       'Requested equity-sized':'1.5% current equity / -5% / +8%'}
def date(t):return datetime.fromtimestamp(t*60,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
def med(x):return f"{x['median']:.0f}" if x else '—'
def money(x):return f'${x:,.0f}'
def frac(n,d):return f'{n}/{d} ({100*n/d:.1f}%)'

lines=['# FTMO 2-Step Swing: 1.5% risk with -5%/+8% daily controls',
       '', '## Decision', '',
       '**Do not promote the requested settings for a durable FTMO account.** They accelerated phase completion among successful starts, but every complete six-month historical scenario eventually breached an FTMO limit. A 4% internal loss buffer reduced daily-limit failures but did not fix total-loss failures. The tested 1% alternative also increased failures. Retain the 0.5%/-2%/+4% research benchmark for forward validation; it is not proven safe or profitable in future trading.', '',
       'Research as of 29 September 2026. Current saved 13-EA package, News OFF, initial $10,000; 972 source signals; 27 September 2025–25 September 2026 (363 days). This identifies the saved package, not every EA actually attached to the active terminal. No live account, order, EA, SET file or deployment was changed.', '',
       '## Six-month lifecycle comparison — reference costs', '',
       '26 weekly starts have a full 180 days of observation (29 September 2025–23 March 2026). These windows overlap heavily. They are historical scenarios, not 26 independent experiments or estimates of future pass/payout probabilities. Times are calendar days from starting phase 1, conditional on completing the milestone. Payout means eligibility/request in this model, not approved or received cash.', '',
       '| Risk / daily stop / daily profit close | Passed both phases | Median days to pass both | First payout request | Median days to first request | Any breach by day 180 | Payout and still valid at day 180 |',
       '|---|---:|---:|---:|---:|---:|---:|']
reference=[x for x in j['scenarios'] if x['case']['name']=='Reference']
for x in reference:
    s=x['summary'][-1];n=s['starts'];c=s['counts'];t=s['timing_days']
    lines.append(f"| {names[x['config']['name']]} | {frac(c['phase2'],n)} | {med(t['phase2'])} | {frac(c['reward'],n)} | {med(t['first_reward'])} | {frac(c['breach'],n)} | {frac(c['reward_and_no_breach'],n)} |")
lines+=['', 'The requested fixed-$150 policy passed both phases in a median 25 days among the 22 successful starts, versus 73 days for the benchmark. First requests were earlier (51 versus 95 days among paths reaching them). However, 12/26 requested-policy starts failed before any reward; all 14 that requested a reward also failed later within their 180-day window.', '',
        'The 1%/-3%/+8% diagnostic had 10/26 failures at reference costs, all involving the overall loss floor, despite the tighter daily close. It is faster but not an equivalently safe substitute.', '',
        '## Dollar reward tradeoff — all 26 starts, including zeros', '',
        'Mean cumulative modeled trader share over 180 days. Assumes 80% share and full withdrawals; excludes challenge purchases, retries, refunds, taxes and payment/approval risk. Larger early rewards can coexist with subsequent account failure. These are not recurring monthly-income estimates.', '',
        '| Policy | Reference | Higher costs | Higher costs + 10% weaker outcomes | 5-minute liquidation |',
        '|---|---:|---:|---:|---:|']
for x in reference:
    same=[p for p in j['scenarios'] if p['config']['name']==x['config']['name']]
    amounts=[money(p['summary'][-1]['total_trader_share_all_starts_usd']['mean']) for p in same]
    lines.append('| '+names[x['config']['name']]+' | '+' | '.join(amounts)+' |')
lines+=['', 'The requested settings produced a higher reference-case mean share ($1,605 versus $1,367), but that advantage disappeared under higher costs ($1,075 versus $1,127), and all requested-policy accounts failed in both cases. Replacing failed accounts is not modeled. The larger number alone does not establish a better sustainable FTMO policy.', '',
        '## Stress tests — same complete six-month cohort', '',
        '| Policy | Cost/execution case | Both phases passed | Any payout request | Any breach | Payout and still valid |',
        '|---|---|---:|---:|---:|---:|']
for x in j['scenarios']:
    s=x['summary'][-1];n=s['starts'];c=s['counts']
    lines.append(f"| {names[x['config']['name']]} | {x['case']['name']} | {c['phase2']}/{n} | {c['reward']}/{n} | {c['breach']}/{n} | {c['reward_and_no_breach']}/{n} |")
lines+=['', 'The 0.5% benchmark was also fragile in terms of earnings: only 14/26 starts requested a reward under the higher-cost/weaker-edge case, although no minute-observed FTMO breaches occurred. A historical no-breach result is not a future guarantee.', '',
        '## Continuous account from 27 September 2025 — no evaluation resets or withdrawals', '',
        'A different experiment from the lifecycle above. Stop the account immediately at a sampled FTMO breach. Do not interpret pre-failure profit as a surviving full-year return. Different failure dates mean the trade statistics below are not equal-duration comparisons. The continuous account retains profits as a buffer against the static overall loss floor; the funded-cycle model withdraws them and returns to $10,000. Phase timing also changes which trades are admitted. Thus a continuous full-year survivor can still fail in some phase/payout-start scenarios.', '',
        '| Policy | Account outcome | Marked equity peak-to-trough DD | Worst daily equity loss | Highest concurrent initial-stop risk | Most simultaneous trades |',
        '|---|---|---:|---:|---:|---:|']
for x in j['continuous']:
    if x['case']['name']!='Reference':continue
    m=x['metrics'];b=m['first_ftmo_breach_minute']
    status=('Failed '+date(b)) if b>=0 else f"Completed; {m['return_pct']:+.2f}% marked equity"
    lines.append(f"| {names[x['config']['name']]} | {status} | {m['equity_dd_pct']:.2f}% | {m['worst_daily_pct']:.2f}% | {m['max_open_risk']/100:.2f}% | {m['max_concurrent']:.0f} |")
lines+=['', 'At requested fixed sizing, the first continuous-account failure was 10 December 2025 at 19:37 UTC, with a 5.28% daily equity loss. The 5% internal stop never safely liquidated first: observed equity had already crossed the FTMO boundary. Sizing each trade at 1.5% of current equity failed earlier, 4 November 2025.', '',
        'At fixed $150, initial committed stop exposure reached about $950 across seven concurrent trades before that first continuous failure. A daily loss-close does not prevent opening too much correlated exposure. The primary experiment intentionally did not add an unrequested aggregate-risk cap.', '',
        'A risk increase also changes which signals are tradable: wider-stop trades previously below minimum lot size can enter, while larger margin needs reject other trades. This is not a simple tripling of the old equity curve.', '',
        '## Why a 5% internal stop is unsuitable here', '',
        'FTMO 2-Step measures a 5% initial-capital daily loss allowance against the balance recorded at midnight CE(S)T, using equity including open P/L, swaps and commissions. The overall limit is 10% of initial capital. Therefore a $500 internal loss trigger on $10,000 sits on the daily failure boundary, not below it. A quote jump or closing delay can breach first. [Official FTMO trading objectives](https://ftmo.com/en/trading-objectives/).', '',
        'Four $150 initial-stop losses total $600 before costs. Several EAs can expose the portfolio to the same market movement. The +8% setting is only an occasional take-profit trigger, not expected daily growth, and does not compensate for a loss-limit breach.', '',
        '## Failure concentration — reference lifecycle', '',
        'Counts below are complete 180-day starts, not independent market events. A few bad dates recur in many overlapping starts.', '',
        '| Policy | Failure-date counts (UTC) | Boundary crossed at failure |',
        '|---|---|---|']
for x in reference:
    pp=[p for p in x['paths'] if p['end']-p['start']>=180*1440 and p['breach'] is not None]
    dates=Counter(date(p['breach'])[:10] for p in pp)
    causes=Counter(('daily + total' if p['stages'][-1]['metrics']['ending_equity']<9000-1e-8 else 'daily') if p['stages'][-1]['metrics']['worst_daily_pct']>5.00000001 else 'total' for p in pp)
    lines.append('| '+names[x['config']['name']]+' | '+(', '.join(f'{k}: {v}' for k,v in sorted(dates.items())) or 'None')+' | '+(', '.join(f'{k}: {v}' for k,v in causes.items()) or 'None')+' |')
lines+=['', '## Assumptions and limits', '',
        '- Most headline comparisons use fixed $50/$100/$150, i.e. percent of initial capital, not compounding. The explicitly labeled equity-sized sensitivity uses 1.5% of current equity. Daily and FTMO loss amounts stay anchored to initial capital.',
        '- Controls replace the original package governors rather than stacking with them. Native EA entry/exit schedules are reused; entries are not regenerated after skipped trades or forced exits. Actual EA re-entry behavior can differ.',
        '- Prices are archived source-broker minute data, translated using the prior public FTMO Swing contract, commission, minimum-size and leverage assumptions. This is not a native FTMO real-tick portfolio backtest. Original total-trade swaps are apportioned approximately for early closes.',
        '- Minute observations cannot certify tick-level compliance. Separate adverse-bar flags are retained in raw results and may reflect nonsimultaneous per-symbol extremes. Real execution could fail earlier.',
        '- Full source ledgers and strategy choices contain selection bias; this is not an untouched out-of-sample year. More capital risk does not validate the underlying edge.',
        '- Phase targets are +10% and +5%, flat, with four opening-trade days per phase. Assume two weekdays between phases and five before funding; holidays, KYC and actual service delays are not modeled.',
        '- Rewards require at least 14 calendar days from first funded entry, flat positions and at least $50 profit in this simulation. Withdraw all profit at 80% share, restart at $10,000 after an assumed two-weekday gap. Eligibility/request is not cash receipt. [Official FTMO reward FAQ](https://ftmo.com/faq/how-do-i-withdraw-my-profits/).',
        '- The constant-risk approach may admit few wide-stop trades at $50, so the basket composition changes at larger sizes. Source signal order, lot rounding and margin checks are preserved across policies.',
        '', '## Verification', '',
        f"- 20 continuous cases, {checks['paths']} weekly-start lifecycle paths, {checks['stages']} stage simulations and {checks['reward_requests']} modeled reward requests checked.",
        '- 39 synthetic test executions passed: original controls plus seven targeted risk/boundary cases (inherited original tests are repeated; these are not 39 unique scenarios).',
        '- Copied-engine defaults exactly matched every returned original-engine metric, trade log, daily record and equity-curve element for the benchmark. The saved baseline and all four prior baseline lifecycle cases reproduced exactly.',
        f"- Flat-stage cash reconciliation maximum error: {checks['accounting_max_error']:.3g} USD; fixed risk budgets, stage sequencing, minimum days and reward timing asserted.",
        '- Archived inputs and earlier audit files stayed unchanged, verified by SHA-256. No market orders, MT5 changes or external account writes.',
        '', 'Reproduction: study.py, test_risk.py, report.py. Inputs/hashes: SOURCE_AUDIT.json. Raw cases: RESULTS.json. Checks: CHECKS.json. Frozen scope: PROTOCOL.md.', '']
(ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('REPORT.md created with',len(lines),'lines.')
