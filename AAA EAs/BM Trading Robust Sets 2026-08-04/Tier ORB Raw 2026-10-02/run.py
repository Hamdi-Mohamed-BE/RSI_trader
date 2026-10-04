"""Frozen, sequential, tester-only ORB runs. Does not initialise the MT5 trading API."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, importlib.util, io, json, os, re, shutil, subprocess, sys, time

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('exit_native_helpers',BASE/'FTMO Exit Management Research 2026-09-27/run.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
TESTER=helper.TESTER
SOURCE=ROOT/'RawORB.mq5'
DEST=TESTER/'MQL5/Experts/AAA Research/Tier ORB 20261002'
OUT=ROOT/'native'
WINDOWS={'1y':('2025.10.02','2026.10.02'),'3y':('2023.10.02','2026.10.02'),'5y':('2021.10.02','2026.10.02'),'smoke':('2026.09.21','2026.09.26')}

def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compile_ea():
 helper.free()
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty'
 assert profile.is_dir() and not list(profile.glob('*.chr')),'Research profile must be empty'
 log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=helper.text(log)
 assert '0 errors, 0 warnings' in body,body[-1000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'RawORB.ex5')
 build={'source_sha256':sha(SOURCE),'binary_sha256':sha(SOURCE.with_suffix('.ex5')),'rules_sha256':sha(ROOT/'RULES.md'),'compiler_tail':body[-350:]}
 save(ROOT/'BUILD.json',build)
 print('Compiled: 0 errors, 0 warnings. Live attachment disabled.',flush=True)

def run_case(symbol,window):
 helper.free()
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty'
 assert profile.is_dir() and not list(profile.glob('*.chr'))
 tag=symbol+'-'+window;folder=OUT/tag;folder.mkdir(parents=True,exist_ok=True)
 start,end=WINDOWS[window]
 values=dict(InpRiskPercent=1.0,InpServerUtcOffsetHours=0,InpCloseHourNY=15,InpCloseMinuteNY=55,InpMagic=10021545,InpAuditTag=tag)
 manifest=dict(symbol=symbol,window=window,start=start,end=end,values=values,model=4,delay_ms=150,deposit=10000,currency='USD',leverage='1:2000',source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')),rules_sha256=sha(ROOT/'RULES.md'))
 frozen=folder/'manifest.json';done=folder/'run.json'
 if frozen.exists():assert json.loads(frozen.read_text())==manifest,'Frozen manifest mismatch'
 else:save(frozen,manifest)
 if done.exists():assert json.loads(done.read_text())['ok'];print('Retained '+tag,flush=True);return
 setname='tierorb-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in values.items())+'\n'
 (folder/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=helper.text(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=folder/'tester.ini'
 ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Tier ORB 20261002\\RawORB
ExpertParameters={setname}
Symbol={symbol}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\tierorb-20261002\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=TESTER/'reports/tierorb-20261002';reportdir.mkdir(parents=True,exist_ok=True)
 offsets={p:p.stat().st_size for p in helper.logfiles()};began=time.time()
 print('START '+tag,flush=True)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(ROOT/'owned-process.json',{'pid':proc.pid,'executable':str(TESTER/'terminal64.exe'),'started':began,'case':tag})
 try:proc.wait(timeout=3600)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own isolated tester timed out: '+tag)
 journal=''
 for p in helper.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 rp=reportdir/(tag+'.htm')
 assert rp.exists() and rp.stat().st_mtime>=began-2,tag+' produced no fresh report; inspect local ignored journal'
 actual=helper._report_inputs(rp)
 assert all(k in actual and helper._same_setting(str(v),actual[k]) for k,v in values.items()),'Report input mismatch'
 report=helper._read_report(rp)
 assert all(x in report for x in (start,end,symbol,'M5')),'Report window/symbol mismatch'
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(v,journal,re.I)) for k,v in dict(init_failed='initialization failed|INIT_FAILED',critical='access violation|critical error|array out of range|zero divide',invalid_stops='invalid stops',invalid_volume='invalid volume',entry_fail='RAWORB_ENTRY_FAIL',close_fail='RAWORB_CLOSE_FAIL',stopout='stop out|stop-out',start_changed='start time changed').items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_stops','invalid_volume')),'Execution error; inspect local ignored journal'
 trades=helper._native_trades(rp,tag);metrics=helper._native_metrics(rp)
 # The maximum relative percentage need not coincide with the largest dollar drawdown.
 from app.mt5_evidence_jobs import _metric, _number
 metrics['max_relative_equity_drawdown_pct']=_number(_metric(report,'Equity Drawdown Relative'))
 assert len(trades)==metrics['trades'],'Native trade-count mismatch'
 assert abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.1,'Native net P&L mismatch'
 exports=[p for p in (TESTER/'Tester').glob('Agent-*/MQL5/Files/RawORB_'+tag+'_signals.csv') if p.stat().st_mtime>=began-2]
 assert len(exports)==1,'No fresh signal audit'
 audit=list(csv.DictReader(exports[0].read_text().splitlines()))
 filled=[x for x in audit if x['retcode']=='10009']
 assert len(filled)==len(trades),'Filled-signal count mismatch'
 for x in filled:
  now=datetime.strptime(x['time'],'%Y.%m.%d %H:%M:%S');bar=datetime.strptime(x['signal_bar'],'%Y.%m.%d %H:%M:%S')
  assert (now-bar).total_seconds()>=300,'Unfinished signal candle'
  assert float(x['quoted_risk'])<=float(x['risk_budget'])+.02,'Risk rounding exceeds ceiling'
  side=int(x['side']);close=float(x['signal_close'])
  assert close>float(x['range_high']) if side>0 else close<float(x['range_low'])
 assert len(set(x['time'][:10] for x in filled))==len(filled),'Multiple fills on one date'
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 (folder/'signals.csv.gz').write_bytes(gzip.compress(exports[0].read_bytes(),mtime=0))
 save(folder/'trades.json',trades)
 notes=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin from|real ticks absent|generated ticks|ticks generated|start time changed|history quality)[^\r\n]*',journal,re.I)))
 result=dict(ok=True,manifest=manifest,metrics=metrics,flags=flags,real_tick_notes=notes,summary=sorted(set(re.findall(r'RAWORB_SUMMARY[^\r\n]*',journal))),symbol_specs=sorted(set(re.findall(r'RAWORB_SPEC[^\r\n]*',journal))),elapsed_seconds=round(time.time()-began,2),report_sha256=sha(rp),verified_input_count=len(values),verified_signals=len(filled))
 save(done,result)
 print('DONE '+tag+' '+json.dumps(metrics)+' flags='+json.dumps(flags),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='compile':compile_ea()
 elif sys.argv[1]=='smoke':run_case('USTEC','smoke')
 elif sys.argv[1]=='grid':
  for symbol in ('USTEC','US500'):
   for window in ('1y','3y','5y'):run_case(symbol,window)
 elif sys.argv[1]=='case':run_case(sys.argv[2],sys.argv[3])
