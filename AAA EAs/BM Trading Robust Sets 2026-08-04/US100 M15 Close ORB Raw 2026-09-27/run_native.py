"""Sequential isolated native tests; imports parsers with live MT5 disabled."""
from pathlib import Path
import gzip,importlib.util,json,re,shutil,subprocess,sys,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
EXIT=BASE/'FTMO Exit Management Research 2026-09-27'
spec=importlib.util.spec_from_file_location('isolated_exit_runner',EXIT/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
CFG=json.loads((ROOT/'run-config.json').read_text());SOURCE=ROOT/'ORB15Close.mq5'
DEST=r.TESTER/'MQL5/Experts/AAA Research/ORB15 Close 20260927'

def compile_ea():
 r.free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{r.TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=r.text(log);assert '0 errors, 0 warnings' in body,body[-5000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'ORB15Close.ex5')
 r.save(ROOT/'BUILD.json',dict(source_sha256=r.sha(SOURCE),binary_sha256=r.sha(SOURCE.with_suffix('.ex5')),config_sha256=r.sha(ROOT/'run-config.json'),compile=body[-350:]))
 print('Compiled research EA: 0 errors, 0 warnings',flush=True)

def run_case(period,target):
 tag=period+'-'+target;folder=ROOT/'native'/tag;folder.mkdir(parents=True,exist_ok=True)
 done=folder/'run.json'
 if done.exists() and json.loads(done.read_text())['ok']:print('Retained '+tag,flush=True);return
 start,end=CFG['periods'][period];rr=CFG['targets'][target]
 vals=dict(InpRewardRisk=rr,InpRiskPercent=1.,InpServerUtcOffsetHours=0,InpCloseHourNY=15,InpCloseMinuteNY=55,InpMagic=9271530,InpAuditTag=tag,InpAuditStart=start+' 00:00')
 setname='orb15close-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
 (folder/setname).write_text(body,encoding='utf-8');(r.TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 common=(EXIT/'native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=folder/'tester.ini';ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ORB15 Close 20260927\\ORB15Close
ExpertParameters={setname}
Symbol=USTEC
Period=M15
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\orb15close-20260927\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=r.TESTER/'reports/orb15close-20260927';reportdir.mkdir(exist_ok=True)
 r.free();offsets={p:p.stat().st_size for p in r.logfiles()};began=time.time()
 print('START '+tag,flush=True)
 proc=subprocess.Popen(f'"{r.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=r.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=1500)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated test timed out: '+tag)
 journal=''
 for p in r.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(r.TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 rp=reportdir/(tag+'.htm');assert rp.exists() and rp.stat().st_mtime>=began-2,(tag,'No fresh report',journal[-2000:])
 actual=r._report_inputs(rp)
 # MT5 serializes datetime inputs as Unix seconds in native report inputs.
 expected={**vals,'InpAuditStart':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
 mismatch=[k for k,v in expected.items() if k not in actual or not r._same_setting(str(v),actual[k])]
 assert not mismatch,(tag,mismatch,actual)
 text=r._read_report(rp);assert all(v in text for v in (start,end,'USTEC','M15'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={key:len(re.findall(p,journal,re.I)) for key,p in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical|access violation','invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed','entry_fail':r'ORB15_ENTRY_FAIL','export_failed':r'ORB15_EXPORT_FAILED'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_stops','invalid_volume','export_failed')),flags
 trades=r._native_trades(rp,tag);metrics=r._native_metrics(rp)
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.1
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));r.save(folder/'trades.json',trades)
 exports=[p for p in (r.TESTER/'Tester').glob('Agent-*/MQL5/Files/ORB15_'+tag+'_bars.csv') if p.stat().st_mtime>=began-2]
 assert len(exports)==1,(tag,exports);shutil.copy2(exports[0],folder/'bars.csv')
 result=dict(ok=True,period=period,target=target,reward_risk=rr,start=start,end=end,delay_ms=150,inputs=actual,metrics=metrics,flags=flags,
  real_ticks=sorted(set(re.findall(r'real ticks begin from[^\r\n]*',journal))),summary=sorted(set(re.findall(r'ORB15_SUMMARY[^\r\n]*',journal))),
  elapsed=time.time()-began,binary_sha256=r.sha(SOURCE.with_suffix('.ex5')),source_sha256=r.sha(SOURCE),report_sha256=r.sha(rp))
 r.save(done,result);print('DONE '+tag+' '+json.dumps(dict(metrics=metrics,flags=flags,summary=result['summary'])),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='compile':compile_ea()
 elif sys.argv[1]=='case':run_case(sys.argv[2],sys.argv[3])
 elif sys.argv[1]=='grid':
  for period in ('latest6m','aligned'):
   for target in ('half','third'):run_case(period,target)
