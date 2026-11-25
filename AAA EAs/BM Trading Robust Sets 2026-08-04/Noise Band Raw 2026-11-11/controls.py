"""Pipeline random-entry control (robustness.random_entry_control: 200 copies, same direction / clock time / stop / holding time on random days, p <= 0.10)
for the WIDE cases, plus DE30 buy & hold price-only (the benchmark EA refuses EUR symbols). Stops from the EA's NB_ENTRY journal lines (stop = 2 x ATR).
The control uses a fixed stop and exits at the real holding time (no trailing), on M5 bars built from the exported M1 bars (bars/<SYM>_m1.npy)."""
import gzip, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H.parent.parent / 'Calyx Research Pipeline')); import robustness  # noqa: E402
ep = lambda s: int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())  # noqa: E731
out = {}
for sym in ('USTEC', 'US500', 'DE30'):
    d = H / 'native' / f'nw-{sym}-WIDE-all'; T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['open_time'])
    j = gzip.open(d / 'journal.txt.gz').read().decode('utf-8', 'replace'); seen = {}
    for m_ in re.finditer(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+NB_ENTRY \w+ K=\d+ move=[-\d.]+ thr=[\d.]+ atr=([\d.]+)', j): seen.setdefault(m_.group(1), float(m_.group(2)))   # the journal holds two log copies
    atr = [seen[k_] for k_ in sorted(seen)]
    assert len(atr) == len(T), (sym, len(atr), len(T))
    bal = 1e4; tr = []; costs = []
    cl = sorted((t['close_time'], t['net_profit']) for t in T)
    for t, a in zip(T, atr):
        b = 1e4 + sum(n for c, n in cl if c <= t['open_time']); r = t['net_profit'] / (0.01 * b); cost = -t['commission'] / (0.01 * b)
        tr.append(dict(open_epoch=ep(t['open_time']), side=1 if t['side'] == 'Long' else -1, stop=2.0 * a, target=None, hold_seconds=ep(t['close_time']) - ep(t['open_time']), r=r)); costs.append(cost)
    m = np.load(H / 'bars' / f'{sym}_m1.npy'); k = (m[:, 0] // 300).astype(np.int64)
    idx = np.flatnonzero(np.r_[True, k[1:] != k[:-1]]); bars = []
    for s, e in zip(idx, list(idx[1:]) + [len(m)]):
        bars.append((int(k[s] * 300), float(m[s, 1]), float(m[s:e, 2].max()), float(m[s:e, 3].min()), float(m[e - 1, 4])))
    rc = robustness.random_entry_control(tr, bars, copies=200, seed=20261111, cost_r=float(np.mean(costs)))
    out[sym] = {k2: v for k2, v in rc.items() if k2 not in ('copies_totals', 'totals')}; print(sym, json.dumps(out[sym])[:600], flush=True)
m = np.load(H / 'bars' / 'DE30_m1.npy'); c = m[:, 4]; pk = np.maximum.accumulate(c)
out['DE30 buy&hold price only'] = dict(start=float(c[0]), end=float(c[-1]), price_return_pct=round(100 * (c[-1] / c[0] - 1), 2), max_dd_pct=round(float(100 * ((pk - c) / pk).max()), 2),
                                       note='price only (no swap, no FX); the benchmark EA refuses EUR-margined symbols')
(H / 'CONTROLS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(out['DE30 buy&hold price only'])
