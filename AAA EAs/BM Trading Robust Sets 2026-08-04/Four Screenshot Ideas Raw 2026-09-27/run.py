"""Serial isolated native tests. No live API; no optimization or production writes."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
spec=importlib.util.spec_from_file_location('native_helpers',BASE/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
from app.mt5_evidence_jobs import _metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text());TESTER=h.TESTER
DEST=TESTER/'MQL5/Experts/AAA Research/Four Ideas 20260927'
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(message,**kw):save(ROOT/'status.json',dict(message=message,**kw));print(message,flush=True)
def free():
 for attempt in range(121):
  try:h.free();return
  except AssertionError:
   if attempt==120:raise
   time.sleep(5)
def compile_ea():
 free();log=ROOT/'compile.log';source=ROOT/'FourIdeas.mq5';begin=time.time()
 subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log);assert '0 errors, 0 warnings' in body,body
 assert source.with_suffix('.ex5').stat().st_mtime>=begin-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),DEST/'FourIdeas.ex5')
 save(ROOT/'BUILD.json',dict(source_sha=h.sha(source),binary_sha=h.sha(source.with_suffix('.ex5')),rules_sha=h.sha(ROOT/'RULES.md'),config_sha=h.sha(ROOT/'run-config.json'),compile=body[-400:]))
 status('Compiled four-idea research EA: 0 errors, 0 warnings')
def run(case,smoke=False):
 build=json.loads((ROOT/'BUILD.json').read_text())
 for path,key in [('FourIdeas.mq5','source_sha'),('FourIdeas.ex5','binary_sha'),('RULES.md','rules_sha'),('run-config.json','config_sha')]:assert h.sha(ROOT/path)==build[key]
 assert h.sha(DEST/'FourIdeas.ex5')==build['binary_sha']
 tag=('smoke-' if smoke else '')+case['id'];out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['ok'] and old['build']==build;status('Retained '+tag);return
 start,end=(CFG['smoke_from'],CFG['smoke_to']) if smoke else (CFG['from'],CFG['to'])
 vals=dict(InpMode=case['mode'],InpControl=str(case['control']).lower(),InpRiskPercent=1.0,InpNotionalUSD=10000.0,InpServerUtcOffsetHours=0,InpMagic=9274040,InpTag=tag)
 setname='fourideas-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 ini=out/'tester.ini';common=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Four Ideas 20260927\\FourIdeas
ExpertParameters={setname}
Symbol={case['symbol']}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\four-ideas-20260927\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=TESTER/'reports/four-ideas-20260927';reportdir.mkdir(parents=True,exist_ok=True)
 free();offsets={p:p.stat().st_size for p in h.logfiles()};begin=time.time();status('START '+tag,case=tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own research test timed out: '+tag)
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<begin-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 report=reportdir/(tag+'.htm');assert report.exists() and report.stat().st_mtime>=begin-2,('Missing fresh report',journal[-3000:])
 actual=h._report_inputs(report);bad=[k for k,v in vals.items() if k not in actual or not h._same_setting(str(v),actual[k])];assert not bad,(tag,bad)
 rb=h._read_report(report);assert all(v in rb for v in (start,end,case['symbol'],'M1'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(p,journal,re.I)) for k,p in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation',
  'invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed','margin_call':r'stop out|margin call',
  'entry_fail':r'IDEA_ENTRY_FAIL','close_fail':r'IDEA_CLOSE_FAIL','cancel_fail':r'IDEA_CANCEL_FAIL'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_volume')),flags
 trades=h._native_trades(report,tag);metrics=h._native_metrics(report)
 metrics.update(max_equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),max_balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')),max_equity_dd_usd=_number(_metric(rb,'Equity Drawdown Maximal')))
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.11,(tag,len(trades),metrics)
 (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0));save(out/'trades.json',trades)
 r=dict(ok=True,case=case,smoke=smoke,start=start,end=end,inputs=actual,metrics=metrics,flags=flags,build=build,report_sha=h.sha(report),
  elapsed_seconds=time.time()-begin,summary=re.findall(r'IDEA_SUMMARY[^\r\n]+',journal),symbol_spec=re.findall(r'IDEA_SPEC[^\r\n]+',journal),
  real_ticks=sorted(set(re.findall(r'real ticks begin from[^\r\n]+',journal))))
 save(out/'run.json',r);status('DONE '+tag+' '+json.dumps(metrics))
def main():
 if sys.argv[1]=='compile':compile_ea();return
 if sys.argv[1]=='smoke':
  for c in CFG['cases'][:4]:run(c,True)
 else:
  for c in CFG['cases']:run(c)
 status('COMPLETE '+sys.argv[1])
if __name__=='__main__':main()
