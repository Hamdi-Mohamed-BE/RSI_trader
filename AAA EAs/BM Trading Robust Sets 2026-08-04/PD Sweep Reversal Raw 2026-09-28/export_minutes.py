"""Read-only, tester-isolated native M1 export for final signal eligibility audit."""
import gzip,json,shutil,subprocess,time
import run as runner
ROOT=runner.ROOT;TESTER=runner.TESTER
def main():
 runner.free();out=ROOT/'minute-audit';out.mkdir(exist_ok=True)
 log=out/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"ExportMinutes.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in runner.read(log),runner.read(log)
 assert (ROOT/'ExportMinutes.ex5').stat().st_mtime>=began-2
 dest=TESTER/'MQL5/Experts/AAA Research/PD Sweep Minute Audit 20260928';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'ExportMinutes.ex5',dest/'ExportMinutes.ex5')
 header=(ROOT/'native/BTC-M5-reversal-5y/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 for asset in ('BTC','US30','US100','XAU'):
  symbol=runner.CFG['symbols'][asset];cached=out/f'{asset}-M1.bin.gz'
  if cached.exists():continue
  runner.free();ini=out/f'{asset}.ini'
  ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\PD Sweep Minute Audit 20260928\\ExportMinutes
Symbol={symbol}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
Optimization=0
FromDate=2021.01.01
ToDate=2026.09.27
Report=reports\\pd-sweep-20260928\\minute-audit-{asset}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
  before={p:p.stat().st_size for p in runner.logs()};began=time.time();print('EXPORT',asset,flush=True)
  proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
  try:proc.wait(timeout=600)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise
  journal=''
  for p in runner.logs():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(before.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
  (out/f'{asset}.journal.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert 'PS_MINUTE_OK' in journal and 'PS_MINUTE_FAILED' not in journal
  source=runner.COMMON/f'{symbol}-M1.bin';assert source.stat().st_mtime>=began-2
  data=source.read_bytes();assert len(data)%48==0
  cached.write_bytes(gzip.compress(data,mtime=0))
  runner.save(out/f'{asset}.json',dict(symbol=symbol,rows=len(data)//48,sha256=runner.sha(cached),source_hash=runner.sha(ROOT/'ExportMinutes.mq5'),binary_hash=runner.sha(ROOT/'ExportMinutes.ex5'),seconds=time.time()-began,read_only=True))
  print('DONE',asset,len(data)//48,round(time.time()-began,1),flush=True)
if __name__=='__main__':main()
