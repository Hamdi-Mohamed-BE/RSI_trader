"""One tester at a time (owner rule). The USDJPY search yields between two runs (it resumes from RUNS.jsonl) for the P7 portfolio streams; then the P7 FTMO jobs
run on the CPU while USDJPY continues. Only the USDJPY search processes and the isolated tester copy are stopped; the normal MT5 is never touched."""
import subprocess, time
from pathlib import Path

B = Path(__file__).resolve().parent; EA_STORE = B.parent / 'EA store'; U = B / 'USDJPY London Optimization 2026-11-05'; P = B / 'Portfolio P7 2026-11-10'
PD = ['uv', 'run', '--with', 'pandas', '--with', 'numpy', 'python', str(P / 'p7.py')]


def ps(cmd): return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True).stdout


runs = U / 'RUNS.jsonl'; size = runs.stat().st_size; t0 = time.time()
while runs.stat().st_size == size and time.time() - t0 < 1800: time.sleep(2)
for _ in range(3):
    print(ps("Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','uv.exe','bash.exe') -and $_.CommandLine -match 'opt\\.py' } | ForEach-Object { 'stopped '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True); time.sleep(2)
print(ps("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -match 'MT5-DMC-20260811' } | ForEach-Object { 'stopped tester '+$_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"), flush=True)
time.sleep(10)
with open(P / 'streams.log', 'w', encoding='utf-8') as f: print('streams exit', subprocess.run(PD + ['streams'], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode, flush=True)
with open(P / 'inputs.log', 'w', encoding='utf-8') as f: print('inputs exit', subprocess.run(PD + ['inputs'], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode, flush=True)
sims = subprocess.Popen(PD + ['runall', '4'], cwd=EA_STORE, stdout=open(P / 'runall.log', 'w', encoding='utf-8'), stderr=subprocess.STDOUT)
with open(U / 'opt.log', 'a', encoding='utf-8') as f:
    f.write('USDJPY search resuming after the P7 streams\n'); f.flush()
    usd = subprocess.Popen(['uv', 'run', 'python', str(U / 'opt.py')], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT)
print('P7 sims exit', sims.wait(), flush=True)
with open(P / 'report.log', 'w', encoding='utf-8') as f: print('report exit', subprocess.run(PD + ['report'], cwd=EA_STORE, stdout=f, stderr=subprocess.STDOUT).returncode, flush=True)
(P / 'DONE.flag').touch()
print('USDJPY exit', usd.wait(), flush=True)
