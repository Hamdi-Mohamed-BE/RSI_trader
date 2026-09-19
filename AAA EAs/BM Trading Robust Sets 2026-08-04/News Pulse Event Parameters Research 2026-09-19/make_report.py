import json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(name,file='stats.json'):return json.loads((ROOT/'native'/name/file).read_text())
names=['NativeBaseline','NativeFullBestV2','NativeTrainSelectedV2','NativeBaselineHoldout','NativeTrainHoldoutV2','NativeBaselineDelay250','NativeFullBestDelay250V2']
stats={n:read(n) for n in names}
chosen=json.loads((ROOT/'selected.json').read_text())
screen=json.loads((ROOT/'screening-comparison.json').read_text())
lines=['# News Pulse XAU — event-family parameter research',
'','Research period: 2025-09-19 inclusive to 2026-09-19 exclusive. USD 10,000 starting balance. Native MT5 Model 4, Exness-MT5Trial16 XAUUSD, leverage 1:2000. Not an FTMO simulation.',
'','## Decision',
'','Do not replace the installed preset based on the full-year fitted result. Chronological validation and execution sensitivity must drive the decision, not the maximum hindsight return. Both pending directions remain eligible; no OCO cancellation was introduced. No production EA, BAT, website or live account settings changed.',
'','## Baseline identity',
'','Local installer set: `12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set`. Lead 30 seconds; current Ask/Bid anchors; $6 price offset; $6 stop; no TP; trail starts 1.5R with $15 distance; close at event +60 seconds. Source defaults differ from this saved set. The comparison is against this verified local installer, not an unverified newer deployment.',
'','Risk is 0.75% equity per pending side, with source lot-round-up/minimum-lot behavior. Both sides can fill. Commission and gaps can make realized risk exceed the nominal 1.5% combined budget. Risk percentage was not optimized.',
'','## Native MT5 results',
'','| Run | Return | Final USD | Net PF | Net win rate | Trades | Max equity DD | Commission | Swap |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|']
labels=['Current, full year','Full-year fitted combination','Earlier-period-selected combination, full year','Current, later-period validation','Earlier-selected, later-period validation','Current, native 250ms','Full-year fitted, native 250ms']
for n,label in zip(names,labels):
 s=stats[n];lines.append(f"| {label} | {s['return_pct']:+.2f}% | ${s['final_balance']:,.2f} | {s['profit_factor']:.2f} | {s['win_rate_pct']:.2f}% | {s['trades']} | {s['max_drawdown_pct']:.2f}% | ${s['commission']:,.2f} | ${s['swap']:,.2f} |")
lines+=['','Full-year results contain 71% real ticks; MT5 generated the remainder. Later-period validation (2026-05-19 to 2026-09-19 exclusive) reports 100% real ticks and restarts each alternative with $10,000. It is one chronological split, not an unbiased repeated walk-forward or a live passing probability. The full-year fitted combination uses the validation releases in its selection and is NOT out of sample.',
'','## Parameters by event family',
'','Price distances are XAUUSD price dollars per ounce, NOT cash risk. The prior closed M1 high is adjusted by current spread for buy-stop anchoring; the low anchors the sell stop. These are separate rules per NFP/CPI/FOMC family, not per historical release date.',
'','| Selection | Event | Before release | Anchor | Entry offset | SL | TP | Trailing | Close after release |',
'|---|---|---:|---|---:|---:|---|---|---:|']
for mode in ['full','train']:
 for kind in ['NFP','CPI','FOMC']:
  p=chosen[kind][mode]['params'];anchor=['Current quote','Active M1 high/low','Previous closed M1 high/low'][int(p[1])]
  tp='None' if not p[4] else f'{p[4]:g}R';trail='Off' if not p[5] else f'Start {p[5]:g}R; distance ${p[6]:g}'
  lines.append(f'| {mode} | {kind} | {p[0]:g}s | {anchor} | ${p[2]:g} | ${p[3]:g} | {tp} | {trail} | {p[7]:g}s |')
