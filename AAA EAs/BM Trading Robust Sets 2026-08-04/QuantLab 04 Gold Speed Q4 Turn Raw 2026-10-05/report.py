"""Offline raw report. No optimisation or promotion."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,html,json,math,re
import run
R=run.R
def esc(x):return html.escape(str(x))
def num(x,n=2):return 'N/A' if x is None else f'{x:,.{n}f}'
def pct(x):return 'N/A' if x is None else f'{x:+.2f}%'
def wilson(w,n):
 if not n:return [None,None]
 z=1.959963984540054;p=w/n;den=1+z*z/n;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;m=(p+z*z/(2*n))/den
 return [100*(m-h),100*(m+h)]
def table(head,rows):
 def line(x,tag):return '<tr>'+''.join(f'<{tag}>{esc(v)}</{tag}>' for v in x)+'</tr>'
 return '<div class="scroll"><table><thead>'+line(head,'th')+'</thead><tbody>'+''.join(line(x,'td') for x in rows)+'</tbody></table></div>'
def native_deal_check(body,df):
 """Independently check exports against native HTML deal rows and close reasons."""
 from app.mt5_evidence_jobs import _clean,_number
 body=body[body.lower().index('<b>deals</b>'):];rows={}
 for rr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',body,re.S|re.I):
  cells=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',rr,re.S|re.I)]
  if len(cells)<13 or not cells[2] or cells[3].lower() not in ('buy','sell'):continue
  deal=int(cells[1]);assert deal not in rows;rows[deal]=cells
 assert set(rows)==set(int(x['deal']) for x in df)
 for d in df:
  c=rows[int(d['deal'])];assert int(c[7])==int(d['order']) and c[4].lower()==('in' if int(d['entry'])==0 else 'out')
  assert c[3].lower()==('buy' if int(d['type'])==0 else 'sell')
  assert int(datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())==int(d['epoch'])
  for key,col in [('volume',5),('price',6),('commission',8),('swap',9),('gross',10)]:assert abs(float(d[key])-_number(c[col]))<.011
 return rows
def verify():
 build=json.loads((R/'build.json').read_text())
 for file,key in [(run.SOURCE,'source_sha256'),(run.EXPERT,'binary_sha256'),(R/'PROTOCOL.txt','protocol_sha256'),(R/'run-config.json','config_sha256')]:assert run.sha(file)==build[key]
 results={}
 for c in run.CFG['cases']:
  cid=c['id'];f=R/'native'/cid;r=json.loads((f/'results.json').read_text());assert r['manifest']==json.loads((f/'manifest.json').read_text()) and r['manifest']['build']==build
  assert not any(r['flags'].values())
  deals=run.pd.read_csv(f/'deals.csv').to_dict('records')
  ts,ld=run.reconstruct(deals,run.pd.read_csv(f/'trades.csv').to_dict('records'))
  assert ld==r['ledger'] and run.metrics(ts)==r['net_metrics']
  j=gzip.decompress((f/'journal.txt.gz').read_bytes()).decode();ss=run.pd.read_csv(f/'signals.csv').to_dict('records')
  assert run.algebra_audit(j,ts,ss,c['control'])==r['audit']
  archive=gzip.decompress((f/'report.htm.gz').read_bytes());assert hashlib.sha256(archive).hexdigest()==r['report_sha256']
  native_text=archive.decode('utf-16') if archive[:2] in (b'\xff\xfe',b'\xfe\xff') else archive.decode('utf-8-sig')
  report_rows=native_deal_check(native_text,deals)
  for t in r['trades']:
   t['exit_comment']=report_rows[t['last_exit_deal']][12]
   t['boundary_exit']='end of test' in t['exit_comment'].lower()
  m=r['net_metrics'];m['wilson_95_pct']=wilson(m['wins'],m['trades']);peak=10000.;dd=0
  m['test_end_liquidations']=sum(t['boundary_exit'] for t in r['trades'])
  m['test_end_net_usd']=round(sum(t['net_profit'] for t in r['trades'] if t['boundary_exit']),2)
  for d in ld:peak=max(peak,d['balance']);dd=max(dd,100*(peak-d['balance'])/peak)
  m['closed_balance_dd_pct']=dd
  start=r['manifest']['start'].replace('.','-');end=r['manifest']['end_exclusive'].replace('.','-')
  days=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days
  weekdays=sum(d.weekday()<5 for d in run.pd.date_range(start,run.pd.Timestamp(end)-run.pd.Timedelta(days=1)))
  m['trades_per_month']=m['trades']/(days/30.4375);m['trades_per_weekday']=m['trades']/weekdays
  m['avg_hold_hours']=sum(t['hold_hours'] for t in ts)/len(ts) if ts else None
  results[cid]=r
 return results,build
RESULTS,BUILD=verify()
def rows(ids):
 out=[]
 for cid in ids:
  r=RESULTS[cid];m=r['net_metrics'];n=r['native'];v=r['manifest']
  out.append([cid,v['start'].replace('.','-')+' → '+v['end_exclusive'].replace('.','-')+' excl.',m['trades'],num(m['trades_per_month']),num(m['trades_per_weekday']),pct(m['return_pct']),num(m['net_pf']),num(m['win_rate_pct'])+'%' if m['win_rate_pct'] is not None else 'N/A',
   num(n['equity_dd_pct'])+'%',num(m['closed_balance_dd_pct'])+'%',num(n.get('sharpe_ratio')),num(n.get('recovery_factor')),str(m['max_win_streak'])+'/'+str(m['max_loss_streak']),n['history_quality']])
 return out
HEAD=['Case','Start → end exclusive','Trades','/ month','/ weekday','Return','Net PF','Net WR','Native equity DD','Closed balance DD','MT5 Sharpe','Recovery','Max W/L','History quality']
def ledger(cid):return [(d['epoch'],d['balance']) for d in RESULTS[cid]['ledger']]
def trace(cid):
 d=run.pd.read_csv(R/'native'/cid/'trace.csv');return [(float(a),float(b)) for a,b in zip(d.time,d.equity)]
def graph(title,series,caption,start,end):
 W=1100;H=300;L=84;T=22;B=34;RR=22
 vs=[v for _,p,_ in series for _,v in p]+[10000];lo=min(vs);hi=max(vs);pad=max(20,(hi-lo)*.08);lo-=pad;hi+=pad
 first=datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp();last=datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()
 def x(t):return L+(t-first)/(last-first)*(W-L-RR)
 def y(v):return T+(hi-v)/(hi-lo)*(H-T-B)
 svg=f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">'
 for i in range(5):
  v=lo+(hi-lo)*i/4;yy=y(v);svg+=f'<line x1="{L}" y1="{yy:.1f}" x2="{W-RR}" y2="{yy:.1f}" stroke="#294337"/><text x="{L-9}" y="{yy+4:.1f}" text-anchor="end">USD {v:,.0f}</text>'
 for label,p,color in series:
  if len(p)>1300:p=p[::max(1,len(p)//1250)]+[p[-1]]
  coords=' '.join(f'{x(t):.2f},{y(v):.2f}' for t,v in [(first,10000)]+p)
  svg+=f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.2"/>'
 svg+=f'<text x="{L}" y="{H-5}">{esc(start)}</text><text x="{W-RR}" y="{H-5}" text-anchor="end">{esc(end)} exclusive</text></svg>'
 keys=' '.join(f'<span style="color:{c}">● {esc(label)}</span>' for label,_,c in series)
 return f'<section class="panel graph"><h2>{esc(title)}</h2><p>{esc(caption)}</p>{svg}<div class="legend">{keys}</div></section>'
def gate(cid):
 m=RESULTS[cid]['net_metrics'];co=RESULTS['CONTROL'+cid]['net_metrics']
 checks=dict(positive_net=m['net_profit']>0,pf_ge_1_15=m['net_pf'] is not None and m['net_pf']>=1.15,positions_ge_30=m['trades']>=30,
  clean_execution=not any(RESULTS[cid]['flags'].values()),mean_net_R_above_control=m['mean_net_initial_R'] is not None and co['mean_net_initial_R'] is not None and m['mean_net_initial_R']>co['mean_net_initial_R'])
 return dict(checks=checks,passed=all(checks.values()))
GATES={w:gate(w) for w in ['3Y','5Y']};verdict='RAW_GATE_PASS_REVIEW_REQUIRED' if all(x['passed'] for x in GATES.values()) else 'RAW_GATE_FAIL_NO_OPTIMISATION'
run.save(R/'summary.json',dict(verdict=verdict,gates=GATES,results={k:dict(metrics=v['net_metrics'],native=v['native'],modules=v['module_metrics']) for k,v in RESULTS.items()},
 combined_raw_parameter_presets=1,standalone_masks_and_control_presets=5,native_cases=len(RESULTS),optimisation_performed=False,deployment_approved=False))
data=[dict(case=k,symbol=v['manifest']['symbol'],start=v['manifest']['start'],end_exclusive=v['manifest']['end_exclusive'],**{a:b for a,b in v['net_metrics'].items() if not isinstance(b,list)},native_equity_dd_pct=v['native']['equity_dd_pct'],history_quality=v['native']['history_quality']) for k,v in RESULTS.items()]
with (R/'FINAL SUMMARY.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
for cid in ['1Y','A1Y','B1Y','C1Y']:
 tt=[{k:v for k,v in t.items() if k not in ['signal_audit','risk_audit']} for t in RESULTS[cid]['trades']]
 if tt:
  with (R/(cid+' positions.csv')).open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=list(tt[0]));w.writeheader();w.writerows(tt)
style='''*{box-sizing:border-box}body{margin:0;background:#07110e;color:#eafff5;font:16px/1.6 "Segoe UI",Arial,sans-serif}main{max-width:1350px;margin:auto;padding:50px 28px}h1{font-size:clamp(34px,5vw,60px);line-height:1.12;letter-spacing:-1.5px}h2{font-size:24px;line-height:1.25;margin:0 0 15px}h3{margin:4px 0 10px}.kicker{color:#8dffd4;font-size:12px;letter-spacing:2px}p{color:#adc4ba}.panel{margin:22px 0;padding:25px;border:1px solid #294337;border-radius:18px;background:#0c1a15}.alert{background:#242310;border-color:#716b28;color:#ffeb9a}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{padding:20px;border:1px solid #294337;border-radius:14px;background:#0d1c17}.card strong{display:block;font-size:28px;color:#8dffd4}.scroll{max-width:100%;overflow-x:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:13px;white-space:nowrap}th,td{padding:12px 10px;text-align:right;border-bottom:1px solid #294337}th:first-child,td:first-child{text-align:left}th{color:#8dffd4;font-size:11px;text-transform:uppercase}td{color:#d1e7dc}svg{display:block;width:100%;height:auto}svg text{fill:#adc4ba;font:12px "Segoe UI",Arial}.legend{display:flex;gap:22px;flex-wrap:wrap;font-size:13px}a{color:#8dffd4}details{margin:15px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#adc4ba;font-size:13px}@media(max-width:750px){main{padding:26px 14px}.panel{padding:16px}.grid{grid-template-columns:1fr}h1{letter-spacing:-.6px}.legend{gap:8px}th,td{padding:9px 8px}}'''
style+='.card{min-width:0;overflow-wrap:anywhere}.grid{grid-template-columns:repeat(3,minmax(0,1fr))}@media(max-width:750px){.grid{grid-template-columns:minmax(0,1fr)}}'
y=RESULTS['1Y'];m=y['net_metrics']
body=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gold Speed Q4 Turn — raw research</title><style>{style}</style></head><body><main><div class="kicker">CALYX · QUANTLAB IDEA 04 · 5 OCT 2026 · RESEARCH ONLY</div><h1>Three gold ideas.<br>One shared-account raw test.</h1><p>Adaptive H4 momentum · Q4 H1 breakout · Turn-of-month. Public-idea reconstruction, not the subscription EA.</p><section class="panel alert"><strong>{esc(verdict.replace('_',' '))}</strong><p>Vendor numerical rules are hidden. Every numerical choice is ours, preregistered before results. This tests our interpretation, not a replication of private performance claims. No live bots, BATs, website or portfolio changed.</p></section><div class="grid"><div class="card">Shared starting balance<strong>$10,000</strong>1% current equity/entry; one slot/module</div><div class="card">Last year return<strong>{pct(m['return_pct'])}</strong>{m['trades']} complete net-cost positions</div><div class="card">Last year native equity DD<strong>{num(y['native']['equity_dd_pct'])}%</strong>Includes open floating P&amp;L</div></div><section class="panel"><h2>Raw combined portfolio — native MT5</h2><p>All modules trade the same balance, margin and floating equity at once, not a ledger overlay. Overnight/weekend holdings, broker spread/commission/swap and 150ms delay included. Lot floor; skip if minimum lot exceeds requested risk.</p>{table(HEAD,rows(['5Y','3Y','1Y','6M','3M']))}<p>PF and win rate are complete-position metrics after costs. MT5 Sharpe is the native platform measure, not annualised daily Sharpe. History quality includes 180-day no-trade warmup; Model4 generates ticks when recorded real ticks are absent. Older results are less reliable.</p></section>'''
body+=graph('Five years — shared native account',[('Actual closed balance',ledger('5Y'),'#8dffd4'),('Sampled floating equity',trace('5Y'),'#88acff')],'Five-minute equity samples thinned for display may miss tick extremes. Maximum equity DD in the table is authoritative native MT5.','2021-10-05','2026-10-05')
body+=graph('Last year — shared native account',[('Actual closed balance',ledger('1Y'),'#8dffd4'),('Sampled floating equity',trace('1Y'),'#88acff')],'Combined equity sizes each entry. The cash ledger includes entry costs.','2025-10-05','2026-10-05')
body+=f'<section class="panel"><h2>Standalone modules — last year</h2><p>Each is a separate $10,000 native test, not a contribution in the shared account.</p>{table(HEAD,rows(["A1Y","B1Y","C1Y"]))}'
if RESULTS['C1Y']['net_metrics']['trades']==0:
 body+='<p><strong>Important: month-turn had NO exposure last year.</strong> All12 monthly entry attempts were skipped because the broker minimum lot with the2×D1ATR stop would exceed the1% cash budget. Its flat result is not evidence of profitability or failure. The shared annual profit came from A/B only; older3Y/5Y did exercise C.</p>'
cirows=[]
for cid in ['A1Y','B1Y','C1Y','1Y']:
 mm=RESULTS[cid]['net_metrics'];ci=mm['wilson_95_pct']
 cirows.append([cid,num(ci[0])+'% – '+num(ci[1])+'%',num(mm['avg_win_usd']),num(mm['avg_loss_usd']),num(mm['expectancy_usd']),num(mm['mean_net_initial_R'],3),num(mm['avg_hold_hours'])])
body+=table(['Case','Win rate95% Wilson','Avg net winUSD','Avg net lossUSD','ExpectancyUSD','Mean net initialR','Mean hold hours'],cirows)+'</section>'
body+=graph('Standalone module balances',[('Adaptive H4',ledger('A1Y'),'#8dffd4'),('Q4 H1',ledger('B1Y'),'#88acff'),('Month-turn',ledger('C1Y'),'#e5b3f5')],'Separate balances; do not add these curves to infer shared equity.','2025-10-05','2026-10-05')
contr=[[run.LABELS[k],mm['trades'],num(mm['net_profit']),num(mm['net_pf']),num(mm['win_rate_pct'])+'%' if mm['win_rate_pct'] is not None else 'N/A',str(mm['max_win_streak'])+'/'+str(mm['max_loss_streak'])] for k,mm in y['module_metrics'].items()]
body+=f'<section class="panel"><h2>Module contributions — shared year</h2><p>Sum to combined net profit; native sizing can differ from standalone accounts.</p>{table(["Module","Trades","NetUSD","Net PF","Net WR","Max W/L"],contr)}</section>'
body+=f'<section class="panel"><h2>Last complete Q4 — seasonal diagnostic</h2><p>The recent six-/three-month windows cover summer plus only the first October weekdays; little exposure to the Q4 module. The last complete Q4 was preregistered, not chosen after results.</p>{table(HEAD,rows(["Q42025"]))}</section>'
body+=graph('Last complete Q4 — all three together',[('Shared native balance',ledger('Q42025'),'#8dffd4')],'1Oct–31Dec2025; not a locked out-of-sample test.','2025-10-01','2026-01-01')
gr=[[w,'PASS' if g['passed'] else 'FAIL',num(RESULTS[w]['net_metrics']['mean_net_initial_R'],3),num(RESULTS['CONTROL'+w]['net_metrics']['mean_net_initial_R'],3),'; '.join(k for k,v in g['checks'].items() if not v) or 'None'] for w,g in GATES.items()]
body+=f'<section class="panel"><h2>Preregistered raw gate and controls</h2>{table(["Window","Raw gate","Strategy mean netR","Control mean netR","Failed requirements"],gr)}<p>Positive net, PF≥1.15, ≥30 positions and mean netR above control on both3Y/5Y, clean execution required. Raw pass is not full validation.</p>{table(HEAD,rows(["CONTROL3Y","CONTROL5Y"]))}<p>A/B control randomises signal direction with one fixed seed; changed exits affect future eligibility, so entry frequency is not exactly matched. C control buys weekdays10–12. Diagnostic only, not significance proof. Overlapping raw windows are not untouched holdouts.</p></section>'
body+=f'<section class="panel"><h2>XAG validation — frozen transfer</h2><p>Same parameters on XAGUSD; no silver tuning. Minimum-lot skips: {RESULTS["XAG1Y"]["counters"]["minlot_skips"]}.</p>{table(HEAD,rows(["XAG1Y"]))}</section>'
body+=graph('Silver transfer — frozen raw rules',[('Shared XAGUSD balance',ledger('XAG1Y'),'#e5b3f5')],'Portability check only, not a deployment recommendation.','2025-10-05','2026-10-05')
rules=[('A · Adaptive H4','ATR14 above50-ATR average uses6-bar momentum/breakout, otherwise24. ±0.5ATR movement, EMA100 slope and close beyond preceding extreme. SL2.5ATR/noTP; original-distance closed-bar trailing from+1R.'),
 ('B · Q4 H1','October–December entries. Expanding ATR14; break preceding60-bar extreme near outer10% of480-bar range. SL2ATR/TP2.5R; original-distance closed-bar trailing from+1R.'),
 ('C · Month-turn','Long last weekday first eligible tick, exit last15min of second weekday next month. Protective2×D1ATR14/noTP. Weekdays, not predicted holiday calendar.'),
 ('All settings ours','Shared10k,1%currentequity/entry,max3(one/module),lot floor/minimumskip. UTC clock. No fabricated vendor daily guard/adaptive cash-risk multiplier. Tester-only/hedging-only.')]
body+='<section class="panel"><h2>Exact interpretation — numerical rules are ours</h2><div class="grid">'+''.join('<div class="card"><h3>'+esc(a)+'</h3><p>'+esc(b)+'</p></div>' for a,b in rules)+'</div><p><a href="PROTOCOL.txt">Full frozen rules</a> · <a href="run-config.json">Preregistered cases</a> · <a href="EA/Calyx Gold Speed Q4 Turn Research.mq5">Tester-only source</a></p></section>'
tt=[[t['number'],t['module_name'],t['side'],t['open_time'],t['close_time'],num(t['volume']),num(t['initial_sl']),num(t['initial_tp']) if t['initial_tp'] else 'None',num(t['net_profit']),num(t['hold_hours']),t['result'],t['exit_comment']] for t in y['trades']]
body+=f'<section class="panel"><h2>Every shared-account trade — last year</h2>{table(["#","Module","Side","OpenedUTC","ClosedUTC","Lots","InitialSL","InitialTP","NetUSD","Hours","Result","Exit comment"],tt)}<p>Test-end forced closes: {m["test_end_liquidations"]}, netUSD {num(m["test_end_net_usd"])}. Each window starts flat; it does not inherit positions from earlier dates.</p><p><a href="1Y positions.csv">Year positionsCSV</a> · <a href="FINAL SUMMARY.csv">All metricsCSV</a></p></section>'
au=[[cid,r['net_metrics']['trades'],r['audit']['max_concurrent_positions'],num(r['audit']['max_actual_stop_risk_to_budget'],4),r['counters']['minlot_skips'],r['counters']['trails'],'PASS'] for cid,r in RESULTS.items()]
costs=[[cid,num(sum(t['gross_profit'] for t in r['trades'])),num(sum(t['commission'] for t in r['trades'])),num(sum(t['swap'] for t in r['trades'])),num(sum(t['fee'] for t in r['trades'])),num(r['net_metrics']['net_profit']),r['net_metrics']['test_end_liquidations'],num(r['net_metrics']['test_end_net_usd'])] for cid,r in RESULTS.items() if cid in ['5Y','3Y','1Y','6M','3M','XAG1Y']]
body+=f'<section class="panel"><h2>Native cash costs and boundary exits</h2>{table(["Case","GrossUSD","CommissionUSD","SwapUSD","FeesUSD","NetUSD","Test-end exits","Test-end netUSD"],costs)}<p>Spread is embedded in executable bid/ask prices, not subtracted a second time. Boundary exits are forced liquidation at test end, not normal strategy exits. Starting each window flat can change signals and sizing versus uninterrupted live trading.</p></section>'
body+=f'<section class="panel"><h2>Execution and evidence audit</h2>{table(["Case","Positions","Max concurrent","Max stop-risk/budget","Min-lot skips","Trails","Execution"],au)}<p>Exact DEAL_POSITION_ID pairing, net costs, native totals, accepted signal algebra and calendars verified. Delay/gaps can exceed selected initial risk. Equity trace is sampled, not a prop-rule certification path.</p><details><summary>Compiler and frozen hashes</summary><pre>{esc(json.dumps(BUILD,indent=2))}</pre></details><p><a href="verification.json">Verification receipt</a> · <a href="summary.json">Structured gates</a> · <a href="native/1Y/report.htm.gz">Compressed native year report</a></p></section>'
body+='''<section class="panel"><h2>Sources and next step</h2><p>Public module/timeframe labels: <a href="https://api-quantlab.com/algorithmen/funded-xauusd-3x-momentum">QuantLab gold overview</a> · <a href="https://api-quantlab.com/algorithmen/funded-xauusd-3x-momentum/analyse">public deep dive</a>, read5Oct2026. Exact settings subscription-masked; no private-content bypass attempted.</p><p>Stop here for review. No optimisation, Monte Carlo, FTMO payout simulation or production promotion in this raw step. Raw failure needs explicit exploratory approval before searching settings. Live account unchanged.</p></section></main></body></html>'''
for before,after in [('above50-ATR','above its 50-ATR'),('uses6-bar','uses 6-bar'),('otherwise24','otherwise 24'),('±0.5ATR','±0.5 ATR'),('SL2.5ATR/noTP','SL 2.5 ATR, no TP'),('from+1R','from +1R'),('preceding60-bar','preceding 60-bar'),('outer10% of480-bar','outer 10% of the 480-bar'),('SL2ATR/TP2.5R','SL 2 ATR, TP 2.5R'),('last15min','last 15 minutes'),('Protective2×D1ATR14/noTP','Protective 2 × D1 ATR14 stop, no TP'),('Shared10k,1%currentequity/entry,max3(one/module),lot floor/minimumskip','Shared $10,000, 1% current equity per entry, max 3 positions (one/module), lot floor/minimum skip'),('All12','All 12'),('the2×D1ATR','the 2 × D1 ATR'),('the1%','the 1%'),('older3Y/5Y','older 3Y/5Y'),('both3Y/5Y','both 3Y/5Y'),('weekdays10–12','weekdays 10–12'),('read5Oct2026','read 5 Oct 2026'),('Model4','Model 4'),('≥30','≥ 30'),('PF≥1.15','PF ≥ 1.15'),('1Oct–31Dec2025','1 Oct–31 Dec 2025'),('Win rate95%','Win rate 95%')]:body=body.replace(before,after)
(R/'Results.html').write_text(body,encoding='utf-8')
run.save(R/'verification.json',dict(native_cases_verified=len(RESULTS),exact_position_mapping=True,native_cash_reconciliation=True,native_html_deal_row_crosscheck=True,signal_algebra=True,frozen_hashes=True,compile_clean=True,xag_present=True,
 raw_gate_verdict=verdict,html_sha256=run.sha(R/'Results.html'),optimisation=False,live_changes=False,deployment=False))
print(json.dumps(dict(verdict=verdict,annual=m,gates=GATES,cases=len(RESULTS)),indent=2))
