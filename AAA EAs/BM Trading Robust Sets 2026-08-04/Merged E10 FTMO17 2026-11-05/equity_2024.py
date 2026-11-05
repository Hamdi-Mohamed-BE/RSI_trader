"""Owner 2026-11-05: equity curve per profile with $10k at 1% risk since the start of 2024, max closed DD, return per month. Python replay of the 22 standalone native ledgers
(native.py, Model 4), no guard: every trade opened from 2024-01-01, trades in time order. COMPOUND = 1% of the closed balance at entry (what the installer's percent mode does).
FIXED = $100 per trade, no compounding. Lot rounding, margin and floating losses are not modelled; closes on 2026-10-30 include positions the tester closed at the end of the data.
Guard lines use analyze.py's closed-balance replay. -> EQUITY_2024.json, EQUITY_2024.md"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent
src = (H / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
ns = dict(__file__=str(H / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns)
PORT, WINDOWS, replay = ns['PORT'], ns['WINDOWS'], ns['replay']; S0 = 10000.0; START = datetime(2024, 1, 1, tzinfo=timezone.utc)
WINDOWS['since2024'] = ('2024-01-01', '2026-11-01')
LABEL = {'FTMO17': 'FTMO17', 'E10': 'E10', 'M22': 'Mixed (M22)'}


def curve(rows, compound):
    rows = [r for r in rows if r['o'] >= START]
    ev = sorted([(r['o'], 1, i) for i, r in enumerate(rows)] + [(r['c'], 2 if r['c'] == r['o'] else 0, i) for i, r in enumerate(rows)], key=lambda e: (e[0], e[1], e[2]))
    bal = peak = S0; dd = dd_cash = 0.0; dd_at = None; open_ = {}; pts = [(START.isoformat(), S0)]; month = defaultdict(float); n = defaultdict(int); wins = 0; low = S0
    for t, kind, i in ev:
        if kind == 1:
            open_[i] = bal * 0.01 if compound else 100.0; continue
        pnl = open_.pop(i) * rows[i]['R']; bal += pnl; wins += pnl > 0; m = t.strftime('%Y-%m'); month[m] += pnl; n[m] += 1; low = min(low, bal)
        peak = max(peak, bal); d = (peak - bal) / peak * 100
        if d > dd: dd, dd_at = d, t.date().isoformat()
        dd_cash = max(dd_cash, peak - bal); pts.append((t.isoformat(), round(bal, 2)))
    b = S0; months = {}
    for m in sorted(month):
        months[m] = dict(pnl=round(month[m], 2), pct=round(100 * month[m] / b, 2), trades=n[m], end=round(b + month[m], 2)); b += month[m]
    return dict(end=round(bal, 2), ret=round((bal / S0 - 1) * 100, 1), max_closed_dd_pct=round(dd, 2), dd_date=dd_at, max_closed_dd_cash=round(dd_cash, 2), lowest_balance=round(low, 2), trades=len(rows), wins=wins, curve=pts, months=months)


out = {}
for n, rows in PORT.items():
    out[n] = dict(compound=curve(rows, True), fixed=curve(rows, False), guards={m: {k: replay(rows, 'since2024', m, 0.01)[k] for k in ('ret', 'trades', 'closed_dd', 'pf', 'last_entry')} for m in ('PROP', 'ONESTEP')},
                  touch=replay(rows, 'since2024', 'NONE', 0.01))
(H / 'EQUITY_2024.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
L = ['| Profile | Trades | Compounding: end balance / return / max closed DD | Fixed $100: end balance / return / max closed DD | Lowest balance (fixed) | Prop guard 1%: return / closed DD / trades | 1-Step guard 1%: return / closed DD / trades |', '|---|---:|---|---|---:|---|---|']
for n, x in out.items():
    c, f, g = x['compound'], x['fixed'], x['guards']
    L.append(f"| {LABEL[n]} | {c['trades']} | ${c['end']:,.0f} / {c['ret']:+,.0f}% / {c['max_closed_dd_pct']}% | ${f['end']:,.0f} / {f['ret']:+,.0f}% / {f['max_closed_dd_pct']}% | ${f['lowest_balance']:,.0f} | {g['PROP']['ret']:+.1f}% / {g['PROP']['closed_dd']}% / {g['PROP']['trades']} | {g['ONESTEP']['ret']:+.1f}% / {g['ONESTEP']['closed_dd']}% / {g['ONESTEP']['trades']} |")
L += ['', '| Month | ' + ' | '.join(f'{LABEL[n]} % (trades)' for n in out) + ' |', '|---|' + '---:|' * 3]
months = sorted({m for x in out.values() for m in x['compound']['months']})
for m in months:
    L.append(f'| {m} | ' + ' | '.join(f"{x['compound']['months'].get(m, dict(pct=0))['pct']:+.1f}% ({x['compound']['months'].get(m, dict(trades=0))['trades']})" for x in out.values()) + ' |')
for n, x in out.items():
    p = [v['pct'] for v in x['compound']['months'].values()]
    L.append(f"\n{LABEL[n]}: {sum(v > 0 for v in p)} of {len(p)} months positive; average {sum(p) / len(p):+.1f}%; best {max(p):+.1f}%; worst {min(p):+.1f}%; firm limits first touched (closed balance) 2-step {x['touch']['touch_2step']}, 1-Step {x['touch']['touch_1step']}; worst day {x['touch']['worst_day']}%; best day {x['touch']['best_day']}%")
(H / 'EQUITY_2024.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
