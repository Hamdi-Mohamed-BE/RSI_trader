"""Native five-year source runs for the prop portfolio selection (owner 2026-11-03: "compare all portfolios and do everything needed
to find the best one to run on prop accounts"). Same audited long-history harness as Portfolio Long History 2026-10-08 / All ORB05
2026-10-14 (isolated tester, ReadOnlyAudit equity marks, 2021-10-06 -> 2026-10-06, Model 4, 150 ms). Only what those runs lack:
  - Nasdaq 5M with the deployed ATR(14)x6 initial stop (2026-11-02), DI ON and DI OFF;
  - ORB Volume Profile Volume Confirmed at 0.5R (funded_v1 preset).
Each row = the existing long-history case with only those inputs changed. Run from AAA EAs/EA store: uv run python "<this>"
"""
import copy, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent; BASE = ROOT.parent
spec = importlib.util.spec_from_file_location('long_history_runner', BASE / 'Portfolio Long History 2026-10-08/run.py')
m = importlib.util.module_from_spec(spec); sys.path.insert(0, str(BASE / 'Portfolio Long History 2026-10-08')); spec.loader.exec_module(m)
m.ROOT = ROOT; m.n.R = ROOT
LONG = BASE / 'Portfolio Long History All ORB05 2026-10-14'
plan = json.loads((LONG / 'PLAN.json').read_text(encoding='utf-8-sig'))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def derive(case_id, changes, label):
    base = next(c for c in plan['cases'] if c['case_id'] == case_id); row = copy.deepcopy(base)
    row['input_settings'].update(changes)
    row['production_hashes'] = {p: sha(p) for p in base['production_hashes']}        # current files (SETs were patched on 2026-11-02)
    sig = hashlib.sha256(json.dumps([row['source'], row['input_settings']], sort_keys=True).encode()).hexdigest()[:12]
    row['case_id'] = f"{row['slug']}-{sig}"; row['derived_from'] = case_id; row['label'] = label
    return row


ROWS = [derive('nasdaq-5m-candle-momentum-0fba68cc8a1c', dict(InpStopMode='0', InpInitialStopATR='6.0', InpRequireDIAgreement='true'), 'Nasdaq 5M ATR6 DI ON'),
        derive('nasdaq-5m-candle-momentum-0fba68cc8a1c', dict(InpStopMode='0', InpInitialStopATR='6.0', InpRequireDIAgreement='false'), 'Nasdaq 5M ATR6 DI OFF'),
        derive('orb-volume-profile-volume-confirmed-68d9e26b8768', dict(InpRewardRisk='0.5'), 'ORB VP Volume Confirmed 0.5R')]

if __name__ == '__main__':
    m.prepare_helpers()
    state = json.loads((ROOT / 'RUN_STATUS.json').read_text()) if (ROOT / 'RUN_STATUS.json').exists() else dict(complete={}, failed={})
    (ROOT / 'NATIVE_PLAN.json').write_text(json.dumps(ROWS, indent=1), encoding='utf-8')
    for row in ROWS:
        if row['case_id'] in state['complete']: continue
        print('RUN', row['label'], row['case_id'], flush=True)
        binary, build = m.n.build(row); result = m.n.run_case(row, 'long-' + row['case_id'].split('-')[-1], binary, build)
        p = ROOT / 'native' / result['tag'] / 'results.json'
        state['complete'][row['case_id']] = dict(path=str(p), sha256=sha(p), trades=len(result['trades']), history_quality=result['native']['history_quality'],
                                                 net=result['native'].get('net_profit'), label=row['label'])
        (ROOT / 'RUN_STATUS.json').write_text(json.dumps(state, indent=1), encoding='utf-8')
        print('DONE', row['label'], len(result['trades']), 'trades', result['native'].get('net_profit'), result['native']['history_quality'], flush=True)
