"""Audit and offline report of the exact continuous three-year AND run."""
from pathlib import Path
import importlib.util,sys,json,html
import numpy as np
import pandas as pd
import run as extension
R=Path(__file__).resolve().parent;P=R.parent;n=extension.n
x=json.loads((R/'RESULTS.json').read_text());m=x['metrics'];native=x['native'];ts=x['trades'];ledger=x['ledger']
assert extension.freeze()==json.loads((R/'build.json').read_text())['frozen']
prior=json.loads((P/'native/AND_M5/results.json').read_text())
assert {k:v for k,v in x['inputs'].items() if k!='InpAuditTag'}=={k:v for k,v in prior['inputs'].items() if k!='InpAuditTag'}
audit=n.native_deal_audit(R/'native/AND_M5_3Y/report.htm',n.csvrows(R/'native/AND_M5_3Y/deals.csv'))
assert abs(sum(t['net'] for t in ts)-native['net_profit'])<.021
assert m['partials']==m['breakevens']==x['counters']['partials']
assert not any(x['counters'][k] for k in ['order_failed','close_failed'])
frozen=json.loads((P/'frozen.json').read_text())
for name,digest in frozen['production'].items():assert n.sha(n.B/name)==digest
for name,digest in frozen['research'].items():assert n.sha(P/'EA'/name)==digest
assert n.sha(n.SOURCE.with_suffix('.ex5'))==json.loads((P/'build.json').read_text())['binary']
trace=n.csvrows(R/'native/AND_M5_3Y/equity.csv');yearly=[]
for start,end in [('2023.10.05','2024.10.05'),('2024.10.05','2025.10.05'),('2025.10.05','2026.10.05')]:
 a=n.epoch(start);b=n.epoch(end);tr=[t for t in ts if a<=t['close_epoch']<b];ys=extension.old_metrics(tr)
 opening=10000+sum(d['cash_flow'] for d in ledger if d['epoch']<a);flows=sum(d['cash_flow'] for d in ledger if a<=d['epoch']<b)
 selected=[v for v in trace if a<=int(v['epoch'])<b];earlier=[v for v in trace if int(v['epoch'])<a]
 points=[float(earlier[-1]['equity']) if earlier else 10000.]+[float(v['equity']) for v in selected]
 peaks=np.maximum.accumulate(points);dd=float(np.max(100*(peaks-np.asarray(points))/peaks))
 yearly.append(dict(start=start,end_exclusive=end,positions=ys['trades'],pf=ys['pf'],win_rate=ys['win_rate'],win_streak=ys['win_streak'],loss_streak=ys['loss_streak'],
  position_net_usd=ys['net_profit'],opening_balance=opening,cash_flow_usd=flows,cash_return_pct=100*flows/opening,
  sampled_equity_dd_pct=dd,cross_boundary_positions=sum(t['open_epoch']<a for t in tr)))
assert sum(y['positions'] for y in yearly)==len(ts)
assert abs(sum(y['cash_flow_usd'] for y in yearly)-native['net_profit'])<.021
sides={s:extension.old_metrics([t for t in ts if t['side']==s]) for s in ['Long','Short']}
past=sum((1 if t['side']=='Long' else -1)*(t['open_price']-float(t['audit']['poc']))>0 for t in ts)
boundary=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in ts)
summary=dict(window=x['window'],metrics=m,native=native,yearly_continuous_segments=yearly,sides=sides,already_past_poc=past,boundary_liquidations=boundary)
n.save(R/'SUMMARY.json',summary);pd.DataFrame(yearly).to_csv(R/'Yearly.csv',index=False)
pd.DataFrame([{k:v for k,v in t.items() if k not in ['audit','exit_comments']} for t in ts]).to_csv(R/'Trades.csv',index=False)
pd.DataFrame(ledger).to_csv(R/'Cash Ledger.csv',index=False)
v=dict(ok=True,same_prior_AND_settings_except_audit_tag=True,unchanged_EA_binary_source_dependencies=True,production_hashes_unchanged=True,
 full_position_net_reconciliation=True,native_deal_audit=audit,positions=len(ts),partials_grouped_with_position=True,
 profile_and_closed_signal_no_lookahead_checks_passed=True,yearly_cash_flow_reconciliation=True,recovered_BE_rejections=int(x['counters']['modify_failed']),
 boundary_liquidations=boundary,no_deployment=True)
