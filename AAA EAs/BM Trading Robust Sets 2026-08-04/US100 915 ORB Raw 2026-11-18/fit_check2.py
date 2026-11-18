"""Addendum 3 follow-up 2: reading A with a next-bar-open fill, and a flat futures-like cost of 1.0 index point per round trip (MNQ ~0.25 pt spread + commission),
instead of the CFD spread. Costs are applied as cost / risk in R per trade."""
import json, statistics
import fit as F

END = '2026-11-17'
A = dict(range_start=555, last=585, first_only=True, body=1, entry='close', ema='m15', flat=None)
W = {'2019-22 (unseen)': ('2019-07-16', '2023-01-01'), 'since 2023': ('2023-01-01', END), '2025': ('2025-01-01', '2026-01-01'), '2026': ('2026-01-01', END)}


D = F.prep(); res = {}
for name, p, cost in (('A_close_fill_no_cost', A, 0.0), ('A_next_open_no_cost', dict(A, entry='open'), 0.0), ('A_next_open_futures_1pt', dict(A, entry='open'), 1.0),
                      ('A_next_open_cfd_spread', dict(A, entry='open'), None)):
    tr = F.sim(D, p, spread=True) if cost is None else F.sim(D, p, cost_pts=cost)
    res[name] = {w: F.stats(tr, *v) for w, v in W.items()}
json.dump(res, open('FIT_CHECK2.json', 'w'), indent=1, default=str)
for k, v in res.items():
    print(k)
    for w, s in v.items(): print('  %-17s n=%4d win=%5.1f%% PF=%5s R=%+6.1f avgR=%+.3f DD=%5.1fR' % (w, s['trades'], s['win'], s['pf'], s['total_r'], s['avg_r'], s['max_dd_r']))
