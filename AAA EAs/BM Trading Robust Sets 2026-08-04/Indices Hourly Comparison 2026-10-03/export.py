"""No API full-year transfer (IPC frame limit); isolated native history export."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,time
R=Path(__file__).resolve().parent
T=R.parent/'_Backtests/MT5-DMC-20260811'
C=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def run(cmd,**kw):return subprocess.run(cmd,creationflags=subprocess.CREATE_NO_WINDOW,**kw)
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def main():
 occupied=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True)
 assert occupied.returncode==0 and str(T).lower() not in occupied.stdout.lower()
 net=run(['netstat','-ano','-p','TCP'],capture_output=True,text=True).stdout
 assert not any(':3000 ' in x and 'LISTENING' in x for x in net.splitlines())
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty'
 assert profile.is_dir() and not list(profile.glob('*.chr'))
 src=R/'ExportRates.mq5';log=R/'compile.log'
 run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log)[-2000:]
 dest=T/'MQL5/Experts/AAA Research/IndicesHourly20261003';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src.with_suffix('.ex5'),dest/'ExportRates.ex5')
 header=read(R.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 def logs():return list((T/'logs').glob('*.log'))+list((T/'Tester/logs').glob('*.log'))+list((T/'Tester').glob('Agent-*/logs/*.log'))
 (R/'data').mkdir(exist_ok=True);results=[]
 for symbol in ['US30','USTEC','US500']:
  ini=R/f'export-{symbol}.ini'
  ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\IndicesHourly20261003\\ExportRates
Symbol={symbol}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=2
Optimization=0
FromDate=2025.10.03
ToDate=2026.10.03
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
  offsets={p:p.stat().st_size for p in logs()};began=time.time()
  si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
  print('COLLECT',symbol,flush=True)
  proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
  (R/'owned-process.json').write_text(json.dumps({'pid':proc.pid,'executable':str(T/'terminal64.exe'),'config':str(ini)}))
  try:proc.wait(timeout=600)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated collector timed out; normal MT5 untouched')
  journal=''
  for p in logs():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
  (R/f'export-{symbol}-journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert proc.returncode==0 and f'INDEX_EXPORT_OK {symbol}' in journal,'Collector failed: '+symbol
  files=[]
  for name,out in [(f'IndicesHourly20261003-{symbol}.csv',f'{symbol}-M1.csv.gz'),(f'IndicesHourly20261003-{symbol}-spec.csv',f'{symbol}-spec.csv')]:
   p=C/name;assert p.exists() and p.stat().st_mtime>=began-2
   b=p.read_bytes();(R/'data'/out).write_bytes(gzip.compress(b,mtime=0) if out.endswith('.gz') else b)
   files.append({'name':out,'uncompressed_sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
  item={'symbol':symbol,'files':files,'elapsed_seconds':time.time()-began,'collector_messages':[x for x in journal.splitlines() if 'INDEX_EXPORT_' in x]}
  results.append(item);print('DONE',symbol,item['elapsed_seconds'],flush=True)
  (R/'EXPORT.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((R/'PROTOCOL.txt').read_bytes()).hexdigest(),'results':results},indent=2))
if __name__=='__main__':main()
