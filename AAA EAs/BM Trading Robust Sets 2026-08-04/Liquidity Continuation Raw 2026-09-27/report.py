"""Read-only analysis of retained native runs; generated study artifacts only."""
from pathlib import Path
from datetime import datetime,timedelta
import json,math,statistics
ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sequences(trades,positive):
 groups=[];n=0
 for t in trades:
  yes=t['net_profit']>0 if positive else t['net_profit']<0
  if yes:n+=1
  elif n:groups.append(n);n=0
 if n:groups.append(n)
 return max(groups,default=0),statistics.mean(groups) if groups else 0
def wilson(w,n):
 if not n:return [0,100]
 z=1.959963984540054;p=w/n;c=(p+z*z/(2*n))/(1+z*z/n);h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
 return [100*(c-h),100*(c+h)]
def metrics(trades,start,end):
 n=len(trades);wins=sum(t['net_profit']>0 for t in trades);profit=sum(max(t['net_profit'],0) for t in trades);loss=-sum(min(t['net_profit'],0) for t in trades)
 a=datetime.strptime(start,'%Y.%m.%d');b=datetime.strptime(end,'%Y.%m.%d');days=(b-a).days
 weekdays=sum((a+timedelta(days=i)).weekday()<5 for i in range(days));months=days/365.2425*12
 mw,aw=sequences(trades,True);ml,al=sequences(trades,False)
 return dict(trades=n,return_pct=sum(t['net_profit'] for t in trades)/100,win_rate_pct=100*wins/n if n else 0,pf=profit/loss if loss else None,win_ci=wilson(wins,n),trades_month=n/months,trades_weekday=n/weekdays,trades_calendar_day=n/days,win_streak=mw,loss_streak=ml,avg_win_streak=aw,avg_loss_streak=al,commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),expectancy=sum(t['net_profit'] for t in trades)/n if n else 0)
def load():
 rows=[]
 for p in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(p.read_text())
  if not r['ok'] or r['smoke']:continue
  trades=json.loads((p.parent/'trades.json').read_text());r['net']=metrics(trades,r['start'],r['end'])
  r['net']['trades_day']=r['net']['trades_calendar_day'] if r['asset']=='BTC' else r['net']['trades_weekday']
  r['counters']={k:int(v) for k,v in __import__('re').findall(r'(\w+)=(\d+)',r['summary'][0])} if r['summary'] else {}
  r['families']={}
  for family in ('PD','AS','LD','PW'):
   subset=[t for t in trades if t['entry_comment'].startswith('LC '+family)];r['families'][family]=metrics(subset,r['start'],r['end'])
  ma=datetime.strptime(r['start'],'%Y.%m.%d');mb=datetime.strptime(r['end'],'%Y.%m.%d')-timedelta(days=1)
  ym=ma.year*12+ma.month-1;last=mb.year*12+mb.month-1
  r['monthly']={f'{k//12:04d}-{k%12+1:02d}':0 for k in range(ym,last+1)}
  for t in trades:
   key=t['close_time'][:7];r['monthly'][key]=r['monthly'].get(key,0)+t['net_profit']
  r['profitable_months_pct']=100*sum(v>0 for v in r['monthly'].values())/len(r['monthly'])
  audit=json.loads((p.parent/'order-audit.json').read_text());r['oversizing']={}
  if audit:
   ratios=[float(o['risk'])/float(o['planned']) for o in audit if float(o['planned'])>0]
   r['oversizing']=dict(median_ratio=statistics.median(ratios),max_ratio=max(ratios),over_110pct=sum(x>1.1 for x in ratios),count=len(ratios))
   slip=[int(o['type'])*(float(o['fill'])-float(o['entry']))*float(o['risk'])/abs(float(o['entry'])-float(o['sl'])) for o in audit]
   r['entry_slippage_cash']=dict(net_adverse=sum(slip),average=statistics.mean(slip),max_adverse=max(slip),best_improvement=min(slip))
  rows.append(r)
 return rows
