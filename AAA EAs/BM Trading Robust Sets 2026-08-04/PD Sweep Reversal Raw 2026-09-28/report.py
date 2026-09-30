"""Generate descriptive comparisons from native ledgers, never simulate new trades."""
from pathlib import Path
from datetime import datetime,timedelta
import json,math,statistics
from verify import fields,streaks
import run as runner
ROOT=runner.ROOT;CFG=runner.CFG
def f(x,d=2):return 'n/a' if x is None else f'{x:.{d}f}'
def stats(trades,start,end,asset):
 p=[t['net_profit'] for t in trades];n=len(p);gross=sum(max(x,0) for x in p);loss=-sum(min(x,0) for x in p)
 a=datetime.strptime(start,'%Y.%m.%d');b=datetime.strptime(end,'%Y.%m.%d');days=(b-a).days
 weekdays=sum((a+timedelta(days=i)).weekday()<5 for i in range(days));months=days/365.2425*12
 mw,aw=streaks(p,True);ml,al=streaks(p,False)
 monthly={};k=a.year*12+a.month-1;z=(b-timedelta(days=1)).year*12+(b-timedelta(days=1)).month-1
 for i in range(k,z+1):monthly[f'{i//12:04d}-{i%12+1:02d}']=0
 for t in trades:monthly[t['close_time'][:7]]=monthly.get(t['close_time'][:7],0)+t['net_profit']
 pn=sum(x>0 for x in p)/n if n else 0;ci=[0,100]
 if n:
  q=1.959963984540054;c=(pn+q*q/(2*n))/(1+q*q/n);h=q*math.sqrt(pn*(1-pn)/n+q*q/(4*n*n))/(1+q*q/n);ci=[100*(c-h),100*(c+h)]
 return dict(trades=n,net_profit=sum(p),return_pct=sum(p)/CFG['deposit']*100,win_rate=pn*100,win_ci=ci,pf=gross/loss if loss else None,
  per_month=n/months,per_day=n/(days if asset=='BTC' else weekdays),max_win_streak=mw,max_loss_streak=ml,average_win_streak=aw,average_loss_streak=al,
  commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),fee=sum(t['fee'] for t in trades),
  expectancy=sum(p)/n if n else 0,monthly=monthly,profitable_months_pct=100*sum(x>0 for x in monthly.values())/len(monthly))
def load():
 rows=[]
 for p in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(p.read_text())
  if r['smoke']:continue
  trades=json.loads((p.parent/'trades.json').read_text());orders=json.loads((p.parent/'orders.json').read_text())
  r['net']=stats(trades,r['start'],r['end'],r['asset']);r['counters']=fields(r['summary'][0]);r['path']=p.parent.name
  ratios=[float(o['risk'])/float(o['planned']) for o in orders if float(o['planned'])>0]
  slip=[int(o['side'])*(float(o['fill'])-float(o['entry']))*float(o['risk'])/abs(float(o['entry'])-float(o['sl'])) for o in orders]
  r['sizing']=dict(median_ratio=statistics.median(ratios) if ratios else None,max_ratio=max(ratios,default=None),above_110pct=sum(x>1.1 for x in ratios))
  r['fills']=dict(mean_adverse_slippage_usd=statistics.mean(slip) if slip else None,max_adverse_slippage_usd=max(slip,default=None))
  r['overnight_positions']=sum(t['open_time'][:10]!=t['close_time'][:10] for t in trades)
  rows.append(r)
 return rows
