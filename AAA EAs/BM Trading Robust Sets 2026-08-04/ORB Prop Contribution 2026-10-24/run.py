"""ORB contribution to prop results: leave-one-out inside the frozen Portfolio Prop Comparison 2026-10-22 engine.
FTMO guarded 17 and Prop ready 9 at 0.5% (the packaged risk). Same streams, guards, MC seeds and rules; only the basket
changes. Python only, no MT5.  python run.py all
"""
import importlib.util, json, shutil, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent; SRC = B / 'Portfolio Prop Comparison 2026-10-22'
ORBS = ['us100-h1-orb-13utc', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30']
BASE = {'ftmo': ('FTMO17', 'FTMO17', True), 'prop-ready': ('DI_ON', 'CORE4_PLUS_FIVE_ORBS_05R', True)}


def engine():
    s = importlib.util.spec_from_file_location('compare', SRC / 'compare.py'); c = importlib.util.module_from_spec(s); s.loader.exec_module(c)
    original = c.setup

    def setup(stream):
        data, plan, events, epochs = original(stream)
        for base, (st, basket, _) in BASE.items():
            if st != stream: continue
            full = list(plan['baskets'][basket])
            plan['baskets'][f'{base}|ALL'] = full
            plan['baskets'][f'{base}|NO_ORBS'] = [e for e in full if e not in ORBS]
            for o in ORBS: plan['baskets'][f'{base}|minus {o}'] = [e for e in full if e != o]
        return data, plan, events, epochs
    c.setup = setup
    for base, (st, basket, guard) in BASE.items():
        for v in ['ALL', 'NO_ORBS'] + [f'minus {o}' for o in ORBS]:
            c.PORTFOLIOS[f'orbx-{base}-{v.replace(" ", "_")}'] = dict(label=f'{base} {v}', stream=st, basket=f'{base}|{v}', guard=guard)
    return c


def job(args):
    slug, part = args; c = engine(); c.run(slug, '0.50', part)
    f = SRC / f'RESULT-{slug}-0.50-{part}.json'; shutil.move(str(f), R / f.name); return f.name


if __name__ == '__main__':
    c = engine(); slugs = [s for s in c.PORTFOLIOS if s.startswith('orbx-')]
    jobs = [(s, 'challenge') for s in slugs] + [(s, 'funded') for s in slugs]
    jobs.sort(key=lambda j: (j[1] != 'funded', 'ftmo' not in j[0]))   # longest first
    with ProcessPoolExecutor(max_workers=10) as ex:
        for name in ex.map(job, jobs): print('saved', name, flush=True)
