"""Compare the C# N5Logic daily signals (data/signals_cs.csv) with the MT5 production EA entries (journals of native Model-4 runs, DI OFF, Best 1-Step inputs):
  Calyx No Opposite/parity/native/nw-nasdaq-5m-candle-momentum-OFF (2026-08-16 -> 11-16) and Best 1-Step Today 2026-11-19/native/nw-nasdaq-5m-candle-momentum (11-12 -> 11-18).
Checks per MT5 entry: same NY date has a C# signal, same direction, stop distance |sl - fill| = 6 x ATR (C#) within 0.02 points. -> PARITY.json"""
import csv, gzip, json, re
from datetime import datetime, timedelta
from pathlib import Path
H = Path(__file__).resolve().parents[1]; B = H.parent
RUNS = [B / '_00 Live profiles/Calyx No Opposite/parity/native/nw-nasdaq-5m-candle-momentum-OFF', B / 'Best 1-Step Today 2026-11-19/native/nw-nasdaq-5m-candle-momentum']
cs = {r['date_ny']: r for r in csv.DictReader(open(H / 'data/signals_cs.csv'))}
pat = re.compile(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+CTrade::OrderSend: market (buy|sell) ([\d.]+) USTEC sl: ([\d.]+) \[done at ([\d.]+)\]')
def ny(t):  # server = UTC; US DST 2026: until Nov 1 06:00 UTC -> UTC-4, then UTC-5
    return t - timedelta(hours=4 if t < datetime(2026, 11, 1, 6) else 5)
rows, seen = [], set()
for run in RUNS:
    j = gzip.decompress((run / 'journal.txt.gz').read_bytes()).decode('utf-8', 'replace')
    for m in pat.finditer(j):
        t = datetime.strptime(m[1], '%Y.%m.%d %H:%M:%S'); d = ny(t).strftime('%Y-%m-%d')
        if (d, m[2]) in seen: continue
        seen.add((d, m[2])); side = 1 if m[2] == 'buy' else -1; dist = abs(float(m[4]) - float(m[5])); c = cs.get(d)
        rows.append(dict(date_ny=d, mt5_time_ny=ny(t).strftime('%H:%M:%S'), mt5_dir=side, mt5_stop_dist=round(dist, 2),
                         cs_dir=int(c['direction']) if c else None, cs_stop_dist=round(float(c['stop_distance']), 2) if c else None,
                         dir_ok=bool(c) and int(c['direction']) == side, stop_ok=bool(c) and abs(float(c['stop_distance']) - dist) <= 0.02))
first, last = min(r['date_ny'] for r in rows), max(r['date_ny'] for r in rows)
cs_days = [d for d, r in cs.items() if first <= d <= last and int(r['direction']) != 0]
missing = sorted(set(cs_days) - {r['date_ny'] for r in rows})
out = dict(mt5_entries=len(rows), window=[first, last], direction_match=sum(r['dir_ok'] for r in rows), stop_match=sum(r['stop_ok'] for r in rows),
           cs_signal_days_in_window=len(cs_days), cs_signal_days_without_mt5_entry=missing,
           max_stop_diff=round(max(abs((r['cs_stop_dist'] or 0) - r['mt5_stop_dist']) for r in rows), 4),
           mismatches=[r for r in rows if not (r['dir_ok'] and r['stop_ok'])], rows=rows)
(H / 'test/PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print({k: v for k, v in out.items() if k != 'rows'})
