"""Unmodified current 5M DI/wide-stop/ATR strategy transferred to Exness DE30.
Native isolated Strategy Tester only. No active account API or live profile writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,io,json,msvcrt,os,re,shutil,subprocess,time
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('native_transfer_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER
SRC=B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5'
SET=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
WINDOWS={'3m':('2026-07-07','2026-10-07'),'6m':('2026-04-07','2026-10-07'),'1y':('2025-10-07','2026-10-07')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def inputs():
 values={}
 for line in SET.read_text(encoding='utf-8-sig').splitlines():
  if '=' in line and not line.startswith(';'):k,v=line.split('=',1);values[k]=v.split('||')[0].strip()
 values['InpRiskPercent']='1.0';values['InpAdaptivePortfolioControls']='false'
 return values
def streaks(trades):
 w=l=mw=ml=0
 for t in trades:
  p=t['net_profit'];w=w+1 if p>0 else 0;l=l+1 if p<0 else 0;mw=max(mw,w);ml=max(ml,l)
 return {'maximum_win_streak':mw,'maximum_loss_streak':ml}
def finish_metrics(manifest,metrics,trades,report,journal,seconds,reused=None):
 assert len(trades)==metrics['trades'],'Missing completed positions'
 assert abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.051,'Native cash ledger does not reconcile'
 netwins=sum(t['net_profit']>0 for t in trades);grosswins=sum(max(0,t['net_profit']) for t in trades);losses=-sum(min(0,t['net_profit']) for t in trades)
 from app.mt5_evidence_jobs import _metric,_number
 metrics['return_pct']=round(metrics['net_profit']/10000*100,4)
 metrics['native_win_rate_pct']=metrics['win_rate_pct']
 metrics['win_rate_pct']=round(netwins/len(trades)*100,4) if trades else 0
 metrics['net_profit_factor']=round(grosswins/losses,6) if losses else None
 metrics['floating_equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
 metrics['closed_balance_dd_pct']=_number(_metric(report,'Balance Drawdown Relative'))
 metrics.update(streaks(trades))
 times=[datetime.fromisoformat(t['open_time']) for t in trades]
 entry_days=len(set(t.date() for t in times))
 metrics['days_with_entries']=entry_days
 metrics['avg_trades_per_active_entry_day']=round(len(trades)/entry_days,4) if entry_days else 0
 metrics['avg_net_per_trade']=round(metrics['net_profit']/len(trades),4) if trades else 0
 metrics['median_hold_hours']=None
 if trades:
  import statistics
  metrics['median_hold_hours']=round(statistics.median((datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds()/3600 for t in trades),4)
 warnings={label:len(re.findall(pattern,journal,re.I)) for label,pattern in {'invalid_stops':'invalid stops','invalid_volume':'invalid volume','market_closed':'market closed','not_enough_money':'not enough money','entry_rejection':'order rejected','history_problem':'not enough history|start time changed','minimum_rounding_overrides':'actual risk exceeds the selected target'}.items()}
 tick_notes=sorted(set(line.strip() for line in journal.splitlines() if re.search(r'(DE30|USTEC).*(real ticks begin|real ticks absent|ticks discarded|generated)',line,re.I)))[:60]
 # Broker real-tick files begin in January 2026; annual tests include older generated ticks.
 quality='mixed_real_and_generated' if manifest['start']<'2026-01-02' else 'real_tick_period_requested'
 if re.search(r'(real ticks absent|ticks discarded)', '\n'.join(tick_notes),re.I):quality='real_ticks_with_gaps_or_discarded_segments'
 return dict(manifest=manifest,metrics=metrics,warnings=warnings,tick_notes=tick_notes,data_quality=quality,seconds=seconds,reused_source=reused,live_changed=False,boundary_exits=sum('end of test' in t['exit_comment'].lower() for t in trades),native_report_sha256=hashlib.sha256(report.encode()).hexdigest())
def case(symbol,window):
 start,end=WINDOWS[window];tag=symbol+'-'+window;out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 values=inputs()
 manifest=dict(symbol=symbol,window=window,start=start,end_exclusive=end,time_zone='UTC / tester server offset zero',period='M5',deposit=10000,currency='USD',risk_percent_equity=1,model=4,execution_delay_ms=150,binary_sha256=sha(SRC.with_suffix('.ex5')),source_sha256=sha(SRC),base_preset_sha256=sha(SET),inputs=values,unchanged_rules=True)
 frozen=out/'manifest.json'
 if frozen.exists():
  assert json.loads(frozen.read_text())==manifest,'Frozen test differs; retain it and select a fresh named run'
  if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 save(frozen,manifest)
 if symbol=='USTEC' and window=='3m':
  old=B/'Five EA Portfolio Standalone 2026-10-07/NativeTests/N5-ORIGINAL1'
  previous=json.loads((old/'manifest.json').read_text());assert previous['binary_sha256']==manifest['binary_sha256'] and previous['inputs']==values and previous['start']==start and previous['end_exclusive']==end and previous['delay_ms']==150,'Cached Nasdaq control does not match'
  rp=out/'reference.htm';rp.write_bytes(gzip.decompress((old/'report.htm.gz').read_bytes()))
  trades=h._native_trades(rp,'Nasdaq');report=h._read_report(rp);journal=gzip.decompress((old/'journal.txt.gz').read_bytes()).decode()
  result=finish_metrics(manifest,h._native_metrics(rp),trades,report,journal,0,str(old.relative_to(B)))
  (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(out/'trades.json',trades);save(out/'results.json',result)
  print('REUSED exact Nasdaq 3m control',flush=True);return result
 h.free()
 empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr')),'Non-empty isolated live profile'
 dest=T/'MQL5/Experts/AAA Research/N5Germany20261007';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(SRC.with_suffix('.ex5'),dest/(tag+'.ex5'))
 setname='n5-germany-'+tag+'.set';body='\n'.join(k+'='+v for k,v in values.items())+'\n'
 (out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 reportdir=T/'reports/n5-germany-20261007';reportdir.mkdir(exist_ok=True);rp=reportdir/(tag+'.htm')
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\N5Germany20261007\\{tag}
ExpertParameters={setname}
Symbol={symbol}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
ForwardMode=0
Report=reports\\n5-germany-20261007\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 began=time.time();offsets={p:p.stat().st_size for p in h.logfiles()}
 save(R/'status.json',dict(message='Running '+tag,started_utc=datetime.now(timezone.utc).isoformat()))
 print('START '+tag+' '+start+' to '+end,flush=True)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=1800)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timeout; normal terminal untouched')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh native report'
 assert not re.search(r'initialization failed|start time changed|not enough history|stop out|margin call|access violation|array out of range|zero divide',journal,re.I),'Native test invalid'
 actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in values.items()),'Native settings mismatch'
 report=h._read_report(rp);assert start.replace('-','.') in report and end.replace('-','.') in report and 'M5' in report,'Native dates/timeframe mismatch'
 metrics=h._native_metrics(rp);trades=h._native_trades(rp,symbol)
 assert all(t['symbol']==symbol for t in trades),'Wrong asset traded'
 result=finish_metrics(manifest,metrics,trades,report,journal,round(time.time()-began,1))
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(out/'trades.json',trades)
 if trades:
  with (out/'Trades.csv').open('w',encoding='utf-8-sig',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=list(trades[0]));writer.writeheader();writer.writerows(trades)
 save(out/'results.json',result)
 print('DONE '+tag+' '+json.dumps(metrics),flush=True);return result
def main():
 lock=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 original={str(p):sha(p) for p in (SRC,SRC.with_suffix('.ex5'),SET)}
 try:
  results=[]
  for window in WINDOWS:
   for symbol in ('DE30','USTEC'):results.append(case(symbol,window))
  assert all(sha(Path(path))==digest for path,digest in original.items()),'Production file changed'
  save(R/'RESULTS.json',dict(results=results,production_unchanged=True,production_fingerprints=original,no_live_deployment=True,no_optimisation=True))
  save(R/'status.json',dict(message='Complete: six comparisons',completed_utc=datetime.now(timezone.utc).isoformat()))
  print('COMPLETE: six research comparisons; live files unchanged.',flush=True)
 finally:lock.close()
if __name__=='__main__':main()
