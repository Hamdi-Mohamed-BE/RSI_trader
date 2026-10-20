"""Build the 26-EA candidate stream (16 FTMO-package + 10 normal EAs on XAUUSD/USTEC/USDJPY) and dev-window PFs. No outcomes.

python prepare_universe.py -> INPUTS-universe.json, UNIVERSE.json
"""
import importlib.util, json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'; SEARCH = B / 'FTMO Fastest Funded Search 2026-10-20'
PLAN = json.loads((R / 'PLAN.json').read_text(encoding='utf-8'))
spec = importlib.util.spec_from_file_location('pr', OLDER / 'prepare.py'); pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)


def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()


def sources(mapping, slugs):
    p = pr.read(pr.LONG / 'PLAN.json'); state = pr.read(pr.LONG / 'RUN_STATUS.json')
    lookup = {(x['key'], x['position_id']): x for x in pr.read(pr.LONG / 'RISK_ROWS.json')[mapping]}
    out = {}
    for slug in slugs:
        cid = p['mappings'][mapping][slug]; row = next(x for x in p['cases'] if x['case_id'] == cid); receipt = state['complete'][cid]
        for file, digest in row['production_hashes'].items():
            assert pr.sha(file) == digest, ('Production source changed', file)
        path = Path(receipt['path']); assert pr.sha(path) == receipt['sha256']
        out[slug] = dict(row=row, case=pr.read(path), folder=path.parent)
    return out, lookup


def pf_r(cands):
    rs = [(c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk'] for c in cands if c['unit_risk'] > 0]
    gains, losses = sum(r for r in rs if r > 0), -sum(r for r in rs if r < 0)
    return (round(gains / losses, 4) if losses else None), len(rs), round(sum(rs), 2)


def main():
    elig = json.loads((SEARCH / 'ELIGIBILITY.json').read_text(encoding='utf-8'))
    ftmo, extra = elig['eligible'], PLAN['part_b_universe']['extra_normal_eas']
    begin, end = midnight(date(2021, 10, 7)), midnight(date(2026, 10, 6)); dev_end = midnight(date(2023, 10, 6))
    cands, info, excluded = [], {}, {}
    for mapping, slugs in (('ftmo', ftmo), ('full-eas', extra)):
        src, lookup = sources(mapping, slugs)
        for slug in slugs:
            try:
                c = pr.candidates(src[slug], lookup, slug, begin, end)
            except AssertionError as exc:
                excluded[slug] = f'model assertion failed: {exc}'; continue
            dev = [x for x in c if x['op'] < dev_end]
            pf, n, total = pf_r(dev)
            info[slug] = dict(source=mapping, symbol=src[slug]['row']['symbol'], trades_5y=len(c), dev_trades=n, dev_pf_r=pf, dev_total_r=total)
            cands += c
    eligible = list(info)
    baskets = dict(LLN_ALL=eligible, LLN_PF095=[s for s in eligible if (info[s]['dev_pf_r'] or 0) > 0.95],
                   EDGE_PF110=[s for s in eligible if (info[s]['dev_pf_r'] or 0) > 1.10])
    data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=['2021-10-07', '2026-10-06'], eligible=eligible)
    (R / 'INPUTS-universe.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    (R / 'UNIVERSE.json').write_text(json.dumps(dict(eas=info, excluded=excluded, baskets=baskets), indent=1), encoding='utf-8')
    for s, v in sorted(info.items(), key=lambda kv: -(kv[1]['dev_pf_r'] or 0)):
        print(f"{s:38} {v['source']:9} {v['symbol']:7} dev trades {v['dev_trades']:4} PF_R {v['dev_pf_r']} total R {v['dev_total_r']}")
    print('excluded', excluded); print({k: len(v) for k, v in baskets.items()})


if __name__ == '__main__':
    main()
