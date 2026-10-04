from pathlib import Path
import gzip, hashlib, json, os, shutil, subprocess, time
ROOT=Path(__file__).resolve().parent
TESTER=ROOT.parent/'_Backtests/MT5-DMC-20260811'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def run(cmd,**kw):return subprocess.run(cmd,creationflags=subprocess.CREATE_NO_WINDOW,**kw)
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def main():
 occupied=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True)
 assert occupied.returncode==0 and str(TESTER).lower() not in occupied.stdout.lower()
 net=run(['netstat','-ano','-p','TCP'],capture_output=True,text=True).stdout
 assert not any(':3000 ' in x and 'LISTENING' in x for x in net.splitlines())
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty'
 assert profile.is_dir() and not list(profile.glob('*.chr'))
 src=ROOT/'ExportRates.mq5';log=ROOT/'compile.log';began=time.time()
 run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log)[-2000:]
 dest=TESTER/'MQL5/Experts/AAA Research/Hourly20261003';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(src.with_suffix('.ex5'),dest/'ExportRates.ex5')
 header=read(ROOT.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=ROOT/'export.ini';ini.write_text(header+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Hourly20261003\\ExportRates
Symbol=USTEC
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=2
Optimization=0
FromDate=2021.10.02
ToDate=2026.10.03
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
 offsets={p:p.stat().st_size for p in logs()};began=time.time()
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 (ROOT/'owned-process.json').write_text(json.dumps({'pid':proc.pid,'executable':str(TESTER/'terminal64.exe')}))
 try:proc.wait(timeout=600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned collector timed out; live MT5 untouched')
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (ROOT/'export-journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and 'HOUR_EXPORT_OK' in journal,'Collector failed; inspect ignored journal'
 (ROOT/'data').mkdir(exist_ok=True);files=[]
 for name,out in [('US100Hourly20261003.csv','USTEC-M1.csv.gz'),('US100Hourly20261003-spec.csv','spec.csv')]:
  p=COMMON/name;assert p.exists() and p.stat().st_mtime>=began-2
  b=p.read_bytes();(ROOT/'data'/out).write_bytes(gzip.compress(b,mtime=0) if out.endswith('.gz') else b)
  files.append({'name':out,'uncompressed_sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
 result={'files':files,'elapsed_seconds':time.time()-began,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest(),'collector_messages':[x.split('   ')[-1] for x in journal.splitlines() if 'HOUR_EXPORT_' in x]}
 (ROOT/'EXPORT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
