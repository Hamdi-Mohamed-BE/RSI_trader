"""Evidence-backed local report; no trading, deployment or Git operations."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import csv,gzip,hashlib,html,importlib.util,json,re,shutil
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
sp=importlib.util.spec_from_file_location('current_xag_audit',R/'run.py')
run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)
sp=importlib.util.spec_from_file_location('audit_display',B/'News Pulse XAU Current Audit 2026-10-05/report.py')
display=importlib.util.module_from_spec(sp);sp.loader.exec_module(display)
table=display.table;graph=display.graph
def read(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
def save(p,v):(R/p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def esc(x):return html.escape(str(x))
def fmt(x,n=2,s=''):return '—' if x is None else f'{x:,.{n}f}{s}'
def stamp(ep):return datetime.fromtimestamp(int(ep),timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def rows(p):
 with (R/p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def verify(result):
 case=result['case'];ts=read(f'native/{case}/trades.json')
 assert sha(R/f'native/{case}/report.htm')==result['report_sha']
 assert len(ts)==result['native']['trades'] and abs(sum(t['net'] for t in ts)-result['native']['net_profit'])<.021
 if result['original']:return ts
 ds=rows(f'native/{case}/deals.csv');groups=defaultdict(list)
 for d in ds:groups[int(d['position_id'])].append(d)
 assert len(groups)==len(ts)
 assert abs(sum(float(d[k]) for d in ds for k in ['gross','commission','swap','fee'])-result['native']['net_profit'])<.021
 specs=rows(f'native/{case}/spec.csv');assert len(specs)==1 and specs[0]['currency_profit']=='USD'
 for t in ts:
  ent=[d for d in groups[t['position_id']] if int(d['entry'])==0];assert len(ent)==1
  outs=[d for d in groups[t['position_id']] if int(d['entry'])==1]
  assert abs(float(ent[0]['volume'])-sum(float(d['volume']) for d in outs))<1e-8
  assert abs(t['cash_factor']-float(specs[0]['contract_size']))<1e-6
  sign=1 if int(ent[0]['type'])==0 else -1
  for d in outs:
   assert abs((float(d['price'])-float(ent[0]['price']))*sign*float(d['volume'])*t['cash_factor']-float(d['gross']))<.011
 ts.sort(key=lambda t:(t['close_epoch'],t['closing_deal']))
 recalculated=run.metrics(ts,*result['window'],rows(f'native/{case}/equity.csv'))
 for key in ['net_profit','trades','win_streak','loss_streak']:assert recalculated[key]==result['metrics'][key]
 for key in ['pf','return_pct','win_rate','daily_equity_sharpe']:
  a,b=recalculated[key],result['metrics'][key]
  assert (a is None and b is None) or abs(a-b)<1e-9
 return ts

def equity(case):
 ds=rows(f'native/{case}/equity.csv');df=pd.DataFrame(ds)
 ser=pd.Series(df.equity.astype(float).to_numpy(),index=pd.to_datetime(df.epoch,format='%Y.%m.%d %H:%M:%S',utc=True))
 ser=ser.groupby(level=0).last().sort_index();daily=ser.resample('D').last().ffill()
 return [(d.timestamp(),float(x)) for d,x in daily.items()],[(d.timestamp(),float(x)) for d,x in (100*(daily/daily.cummax()-1)).items()]

def diagnostics(result,trades):
 case=result['case'];its=rows(f'native/{case}/intents.csv');journal=gzip.decompress((R/f'native/{case}/journal.txt.gz').read_bytes()).decode()
 accepted=[i for i in its if int(i['retcode']) in [10008,10009,10010]]
 placed={int(i['comment'].split('|')[1]) for i in accepted}
 lo,hi=[datetime.strptime(d,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp() for d in result['window']]
 missing=[e for e in read('calendar.json')['events'] if lo<=e['epoch']<hi and e['epoch'] not in placed]
 trace=sorted({q['epoch'] for q in rows(f'native/{case}/equity.csv')});gaps=[]
 for e in missing:
  dt=datetime.fromtimestamp(e['epoch'],timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
  before=[t for t in trace if t<dt];after=[t for t in trace if t>=dt]
  gaps.append(dict(kind=e['kind'],event_utc=stamp(e['epoch']),previous_trace=before[-1] if before else None,next_trace=after[0] if after else None))
 late=[dict(comment=i['comment'],acknowledged=i['epoch']) for i in accepted if datetime.strptime(i['epoch'],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()>=int(i['comment'].split('|')[1])]
 spreads=[float(i['ask'])-float(i['bid']) for i in accepted]
 request_risks=[float(i['planned_risk'])/float(i['budget']) for i in accepted]
 lines=sorted(set(re.sub(r'^.*?(?=20\d\d\.\d\d\.\d\d \d\d:)', '',l) for l in journal.splitlines() if any(p in l for p in ['trailing-stop update failed','could not close position','could not delete pending order'])))
 realized=max((-t['net']/t['budget'] for t in trades if t['net']<0),default=None)
 ts=sorted(trades,key=lambda t:t['net'],reverse=True);after_best=sum(t['net'] for t in ts[1:])
 wins=[t['net'] for t in trades if t['net']>0];losses=[t['net'] for t in trades if t['net']<0]
 return dict(unplaced_events=gaps,accepted_at_or_after_release=late,execution_messages=lines,max_realized_net_loss_budget_ratio=realized,median_quote_spread=float(np.median(spreads)) if spreads else None,max_quote_spread=max(spreads,default=None),zero_spread_accepted_requests=sum(abs(s)<1e-9 for s in spreads),accepted_requests=len(accepted),max_planned_risk_budget_ratio=max(request_risks,default=None),net_without_single_best_position=round(after_best,2),mean_win=float(np.mean(wins)) if wins else None,mean_loss=float(np.mean(losses)) if losses else None,accepted_market_entries=sum(int(i['market']) for i in accepted))

def media(case):
 out=R/f'native/{case}';body=run.h.text(out/'report.htm');receipt={}
 for name in re.findall(r'src=["\x27]([^"\x27]+)["\x27]',body,re.I):
  assert Path(name).name==name and name.startswith(case)
  source=run.T/'reports/newsxagaudit20261005'/name;assert source.is_file()
  shutil.copy2(source,out/name);receipt[name]=sha(out/name)
 return receipt

def main():
 run.verify_frozen();results=read('RESULTS.json');by={r['case']:r for r in results}
 assert read('PARITY.json')['passed'];trades={r['case']:verify(r) for r in results}
 diagnoses={r['case']:diagnostics(r,trades[r['case']]) for r in results if not r['original']}
 save('EXECUTION DIAGNOSIS.json',diagnoses);save('NATIVE MEDIA.json',{r['case']:media(r['case']) for r in results})
 complete=(R/'COMPLETE.json').exists()
 if complete:assert set(by)=={c[0] for c in run.CASES}
 gate=read('INPUT GATE STOP.json') if (R/'INPUT GATE STOP.json').exists() else None
 verification=dict(native_replays=len(results),completed=complete,production_hashes_unchanged=True,shipped_binary_parity_passed=True,whole_positions_cash_reconciled=True,contract_conversion_matches_all_native_exits=True,streaks_follow_final_native_close_deal=True,optimization=False,monte_carlo_promotion=False,live_account_accessed=False,deployment_changed=False,older_tests_not_run=True,status='DESCRIPTIVE CURRENT-CONFIG AUDIT; NOT A VALIDATED OPTIMISATION')
 save('VERIFICATION.json',verification)
 style='''<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#17392a,#07120f 65%);color:#eef8f2;font:15px/1.65 system-ui,sans-serif}main{max-width:1450px;margin:auto;padding:38px 26px}h1{font-size:clamp(32px,4vw,54px);line-height:1.13}h2{font-size:27px;margin-top:40px}h3{font-size:21px}p,li{color:#b4c8bd}a,summary{color:#79f8c6}a{overflow-wrap:anywhere}.eyebrow{font:12px monospace;letter-spacing:2px;color:#78efb9}.notice,.card,.chart{padding:20px;border:1px solid #3a5547;border-radius:14px;background:#0b2119b8;margin:20px 0}.notice{border-color:#91753d;background:#26271acd}.notice p{color:#ead3a1}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{margin:0}.card strong{display:block;font-size:29px;color:#7bf6c0}.card small,footer,.muted{color:#9ab6a5;font-size:13px}.scroll{overflow:auto;border:1px solid #2e4c3c;border-radius:12px}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:13px;white-space:nowrap;text-align:right;border-bottom:1px solid #254333}th{background:#163226;color:#b9d2c4}th:first-child,td:first-child{text-align:left}svg{width:100%;height:auto}svg text{fill:#abc6b7;font:12px system-ui}details{padding:16px 0;border-bottom:1px solid #294638}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#122b20;padding:15px;font-size:12px;border-radius:10px}footer{margin-top:40px}@media(max-width:650px){main{padding:25px 14px}.cards{grid-template-columns:repeat(2,1fr)}.card{padding:14px}.card strong{font-size:23px}.notice,.chart{padding:15px}h2{font-size:23px}}</style>'''
 out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx · News Pulse Silver current audit</title>'+style+'</head><body><main><div class="eyebrow">CALYX · RESEARCH ONLY · 5 OCTOBER 2026</div><h1>News Pulse Silver<br>Exact-current execution audit.</h1>',
 '<div class="notice" id="outcome"><b>Descriptive replay, not a validated new winner.</b><p>No parameters optimised and no replacement selected. No live bot, BAT, public website or account was changed. These existing event settings were fitted to 2025-09-19 → 2026-09-19 history; most displayed dates overlap that fit. They are not independent out-of-sample validation.</p></div>',
 '<p><a href="../Active%20EA%20Recent%20Review%202026-10-05/Results.html#future-bat-keeps">Active-EA review + future-BAT keep list</a> · <a href="../News%20Pulse%20XAU%20Current%20Audit%202026-10-05/Results.html">Previous Gold news audit</a> · <a href="PROTOCOL.md">Frozen protocol</a></p>',
 f'<p class="muted">{"Completed recent diagnostic audit" if complete else "Partial — replays running"} · {len(results)} native cases · one unchanged trading configuration. Each window starts a separate USD 10,000 balance. Overlapping windows cannot be added together.</p>']
 year=by.get('1Y-150')
 if year:
  diag=diagnoses['1Y-150'];out.append('<div class="notice"><b>Not suitable for the requested high-win-rate shortlist yet.</b><p>The year has '+fmt(year['metrics']['win_rate'],1,'%')+' net wins and '+str(year['metrics']['win_streak'])+' wins / '+str(year['metrics']['loss_streak'])+' losses in its longest streaks. Actual initial stop exposure reached '+fmt(year['max_actual_risk_budget_ratio'],2,'×')+' the pre-send risk budget; maximum realised net position loss reached '+fmt(diag['max_realized_net_loss_budget_ratio'],2,'×')+'. '+str(diag['zero_spread_accepted_requests'])+' of '+str(diag['accepted_requests'])+' accepted year request quotes have zero spread. Those limits matter more than the headline historical return.</p></div>')
  m=year['metrics'];out.append('<div class="cards">'+''.join(f'<div class="card">{esc(label)}<strong>{esc(value)}</strong><small>{esc(note)}</small></div>' for label,value,note in [('Year return',fmt(m['return_pct'],2,'%'),'Historical, fitted/mixed-tick diagnostics'),('Year positions',str(m['trades']),fmt(m['win_rate'],1,'%')+' net win rate'),('Year net PF',fmt(m['pf'],3),'Whole-position net costs'),('Year equity DD',fmt(year['native']['equity_dd_pct'],2,'%'),'Native intraday floating-equity metric')])+'</div>')
 out+=['<h2>Actual rules — not the SET fallback values</h2><p>Shipped Multi Asset Event v2.21, installer 12B XAG two-sided SET, Exness XAGUSD/M1, USD 10,000, leverage 1:2000, Model 4. 0.75% equity risk per side; not a shared portfolio cap. Both pending sides remain armed, not OCO. Adaptive, Markov and dynamic trailing are off. Definitive rejected prices repair using a fresh quote, then same-direction market fallback. Unknown responses must reconcile; no blind retry.</p>',
 table(['Event','Lead','Anchor','Offset / initial SL (price)','Trailing','Liquidation'],[['NFP','15s','Current Ask/Bid','0.12 / 0.02','Off','Release +60s'],['CPI','10s','Previous completed M1 high/low','0.02 / 0.02','Off','Release +60s'],['FOMC','120s','Previous completed M1 high/low','0.12 / 0.02','From +0.5R; 0.40 price gap','Release +60s']]),
 '<p>No fixed TP. A 0.5R FOMC trigger does not automatically mean breakeven: its 0.40 trailing gap is twenty times the nominal 0.02 initial stop. The candidate SL must improve the existing stop before it is sent. Broker stop constraints and crossed-level market geometry can widen the requested stop. Price dollars are not account-risk dollars.</p>',
 '<h2>Results by window and request delay</h2><p>UTC [start inclusive, end exclusive]. Positions, not deals or pending orders. Net PF groups entry/exit commission, fee and swap into each position; the native headline PF is shown in its linked report and may differ while account cash matches. Sharpe is sampled daily floating-equity returns, √252, not native trade-based Sharpe. W/L = longest net win/loss streak in final closing-deal order. Sparse windows and related sides can exaggerate ratios.</p>']
 records=[]
 for r in results:
  m=r['metrics'];records.append([r['case'],' → '.join(r['window']),str(r['delay_ms'])+'ms',m['trades'],fmt(m['win_rate'],1,'%'),fmt(m['pf'],3),fmt(m['return_pct'],2,'%'),fmt(r['native']['equity_dd_pct'],2,'%'),fmt(m['daily_equity_sharpe']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday']),r['native']['history_quality']])
 out.append(table(['Case','Dates [start,end)','Delay','Positions','Net wins','Net PF','Return','Equity DD','Daily Sharpe','W / L','/ month','/ weekday','History'],records,'performance'))
 if year:
  ep,dd=equity('1Y-150');out+=[graph([('150ms',ep)],'Latest year · daily-close floating equity (USD)','equity-chart'),graph([('150ms',dd)],'Latest year · daily-close floating-equity drawdown (%)','dd-chart','%')]
 recent=[r for r in results if r['case'] in ['3M-150','3M-3000']]
 if recent:out.append(graph([(str(r['delay_ms'])+'ms',equity(r['case'])[0]) for r in recent],'Three months · request-delay sensitivity (USD)','delay-chart'))
 out.append('<p class="muted">Curves use UTC daily-close samples and can miss news-second drawdown. The native equity-DD table is the headline. This is not a shared-portfolio backtest.</p><h2>Execution and risk sizing</h2><p>Complete means both sides accepted, not both filled. Retained unfilled orders can expire. Repaired/market fallback counts are not automatically failures. All whole positions and individual native deal cash independently reconcile; all cases finish flat. Journal error counts can contain duplicate terminal/agent messages.</p>')
 execution=[];baskets=[]
 for r in results:
  if r['original']:continue
  d=diagnoses[r['case']];a=r['event_audit'];e=r['errors'];bm=r['event_basket_metrics']
  execution.append([r['case'],f"{a['complete']} / {a['expected']}",r['both_sides_filled_events'],e['fallbacks'],fmt(r['max_actual_risk_budget_ratio'],2,'×'),fmt(d['max_realized_net_loss_budget_ratio'],2,'×'),fmt(r['latest_exit_seconds_after_deadline'],0,'s'),len(d['accepted_at_or_after_release']),e['modify_failed'],e['close_failed']+e['delete_failed'],len(r['qualification_failures'])])
  if bm:baskets.append([r['case'],bm['trades'],fmt(bm['win_rate'],1,'%'),fmt(bm['pf'],3),f"{bm['win_streak']} / {bm['loss_streak']}",fmt(bm['net_profit'])])
 out.append(table(['Case','Complete / scheduled','Both sides filled','Market fallbacks','Max initial exposure / budget','Max realised loss / budget','Latest exit vs +60s','Acks at/after release','Trail errors','Close/delete errors','Gate issues'],execution,'execution'))
 out.append('<p>Budget was recorded before each send. Initial stop exposure uses the actual entry fill and original requested SL, before fees, and is not a guaranteed realised loss cap. Conversion is measured with tester OrderCalcProfit and checked against every native exit cash amount; XAG is 5,000 ounces per CFD lot here, not the 100-ounce Gold multiplier. Upward lot rounding, price gaps, market fallback and stop slippage can defeat a nominal cash budget. A negative exit lateness means an earlier stop exit. Request-delay tests are not extra latency applied to server-triggered stops.</p>')
 spread_rows=[[r['case'],diagnoses[r['case']]['accepted_requests'],diagnoses[r['case']]['zero_spread_accepted_requests'],fmt(diagnoses[r['case']]['median_quote_spread'],3),fmt(diagnoses[r['case']]['max_quote_spread'],3)] for r in results if not r['original']]
 out.append(table(['Case','Accepted requests','Zero-spread request quotes','Median quote spread','Max quote spread'],spread_rows,'spread-audit'))
 out.append('<p><b>Important cost-path limitation:</b> some accepted request quotes have identical Bid and Ask, including every accepted August parity request. These are recorded tester quotes, not evidence of a zero-cost live Silver market. A real-tick percentage alone does not validate news-time spreads, stop liquidity or live slippage. No extra spread/slippage amount was invented to make a result look conservative. Credible measured historical costs are required before optimisation. Unrealistic early compounded profits also amplify later cash and lot size; later dollar profits inside the year replay are not a clean separate-period backtest.</p>')
 if year:
  d=diagnoses['1Y-150'];out.append('<div class="notice"><b>Year execution diagnostic</b><p>Average net winner $'+fmt(d['mean_win'])+'; average net loser $'+fmt(d['mean_loss'])+'. Quote spread at accepted requests: median '+fmt(d['median_quote_spread'],3)+' / maximum '+fmt(d['max_quote_spread'],3)+' price units, versus nominal 0.020 SL. Net cash excluding the single best position: $'+fmt(d['net_without_single_best_position'])+' (descriptive concentration check, not an alternate trading strategy).</p></div>')
  for gap in d['unplaced_events']:out.append('<div class="notice"><b>Unplaced release: '+esc(gap['kind']+' · '+gap['event_utc'])+' UTC</b><p>Previous quote-clock trace '+esc(gap['previous_trace'])+'; next '+esc(gap['next_trace'])+'. This records a missing quote/session opportunity, not proof of an order-placement bug. The prospectively frozen all-calendar-events gate retains it; broker session eligibility was not independently established.</p></div>')
  attribution=[]
  for kind in ['NFP','CPI','FOMC']:
   ts=[t for t in trades['1Y-150'] if t['kind']==kind];mm=run.metrics(ts,*year['window'])
   attribution.append([kind,len(ts),len({t['event'] for t in ts}),fmt(mm['win_rate'],1,'%'),fmt(mm['pf'],3),fmt(mm['net_profit']),f"{mm['win_streak']} / {mm['loss_streak']}"])
  out+=['<h2>Year event attribution · 150ms</h2>',table(['Event','Positions','Filled releases','Net wins','Net PF','Net cash $','W / L'],attribution,'event-attribution')]
 out+=['<h3>Release baskets — same cash grouped by event</h3><p>Both sides of each filled release are summed once. Not an extra independent sample, and unfilled releases are not counted as wins.</p>',table(['Case','Filled releases','Positive events','Net PF','Event W / L','Net cash $'],baskets,'baskets')]
 if year:
  detail=[[t['kind'],t['side'],stamp(t['open_epoch']),stamp(t['close_epoch']),fmt(t['volume']),fmt(t['open_price'],3),fmt(t['initial_sl'],3),fmt(t['budget']),fmt(t['actual_risk']),fmt(t['net'])] for t in trades['1Y-150']]
  out+=['<details><summary>Every year trade · actual fill, stop exposure and net cash</summary>',table(['Event','Side','Fill UTC','Close UTC','Lots','Fill','Initial SL','Budget $','Initial exposure $','Net $'],detail,'trade-breakdown'),'</details>']
 out+=['<h2>Qualification and next optimisation hypothesis</h2><div class="notice"><b>No validated replacement, and no optimisation promotion.</b><p>Three-/five-year performance tests are NOT RUN. The year journal records the real-tick start; older event-second quotes are not established. Recent replay statistics cannot supply those missing prices or prove the original fit out of sample. Reconstructing news ticks can alter which side triggers and whether a tight stop survives. Monte Carlo cannot repair this input limitation.</p></div>']
 if gate:out.append('<pre>'+esc(json.dumps(gate,indent=2))+'</pre>')
 out+=['<p>Credible bid/ask event paths and live-fill evidence must come first. After that, the highest-priority research dimensions are spread-aware stop geometry and budget-aware sizing, followed by OCO versus both sides, current-quote versus prior-candle anchoring, and a frozen 30/60/120-second exit search on separate dates. Those would change trading behaviour; none is implemented or selected here. ADX/DI is not automatically an appropriate news-execution fix. Any risk rejection/skip guard conflicts with the earlier force-entry instruction and requires a user decision before deployment.</p>',
 '<p><a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation" target="_blank" rel="noopener">MetaQuotes: real-tick mode can generate missing ticks</a> · <a href="https://www.metatrader5.com/en/terminal/help/algotrading/testing" target="_blank" rel="noopener">MetaQuotes: request-delay mechanics</a>. Restricting this to descriptive evidence is our inference from those mechanics and the saved journals. No independent control advantage, FTMO pass probability or payout forecast is claimed.</p>',
 '<h2>Exact evidence</h2>']
 for r in results:
  case=r['case'];detail=dict(failures=r['qualification_failures'],errors=r['errors'],tick_notes=r['tick_notes'],diagnostics=diagnoses.get(case))
  out.append(f'<details><summary>{esc(case)} · inputs, native reports and diagnosis</summary><p><a href="native/{case}/report.htm">Native report</a> · <a href="native/{case}/inputs.set">Inputs</a> · <a href="native/{case}/trades.json">Positions</a> · <a href="native/{case}/results.json">Full results</a></p><pre>'+esc(json.dumps(detail,indent=2))+'</pre></details>')
 out.append('<p>Original EX5 versus instrumented copy: August parity passed for '+str(read('PARITY.json')['positions'])+' positions, identical entries/exits/lots/times/costs. Original embedded tester calendar has limited June–September 2026 dates. The research calendar extension uses saved official BLS/Fed plus FXMacroData receipts, not newly assumed times. Fresh connector history begins July 27, 2026 and is explicitly truncated; older dates rely on archived official provenance. No actual/forecast/revised macro values are used; live historical pre-order schedule availability remains unproven. Original source/SET/shared helper fingerprints are unchanged.</p>')
 out.append('<footer><a href="VERIFICATION.json">Verification</a> · <a href="FROZEN.json">Frozen hashes</a> · <a href="PARITY.json">Parity</a> · <a href="calendar.json">Calendar</a> · <a href="fresh-calendar-receipts.json">Calendar receipts</a> · <a href="RESULTS.json">All results</a><p>Historical simulation, not a return forecast. Research only; no BAT, website deployment or live changes. Stop here for review before the next EA.</p></footer></main></body></html>')
 (R/'Results.html').write_text('\n'.join(out),encoding='utf-8');print(json.dumps(verification,indent=2))

if __name__=='__main__':main()
