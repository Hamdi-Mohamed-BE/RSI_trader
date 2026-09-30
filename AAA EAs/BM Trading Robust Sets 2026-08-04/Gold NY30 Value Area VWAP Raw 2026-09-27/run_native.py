"""Serial isolated MT5 research; no live API. Frozen 2026-09-27."""
from pathlib import Path
import gzip,importlib.util,json,re,shutil,subprocess,sys,time,hashlib,os
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
EXIT=BASE/'FTMO Exit Management Research 2026-09-27'
spec=importlib.util.spec_from_file_location('isolated_exit_runner',EXIT/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
from app.mt5_evidence_jobs import _metric,_number,_percent_in_parentheses
CFG=json.loads((ROOT/'run-config.json').read_text(encoding='utf-8'))
SOURCE=ROOT/'GoldNY30.mq5';DEST=r.TESTER/'MQL5/Experts/AAA Research/Gold NY30 20260927'
def save(p,v):r.save(p,v)
def status(s,**kw):
 save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s,**kw))
 print(s,flush=True)
def compile_ea():
 r.free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{r.TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=r.text(log);assert '0 errors, 0 warnings' in body,body[-5000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'GoldNY30.ex5')
 save(ROOT/'BUILD.json',dict(source_sha256=r.sha(SOURCE),binary_sha256=r.sha(SOURCE.with_suffix('.ex5')),config_sha256=r.sha(ROOT/'run-config.json'),rules_sha256=r.sha(ROOT/'RULES.md'),compile=body[-350:]))
 status('Compiled: 0 errors, 0 warnings')
def frozen():
 b=json.loads((ROOT/'BUILD.json').read_text())
 for path,key in ((SOURCE,'source_sha256'),(SOURCE.with_suffix('.ex5'),'binary_sha256'),(ROOT/'run-config.json','config_sha256'),(ROOT/'RULES.md','rules_sha256')):
  assert r.sha(path)==b[key],('Frozen input changed',str(path))
 assert r.sha(DEST/'GoldNY30.ex5')==b['binary_sha256']
 return b
def run_case(period,variant,model=4):
 build=frozen();tag=f'{period}-{variant}-m{model}';folder=ROOT/'native'/tag;folder.mkdir(parents=True,exist_ok=True)
 done=folder/'run.json'
 if done.exists():
  old=json.loads(done.read_text())
  assert old['ok'] and old['source_sha256']==build['source_sha256'] and old['config_sha256']==build['config_sha256']
  status('Retained '+tag);return
 start,end=CFG['periods'][period]
 vals=dict(InpMode=CFG['variants'][variant],InpRiskPercent=1.0,InpRewardRisk=3.0,InpBins=64,InpValueArea=70.0,InpServerUtcOffsetHours=0,InpExcursionMinutes=15,InpRetestMinutes=10,InpMinStopSpread=3.0,InpMagic=9273030,InpAuditTag=tag)
 setname='ny30-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
 (folder/setname).write_text(body,encoding='utf-8');(r.TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 common=(EXIT/'native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=folder/'tester.ini';ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Gold NY30 20260927\\GoldNY30
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\gold-ny30-20260927\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=r.TESTER/'reports/gold-ny30-20260927';reportdir.mkdir(exist_ok=True)
 r.free();offsets={p:p.stat().st_size for p in r.logfiles()};began=time.time()
 status('START '+tag,case=tag)
 proc=subprocess.Popen(f'"{r.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=r.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated test timed out: '+tag)
 journal=''
 for p in r.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:
   f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(r.TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 rp=reportdir/(tag+'.htm');assert rp.exists() and rp.stat().st_mtime>=began-2,(tag,'No fresh report',journal[-2000:])
 actual=r._report_inputs(rp);mismatch=[k for k,v in vals.items() if k not in actual or not r._same_setting(str(v),actual[k])]
 assert not mismatch,(tag,mismatch,actual)
 report=r._read_report(rp);assert all(v in report for v in (start,end,'XAUUSD','M1'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={key:len(re.findall(p,journal,re.I)) for key,p in {
  'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical|access violation',
  'invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed',
  'entry_fail':r'NY30_ENTRY_FAIL','close_fail':r'NY30_CLOSE_FAIL','be_fail':r'NY30_BE_FAIL',
  'margin_call':r'stop out|margin call','no_history':r'no history|history not found'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_volume')),flags
 trades=r._native_trades(rp,tag);metrics=r._native_metrics(rp)
 metrics['max_equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
 metrics['max_balance_dd_pct']=_number(_metric(report,'Balance Drawdown Relative'))
 metrics['max_equity_dd_usd']=_number(_metric(report,'Equity Drawdown Maximal'))
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.11,(tag,len(trades),metrics)
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(folder/'trades.json',trades)
 for suffix in ('bars','profiles'):
  exports=[p for p in (r.TESTER/'Tester').glob('Agent-*/MQL5/Files/NY30_'+tag+'_'+suffix+'.csv') if p.stat().st_mtime>=began-2]
  assert len(exports)==1,(tag,suffix,exports)
  (folder/(suffix+'.csv.gz')).write_bytes(gzip.compress(exports[0].read_bytes(),mtime=0))
 result=dict(ok=True,tag=tag,period=period,variant=variant,model=model,start=start,end=end,delay_ms=150,inputs=actual,metrics=metrics,flags=flags,
  real_ticks=sorted(set(re.findall(r'real ticks begin from[^\r\n]*',journal))),summary=sorted(set(re.findall(r'NY30_SUMMARY[^\r\n]*',journal))),
  coverage_lines=sorted(set(re.findall(r'[^\r\n]*(?:real ticks|ticks generated|mismatch)[^\r\n]*',journal)))[:200],
  elapsed=time.time()-began,**{k:v for k,v in build.items() if k.endswith('sha256')},report_sha256=r.sha(rp))
 save(done,result);status('DONE '+tag+' '+json.dumps(dict(metrics=metrics,flags=flags)),case=tag)
def main():
 if sys.argv[1]=='compile':compile_ea()
 elif sys.argv[1]=='case':run_case(sys.argv[2],sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 4)
 elif sys.argv[1]=='smoke':
  for variant in CFG['variants']:run_case('smoke',variant)
 elif sys.argv[1]=='grid':
  for period in ('3y','5y'):
   for variant in CFG['variants']:run_case(period,variant,1)
  for period in ('6m','1y','3y','5y'):
   for variant in CFG['variants']:run_case(period,variant,4)
  status('COMPLETE: 24 raw comparison runs')
if __name__=='__main__':main()

