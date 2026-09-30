"""Build the user-facing audit from actual saved simulation output."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,numpy as np
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def date(t):return datetime.fromtimestamp(t*60,timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if t>=0 else 'None observed'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def main():
    allrows=read(ROOT/'RESULTS.json');sens=read(ROOT/'SENSITIVITY.json');a=read(ROOT/'recent-AUDIT.json')
    recent=[r for r in allrows if r['period']=='recent-'];ref=[r for r in recent if not r['stress']]
    def get(name,account,stress=False):return next(r['metrics'] for r in recent if r['config']['name']==name and r['account']==account and r['stress']==stress)
    names=list(dict.fromkeys(r['config']['name'] for r in ref))
    lines=['# Daily equity controls — research results, 29 September 2026','',
    '## Bottom line','',
    'For the current 13-EA FTMO basket, **A: 2% daily equity-loss cut + 4% equity-profit goal** had the highest return in the fixed-$50 reference replay, but the improvement was small and did not survive a five-minute closing-delay sensitivity. Its main benefit was lower worst daily loss, not a material improvement in overall drawdown. **B: 2.5% open-risk cap alone is not a daily loss limit.** It slightly reduced return here and is not a substitute for an equity-loss stop.',
    '',
    '**No production settings, running EAs, open trades, MT5 account or crypto-paper bots were changed. This is a source-trade/M1 replay, not a native shared-account or real-tick equity-stop backtest.**',
    '',
    '## Coverage — what is and is not complete','',
    '- Current FTMO13 News-OFF strategy package: 972 source trades; **27 September 2025–24 September 2026**, 363 days. Exact existing package/source receipts rechecked unchanged. Nasdaq is DI14/EMA12, 0.60% price stop, ATR6 trail from +1R, no TP. The requested risk policies replace existing BAT/adaptive guards for comparison.',
    '- Broad installer catalogue: 34 products, but **only 33 have comparable cached ledgers**; Gold News V9 is missing. The common cached year is **31 August 2025–30 August 2026**, not the trailing year through today.',
    '- **31 broad-basket binary hashes differ from current builds**, and XAU Regime Switch has a SET mismatch. Those results are historical diagnostics, not an audit proving current-build performance. The current local connection confirms Exness demo, but not every running chart/VPS EA.',
    '- News Pulse cached parameters were selected on overlapping history. Unfilled pending-side reservations are missing from the broad replay. Treat its unusually high returns as unfit for a deployment decision. Non-news results are separated below.',
    '',
    '## Rules and account assumptions','',
    'One shared $10,000 account; primary comparison uses **fixed $50 planned initial-stop risk**, 0.5% of starting capital. Lots round DOWN; unaffordable or minimum-lot-over-budget entries are rejected. Commission, spread, gaps and slippage can cause losses beyond planned stop risk. Nasdaq is not quarter-sized in this requested comparison.',
    '',
    'A closes the portfolio after net equity (including floating P&L and modeled costs) minus Prague-midnight balance reaches -$200/-$250 or +$400/+$500. It blocks entries until the next Prague day. B instead caps summed original open-stop risk at $250, with NO internal daily loss stop, retaining the same profit close/day lock. Trailing-stop risk relief is not assumed. Profit targets include already closed daily P&L; they are not open-position profit alone.',
    '',
    'The daily thresholds stay fixed to initial capital, including in the equity-sizing sensitivity. They are not 4–5% of a growing balance. FTMO imposes separate $500 daily equity loss and $9,000 static total-equity floor checks, reset at 00:00 CE(S)T. Normal capital has no FTMO disqualification. Both accounts use an 80% equity margin-admission assumption.',
    '',
    'Forced exits are scheduled one minute after observation at the first available minute open; native exits may occur first. Thresholds are triggers, not guaranteed fill prices. No future bar closes are used before bar completion, but the source-total swap timing is approximated across its observed duration. Intraminute paths and signal changes after forced exits are not reproduced.',
    '',
    'Official rules checked: [FTMO trading objectives](https://ftmo.com/en/trading-objectives/), [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/), [public instrument specifications](https://ftmo.com/wp-json/ftmo/symbols). Swing leverage and target commission assumptions differ from Exness; actual FTMO historical quotes, minimum lots and swaps are not verified.',
    '',
    '## Current FTMO13: continuous $10,000 account, fixed $50 risk','',
    'Returns below are account-equity changes, NOT payouts or withdrawable FTMO rewards. DD is peak-to-trough sampled equity drawdown divided by the running equity peak. Daily loss is relative to the initial $10K. No sampled FTMO breach occurred in any fixed-$50 reference or stress row; this is not proof of tick-level compliance.',
    '']
    rows=[]
    for name in names:
        n=get(name,'Normal capital');f=get(name,'FTMO Swing')
        rows.append([name,f"{n['return_pct']:+.2f}%",f"{f['return_pct']:+.2f}%",f"{n['equity_dd_pct']:.2f}% / {f['equity_dd_pct']:.2f}%",f"{f['worst_daily_pct']:.2f}%",int(f['goal_days']),int(f['loss_stop_days'])])
    lines += [table(['Policy','Normal return','FTMO return','DD normal / FTMO','Worst FTMO day loss','Goal triggers','Loss-stop triggers'],rows)]
    n=get(names[1],'Normal capital');f=get(names[1],'FTMO Swing');base=get('Baseline','FTMO Swing')
    lines += [f"A 2%/4% ends at **${n['ending_equity']:,.2f} normal / ${f['ending_equity']:,.2f} FTMO**. Compared with baseline its FTMO gain improves by ${(f['return_pct']-base['return_pct'])*100:,.2f}, while worst daily loss falls from {base['worst_daily_pct']:.2f}% to {f['worst_daily_pct']:.2f}%. Its overall peak drawdown is slightly higher, not lower.", '',
    f"Only five 4% goal triggers occurred in 363 calendar days; the 5% target triggered zero times in this basket at fixed $50 sizing. The 2%/4% policy forced {int(f['forced_closes'])} positions out and skipped {int(f['blocked_day'])} later signals on locked days. The largest loss-close underfill was ${f['max_loss_overshoot']:.2f} beyond its trigger; the largest profit-close shortfall was ${f['max_goal_underfill']:.2f}. Thus even the sampled model does not deliver exact 2% caps or 4% banked wins.", '',
    '### Costs and execution sensitivity','']
    rows=[]
    for name in names:
        n=get(name,'Normal capital',True);f=get(name,'FTMO Swing',True)
        delay=next(r['metrics'] for r in sens if r['kind']=='five-minute-close' and r['account']=='FTMO Swing' and r['config']['name']==name)
        rows.append([name,f"{n['return_pct']:+.2f}%",f"{f['return_pct']:+.2f}%",f"{f['equity_dd_pct']:.2f}%",f"{delay['return_pct']:+.2f}%"])
    lines += [table(['Policy','Normal stressed return','FTMO stressed return','FTMO stress DD','FTMO 5-min close return'],rows),
    'Stress is a hypothetical additional adverse fill plus doubled negative swaps, NOT a measured execution distribution or worst-case loss. The 5-minute column uses reference costs. A 2%/4% loses its slight profit advantage when liquidation is delayed. There is no robust statistical winner between 4% and 5% profit targets.', '',
    '### If 0.5% means current equity instead of fixed $50','',
    'Trade risk increases as equity grows; daily targets/loss budgets remain $400/$500 and $200/$250. This is a separate sizing policy, not an interchangeable interpretation of the table above. A stopped FTMO return is truncated at its first sampled breach.', '']
    rows=[]
    for r in sens:
        if r['kind']!='equity-sizing' or r['account']!='FTMO Swing':continue
        m=r['metrics'];normal=next(x['metrics'] for x in sens if x['kind']=='equity-sizing' and x['account']=='Normal capital' and x['config']['name']==r['config']['name'])
        rows.append([r['config']['name'],f"{normal['return_pct']:+.2f}%",f"{m['return_pct']:+.2f}%",f"{m['equity_dd_pct']:.2f}%",f"{m['worst_daily_pct']:.2f}%",date(m['first_ftmo_breach_minute'])])
    lines += [table(['Policy','Normal return','FTMO return to end/breach','FTMO DD','Worst daily loss','First FTMO breach'],rows),
    'The compounding baseline breaches the $500 FTMO daily-loss floor on 1 September 2026 despite substantial prior profits. B keeps open commitments below $250 but still experiences roughly 4.5% daily losses as risk capacity is reused after exits. A also overshoots its chosen internal cap due to observation/fill delay; it is not insurance against gaps.', '',
    '### Single historical two-phase path','',
    'All seven fixed-$50 policies reached the same modeled milestones on this one start: Challenge flat above +10% on **27 October 2025**, Verification flat above +5% on **21 November 2025**, with at least four opening days per phase. The model resets balance and restarts on the next weekday, ignoring actual review delays. This does not establish a pass probability, payout eligibility, payment or a promise that a new challenge would pass.', '',
    '## Broad historical basket: NOT current-build validated','',
    'Do not rank these figures against the newer FTMO13 table as if dates and evidence quality were equal. The news-inclusive basket is shown only for completeness and is not suitable for estimating future profit.', '']
    for group,title in [('NonNews29','29 non-news catalogue EAs'),('Broad33','33 cached catalogue EAs, news included; Gold News V9 excluded')]:
        lines += ['### '+title,'']
        rows=[]
        for name in names:
            nr=next(r for r in allrows if r['group']==group and not r['stress'] and r['account']=='Normal capital' and r['config']['name']==name)
            fr=next(r for r in allrows if r['group']==group and not r['stress'] and r['account']=='FTMO Swing' and r['config']['name']==name)
            n=nr['metrics'];f=fr['metrics']
            rows.append([name,f"{n['return_pct']:+.2f}%",f"{f['return_pct']:+.2f}%",f"{n['equity_dd_pct']:.2f}% / {f['equity_dd_pct']:.2f}%",int(f['goal_days']),f"{f['worst_daily_pct']:.2f}%"])
        lines += [table(['Policy','Normal return','FTMO-overlay return','DD normal / FTMO','FTMO goal triggers','FTMO worst daily loss'],rows)]
    lines += ['The older basket’s daily profit caps cut off profitable trend/news excursions and reduce its reported return. The large news contribution is dominated by fitted historical outcomes and incomplete pending-order modeling. It must not be used to justify purchasing an FTMO account or deploying the entire catalogue. Every cost case, including unattractive outcomes, is retained in RESULTS.json.', '',
    '## Monthly and EA detail — current FTMO13, A 2%/4%','']
    z=np.load(ROOT/'recent-FTMO13-1-0-A_loss2_goal4.npz');monthly=defaultdict(lambda:[0,0.]);eas=defaultdict(lambda:[0,0.])
    for row in z['logs']:
        t=z['trades'][int(row[0])];key=a['keys'][int(t[2])];month=datetime.fromtimestamp(row[2]*60,timezone.utc).strftime('%Y-%m')
        monthly[month][0]+=1;monthly[month][1]+=row[4];eas[key][0]+=1;eas[key][1]+=row[4]
    lines += [table(['Exit month UTC','Closed positions','Net USD'],[[k,v[0],f'${v[1]:,.2f}'] for k,v in sorted(monthly.items())]),
    'September endpoints are partial months. Attribution is closed-position net P&L, not a payout schedule.', '',
    table(['EA','Closed positions','Net USD'],[[k,v[0],f'${v[1]:,.2f}'] for k,v in sorted(eas.items(),key=lambda x:-x[1][1])]),
    '## Checks and next decision','',
    '- 112 continuous-account cases plus 35 sensitivity/stage cases generated. 16 targeted accounting, floating-equity, midnight/DST, margin, sizing and liquidation tests passed. Saved-case accounting and risk checks passed for all 112 primary cases.',
    '- All 972 current FTMO13 source entry/exit quotes were compared with matching M1 envelopes: none exceeded the envelope by more than 0.25 initial R; maximum deviation was about 0.107R. This is a reconciliation check, not tick-path validation.',
    '- Original source entry schedules remain fixed; after a forced close an EA might reenter, and after a skipped trade it might generate different later signals. That requires a native multi-EA rerun to validate.',
    '- Current FTMO13 retains prior strategy-selection bias. One historical year and small policy differences are not evidence of a durable edge.',
    '- For a forward demo test, the **daily marked-equity loss cut is the useful safety feature**. Do not replace it with open-risk admission alone. Treat the 4–5% goal as an occasional lock-in trigger, not expected daily earnings. Do not promote a new live policy from this audit.',
    '- To finish a true full-current-EA audit: freeze the actual running EA/SET roster, archive/replay Gold News V9 predictions, regenerate current-build ledgers through the same end date, reserve all pending orders, and run coordinated tick-level forced-close/reentry tests with verified target-broker specifications.',
    '',
    'Reproduction: inventory.py, collect.py (read-only price/spec access), prepare.py and prepare.py --recent, simulate.py, sensitivity.py, verify.py, and test_simulate.py. See PROTOCOL.md and AMENDMENTS.md for complete assumptions. No changes were made outside this new research directory.', '']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('REPORT.md created',len(lines),'sections/paragraphs')
if __name__=='__main__':main()
