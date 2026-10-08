"""Research-only standalone entry/exit refresh. No live terminal or MT5 API.

Match strategy inputs to the actual FTMO manifest, but not its shared guard.
The subsequent offline overlay applies fixed-$50 sizing and shared guards.
"""
from pathlib import Path
import importlib.util, json, msvcrt, os, sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PRIOR = BASE / 'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
spec = importlib.util.spec_from_file_location('orb_native_helpers', PRIOR / 'run.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
n.R = ROOT / 'native-refresh'
n.R.mkdir(parents=True, exist_ok=True)
# A distinct test tag avoids overwriting the previous diagnostic exports.
# Instrumentation continues to export into its already verified common folder.
audit = n.R / 'ReadOnlyAudit.mqh'
if not audit.exists():
    audit.write_bytes((PRIOR / 'ReadOnlyAudit.mqh').read_bytes())

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, v): n.save(p, v)
def differences(actual, expected):
    return {k: [v, actual[k]] for k, v in expected.items()
            if k in actual and not n.h._same_setting(v, actual[k])
            and not any(s in k.lower() for s in ('risk', 'magic', 'expected', 'ftmo', 'case', 'write', 'tester'))}

def main():
    manifest = read(BASE / 'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    products = {p.slug: p for p in n.get_website_catalog()}
    plan = {r['slug']: r for r in read(PRIOR / 'PLAN.json')['setups']}
    sources = {}
    output = dict(window=[n.START, n.END], package_sha256=n.sha(BASE / 'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json'),
                  standalone_strategy_inputs_match_ftmo=True, guarded_native_portfolio=False, entries={})
    for entry in manifest['entries']:
        slug = entry['slug']
        prior_file = PRIOR / 'comparisons' / (slug + '.json')
        if prior_file.exists():
            q = read(prior_file)['current']
            if not differences(q['inputs'], entry['inputs']):
                output['entries'][slug] = dict(path=str(prior_file), kind='comparison-current', sha256=n.sha(prior_file), reused=True)
                print('VERIFIED REUSE ' + slug, flush=True)
                continue
        p = products[slug]
        # Normal catalogue sources own strategy rules; FTMO binaries only wrap guards.
        source = (BASE / p.expert_source).resolve().with_suffix('.mq5')
        if slug in plan:
            row = dict(plan[slug])
        else:
            row = dict(slug=slug, label=p.label, symbol=p.canonical, period=p.timeframe,
                       source=str(source), expert=str(source.with_suffix('.ex5')), preset=str(BASE / p.set_source),
                       candidate_overrides={}, production_hashes={str(f): n.sha(f) for f in
                           sorted(n.closure(source) | {source.with_suffix('.ex5'), (BASE / p.set_source).resolve()})})
        row['input_settings'] = dict(entry['inputs'])
        row['slug'] = slug
        # Ordinary SL targets are unchanged. 3-Way candidate needs its existing TP-only accessor.
        if slug != '3-way-gold': row['candidate_overrides'] = {}
        binary, build = n.build(row)
        # Different variant names are intentional; the helper adds only an exact "half" override.
        q = n.run_case(row, 'ftmo-current', binary, build)
        assert not differences(q['inputs'], entry['inputs']), differences(q['inputs'], entry['inputs'])
        f = n.R / 'native' / q['tag'] / 'results.json'
        output['entries'][slug] = dict(path=str(f), kind='native-current', sha256=n.sha(f), reused=False)
        if slug == '3-way-gold':
            half = n.run_case(row, 'half', binary, build)
            save(ROOT / 'FTMO_MARKET_3WAY_COMPARISON.json', n.comparison(row, q, half))
        save(ROOT / 'NATIVE_SOURCES.json', output)
    assert len(output['entries']) == 14
    save(ROOT / 'NATIVE_SOURCES.json', output)
    print('FTMO STRATEGY REFRESH COMPLETE: 14 sources, no live changes', flush=True)

if __name__ == '__main__':
    with (BASE / 'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0); msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        main()
