"""Replay the exact promoted DI binary in the isolated tester, never live MT5."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,shutil,subprocess,time
ROOT=Path(__file__).resolve().parent
EXIT=ROOT.parent
BASE=EXIT.parent
spec=importlib.util.spec_from_file_location('isolated_runner',EXIT/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
EXPERT=BASE/'Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum DI EA.ex5'
SET=BASE/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R + DI AGREE M5 - HARD 1PCT.set'
OUT=ROOT/'native-di'

def main():
 assert r.sha(EXPERT)=='49c4f03622a8ec7fb8e70db990a2f19b3006b5641aeb915a5d7f2454f26bab35'
 assert r.sha(SET)=='8c28dd5522eb9a33f9f6033299beb996dfdcb29103f4ec773399ddac2076c1b9'
 OUT.mkdir(exist_ok=True)
 if (OUT/'run.json').exists():
  assert json.loads((OUT/'run.json').read_text())['ok'];print('Already completed; retained existing native evidence.',flush=True);return
 inputs=dict(line.split('=',1) for line in r.text(SET).splitlines() if '=' in line and not line.startswith(';'))
 protocol=dict(expert_sha256=r.sha(EXPERT),settings_sha256=r.sha(SET),symbol='USTEC',period='M5',start='2026.03.02',end='2026.08.31',model=4,delay_ms=150,inputs=inputs)
 r.save(ROOT/'NATIVE_FROZEN.json',protocol)
 r.free()
 dest=r.TESTER/'MQL5/Experts/AAA Research/Claude Nasdaq Followup 20260927';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(EXPERT,dest/'nasdaq-di.ex5')
 setname='claude-nasdaq-di-followup-20260927.set'
 shutil.copy2(SET,OUT/setname);shutil.copy2(SET,r.TESTER/'MQL5/Profiles/Tester'/setname)
 # Keep the existing isolated research account, without exposing it in outputs.
 template=(EXIT/'native/gold-native/tester.ini').read_text(encoding='utf-8-sig')
 common=template.split('[Experts]')[0]
 ini=OUT/'tester.ini'
 ini.write_text(common+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Claude Nasdaq Followup 20260927\\nasdaq-di
ExpertParameters='''+setname+'''
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2026.03.02
ToDate=2026.08.31
Report=reports\\claude-nasdaq-followup-20260927\\nasdaq-di.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 reportdir=r.TESTER/'reports/claude-nasdaq-followup-20260927';reportdir.mkdir(exist_ok=True)
 offsets={p:p.stat().st_size for p in r.logfiles()};began=time.time()
 print('START exact promoted Nasdaq DI, real ticks, 150 ms delay',flush=True)
 proc=subprocess.Popen(f'"{r.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=r.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=1500)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated tester timed out; live terminal untouched')
 journal=''
 for p in r.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:
   f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(r.TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (OUT/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 report=reportdir/'nasdaq-di.htm'
 assert report.exists() and report.stat().st_mtime>=began-2,('Missing fresh report',proc.returncode,journal[-2000:])
 actual=r._report_inputs(report)
 assert not [k for k,v in inputs.items() if k not in actual or not r._same_setting(v,actual[k])]
 body=r._read_report(report)
 assert all(t in body for t in ('2026.03.02','2026.08.31','USTEC','M5'))
 flags={key:len(re.findall(pattern,journal,re.I)) for key,pattern in {
  'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical|access violation',
  'invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed',
  'no_history':r'no history|history not found|waiting for history'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_stops','invalid_volume','no_history')),flags
 trades=r._native_trades(report,'Claude Nasdaq DI');metrics=r._native_metrics(report)
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.1
 (OUT/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 r.save(OUT/'trades.json',trades)
 result=dict(protocol,ok=True,elapsed_seconds=time.time()-began,inputs=actual,metrics=metrics,flags=flags,
             real_ticks=sorted(set(re.findall(r'real ticks begin from[^\r\n]*',journal))),report_sha256=r.sha(report))
 r.save(OUT/'run.json',result)
 assert r.sha(EXPERT)==protocol['expert_sha256'] and r.sha(SET)==protocol['settings_sha256']
 print('DONE '+json.dumps(dict(metrics=metrics,flags=flags,real_ticks=result['real_ticks'])),flush=True)
if __name__=='__main__':main()