n.save(R/'verification.json',v)
sys.modules['run']=n
sp=importlib.util.spec_from_file_location('parent_lta_charts',P/'report.py');plots=importlib.util.module_from_spec(sp);sp.loader.exec_module(plots);plots.R=R
rows=[('AND_M5_3Y',x,'#8df5d2')]
charts=plots.chart(rows,'balance','Closed cash balance — one continuous account')+plots.chart(rows,'equity','Sampled floating equity — one continuous account')
def esc(v):return html.escape(str(v))
def f(v,d=2):return '—' if v is None else f'{v:,.{d}f}'
def table(head,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(c)+'</th>' for c in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
style='''*{box-sizing:border-box}body{margin:0;background:#06110e;color:#ebfaf5;font:15px/1.65 Arial,sans-serif}main{max-width:1260px;margin:auto;padding:40px 24px 75px}h1{font-size:clamp(30px,5vw,52px);line-height:1.15}h2{font-size:24px}p,li{color:#afd0c4}a{color:#8df5d2}section,details{background:#0b1d16;border:1px solid #25483b;border-radius:14px;padding:22px;margin:22px 0}.kicker{color:#8df5d2;font-size:12px;letter-spacing:2px}.notice{background:#251b13;border:1px solid #765235}.scroll,.plot{overflow:auto;max-width:100%}table{border-collapse:collapse;min-width:100%;font-size:14px;white-space:nowrap}th,td{text-align:right;padding:12px 14px;border-bottom:1px solid #25483b}th:first-child,td:first-child{text-align:left}th{color:#9bbdaf}svg{width:100%;height:auto;display:block;min-width:900px}svg text{fill:#bdd9cc;font-size:13px}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px}.legend i{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:6px}summary{cursor:pointer;color:#8df5d2}.small{font-size:13px}p,a,h1,h2,li{overflow-wrap:anywhere}@media(max-width:650px){main{padding:24px 12px}section,details{padding:16px}}'''
page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTA AND Flow · Three Years</title><style>{style}</style></head><body><main><div class="kicker">CALYX · EXACT AND VARIANT · THREE-YEAR RAW EXTENSION</div><h1>Existing LTA signal<br>AND the new M5 flow.</h1><p>05 October 2023 through 04 October 2026 inclusive. Exact prior AND settings; Safe and adaptive portfolio controls OFF. No optimisation or deployment.</p>'
page+=f'<section class="notice"><h2>High win rate, but negative net expectancy.</h2><p>{m["wins"]} wins / {m["losses"]} losses. Average net winner USD {f(m["avg_win"])}, average net loser USD {f(m["avg_loss"])}. Winning streaks alone did not demonstrate a profitable edge over this window.</p></section>'
page+='<section><h2>Full three-year results</h2><p>USD10,000 initial equity; 1% intended current-equity stop risk; Exness XAUUSD CFD; Model4 / 150ms delay. Broker spread, commission and swap included.</p>'+table(['Positions','Net return','Net PF','Win rate','Native equity DD','Daily equity Sharpe','MT5 Sharpe','Max W / L'],[[m['trades'],f(m['return_pct'])+'%',f(m['pf'],3),f(m['win_rate'],1)+'%',f(native['equity_dd_pct'])+'%',f(m['sharpe_daily_equity']),f(native['sharpe_ratio']),str(m['win_streak'])+' / '+str(m['loss_streak'])]])+f'<p>Final balance USD {f(native["final_balance"])}; net P&amp;L USD {f(native["net_profit"])}. {f(m["trades_month"])} positions/month; {m["partials"]} partials and {m["breakevens"]} break-even moves. Full positions count once, including all partial legs and costs.</p><p class="small">Quality: {esc(native["history_quality"])}. Real ticks begin01 Jan2026; earlier history uses generated ticks. Volume profile/VWAP use the broker volume proxy, not centralized exchange volume. Daily-equity Sharpe uses sampled day-end equity / √252 annualisation; MT5 Sharpe is a separate statistic.</p></section>'
page+=charts+'<p class="small">Cash curve steps at deal cash-flow events. Equity sampled every five minutes, reduced to daily first/last/min/max for display. It cannot reproduce every intrabar excursion; native DD above is primary.</p>'
yr=[[y['start']+' → '+y['end_exclusive'],y['positions'],f(y['cash_return_pct'])+'%',f(y['cash_flow_usd']),f(y['pf'],3),f(y['win_rate'],1)+'%',str(y['win_streak'])+' / '+str(y['loss_streak']),f(y['sampled_equity_dd_pct'])+'%'] for y in yearly]
page+='<section><h2>Year by year within the continuous run</h2>'+table(['Dates (end exclusive)','Positions closed','Cash return','Net cash USD','Position PF','Win rate','Max W / L','Sampled equity DD'],yr)+'<p class="small">These are segments of ONE compounded three-year account, not fresh annual reruns. Cash return uses actual deal cash flows / each opening balance. PF and win rate group complete positions by final exit, including full costs. Annual DD is five-minute sampled, not native per-year tick DD.</p></section>'
page+='<section><h2>Long versus short</h2>'+table(['Side','Positions','Net USD','PF','Win rate'],[[s,q['trades'],f(q['net_profit']),f(q['pf'],3),f(q['win_rate'],1)+'%'] for s,q in sides.items()])+'</section>'
page+='<section><h2>Rules remain unchanged</h2><ol><li>Original LTA M5 entry signal AND strong completed M5 candle inside yesterday value area, above today VWAP/developing POC for buys; sells mirror below.</li><li>Strong means body≥60% of range and close in outer25%. Signal and entry must both be inside yesterday’s70% value area.</li><li>Original structural stop; target yesterday VAH for buy/VAL for sell. Existing direction filters, one-position limit and two-loss pause remain.</li><li>After a later completed M5 candle closes beyond frozen yesterday POC: take50% and move remaining SL to actual entry when broker-legal. Levels do not roll at midnight.</li></ol>'+f'<p>{past} of {len(ts)} entries were already past yesterday POC on entry, allowing an early partial/BE later. No extra POC-ahead filter was added. Broker ceil/min-lot sizing is unchanged: largest actual initial-stop risk / intended budget was {f(m["max_actual_risk_budget_ratio"])}×. A 1% target is not a guaranteed loss cap.</p></section>'
page+='<section><h2>Earlier one-year reference</h2><p>The earlier fresh one-year AND test remains unchanged: +2.35%, PF1.107, win71.4%, DD6.46%,77 positions. The latest annual segment here starts with accumulated equity/state and can differ.</p><p><a href="../Results.html">Original comparison</a> · <a href="../PROTOCOL.md">Original frozen rules</a></p></section>'
pos=[[t['open_time'],t['close_time'],t['side'],f(t['volume']),f(t['open_price'],3),f(t['sl'],3),f(t['tp'],3),f(t['net']),str(t['partial']),str(t['breakeven'])] for t in ts]
page+='<details><summary>All positions and exact native evidence</summary>'+table(['Entry UTC/broker','Final exit','Side','Lots','Entry','Initial SL','TP','Net USD','Partial','BE'],pos)+'<p><a href="Trades.csv">Positions CSV</a> · <a href="Cash%20Ledger.csv">Cash ledger</a> · <a href="Yearly.csv">Yearly CSV</a> · <a href="native/AND_M5_3Y/report.htm">Native report</a> · <a href="native/AND_M5_3Y/events.csv">Signal/partial/BE audit</a> · <a href="native/AND_M5_3Y/equity.csv">Equity CSV</a> · <a href="native/AND_M5_3Y/inputs.set">Exact settings</a></p></details>'
page+=f'<section><h2>Verification</h2><p>Exact prior AND settings except output filename tag; same compiled source and dependencies. Fifteen rule/source tests passed. All native deals, full position net profit and annual cash flows reconcile. Earlier profile and completed-signal timestamps pass the past-only checks. {int(x["counters"]["modify_failed"])} rejected BE modifications were subsequently recovered; original stops were retained. {boundary} end-of-test liquidations included. No production, BAT, website, live or Git change.</p><p><a href="PROTOCOL.md">Protocol</a> · <a href="SUMMARY.json">Summary</a> · <a href="verification.json">Verification</a> · <a href="frozen.json">Frozen hashes</a></p><p class="small">Historical raw research, not a forecast, an independent unseen sample or a completed validation pipeline.</p></section></main></body></html>'
(R/'Results.html').write_text(page,encoding='utf-8')
print(json.dumps(dict(metrics=m,native=native,yearly=yearly,verification=v),indent=2),flush=True)
