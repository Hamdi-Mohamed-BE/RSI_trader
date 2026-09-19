from pathlib import Path
from collections import defaultdict
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parent
money=lambda x:f'${x:,.2f}' if x>=0 else f'-${-x:,.2f}'
periods=['6m','1y','3y','5y']
rows=[]
verification=json.loads((ROOT/'verification.json').read_text())
assert len(verification)==8 and all(v['passed'] for v in verification)
expected_hash=hashlib.sha256((ROOT/'EA'/'D14 H1 M5 Break Retest Raw.mq5').read_bytes()).hexdigest()
for symbol in ('XAUUSD','USTEC'):
    for period in periods:
        tag=f'{symbol.lower()}-d14-raw-{period}-model4'
        r=json.loads((ROOT/f'{tag}-stats.json').read_text());assert r['source_sha256']==expected_hash
        r['display_symbol']='US100 (USTEC)' if symbol=='USTEC' else 'XAUUSD'
        r['max_equity_dd_pct']=float(re.search(r'([\d.]+)%',r['equity_dd_relative']).group(1))
        trades=json.loads((ROOT/'Audit'/f'{tag}-trades.json').read_text())
        r['boundary_exits']=sum('end of test' in t['exit_comment'].lower() for t in trades)
        r['report_sha256']=hashlib.sha256((ROOT/'Backtest Reports'/f'{tag}.htm').read_bytes()).hexdigest()
        rows.append(r)