def f(x,dp=2):return 'n/a' if x is None else f'{x:.{dp}f}'
def main():
 rows=load();idx={(r['asset'],r['variant'],r['window']):r for r in rows};gates={}
 for a in CFG['symbols']:
  for v in ('touch','retest'):
   checks=[]
   for w in ('3y','5y'):
    r=idx.get((a,v,w));c=idx.get((a,v+'-control',w))
    checks.append(None if not r or not c else r['net']['trades']>=30 and r['net']['return_pct']>0 and (r['net']['pf'] or 0)>=1.15 and r['net']['return_pct']>c['net']['return_pct'] and (r['net']['pf'] or 0)>(c['net']['pf'] or 0))
   gates[a+'-'+v]='INCOMPLETE' if None in checks else 'PASS_RAW_REVIEW' if all(checks) else 'FAIL'
 verification=json.loads((ROOT/'VERIFICATION.json').read_text()) if (ROOT/'VERIFICATION.json').exists() else None
 bar_verification=json.loads((ROOT/'BAR_VERIFICATION.json').read_text()) if (ROOT/'BAR_VERIFICATION.json').exists() else None
 save(ROOT/'RESULTS.json',dict(completed=len(rows),expected=80,gates=gates,verification=verification,bar_verification=bar_verification,runs=rows))
 lines=['# Calyx Liquidity Continuation — raw results','',f'Completed: **{len(rows)}/80** frozen native tests. No optimization or deployment.','',
 'Independent reconstruction, NOT T-812. The source keeps its profitable rules private: [Telonics research](https://www.telonicstrading.com/research-liquidity-sweeps.html).',
 '', '## Decision','',
 ('**Do not deploy or optimize this raw version without a new research decision. All ten real-level variants fail the frozen 3y + 5y gate.** The strongest recent result alone is not evidence of a durable edge.' if len(rows)==80 and all(g=='FAIL' for g in gates.values()) else 'The study is still incomplete; partial results are not approval to deploy.'),
 '', '## At a glance: real levels only','', '| Asset | Entry | 6m return | 1y return | 3y return | 5y return |','|---|---|---:|---:|---:|---:|']
 for a in CFG['symbols']:
  for v in ('touch','retest'):
   values=[]
   for w in ('6m','1y','3y','5y'):
    r=idx.get((a,v,w));values.append(f'{r["net"]["return_pct"]:+.2f}%' if r else 'pending')
   lines.append('| '+a+' | '+v+' | '+' | '.join(values)+' |')
 lines += ['', '## Read this first','',
 '- Separate $10,000 accounts per asset/entry/window, 1% current-equity target stop risk, upward broker lot rounding. Results are not a combined portfolio or FTMO simulation.',
 '- Exness isolated CFD research, Model 4 + 150 ms delay. Native spread, commissions and swaps; not exchange futures prints, guaranteed fills or exact FTMO costs.',
 '- Native journals report real ticks beginning 2026-01-01 for all five symbols. Earlier periods use generated ticks. None of the quote streams supplies nonzero contract volume or aggressor buy/sell flags, so the video\'s 8x volume / 70% directional-contract observation cannot be replicated with this data.',
 '- An extra 300 calendar days warms up controls without trading. Report-native history-quality percentages include that warmup, NOT just the requested trade window. Journal real-tick start dates and data warnings are retained.',
 '- First touch versus completed-M5 breakout then a later retest; both 1 ATR(14) M5 stop and target, 60-minute time exit. No order-flow or volume filter. See RULES.md for exact UTC sessions and expiry.',
 '- All PF and win rates below are recalculated NET of deal commission/swap. Equity DD comes from the native floating-equity report; the figure shows CLOSED balance only.',
 '- /day divides by all weekdays for indices/gold and all calendar days for BTC, including days with no trades; not just active trading days. /month uses elapsed calendar time.',
 '- Severely depleted long-run accounts may stop taking signals when minimum lots cannot be margined. This can make a five-year run contain fewer executed trades than a three-year run. No capital resets or deposits are used; minimum-lot rounding can exceed the intended 1% risk.',
 '- A few terminal balances slightly below zero are native tester loss/cost overshoots near account depletion. They are reported without clipping, not a claim about a live broker\'s negative-balance protection or a debt owed.',
 '- Control = past-donor synthetic levels, formation-clock/direction/ATR-distance matched approximately. Not exact matched touch times, not paired trade counts, not proof of causality. Warmup failures and missing profiles are not zero risk.',
 '- 1y / 6m / 3y / 5y are overlapping descriptive windows, not untouched out-of-sample tests. Choosing the best of ten real variants itself introduces selection bias.',
 '', '## Gate','', '| Asset / model | 3y + 5y raw gate |','|---|---|']
 lines += [f'| {k} | {v} |' for k,v in gates.items()]
 for w in CFG['windows']:
  lines += ['',f'## {w}: {CFG["windows"][w]} to {CFG["end"]} (end exclusive)','', '| Asset | Entry | Return | Trades | /mo | /day | Win | Net PF | Equity DD | Balance DD | Max W/L |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
  for a in CFG['symbols']:
   for model in CFG['models']:
    r=idx.get((a,model['name'],w))
    if not r:continue
    n=r['net'];m=r['metrics']
    lines.append(f'| {a} | {r["variant"]} | {n["return_pct"]:+.2f}% | {n["trades"]} | {n["trades_month"]:.1f} | {n["trades_day"]:.2f} | {n["win_rate_pct"]:.2f}% | {f(n["pf"])} | {m["max_equity_dd_pct"]:.2f}% | {m["max_balance_dd_pct"]:.2f}% | {n["win_streak"]}/{n["loss_streak"]} |')
 lines += ['', '## One-year uncertainty, costs and sizing','', '| Asset | Model | Win rate 95% interval | Average W/L streak | Commission | Swap | Median / max risk multiplier | Trades above 1.1% planned-stop risk |','|---|---|---|---|---:|---:|---|---:|']
 for r in rows:
  if r['window']!='1y' or 'control' in r['variant']:continue
  n=r['net'];o=r['oversizing'];ci=n['win_ci']
  lines.append(f'| {r["asset"]} | {r["variant"]} | {ci[0]:.1f}–{ci[1]:.1f}% | {n["avg_win_streak"]:.2f}/{n["avg_loss_streak"]:.2f} | ${n["commission"]:.2f} | ${n["swap"]:.2f} | {f(o.get("median_ratio"))}x / {f(o.get("max_ratio"))}x | {o.get("over_110pct",0)} |')
 lines += ['', 'Wilson intervals treat trades as independent and are descriptive; serial dependence makes them optimistic. Risk is at submission quote, excluding costs/slippage; not a hard loss cap.','', '## One-year fills and execution limitations','', '| Asset | Model | Failed entries | Failed timed-close attempts | Mean entry slippage, USD | Largest adverse entry slip, USD |','|---|---|---:|---:|---:|---:|']
 for r in rows:
  if r['window']!='1y' or 'control' in r['variant']:continue
  c=r['counters'];s=r.get('entry_slippage_cash',{})
  lines.append(f'| {r["asset"]} | {r["variant"]} | {c.get("entryFails",0)} | {c.get("closeFails",0)} | {f(s.get("average"))} | {f(s.get("max_adverse"))} |')
 lines += ['', 'Positive slippage means adverse entry price versus submission quote; negative means improvement. Already reflected in native returns, not added/subtracted twice. Exit slippage is not measured separately. Native journal flag occurrences below can repeat between agent/terminal logs; EA counters above are the actual attempt counts. Missing-profile and setup-expiry counters include warmup.','', '## One-year level-family breakdown (descriptive, not separately tested variants)','', '| Asset | Model | Family | Trades | Win | Net PF | Net P/L USD |','|---|---|---|---:|---:|---:|---:|']
 for r in rows:
  if r['window']!='1y' or 'control' in r['variant']:continue
  for family,n in r['families'].items():lines.append(f'| {r["asset"]} | {r["variant"]} | {family} | {n["trades"]} | {n["win_rate_pct"]:.2f}% | {f(n["pf"])} | {n["return_pct"]*100:+.2f} |')
 lines += ['', 'PD = previous day, AS = completed Asia, LD = completed London, PW = previous week. Family counts reflect fixed collision priority and the combined one-position cap; they are NOT results of standalone family EAs.','', '## Native data and execution audit','']
 for r in rows:
  lines += [f'### {r["asset"]} / {r["variant"]} / {r["window"]}','',f'- Native quality (including warmup): {r["metrics"]["history_quality"]}',f'- Flags: `{json.dumps(r["flags"])}`']
  lines += ['- '+s for s in r['summary']]
 lines += ['', '## Verification','']
 if verification:
  checks=verification['native_cases']
  lines += [f'Helper tests: {verification["unit_tests"]}, failures: {verification["unit_failures"]}. Retained native cases checked: {len(checks)} (including smoke tests); reconciled orders/deals: {sum(c["trades"] for c in checks):,}. Full case-by-case evidence: `VERIFICATION.json`.']
 if bar_verification:
  lines += ['',f'Independent native M5/D1 bar rebuild: **{bar_verification["total_errors"]} discrepancies** across {len(bar_verification["cases"])} retained cases. Full counts and any examples: `BAR_VERIFICATION.json`.']
 else:lines += ['', 'Independent historical-bar rebuild pending; no successful audit is claimed yet.']
 lines += ['', '## Evidence','', 'BUILD.json freezes source, binary, config and rules hashes. native/<case>/ stores inputs, native report (gzip), deals, journal (gzip), order audit and run metadata. RESULTS.json additionally holds per-level-family and monthly breakdowns. No installer, active terminal, website, or FTMO package changed.','', 'No forward return, pass rate or payout probability follows from these raw results.']
 (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(dict(completed=len(rows),gates=gates)),flush=True)
if __name__=='__main__':main()
