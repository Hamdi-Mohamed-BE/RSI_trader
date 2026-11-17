"""No-opposite-trade rule (owner 2026-11-17, after FundingPips support said a buy and a sell on the same symbol is forbidden hedging,
even from two independent strategies). Rule: going through the trades in open order, a trade is SKIPPED if, when it opens, an accepted
trade on the same symbol in the opposite direction is still open. Skipped trades block nothing. Same-direction stacking is unchanged.
Writes INPUTS-NOHEDGE.json (same format as the source) + NOHEDGE.json (what was removed). python nohedge.py"""
import json
from collections import defaultdict
from pathlib import Path

import sim

H = Path(__file__).resolve().parent
D = json.loads(sim.SRC_BASE.read_text(encoding='utf-8')); end = D['year_end_exclusive_epoch']
R = lambda c: (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk']  # noqa: E731
keep, skip, open_ = [], [], defaultdict(list)
for c in sorted(D['candidates'], key=lambda c: (c['op'], c['id'])):
    cl = c['cl'] or end; L = open_[c['symbol']]; L[:] = [x for x in L if x[1] > c['op']]
    if any(side != c['side'] for side, _ in L): skip.append(c); continue
    keep.append(c); L.append((c['side'], cl))
per = defaultdict(lambda: dict(kept=0, skipped=0, kept_r=0.0, skipped_r=0.0))
for lst, k in ((keep, 'kept'), (skip, 'skipped')):
    for c in lst: p = per[c['ea']]; p[k] += 1; p[k + '_r'] = round(p[k + '_r'] + R(c), 2)
# check: no opposite overlap left
chk = 0; by = defaultdict(list)
for c in keep: by[c['symbol']].append((c['side'], c['op'], c['cl'] or end))
for s, L in by.items():
    for a in L: chk += any(b[0] != a[0] and b[1] < a[1] < b[2] for b in L)
gw = lambda L: sum(R(c) for c in L if R(c) > 0) / -sum(R(c) for c in L if R(c) < 0)  # noqa: E731
out = dict(rule=__doc__.split('\n')[1:4], source=str(sim.SRC_BASE), trades_before=len(D['candidates']), trades_after=len(keep), skipped=len(skip),
           r_before=round(sum(R(c) for c in D['candidates']), 1), r_after=round(sum(R(c) for c in keep), 1), r_skipped=round(sum(R(c) for c in skip), 1),
           pf_before=round(gw(D['candidates']), 3), pf_after=round(gw(keep), 3), per_month_after=round(len(keep) / 60, 1), per_day_after=round(len(keep) / 60 / 21, 2),
           remaining_opposite_overlaps=chk, per_ea=dict(sorted(per.items())))
(H / 'INPUTS-NOHEDGE.json').write_text(json.dumps(dict({k: v for k, v in D.items() if k != 'candidates'}, candidates=keep), separators=(',', ':')), encoding='utf-8')
(H / 'NOHEDGE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k != 'per_ea'}, indent=1)); [print(k, v) for k, v in out['per_ea'].items()]
