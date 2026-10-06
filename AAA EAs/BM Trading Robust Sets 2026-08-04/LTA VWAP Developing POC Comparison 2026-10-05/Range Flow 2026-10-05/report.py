"""Past-only gate audit and evidence report, without selecting/tuning settings."""
from pathlib import Path
import importlib.util,sys,json,html
import numpy as np
import pandas as pd
import run as extension
R=Path(__file__).resolve().parent;P=R.parent;n=extension.n
KEYS=['RANGE_OFF_3Y','RANGE_DAILY_3Y','RANGE_COMBO_3Y'];COLORS=['#93b9ff','#e8c66d','#8df5d2']
rows=[(k,json.loads((R/'native'/k/'results.json').read_text()),COLORS[i]) for i,k in enumerate(KEYS)]
assert json.loads((R/'PARITY.json').read_text())['passed']
assert extension.freeze()==json.loads((R/'build.json').read_text())['frozen']

def gate_audit(tag,x):
 gates=pd.read_csv(R/'native'/tag/'gate.csv');days=pd.read_csv(R/'native'/tag/'daily.csv')
 if not extension.CASES[tag]['range_mode']:
  assert gates.empty
  return dict(mode=0,ungated=True)
 hours=pd.read_csv(R/'native'/tag/'adx.csv').set_index('bar_epoch')
 assert len(days)>252 and not days.bar_epoch.duplicated().any()
 assert (days.known_at_epoch>days.bar_epoch).all()
 states={};checked_probabilities=0
 for asof,g in gates.groupby('daily_asof'):
  past=days[days.known_at_epoch<=asof].tail(2600)
  assert len(past)>20+252
  latest=past.iloc[-1];ret=latest.close/past.iloc[-21].close-1
  s=2 if ret>.05 else 0 if ret<-.05 else 1
  assert (g.closed_d1_epoch==latest.bar_epoch).all()
  assert np.max(np.abs(g.rolling_return-ret))<1e-9
  assert (g.state==s).all() and (g.daily_asof<=g.epoch).all()
  probs=g[['p_bear','p_sideways','p_bull']].to_numpy()
  assert np.all(probs>=0) and np.all(probs<=1) and np.max(np.abs(probs.sum(axis=1)-1))<1e-8
  if len(past)==2600:
   values=past.close.to_numpy()[::-1];rs=values[:-20]/values[20:]-1
   labels=np.where(rs>.05,2,np.where(rs<-.05,0,1));counts=np.zeros((3,3))
   for newer in range(len(labels)-2,0,-1):counts[labels[newer+1],labels[newer]]+=1
   expected=counts[s]/counts[s].sum()
   assert np.max(np.abs(probs-expected))<1e-8
   checked_probabilities+=len(g)
  states[int(asof)]=s
 ready=(gates.h1_epoch>0)&(gates.h1_epoch+3600<=gates.epoch)&(gates.adx>=0)
 expected=(gates.state==1)
 if extension.CASES[tag]['range_mode']==2:expected=expected&ready&(gates.adx<20)
 assert np.array_equal(gates.allow.to_numpy(),expected.astype(int).to_numpy())
 for row in gates.itertuples():
  if row.h1_epoch in hours.index:
   q=hours.loc[row.h1_epoch]
   assert q.known_at_epoch<=row.epoch
   assert abs(q.adx-row.adx)<1e-7
  elif extension.CASES[tag]['range_mode']==2 and row.allow:raise AssertionError('Missing independent completed H1 ADX audit')
 for t in x['trades']:
  side=1 if t['side']=='Long' else -1
  found=gates[(gates.epoch<=t['open_epoch'])&(gates.epoch>=t['open_epoch']-5)&(gates.dir==side)&(gates.allow==1)]
  assert len(found)==1,(tag,t['open_time'])
 return dict(mode=extension.CASES[tag]['range_mode'],candidate_gate_checks=len(gates),allowed_checks=int(gates.allow.sum()),
  rejected_checks=int((gates.allow==0).sum()),all_entries_closed_D1_sideways=True,closed_H1_ADX_verified=True,
  matrix_probabilities_checked_when_full_history_export_available=checked_probabilities,gate_times_and_classifications_recomputed=True)

