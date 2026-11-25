"""Engine vs native Model 4 ledgers (WIDE / PAPER, USTEC / US500): same entry day + direction >= 95%, total R within 15% (or 10 R). -> PARITY.json"""
import gzip, json, sys, time
from datetime import datetime, timezone
import numpy as np
sys.path.insert(0, '.'); import engine as E  # noqa: E402
COMM = {'USTEC': 0.625 + 0.44, 'US500': 0.25 + 0.13, 'DE30': 0.564 + 0.44}   # commission + fill cost calibrated on WIDE (calib.py: mean implied price cost native - engine); checked on PAPER
CF = {'WIDE': dict(k=1.4, stop_mult=2.0), 'PAPER': dict(k=0.6, stop_mult=1.5)}
res = {}
for sym in ('USTEC', 'US500'):
    t0 = time.time(); D = E.Data(sym, 30, COMM[sym]); print(sym, 'prep', round(time.time() - t0, 1), 's', flush=True)
    for name, cfg in CF.items():
        tr = E.run(D, cfg)
        T = sorted(json.loads(gzip.open(E.RAW / 'native' / f'nw-{sym}-{name}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; nat = {}
        for t in T: nat[t['open_time'][:16]] = (1 if t['side'] == 'Long' else -1, t['net_profit'] / (0.01 * bal)); bal += t['net_profit']
        eng = {datetime.fromtimestamp(int(D.t[int(r[4])]), timezone.utc).strftime('%Y-%m-%dT%H:%M'): (int(r[2]), float(r[3])) for r in tr}
        nd = {k[:10]: v for k, v in nat.items()}; ed = {k[:10]: v for k, v in eng.items()}
        same_day_dir = sum(1 for d, v in nd.items() if d in ed and ed[d][0] == v[0]); same_min = sum(1 for k, v in nat.items() if k in eng and eng[k][0] == v[0])
        both = [d for d in nd if d in ed and ed[d][0] == nd[d][0]]
        corr = float(np.corrcoef([nd[d][1] for d in both], [ed[d][1] for d in both])[0, 1])
        nr, er = sum(v[1] for v in nat.values()), sum(v[1] for v in eng.values())
        ok = same_day_dir / len(nat) >= 0.95 and (abs(er - nr) <= max(10, 0.15 * abs(nr)))
        res[f'{sym} {name}'] = dict(native_trades=len(nat), engine_trades=len(eng), same_day_dir_pct=round(100 * same_day_dir / len(nat), 1), same_minute_pct=round(100 * same_min / len(nat), 1),
                                   native_R=round(nr, 1), engine_R=round(er, 1), per_trade_corr=round(corr, 3), PASS=ok)
        print(sym, name, res[f'{sym} {name}'], flush=True)
json.dump(res, open('PARITY.json', 'w'), indent=1)
