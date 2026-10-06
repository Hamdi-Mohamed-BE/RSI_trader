"""Non-trading native diagnosis of the three unexpected Friday carries."""
from pathlib import Path
import gzip,subprocess,time
import run
R=run.R;T=run.T;folder=R/'Diagnostics';src=folder/'Friday Availability.mq5';log=src.with_suffix('.compile.log')
run.h.free()
si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',
 creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si,timeout=180)
assert '0 errors, 0 warnings' in run.h.text(log)
dest=T/'MQL5/Experts/AAA Research/QuantLabNQBIndependent20261004/FridayProbe.ex5'
run.shutil.copy2(src.with_suffix('.ex5'),dest)
header=run.h.text(R.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
ini=folder/'tester.ini'
ini.write_text(header+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\QuantLabNQBIndependent20261004\\FridayProbe
Symbol=USTEC
Period=M3
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2025.10.04
ToDate=2026.10.04
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
offsets={p:p.stat().st_size for p in run.h.logfiles()};began=time.time();run.h.free()
proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,
 creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
try:proc.wait(timeout=180)
except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise
assert proc.returncode==0
journal=''
for p in run.h.logfiles():
 if p.stat().st_mtime<began-2:continue
 with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
rows=sorted(set(s.split('PROBE_',1)[1] for s in journal.splitlines() if 'PROBE_' in s))
assert any('DAY date=20251205' in s for s in rows)
run.save(folder/'availability.json',dict(read_only=True,no_orders=True,source_sha256=run.sha(src),
 binary_sha256=run.sha(src.with_suffix('.ex5')),findings=rows,seconds=round(time.time()-began,1)))
print(*rows,sep='\n')

