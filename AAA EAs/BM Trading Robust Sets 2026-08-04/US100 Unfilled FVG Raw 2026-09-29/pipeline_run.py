"""Execute frozen raw protocol serially; no optimization or live-terminal calls."""
from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parent
for args in [['audit.py'],['run.py','screen'],['run.py','confirm'],['audit.py'],['report.py']]:
    print('STAGE',args,flush=True)
    subprocess.run([sys.executable,*args],cwd=R,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
