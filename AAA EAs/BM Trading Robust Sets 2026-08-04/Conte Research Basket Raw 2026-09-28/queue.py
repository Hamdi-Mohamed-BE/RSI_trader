"""Run the frozen research queue serially; stop on integrity failure."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
prop=None
for stage in ['year','recent','screen','confirm']:
 print('QUEUE STAGE',stage,flush=True)
 subprocess.run([sys.executable,str(root/'run.py'),stage],cwd=root,check=True)
 if stage=='year':
  subprocess.run([sys.executable,str(root/'analyze.py')],cwd=root,check=True)
  log=(root/'prop-progress.log').open('w',encoding='utf-8')
  prop=subprocess.Popen([sys.executable,str(root/'prop_sim.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  log.close()
  print('Offline prop replay started; native tester remains serial',prop.pid,flush=True)
if prop is not None:assert prop.wait()==0,'Read prop-progress.log'
print('NATIVE QUEUE COMPLETE',flush=True)
