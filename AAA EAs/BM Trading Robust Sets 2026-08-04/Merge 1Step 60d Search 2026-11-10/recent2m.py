"""Last two months (owner 2026-11-10): profiles built from the 13 native r2m runs (tester_jobs.py recent), trades OPENED 2026-09-10 -> 2026-11-10 (data end).
R = net / 1% of the EA's own balance before the trade (standalone $10k runs). 3 Way Gold = breakout module only (comment '3WG BRK', magic 930930101) as in the streams.
FTMO 1-Step replay (CLOSED-TRADE approximation, not the frozen engine: no floating equity, no guard caps, no margin): every weekday start, risk x R x the
current balance per trade, target +10%, daily loss 3% of the start balance from the day-start closed balance, 10% max loss trailing the end-of-day balance,
pass needs best day <= 50% of profit. A start passes within N days only if it reached the target by start+N; starts with fewer than N days of data left are not
counted for that N. Run: python recent2m.py -> RECENT2M.json / RECENT2M.md"""
import gzip, json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent
A, END = '2026-09-10', '2026-11-11'
SYM = {'nasdaq-5m-candle-momentum': 'USTEC', 'overnight-bias-orb': 'USTEC', 'vault-break': 'USTEC', 'sell-nasdaq-15min': 'USTEC', 'us100-selective-orb-v3': 'USTEC', 'usdjpy-london-open-momentum': 'USDJPY'}


def ledger(slug):
    key = '3-way-gold' if slug.startswith('3-way-gold') else slug; d = H / 'native-recent' / f"nw-{SYM.get(key, 'XAUUSD')}-{key}-r2m"
    T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; out = []
    for t in T:
        r = t['net_profit'] / (0.01 * bal); bal += t['net_profit']
        if slug.startswith('3-way-gold') and t['entry_comment'] != '3WG BRK': continue
        if A <= t['open_time'][:10] < END: out.append(dict(ea=slug, o=t['open_time'], c=t['close_time'], r=r))
    return out


def stats(rows):
    rows = sorted(rows, key=lambda x: x['c']); gw = sum(x['r'] for x in rows if x['r'] > 0); gl = -sum(x['r'] for x in rows if x['r'] < 0); eq = pk = dd = 0.0; days = defaultdict(float)
    for x in rows:
        eq += x['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[x['c'][:10]] += x['r']
    months = (date.fromisoformat(END) - date.fromisoformat(A)).days / 30.4375
    return dict(trades=len(rows), per_month=round(len(rows) / months, 1), per_day=round(len(rows) / (months * 21.74), 2), win=round(100 * sum(x['r'] > 0 for x in rows) / max(1, len(rows)), 1),
                pf=round(gw / gl, 2) if gl else None, total_r=round(sum(x['r'] for x in rows), 2), closed_dd_r=round(dd, 2), worst_day_r=round(min(days.values()), 2) if days else None)


def challenge(rows, risk, start):
    rows = sorted((x for x in rows if x['o'][:10] >= start.isoformat()), key=lambda x: x['c']); C = 1e5; bal = C; hwm = C; day = None; anchor = C; daily = defaultdict(float)
    for x in rows:
        d = x['c'][:10]
        if d != day:
            hwm = max(hwm, bal); anchor = bal; day = d
        pnl = risk * x['r'] * bal; bal += pnl; daily[d] += pnl
        if bal <= anchor - 0.03 * C or bal <= hwm - 0.10 * C: return dict(status='breach', day=(date.fromisoformat(d) - start).days + 1)
        if bal >= 1.10 * C and max(daily.values()) <= 0.5 * (bal - C): return dict(status='pass', day=(date.fromisoformat(d) - start).days + 1)
    return dict(status='open', day=None)


def ftmo(rows, risk):
    starts = []; d = date.fromisoformat(A)
    while d < date.fromisoformat(END):
        if d.weekday() < 5: starts.append(d)
        d += timedelta(days=1)
    res = [(s, challenge(rows, risk, s)) for s in starts]; left = lambda s: (date.fromisoformat(END) - s).days  # noqa: E731
    out = {}
    for n in (30, 60):
        el = [(s, r) for s, r in res if left(s) >= n]
        out[f'pass_{n}'] = round(sum(r['status'] == 'pass' and r['day'] <= n for s, r in el) / len(el), 3) if el else None
        out[f'breach_{n}'] = round(sum(r['status'] == 'breach' and r['day'] <= n for s, r in el) / len(el), 3) if el else None
        out[f'starts_{n}'] = len(el)
    first = res[0][1]; out['started_sep10'] = first
    return out


def main():
    F = json.loads((H / 'FINAL.json').read_text(encoding='utf-8')) if (H / 'FINAL.json').exists() else {'picks': {}}
    import search as SR
    sets = {f'{k} pick ({v["risk"] * 100:g}%)': (v['members'], v['risk']) for k, v in F['picks'].items() if v}
    pool = sorted({c['ea'] for c in SR.pool()['candidates']})
    for name, mem in dict(SR.REFS, ALL13=pool).items(): sets[name] = (mem, None)
    led = {e: ledger(e) for e in pool}
    out = dict(window=[A, '2026-11-10'], eas={e: stats(led[e]) for e in pool}, profiles={})
    for name, (mem, risk) in sets.items():
        rows = [x for e in mem for x in led[e]]
        out['profiles'][name] = dict(members=mem, stats=stats(rows), ftmo={str(r): ftmo(rows, r) for r in ((risk,) if risk else (0.005, 0.0075, 0.01))})
    (H / 'RECENT2M.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out, indent=1, default=str)[:8000])


if __name__ == '__main__':
    main()
