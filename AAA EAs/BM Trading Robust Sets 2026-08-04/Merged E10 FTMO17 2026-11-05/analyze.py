"""All-years analysis of FTMO17, E10 and the merged M22 from the 22 standalone native ledgers of native.py (2019-01-01 -> 2026-11-01, USTEC data from 2019-07-16).
R = net / (1% of the standalone balance before the trade). Evidence type: Python replay of native ledgers, not a combined native run.
Replay from a fresh $10,000 per window at 0.5 / 0.75 / 1%:
  NONE    every trade, risk = r x current closed balance.
  PROP    Prop Ready guard in Funded mode (no target stop): risk = min(r x reference, r x balance), 4.5R / 3R caps, 7 entries and 3 losing closes a Prague day,
          projected = balance - reserve(open) - 1.25 risk - 0.05% ref; reject below 92% ref or a projected daily loss over 3%; day latch at 3%; 3 s wait.
  ONESTEP ftmo 1_step guard in Funded mode: as PROP, projected >= trailing floor + 2%, projected daily loss <= 2.5%, latch 2.5%, no entries after a +4.5% day.
Guards work from closed balance here: floating equity, margin and swap reserves are not modelled. A guard stuck at its buffer stays stuck, as on a live account until a rerun.
Also: firm-limit touches on closed balance; three-way Monte Carlo and day-block bootstrap on R; buy-and-hold on the same windows. -> ANALYSIS.json, TABLES_ALL_YEARS.md"""
import gzip, json, statistics, sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

H = Path(__file__).resolve().parent; PIPE = H.parents[1] / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, robustness as rb  # noqa: E402
PLAN = json.loads((H / 'NATIVE_PLAN.json').read_text(encoding='utf-8')); PRAGUE = ZoneInfo('Europe/Prague'); S0 = 10000.0
WINDOWS = {**PLAN['windows'], **PLAN['years']}; RUNS = {r['key']: r for r in PLAN['runs']}
EXTRA = {'orb-volume-profile-volume-confirmed', 'orb-volume-profile', 'sell-nasdaq-15min', 'xau-regime-switch', 'xau-elliott-wave-1-2-3'}
E10_KEYS = {'usdjpy-london-open-momentum', 'ema3', 'nasdaq-5m-candle-momentum', 'xau-rsi-vwap'} | {'orb-volume-profile-volume-confirmed', 'orb-volume-profile', 'sell-nasdaq-15min', 'xau-regime-switch', 'xau-elliott-wave-1-2-3'}
RISKS = (0.005, 0.0075, 0.01); MODES = ('NONE', 'PROP', 'ONESTEP')


def ledger(key):
    d = H / 'native' / RUNS[key]['case']; meta = json.loads((d / 'run.json').read_text(encoding='utf-8')); assert meta['ok'], key
    T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda x: x['close_time']); bal = S0; out = []
    for x in T:
        r = x['net_profit'] / (0.01 * bal); bal += x['net_profit']
        out.append(dict(key=key, symbol=RUNS[key]['symbol'], o=datetime.fromisoformat(x['open_time']).replace(tzinfo=timezone.utc), c=datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc),
                        R=r, comment=x.get('entry_comment') or ''))
    return out, meta


LEDGERS = {k: ledger(k) for k in RUNS}
ALL = {k: v[0] for k, v in LEDGERS.items()}
PORT = {'FTMO17': [r for k, v in ALL.items() if k not in EXTRA for r in v],
        'E10': [r for k, v in ALL.items() if k in E10_KEYS for r in v] + [r for r in ALL['3-way-gold'] if r['comment'].startswith('3WG BRK')],
        'M22': [r for v in ALL.values() for r in v]}


def weekdays(a, b):
    return sum(1 for o in range(date.fromisoformat(a).toordinal(), date.fromisoformat(b).toordinal()) if date.fromordinal(o).weekday() < 5)


