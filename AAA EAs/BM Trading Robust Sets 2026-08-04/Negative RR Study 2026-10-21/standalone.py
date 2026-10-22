"""Negative RR Study part A tables: per-EA native results by window (fresh baseline vs 0.75 / 0.6 / 0.5R).

python standalone.py
"""
import importlib.util, json, math
from datetime import date, datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
LEVELS = ['base', 'rr075', 'rr060', 'rr050']; LABEL = {'base': 'Current', 'rr075': '0.75R', 'rr060': '0.60R', 'rr050': '0.50R'}
NAMES = {'dmc-current-xau': 'DMC Current XAU', 'dmc-fresh-reaction-us100': 'DMC Fresh Reaction US100', 'ema3': 'EMA3 Gold',
         'gold-overnight-value-area': 'Gold Overnight Value Area', 'nasdaq-5m-candle-momentum': 'Nasdaq 5M (DI ON)',
         'nasdaq-overnight': 'Nasdaq Overnight', 'us100-month-end-flow': 'US100 Month End Flow', 'usdjpy-london-open-momentum': 'USDJPY London Open',
         'xau-squeeze-momentum-standard': 'XAU Squeeze Momentum', '3-way-gold': '3-Way Gold', 'nasdaq-5m-candle-momentum|dioff': 'Nasdaq 5M (DI OFF, prop)'}
CONTRACT = {'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000.}


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def ep(d): return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


split = load('ds', B.parent / 'Calyx Research Pipeline' / 'data_split.py').research_split('2021-10-06', '2026-10-06')
WINDOWS = {'Dev 2021-23': (split['development']['start'], split['development']['end_exclusive']),
           'Val 2023-24': (split['validation']['start'], split['validation']['end_exclusive']),
           'OOS 2024-26': (split['oos']['start'], split['oos']['end_exclusive']), '5 years': ('2021-10-06', '2026-10-06')}


def exit_kind(t):
    c = ' '.join(t['exit_comments']).lower()
    return 'tp' if c.startswith('tp') or ' tp ' in f' {c} ' or '[tp' in c else ('sl' if c.startswith('sl') or '[sl' in c else 'other')


def stats(res, symbol, a, b):
    ts = [t for t in res['trades'] if ep(date.fromisoformat(a)) <= t['open_epoch'] < ep(date.fromisoformat(b))]
    bal = 10000.0; start_bal = None
    for t in sorted(res['trades'], key=lambda t: t['close_epoch']):
        if t['close_epoch'] >= ep(date.fromisoformat(a)) and start_bal is None: start_bal = bal
        bal += t['net']
    start_bal = start_bal or bal
    nets = [t['net'] for t in ts]; gp = sum(x for x in nets if x > 0); gl = -sum(x for x in nets if x < 0)
    rs = []
    for t in ts:
        unit = abs(t['open_price'] - t['sl']) * CONTRACT[symbol] / (t['sl'] if symbol == 'USDJPY' else 1.)
        if unit > 0 and t['volume'] > 0: rs.append(t['net'] / (unit * t['volume']))
    b_, peak, dd = start_bal, start_bal, 0.0
    for t in sorted(ts, key=lambda t: t['close_epoch']):
        b_ += t['net']; peak = max(peak, b_); dd = max(dd, (peak - b_) / peak)
    days = (date.fromisoformat(b) - date.fromisoformat(a)).days; weekdays = days * 5 / 7
    kinds = [exit_kind(t) for t in ts]
    return dict(trades=len(ts), per_month=round(len(ts) / (days / 30.4375), 2), per_day=round(len(ts) / weekdays, 3),
                win_rate=round(100 * sum(x > 0 for x in nets) / len(nets), 1) if nets else None, pf=round(gp / gl, 2) if gl else None,
                avg_r=round(sum(rs) / len(rs), 3) if rs else None, ret=round(100 * sum(nets) / start_bal, 1), closed_dd=round(100 * dd, 1),
                tp=round(100 * kinds.count('tp') / len(kinds)) if kinds else None, sl=round(100 * kinds.count('sl') / len(kinds)) if kinds else None)


def main():
    status = read(R / 'RUN_STATUS.json')['complete']; plan = read(B / 'Portfolio Long History All ORB05 2026-10-14' / 'PLAN.json')
    out = {}; lines = ['# Negative RR Study — standalone native results (generated)', '',
                       'Native MT5 Model 4, 150 ms, $10k, 1% risk, 2021-10-06 -> 2026-10-06. Current = FRESH baseline in the same tester state.',
                       'Windows by trade open date (data_split.py). Avg R = net / initial stop risk. TP / SL = share of exits at target / stop.', '']
    for key in NAMES:
        slug, _, flag = key.partition('|'); sym = next(c for c in plan['cases'] if c['slug'] == slug)['symbol']
        out[key] = {}
        lines += [f'## {NAMES[key]}', '', '| Window | Target | Trades | / month | / day | Win rate | PF | Avg R | Return | Closed DD | TP exits | SL exits | 5y native equity DD |',
                  '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for w, (a, b) in WINDOWS.items():
            for lv in LEVELS:
                st = status.get(f"{lv}{'-dioff' if flag else ''}|{slug}")
                if not st: continue
                res = read(st['path']); s = stats(res, sym, a, b); out[key].setdefault(w, {})[lv] = s
                dd5 = res['metrics']['equity_dd_pct'] if w == '5 years' else ''
                lines.append(f"| {w} | {LABEL[lv]} | {s['trades']} | {s['per_month']} | {s['per_day']} | {s['win_rate']}% | {s['pf']} | {s['avg_r']} | {s['ret']}% | {s['closed_dd']}% | {s['tp']}% | {s['sl']}% | {dd5}{'%' if dd5 != '' else ''} |")
        lines.append('')
    (R / 'STANDALONE.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    (R / 'STANDALONE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8'); print('\n'.join(lines))


if __name__ == '__main__':
    main()
