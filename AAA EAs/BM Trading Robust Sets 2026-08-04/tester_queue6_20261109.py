"""Owner 2026-11-09: "focus only on fixing the nasdaq 5m for now". After the missed-signal replay, stop queue 5 (video ideas, USDJPY) and run only the
Nasdaq 5M carry-fix study. Paused work resumes later from its own files. Only Calyx research python processes and the isolated tester copy are stopped;
the normal MT5 is never touched."""
import subprocess, time
from pathlib import Path

B = Path(__file__).resolve().parent; EA_STORE = B.parent / 'EA store'; R = B / 'Nasdaq 5M Missed Signal 2026-11-09'; C = B / 'Nasdaq 5M Carry Fix 2026-11-09'


def ps(cmd): return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True).stdout


def stop(pattern):
    return ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','uv.exe') -and $_.CommandLine -match '" + pattern + "' } | ForEach-Object { 'stopped '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }")


def job(args, log):
    with open(log, 'w', encoding='utf-8') as f:
        code = subprocess.run(['uv', 'run', 'python', str(C / 'carry.py'), *args], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode
    print('carry', args, 'exit', code, flush=True); return code


while True:
    text = (R / 'replay.log').read_text(encoding='utf-8', errors='replace') if (R / 'replay.log').exists() else ''
    if 'journal lines' in text or 'Traceback' in text: break
    time.sleep(1)
for _ in range(3):
    print(stop('tester_queue5_20261109'), stop('Video ORB VWAP Ideas Raw'), stop('opt\\.py'), stop('phase_stats\\.py'), stop('nas\\.py'), flush=True); time.sleep(2)
print(ps("Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Where-Object { $_.ExecutablePath -match 'MT5-DMC-20260811' } | ForEach-Object { 'stopped tester '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
time.sleep(10)
if job(['native'], C / 'native.log') == 0 and job(['report'], C / 'report.log') == 0: job(['dion'], C / 'dion.log')
(C / 'DONE.flag').touch()
