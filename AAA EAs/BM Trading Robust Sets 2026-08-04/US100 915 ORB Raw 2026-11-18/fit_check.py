"""Addendum 3 follow-up: the two closest readings (FIT.json) on every window, without and with the recorded spread."""
import json
import fit as F

END = '2026-11-17'
CFG = {'A_72pct_since_2023': dict(range_start=555, last=585, first_only=True, body=1, entry='close', ema='m15', flat=None),
       'B_best_overall_CT_clock': dict(range_start=615, last=720, first_only=True, body=0, entry='close', ema='m15', flat=None),
       'reel_literal': dict(range_start=555, last=930, first_only=False, body=0, entry='open', ema='m15', flat=None)}
W = {'2019-22 (unseen)': ('2019-07-16', '2023-01-01'), 'since 2023': ('2023-01-01', END), '2023': ('2023-01-01', '2024-01-01'), '2024': ('2024-01-01', '2025-01-01'),
     '2025': ('2025-01-01', '2026-01-01'), '2026': ('2026-01-01', END), 'all': ('2019-07-16', END)}
D = F.prep(); out = {}
for k, p in CFG.items():
    a, b = F.sim(D, p), F.sim(D, p, spread=True)
    out[k] = dict(p=p, no_cost={w: F.stats(a, *v) for w, v in W.items()}, spread={w: F.stats(b, *v) for w, v in W.items()})
json.dump(out, open('FIT_CHECK.json', 'w'), indent=1, default=str)
for k, v in out.items():
    print(k)
    for w in W:
        s, t = v['no_cost'][w], v['spread'][w]
        print('  %-17s n=%4d %4.1f/mo win=%5.1f%% PF=%5s R=%+6.1f DD=%5.1fR | spread: win=%5.1f%% PF=%5s R=%+6.1f' % (w, s['trades'], s['per_month'], s['win'], s['pf'], s['total_r'], s['max_dd_r'], t['win'], t['pf'], t['total_r']))
