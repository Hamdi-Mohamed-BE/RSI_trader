"""Negative RR Study — native 5-year runs (PLAN.md part A). Isolated tester only; never a live terminal or account.

Reuses the audited build/run_case of `ORB and Range Breakout RR05 Comparison 2026-10-08` (same ReadOnlyAudit export as
the long-history baselines). Only target inputs change. 3-Way Gold: tester-only TP accessor override for all modules.

python run_native.py parity | run
"""
import copy, hashlib, importlib.util, inspect, json, msvcrt, shutil, sys, time, traceback
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
LONG = B / 'Portfolio Long History All ORB05 2026-10-14'; OLD = B / 'Portfolio Long History 2026-10-08'
LOCK = B / 'LTA VWAP Developing POC Comparison 2026-10-05' / 'tester.lock'
spec = importlib.util.spec_from_file_location('rr05_native', B / 'ORB and Range Breakout RR05 Comparison 2026-10-08' / 'run.py')
n = importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
n.START, n.END = '2021.10.06', '2026.10.06'
LEVELS = {'rr075': 0.75, 'rr060': 0.6, 'rr050': 0.5}
OVR = {'dmc-current-xau': lambda x: {'InpRewardRisk': x}, 'dmc-fresh-reaction-us100': lambda x: {'InpRewardRisk': x},
       'ema3': lambda x: {'InpRewardRisk': x}, 'gold-overnight-value-area': lambda x: {'InpTargetR': x},
       'nasdaq-5m-candle-momentum': lambda x: {'InpUseFixedTarget': 'true', 'InpRewardRisk': x},
       'nasdaq-overnight': lambda x: {'InpRewardRisk': x}, 'us100-month-end-flow': lambda x: {'InpRewardRisk': x},
       # USDJPY's current exit is PIPELINE_TIME_EXIT (mode 0): InpTargetR is inactive unless the mode is PIPELINE_FIXED_R (1).
       'usdjpy-london-open-momentum': lambda x: {'InpTargetMode': '1', 'InpTargetR': x}, 'xau-squeeze-momentum-standard': lambda x: {'InpTargetR': x},
       '3-way-gold': lambda x: {'InpRR05ModuleTarget': x}}
PARITY = ['usdjpy-london-open-momentum', 'nasdaq-5m-candle-momentum']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def fmt(x): return f'{x:g}' if isinstance(x, float) else str(x)


# 3-Way Gold: same patch as the RR05 study, minus its "S[s].c<2" restriction (all three modules).
_src = inspect.getsource(n.build)
assert _src.count('S[s].c<2 && ') == 1 and _src.count("'TP accessor override for MOM/BRK only; baseline override is zero.'") == 1
_src = (_src.replace('S[s].c<2 && ', '').replace("'TP accessor override for MOM/BRK only; baseline override is zero.'",
        "'TP accessor override for ALL three modules (Negative RR Study 2026-10-21); baseline override is zero.'")
        .replace('def build(row):', 'def build_all_modules(row):'))
exec(compile(_src, 'build_all_modules', 'exec'), n.__dict__)


def base_rows():
    plan = read(LONG / 'PLAN.json'); state = read(LONG / 'RUN_STATUS.json'); out = {}
    for slug in OVR:
        cid = plan['mappings']['current14-orb05'][slug]
        out[slug] = (next(c for c in plan['cases'] if c['case_id'] == cid), state['complete'][cid])
    return out


def build(row):
    n.R = R / 'build'; n.R.mkdir(exist_ok=True)
    audit = R / 'build' / 'ReadOnlyAudit.mqh'
    if not audit.exists(): shutil.copy2(OLD / 'ReadOnlyAudit.mqh', audit)
    assert sha(audit) == sha(OLD / 'ReadOnlyAudit.mqh')
    return n.build_all_modules(row) if row['slug'] == '3-way-gold' else n.build(row)


def run_one(row, folder, variant):
    binary, info = build(row); n.R = R / folder; n.R.mkdir(exist_ok=True)
    return n.run_case(row, variant, binary, info)