def replay(all_rows, window, mode, risk_pct):
    a, b = WINDOWS[window]; lo = datetime.fromisoformat(a).replace(tzinfo=timezone.utc); hi = datetime.fromisoformat(b).replace(tzinfo=timezone.utc)
    rows = [r for r in all_rows if lo <= r['o'] < hi]
    events = sorted([(r['o'], 1, i) for i, r in enumerate(rows)] + [(r['c'], 2 if r['c'] == r['o'] else 0, i) for i, r in enumerate(rows)], key=lambda e: (e[0], e[1], e[2]))   # a same-second trade opens first
    bal = peak = hwm = anchor = S0; dd = 0.0; open_ = {}; taken = []; blocked = defaultdict(int); day = None; entries = losses = 0; stopped = False; last = None; day_net = defaultdict(float)
    touch2 = touch1 = None; last_entry = None; daily = {'PROP': 0.03, 'ONESTEP': 0.025}.get(mode)
    for t, kind, i in events:
        r = rows[i]; d = t.astimezone(PRAGUE).date()
        if d != day:
            if day is not None: hwm = max(hwm, bal)
            day = d; anchor = bal; entries = losses = 0; stopped = False
        if kind != 1:
            if i not in open_: continue
            pnl = open_.pop(i) * r['R']; bal += pnl; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100); losses += pnl < 0; day_net[d] += pnl; taken.append(dict(r, pnl=pnl))
            if daily and bal <= anchor - daily * S0 + 1e-8: stopped = True
            if touch2 is None and (bal <= 0.90 * S0 or bal <= anchor - 0.05 * S0): touch2 = d.isoformat()
            if touch1 is None and (bal <= hwm - 0.10 * S0 or bal <= anchor - 0.03 * S0): touch1 = d.isoformat()
            continue
        if mode == 'NONE':
            open_[i] = bal * risk_pct; continue
        risk = min(S0, bal) * risk_pct; reserve = sum(1.25 * v + 0.0005 * S0 for v in open_.values()); projected = bal - reserve - 1.25 * risk - 0.0005 * S0
        tot = sum(open_.values()); same = sum(v for j, v in open_.items() if rows[j]['symbol'] == r['symbol']); why = None
        if stopped: why = 'day latched'
        elif entries >= 7: why = '7 entries'
        elif losses >= 3: why = '3 losses'
        elif mode == 'ONESTEP' and bal - anchor >= 0.045 * S0 - 1e-8: why = 'best-day cap'
        elif tot + risk > 4.5 * S0 * risk_pct + 1e-7: why = 'total 4.5R'
        elif same + risk > 3 * S0 * risk_pct + 1e-7: why = 'symbol 3R'
        elif mode == 'PROP' and projected < 0.92 * S0: why = 'buffer'
        elif mode == 'ONESTEP' and projected < hwm - 0.08 * S0: why = 'buffer'
        elif anchor - projected > daily * S0 + 1e-8: why = 'daily reserve'
        elif last is not None and (t - last).total_seconds() < 3: why = '3 s wait'
        if why: blocked[why] += 1; continue
        open_[i] = risk; entries += 1; last = t; last_entry = d
    P = [x['pnl'] for x in taken]; gp, gl = sum(v for v in P if v > 0), -sum(v for v in P if v < 0); months = weekdays(a, b) / 21.75
    return dict(ret=round((bal / S0 - 1) * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(v > 0 for v in P) / len(P), 1) if P else None, signals=len(rows), trades=len(P),
                per_month=round(len(P) / months, 1), per_weekday=round(len(P) / max(1, weekdays(a, b)), 2), closed_dd=round(dd, 2), best_day=round(max(day_net.values(), default=0) / S0 * 100, 2),
                worst_day=round(min(day_net.values(), default=0) / S0 * 100, 2), blocked=dict(blocked), last_entry=str(last_entry), touch_2step=touch2, touch_1step=touch1)


out = dict(native_checks={k: dict(ok=m['ok'], flags=m['journal_flags'], first=min((r['o'] for r in v), default=None).isoformat() if v else None) for k, (v, m) in LEDGERS.items()},
           per_ea={}, portfolios={}, monte_carlo={}, buy_hold={})
