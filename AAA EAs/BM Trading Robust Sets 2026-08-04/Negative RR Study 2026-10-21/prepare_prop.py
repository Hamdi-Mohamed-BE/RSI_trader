"""Negative RR Study part B inputs: Best Prop 9 candidate streams per RR level (same builder as the Best Prop retest).

Nasdaq 5M DI OFF, USDJPY and Month End Flow come from this study's native runs at each level; RSI VWAP and the five
ORBs are the unchanged sources. Stop risk from trade geometry (verified identical to the stored risk rows).
Gate: the baseline stream must equal `Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_OFF.json` exactly.

python prepare_prop.py
"""
import hashlib, importlib.util, json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'; RT = B / 'Best Prop Portfolio Retest 2026-10-20'
DIOFF = B / 'FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16' / 'native' / 'allrr05-nasdaq-5m-candle-momentum-core-dioff-long-20261016'
N = 'nasdaq-5m-candle-momentum'
CHANGED = {N: '-dioff', 'usdjpy-london-open-momentum': '', 'us100-month-end-flow': ''}
EXPECT = {N: ('InpRewardRisk', {'InpUseFixedTarget': 'true', 'InpRequireDIAgreement': 'false'}),
          'usdjpy-london-open-momentum': ('InpTargetR', {'InpTargetMode': '1'}), 'us100-month-end-flow': ('InpRewardRisk', {})}
LEVELS = {'rr075': 0.75, 'rr060': 0.6, 'rr050': 0.5}
ORIGINAL = {N: 2.5, 'usdjpy-london-open-momentum': 1.0, 'us100-month-end-flow': 2.5}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


pr = load('pr', OLDER / 'prepare.py')


def geometry(slug, case, symbol):
    contract = {'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000.}[symbol]
    return {(slug, t['position_id']): dict(unit_risk=abs(t['open_price'] - t['sl']) * contract / (t['sl'] if symbol == 'USDJPY' else 1.)) for t in case['trades']}


def stream(src, lookup, level):
    begin, end = midnight(date(2021, 10, 7)), midnight(date(2026, 10, 6)); sources = dict(src); lk = {s: lookup for s in pr.SLUGS}; receipts = {}
    off = read(DIOFF / 'results.json'); assert off['inputs'].get('InpRequireDIAgreement') == 'false'
    sources[N] = dict(row=dict(src[N]['row']), case=off, folder=DIOFF); lk[N] = geometry(N, off, 'USTEC'); receipts[N] = dict(path=str(DIOFF / 'results.json'), sha256=sha(DIOFF / 'results.json'))
    if level:
        status = read(R / 'RUN_STATUS.json')['complete']
        for slug, suffix in CHANGED.items():
            st = status[f'{level}{suffix}|{slug}']; path = Path(st['path']); assert sha(path) == st['sha256']
            case = read(path); key, extra = EXPECT[slug]
            if level == 'base':  # fresh baseline: original targets, DI OFF for Nasdaq only
                extra = {k: v for k, v in extra.items() if k == 'InpRequireDIAgreement'}
                assert float(case['inputs'][key]) == ORIGINAL[slug] and all(case['inputs'][k] == v for k, v in extra.items()), ('inputs', slug, level)
                if slug == N: assert case['inputs']['InpUseFixedTarget'] == 'false'
            else:
                assert float(case['inputs'][key]) == LEVELS[level] and all(case['inputs'][k] == v for k, v in extra.items()), ('inputs', slug, level)
            sources[slug] = dict(row=dict(src[slug]['row']), case=case, folder=path.parent); lk[slug] = geometry(slug, case, src[slug]['row']['symbol'])
            receipts[slug] = dict(path=str(path), sha256=st['sha256'], inputs={k: case['inputs'][k] for k in [key, *extra]})
    cands = []
    for slug in pr.SLUGS: cands += pr.candidates(sources[slug], lk[slug], slug, begin, end)
    return dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=['2021-10-07', '2026-10-06']), receipts


def main():
    src, lookup, hashes = pr.load_sources(); out = R / 'prop'; out.mkdir(exist_ok=True); info = {}
    base, rec = stream(src, lookup, None)
    ref = read(RT / 'INPUTS-DI_OFF.json'); assert base == ref, 'baseline stream differs from the retest INPUTS-DI_OFF.json'
    (out / 'INPUTS-base.json').write_text(json.dumps(base, separators=(',', ':')), encoding='utf-8')
    info['base'] = dict(parity_vs_retest_inputs='exact', candidates=len(base['candidates']), receipts=rec)
    for level in ['base', *LEVELS]:
        name = 'base-fresh' if level == 'base' else level
        data, rec = stream(src, lookup, level)
        (out / f'INPUTS-{name}.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
        info[name] = dict(candidates=len(data['candidates']), per_ea={s: sum(c['ea'] == s for c in data['candidates']) for s in pr.SLUGS}, receipts=rec)
    info['unchanged_source_hashes'] = hashes
    (out / 'SOURCES.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    print(json.dumps({k: (v['candidates'] if isinstance(v, dict) and 'candidates' in v else None) for k, v in info.items()}, indent=1))


if __name__ == '__main__':
    main()
