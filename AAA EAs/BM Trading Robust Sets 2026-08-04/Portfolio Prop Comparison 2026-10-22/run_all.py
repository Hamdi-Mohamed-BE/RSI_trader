"""Run every portfolio x risk x part of compare.py, 10 processes at a time; skips results that already exist."""
import subprocess, sys, time
from pathlib import Path

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
JOBS = [(p, r, part) for part in ('funded', 'challenge') for p in ('ftmo', 'current14-orb05', 'orbs-only', 'prop-ready', 'best-prop')
        for r in ('0.50', '0.75', '1.00')]
WORKERS = 10

if __name__ == '__main__':
    pending = [j for j in JOBS if not (R / f'RESULT-{j[0]}-{j[1]}-{j[2]}.json').is_file()]; running = []
    while pending or running:
        while pending and len(running) < WORKERS:
            p, r, part = pending.pop(0); log = (R / f'log-{p}-{r}-{part}.txt').open('w')
            running.append(((p, r, part), subprocess.Popen([sys.executable, str(R / 'compare.py'), 'run', p, r, part], stdout=log, stderr=subprocess.STDOUT, cwd=R), log))
            print('START', p, r, part, flush=True)
        for item in list(running):
            job, proc, log = item
            if proc.poll() is not None:
                log.close(); running.remove(item); print('END' if proc.returncode == 0 else 'FAIL', *job, proc.returncode, flush=True)
        time.sleep(5)
    print('ALL DONE', flush=True)
