"""Addendum 4: the volatility-filter prompt in the bar replay (fit.sim): MT5-like (spread), TradingView (no costs), first-breakout-only, futures-like 1 pt."""
import json
import fit as F

END = '2026-11-17'
V = dict(range_start=555, last=930, first_only=False, body=0, entry='open', ema='none', flat=None, atr=1.5)
W = {'2019-22': ('2019-07-16', '2023-01-01'), 'since 2023': ('2023-01-01', END), '2023': ('2023-01-01', '2024-01-01'), '2024': ('2024-01-01', '2025-01-01'),
     '2025': ('2025-01-01', '2026-01-01'), '2026': ('2026-01-01', END)}
D = F.prep(); out = {}
for name, p, kw in (('cfd_spread', V, dict(spread=True)), ('tv_no_cost', V, {}), ('tv_signal_close_fill', dict(V, entry='close'), {}),
                    ('tv_first_breakout_only', dict(V, first_only=True), {}), ('futures_1pt', V, dict(cost_pts=1.0)), ('first_only_futures_1pt', dict(V, first_only=True), dict(cost_pts=1.0))):
    tr = F.sim(D, p, **kw); out[name] = {w: F.stats(tr, *v) for w, v in W.items()}
json.dump(out, open('VOL_REPLAY.json', 'w'), indent=1, default=str)
for k, v in out.items():
    print(k)
    for w, s in v.items(): print('  %-11s n=%4d %4.1f/mo win=%5.1f%% PF=%5s R=%+6.1f avgR=%+.3f DD=%5.1fR' % (w, s['trades'], s['per_month'], s['win'], s['pf'], s['total_r'], s['avg_r'], s['max_dd_r']))
