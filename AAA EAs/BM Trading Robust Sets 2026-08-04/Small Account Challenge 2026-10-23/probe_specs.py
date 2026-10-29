"""Read Exness-MT5Trial16 symbol rules (min lot, step, contract, margin) in the ISOLATED tester with a print-only EA.
No orders, no live terminal. Output: SPECS.json."""
import importlib.util, json, re, shutil, subprocess, time
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
s = importlib.util.spec_from_file_location('h', B / 'FTMO Exit Management Research 2026-09-27/run.py'); h = importlib.util.module_from_spec(s); s.loader.exec_module(h)
T = h.TESTER; NAME = 'Spec Probe'; DEST = T / 'MQL5/Experts/AAA Research/SmallAccount20261023'

h.free()
src = R / 'EA' / (NAME + '.mq5'); log = R / 'EA' / (NAME + '.compile.log'); began = time.time()
subprocess.run(f'"{T / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
body = h.text(log); assert '0 errors, 0 warnings' in body, body[-3000:]
DEST.mkdir(parents=True, exist_ok=True); shutil.copy2(src.with_suffix('.ex5'), DEST / (NAME + '.ex5'))
ini = R / 'probe-tester.ini'
ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\SmallAccount20261023\\{NAME}
Symbol=USTEC
Period=M5
Deposit=100
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=150
Optimization=0
FromDate=2026.10.12
ToDate=2026.10.14
ForwardMode=0
Report=reports\\small-account-probe.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
offsets = {p: p.stat().st_size for p in h.logfiles()}; began = time.time()
proc = subprocess.run(f'"{T / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=T, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
journal = ''
for p in h.logfiles():
    if p.stat().st_mtime < began - 2: continue
    with p.open('rb') as f: f.seek(offsets.get(p, 0)); journal += f.read().decode('utf-16-le', errors='replace') + '\n'
specs = {}
for m in re.finditer(r'SPEC sym=(\S+) ([^\r\n]*)', journal):
    specs[m[1]] = {k: float(v) for k, v in re.findall(r'(\w+)=([-\d.]+)', m[2])}
acct = re.search(r'SPEC account ([^\r\n]*)', journal)
out = dict(server='Exness-MT5Trial16', leverage='1:2000 (tester setting)', symbols=specs, account=acct[1] if acct else None)
(R / 'SPECS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))
