"""Owner-facing table for COMPARE_2M: per EA Exness vs FTMO in R, with FTMO commission added post hoc (custom symbols charge none):
XAUUSD $3 / lot / side (measured on the owner's FTMO account deals), USDJPY $2.5 / lot / side (ASSUMED, not verified), US100 / UK100 $0 (measured US100: $0).
R = net / (1% of balance at entry), Nasdaq 5M x0.75 as installed. Trades matched by entry within 15 minutes and same side."""
import gzip, json
from datetime import datetime
from pathlib import Path
H = Path(__file__).resolve().parent
spec = __import__('importlib.util').util.spec_from_file_location('c', H / 'compare2m.py'); C = __import__('importlib.util').util.module_from_spec(spec); spec.loader.exec_module(C)
COMM = {'XAUUSD': 3.0, 'USDJPY': 2.5, 'USTEC': 0.0, 'UK100': 0.0}
def load(key, feed, canon):
    T = sorted(json.loads(gzip.open(H / 'native' / f'nw-{key}-{feed}' / 'trades.json.gz').read()), key=lambda t: t['close_time'])
    bal = 1e4; out = []; f = C.FACTOR.get(key, 1.0)
    # balance at entry = deposit + trades closed before the entry
    closed = [(t['close_time'], t['net_profit']) for t in T]
    for t in sorted(T, key=lambda t: t['open_time']):
        b = 1e4 + sum(n for c, n in closed if c <= t['open_time']); risk = 0.01 * b
        extra = -2 * COMM[canon] * t['volume'] if feed == 'FTMO' else 0.0
        out.append(dict(open=t['open_time'], close=t['close_time'], side=t['side'], r=t['net_profit'] / risk * f, r_c=(t['net_profit'] + extra) / risk * f, entry=t['open_price'], exit=t['close_price'], why=t['exit_comment']))
    return out
def st(L, k):
    R = [x[k] for x in L]; g = sum(r for r in R if r > 0); l = -sum(r for r in R if r < 0)
    return dict(n=len(R), win=round(100 * sum(r > 0 for r in R) / len(R), 1) if R else None, R=round(sum(R), 2), PF=round(g / l, 2) if l else None)
res = {}; allE = []; allF = []; months = (datetime(2026, 11, 21) - datetime(2026, 9, 22)).days / 30.4375
for e in C.entries():
    E = load(e['key'], 'EXNESS', e['canonical']); F = load(e['key'], 'FTMO', e['canonical']); allE += E; allF += F
    used = set(); pairs = []
    for x in E:
        tx = datetime.fromisoformat(x['open'])
        m = next((i for i, y in enumerate(F) if i not in used and y['side'] == x['side'] and abs((datetime.fromisoformat(y['open']) - tx).total_seconds()) <= 900), None)
        if m is not None: used.add(m); pairs.append((x, F[m]))
    res[e['label']] = dict(exness=st(E, 'r'), ftmo_no_comm=st(F, 'r'), ftmo=st(F, 'r_c'), matched=len(pairs), only_exness=len(E) - len(pairs), only_ftmo=len(F) - len(used),
                           matched_r_diff=round(sum(b['r_c'] - a['r'] for a, b in pairs), 2),
                           unmatched_exness=[(x['open'][:16], x['side'], round(x['r'], 2)) for x in E if not any(x is a for a, _ in pairs)],
                           unmatched_ftmo=[(y['open'][:16], y['side'], round(y['r_c'], 2)) for i, y in enumerate(F) if i not in used],
                           pairs=[(a['open'][:16], b['open'][:16], a['side'], round(a['r'], 2), round(b['r_c'], 2), a['why'][:10], b['why'][:10]) for a, b in pairs])
res['TOTAL'] = dict(exness=st(allE, 'r'), ftmo_no_comm=st(allF, 'r'), ftmo=st(allF, 'r_c'), months=round(months, 2), exness_per_month=round(len(allE) / months, 1), ftmo_per_month=round(len(allF) / months, 1),
                    exness_per_day=round(len(allE) / months / 21.0, 2), ftmo_per_day=round(len(allF) / months / 21.0, 2))
(H / 'COMPARE_2M_TABLE.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
for k, v in res.items():
    print(f"{k[:34]:34s}", v['exness'], v['ftmo_no_comm']['R'], v['ftmo'], {x: v[x] for x in ('matched', 'only_exness', 'only_ftmo', 'matched_r_diff') if x in v})
print(res['TOTAL'])
for k, v in res.items():
    if k != 'TOTAL' and (v['unmatched_exness'] or v['unmatched_ftmo']): print(k, 'EX only', v['unmatched_exness'], 'FT only', v['unmatched_ftmo'])