def table(rows):
 lines=['| Asset | TF / variant | Return | Trades | /month | /day | Win rate | Net PF | Equity DD | Balance DD | Max W/L | Avg W/L |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  n=r['net'];m=r['metrics'];variant='raw' if r['variant']=='reversal' else 'control'
  lines.append(f'| {r["asset"]} | M{r["timeframe"]} {variant} | {n["return_pct"]:+.2f}% | {n["trades"]} | {n["per_month"]:.1f} | {n["per_day"]:.2f} | {n["win_rate"]:.2f}% | {f(n["pf"])} | {m["max_equity_dd_pct"]:.2f}% | {m["max_balance_dd_pct"]:.2f}% | {n["max_win_streak"]}/{n["max_loss_streak"]} | {n["average_win_streak"]:.2f}/{n["average_loss_streak"]:.2f} |')
 return lines
def main():
 rows=load();index={(r['asset'],r['timeframe'],r['variant'],r['window']):r for r in rows};gates={};comparisons=[]
 for asset in CFG['symbols']:
  for tf in CFG['timeframes']:
   checks=[]
   for w in ('3y','5y'):
    r=index.get((asset,tf,'reversal',w));c=index.get((asset,tf,'random-direction-control',w))
    checks.append(None if not r or not c else r['net']['trades']>=30 and r['net']['return_pct']>0 and (r['net']['pf'] or 0)>=1.15 and r['net']['return_pct']>c['net']['return_pct'] and (r['net']['pf'] or 0)>(c['net']['pf'] or 0))
   gates[f'{asset}-M{tf}']='INCOMPLETE' if None in checks else 'PASS_RAW_REVIEW' if all(checks) else 'FAIL'
  a=index.get((asset,5,'reversal','1y'));b=index.get((asset,15,'reversal','1y'))
  if a and b:comparisons.append(dict(asset=asset,last_year_higher_return='M5' if a['net']['return_pct']>b['net']['return_pct'] else 'M15',last_year_higher_pf='M5' if (a['net']['pf'] or 0)>(b['net']['pf'] or 0) else 'M15',last_year_lower_equity_dd='M5' if a['metrics']['max_equity_dd_pct']<b['metrics']['max_equity_dd_pct'] else 'M15',m5_gate=gates[f'{asset}-M5'],m15_gate=gates[f'{asset}-M15']))
 verify=json.loads((ROOT/'VERIFICATION.json').read_text()) if (ROOT/'VERIFICATION.json').exists() else None
 runner.save(ROOT/'RESULTS.json',dict(completed=len(rows),expected=64,gates=gates,comparisons=comparisons,verification=verify,runs=rows))
 lines=['# Previous-day sweep rejection — M5 versus M15','',f'Completed main runs: **{len(rows)}/64**. Four extra engineering smoke runs. No optimization, production changes or live orders.','',
  '## What was tested','',
  'The transcript supplies only the previous-day sweep and reverse-on-close idea. Our raw defaults: same-candle rejection on M5 or M15, market entry at the next fresh quote, one-tick-beyond-candle stop, 2R target, 1% equity planned risk, one position, first qualifying signal per PDH/PDL per day, 23:50 broker-time close attempt. See `RULES.md` for boundary cases and day-end gaps.',
  '', 'The two timeframes share every other rule. Each run starts independently at $10,000, on isolated Exness CFD history; not FTMO, not a combined portfolio, not an exact copy of RoboQuant.','', '## Which timeframe looks better?','']
 if comparisons:
  for c in comparisons:lines.append(f'- **{c["asset"]}**: last-year return leader {c["last_year_higher_return"]}; PF leader {c["last_year_higher_pf"]}; lower equity DD {c["last_year_lower_equity_dd"]}. Long-window raw gates: M5 **{c["m5_gate"]}**, M15 **{c["m15_gate"]}**.')
 else:lines.append('Comparison pending. Do not rank partially completed pairs.')
 if len(rows)==64:
  passed=[name for name,value in gates.items() if value=='PASS_RAW_REVIEW']
  lines += ['', '**Completed raw decision: all eight asset/timeframe variants FAIL the frozen gate. None is selected for optimization or promotion.**' if not passed else '**Raw-review survivors:** '+', '.join(passed)+'. These are not live-approved.']
 lines += ['', 'A recent-year winner is descriptive, not proof of future superiority. The predeclared 3y/5y/control gate takes priority. Passing that gate only qualifies for review, not live/FTMO use. All windows overlap; none is untouched out-of-sample evidence.','', '## Latest year — reversal only','']
 one=[index[(a,tf,'reversal','1y')] for a in CFG['symbols'] for tf in CFG['timeframes'] if (a,tf,'reversal','1y') in index]
 lines += table(one)
 for w,start in CFG['windows'].items():
  lines += ['',f'## {w}: {start} to {CFG["end"]} (end exclusive)','']
  selected=[index[(a,tf,v,w)] for a in CFG['symbols'] for tf in CFG['timeframes'] for v in CFG['variants'] if (a,tf,v,w) in index]
  lines += table(selected)
 lines += ['', '## Costs, sizing and holding limitations — latest-year raw','', '| Asset / TF | Trades (/month; /day) | Commission / swap / fee | Median / max risk multiplier | Above 1.1% planned risk | Mean adverse entry slip | Overnight positions | Profitable calendar months |','|---|---|---|---|---:|---:|---:|---:|']
 for r in one:
  n=r['net'];s=r['sizing'];sl=r['fills']
  lines.append(f'| {r["asset"]} M{r["timeframe"]} | {n["trades"]} ({n["per_month"]:.1f}; {n["per_day"]:.2f}) | ${n["commission"]:.2f} / ${n["swap"]:.2f} / ${n["fee"]:.2f} | {f(s["median_ratio"])}x / {f(s["max_ratio"])}x | {s["above_110pct"]} | ${f(sl["mean_adverse_slippage_usd"])} | {r["overnight_positions"]} | {n["profitable_months_pct"]:.1f}% |')
 lines += ['',
  '- Returns/PF/wins are recomputed from position-ID ledgers NET of commission, swap and fees. Spread and simulated delay are already in execution prices; they are not subtracted twice. Positive entry slippage means an adverse fill versus submission quote. Exit slippage is not separately measured.',
  '- Lots round UP per the existing raw-research convention. The risk multiplier is planned stop loss after lot rounding divided by requested 1% risk, BEFORE commissions/slippage. This is not a hard maximum loss. Minimum lots or account depletion can reduce comparability.',
  '- Day-end closes require a tradable tick. Instrument closure can carry positions past midnight/weekends; those exposures and swap are retained, not removed after seeing results.',
  '- /day is all weekdays for US30/US100/XAU and all calendar days for BTC, including no-trade days. /month uses elapsed calendar time. Monthly consistency includes two partial endpoint months (13 calendar buckets for 1y). Zero-net trades break win/loss streaks.',
  '- Native floating-equity DD is distinct from closed-balance DD. Do not use either alone to estimate FTMO daily-equity breaches.',
  '- Model 4 plus 150 ms delay is used throughout. Real ticks in the retained broker history begin January 2026; earlier data use generated ticks. A mode label does not guarantee real-tick coverage. [MetaTrader documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).',
  '- The control retains sweep conditions but randomizes direction with one predeclared seed. It is not a test against non-key price levels, multiple seeds, or a perfectly paired execution experiment. Different trade counts can result from stops and occupancy.',
  '- The Instagram $10,000/week statement and optimized screenshot results are not verified and are not a return forecast for these settings.',
  '', '## Data / execution audit','']
 for r in rows:
  lines += [f'- {r["asset"]} M{r["timeframe"]} {r["variant"]} {r["window"]}: native history quality `{r["metrics"]["history_quality"]}` including warmup; flags `{json.dumps(r["flags"])}`; `{r["summary"][0]}`.']
 lines += ['', '## Verification','']
 if verify:
  fully_checked=len(verify['completed_cases'])==68 and len(verify['historical_bar_checks'])==68 and verify['unresolved_omissions']==0
  lines += [f'{verify["helper_tests"]} helper tests; {len(verify["completed_cases"])} completed native cases checked; {verify["total_orders"]:,} positions and {verify["total_signals"]:,} signals reconciled.',
   f'Historical-bar reconstruction: {len(verify["historical_bar_checks"])} cases checked; unresolved omitted-signal candidates: {verify["unresolved_omissions"]}. '+('COMPLETE: all recorded signals match native historical candles/previous-day levels and every independently reconstructed eligible signal is accounted for.' if fully_checked else 'Provisional until every completed run is covered and omissions are explained.'),
   'The independent audit also uses native M1 availability for the <60-second entry guard. On BTC, 9 July 2024, the nominal 18:50 M5 candle actually begins with the 18:52 minute: the earlier 18:45 rejection is correctly skipped as stale. The later 22:50 rejection remains eligible. This correction affects the audit only, not the frozen EA or results.']
 else:lines.append('Verification pending.')
 lines += ['', '## Evidence','', '`BUILD.json` freezes EA source, binary, rules and configuration. `native/<case>/` retains exact SET/INI, compressed native report and journal, full deals, position ledger and entry audits. Five-year raw runs export the native signal/D1 bars for independent reconstruction. The separate read-only `minute-audit/` exports verify fresh-quote availability. `RESULTS.json` retains monthly breakdowns, costs and all comparisons.','', 'No optimization, Monte Carlo, FTMO pass probability, website/BAT update or live deployment is claimed.']
 if (ROOT/'balance-1y.png').exists():lines += ['', '## Latest-year closed balance — not floating equity','', '![Closed balance comparison](balance-1y.png)']
 (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(dict(completed=len(rows),gates=gates,comparisons=comparisons)),flush=True)
if __name__=='__main__':main()
