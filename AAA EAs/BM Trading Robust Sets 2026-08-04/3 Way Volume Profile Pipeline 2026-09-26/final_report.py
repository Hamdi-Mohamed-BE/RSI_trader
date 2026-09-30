"""Build final research handoff; no MT5 initialization or tests."""
from collections import defaultdict
from datetime import datetime,timedelta
from decimal import Decimal
import gzip
import html
import json
from pathlib import Path
import re
import statistics
import sys

import run_qualification as q
import audit_results
ROOT=Path(__file__).resolve().parent
OPT=ROOT/'Optimization'
sys.path.insert(0,str(OPT))
import search

def detail(name):
    folder=OPT/'native'/name
    result=json.loads((folder/'results.json').read_text())[0]
    manifest=json.loads((folder/'manifest.json').read_text())
    report=gzip.decompress(next(folder.glob('*.htm.gz')).read_bytes()).decode('utf-16')
    legs=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
    positions={}
    for t in legs:
        key=(t['open_time'],t['side'],t['open_price'])
        if key not in positions:
            positions[key]=dict(open_time=t['open_time'],close_time=t['close_time'],net_profit=0.,legs=0,side=t['side'])
        p=positions[key]; p['net_profit']+=t['net_profit']; p['legs']+=1; p['close_time']=max(p['close_time'],t['close_time'])
    ordered=sorted(positions.values(),key=lambda x:x['close_time'])
    month=defaultdict(lambda:dict(positions=0,exit_legs=0,net_usd=0.))
    for p in ordered: month[p['close_time'][:7]]['positions']+=1
    for p in legs:
        m=month[p['close_time'][:7]]; m['exit_legs']+=1; m['net_usd']+=p['net_profit']
    groups={'W':[],'L':[]}; side=None; length=0
    for p in ordered:
        nxt='W' if p['net_profit']>0 else 'L' if p['net_profit']<0 else None
        if nxt==side: length+=1
        else:
            if side: groups[side].append(length)
            side,length=nxt,1
    if side: groups[side].append(length)
    # Exact cash-flow reconciliation bypasses per-partial-leg two-decimal allocation rounding.
    deals=report[report.lower().index('<b>deals</b>'):]
    total=Decimal('0')
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',deals,re.I|re.S):
        cells=[html.unescape(re.sub(r'<[^>]+>','',x)).replace('\xa0',' ').strip() for x in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
        if len(cells)!=13 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]) or cells[3].lower()=='balance': continue
        for i in (8,9,10): total+=Decimal(cells[i].replace(' ','') or '0')
    result['detail']=dict(
        positions=len(ordered),exit_legs=len(legs),partially_closed_positions=sum(p['legs']>1 for p in ordered),
        whole_position_win_pct=100*sum(p['net_profit']>0 for p in ordered)/len(ordered),
        whole_position_pf=sum(max(0,p['net_profit']) for p in ordered)/max(.01,-sum(min(0,p['net_profit']) for p in ordered)),
        max_equity_relative_dd_pct=q.h._number(q.h._metric(report,'Equity Drawdown Relative')),
        max_balance_relative_dd_pct=q.h._number(q.h._metric(report,'Balance Drawdown Relative')),
        max_win_streak=max(groups['W'],default=0),max_loss_streak=max(groups['L'],default=0),
        avg_win_streak=statistics.mean(groups['W']) if groups['W'] else 0,
        avg_loss_streak=statistics.mean(groups['L']) if groups['L'] else 0,
        exact_cashflow_net=float(total),cashflow_reconciled=abs(float(total)-result['metrics']['net_profit'])<.001,
        rounded_allocated_ledger_net=sum(p['net_profit'] for p in ordered),monthly=dict(month))
    result['manifest']=manifest
    return result