lines=['# Raw D14 / H1 / M5 break-and-retest — XAUUSD and US100','',
       'Native MetaTrader 5 backtests, restarted after the user returned the active terminal to Exness. Frozen strategy v1; no optimization, live EA installation, BAT change or website publication.', '',
       '## What was tested','',
       '- Daily: last 14 completed candles split into two seven-candle blocks. Both highs/lows higher = buy; both lower = sell; mixed/equal = no entry.',
       '- H1: strict two-left/two-right confirmed swing break, following an opposite swing. The broken swing candle wick is the zone; only the latest zone is used.',
       '- M5: zone retest, at least two full-body-outside rejection wicks in three completed candles, then a new confirmed high/low stair-step and a close beyond the swing. Mirror for sells.',
       '- Stop one tick beyond the last M5 swing; 2R target; no break-even, trailing, partial closes, news/session filters or adaptive overlay.',
       '- These are explicit interpretations of discretionary wording. In particular, the transcript does not define sideways, box width, pivot confirmation, freshness or the number of wicks. This is not a claim of exact replication. All definitions were frozen before evaluating performance.',
       '- No same-day forced exit was specified. Positions can remain overnight. Details are in [RULES.md](RULES.md).','',
       '## Account, period and execution','',
       '- Exness-MT5Trial16 demo; current symbols listed under Zero. XAUUSD = gold, USTEC = US100/Nasdaq CFD. Not FTMO, not futures and not the Ava terminal.',
       '- Independent $10,000 USD start for each instrument and each window. Target 1% of current equity per trade; lot step rounds UP with broker minimum lot. Actual initial stop risk can exceed 1%, before fees/gaps.',
       '- Tester leverage 1:2000 (not a risk target). One open position per instrument; no portfolio compounding across XAUUSD and USTEC.',
       '- End date 2026-09-05 exclusive (last full trading week available to the established research windows). The rows below list each exact start date. They do not cover 5–13 September 2026.',
       '- Each window starts with fresh account/strategy state; overlapping windows are not independent samples and need not equal slices of the five-year run.',
       '- Native real-tick mode requested. ACTUAL coverage is listed below. The tester journal says real ticks begin 2026-01-01 on this feed. Older dates use generated ticks where the real history is missing; do not label the long windows 100% real-tick evidence.',
       '- Broker bid/ask prices and tester-booked commission/swap are included. Fixed 1 ms execution delay, not randomized or news-stressed execution. Stop fills may differ from requested SL. No additional invented slippage penalty was added.',
       '- Recorded zero swap is not a promise of free overnight financing or proof of historically exact charges. Current contract/account settings and historical market data do not recreate every past account-specific fee change.',
       '- Reported net win rate/PF are independently recomputed from closed trades after commission and swap; native headline PF can differ slightly. Drawdown is native maximum RELATIVE equity drawdown, including floating equity.','',
       '## Raw results — each row starts at $10,000','',
       '| Market | Window | Start | End exclusive | Closed trades | Net return | Net USD | Ending balance | Net win rate | Net PF | Max equity DD | Real-tick coverage |',
       '|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
for r in rows:
    pf=f"{r['net_pf']:.2f}" if r['net_pf'] is not None else 'N/A'
    lines.append(f"| {r['display_symbol']} | {r['period']} | {r['from']} | {r['to_exclusive']} | {r['trades']} | {r['return_pct']:+.2f}% | {money(r['net_profit'])} | {money(r['final_balance'])} | {r['net_win_rate']:.2f}% | {pf} | {r['max_equity_dd_pct']:.2f}% | {r['history_quality']} |")
lines+=['','## Costs and trading detail','',
        '| Market | Window | Commission | Swap | Winners / losers | Avg winner | Avg loser | Worst losing streak | Long trades / net | Short trades / net | Overnight trades |',
        '|---|---|---:|---:|---|---:|---:|---:|---|---|---:|']
for r in rows:
    lines.append(f"| {r['display_symbol']} | {r['period']} | {money(r['commission'])} | {money(r['swap'])} | {r['wins']} / {r['losses']} | {money(r['average_win'])} | {money(r['average_loss'])} | {r['max_loss_streak']} | {r['long_trades']} / {money(r['long_net'])} | {r['short_trades']} / {money(r['short_net'])} | {r['overnight_trades']} |")
lines+=['','## Signal funnel and execution audit','',
        '| Market | Window | H1 zones | M5 holds | Entry signals | Fills | Rejections | Order errors | Planned risk min–max | End-of-test exits |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|---:|']
for r in rows:
    lines.append(f"| {r['display_symbol']} | {r['period']} | {r['zones']} | {r['holds']} | {r['signals']} | {r['trades']} | {r['rejected']} | {len(r['execution_errors'])} | {r['planned_risk_pct_min']:.3f}%–{r['planned_risk_pct_max']:.3f}% | {r['boundary_exits']} |")
lines+=['','## Five-year run, calendar-year breakdown','',
        'Partial 2021 and 2026; these calendar-year figures partition the continuous five-year run, not separate annual restarts.', '',
        '| Market | Calendar year | Closed trades | Net USD | Commission | Swap | Win rate | Net PF |','|---|---:|---:|---:|---:|---:|---:|---:|']
yearly=[]
for symbol in ('XAUUSD','USTEC'):
    trades=json.loads((ROOT/'Audit'/f'{symbol.lower()}-d14-raw-5y-model4-trades.json').read_text())
    groups=defaultdict(list)
    for t in trades:groups[t['close_time'][:4]].append(t)
    for year,ts in sorted(groups.items()):
        wins=sum(max(0,t['net_profit']) for t in ts);loss=-sum(min(0,t['net_profit']) for t in ts)
        v={'symbol':symbol,'year':year,'trades':len(ts),'net':sum(t['net_profit'] for t in ts),'commission':sum(t['commission'] for t in ts),'swap':sum(t['swap'] for t in ts),'win_rate':100*sum(t['net_profit']>0 for t in ts)/len(ts),'pf':wins/loss if loss else None}
        yearly.append(v);pf=f"{v['pf']:.2f}" if v['pf'] is not None else 'N/A'
        lines.append(f"| {symbol} | {year} | {len(ts)} | {money(v['net'])} | {money(v['commission'])} | {money(v['swap'])} | {v['win_rate']:.2f}% | {pf} |")
lines+=['','## Verification','',
        '- Research EA refuses to initialize outside the MT5 Strategy Tester. Compilation: zero errors and warnings. Embedded synthetic rule checks passed on initialization.',
        '- Ten independent deterministic unit tests cover higher/lower/mixed/equal daily structure, strict pivots, unavailable right-hand candles and mirrored rejection rules.',
        '- Every native zone, holding confirmation and entry was independently checked against the exported D1/H1/M5 OHLC history. Checks include completed-bar daily bias, delayed swing availability, H1 break chronology, no broken-zone resurrection, wick count, higher-low/lower-high ordering, stop placement and fixed 2R arithmetic.',
        '- Trade counts, profit, commission and swap reconcile to the MT5 reports. No overlapping positions per instrument; unique trade numbers. All eight reports use the same final EA source hash.',
        f'- Source SHA-256: `{expected_hash}`.',
        '- A pre-final implementation review moved zone invalidation ahead of the open-position check and prohibited pre-test stale breaks. These are correctness fixes; no strategy parameters were selected using returns. All final tests were rerun with the corrected frozen source after the Exness restart.', '',
        '## Native reports and full trades','']
for r in rows:
    tag=f"{r['symbol_requested'].lower()}-d14-raw-{r['period']}-model4"
    lines.append(f"- {r['display_symbol']} {r['period']}: [native MT5 report](<Backtest Reports/{tag}.htm>), [closed trades with costs](<Audit/{tag}-trades.json>), [signal audit](<Audit/{tag}.csv>).")
lines+=['','## Recommendation before optimization','',
        '- XAUUSD: defer the full pipeline. The three-year result is positive, but the five-year account gains only $79.64 (+0.80%) with 17.52% equity drawdown and just 66 trades. The six-month fully real-tick sample also loses and has only seven trades. This is not a stable demonstrated edge.',
        '- US100: skip this raw version. All four requested windows lose; five-year net is -$1,705.63 (-17.06%), PF 0.60 and 20.34% equity drawdown.',
        '- If revisiting the concept, first clarify the creator’s exact daily-trend, H1-zone and M5-structure definitions. Any different interpretation must be labelled a new hypothesis, not silently called the same raw strategy. No optimization has been authorized or performed.',
        '- One XAU order attempt was rejected as market closed on 2025-02-12 at 21:20 server time. The same event appears in both overlapping 3Y and 5Y reports. It was not filled, retried late or counted as a completed trade.',
        '', '## Interpretation and limits','',
        'This raw test decides whether further research is justified; it is not a guarantee of an edge, proof of out-of-sample profitability, or authorization for optimization/deployment. A small trade count can produce misleading win rates. The transcript’s fixed 2R exit means the theoretical pre-cost break-even win rate is 33.33%; spread, commission, swap and adverse fills increase it.',
        '', '## References','',
        '- User-supplied strategy transcript (primary strategy specification).',
        '- [MetaTrader 5 testing modes, execution delay and historical testing](https://www.metatrader5.com/en/terminal/help/algotrading/testing).',
        '- [MQL5 CopyRates ordering and current versus completed bars](https://www.mql5.com/en/docs/series/copyrates).','']
(ROOT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
(ROOT/'results.json').write_text(json.dumps({'source_sha256':expected_hash,'rows':rows,'yearly':yearly,'verification':verification},indent=2),encoding='utf-8')
print('\n'.join(lines[lines.index('## Raw results — each row starts at $10,000'):lines.index('## Costs and trading detail')]))