def segment(x,start,end):
 a=n.epoch(start);b=n.epoch(end);ts=[t for t in x['trades'] if a<=t['close_epoch']<b]
 m=extension.old_metrics(ts)
 opening=10000+sum(d['cash_flow'] for d in x['ledger'] if d['epoch']<a)
 cash=sum(d['cash_flow'] for d in x['ledger'] if a<=d['epoch']<b)
 return dict(start=start,end_exclusive=end,positions=m['trades'],cash_return_pct=100*cash/opening,cash_flow_usd=round(cash,2),
  pf=m['pf'],win_rate=m['win_rate'],win_streak=m['win_streak'],loss_streak=m['loss_streak'],
  opening_balance=opening,positions_crossing_into_segment=sum(t['open_epoch']<a for t in ts))

audits={};summary=[];yearly=[];recent=[]
for tag,x,color in rows:
 assert x['window']==[extension.START,extension.END] and x['inputs']['InpFlowMode']=='1'
 assert abs(sum(t['net'] for t in x['trades'])-x['native']['net_profit'])<.021
 assert x['counters']['close_failed']==0
 failures=[v for v in n.csvrows(R/'native'/tag/'events.csv') if v['event']=='order_failed']
 assert len(failures)==x['counters']['order_failed'] and all(v['note']=='market closed' for v in failures)
 audits[tag]=dict(gate=gate_audit(tag,x),deals=n.native_deal_audit(R/'native'/tag/'report.htm',n.csvrows(R/'native'/tag/'deals.csv')))
 boundary=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in x['trades'])
 summary.append(dict(case=tag,label=x['label'],**x['metrics'],native_equity_dd=x['native']['equity_dd_pct'],
  native_sharpe=x['native']['sharpe_ratio'],quality=x['native']['history_quality'],boundary_liquidations=boundary,
  rejected_market_closed_attempts=len(failures)))
 for a,b in [('2023.10.05','2024.10.05'),('2024.10.05','2025.10.05'),('2025.10.05','2026.10.05')]:
  yearly.append(dict(case=tag,**segment(x,a,b)))
 recent.append(dict(case=tag,**segment(x,'2026.07.05','2026.10.05')))
 pd.DataFrame([{k:v for k,v in t.items() if k not in ['audit','exit_comments']} for t in x['trades']]).to_csv(R/(tag+' Trades.csv'),index=False)
 ys=[y for y in yearly if y['case']==tag]
 assert sum(y['positions'] for y in ys)==len(x['trades'])
 assert abs(sum(y['cash_flow_usd'] for y in ys)-x['native']['net_profit'])<.021
pd.DataFrame(summary).to_csv(R/'Comparison.csv',index=False)
pd.DataFrame(yearly).to_csv(R/'Yearly.csv',index=False)
pd.DataFrame(recent).to_csv(R/'Recent.csv',index=False)
n.save(R/'SUMMARY.json',dict(comparison=summary,yearly=yearly,last_three_months=recent))
n.save(R/'verification.json',dict(ok=True,parity=json.loads((R/'PARITY.json').read_text()),native_audits=audits,
 whole_positions_including_partials_and_costs=True,production_hashes_unchanged=True,no_deployment=True,range_unit_tests=16))

