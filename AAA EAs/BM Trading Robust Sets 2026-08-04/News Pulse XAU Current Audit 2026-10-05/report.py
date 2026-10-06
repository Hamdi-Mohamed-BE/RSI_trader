"""Derived, local news execution audit. Never edits trading rules or deployment."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv, gzip, hashlib, html, json, math, re, shutil
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
def read(p):return json.loads((R/p).read_text(encoding='utf-8-sig'))
def save(p,x):(R/p).write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def esc(x):return html.escape(str(x))
def fmt(x,n=2,suffix=''):return '—' if x is None else f'{x:,.{n}f}{suffix}'
def stamp(ep):return datetime.fromtimestamp(int(ep),timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def rows(p):
 with (R/p).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def native_media(case):
 data=(R/f'native/{case}/report.htm').read_bytes()
 body=data.decode('utf-16') if data.startswith(b'\xff\xfe') else data.decode('utf-8-sig',errors='replace')
 source_root=B/'_Backtests/MT5-DMC-20260811/reports/newsaudit20261005'
 receipt={}
 for name in re.findall(r'src=["\x27]([^"\x27]+)["\x27]',body,re.I):
  assert Path(name).name==name and name.startswith(case),'Unexpected native report media path'
  source=source_root/name;assert source.is_file(),'Native graph missing: '+name
  target=R/f'native/{case}'/name;shutil.copy2(source,target);receipt[name]=sha(target)
 return receipt
def table(headers,records,ident=''):
 return f'<div class="scroll"><table id="{ident}"><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in record)+'</tr>' for record in records)+'</tbody></table></div>'
def graph(series,title,ident,unit='$'):
 if not series:return ''
 width,height=1160,355;left,right,top,bottom=90,24,32,48
 xs=[float(x) for _,points in series for x,y in points];ys=[float(y) for _,points in series for x,y in points]
 xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
 if ymax-ymin<1e-10:ymin-=1;ymax+=1
 pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad
 X=lambda x:left+(x-xmin)/max(1,xmax-xmin)*(width-left-right)
 Y=lambda y:top+(ymax-y)/(ymax-ymin)*(height-top-bottom)
 grid=''
 for y in np.linspace(ymin,ymax,5):
  grid+=f'<line x1="{left}" x2="{width-right}" y1="{Y(y):.1f}" y2="{Y(y):.1f}" stroke="#24453a"/><text x="{left-10}" y="{Y(y)+4:.1f}" text-anchor="end">{fmt(y,0 if unit=="$" else 1)}{esc(unit) if unit!="$" else ""}</text>'
 for x in np.linspace(xmin,xmax,5):
  grid+=f'<text x="{X(x):.1f}" y="{height-13}" text-anchor="middle">{datetime.fromtimestamp(x,timezone.utc):%b %Y}</text>'
 colors=['#6cf5be','#e4bf7b','#91b7ff'];paths='';legend=''
 for i,(name,points) in enumerate(series):
  points=sorted(points);color=colors[i%len(colors)]
  paths+=f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="'+ ' '.join(f'{X(x):.2f},{Y(y):.2f}' for x,y in points)+'"/>'
  legend+=f'<span style="color:{color}">● {esc(name)}</span> '
 return f'<section class="chart" id="{ident}"><h3>{esc(title)}</h3><p>{legend}</p><svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>{grid}{paths}</svg></section>'
def equity(case):
 q=rows(f'native/{case}/equity.csv')
 frame=pd.DataFrame(q);ser=pd.Series(frame.equity.astype(float).to_numpy(),index=pd.to_datetime(frame.epoch,format='%Y.%m.%d %H:%M:%S',utc=True))
 # Deduplicate successive timer/tick observations; keep all event-second samples.
 ser=ser.groupby(level=0).last().sort_index()
 daily=ser.resample('D').last().ffill()
 points=[(t.timestamp(),float(v)) for t,v in daily.items()]
 dd=100*(daily/daily.cummax()-1)
 return points,[(t.timestamp(),float(v)) for t,v in dd.items()]
def verify(result):
 case=result['case'];trades=read(f'native/{case}/trades.json')
 assert sha(R/f'native/{case}/report.htm')==result['report_sha']
 assert abs(sum(t['net'] for t in trades)-result['native']['net_profit'])<.021
 if not result['original']:
  deals=rows(f'native/{case}/deals.csv');net=sum(float(d[k]) for d in deals for k in ['gross','commission','swap','fee'])
  assert abs(net-result['native']['net_profit'])<.021
  grouping=defaultdict(list)
  for d in deals:grouping[int(d['position_id'])].append(d)
  assert len(grouping)==len(trades)==result['native']['trades']
  # Confirm the $100-per-lot-per-price-dollar risk conversion against every exit.
  for ds in grouping.values():
   entry=[d for d in ds if int(d['entry'])==0];assert len(entry)==1
   direction=1 if int(entry[0]['type'])==0 else -1
   for d in ds:
    if int(d['entry'])==1:
     expected=(float(d['price'])-float(entry[0]['price']))*direction*float(d['volume'])*100
     assert abs(expected-float(d['gross']))<.011,'Contract-size risk conversion does not match native cash'
  final_deals={pid:max(int(d['deal']) for d in ds if int(d['entry'])==1) for pid,ds in grouping.items()}
  trades.sort(key=lambda x:(x['close_epoch'],final_deals[x['position_id']]))
  # Whole-position streaks follow the native final-close deal sequence, not ID ties.
  w=l=mw=ml=0
  for trade in trades:
   w=w+1 if trade['net']>0 else 0;l=l+1 if trade['net']<0 else 0;mw=max(mw,w);ml=max(ml,l)
  result['metrics'].update(win_streak=mw,loss_streak=ml)
 return trades
def event_breakdown(trades):
 out=[]
 for kind in ['NFP','CPI','FOMC']:
  ts=[t for t in trades if t['kind']==kind];n=len(ts);nets=[t['net'] for t in ts]
  wins=[x for x in nets if x>0];losses=[x for x in nets if x<0]
  gp=sum(wins);gl=-sum(losses);unique=len(set(t['event'] for t in ts))
  out.append([kind,n,unique,fmt(100*len(wins)/n,1,'%') if n else '—',fmt(gp/gl,3) if gl else '— (no net losses)',fmt(sum(nets),2),fmt(np.mean(wins) if wins else None),fmt(np.mean(losses) if losses else None),fmt(max((t['actual_risk']/t['budget'] for t in ts),default=None),2,'×')])
 return out
def diagnostics(case,result):
 if result['original']:return {}
 intents=rows(f'native/{case}/intents.csv');placed={int(x['comment'].split('|')[1]) for x in intents}
 lo,hi=(datetime.strptime(s,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp() for s in result['window'])
 calendar=read('calendar.json')['events'];missing=[x for x in calendar if lo<=x['epoch']<hi and x['epoch'] not in placed]
 trace=rows(f'native/{case}/equity.csv');dates=sorted({x['epoch'] for x in trace})
 gaps=[]
 for x in missing:
  text=datetime.fromtimestamp(x['epoch'],timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
  before=[d for d in dates if d<text];after=[d for d in dates if d>=text]
  gaps.append(dict(event_utc=stamp(x['epoch']),kind=x['kind'],previous_trace_time=before[-1] if before else None,next_trace_time=after[0] if after else None,diagnosis='No usable release-time quote trace; consistent with Good Friday closure, not proof of placement bug' if x['epoch']==1775219400 else 'Not explained; investigate quote/session eligibility before promotion'))
 journal=gzip.decompress((R/f'native/{case}/journal.txt.gz').read_bytes()).decode()
 unique=[]
 for line in journal.splitlines():
  if 'trailing-stop update failed' not in line:continue
  m=re.search(r'20\d\d\.\d\d\.\d\d \d\d:\d\d:\d\d\s+.*',line)
  if m and m.group() not in unique:unique.append(m.group())
 late=[]
 for intent in intents:
  if int(intent['retcode']) not in (10008,10009,10010):continue
  accepted=datetime.strptime(intent['epoch'],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
  event=int(intent['comment'].split('|')[1]);lag=accepted-event
  if lag>=0:late.append(dict(comment=intent['comment'],acknowledgement_at_or_after_release_seconds=lag))
 return dict(unplaced_calendar_events=gaps,distinct_trailing_failure_messages=unique,terminal_and_agent_journal_duplicates_removed=True,accepted_at_or_after_release=late)
def main():
 results=read('RESULTS.json');by={x['case']:x for x in results};frozen=read('FROZEN.json')
 assert all(sha(B/p)==v for p,v in frozen['production'].items()),'Production hash changed'
 parity=read('PARITY.json');assert parity['passed']
 trades={x['case']:verify(x) for x in results}
 save('NET POSITION METRICS.json',{x['case']:dict(metrics=x['metrics'],streak_order='Final native closing-deal sequence') for x in results})
 diagnoses={x['case']:diagnostics(x['case'],x) for x in results if not x['original']}
 media={x['case']:native_media(x['case']) for x in results};save('NATIVE MEDIA.json',media)
 save('EXECUTION DIAGNOSIS.json',diagnoses)
 complete=(R/'COMPLETE.json').exists()
 planned=[x[0] for x in frozen['cases']]
 skips=read('NOT RUN.json') if (R/'NOT RUN.json').exists() else []
 done=set(by)|{x['case'] for x in skips}
 if complete:assert done==set(planned),'Missing planned case status'
 if complete:save('status.json',dict(message='COMPLETE recent diagnostics; input-quality stop before optimisation',utc=datetime.now(timezone.utc).isoformat(),finished_native_replays=len(results),uncompleted_older_cases=len(skips),production_changed=False))
 outcome={'audit_finished':complete,'current_configuration_count':1,'finished_native_replays':len(results),'planned_cases':len(planned),'original_binary_parity_passed':True,'no_optimisation_performed':True,'no_new_version_selected':True,'production_hashes_unchanged':True,'all_closed_cash_reconciled':True,'risk_conversion_checked_against_all_exit_deals':True,'new_bat_created':False,'live_account_accessed':False,'tick_quality_qualified_for_older_news_events':False,'pending_stop_trigger_server_latency_simulated':False,'status':'DESCRIPTIVE ONLY — execution/history qualification incomplete'}
 save('VERIFICATION.json',outcome)
 parts=['''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx · News Pulse XAU exact-current audit</title><style>
 :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#163729,#07130f 65%);color:#edf7f1;font:15px/1.65 system-ui,sans-serif}main{max-width:1450px;margin:auto;padding:38px 28px}h1{font-size:clamp(32px,4vw,54px);line-height:1.12;margin:15px 0 25px}h2{font-size:27px;margin-top:42px}h3{font-size:20px}p,li{color:#b4c8bd}a,summary{color:#79f8c6}a{overflow-wrap:anywhere}.eyebrow{color:#79f8c6;font:12px monospace;letter-spacing:2px}.notice,.card,.chart{border:1px solid #365446;border-radius:14px;background:#0c2119ba;padding:20px;margin:20px 0}.notice{border-color:#88703c;background:#24271bc9;color:#ecd4a0}.notice p{color:inherit}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{margin:0}.card strong{display:block;font-size:29px;color:#77f5c0}.card small{display:block;color:#a9c0b4}.scroll{overflow:auto;border:1px solid #2e493e;border-radius:12px}table{border-collapse:collapse;width:100%;font:13px/1.5 system-ui;font-variant-numeric:tabular-nums}th,td{padding:13px;border-bottom:1px solid #244538;white-space:nowrap;text-align:right;vertical-align:top}th{background:#123126;color:#adcfbf}th:first-child,td:first-child{text-align:left}.scroll.wrap th,.scroll.wrap td{white-space:normal;min-width:220px}input,select{background:#122b21;border:1px solid #3b5d4b;color:#eef7ee;padding:10px 13px;border-radius:8px;font:inherit;margin:4px}.muted,footer{color:#93afa0;font-size:13px}.good{color:#7ff0c5}.bad{color:#fa9c98}svg{width:100%;height:auto}svg text{fill:#aac6b7;font:12px system-ui}details{padding:15px 0;border-bottom:1px solid #294839}summary{cursor:pointer}pre,code{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}pre{padding:14px;background:#13291f;border-radius:10px}footer{margin-top:38px}@media(max-width:650px){main{padding:24px 14px}.cards{grid-template-columns:repeat(2,1fr)}.card{padding:14px}.card strong{font-size:23px}.notice,.chart{padding:15px}h2{font-size:23px}}
 </style></head><body><main><div class="eyebrow">CALYX · RESEARCH ONLY · 5 OCTOBER 2026</div><h1>News Pulse XAU<br>Audit before optimisation.</h1>
 <div class="notice" id="outcome"><b>Descriptive replay, not a validated new winner.</b><p>No bot, BAT, current website or live account was changed. No parameters optimised or candidate deployed. First establish credible news-time prices and fills; fitting exit settings to generated news ticks would not establish an edge.</p></div>
 <p><a href="../Active%20EA%20Recent%20Review%202026-10-05/Results.html#future-bat-keeps">Full active-EA review + your future-BAT keep list</a> · <a href="PROTOCOL.md">Frozen audit protocol</a></p>''']
 parts.append(f'<p class="muted" id="run-status">{"Recent diagnostic audit finished; input-quality stop" if complete else "Partial report — replays still running"} · {len(results)} finished native replays · {len(skips)} older cases not completed · one unchanged trading configuration. Each case starts a separate USD 10,000 account; windows overlap and cannot be added together.</p>')
 year=by.get('1Y-150')
 if year:
  m=year['metrics'];parts.append('<div class="cards">'+''.join(f'<div class="card">{esc(label)}<strong>{esc(value)}</strong><small>{esc(note)}</small></div>' for label,value,note in [('Year · net return',fmt(m['return_pct'],2,'%'),'Not a forecast; mixed real/generated history'),('Year · whole positions',str(m['trades']),fmt(m['win_rate'],1,'%')+' net wins'),('Year · net PF',fmt(m['pf'],3),'All recorded commission/swap/fees included'),('Year · native equity DD',fmt(year['native']['equity_dd_pct'],2,'%'),'Floating drawdown, not just closed balance')])+'</div>')
 parts.append('''<h2>Exactly what was tested</h2><p>Normal installer v2.21, two-sided XAU event-specific SET, Exness XAUUSD/M1, USD 10,000, leverage 1:2000, native Model 4. Risk is <b>0.75% of equity per side</b> (nominally 1.5% if both trigger), not a shared portfolio cap. Original upward/minimum broker-lot rounding remains. Safe/Markov, dynamic and adaptive gates are off as in this SET. This is an installer configuration audit, not verification of a particular live chart.</p>
 <p>Both sides stay armed; not OCO. Fixed price offset $6 and initial price-stop gap $10, subject to broker constraints. Definitive price rejection retries from a fresh quote, then same-direction market fallback. An uncertain send must not blind-retry. One accepted entry per side/event is remembered; a manual close does not create a new accepted side.</p>''')
 parts.append(table(['Event','Lead before release','Profit target','Trailing','Scheduled liquidation'],[
 ['NFP','10 seconds','None','None','Release + 30 seconds'],['CPI','5 seconds','None','From +1R; price gap $10','Release + 30 seconds'],['FOMC','60 seconds','5.5R','From +0.5R; price gap $4','Release + 30 seconds']]))
 parts.append('<p>The $6/$10 figures are symbol-price dollars, not account-cash risk. A missing stop trigger is different from a rejected order. Accepted pending orders can expire unfilled if quotes never reach their trigger before liquidation.</p>')
 parts.append('<h2>All replay windows and delays</h2><p>Start inclusive, end exclusive, UTC (Exness server clock used here). Net whole-position results, not order/deal counts. Net PF groups all entry/exit costs into each position and can differ from the native report headline PF; both reconcile to identical account cash. Daily Sharpe uses sampled floating equity and √252 annualisation; a sparse short window can produce a misleadingly large number. It is not the platform’s trade-based Sharpe. W/L = longest net winning/losing run in final closing-deal sequence; flats reset both. Frequencies include all weekdays, not only release days.</p>')
 records=[]
 for x in results:
  m=x['metrics'];n=x['native'];records.append([x['case'],x['window'][0]+' → '+x['window'][1],str(x['delay_ms'])+'ms',m['trades'],fmt(m['win_rate'],1,'%'),fmt(m['pf'],3),fmt(m['return_pct'],2,'%'),fmt(n['equity_dd_pct'],2,'%'),fmt(m['daily_equity_sharpe']),f"{m['win_streak']} / {m['loss_streak']}",fmt(m['trades_month']),fmt(m['trades_weekday']),n['history_quality']])
 for x in skips:records.append([x['case'],x['status'],str(x['delay_ms'])+'ms']+['—']*10)
 parts.append(table(['Case','Dates [start, end)','Delay','Positions','Net wins','Net PF','Return','Native equity DD','Daily Sharpe','W / L run','/ month','/ weekday','Reported history'],records,'performance'))
 if skips:parts.append('<p class="muted">The already-running batch had no stop-file hook: its exclusively owned 3Y replay was aborted at startup by the input-quality guard, and the 5Y case was not started. Neither has a completed performance result. No three-/five-year returns or win rates are inferred from shorter tests.</p>')
 annual=[by[c] for c in ['1Y-150','1Y-1000','1Y-3000'] if c in by]
 if annual:
  curves=[];dds=[]
  for x in annual:
   ep,dd=equity(x['case']);curves.append((str(x['delay_ms'])+'ms',ep));dds.append((str(x['delay_ms'])+'ms',dd))
  parts.append(graph(curves,'Latest year · daily-close floating equity (USD)','equity-chart'))
  parts.append(graph(dds,'Latest year · daily-close equity drawdown (%)','dd-chart','%'))
  parts.append('<p class="muted">Charts sample the end of each UTC day. They can miss intraday event-second drawdown; native equity DD in the table is the correct headline. These curves do not represent a shared portfolio.</p>')
 parts.append('<h2>Order coverage, fills and execution risk</h2><p>Complete means both sides accepted for a release, not both filled. All research replays independently reconcile every exported native deal and the final account cash. Repaired definitive rejection counts are not automatically missing trades; uncertainty, liquidation errors, missing setups and duplicate accepted sides cannot qualify. Journal counts below are occurrences, not unique failed events.</p>')
 execution=[];basket=[]
 for x in results:
  if x['original']:continue
  audit=x['event_audit'];err=x['errors'];bm=x['event_basket_metrics']
  execution.append([x['case'],f"{audit['complete']} / {audit['expected']}",audit['attempted'],x['both_sides_filled_events'],fmt(x['max_actual_risk_budget_ratio'],2,'×'),fmt(x['latest_exit_seconds_after_deadline'],0,'s'),err['rejected'],err['fallbacks'],err['uncertain'],err['close_failed']+err['delete_failed']+err['modify_failed'],len(x['qualification_failures'])])
  if bm:basket.append([x['case'],bm['trades'],fmt(bm['win_rate'],1,'%'),fmt(bm['pf'],3),f"{bm['win_streak']} / {bm['loss_streak']}",fmt(bm['net_profit'])])
 parts.append(table(['Case','Complete / scheduled events','Attempted','Both sides filled','Max initial stop exposure / budget','Latest exit vs +30s','Rejected sends','Market fallbacks','Uncertain sends','Close/delete/modify errors','Gate failures'],execution,'execution'))
 if '1Y-3000' in diagnoses:
  late=diagnoses['1Y-3000']['accepted_at_or_after_release']
  parts.append('<p><b>Slow-connection preparation:</b> at 3-second delay, '+str(len(late))+' CPI sell-side acknowledgements occur at the release second or one second after it. The 5-second CPI lead is shorter than two sequential 3-second acknowledgements. Both sides being eventually accepted is not proof that the straddle was ready before release. At 150ms/1s, no acknowledgement in this trace was at or after release.</p>')
 if year:
  diag=diagnoses['1Y-150'];parts.append(f'<p><b>Year diagnostic:</b> {len(diag["distinct_trailing_failure_messages"])} distinct trailing-failure messages (the terminal and agent journals duplicate them). One FOMC message is an invalid-stops rejection; another tries to modify a position that has already closed. They do not establish that all trailing management failed, but they must be explained before a clean execution pass.</p>')
  for gap in diag['unplaced_calendar_events']:
   parts.append('<div class="notice"><b>Unplaced release: '+esc(gap['kind']+' · '+gap['event_utc'])+' UTC</b><p>Previous quote-clock trace '+esc(gap['previous_trace_time'])+'; next '+esc(gap['next_trace_time'])+'. '+esc(gap['diagnosis'])+'. The frozen all-events setup gate remains marked failed, rather than silently changing its denominator after seeing results. A broker-tradable event calendar would need to be defined prospectively.</p></div>')
  parts.append('<p>Exness lists April 3, 2026 as Good Friday and says holiday hours may change by instrument. Its current page does not retain this account’s precise April XAU session schedule; the closure explanation above is an inference from the replay quote gap, not a verified historical account-session rule. <a href="https://get.exness.help/hc/en-us/articles/17923046759836-Holiday-trading-hours" target="_blank" rel="noopener">Exness holiday information</a>.</p>')
 parts.append('<p>Initial stop exposure uses the actual entry-fill price and original requested SL, before costs. It is not a guaranteed maximum realised loss; gaps through the stop can lose more. Its cash conversion was checked against every exit deal. The intent budget is recorded immediately after the send; a market fallback can already change equity at that instant. Negative exit-vs-deadline means an earlier stop/target exit. Observed latency allowance for the audit is 2 × configured delay + 2 seconds, not permission to hold longer by design.</p>')
 parts.append('<h3>Event baskets: group both sides of one release</h3><p>A filled event counts once after summing its sides. Unfilled events are not included as zero-return wins; see accepted/scheduled setup coverage above. These basket metrics are a second view of the same cash, not extra independent trades.</p>')
 parts.append(table(['Case','Filled events','Net positive events','Net PF','Event W / L run','Net cash (USD)'],basket,'baskets'))
 if year:
  parts.append('<h2>Latest-year event attribution · 150ms</h2>')
  parts.append(table(['Event','Positions','Filled releases','Net wins','Net PF','Net cash','Mean win $','Mean loss $','Max stop exposure / budget'],event_breakdown(trades['1Y-150']),'events'))
 incident=by.get('INCIDENT')
 if incident:
  parts.append('<h2>October 2 NFP · simulated trade breakdown</h2><p>Both pending orders were accepted at 12:29:50 UTC. Only the buy triggered in this replay. This is not evidence of what happened on your live account or another broker.</p>')
  its=trades['INCIDENT'];parts.append(table(['Side','Fill UTC','Close UTC','Volume','Fill price','Initial requested SL','Nominal budget $','Initial stop exposure $','Net $'],[[t['side'],stamp(t['open_epoch']),stamp(t['close_epoch']),fmt(t['volume']),fmt(t['open_price'],3),fmt(t['initial_sl'],3),fmt(t['budget']),fmt(t['actual_risk']),fmt(t['net'])] for t in its],'incident'))
  if its:
   t=its[0];parts.append('<p>The buy-stop trigger was 4190.868 but it filled at '+fmt(t['open_price'],3)+'. The unchanged SL stayed at '+fmt(t['initial_sl'],3)+', so its initial exposure was $'+fmt(t['actual_risk'])+' against a $'+fmt(t['budget'])+' budget. Upward lot rounding already budgets roughly $80 rather than $75 for a $10 price stop; the fill jump increased it further. This is why forced placement is not the same as fixed-risk execution.</p>')
 parts.append('''<h2>Why this is not yet an optimisation pass</h2><div class="notice"><p><b>Price-path and fill evidence come before a higher win rate.</b> Real-tick mode can generate missing minute ticks. The older part of this broker history is not an established event-second bid/ask record; reconstructed paths can decide which side triggers, whether a trail activates and whether a 30-second exit wins.</p><p>MT5 delay stress applies to EA trade requests, not additional server-side latency of an already accepted pending stop. The 150ms/1s/3s runs are request-latency sensitivities, not a simulation of all live news slippage, order-book depth or liquidity. Broker demo history is not live fill proof.</p></div>
 <p>These limits are documented by <a href="https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation" target="_blank" rel="noopener">MetaQuotes: real and generated ticks</a> and <a href="https://www.metatrader5.com/en/terminal/help/algotrading/testing" target="_blank" rel="noopener">MetaQuotes: tester execution delay</a>. The restriction to descriptive results is our inference from those mechanics plus the archived run journals.</p>
 <p>No full optimisation, walk-forward candidate selection, Monte Carlo promotion test, FTMO simulation or payout forecast was run. Reshuffling trades cannot fix questionable event-time prices. The original raw 3Y/5Y PF ≥1.15 / ≥30-position prerequisite is necessary but not sufficient; it cannot replace the execution-history requirement.</p>
 <h3>Next bounded hypothesis — not deployed</h3><p>First obtain credible event-second bid/ask history and compare intended stops with actual entry/exit fills. CPI preparation should allow time for both acknowledgements; liquidation should prioritise reducing filled exposure instead of letting sequential requests extend the deadline. Audit fresh-quote stop validation and position re-selection before trailing; this reduces stale requests but cannot eliminate a close during network delay. Define broker-tradable releases before judging setup coverage. Then test budget-aware sizing and slippage/exposure guards before tuning payoff. A rejection/skip guard can conflict with the earlier instruction to force entry; that trade-off needs your choice. Only after this input gate should a small pre-frozen exit/hold-time search (within your two-minute Gold limit) be judged on separate dates. No automatic switch to ADX/DI, wider stops or longer holds has been made.</p>''')
 parts.append('<h2>Evidence and qualification details</h2>')
 for x in results:
  case=x['case'];parts.append(f'<details><summary>{esc(case)} · native evidence and failures</summary><p><a href="native/{case}/report.htm">Native report</a> · <a href="native/{case}/results.json">Metrics and coverage</a> · <a href="native/{case}/trades.json">Whole positions</a> · <a href="native/{case}/inputs.set">Exact inputs</a></p><pre>'+esc(json.dumps({'qualification_failures':x['qualification_failures'],'tick_notes':x['tick_notes'],'errors':x['errors']},indent=2))+'</pre></details>')
 parts.append(f'''<p>Shipped binary versus tester-only audit copy: August parity passed for {parity['positions']} positions, identical entry/exit prices, times, lots and costs. The research copy only adds file diagnostics and extends its tester calendar; it does not change trading decisions. Original embedded tester dates cover June–September 2026 only. Historical calendar extension combines archived official BLS/Fed receipts and the fresh USD release-calendar connector. Fresh API history begins July 27, 2026 and is explicitly truncated; older dates were not newly verified through that connector. No forecast/actual/revised macro values were used. Historical live schedule availability before every order is not proven.</p>
 <p>The parser-only correction is recorded in <a href="PARSER%20AMENDMENT.json">its amendment</a>; no trading code/binary or frozen settings were changed to repair it. Original sources, inputs, helper hashes, native reports/journals, deal rows and request intentions are retained. Production fingerprints are unchanged.</p>
 <footer><a href="VERIFICATION.json">Verification</a> · <a href="FROZEN.json">Frozen inputs and source hashes</a> · <a href="PARITY.json">Parity check</a> · <a href="calendar.json">Calendar provenance</a> · <a href="fresh-calendar-receipts.json">Fresh calendar receipts</a> · <a href="RESULTS.json">All results</a><p>Historical simulations are not forecasts or guaranteed live results. No BAT was built, no production bot removed and no chart/account modified. Stop here for your review before the next EA.</p></footer></main></body></html>''')
 (R/'Results.html').write_text('\n'.join(parts),encoding='utf-8')
 print(json.dumps(outcome,indent=2))
if __name__=='__main__':main()