lines+=['','## Event-family contributions in the combined account',
'','These cash contributions use each combined account’s changing equity. They are not independent standalone strategy returns.',
'','| Event | Current trades | Current net USD | Fitted trades | Fitted net USD | Fitted net win rate |',
'|---|---:|---:|---:|---:|---:|']
trades={n:read(n,'trades.json') for n in ['NativeBaseline','NativeFullBestV2']}
family={}
for k in ['NFP','CPI','FOMC']:
 a=[t for t in trades['NativeBaseline'] if '|'+k+'|' in t['entry_comment']]
 b=[t for t in trades['NativeFullBestV2'] if '|'+k+'|' in t['entry_comment']]
 row=dict(current_trades=len(a),current_net=sum(t['net_profit'] for t in a),fitted_trades=len(b),fitted_net=sum(t['net_profit'] for t in b),fitted_win_rate=100*sum(t['net_profit']>0 for t in b)/len(b))
 family[k]=row
 lines.append(f"| {k} | {len(a)} | ${row['current_net']:,.2f} | {len(b)} | ${row['fitted_net']:,.2f} | {row['fitted_win_rate']:.2f}% |")
lines+=['','## Monthly realized breakdown',
'','| Month | Current trades | Current net USD | Fitted trades | Fitted net USD |',
'|---|---:|---:|---:|---:|']
months=sorted(set(t['close_time'][:7] for ts in trades.values() for t in ts))
for m in months:
 a=[t for t in trades['NativeBaseline'] if t['close_time'].startswith(m)];b=[t for t in trades['NativeFullBestV2'] if t['close_time'].startswith(m)]
 lines.append(f"| {m} | {len(a)} | ${sum(t['net_profit'] for t in a):,.2f} | {len(b)} | ${sum(t['net_profit'] for t in b):,.2f} |")
lines+=['','## Screening stress — not native tester results',
'','Historical bid/ask spread was used. Moderate stress adds $0.25 spread, $0.25 adverse entry/stop/market-exit fills, and 100ms placement delay. Severe adds $0.50 spread, $0.75 adverse fills, and 250ms placement delay. TP fills remain at target. This is a simplified sensitivity model, not a complete live latency/queue/liquidity simulation.',
'','| Modelled scenario | Current return | Fitted return | Fitted estimated DD |',
'|---|---:|---:|---:|']
for label in ['stress','severe']:
 a=screen['baseline'][label];b=screen['full'][label]
 lines.append(f"| {label} | {a['return_pct']:+.2f}% | {b['return_pct']:+.2f}% | {b['dd']:.2f}% |")
lines+=['','Native 250ms execution delay produced a different trade path and can increase, not merely reduce, backtest profit. This is sensitivity evidence, not proof that slower execution improves the strategy. Do not interpret the 1ms run as realistic guaranteed news execution.',
'','## Coverage and checks',
'','- 30 scheduled releases: 11 NFP, 11 CPI, 8 FOMC. The 2026-04-03 NFP has no executable gold quotes; zero trades are retained rather than fabricated.',
'- Official BLS/Fed calendar receipt archive extended with FXMacroData records. Connector receipts do not establish point-in-time historical-vintage safety; this limitation is preserved in the saved data.',
'- Final bounded search: 5,066 configurations per event family; lead 5–120s, three anchors, offset $1–20, SL $2–20, TP disabled or 0.5–8R in 0.5R steps, trailing on/off, close 60–600s. Not an exhaustive global optimum.',
'- Selection ranks return minus twice estimated equity DD; the top 100 first-pass candidates per family are reranked under moderate cost stress. Training uses only releases before 2026-05-19 (7 NFP, 7 CPI, 5 FOMC). This is a very small sample for many parameters.',
'- A first-pass 30-second close candidate failed native specified-expiration validation and was excluded. First-pass files were archived. Final selections were rerun natively.',
'- The fitted closed-M1-anchor setup also had four single-side invalid-price placement rejections when price was already beyond the proposed stop entry. Native results include those rejections; successfully placed events can have only one valid pending side. Retaining the opposite side is not a promise that both orders are accepted.',
'- A quote-only native export removed three missing callback quotes seen when exporting alongside synchronous trading. The revised export passed full running-candle high/low checks, baseline trade-count/net-win reconciliation, and baseline cash reconciliation within $1.',
'- Main final results are parsed from native deals; net PF and net win rate include recorded commission and swap. Equity DD is MT5 relative equity DD, not balance-only drawdown.',
'- Tester fills include the historical bid/ask path and native gap behavior, but cannot certify live news slippage, rejection rates, historical liquidity, or future profitability.',
'','Saved native HTML reports, trade-level JSON, logs, full calendar receipts, parameter candidates and screening results are in this research directory. No active system changes were made.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'final-summary.json').write_text(json.dumps(dict(stats=stats,families=family,selected=chosen),indent=2))
print(json.dumps(dict(stats=stats,families=family),indent=2))
