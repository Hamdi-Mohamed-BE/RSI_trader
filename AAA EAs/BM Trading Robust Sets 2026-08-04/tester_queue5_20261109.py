"""One tester at a time (owner rule). After the Core 9 Sell Nasdaq parity: the Nasdaq 5M missed-signal replay, the video ideas smoke + full raw run, then the
USDJPY search resumes (it continues from RUNS.jsonl). Only the USDJPY search processes and the isolated tester copy are ever stopped; the normal MT5 is never touched."""
import subprocess, time
from pathlib import Path

B = Path(__file__).resolve().parent; EA_STORE = B.parent / 'EA store'; U = B / 'USDJPY London Optimization 2026-11-05'; P = B / '_00 Live profiles/Core 9/parity'
R = B / 'Nasdaq 5M Missed Signal 2026-11-09'; S = B / 'Video ORB VWAP Ideas Raw 2026-11-09'


def ps(cmd): return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True).stdout


def job(script, args, log):
    with open(log, 'w', encoding='utf-8') as f:
        code = subprocess.run(['uv', 'run', 'python', str(script), *args], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode
    print(script.parent.name, args, 'exit', code, flush=True); return code


while not (P / 'DONE.flag').exists(): time.sleep(1)
for _ in range(3):
    print(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','uv.exe') -and $_.CommandLine -match 'USDJPY London Optimization 2026-11-05.opt\.py' } | ForEach-Object { 'stopped opt '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
    time.sleep(2)
print(ps("Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Where-Object { $_.ExecutablePath -match 'MT5-DMC-20260811' } | ForEach-Object { 'stopped tester '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
time.sleep(10)
job(R / 'replay.py', [], R / 'replay.log')
if job(S / 'study.py', ['smoke'], S / 'smoke.log') == 0:
    if job(S / 'study.py', ['native'], S / 'native.log') == 0: job(S / 'study.py', ['report'], S / 'report.log')
(S / 'DONE.flag').touch()
with open(U / 'opt.log', 'a', encoding='utf-8') as f:
    f.write('USDJPY search resuming after the video ideas run\n'); f.flush()
    code = subprocess.run(['uv', 'run', 'python', str(U / 'opt.py')], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode
print('USDJPY exit', code, flush=True)
