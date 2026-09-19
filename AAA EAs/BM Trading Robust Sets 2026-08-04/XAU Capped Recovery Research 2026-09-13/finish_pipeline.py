from pathlib import Path
import json,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
# The baseline owns the isolated tester until it has saved all four runs.
while not (ROOT/'baseline.json').exists():time.sleep(5)
if not (ROOT/'selection.json').exists():subprocess.run([sys.executable,str(ROOT/'run_batch.py')],cwd=ROOT,check=True)
if not (ROOT/'final.json').exists():subprocess.run([sys.executable,str(ROOT/'run_research.py'),'--stage','final'],cwd=ROOT,check=True)
if not (ROOT/'diagnostics.json').exists():subprocess.run([sys.executable,str(ROOT/'run_research.py'),'--stage','diagnostics'],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(ROOT/'verify_research.py')],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(ROOT/'make_report.py')],cwd=ROOT,check=True)