for k, v in sorted(ALL.items(), key=lambda kv: -sum(r['R'] for r in kv[1])):
    R = [r['R'] for r in v]; a, b = WINDOWS['all']; seg = {w: round(sum(r['R'] for r in v if WINDOWS[w][0] <= r['o'].date().isoformat() < WINDOWS[w][1]), 1) for w in ('dev', 'val', 'oos')}
    gl = -sum(x for x in R if x < 0)
    out['per_ea'][k] = dict(in_ftmo17=k not in EXTRA, in_e10=k in E10_KEYS or k == '3-way-gold', trades=len(R), per_month=round(len(R) / (weekdays(a, b) / 21.75), 2), total_r=round(sum(R), 1), mean_r=round(statistics.fmean(R), 3) if R else None,
                            pf=round(sum(x for x in R if x > 0) / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in R) / len(R), 1) if R else None, dd_r=round(rb.max_drawdown(R), 1), seg=seg,
                            years={y: round(sum(r['R'] for r in v if WINDOWS[y][0] <= r['o'].date().isoformat() < WINDOWS[y][1]), 1) for y in PLAN['years']})
for name, rows in PORT.items():
    out['portfolios'][name] = {f'{m}-{r * 100:g}': {w: replay(rows, w, m, r) for w in WINDOWS} for m in MODES for r in RISKS}
    seq = sorted(rows, key=lambda r: (r['c'], r['key'])); R = [r['R'] for r in seq]; a, b = WINDOWS['all']; yrs = (date.fromisoformat(b) - date.fromisoformat(a)).days / 365.25; per_year = round(len(R) / yrs)
    T = [dict(close_time=r['c'].strftime('%Y-%m-%dT%H:%M:%S'), r=r['R']) for r in seq]; cal = [date.fromordinal(o).isoformat() for o in range(date.fromisoformat(a).toordinal(), date.fromisoformat(b).toordinal()) if date.fromordinal(o).weekday() < 5]
    out['monte_carlo'][name] = dict(trades=len(R), per_month=round(len(R) / (yrs * 12), 1), mean_r=round(statistics.fmean(R), 4), pf=round(sum(x for x in R if x > 0) / -sum(x for x in R if x < 0), 3), win=round(100 * sum(x > 0 for x in R) / len(R), 1),
                                    dependence=rb.dependence(T, value='r', time='close_time'), break_even_extra_cost_r=round(statistics.fmean(R), 4), full=rb.three_monte_carlo(R), one_year=rb.three_monte_carlo(R, horizon=per_year),
                                    cost_ladder_one_year={f'{c:.2f}': rb.three_monte_carlo(R, horizon=per_year, extra_cost=c)['randomize']['both'] for c in (0.02, 0.05, 0.10, 0.20)},
                                    block_3m=rb.day_block_bootstrap(T, 65, value='r', paths=10000, block_days=5, seed=20261105, calendar_days=cal), block_12m=rb.day_block_bootstrap(T, 261, value='r', paths=10000, block_days=5, seed=20261105, calendar_days=cal))
for sym in ('XAUUSD', 'USTEC', 'USDJPY'):
    out['buy_hold'][sym] = {w: buy_hold.load(H, sym, w) for w in WINDOWS}
(H / 'ANALYSIS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')

L = []
W = list(PLAN['years']); SEG = ('dev', 'val', 'oos', 'all')
for r in ('0.5', '0.75', '1'):
    L += [f'## {r}% risk: return by window (fresh $10k each; closed DD in brackets for "all")', '| Portfolio | Version | ' + ' | '.join(W) + ' | Dev | Val | OOS | All | All: trades (/month) | All: closed DD | Firm limit first touched (2-step / 1-Step) |', '|---|---|' + '---:|' * (len(W) + 7) + '---|']
    for n in PORT:
        for m in MODES:
            x = out['portfolios'][n][f'{m}-{r}']; a = x['all']
            L.append(f"| {n} | {m} | " + ' | '.join(f"{x[w]['ret']:+.1f}%" for w in W) + ' | ' + ' | '.join(f"{x[s]['ret']:+.1f}%" for s in SEG) + f" | {a['trades']} ({a['per_month']}) | {a['closed_dd']}% | {a['touch_2step'] or '-'} / {a['touch_1step'] or '-'} |")
    L.append('')
