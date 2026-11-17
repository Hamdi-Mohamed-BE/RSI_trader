"""Owner 2026-11-17: "gold has a lot of EAs, keep the EAs that make sense based on last year performance, not full period".
Last year = the stream's last 365 days (2025-10-06 -> 2026-10-06, trades opened and closed inside). Gold EAs only; the 4 non-gold EAs all stay.
Keep rules fixed BEFORE any simulation (selection on the last year = hindsight; that year is inside every result below):
  G6 = drop gold EAs with last-year R <= 0                      -> drops Gold Band Wave
  G4 = keep gold EAs with last-year PF >= 1.25 (and R > 0)        -> ORB VP VC, Squeeze, EMA3, 3 Way Gold
  G3 = keep gold EAs with last-year R/trade >= 0.10 (and PF >= 1.25) -> ORB VP VC, Squeeze, 3 Way Gold
The no-opposite-trade rule (nohedge.py) is applied after the EA filter (fewer EAs = fewer conflicts). python gold.py"""
import json
from collections import defaultdict
from pathlib import Path

import sim

H = Path(__file__).resolve().parent
D = json.loads(sim.SRC_BASE.read_text(encoding='utf-8')); END = D['year_end_exclusive_epoch']; LY = END - 365 * 86400
R = lambda c: (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk']  # noqa: E731
GOLD = sorted({c['ea'] for c in D['candidates'] if c['symbol'] == 'XAUUSD'})


def ly_stats(ea):
    x = [R(c) for c in D['candidates'] if c['ea'] == ea and c['op'] >= LY and (c['cl'] or END) >= LY]
    w = sum(v for v in x if v > 0); l = -sum(v for v in x if v < 0)
    return dict(n=len(x), r=sum(x), pf=w / l if l else 99.0, rpt=sum(x) / len(x))


S = {ea: ly_stats(ea) for ea in GOLD}
RULES = {'G6': lambda s: s['r'] > 0, 'G4': lambda s: s['r'] > 0 and s['pf'] >= 1.25, 'G3': lambda s: s['pf'] >= 1.25 and s['rpt'] >= 0.10 - 1e-9}


def nohedge(cands):
    keep, open_ = [], defaultdict(list)
    for c in sorted(cands, key=lambda c: (c['op'], c['id'])):
        L = open_[c['symbol']]; L[:] = [x for x in L if x[1] > c['op']]
        if any(side != c['side'] for side, _ in L): continue
        keep.append(c); L.append((c['side'], c['cl'] or END))
    return keep


def stats(cands, a=None):
    x = [(c, R(c)) for c in cands if a is None or (c['op'] >= a and (c['cl'] or END) >= a)]
    rs = [r for _, r in sorted(x, key=lambda t: t[0]['cl'] or END)]; w = sum(v for v in rs if v > 0); l = -sum(v for v in rs if v < 0)
    eq = pk = dd = 0.0
    for v in rs: eq += v; pk = max(pk, eq); dd = max(dd, pk - eq)
    months = (END - (a or D['year_begin_epoch'])) / 86400 / 30.4375
    return dict(trades=len(rs), per_month=round(len(rs) / months, 1), per_day=round(len(rs) / months / 21, 2), r=round(sum(rs), 1), pf=round(w / l, 3) if l else None, closed_dd_r=round(dd, 1))


out = dict(last_year=[LY, END], gold_last_year={k: {a: round(b, 3) for a, b in v.items()} for k, v in S.items()}, variants={})
base = nohedge(D['candidates']); out['variants']['ALL11'] = dict(eas=sorted({c['ea'] for c in base}), all=stats(base), last_year=stats(base, LY))
for name, rule in RULES.items():
    drop = [ea for ea in GOLD if not rule(S[ea])]; cands = nohedge([c for c in D['candidates'] if c['ea'] not in drop])
    out['variants'][name] = dict(dropped=drop, eas=sorted({c['ea'] for c in cands}), all=stats(cands), last_year=stats(cands, LY))
    (H / f'INPUTS_{name}.json').write_text(json.dumps(dict({k: v for k, v in D.items() if k != 'candidates'}, candidates=cands), separators=(',', ':')), encoding='utf-8')
(H / 'GOLD.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for k, v in out['variants'].items(): print(k, v.get('dropped'), len(v['eas']), 'ALL', v['all'], 'LY', v['last_year'])
