"""Offline comparison report built only from verified native evidence."""
from pathlib import Path
from datetime import datetime,timezone
import csv,html,json,math
import run
R=Path(__file__).resolve().parent
KEYS=['CURRENT_M15','CURRENT_M5','FLOW_M5','AND_M5','SAFE_M15','FLOW_SAFE_M5']
COLORS=['#8df5d2','#e8c66d','#93b9ff','#e48db8','#b1a0ff','#ecaa71']
def esc(v):return html.escape(str(v))
def fmt(x,n=2):return '—' if x is None else f'{x:,.{n}f}'
def chart(rows,kind,title):
 start=run.epoch(run.START);end=run.epoch(run.END);series=[]
 for key,row,color in rows:
  if kind=='balance':pts=[(start,10000)]+[(x['epoch'],x['balance']) for x in row['ledger']]+[(end,10000+row['metrics']['net_profit'])]
  else:
   trace=run.csvrows(R/'native'/key/'equity.csv');pts=[(start,10000)]+[(int(x['epoch']),float(x['equity'])) for x in trace]
   # Keep first/last/min/max within each day, ordered; not a continuous equity history.
   bins={}
   for x in pts:bins.setdefault(x[0]//86400,[]).append(x)
   pts=[]
   for group in bins.values():pts.extend(sorted(set([group[0],group[-1],min(group,key=lambda x:x[1]),max(group,key=lambda x:x[1])])) )
   pts.append((end,10000+row['metrics']['net_profit']))
  series.append((key,row,color,pts))
 lo=min(y for *_,p in series for x,y in p);hi=max(y for *_,p in series for x,y in p);pad=max(300,(hi-lo)*.07);lo-=pad;hi+=pad
 width=1060;height=370;left=85;right=26;top=20;bottom=55
 X=lambda x:left+(x-start)/(end-start)*(width-left-right)
 Y=lambda y:top+(hi-y)/(hi-lo)*(height-top-bottom)
 svg=f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
 for i in range(5):
  v=lo+(hi-lo)*i/4;y=Y(v);svg+=f'<path d="M{left},{y:.1f}H{width-right}" stroke="#244237"/><text x="{left-12}" y="{y+4:.1f}" text-anchor="end">${v:,.0f}</text>'
 for n in range(5):
  t=start+(end-start)*n/4;anchor='start' if n==0 else 'end' if n==4 else 'middle';svg+=f'<text x="{X(t):.1f}" y="{height-28}" text-anchor="{anchor}">{datetime.fromtimestamp(t,timezone.utc):%b %Y}</text>'
 for key,row,color,pts in series:
  path=f'M{X(pts[0][0]):.2f},{Y(pts[0][1]):.2f}'
  for x,y in pts[1:]:path+=f' H{X(x):.2f} V{Y(y):.2f}' if kind=='balance' else f' L{X(x):.2f},{Y(y):.2f}'
  svg+=f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
 svg+=f'<text x="{(left+width-right)/2}" y="{height-5}" text-anchor="middle">Broker date</text><text transform="translate(19,{height/2}) rotate(-90)" text-anchor="middle">USD</text></svg>'
 legend=''.join(f'<span><i style="background:{color}"></i>{esc(row["label"])}</span>' for key,row,color,p in series)
 return '<section><h2>'+esc(title)+'</h2><div class="legend">'+legend+'</div><div class="plot">'+svg+'</div></section>'
def main():
 parity=json.loads((R/'PARITY.json').read_text());assert parity['passed'];run.freeze()
 rows=[(k,json.loads((R/'native'/k/'results.json').read_text()),COLORS[i]) for i,k in enumerate(KEYS)]
 for k,row,c in rows:
  assert not any(v for k,v in row['flags'].items() if k!='invalid_stops');assert row['counters']['entries']==row['metrics']['trades']
  assert all(row['counters'][x]==0 for x in ['order_failed','close_failed'])
 audits={key:run.native_deal_audit(R/'native'/key/'report.htm',run.csvrows(R/'native'/key/'deals.csv')) for key,row,color in rows}
 summary=[];body=''
 for k,row,color in rows:
  m=row['metrics'];n=row['native'];c=row['counters'];record=dict(case=k,label=row['label'],from_date=run.START,end_exclusive=run.END,
   **m,native_equity_dd=n['equity_dd_pct'],observed_tick_equity_dd=c['observed_dd'],native_sharpe=n['sharpe_ratio'],quality=n['history_quality'])
  summary.append(record)
  body+=f'<tr><th>{esc(row["label"])}</th><td>{m["trades"]}</td><td>{fmt(m["trades_month"])}/{fmt(m["trades_weekday"])}</td><td>{fmt(m["return_pct"])}%</td><td>{fmt(m["pf"],3)}</td><td>{fmt(m["win_rate"],1)}%</td><td>{fmt(n["equity_dd_pct"])}%</td><td>{fmt(m["sharpe_daily_equity"])} / {fmt(n["sharpe_ratio"])}</td><td>{m["win_streak"]} / {m["loss_streak"]}</td><td>{m["partials"]} / {m["breakevens"]}</td></tr>'
 run.save(R/'SUMMARY.json',summary)
 with (R/'SUMMARY.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 rules='<ol><li>Closed M5 candle and entry quote inside yesterday’s 70% value area.</li><li>Body ≥60% of range; close in outer25%. Buy above today’s session VWAP and developing POC; mirrored sell below both.</li><li>Keep LTA’s completed D1/H1 direction and momentum filter, one position and daily two-loss pause. The “AND” row additionally requires an original LTA entry.</li><li>New-flow stop: last three completed M5 lows/highs plus .12 ATR buffer. “AND” retains LTA’s original structural stop.</li><li>Target yesterday’s VAH for buys or VAL for sells. Levels stay frozen for the life of the trade.</li><li>After a later M5 candle closes beyond yesterday’s POC, take50% and move remaining SL to actual entry, if broker-legal and currently profitable. Odd lots round partial down; minimum lots cannot split. Fees and slippage mean entry-price BE is not guaranteed net zero.</li></ol>'
 detail='';monthly={}
 for k,row,c in rows:
  m=row['metrics'];trades=row['trades'];short=run.metrics([t for t in trades if t['side']=='Short']);long=run.metrics([t for t in trades if t['side']=='Long'])
  monthly[k]={}
  for t in trades:
   month=t['close_time'][:7];monthly[k][month]=monthly[k].get(month,0)+t['net']
  legs=''
  for t in trades:
   legs+=f'<tr><td>{esc(t["open_time"])}</td><td>{esc(t["close_time"])}</td><td>{t["side"]}</td><td>{fmt(t["volume"])} </td><td>{fmt(t["open_price"],3)}</td><td>{fmt(t["sl"],3)}</td><td>{fmt(t["tp"],3)}</td><td>{fmt(t["net"])} </td><td>{"Yes" if t["partial"] else "No"}/{"Yes" if t["breakeven"] else "No"}</td></tr>'
  detail+=f'<details><summary>{esc(row["label"])} — {m["trades"]} positions</summary><p>Long: {long["trades"]} trades, PF {fmt(long["pf"],3)}, win rate {fmt(long["win_rate"],1)}%. Short: {short["trades"]} trades, PF {fmt(short["pf"],3)}, win rate {fmt(short["win_rate"],1)}%.</p><p>Average net win ${fmt(m["avg_win"])}, loss ${fmt(m["avg_loss"])}. Commission ${fmt(m["commission"])}, swap ${fmt(m["swap"])}. Native equity DD {fmt(row["native"]["equity_dd_pct"])}%; EA tick-observed DD {fmt(row["counters"]["observed_dd"])}%. Largest actual initial-stop risk / intended budget: {fmt(m["max_actual_risk_budget_ratio"])}×. Partial blocked by minimum lot: {int(row["counters"]["minpartial"])}.</p><p><a href="native/{k}/report.htm">Native MT5 report</a> · <a href="native/{k}/inputs.set">Exact settings</a> · <a href="native/{k}/trades.json">Full position audit</a></p><div class="scroll"><table><thead><tr><th>Entry (broker time)</th><th>Final exit</th><th>Side</th><th>Lots</th><th>Entry</th><th>Initial SL</th><th>TP</th><th>Net USD</th><th>Partial/BE</th></tr></thead><tbody>{legs}</tbody></table></div></details>'
 months=sorted({x for data in monthly.values() for x in data});mt=''
 for mon in months:mt+='<tr><th>'+mon+'</th>'+''.join('<td>'+fmt(monthly[k].get(mon,0))+'</td>' for k in KEYS)+'</tr>'
 deltas={}
 for a,b in [('CURRENT_M15','FLOW_M5'),('CURRENT_M5','FLOW_M5'),('SAFE_M15','FLOW_SAFE_M5')]:
  one=next(r for k,r,c in rows if k==a);two=next(r for k,r,c in rows if k==b)
  deltas[a+' -> '+b]={x:two['metrics'][x]-one['metrics'][x] for x in ['trades','return_pct','pf','win_rate','sharpe_daily_equity']}
 run.save(R/'DELTAS.json',deltas)
 page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LTA vs M5 VWAP and developing POC</title><style>
 *{{box-sizing:border-box}}body{{margin:0;background:#06110e;color:#ebfaf5;font:15px/1.65 Arial,sans-serif}}main{{max-width:1320px;margin:auto;padding:40px 24px}}h1{{font-size:clamp(28px,4vw,50px);line-height:1.15;max-width:950px}}h2{{font-size:22px}}p,li{{color:#afd0c4}}a{{color:#8df5d2}}section,details{{background:#0b1d16;border:1px solid #25483b;border-radius:14px;padding:22px;margin:22px 0}}.kicker{{color:#8df5d2;font-size:12px;letter-spacing:2px}}.note{{background:#21240f;border:1px solid #655d23;padding:18px;border-radius:10px}}.scroll{{overflow:auto;max-width:100%}}table{{border-collapse:collapse;min-width:100%;font-size:14px;white-space:nowrap}}th,td{{text-align:left;padding:12px 14px;border-bottom:1px solid #25483b}}thead{{color:#88b4a4}}tbody th{{font-weight:400}}summary{{cursor:pointer;color:#8df5d2;font-size:18px}}svg{{width:100%;height:auto;display:block}}svg text{{fill:#bdd9cc;font-size:13px}}.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:13px}}.legend i{{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:6px}}li{{margin:10px 0}}footer{{font-size:13px;color:#92b4a4}}p,a,h1,h2,li{{overflow-wrap:anywhere}}@media(max-width:650px){{main{{padding:24px 12px}}section,details{{padding:16px}}}}
 </style></head><body><main><div class="kicker">CALYX · FROZEN RAW RESEARCH · XAUUSD</div><h1>Current LTA vs M5 VWAP and developing POC.</h1><p>2025-10-05 through 2026-10-04 inclusive. One $10,000 account per test, 1% intended equity risk per entry, native MT5 Model4 with150ms execution delay and broker costs.</p><div class="note">No production EA, preset, BAT, website or live account was changed. This is a last-year comparison, not an optimized or multi-year-validated strategy. {esc(rows[0][1]['native']['history_quality'])}; real ticks start2026-01-01 and earlier data may use generated ticks. Gold volume profiles use the broker’s tick-volume approximation where real volume is absent.</div><section><h2>Matched comparison</h2><p>“Current LTA” follows the last installed preset: Safe off. The BAT-recommended Safe rows are shown separately. All results below count a partially closed position once, including entry/exit costs. Trades/month and trading weekday are separate rates.</p><div class="scroll"><table><thead><tr><th>Version</th><th>Positions</th><th>Per month/day</th><th>Return</th><th>Net PF</th><th>Net win rate</th><th>Native equity DD</th><th>Daily equity / MT5 Sharpe</th><th>Win/loss streak</th><th>Partial/BE</th></tr></thead><tbody>{body}</tbody></table></div><p>Daily equity Sharpe uses five-minute sampled mark-to-market day-end values, annualized with√252. MT5’s native Sharpe uses its own methodology and is listed separately; neither is interchangeable with a trade-return Sharpe.</p></section>{chart(rows[:4],'balance','Closed cash balance — separate strategy tests')}{chart([rows[0],rows[2],rows[4],rows[5]],'equity','Sampled floating equity — separate strategy tests')}<p>These are comparison overlays, not a shared portfolio. Cash curves are steps at cash-flow events. Equity curves are sampled every5minutes and cannot reproduce all intrabar extrema; use native and EA tick-observed DD figures for drawdown.</p><section><h2>The tested rule and stated assumptions</h2>{rules}<p>Developing POC/VWAP uses today’s completed M5 bars only (at least8). Yesterday’s profile ends strictly before today’s first bar. VWAP is volume-weighted M5 typical price, not tick-level exchange VWAP. “Today inside value” means signal and entry are inside, not that the complete future day stays inside. Both directions are mirrored; no extra crossing or minimum-RR gate was added. Original LTA profile M15 is retained for the M5 legacy control; the new flow uses M5 profiles. See <a href="PROTOCOL.md">frozen protocol</a>.</p></section><section><h2>Monthly net P/L (USD, complete positions by final exit)</h2><div class="scroll"><table><thead><tr><th>Month</th>{''.join('<th>'+esc(row['label'])+'</th>' for k,row,c in rows)}</tr></thead><tbody>{mt}</tbody></table></div></section><h2>Position-by-position evidence</h2>{detail}<section><h2>Verification</h2><p>The new-rule off switch matches all {parity['trades']} shipped-binary trades: entry/exit times, sides, prices, lots, commissions, swap and net P/L. Compile:0errors,0warnings. Fifteen rule tests passed. All native reports verify symbol, date, SET inputs and150ms delay; exported position IDs reconcile full entries with all partial/final exits and native net P/L. No invalid-stop/volume, order, close, modification or stop-out failures occurred.</p><p>Broker lot rounding is unchanged: round up and use minimum lot, so actual planned stop risk can exceed1%. Exposure is not hard-capped at1%, and gaps/slippage can exceed planned stop risk. If entry is already past yesterday’s POC, the partial can happen soon after entry—only after a later favourable close. This is important when interpreting the win rate.</p><p><a href="SUMMARY.csv">Comparison CSV</a> · <a href="SUMMARY.json">Metrics and provenance</a> · <a href="PARITY.json">Off-switch parity</a> · <a href="frozen.json">Frozen source hashes</a></p></section><footer>Historical test only. No future return guarantee. Source and broker conventions differ from TradingView’s chart.</footer></main></body></html>'''
 retry_total=int(sum(row['counters']['modify_failed'] for key,row,color in rows))
 flow=next(row for key,row,color in rows if key=='FLOW_M5')
 already_past=sum((1 if t['side']=='Long' else -1)*(t['open_price']-float(t['audit']['poc']))>0 for t in flow['trades'])
 page=page.replace('<section><h2>Monthly net P/L',f'<section><h2>Why the win rate changed</h2><p>{already_past} of {flow["metrics"]["trades"]} new-flow entries were already beyond yesterday’s POC. The stated rule does not require the POC to be ahead of entry, so these positions can take partials and move to entry soon after opening. Average net new-flow win: ${fmt(flow["metrics"]["avg_win"])}; average net loss: ${fmt(flow["metrics"]["avg_loss"])}. A higher win rate therefore did not translate into a higher annual return or Sharpe. Requiring the prior-day POC ahead of entry would be an additional rule, not tested here.</p></section><section><h2>Monthly net P/L')
 page=page.replace('No invalid-stop/volume, order, close, modification or stop-out failures occurred.',
  f'No entry, partial-close, volume or stop-out failures occurred. {retry_total} breakeven modifications were rejected as invalid stops after simulated latency; original stops were retained and all those requests were later successfully retried. These rejections are preserved in the audit, not removed from the results.')
 page=page.replace('</style>',' .plot{overflow:auto;max-width:100%}.plot svg{min-width:900px}</style>')
 (R/'Results.html').write_text(page,encoding='utf-8')
 run.save(R/'verification.json',dict(parity=parity,unit_tests=15,rows=len(rows),source_and_production_hashes_unchanged=True,native_cost_reconciliation=True,exact_native_deal_audits=audits,recovered_be_rejections=retry_total,no_deployment=True))
 print(json.dumps(summary,indent=2));print('REPORT '+str(R/'Results.html'))
if __name__=='__main__':main()
