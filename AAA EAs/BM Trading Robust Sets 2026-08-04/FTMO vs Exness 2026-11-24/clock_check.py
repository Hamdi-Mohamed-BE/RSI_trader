"""Week-by-week lag between FTMO bars (converted with export_ftmo.eet_offset = EU DST rule) and Exness (UTC): the lag in minutes that maximises the
correlation of 1-minute close changes. 0 = conversion right; +60 = FTMO prices appear 1 h late (server was +3 while the conversion used +2)."""
import json, os, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent; F = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxFTMO'
dt = np.dtype([('t', '<i8'), ('o', '<f8'), ('h', '<f8'), ('l', '<f8'), ('c', '<f8'), ('v', '<i8'), ('s', '<i4')])
out = {}
for fn, ex in (('US100', 'USTEC'), ('XAUUSD', 'XAUUSD')):
    a = np.fromfile(F / f'{fn}_m1.bin', dtype=dt); b = np.load(H / 'exness' / f'{ex}_m1.npy')
    fa = dict(zip(a['t'].tolist(), a['c'].tolist())); eb = dict(zip(b[:, 0].astype(np.int64).tolist(), b[:, 4].tolist()))
    t0 = int(datetime(2021, 6, 7, tzinfo=timezone.utc).timestamp()); W = []
    while t0 < int(datetime(2026, 11, 16, tzinfo=timezone.utc).timestamp()):
        ts = np.arange(t0 + 86400, t0 + 5 * 86400, 60)
        e = np.array([eb.get(int(t), np.nan) for t in ts]); de = np.diff(e); best = None
        for lag in (-120, -60, 0, 60, 120):
            f = np.array([fa.get(int(t) + lag * 60, np.nan) for t in ts]); df = np.diff(f); k = ~np.isnan(de) & ~np.isnan(df) & (de != 0)
            if k.sum() < 500: continue
            c = np.corrcoef(de[k], df[k])[0, 1]
            if best is None or c > best[1]: best = (lag, c)
        W.append((datetime.fromtimestamp(t0, timezone.utc).strftime('%Y-%m-%d'), best[0] if best else None, round(best[1], 3) if best else None)); t0 += 7 * 86400
    out[fn] = W
    bad = [w for w in W if w[1] not in (0, None)]
    print(fn, Counter(w[1] for w in W), 'weeks not 0:', bad)
(H / 'CLOCK_CHECK.json').write_text(json.dumps(out, indent=0), encoding='utf-8')
