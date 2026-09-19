from collections import defaultdict
from pathlib import Path
import hashlib,json,re

ROOT=Path(__file__).resolve().parent
money=lambda x:f'${x:,.2f}' if x>=0 else f'-${-x:,.2f}'
pf=lambda x:f'{x:.2f}' if x is not None else 'N/A'
periods=('6m','1y','3y','5y');rows=[]
verification=json.loads((ROOT/'verification.json').read_text());assert len(verification)==8 and all(x['passed'] for x in verification)
source=ROOT/'EA'/'H4 Fair Value Gap Raw.mq5';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
for symbol in ('XAUUSD','USTEC'):
    for period in periods:
        tag=f'{symbol.lower()}-h4-fvg-raw-{period}-model4'
        r=json.loads((ROOT/f'{tag}-stats.json').read_text());assert r['source_sha256']==source_hash
        r['display']='US100 (USTEC)' if symbol=='USTEC' else 'XAUUSD'
        r['equity_dd_pct']=float(re.search(r'([\d.]+)%',r['equity_dd_relative']).group(1))
        r['report_sha256']=hashlib.sha256((ROOT/'Backtest Reports'/f'{tag}.htm').read_bytes()).hexdigest()
        rows.append(r)
lines=['# Raw H4 fair-value-gap swing — XAUUSD and US100','',
 '**Raw research only. No optimization, deployment, website/BAT modification or Git push.** One frozen mechanical rule set was applied unchanged to both markets.','',
 '## Mechanical interpretation','',
 '- Completed H4 candles only. Bullish FVG: candle 3 low above candle 1 high. Bearish: candle 3 high below candle 1 low.',
 '- Keep the newest untraded gap per direction. Enter at the first later executable tick inside it; invalidate if price crosses the far edge first.',
 '- Stop one tradable tick beyond candle 1 extreme; fixed 2R target. One position per symbol; both directions.',
 '- No displacement threshold, trend, volume, lower-timeframe, news, session, expiry, break-even or trailing filter.',
 '- The transcript defines only the visual H4 gap and retrace. Stop, target, symmetry and zone lifecycle are necessary explicit assumptions, frozen before results. This is not an exact clone of a discretionary/private strategy. See [RULES.md](RULES.md).','',
 '## Account and evidence','',
 '- Native MT5 Strategy Tester on Exness-MT5Trial16 Zero demo, XAUUSD and USTEC, H4, independent $10,000 starts, leverage 1:2000.',
 '- Planned risk is 1% of current equity; volume rounds up to the broker step/minimum, so it is not a hard cap. Spread, tester-booked commission and swap are included.',
 '- Real-tick mode requested with 1ms delay. Journal evidence says real ticks begin 2026-01-01; older missing ticks are generated. All windows end 2026-09-05 exclusive.',
 '- Overlapping periods restart balance and setup state; they are not independent experiments. Returns are total-period, not annualized.','',
 '## Raw results','',
 '| Market | Window | Trades | Return | Net USD | Final balance | Win rate | PF | Max equity DD | Real-tick coverage |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
for r in rows:
    lines.append(f"| {r['display']} | {r['period']} | {r['trades']} | {r['return_pct']:+.2f}% | {money(r['net_profit'])} | {money(r['final_balance'])} | {r['net_win_rate']:.2f}% | {pf(r['net_pf'])} | {r['equity_dd_pct']:.2f}% | {r['history_quality']} |")
lines+=['','## Costs, direction and holding','',
 '| Market | Window | Commission | Swap | Winners / losers | Long trades / net | Short trades / net | Overnight | Avg holding | Worst loss streak |',
 '|---|---|---:|---:|---|---|---|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['display']} | {r['period']} | {money(r['commission'])} | {money(r['swap'])} | {r['wins']} / {r['losses']} | {r['long_trades']} / {money(r['long_net'])} | {r['short_trades']} / {money(r['short_net'])} | {r['overnight_trades']} | {r['mean_holding_minutes']/60:.1f}h | {r['max_loss_streak']} |")
lines+=['','## Signal and execution audit','',
 '| Market | Window | H4 gaps | Invalidated | Attempts | Fills | Rejected | Errors | Actual filled stop risk | Boundary exits |',
 '|---|---|---:|---:|---:|---:|---:|---:|---|---:|']
for r in rows:
    lines.append(f"| {r['display']} | {r['period']} | {r['zones']} | {r['invalidated']} | {r['attempted']} | {r['trades']} | {r['rejected']} | {len(r['execution_errors'])} | {r['planned_risk_pct_min']:.3f}%–{r['planned_risk_pct_max']:.3f}% | {r['boundary_exits']} |")
lines+=['','## Five-year calendar breakdown','',
 'Partial 2021 and 2026. These partition each continuous five-year run.','',
 '| Market | Year | Trades | Net USD | Win rate | PF | Commission | Swap |','|---|---:|---:|---:|---:|---:|---:|---:|']
yearly=[]
for symbol in ('XAUUSD','USTEC'):
    ts=json.loads((ROOT/'Audit'/f'{symbol.lower()}-h4-fvg-raw-5y-model4-trades.json').read_text());groups=defaultdict(list)
    for t in ts:groups[t['close_time'][:4]].append(t)
    for year,v in sorted(groups.items()):
        wins=sum(max(0,t['net_profit']) for t in v);loss=-sum(min(0,t['net_profit']) for t in v)
        x=dict(symbol=symbol,year=year,trades=len(v),net=sum(t['net_profit'] for t in v),win_rate=100*sum(t['net_profit']>0 for t in v)/len(v),pf=wins/loss if loss else None,commission=sum(t['commission'] for t in v),swap=sum(t['swap'] for t in v));yearly.append(x)
        lines.append(f"| {symbol} | {year} | {len(v)} | {money(x['net'])} | {x['win_rate']:.2f}% | {pf(x['pf'])} | {money(x['commission'])} | {money(x['swap'])} |")
    five=next(r for r in rows if r['symbol_requested']==symbol and r['period']=='5y')
    assert sum(x['trades'] for x in yearly if x['symbol']==symbol)==five['trades']
    assert abs(sum(x['net'] for x in yearly if x['symbol']==symbol)-five['net_profit'])<.051
lines+=['','## Verification','',
 '- EA compilation completed with zero errors and zero warnings, and it refuses non-tester initialization.',
 '- Ten deterministic rule tests passed. Every native H4 gap was independently recomputed from exported candles; completed-bar chronology, exact zone/stop construction, first-use uniqueness, 2R arithmetic, risk rounding and mirrored invalidation were checked.',
 '- Every trade count and its profit, commission and swap reconcile to the native report. No overlapping strategy positions occurred. All eight runs use the same source hash.',
 '- Four XAU and four US100 attempts in the overlapping longer windows were rejected as market closed. They were not filled or counted as trades; the EA did not retry them later.',
 f'- Source SHA-256: `{source_hash}`.','',
 '## Recommendation','']
x5=next(r for r in rows if r['symbol_requested']=='XAUUSD' and r['period']=='5y')
u5=next(r for r in rows if r['symbol_requested']=='USTEC' and r['period']=='5y')
for r in (x5,u5):
    decision='consider a full pipeline only if performance is positive across meaningful windows with acceptable drawdown' if r['return_pct']>0 and (r['net_pf'] or 0)>1 else 'skip full optimization of this raw interpretation'
    lines.append(f"- {r['display']}: {decision}. Five-year result {r['return_pct']:+.2f}%, PF {pf(r['net_pf'])}, equity DD {r['equity_dd_pct']:.2f}%, {r['trades']} trades.")
lines+=['- No profitability is guaranteed. If the raw version fails, optimization could mostly fit assumptions the transcript never supplied. A better next step would be obtaining the creator\'s exact stop, target, invalidation and multi-gap rules.','',
 '## Native reports','']
for r in rows:
    tag=f"{r['symbol_requested'].lower()}-h4-fvg-raw-{r['period']}-model4"
    lines.append(f"- {r['display']} {r['period']}: [MT5 report](<Backtest Reports/{tag}.htm>), [trades](<Audit/{tag}-trades.json>), [signal audit](<Audit/{tag}.csv>).")
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'results.json').write_text(json.dumps(dict(source_sha256=source_hash,rows=rows,yearly=yearly,verification=verification),indent=2),encoding='utf-8')
files=[ROOT/'RESULTS.md',ROOT/'results.json',ROOT/'RULES.md',ROOT/'verification.json',ROOT/'run_raw.py',ROOT/'verify.py',ROOT/'report.py',ROOT/'test_rules.py',source]
files += sorted(ROOT.glob('*-stats.json'))+sorted((ROOT/'Audit').glob('*-trades.json'))+sorted((ROOT/'Backtest Reports').glob('*.htm'))
(ROOT/'manifest.json').write_text(json.dumps({str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files},indent=2),encoding='utf-8')
print('\n'.join(lines[lines.index('## Raw results'):lines.index('## Costs, direction and holding')]))
