"""Derived report; frozen EA/search are never edited here."""
from pathlib import Path
import hashlib,html,importlib.util,json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('slow_report_helpers',R/'analyze.py')
a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
read=a.read;save=a.save;fmt=a.fmt
LABELS={'CURRENT':'Normal 1R','FTMO_TARGET':'FTMO target 0.5R','CANDIDATE':'Research candidate'}
HEADER='<tr><th>Version / period</th><th>Trades</th><th>Net wins</th><th>PF</th><th>Return</th><th>Equity DD</th><th>Daily Sharpe</th><th>Win / loss run</th><th>/ month</th><th>/ weekday</th><th>History</th></tr>'
def row(label,r):
 m=r['metrics'];nat=r['native']
 if r.get('disqualified'):label='REJECTED · '+label
 vals=[label,m['trades'],fmt(m['win_rate'],1)+'%',fmt(m['pf'],3),fmt(m['return_pct'])+'%',fmt(nat['equity_dd_pct'])+'%',fmt(m['sharpe_daily_equity']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday']),nat['history_quality']]
 return '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in vals)+'</tr>'
def table(rows):return '<div class="scroll"><table><thead>'+HEADER+'</thead><tbody>'+''.join(rows)+'</tbody></table></div>'
def describe(p):
 tf={16388:'H4',16408:'D1',32769:'W1'}[int(p['InpSignalTimeframe'])]
 horizon=['1m','3m','6m','1/3/6m','3/6/12m'][int(p['InpHorizonMode'])]
 trend=['none','EMA100 trading-day scaled','EMA200 trading-day scaled','EMA200 +21-day slope'][int(p['InpTrendMode'])]
 stop=['ATR14 x'+fmt(p['InpStopATR']), 'original swing with ATR clamp','original chandelier boundary with ATR clamp',fmt(p['InpResearchStopPercent'])+'% price','$'+fmt(p['InpResearchStopPrice'])+' price distance','completed signal candle extreme with ATR clamp'][int(p['InpStopMode'])]
 management=['none','breakeven','ATR trail','chandelier trail','step lock','percentage trail','50% partial +BE'][int(p['InpManagement'])]
 if p['InpManagement']>0:management+=' from '+fmt(p['InpResearchTriggerR'] or (.5 if p['InpManagement']==4 else 1.))+'R'
 if p['InpManagement']==2:management+=' distance '+fmt(p['InpResearchTrailATR'])+'ATR'
 if p['InpManagement']==4:management+=' lock '+fmt(p['InpResearchLockR'])+'R'
 if p['InpManagement']==5:management+=' distance '+fmt(p['InpResearchTrailPercent'])+'%'
 exit=['signal reversal/no TP',fmt(p['InpRewardRisk'])+'R target','adaptive4R/1.5R','no TP/time exit'][int(p['InpExitMode'])]
 side='both' if p['InpAllowLong'] and p['InpAllowShort'] else 'long only' if p['InpAllowLong'] else 'short only'
 session=['all','00–08','07–12','13–21','13–16'][int(p['InpResearchSession'])]
 if p['InpSessionMinuteUTC']>=0:
  m=int(p['InpSessionMinuteUTC']);session=f'exact {m//60:02}:{m%60:02}'
 filt=('ADX14≥'+fmt(p['InpResearchADXMin'],0) if p['InpResearchADXMin'] else 'ADX off')+(' +DI' if p['InpResearchDI'] else ', DI off')
 days=['none','Monday','Friday','Monday+Friday'][int(p['InpResearchSkipDays'])]
 return f'{tf} · {horizon} vote · {trend} · '+('unanimous · ' if p['InpResearchVoteMin'] else '')+('same-direction completed candle · ' if p['InpResearchConfirmCandle'] else '')+f'{stop} · {exit} · {management} · {side} · broker clock {session} · {filt} · excluded {days} · cooldown {int(p["InpResearchCooldownDays"]) or "original"} days · max hold {int(p["InpMaximumHoldDays"]) or "none"} days'
def main():
 comparisons=read('COMPARISON.json');search=read('SEARCH RESULTS.json');selection=read('SELECTION.json')
 expected={(w,v) for w in ['1Y','6M','3M','3Y','5Y','OLDER'] for v in LABELS}
 assert len(comparisons)==len(expected) and {(r['period'],r['variant']) for r in comparisons}==expected,'Incomplete comparisons'
 refs={label:next(r['parameters'] for r in search if r['case'].startswith('PARITY_'+label+'-')) for label in ['NORMAL','FTMO_TARGET']}
 chosen=selection['candidate']['validation']['parameters']
 assert all(r['model']==4 and r['parameters']==(chosen if r['variant']=='CANDIDATE' else refs['NORMAL' if r['variant']=='CURRENT' else 'FTMO_TARGET']) for r in comparisons)
 for r in search:a.independent(a.full(r))
 ids={r['parameter_id'] for r in search};trials=len(ids)
 hashes=read('frozen.json');unchanged=all(a.digest(R.parent/p)==v for p,v in hashes['production'].items());assert unchanged
 robust={}
 for r in comparisons:
  if r['period']=='1Y' or (r['period']=='5Y' and r['variant']=='CANDIDATE'):
   key=r['variant']+'_'+r['period'];robust[key]=a.robustness(a.full(r),trials)
 save('ROBUSTNESS.json',robust)
 save('VERIFICATION.json',dict(audited_current_runs=len(search),distinct_settings=trials,execution_rejected=sum(bool(r.get('disqualified')) for r in search),
  whole_position_cash_and_streak_reconciliation=True,all_native_deal_rows_checked=True,production_hashes_unchanged=True,parity=read('PARITY.json'),qualified_validation=selection['qualified_validation']))
 parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Slow Trend optimisation · research only</title><style>body{background:#081511;color:#e8f5ef;font:16px/1.6 system-ui;margin:0}main{max-width:1300px;padding:36px 24px;margin:auto}h1{font-size:42px;line-height:1.15}h2{margin-top:42px}p{color:#b2c6bd}a,summary{color:#77f5c4}.notice{padding:18px;border:1px solid #a5894d;background:#1c2118;border-radius:12px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th,td{text-align:right;padding:12px;border-bottom:1px solid #24433b;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:#98b6a9}code,pre{background:#132720;padding:8px;white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:auto}svg text{fill:#b2c6bd;font:12px system-ui}details{padding:18px 0;border-bottom:1px solid #24433b}summary{cursor:pointer}@media(max-width:600px){main{padding:24px 14px}h1{font-size:30px}}</style><main><p>CALYX · RESEARCH ONLY · 5 OCTOBER 2026</p><h1>XAU Slow Trend<br>Sequential optimisation</h1><div class="notice">Nothing removed or deployed. No live MT5 chart or account was accessed. BATs, website and EA configurations remain unchanged. Stop after this EA for review.</div>']
 parts.append(f'<p>{trials} distinct settings · {len(search)} audited runs · nominal1% equity risk · USD10,000 · Exness XAUUSD · 150ms. Original upward/minimum lot rounding retained; actual risk can exceed1%. The two references are configured normal1R and FTMO0.5R targets, not verified live-chart inputs. FTMO-target tests use the same nominal1% sizing and are NOT the guarded $50 FTMO portfolio or pass forecasts.</p>')
 parts.append('<h2>Frozen candidate</h2><p>'+html.escape(describe(chosen))+'.</p>')
 parts.append(a.verdict(comparisons,selection))
 parts.append('<p>Selection: development2021-10-05–2024-10-05, then validation2024-10-05–2025-10-05. Frozen before recent candidate tests. Previously seen history is not an untouched holdout. Screens are Model0 generated every tick; Model4 confirmations use real ticks only where available. This is a bounded original-strategy search, not the complete portfolio/prop promotion pipeline.</p>')
 parts.append('<h2>Normal versus FTMO target versus candidate</h2><p>All periods end2026-10-05 exclusive: 1Y starts2025-10-05;6M2026-04-05;3M2026-07-05;3Y2023-10-05;5Y2021-10-05. Older stress2019-10-05–2021-10-05. Each run resets $10,000; overlapping periods are not additive. Net whole-position wins include fees and swaps. Equity DD is native floating equity; daily Sharpe uses sampled equity and sqrt252. Frequency per weekday uses all weekdays in the window, not only days with trades.</p>')
 parts.append(table([row(LABELS[r['variant']]+' · '+r['period'],r) for r in comparisons]))
 curves=[];dds=[]
 for r in [r for r in comparisons if r['period']=='1Y']:
  q=a.full(r);daily,_=a.daily_equity(q)
  curves.append((LABELS[r['variant']],[(t.timestamp(),float(v)) for t,v in daily.items()]))
  dd=100*(daily/daily.cummax()-1);dds.append((LABELS[r['variant']],[(t.timestamp(),float(v)) for t,v in dd.items()]))
  small=[t for t in q['trades'] if t.get('breakeven') and t['net']<0]
  if small:parts.append('<p>'+html.escape(LABELS[r['variant']])+f': {len(small)} losses followed a stop move to entry or better; mean net ${fmt(sum(t["net"] for t in small)/len(small))}. These remain net losses, not wins.</p>')
 parts.append(a.graph(curves,'Recent year · sampled floating equity (USD)'));parts.append(a.graph(dds,'Recent year · daily-close equity drawdown (%)'))
 parts.append('<h2>Older native selection and neighbourhoods</h2><p>Dev eligibility≥60 trades, positive net, PF≥1.10; validation≥20 and PF≥1.15. Prefer PF≥1.20, net wins≥50%, winning run longer than losing run. Execution rejects cannot qualify. Any exploratory seed fallback is listed below and does not weaken final gates.</p>')
 parts.append(table([row(f'Finalist{i+1} · '+kind,r[kind]) for i,r in enumerate(read('NATIVE FINALISTS.json')) for kind in ['development','validation']]))
 for r in read('PLATEAUS.json'):parts.append(f'<p>Neighbourhood {r["finalist"]["parameter_id"]}: {len(r["neighbours"])} points; {fmt(100*r["positive_fraction"],1)}% valid positive neighbours; medianPF {fmt(r["median_pf"],3)}; pass {r["passed"]}.</p>')
 parts.append('<h2>10,000-path robustness</h2><p>Block bootstrap length5, trade shuffle and10/20% omission of whole-position proportional closed returns. Yearly comparisons plus the frozen candidate\'s native full5-year replay (not an overlapping stitched ledger). NOT floating-equity, exact broker lot, margin, elapsed-day or FTMO simulation. Conditional historical resampling, not future-profit probabilities.</p>')
 mc_gate={}
 for label,v in robust.items():
  parts.append('<h3>'+html.escape(label)+'</h3>')
  if v.get('status'):parts.append('<p>'+html.escape(v['limits'])+'</p>');continue
  b=v['bootstrap'];s=v['sharpe_statistics'];stress=v['extra_recorded_cost_stress']
  passed=b['return_p05_pct']>0 and b['pf_p05']>1 and s['deflated_sharpe_pct']>=95 and stress['net_profit']>0
  mc_gate[label]=passed
  parts.append(f'<p>Return P5 / median / P95: {fmt(b["return_p05_pct"])} / {fmt(b["return_p50_pct"])} / {fmt(b["return_p95_pct"])}%. Closed DD P95 {fmt(b["closed_dd_p95_pct"])}%; PF P5 {fmt(b["pf_p05"],3)}; profitable resampled paths {fmt(b["positive_paths_pct"],1)}%; approximate deflated Sharpe {fmt(s["deflated_sharpe_pct"],1)}%. Stated robustness gate: {"PASS" if passed else "FAIL"}.</p>')
  parts.append('<details><summary>Shuffle, omission, costs and uncertainty</summary><pre>'+html.escape(json.dumps({k:x for k,x in v.items() if k!='slippage_measurement'},indent=2))+'</pre><p>'+html.escape(v['slippage_measurement']['note'])+f' Entry quotes matched {v["slippage_measurement"]["matched_entries"]}/{v["slippage_measurement"]["total_entries"]}; observed adverse entry price P95 {fmt(v["slippage_measurement"]["adverse_price_p95"],4)}. Missing quotes or near-zero measured slippage make the extra-cost test weak.</p></details>')
 save('ROBUSTNESS GATES.json',mc_gate)
 if not mc_gate.get('CANDIDATE_5Y',False):parts.append('<div class="notice">Frozen candidate does not pass the stated full-period robustness screen. No live promotion recommendation.</div>')
 parts.append('<h2>All development screens</h2>')
 bycase={r['case']:r for r in search}
 for file in sorted(R.glob('stage-*.json')):
  stage=json.loads(file.read_text());parts.append('<details><summary>'+html.escape(stage['stage'])+f' · {stage["tested"]} settings</summary>')
  fallback=R/('exploratory-'+stage['stage']+'.json')
  if fallback.exists():parts.append('<p>EXPLORATORY SEEDS: no candidate met the original development gate at this stage.</p>')
  parts.append(table([row(c,bycase[c]) for c in stage['all_cases']]))
  parts.append('<pre>'+html.escape(json.dumps([r['parameters'] for r in stage['carry']],indent=2))+'</pre></details>')
 parts.append('<h2>Exact frozen candidate parameters</h2><pre>'+html.escape(json.dumps(chosen,indent=2))+'</pre>')
 failed=[r for r in comparisons if r.get('disqualified')]
 if failed:
  parts.append('<h2>Execution gate warnings</h2><p>REJECTED rows retain genuine realised results, but have broker order/close/modify rejections and cannot qualify. A market-closed rejection is not a crash.</p>')
  for r in failed:
   events=a.csv.DictReader((R/'native'/r['case']/'events.csv').open(encoding='utf-8-sig'))
   counts={}
   for e in events:
    if e['event'].endswith('_failed'):counts[e['event']+' / '+e['note']]=counts.get(e['event']+' / '+e['note'],0)+1
   parts.append('<p>'+html.escape(LABELS[r['variant']]+' '+r['period']+': '+json.dumps(counts))+'</p>')
 parts.append('<h2>Verification and limits</h2><p>Both shipped-binary references passed entry/exit/time/lot/cost parity. Native deal-row and final-cash reconciliation is independent of headline MT5 win counts. Reports, journals, events, exports, compiler hashes, settings and the frozen protocol are retained here. Single-EA accounts: no shared portfolio equity, correlation or FTMO rules replay. No prospective validation, no guarantee, no automatic deployment.</p><p><a href="https://www.metatrader5.com/en/terminal/help/start_advanced/start">Official MT5 testing models</a> · <a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation">Real/generated tick limitations</a></p><p>Await review before Trend Progression.</p></main></html>')
 (R/'Results.html').write_text(''.join(parts),encoding='utf-8')
 print(json.dumps(dict(settings=trials,qualified_validation=selection['qualified_validation'],production_unchanged=unchanged,report=str(R/'Results.html'))))
if __name__=='__main__':main()