sys.modules['run']=n
sp=importlib.util.spec_from_file_location('lta_range_charts',P/'report.py');plots=importlib.util.module_from_spec(sp);sp.loader.exec_module(plots);plots.R=R
def esc(v):return html.escape(str(v))
def f(v,d=2):return '—' if v is None else f'{v:,.{d}f}'
def table(headers,data):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in data)+'</tbody></table></div>'
style='''*{box-sizing:border-box}body{margin:0;background:#06110e;color:#ebfaf5;font:15px/1.65 Arial,sans-serif}main{max-width:1320px;margin:auto;padding:40px 24px 75px}h1{font-size:clamp(30px,5vw,52px);line-height:1.15}h2{font-size:24px}p,li{color:#afd0c4}a{color:#8df5d2}section,details{background:#0b1d16;border:1px solid #25483b;border-radius:14px;padding:22px;margin:22px 0}.kicker{color:#8df5d2;font-size:12px;letter-spacing:2px}.notice{background:#251b13;border:1px solid #765235}.scroll,.plot{overflow:auto;max-width:100%}table{border-collapse:collapse;min-width:100%;font-size:14px;white-space:nowrap}th,td{text-align:right;padding:12px 14px;border-bottom:1px solid #25483b}th:first-child,td:first-child{text-align:left}th{color:#9bbdaf}svg{width:100%;height:auto;display:block;min-width:900px}svg text{fill:#bdd9cc;font-size:13px}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px}.legend i{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:6px}summary{cursor:pointer;color:#8df5d2}.small{font-size:13px}p,a,h1,h2,li{overflow-wrap:anywhere}@media(max-width:650px){main{padding:24px 12px}section,details{padding:16px}}'''
page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTA New Flow · Range Gate</title><style>{style}</style></head><body><main><div class="kicker">CALYX · NEW FLOW ONLY · FROZEN RANGE-GATE RESEARCH</div><h1>The new M5 flow.<br>Only in ranging markets.</h1><p>05 October 2023–04 October 2026 inclusive. USD10,000 initial capital; 1% intended current-equity risk; Exness XAUUSD CFD; Model4 / 150ms execution delay, broker spread, commission and swap.</p>'
page+='<section class="notice"><h2>An exploratory filter test, not an optimized winner.</h2><p>The original LTA entry is not required. Only the range gate changes between these matched cases. All stops, targets, partial/BE management and parent direction/safety controls stay unchanged. No parameters were selected from this run, and the history has already been inspected.</p></section>'
page+='<section><h2>Full three-year comparison</h2>'+table(['Version','Positions','Return','Net PF','Win rate','Native equity DD','Daily equity Sharpe','Max W / L','Average win / loss'],[[s['label'],s['trades'],f(s['return_pct'])+'%',f(s['pf'],3),f(s['win_rate'],1)+'%',f(s['native_equity_dd'])+'%',f(s['sharpe_daily_equity']),str(s['win_streak'])+' / '+str(s['loss_streak']),f(s['avg_win'])+' / '+f(s['avg_loss'])] for s in summary])+'<p>Each row is an independent compounded account, not a shared portfolio. Whole positions count once, including partial exits and all costs. Primary drawdown is native floating-equity drawdown; daily-equity Sharpe uses five-minute sampled day-end values, annualized with √252.</p></section>'
page+=plots.chart(rows,'balance','Closed cash balance — separate strategy tests')+plots.chart(rows,'equity','Sampled floating equity — separate strategy tests')
page+='<p class="small">Cash curves step at deal cash-flow events. Equity is sampled every five minutes and reduced to daily first/last/min/max for display; it cannot reproduce all intrabar excursions.</p>'
page+='<section><h2>The fixed range definition</h2><ol><li>Completed D1 return over20 sessions within ±5% → Sideways. At least252 prior labels required. Daily regime is updated only at a new broker D1 bar.</li><li>Main requested case also needs completed H1 ADX(14)&lt;20. Daily-only is a diagnostic ablation, not a searched alternative.</li><li>Gate only new entries. Trades already open retain their original management even if the market changes regime.</li></ol><p>Transition probabilities are computed from past completed labels for diagnostics only; no forecast-probability threshold is used. Sideways based on return is a coarse proxy, and low ADX measures weak trend strength, not a guarantee of a stable range. The regime skill’s helper script was absent, so the existing native regime helper implements its fixed default classification.</p></section>'
page+='<section><h2>Yearly segments of each continuous account</h2>'+table(['Version','Dates (end exclusive)','Positions closed','Cash return','Position PF','Win rate','Max W / L'],[[extension.CASES[y['case']]['label'],y['start']+' → '+y['end_exclusive'],y['positions'],f(y['cash_return_pct'])+'%',f(y['pf'],3),f(y['win_rate'],1)+'%',str(y['win_streak'])+' / '+str(y['loss_streak'])] for y in yearly])+'<p class="small">Segments retain accumulated equity and strategy state. Cash return uses exact deal cash flows / segment opening balance; PF, win rate and streaks use complete positions by final exit. This is not a set of fresh annual reruns.</p></section>'
page+='<section><h2>Last three months within the continuous run</h2>'+table(['Version','Positions closed','Cash return','PF','Win rate','Max W / L','Cross-boundary positions'],[[extension.CASES[y['case']]['label'],y['positions'],f(y['cash_return_pct'])+'%',f(y['pf'],3),f(y['win_rate'],1)+'%',str(y['win_streak'])+' / '+str(y['loss_streak']),y['positions_crossing_into_segment']] for y in recent])+'<p class="small">05 July–04 October2026 inclusive. Small samples must not be interpreted as proof of improvement.</p></section>'
old=json.loads((P/'Three Year 2026-10-05/SUMMARY.json').read_text())
page+=f'<section><h2>Earlier LTA AND flow reference</h2><p>The previous combined-entry variant returned {f(old["metrics"]["return_pct"])}%, PF {f(old["metrics"]["pf"],3)}, win {f(old["metrics"]["win_rate"],1)}%, equity DD {f(old["native"]["equity_dd_pct"])}% on235 positions. Its entry requirement and structural stop differ, so it is context—not the matched control for the range filter.</p><p><a href="../Three%20Year%202026-10-05/Results.html">Earlier three-year AND report</a></p></section>'
for tag,x,color in rows:
 ts=x['trades'];m=x['metrics'];boundary=next(s['boundary_liquidations'] for s in summary if s['case']==tag)
 page+='<details><summary>'+esc(x['label'])+' — '+str(len(ts))+' whole positions</summary>'+table(['Entry','Final exit','Side','Lots','Entry price','Initial SL','TP','Net USD','Partial / BE'],[[t['open_time'],t['close_time'],t['side'],f(t['volume']),f(t['open_price'],3),f(t['sl'],3),f(t['tp'],3),f(t['net']),str(t['partial'])+' / '+str(t['breakeven'])] for t in ts])
 rejected=next(s['rejected_market_closed_attempts'] for s in summary if s['case']==tag)
 page+=f'<p>{m["partials"]} partials; {m["breakevens"]} BE moves; {int(x["counters"]["modify_failed"])} recovered BE rejections; {boundary} end-of-test liquidations included; {rejected} market-closed entry attempts rejected (not positions). Actual initial-stop risk / intended budget reached {f(m["max_actual_risk_budget_ratio"])}×. Broker minimum/ceil lots and gaps mean 1% is not a hard loss cap.</p><p><a href="native/{tag}/report.htm">Native report</a> · <a href="native/{tag}/inputs.set">Exact SET</a> · <a href="native/{tag}/gate.csv">Range-gate audit</a> · <a href="native/{tag}/daily.csv">Completed D1 closes</a>'
 if extension.CASES[tag]['range_mode']:page+=f' · <a href="native/{tag}/adx.csv">Completed H1 ADX</a>'
 page+='</p></details>'
