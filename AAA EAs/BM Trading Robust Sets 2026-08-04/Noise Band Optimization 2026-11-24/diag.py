"""After the frozen decision (REJECTED_AT_VALIDATION): diagnostic table of the finalists and the raw WIDE on every window, per asset and per year.
OOS numbers of the finalists are DIAGNOSTIC ONLY (the decision was taken before they were computed) -> DIAG.json"""
import json, sys
from collections import defaultdict
sys.path.insert(0, '.'); import search as S  # noqa: E402
F = json.load(open(S.H / 'FINAL.json'))
cases = {'raw WIDE (M30, k1.4, 2 ATR stop, 2 ATR trail from +1R)': S.BASE}
for i, f in enumerate(F['finalists'], 1): cases[f'finalist {i}'] = f['cfg']
W = dict(dev=S.DEV, val=S.VAL, oos=S.OOS, last12m=('2025-11-21', '2026-11-21'), all=S.ALL)
out = {}
for name, c in cases.items():
    rows = S.ledger(c); yrs = defaultdict(float)
    for r in rows: yrs[r[0][:4]] += r[3]
    out[name] = dict(cfg=c, both={w: S.stats(rows, v) for w, v in W.items()}, USTEC={w: S.stats(rows, v, 'USTEC') for w, v in W.items()}, US500={w: S.stats(rows, v, 'US500') for w, v in W.items()},
                     years={k: round(v, 1) for k, v in sorted(yrs.items())})
json.dump(out, open(S.H / 'DIAG.json', 'w'), indent=1)
for n, v in out.items():
    print(n); [print('   both', w, {k: v['both'][w][k] for k in ('n', 'per_month', 'R', 'PF', 'win', 'DD')}) for w in W]
    print('   USTEC', {w: (v['USTEC'][w]['R'], v['USTEC'][w]['PF']) for w in W}); print('   US500', {w: (v['US500'][w]['R'], v['US500'][w]['PF']) for w in W}); print('   years', v['years'])