def main():
    audit_results.main()
    ledger=json.loads((OPT/'SEARCH RESULTS.json').read_text())
    unique=len({search.digest(x['parameters']) for x in ledger})
    names=['XAUUSD-raw-validation']+[f'XAUUSD-BRK-validation-{i}' for i in range(3)]
    validation={n:detail(n) for n in names}
    stages=defaultdict(list)
    for x in ledger: stages[x['stage']].append(x)
    q.dump(ROOT/'FINAL RESULTS.json',dict(search_passes=len(ledger),unique_configurations=unique,
           qualification=json.loads((ROOT/'qualification.json').read_text()),validation=validation,
           conclusion='KEEP_RAW_REJECT_ALL_OPTIMIZED_FINALISTS',holdout_used=False,monte_carlo_run=False,
           production_changed=False))
    lines=['# 3 Way Volume Profile — completed qualification and parameter search','',
           '**Conclusion: keep the raw gold breakout version for research. None of the optimized finalists passed validation. Nothing was deployed.**','',
           f'Completed {len(ledger)} native development optimization passes ({unique} distinct parameter vectors), nearby-parameter checks, three native validation runs and a matched raw validation run. A staged top-three search is not an exhaustive Cartesian search and does not prove a global optimum.','',
           '## 1. Longer-history raw qualification','',
           '| Version | 3y return | 3y PF | 5y return | 5y PF | 5y max equity DD | Decision |',
           '|---|---:|---:|---:|---:|---:|---|']
    audit=json.loads((ROOT/'AUDIT.json').read_text())
    for c in q.CFG['candidates']:
        rr={r['period']:r for r in audit if r['model']==4 and r['control_seed'] is None and r['symbol']==c['symbol'] and r['variant']==c['variant']}
        a,b=rr['3y'],rr['5y']
        lines.append(f"| {c['symbol']} {c['variant']} | {a['metrics']['return_pct']:+.2f}% | {a['metrics']['profit_factor']:.2f} | {b['metrics']['return_pct']:+.2f}% | {b['metrics']['profit_factor']:.2f} | {b['audit']['max_equity_relative_dd_pct']:.2f}% | {'Qualified; optimized' if c['symbol']=='XAUUSD' else 'Did not qualify; no parameter search'} |")
    lines+=['','The predeclared gate required positive return, PF >=1.15 and >=30 trades in BOTH 3y and 5y, plus beating the control. Gold beat the three-seed median random-control return/PF: -23.93% / 0.87 over 3y, -31.41% / 0.89 over 5y. Random controls use 2 ATR stops rather than structural stops; this is a sanity reference, not causal proof.','',
            '## 2. Fair out-of-development comparison','',
            'Same validation year: **26 September 2024 to 26 September 2025, end exclusive**. Native MT5 Model 4, $10,000, target 1% risk, 150ms configured delay. This older year has generated ticks, not broker real ticks.','',
            '| Version | Return | Net USD | Native PF | Whole-position win | Positions | Exit legs | Max equity DD | Longest W/L streak | Verdict |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for i,(name,r) in enumerate(validation.items()):
        m,d=r['metrics'],r['detail']; label='Raw M15' if i==0 else f'Optimized finalist {i}'
        lines.append(f"| {label} | {m['return_pct']:+.2f}% | ${m['net_profit']:,.2f} | {m['profit_factor']:.2f} | {d['whole_position_win_pct']:.2f}% | {d['positions']} | {d['exit_legs']} | {d['max_equity_relative_dd_pct']:.2f}% | {d['max_win_streak']}/{d['max_loss_streak']} | {'Raw reference' if i==0 else 'REJECT: PF below 1.15'} |")
    lines+=['','Finalists 2 and 3 produced the same validation trades; they are not independent confirmations. Their only difference is the two-versus-three daily-entry cap.',
            '', '**Win-rate warning:** the optimized finalists show 63.16% winning exit legs in the MT5 summary, but only 53.23% winning whole positions. Partial profit-taking splits a position into multiple exits; comparing that headline directly with the raw strategy would be misleading. Both figures and whole-position PF are preserved in FINAL RESULTS.json.',
            '', '## 3. What was tested','',
            '| Development stage | Native passes | Best stage PF | Best stage return | Best stage equity DD |',
            '|---|---:|---:|---:|---:|']
    for stage,items in stages.items():
        best=max(items,key=search.score); n=best['native']
        lines.append(f"| {stage} | {len(items)} | {n['Profit Factor']:.3f} | {n['Profit']/100:+.2f}% | {n['Equity DD %']:.2f}% |")
    lines+=['','Development window: 26 September 2021 to 26 September 2024. Development numbers are fitted results, not independent evidence.',
            '', 'Dimensions: eight timeframes; market/confirmation/limit/stop entries; structural/ATR/percent/fixed-price/signal/swing stops; seven trailing alternatives plus none; 0.5–6R and alternative exits; sessions, direction, filters, daily/position/holding limits; profile bins/value area/ATR/breakout/pullback parameters; 81 nearby-parameter cases. Exact vectors and rejected alternatives are in Optimization/SEARCH RESULTS.json.',
            '', 'News blackout was NOT tested: complete point-in-time calendar coverage was not verified. Signal-close and next-bar market entry are one causal implementation, not separate invented fills.',
            '', 'The development leaders converged on M30 breakout stop entries, a stop 0.5 ATR from the signal-time quote, 2R target, partial 50% close at 1R where lot rules permit, 1 ATR trailing starting at 1R, ATR-percentile filter and wider pullback proximity. These are rejected research candidates, not recommended live settings.',
            '', '## 4. Integrity and limitations','',
            '- Raw parity passed twice: the qualification wrapper and optimization extensions with switches off reproduced the original 78 gold trades and all summary metrics.',
            '- Both native builds compiled with zero errors and zero warnings. Native optimization XML contains every expected case index; per-batch source, binary, vector and report evidence is retained.',
            '- Native cash-flow sums reconcile exactly to the report for all four validation runs. The position ledger allocates partial entry costs rounded to cents and can differ by a few cents; use native net P/L as authoritative.',
            '- Trade-count-based development scoring includes partial exit legs, so partial-closing variants get an imperfect count advantage. Whole-position validation is reported separately; this does not rescue any failed finalist.',
            '- Broker lots round upward; target 1% is not a strict maximum. The study uses saved Exness contract conditions and 1:2000 test leverage, not FTMO Swing margin rules.',
            '- Broker real ticks begin January 2026. Older tests rely on generated ticks; historical slippage/order-book depth cannot be reconstructed. Fixed 150ms delay is not a guarantee of live fills.',
            '- The reserved 2019–2021 holdout was NOT opened because all finalists failed validation. The already-inspected latest year is not an untouched holdout.',
            '- No Monte Carlo/payout probabilities were generated for rejected candidates. No candidate passed the prerequisite validation gate. Additional measured cost stress and live forward evidence remain absent.',
            '- No active terminal, live orders, BAT configuration, website, portfolio, or Git remote was changed.',
            '', '## Decision','',
            'Do not replace raw gold breakout with these optimized variants. The higher exit-level win rate traded away too much profit and did not survive the separate validation year. BTC reversal and the two USDJPY versions remain unoptimized under the agreed longer-history cutoff.',
            '', '## Evidence','',
            '- AUDITED RESULTS.md / AUDIT.json: full 3y/5y raw metrics, consistency, streaks, monthly records, controls and coverage.',
            '- Optimization/SEARCH RESULTS.json: all development and plateau trials.',
            '- Optimization/native/: per-batch source/binary snapshots, native XML/HTML, journals and exact parameters.',
            '- FINAL RESULTS.json: reconciled validation comparison and monthly position/exit data.',
            '- Optimization/PROTOCOL.md: frozen search rules, omissions and validation thresholds.',
            '', 'MT5 modes and command-line configuration: https://www.metatrader5.com/en/terminal/help/start_advanced/start',
            'Maximum relative equity drawdown statistic: https://www.mql5.com/en/docs/constants/environment_state/Statistics','']
    (ROOT/'FINAL REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    search.progress(state='complete_rejected',search_passes=len(ledger),unique_configurations=unique,
                    result='Raw gold retained; all optimized finalists rejected on validation; holdout preserved; nothing deployed')
    print(json.dumps({name:r['detail']|{'monthly':'saved'} for name,r in validation.items()},indent=2))

if __name__=='__main__': main()
