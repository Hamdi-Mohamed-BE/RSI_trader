"""Builds REPORT.md from RESULTS.json + native ledgers (run analyse.py first). Prose is fixed below; numbers are generated."""
import gzip, json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT / 'RESULTS.json').read_text())
CFG = json.loads((ROOT / 'run-config.json').read_text())
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d')
WEEKENDS = {'6m': 26, '1y': 52, '3y': 157, '5y': 261}   # from the EA's WVA_SUMMARY weekends= counter
f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731


def ledger(v, per):
    t = json.loads(gzip.decompress((ROOT / 'native' / f'nw-BTCUSD-{v}-{per}' / 'trades.json.gz').read_bytes()))
    return t


def main_table():
    out = ['| Version | Window | Trades | /month | /day | /weekend | Return | PF | Win % | Consistency | Avg win / loss streak (max) | Sharpe | Bal DD | Eq DD | Mean R | Exits TP / SL / Mon 00:00 |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|']
    for r in R['rows']:
        days = (END - datetime.strptime(CFG['periods'][r['period']], '%Y.%m.%d')).days
        e = r['exits']
        out.append(f"| {r['variant']} | {r['period']} | {r['trades']} | {r['per_month']} | {r['trades'] / days:.3f} | {r['trades'] / WEEKENDS[r['period']]:.2f} | "
                   f"{r['ret']:+.2f}% | {f(r['pf'])} | {f(r['win'])} | {f(r['consistency'], '%')} | {r['avg_w']} / {r['avg_l']} ({r['max_w']} / {r['max_l']}) | "
                   f"{f(r['sharpe'])} | {r['bal_dd']}% | {f(r['eq_dd'], '%')} | {f(r['mean_R'])} | {e.get('TP', 0)} / {e.get('SL', 0)} / {e.get('time/other', 0)} |")
    return '\n'.join(out)


def side_table():
    out = ['| Version | Window | Long trades / net $ | Short trades / net $ |', '|---|---|---|---|']
    for r in R['rows']:
        out.append(f"| {r['variant']} | {r['period']} | {r['long_n']} / {r['long_net']:+,.0f} | {r['short_n']} / {r['short_net']:+,.0f} |")
    return '\n'.join(out)


def year_table():
    out = ['| Year (5y run, by close date) | WVA trades / net $ / PF | WVAH trades / net $ / PF | CRNG trades / net $ / PF |', '|---|---|---|---|']
    data = {}
    for v in ('WVA', 'WVAH', 'CRNG'):
        y = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
        for t in ledger(v, '5y'):
            k = datetime.fromisoformat(t['close_time']).year; p = t['net_profit']
            y[k][0] += 1; y[k][1] += p; y[k][2 if p > 0 else 3] += abs(p)
        data[v] = y
    for k in sorted(set().union(*[d.keys() for d in data.values()])):
        cells = []
        for v in ('WVA', 'WVAH', 'CRNG'):
            n, p, g, l = data[v].get(k, [0, 0, 0, 0])
            cells.append(f"{n} / {p:+,.0f} / {g / l:.2f}" if l else f"{n} / {p:+,.0f} / —")
        label = f'{k} (from 13 Oct)' if k == 2021 else f'{k} (to 12 Oct)' if k == 2026 else str(k)
        out.append(f"| {label} | " + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def diag():
    lines = []
    for v in ('WVA', 'WVAH', 'CRNG'):
        t = ledger(v, '5y')
        gross = sum(x['gross_profit'] for x in t); cost = sum(x['total_costs'] for x in t)
        wk = defaultdict(set)
        for x in t: wk[datetime.fromisoformat(x['open_time']).isocalendar()[:2]].add(x['side'])
        tm = [x['net_profit'] for x in t if not (x.get('exit_comment') or '').lower().startswith(('tp', 'sl'))]
        hold = sorted((datetime.fromisoformat(x['close_time']) - datetime.fromisoformat(x['open_time'])).total_seconds() / 3600 for x in t)
        lines.append(f"| {v} | {gross:+,.0f} | {cost:+,.0f} | {len(wk)} / {sum(len(s) == 2 for s in wk.values())} | "
                     f"{len(tm)} / {sum(tm):+,.0f} / {sum(p > 0 for p in tm)} | {hold[len(hold) // 2]:.1f} / {hold[int(.9 * len(hold))]:.1f} / {hold[-1]:.1f} |")
    return ('| 5y | Gross P&L $ (before costs) | Commission + swap $ | Weekends with a fill / both sides filled | Monday 00:00 time exits: n / net $ / winners | Hold hours median / p90 / max |\n'
            '|---|---:|---:|---|---|---|\n' + '\n'.join(lines))


gate = R['gate']
gate_rows = []
for v, g in gate.items():
    for per, c in g['windows'].items():
        gate_rows.append(f"| {v} | {per} | {'yes' if c['positive'] else '**no**'} | {'yes' if c['pf'] else '**no**'} | {'yes' if c['trades'] else 'no'} | "
                         f"{'yes' if c['beats_control'] else '**no**'} | {'yes' if c['clean'] else 'no'} |")
    gate_rows.append(f"| **{v}** | **verdict** | | | | | **{'PASS' if g['passed'] else 'FAIL'}** |")

TEMPLATE = (ROOT / 'REPORT.template.md').read_text(encoding='utf-8')
(ROOT / 'REPORT.md').write_text(TEMPLATE.replace('{{MAIN}}', main_table()).replace('{{SIDES}}', side_table()).replace('{{YEARS}}', year_table())
                                .replace('{{DIAG}}', diag()).replace('{{GATE}}', '\n'.join(gate_rows)), encoding='utf-8')
print('REPORT.md written')
