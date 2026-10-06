from pathlib import Path
import importlib.util,os,gzip,subprocess,shutil,time,json,hashlib
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('native_er_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER
h.free()
log=R/'export.compile.log';began=time.time()
subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{R/"ExportM5.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
assert '0 errors, 0 warnings' in h.text(log),h.text(log)
dest=T/'MQL5/Experts/AAA Research/NasdaqER20261005';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'ExportM5.ex5',dest/'ExportM5.ex5')
header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
ini=R/'export.ini'
ini.write_text(header+'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\NasdaqER20261005\\ExportM5
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
Optimization=0
FromDate=2020.01.01
ToDate=2026.10.05
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free()
proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
(R/'export-process.json').write_text(json.dumps(dict(pid=proc.pid,started=began)))
try:proc.wait(timeout=900)
except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned research export timed out')
journal=''
for p in h.logfiles():
 if p.stat().st_mtime<began-2:continue
 with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
(R/'export-journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
f=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxNasdaqER20261005-M5.csv'
assert proc.returncode==0 and f.exists() and f.stat().st_mtime>=began-2,journal[-8000:]
assert 'ER_EXPORT_OK' in journal and 'ER_EXPORT_ERROR' not in journal
out=R/'data';out.mkdir(exist_ok=True);raw=f.read_bytes();(out/'USTEC-M5.csv.gz').write_bytes(gzip.compress(raw,mtime=0))
v=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),log=[x for x in journal.splitlines() if 'ER_EXPORT_OK' in x],seconds=time.time()-began)
(R/'export.json').write_text(json.dumps(v,indent=2));print(json.dumps(v),flush=True)
