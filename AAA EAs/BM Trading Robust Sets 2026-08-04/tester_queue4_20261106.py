"""One tester at a time (owner rule). The USDJPY search has more than a day of runs left and resumes from RUNS.jsonl, so it yields between two runs for two shorter jobs:
Nasdaq Overnight Protocol screen + Model 4 confirmation, then the Core 9 Sell Nasdaq parity. Only the USDJPY search processes and the isolated tester copy are stopped; the normal MT5 is never touched."""
import json, subprocess, time
from pathlib import Path

B = Path(__file__).resolve().parent; EA_STORE = B.parent / 'EA store'; U = B / 'USDJPY London Optimization 2026-11-05'; S = B / 'Nasdaq Overnight Protocol 2026-11-06'; P = B / '_00 Live profiles/Core 9/parity'


def ps(cmd):
    return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True).stdout


def job(script, stage, log):
    with open(log, 'w', encoding='utf-8') as f:
        code = subprocess.run(['uv', 'run', 'python', str(script), stage], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode
    print(script.parent.name, stage, 'exit', code, flush=True); return code


runs = U / 'RUNS.jsonl'; size = runs.stat().st_size
while runs.stat().st_size == size: time.sleep(2)
print('USDJPY finished a run; pausing the search', flush=True)
print(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','uv.exe') -and $_.CommandLine -match 'USDJPY London Optimization 2026-11-05.opt\\.py' } | ForEach-Object { $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
time.sleep(5)
print(ps("Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Where-Object { $_.ExecutablePath -match 'MT5-DMC-20260811' } | ForEach-Object { $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
time.sleep(10)

if job(S / 'study.py', 'native', S / 'native.log') == 0 and job(S / 'study.py', 'report', S / 'report.log') == 0:
    if json.loads((S / 'FINALISTS.json').read_text(encoding='utf-8')) is not None: job(S / 'study.py', 'confirm', S / 'confirm.log')
(S / 'DONE.flag').touch()
job(P / 'parity.py', 'native', P / 'native.log'); job(P / 'parity.py', 'report', P / 'report.log')

with open(U / 'opt.log', 'a', encoding='utf-8') as f:
    print('USDJPY search resuming', flush=True); code = subprocess.run(['uv', 'run', 'python', str(U / 'opt.py')], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode
print('USDJPY exit', code, flush=True)
