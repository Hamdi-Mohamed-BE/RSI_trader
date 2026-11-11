"""Best 1-Step (B1 = Core 9 + P4, 11 EAs) on the frozen FTMO engines (owner 2026-11-11: "show me performance on ftmo pass rate and average days to pass etc? and expected
monthly income in 100k account"). Same engines and stream as Portfolio P7 2026-11-10/p7.py (prop_select / nobuffer / f1_profile, $100k, 2021-10-07 -> 2026-10-06,
MC seeds unchanged); only the member list differs. B1 = guarded, B1U = no guard.
Jobs: FTMO 1-Step guard (f1g) / no guard (f1u), FTMO 2-step (ch), funded (fu, the frozen engine's FTMO STANDARD funded rules = 2-step funded account, NOT the 1-Step funded rules),
at 0.5 / 0.75 %. Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" [workers]"""
import importlib.util, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent
MEMBERS = ['3-way-gold#930930101', 'ema3', 'gold-band-wave', 'nasdaq-5m-candle-momentum', 'orb-volume-profile-volume-confirmed', 'overnight-bias-orb', 'sell-nasdaq-15min',
           'us100-selective-orb-v3', 'usdjpy-london-open-momentum', 'xau-rsi-vwap', 'xau-squeeze-momentum-standard']
JOBS = [(k, n, r) for r in ('0.50', '0.75') for k, n in (('f1g', 'B1'), ('f1u', 'B1U'), ('ch', 'B1'), ('ch', 'B1U'), ('fu', 'B1'), ('fu', 'B1U'))]


def p7():
    spec = importlib.util.spec_from_file_location('p7', B / 'Portfolio P7 2026-11-10/p7.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.H = H; return m


def inputs():
    f = H / 'INPUTS-B1.json'
    if f.exists(): return
    pool = json.loads((H / 'INPUTS-POOL.json').read_text(encoding='utf-8')); cands = [c for c in pool['candidates'] if c['ea'] in MEMBERS]
    assert {c['ea'] for c in cands} == set(MEMBERS); f.write_text(json.dumps(dict({k: v for k, v in pool.items() if k != 'candidates'}, candidates=cands), separators=(',', ':')), encoding='utf-8')
    print('INPUTS-B1', len(cands), flush=True)


def run(job):
    kind, name, risk = job; m = p7()
    if kind == 'f1u':
        orig = m.engines

        def eng():
            S, *rest = orig(); S.CANDIDATES['B1'] = dict(label='Best 1-Step', guard=True, risks=m.RISKS, members=None); S.CANDIDATES['B1U'] = dict(label='Best 1-Step no guard', guard=False, risks=m.RISKS, members=None)
            return (S, *rest)
        m.engines = eng; m.f1u(name, risk); return job
    S, F1, *_ = m.engines()
    S.CANDIDATES['B1'] = dict(label='Best 1-Step', guard=True, risks=m.RISKS, members=None); S.CANDIDATES['B1U'] = dict(label='Best 1-Step no guard', guard=False, risks=m.RISKS, members=None)
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk), 'fu': lambda: S.funded(name, risk)}[kind]()
    return job


if __name__ == '__main__':
    inputs(); todo = [j for j in JOBS if not (H / f"{dict(f1g='F1P', f1u='F1U', ch='CH', fu='FU')[j[0]]}-{j[1]}-{j[2]}.json").exists()]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 11) as ex:
        for j in ex.map(run, todo): print('finished', *j, flush=True)
    print('ALL DONE', flush=True)
