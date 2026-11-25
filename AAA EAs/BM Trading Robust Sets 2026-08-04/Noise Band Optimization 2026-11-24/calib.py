import gzip, json, sys
from datetime import datetime, timezone
import numpy as np
sys.path.insert(0, '.'); import engine as E  # noqa
COMM = {'USTEC': 0.625, 'US500': 0.25}
for sym in ('USTEC', 'US500'):
    D = E.Data(sym, 30, COMM[sym])
    for name, cfg in {'WIDE': dict(k=1.4, stop_mult=2.0), 'PAPER': dict(k=0.6, stop_mult=1.5)}.items():
        tr = E.run(D, cfg)
        T = sorted(json.loads(gzip.open(E.RAW / 'native' / f'nw-{sym}-{name}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; nat = {}
        for t in T: nat[t['open_time'][:16]] = (t['net_profit'] / (0.01 * bal), t['open_price'], t['close_price'], t['exit_comment']); bal += t['net_profit']
        rows = []
        for r in tr:
            k = datetime.fromtimestamp(int(D.t[int(r[4])]), timezone.utc).strftime('%Y-%m-%dT%H:%M')
            if k in nat:
                o = D.o[int(r[4])] + (D.spr[int(r[4])] if r[2] > 0 else 0)
                rows.append((nat[k][0] - r[3], r[6], (nat[k][1] - o) * r[2], nat[k][0], r[3], nat[k][3][:2]))
        a = np.array([x[:5] for x in rows]); dif, dist, entry_slip = a[:, 0], a[:, 1], a[:, 2]
        # implied price cost per trade = -dif * dist
        pc = -dif * dist
        sl = [x for x in rows if x[5] == 'sl']; other = [x for x in rows if x[5] != 'sl']
        print(sym, name, 'n', len(a), 'mean dR', round(dif.mean(), 4), 'median implied price cost', round(np.median(pc), 3), 'mean', round(pc.mean(), 3),
              'entry slip (native-engine, adverse +) median', round(np.median(entry_slip), 3), 'mean', round(entry_slip.mean(), 3),
              '| dR sl', round(np.mean([x[0] for x in sl]), 4), 'other', round(np.mean([x[0] for x in other]), 4))
