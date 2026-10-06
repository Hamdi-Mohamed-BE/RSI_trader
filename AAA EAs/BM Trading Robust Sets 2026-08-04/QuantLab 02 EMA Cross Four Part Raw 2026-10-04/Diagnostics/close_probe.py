"""One tiny simulated position, tester-only: diagnostic, not performance."""
from pathlib import Path
import subprocess,time,gzip
import run
R=run.R;T=run.T;folder=R/'Diagnostics';src=folder/'Historical Close Probe.mq5';log=src.with_suffix('.compile.log')
run.h.free()
si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si,timeout=180)
assert '0 errors, 0 warnings' in run.h.text(log)
dest=T/'MQL5/Experts/AAA Research/QuantLabNQBIndependent20261004/CloseProbe.ex5';run.shutil.copy2(src.with_suffix('.ex5'),dest)
text=(folder/'tester.ini').read_text(encoding='utf-8-sig').replace('FridayProbe','CloseProbe').replace('2025.10.04','2025.12.05').replace('2026.10.04','2025.12.08')
ini=folder/'close-tester.ini';ini.write_text(text,encoding='utf-8-sig')
offsets={p:p.stat().st_size for p in run.h.logfiles()};began=time.time();run.h.free()
proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
try:proc.wait(timeout=180)
except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise
assert proc.returncode==0
journal=''
for p in run.h.logfiles():
 if p.stat().st_mtime<began-2:continue
 with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
rows=sorted(set(s.split('PROBE_HIST_',1)[1] for s in journal.splitlines() if 'PROBE_HIST_' in s))
assert any('CLOSE time=' in s for s in rows)
run.save(folder/'historical-close.json',dict(tester_only=True,simulated_min_lot_diagnostic_not_performance=True,findings=rows))
print(*rows,sep='\n')
