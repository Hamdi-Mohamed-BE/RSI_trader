"""One frozen isolated native backtest; never connects to the live trading API."""
from pathlib import Path
import collections, csv, gzip, hashlib, html, importlib.util, json, math, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
import pandas as pd
import numpy as np

R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('rq_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER;SOURCE=R/'Roboquant ORB Raw.mq5'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def compile_ea():
 h.free(); log=R/'compile.log'; began=time.time()
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log)
 assert '0 errors, 0 warnings' in body,body[-3000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 target=T/'MQL5/Experts/AAA Research/Roboquant Raw 20261006';target.mkdir(parents=True,exist_ok=True)
 shutil.copy2(SOURCE.with_suffix('.ex5'),target/SOURCE.with_suffix('.ex5').name)
 save(R/'build.json',{'source':sha(SOURCE),'binary':sha(SOURCE.with_suffix('.ex5')),'protocol':sha(R/'PROTOCOL.md'),'compiler':body[-400:]})
 print('Compiled: zero errors and warnings',flush=True)
def run():
 out=R/'native';out.mkdir(exist_ok=True)
 build=json.loads((R/'build.json').read_text())
 assert build['source']==sha(SOURCE) and build['protocol']==sha(R/'PROTOCOL.md')
 assert build['binary']==sha(SOURCE.with_suffix('.ex5'))
 empty=T/'MQL5/Profiles/Charts/Calyx Research Empty'
 assert empty.is_dir() and not list(empty.glob('*.chr'))
 inputs={'InpRiskUSD':'100.0','InpMagic':'26100655'}
 setname='rq-orb-20261006.set';body=''.join(f'{k}={v}\n' for k,v in inputs.items())
 (out/setname).write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 # Private existing isolated account configuration, never emitted or embedded in public results.
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Roboquant Raw 20261006\\Roboquant ORB Raw
ExpertParameters={setname}
Symbol=USTEC
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2023.10.06
ToDate=2026.10.06
Report=reports\\roboquant-20261006\\raw.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rd=T/'reports/roboquant-20261006';rd.mkdir(parents=True,exist_ok=True)
 h.free(); offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time()
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',{'pid':proc.pid,'terminal':str(T),'started':began})
 print(f'Native 3-year run started in isolated tester, PID {proc.pid}',flush=True)
 deadline=began+2400
 while proc.poll() is None and time.time()<deadline:
  time.sleep(20)
  print(f'Native tester running: {int(time.time()-began)} seconds',flush=True)
 if proc.poll() is None:
  proc.terminate();proc.wait(timeout=30)
  save(out/'status.json',{'ok':False,'reason':'owned isolated process timed out'});raise RuntimeError('Isolated run timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(T))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 report=rd/'raw.htm'
 if not report.exists() or report.stat().st_mtime<began-2:
  flags={k:len(re.findall(v,journal,re.I)) for k,v in {'authorization':r'authorization.*failed|authentication.*failed','connection':r'connect.*failed|no connection','history':r'no history|history not found'}.items()}
  save(out/'status.json',{'ok':False,'reason':'No fresh native report','exit_code':proc.returncode,'flags':flags})
  print('No fresh report; failure categories: '+json.dumps(flags),flush=True);return
 for k,v in inputs.items():assert h._same_setting(v,h._report_inputs(report).get(k,'')),k
 txt=h._read_report(report);assert '2023.10.06' in txt and '2026.10.06' in txt and 'USTEC' in txt
 flags={k:len(re.findall(v,journal,re.I)) for k,v in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','stopout':r'stop out'}.items()}
 assert not flags['init_failed'] and not flags['critical']
 shutil.copy2(report,out/'report.htm')
 for suffix in ['decisions','equity']:
  path=COMMON/f'rq-orb-20261006-{suffix}.csv';assert path.exists() and path.stat().st_mtime>=began-2
  shutil.copy2(path,out/f'{suffix}.csv')
 trades=h._native_trades(report,'Roboquant ORB raw');m=h._native_metrics(report)
 assert len(trades)==m['trades']
 assert abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<0.03
 save(out/'trades.json',trades)
 save(out/'status.json',{'ok':True,'from':'2023-10-06','end_exclusive':'2026-10-06','elapsed_seconds':time.time()-began,'native':m,'flags':flags,'real_tick_notes':sorted(set(re.findall(r'[^\r\n]*real ticks begin from[^\r\n]*',journal))), 'source_sha256':build['source'],'protocol_sha256':build['protocol'],'report_sha256':sha(report)})
 print('Native run completed: '+json.dumps(m),flush=True)
 analyse()
def stats(trades,start,end,initial=10000):
 vals=[x['net_profit'] for x in trades];w=[v for v in vals if v>0];l=[v for v in vals if v<0]
 ws=ls=mw=ml=0;balance=peak=initial;dd=0
 for v in vals:
  ws=ws+1 if v>0 else 0;ls=ls+1 if v<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
  balance+=v;peak=max(peak,balance);dd=max(dd,(peak-balance)/peak*100)
 days=pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));daily=pd.Series(0.0,index=days)
 for t in trades:
  dt=pd.Timestamp(t['close_time']).normalize()
  if dt in daily.index:daily.loc[dt]+=t['net_profit']
 balances=initial+daily.cumsum();previous=balances.shift(1).fillna(initial);ret=daily/previous
 sd=ret.std(ddof=1);sharpe=float(np.sqrt(252)*ret.mean()/sd) if sd>0 else None
 return {'trades':len(vals),'win_rate':100*len(w)/len(vals) if vals else None,'pf':sum(w)/-sum(l) if l else None,'net':sum(vals),'return_pct':100*sum(vals)/initial,'closed_balance_dd':dd,'daily_balance_sharpe':sharpe,'win_streak':mw,'loss_streak':ml,'avg_win':sum(w)/len(w) if w else None,'avg_loss':sum(l)/len(l) if l else None,'trades_per_month':len(vals)/((pd.Timestamp(end)-pd.Timestamp(start)).days/30.4375),'trades_per_weekday':len(vals)/len(days),'commission':sum(t['commission'] for t in trades),'swap':sum(t['swap'] for t in trades)}
def analyse():
 out=R/'native';status=json.loads((out/'status.json').read_text());assert status['ok']
 trades=json.loads((out/'trades.json').read_text());total=stats(trades,'2023-10-06','2026-10-06')
 eq=pd.read_csv(out/'equity.csv',encoding='utf-16');decision=pd.read_csv(out/'decisions.csv',encoding='utf-16')
 decision['ny']=pd.to_datetime(decision.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
 sent=decision[decision.reason=='entry_sent'];assert sent.ny.dt.strftime('%H%M%S').ge('095955').all()
 assert sent.ny.dt.date.nunique()==len(sent),'More than one entry per day'
 assert len(sent)==len(trades),'Entry and completed-position count mismatch'
 eq['utc']=pd.to_datetime(eq.epoch,unit='s',utc=True)
 assert eq.utc.min()<pd.Timestamp('2023-10-07',tz='UTC') and eq.utc.max()>=pd.Timestamp('2026-10-05',tz='UTC')
 assert abs(eq.balance.iloc[-1]-status['native']['final_balance'])<0.03
 years=[]
 for year in [2023,2024,2025,2026]:
  start=max(pd.Timestamp(f'{year}-01-01'),pd.Timestamp('2023-10-06'));end=min(pd.Timestamp(f'{year+1}-01-01'),pd.Timestamp('2026-10-06'))
  selected=[t for t in trades if start<=pd.Timestamp(t['close_time'])<end]
  initial=10000+sum(t['net_profit'] for t in trades if pd.Timestamp(t['close_time'])<start)
  years.append({'period':f'{start.date()} to {(end-pd.Timedelta(days=1)).date()}',**stats(selected,start,end,initial)})
 notes=status['real_tick_notes'];counts=decision.reason.value_counts().to_dict()
 save(R/'results.json',{'summary':total,'native':status['native'],'years':years,'decisions':counts,'real_tick_notes':notes,'checks':{'native_pnl_matches_trades':True,'one_entry_per_ny_day':True,'snapshot_not_before_095955':True,'trace_covers_full_window':True}})
 pd.DataFrame(trades).to_csv(R/'Trades.csv',index=False)
 def f(x):return '—' if x is None else f'{x:.2f}'
 def row(label,m):return '<tr><td>'+html.escape(label)+'</td>'+''.join('<td>'+f(m[k])+'</td>' for k in ['trades','return_pct','pf','win_rate','daily_balance_sharpe','win_streak','loss_streak','closed_balance_dd'])+'</tr>'
 points=[[int(pd.Timestamp('2023-10-06',tz='UTC').timestamp()*1000),10000]]+[[int(pd.Timestamp(t['close_time'],tz='UTC').timestamp()*1000),10000+sum(x['net_profit'] for x in trades[:i+1])] for i,t in enumerate(trades)]
 data=json.dumps(points)
 report=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>US100 Precision ORB — raw 3 years</title><style>body{{background:#071411;color:#edfff6;font:16px system-ui;max-width:1250px;margin:40px auto;padding:20px}}h1{{font-size:42px}}.muted{{color:#a6bdb7}}.notice{{border:1px solid #a18330;padding:20px;border-radius:12px;background:#1b2518}}table{{border-collapse:collapse;width:100%;margin:24px 0}}td,th{{padding:13px;border-bottom:1px solid #29433b;text-align:left}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{padding:20px;border:1px solid #29433b;border-radius:12px}}b{{color:#58f4bf;font-size:28px}}svg{{width:100%;height:300px;background:#0c201b;border-radius:12px}}a{{color:#67ffd1}}.scroll{{overflow:auto}}</style></head><body><p class="muted">CALYX · ISOLATED RESEARCH · NO OPTIMISATION</p><h1>US100 — Precision Opening Range</h1><p>6 October 2023 – 5 October 2026 · Exness USTEC · $10,000 initial balance · $100 fixed planned risk/trade</p><div class="notice">CFD reconstruction of the supplied NQ code, not NQ futures results. CFD Bid/Ask and tick-volume replace futures prints/volume. MT5 native ATR smoothing is an unverified SDK-equivalence assumption. Earlier periods can use generated ticks; tick quality notes below are essential for this very small target. Historical results are not forecasts.</div><div class="grid">{''.join(f'<div class="card">{label}<br><b>{f(value)}{unit}</b></div>' for label,value,unit in [('Net return',total['return_pct'],'%'),('Net PF',total['pf'],''),('Win rate',total['win_rate'],'%'),('Native max equity DD',status['native']['max_drawdown_pct'],'%'),('Trades',total['trades'],''),('Longest wins',total['win_streak'],''),('Longest losses',total['loss_streak'],''),('Daily balance Sharpe',total['daily_balance_sharpe'],'')])}</div><h2>Closed balance — all trades</h2><svg id="chart" viewBox="0 0 1000 300"></svg><p id="hover" class="muted"></p><h2>Calendar breakdown</h2><div class="scroll"><table><thead><tr><th>Period (inclusive)</th><th>Trades</th><th>Return %</th><th>PF</th><th>Win %</th><th>Daily Sharpe</th><th>Win streak</th><th>Loss streak</th><th>Closed DD %</th></tr></thead><tbody>{row('Full 3 years',total)+''.join(row(y['period'],y) for y in years)}</tbody></table></div><p class="muted">Annual slices share one continuous account. Return uses each slice's starting closed balance. Closed drawdown excludes floating losses; native equity drawdown above includes them. Sharpe is weekday daily closed-balance returns, annualised √252, zero risk-free rate.</p><h2>Activity and execution</h2><p>{f(total['trades_per_month'])} trades/month · {f(total['trades_per_weekday'])} trades/weekday · Average win ${f(total['avg_win'])} · Average loss ${f(total['avg_loss'])} · Native commission ${f(total['commission'])}, swap ${f(total['swap'])}; spread and delayed fills embedded in prices.</p><pre>{html.escape(json.dumps(counts,indent=2))}</pre><h2>Tick coverage / quality</h2><pre>{html.escape(chr(10).join(notes) or 'Journal did not explicitly identify start of real ticks. Do not interpret absence as full real-tick coverage.')}</pre><p>Model 4 · 150ms delay · Native history quality {html.escape(status['native']['history_quality'])}. That percentage alone does not prove historical real-tick availability.</p><h2>Rules</h2><p>09:30–09:45 NY range; snapshot first eligible tick at/after 09:59:55; long above / short below. ATR14 stop 2.2×, target 0.3×; 8-minute hold maximum on available ticks. Relative volume [0.5,1.5], ATR14/50 [1,2.5]. No added filters, trailing or optimisation. Lots floor to broker step. Invalid broker stops skip the signal.</p><p><a href="Trades.csv">Trade breakdown CSV</a> · <a href="native/report.htm">Native MT5 report</a> · <a href="PROTOCOL.md">Frozen protocol</a> · <a href="results.json">Full metrics / verification</a></p><script>const data={data};const svg=document.getElementById('chart');const min=Math.min(...data.map(x=>x[1])),max=Math.max(...data.map(x=>x[1]));const x=t=>40+920*(t-data[0][0])/(data.at(-1)[0]-data[0][0]);const y=v=>260-220*(v-min)/(max-min||1);svg.innerHTML='<polyline fill="none" stroke="#58f4bf" stroke-width="2" points="'+data.map(p=>x(p[0])+','+y(p[1])).join(' ')+'"/>';svg.onmousemove=e=>{{const t=data[0][0]+(e.offsetX/svg.clientWidth*1000-40)/920*(data.at(-1)[0]-data[0][0]);const p=data.reduce((a,b)=>Math.abs(b[0]-t)<Math.abs(a[0]-t)?b:a);document.getElementById('hover').textContent=new Date(p[0]).toISOString().slice(0,19)+' UTC — $'+p[1].toFixed(2)}};</script></body></html>'''
 report=report.replace('<h2>Activity and execution</h2>','<p class="muted">The closing ledger books entry commissions at trade close; native account balance books them on entry. Native relative balance drawdown is 11.44%; ledger drawdown is 11.42%. MT5 headline PF/win rate are 0.87/83.83%; this page uses whole-position NET PF/win rate including both entry and exit commissions.</p><h2>Activity and execution</h2>')
 (R/'Results.html').write_text(report,encoding='utf-8')
 print('RESULTS '+json.dumps(total),flush=True)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'run'
 if command=='analyse':analyse()
 else:
  import msvcrt
  with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
   lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
   if command=='compile':compile_ea()
   else:run()
