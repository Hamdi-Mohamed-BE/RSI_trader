"""Addendum 2 timing check: is the server clock UTC and the NY conversion right? Uses the exported M15 bars."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
import numpy as np
import tv_replay as T

z = T.load('M15'); t, h, l = z['time'], z['high'], z['low']
out = {}
for season, months in (('summer_EDT', (6, 7, 8)), ('winter_EST', (12, 1, 2))):
    rng = defaultdict(list); present = Counter(); days = set()
    for x, hi, lo in zip(t, h, l):
        u = datetime.fromtimestamp(int(x), timezone.utc)
        if u.month not in months or u.weekday() >= 5: continue
        d = T.ny(x); m = d.hour * 60 + d.minute; rng[m].append(hi - lo); present[m] += 1; days.add(d.date())
    nd = len(days); missing = sorted(m for m in range(0, 1440, 15) if present[m] < 0.5 * nd)
    top = sorted(rng, key=lambda m: -np.median(rng[m]))[:4]
    out[season] = dict(days=nd, ny_minutes_mostly_missing=[f'{m // 60:02d}:{m % 60:02d}' for m in missing],
                       biggest_median_range_bars_NY=[f'{m // 60:02d}:{m % 60:02d} ({np.median(rng[m]):.1f} pts)' for m in top],
                       bar_0915_median=round(float(np.median(rng[555])), 1), bar_0930_median=round(float(np.median(rng[570])), 1))
# DST switch weeks: the cash open must stay at 09:30 NY on both sides of the change
for d in ('2025-03-07', '2025-03-10', '2025-10-31', '2025-11-03', '2026-03-06', '2026-03-09'):
    best = None
    for x, hi, lo in zip(t, h, l):
        dd = T.ny(x)
        if dd.date().isoformat() == d and 8 * 60 <= dd.hour * 60 + dd.minute <= 12 * 60:
            if best is None or hi - lo > best[1]: best = (dd.strftime('%H:%M'), round(float(hi - lo), 1), datetime.fromtimestamp(int(x), timezone.utc).strftime('%H:%M UTC'))
    out['dst_' + d] = best
print(json.dumps(out, indent=1)); (__import__('pathlib').Path(__file__).parent / 'TIMING_CHECK.json').write_text(json.dumps(out, indent=1))
