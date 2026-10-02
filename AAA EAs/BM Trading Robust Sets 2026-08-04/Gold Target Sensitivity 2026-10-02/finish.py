"""Finish the ongoing sweep, refresh derived metrics/charts, then render and verify."""
from pathlib import Path
import subprocess,sys,time
ROOT=Path(__file__).resolve().parent
deadline=time.monotonic()+90*60
print('Waiting for the current native sweep before post-processing.',flush=True)
while not (ROOT/'TRIALS.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Native sweep did not complete; no report was labelled finished.')
 time.sleep(2)
time.sleep(2)
for script in ['run.py','report.py','verify.py']:
 print('POSTPROCESS '+script,flush=True)
 subprocess.run([sys.executable,str(ROOT/script)],check=True)
print('ALL GOLD TARGET WORK COMPLETE AND VERIFIED.',flush=True)