L += ['## Buy and hold, 1x notional (native, real spread and swap; long only; USDJPY long is an arbitrary direction)', '| Asset | ' + ' | '.join(W) + ' | Dev | Val | OOS | All | All: price return before financing | All: swap | All: equity DD |', '|---|' + '---:|' * (len(W) + 7)]
for s, x in out['buy_hold'].items():
    a = x['all']; L.append(f'| {s} | ' + ' | '.join(f"{x[w]['return_pct']:+.1f}%" for w in W) + ' | ' + ' | '.join(f"{x[g]['return_pct']:+.1f}%" for g in SEG) + f" | {a['price_return_pct']:+.1f}% | {a['swap_pct']:+.1f}% | {a['max_dd_pct']}% |")
L += ['', '## Portfolio vs buy and hold, all years (no guard; portfolio DD is closed-balance, buy-and-hold DD is equity)', '| Portfolio | Risk | Return | DD | Against | Hold return | Hold DD | Verdict |', '|---|---|---:|---:|---|---:|---:|---|']
for n in PORT:
    for r in ('0.5', '1'):
        a = out['portfolios'][n][f'NONE-{r}']['all']
        for s in ('XAUUSD', 'USTEC'):
            h = out['buy_hold'][s]['all']; c = buy_hold.compare(dict(return_pct=a['ret'], max_dd_pct=a['closed_dd']), h)
            L.append(f"| {n} | {r}% | {a['ret']:+.1f}% | {a['closed_dd']}% | {s} | {h['return_pct']:+.1f}% | {h['max_dd_pct']}% | {c['verdict']} |")
L += ['', '## Monte Carlo, all years (per trade in R, no guard)', '| Portfolio | Trades (/month) | Win % | PF | Mean R | Real DD R / shuffle p95 | Real DD worse than | Best-day check | Resample red 8y / 1y | Randomize red 8y / 1y | 1y red at +0.02 / 0.05 / 0.10R | 12 m block: total p05 / p50 R, DD p95 R |', '|---|---|---:|---:|---:|---|---:|---|---|---|---|---|']
for n, v in out['monte_carlo'].items():
    f, y, bk, c = v['full'], v['one_year'], v['block_12m'], v['cost_ladder_one_year']
    L.append(f"| {n} | {v['trades']} ({v['per_month']}) | {v['win']} | {v['pf']} | {v['mean_r']:+.3f} | {f['real']['max_drawdown']:.1f} / {f['reshuffle']['max_drawdown']['p95']:.1f} | {f['reshuffle']['real_drawdown_worse_than_pct']}% | {v['dependence']['verdict']} | {f['resample']['red_pct']}% / {y['resample']['red_pct']}% | {f['randomize']['both']['red_pct']}% / {y['randomize']['both']['red_pct']}% | {c['0.02']['red_pct']} / {c['0.05']['red_pct']} / {c['0.10']['red_pct']}% | {bk['total']['p05']:+.0f} / {bk['total']['p50']:+.0f}, DD {bk['max_drawdown']['p95']:.0f} |")
L += ['', '## Per EA, all years at 1R per trade', '| EA | FTMO17 | E10 | Trades (/month) | Win % | PF | Mean R | Total R | DD R | ' + ' | '.join(W) + ' | Dev | Val | OOS |', '|---|---|---|---|---:|---:|---:|---:|---:|' + '---:|' * (len(W) + 3)]
for k, v in out['per_ea'].items():
    L.append(f"| {k} | {'yes' if v['in_ftmo17'] else '-'} | {'yes' if v['in_e10'] else '-'} | {v['trades']} ({v['per_month']}) | {v['win']} | {v['pf']} | {v['mean_r']} | {v['total_r']:+.1f} | {v['dd_r']} | " + ' | '.join(f"{v['years'][y]:+.1f}" for y in W) + f" | {v['seg']['dev']:+.1f} | {v['seg']['val']:+.1f} | {v['seg']['oos']:+.1f} |")
(H / 'TABLES_ALL_YEARS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