def save_status(state): (R / 'RUN_STATUS.json').write_text(json.dumps(state, indent=1), encoding='utf-8')


def parity():
    rows = base_rows(); out = {}
    for slug in PARITY:
        row, receipt = rows[slug]; ref = read(receipt['path'])
        res = run_one(copy.deepcopy(dict(row, candidate_overrides={})), 'parity', 'base')
        sig = lambda t: (t['open_epoch'], t['close_epoch'], t['side'], t['open_price'], round(t['close_price'], 5), tuple(t['exit_comments']))  # noqa: E731
        a, b = res['trades'], ref['trades']
        out[slug] = dict(trades=len(a), reference_trades=len(b), signal_path_identical=len(a) == len(b) and all(sig(x) == sig(y) for x, y in zip(a, b)),
                         cash_identical=[(t['volume'], t['net']) for t in a] == [(t['volume'], t['net']) for t in b],
                         net=round(sum(t['net'] for t in a), 2), reference_net=round(sum(t['net'] for t in b), 2),
                         swap=round(sum(t['swap'] for t in a), 2), reference_swap=round(sum(t['swap'] for t in b), 2),
                         lot_size_differences=sum(x['volume'] != y['volume'] for x, y in zip(a, b)))
        print('PARITY', slug, json.dumps(out[slug]), flush=True)
        assert out[slug]['signal_path_identical'], ('native signal-path parity failed', slug)
    out['note'] = ('Signal path (entry/exit times, side, prices, exit reasons) must be identical to the stored baselines. Cash may differ '
                   'only through tester symbol specifications refreshed since the baselines (swap); every variant is therefore compared '
                   'with a FRESH baseline run in the same tester state (level base).')
    (R / 'NATIVE-PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def run():
    assert (R / 'NATIVE-PARITY.json').exists() and all(v['signal_path_identical'] for k, v in read(R / 'NATIVE-PARITY.json').items() if k != 'note'), 'run parity first'
    rows = base_rows(); jobs = []
    for slug, (row, _) in rows.items():  # fresh baselines in the current tester state
        jobs.append(('base', slug, row, {}))
    jobs.append(('base-dioff', 'nasdaq-5m-candle-momentum', rows['nasdaq-5m-candle-momentum'][0], {'InpRequireDIAgreement': 'false'}))
    for level, x in LEVELS.items():
        for slug, (row, _) in rows.items():
            jobs.append((level, slug, row, OVR[slug](x)))
        row = rows['nasdaq-5m-candle-momentum'][0]
        jobs.append((level + '-dioff', 'nasdaq-5m-candle-momentum', row, dict(OVR['nasdaq-5m-candle-momentum'](x), InpRequireDIAgreement='false')))
    state = read(R / 'RUN_STATUS.json') if (R / 'RUN_STATUS.json').exists() else dict(window=[n.START, n.END], total=len(jobs), complete={}, failed={})
    for level, slug, row, ov in jobs:
        key = f'{level}|{slug}'
        if key in state['complete']: continue
        r = copy.deepcopy(row); ov = {k: fmt(v) for k, v in ov.items()}
        r['input_settings'].update(ov); r['candidate_overrides'] = ov; r['case_id'] = f'{slug}-{level}'
        try:
            res = run_one(r, level, 'half'); p = R / level / 'native' / res['tag'] / 'results.json'
            state['complete'][key] = dict(path=str(p), sha256=sha(p), trades=len(res['trades']), seconds=round(res['seconds']),
                                          overrides=ov, history_quality=res['native']['history_quality'])
            state['failed'].pop(key, None)
        except Exception as e:
            state['failed'][key] = dict(error=str(e), trace=traceback.format_exc()[-4000:]); print('FAILED', key, e, flush=True)
        save_status(state); print('PROGRESS', len(state['complete']), '/', state['total'], key, flush=True)
    assert not state['failed'], state['failed']
    print('ALL NATIVE RUNS COMPLETE; no production/live changes', flush=True)


if __name__ == '__main__':
    with LOCK.open('a+b') as lock:
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        {'parity': parity, 'run': run}[sys.argv[1]]()