page+='<section><h2>Verification and limitations</h2><p>Ungated off-switch exactly matches all254 prior one-year new-flow positions, including times, prices, lots and costs. Range classification, completed-bar timestamps and admitted entries are independently checked. Native deals and complete-position net profit reconcile. Compile: zero errors/warnings. Sixteen range/source tests and fifteen original-rule tests passed. Original production/source hashes remain unchanged. Analysis permits only documented market-closed entry rejections; no artificial fills or strategy changes were made.</p><p>Native history quality: '+esc(summary[0]['quality'])+'. Real ticks begin01 January2026; older ticks are generated. VWAP and volume profile use the broker volume proxy, not centralized exchange volume. No independent holdout, Monte Carlo, walk-forward parameter search or deployment was performed.</p><p><a href="Comparison.csv">Comparison CSV</a> · <a href="Yearly.csv">Yearly CSV</a> · <a href="Recent.csv">Recent CSV</a> · <a href="SUMMARY.json">Summary</a> · <a href="verification.json">Verification</a> · <a href="PARITY.json">Off-switch parity</a> · <a href="PROTOCOL.md">Frozen protocol</a> · <a href="ANALYSIS_EXCEPTION.json">Broker rejection analysis note</a></p></section></main></body></html>'
(R/'Results.html').write_text(page,encoding='utf-8')
print(json.dumps(dict(comparison=summary,yearly=yearly,recent=recent,verification=audits),indent=2),flush=True)
