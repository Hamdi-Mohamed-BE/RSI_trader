"""Owner 2026-11-04: FTMO17 (current pick) vs E10 for October 2026 at 1% risk per trade, per EA with trade counts, no guard, Prop Ready
guard, and the ftmo 1_step guard. Source = the native Model 4 October member ledgers (Portfolio October 2026 ATR6 2026-11-03/native,
2026-10-01 -> 2026-11-01 exclusive, 100% real ticks, recorded costs, standalone at 1%, $10k). R = net / (1% of the standalone balance before
the trade). E10's 3 Way Gold = only the '3WG BRK' trades of the market-entry run (checked against the breakout-only parity run).
Replay from a fresh $10,000, trades in time order, closes before opens at equal timestamps:
  NONE   : risk 1% of the current closed balance, every trade taken.
  PROP   : CalyxFTMOGuard.mqh Prop Ready family at a 1% cap (Packages/FTMO-AnyBroker), phase 1 = Challenge: risk = min(1% reference, 1% balance);
           total 4.5R / symbol 3R; 7 entries, 3 losing closes per Prague day; projected = balance - reserve(open) - 1.25 risk - 0.05% ref;
           reject if projected < 92% ref or anchor - projected > 3% ref; day latch at anchor - 3%; 3 s entry wait; +10% target after 4 days.
  ONESTEP: ftmo 1_step/CalyxFTMOGuard.mqh, Challenge: as PROP, but projected must stay >= floor + 2% (floor = highest Prague-midnight balance
           - 10% ref) and anchor - projected <= 2.5% (day latch 2.5%); no entries once today's P&L >= 4.5%; target +10% only when best day <= 50%.
Guards are replayed from closed balance: floating equity, margin and swap reserves are NOT modelled (no intratrade marks in these runs).
Python replay of native ledgers, not a native combined run. -> RESULTS.json, RESULTS.md"""
import gzip, json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

H = Path(__file__).resolve().parent; OCT = H.parent / 'Portfolio October 2026 ATR6 2026-11-03'
PLAN = json.loads((OCT / 'PLAN.json').read_text(encoding='utf-8')); PRAGUE = ZoneInfo('Europe/Prague'); S0 = 10000.0; RISK = 0.01
WEEKDAYS = sum(1 for i in range(31) if (date(2026, 10, 1) + timedelta(days=i)).weekday() < 5)
FTMO17 = [(p['key'], 'NEW', None) for p in PLAN if p['tag'] == 'NEW']
E10 = [('usdjpy-london-open-momentum', 'NEW', None), ('ema3', 'NEW', None), ('orb-volume-profile-volume-confirmed', 'FULL', None), ('orb-volume-profile', 'FULL', None),
       ('sell-nasdaq-15min', 'FULL', None), ('xau-regime-switch', 'FULL', None), ('xau-elliott-wave-1-2-3', 'FULL', None), ('nasdaq-5m-candle-momentum', 'NEW', None),
       ('xau-rsi-vwap', 'NEW', None), ('3-way-gold', 'NEW', '3WG BRK')]


def ledger(key, tag, only):
    row = next(p for p in PLAN if p['key'] == key and p['tag'] == tag); d = OCT / 'native' / row['case']
    meta = json.loads((d / 'run.json').read_text(encoding='utf-8')); assert meta['ok'], key
    T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda x: x['close_time']); bal = S0; out = []
    for x in T:
        r = x['net_profit'] / (0.01 * bal); bal += x['net_profit']
        if only and not (x.get('entry_comment') or '').startswith(only): continue
        out.append(dict(key=key, symbol=row['symbol'], o=datetime.fromisoformat(x['open_time']).replace(tzinfo=timezone.utc),
                        c=datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc), R=r, eot='end of test' in (x.get('exit_comment') or '').lower()))
    return out


def replay(members, mode):
    rows = [r for m in members for r in ledger(*m)]
    events = sorted([(r['o'], 1, i) for i, r in enumerate(rows)] + [(r['c'], 0, i) for i, r in enumerate(rows)], key=lambda e: (e[0], e[1], e[2]))
    bal = peak = hwm = anchor = S0; dd = 0.0; open_ = {}; taken = []; blocked = defaultdict(int); blocked_ea = defaultdict(int); day = None; entries = losses = 0
    stopped = False; last = None; day_net = defaultdict(float); entry_days = set()
    breach2 = breach1 = None; max_open = 0
    daily = {'PROP': 0.03, 'ONESTEP': 0.025}.get(mode)

    def best_ok():
        profit = bal - S0
        return profit > 0 and max(day_net.values(), default=0.0) <= 0.5 * profit + 1e-8

    for t, kind, i in events:
        r = rows[i]; d = t.astimezone(PRAGUE).date()
        if d != day:
            if day is not None: hwm = max(hwm, bal)      # end-of-day balance trails the 1-Step floor up
            day = d; anchor = bal; entries = losses = 0; stopped = False
        if kind == 0:
            if i not in open_: continue
            risk = open_.pop(i); pnl = risk * r['R']; bal += pnl; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
            losses += pnl < 0; day_net[d] += pnl; taken.append(dict(r, pnl=pnl))
            if daily and bal <= anchor - daily * S0 + 1e-8: stopped = True
            if bal <= 0.90 * S0 or bal <= anchor - 0.05 * S0: breach2 = breach2 or (d.isoformat(), round((bal / S0 - 1) * 100, 2), round((bal - anchor) / S0 * 100, 2))   # FTMO 2-step limits, closed balance only
            if bal <= hwm - 0.10 * S0 or bal <= anchor - 0.03 * S0: breach1 = breach1 or (d.isoformat(), round((bal / S0 - 1) * 100, 2), round((bal - anchor) / S0 * 100, 2))   # FTMO 1-Step limits, closed balance only
            continue
        if mode == 'NONE':
            open_[i] = bal * RISK; max_open = max(max_open, len(open_)); continue
        risk = min(S0 * RISK, bal * RISK); reserve = sum(1.25 * v + 0.0005 * S0 for v in open_.values())
        projected = bal - reserve - 1.25 * risk - 0.0005 * S0
        tot = sum(open_.values()); same = sum(v for j, v in open_.items() if rows[j]['symbol'] == r['symbol']); why = None
        if mode == 'PROP' and bal >= 1.10 * S0 and len(entry_days) >= 4: why = 'target reached'
        elif mode == 'ONESTEP' and bal >= 1.10 * S0 and best_ok(): why = 'target reached'
        elif stopped: why = 'day latched'
        elif entries >= 7: why = '7 entries a day'
        elif losses >= 3: why = '3 losses a day'
        elif mode == 'ONESTEP' and bal - anchor >= 0.045 * S0 - 1e-8: why = 'best-day cap 4.5%'
        elif tot + risk > 4.5 * S0 * RISK + 1e-7: why = 'total open risk 4.5R'
        elif same + risk > 3 * S0 * RISK + 1e-7: why = 'symbol open risk 3R'
        elif mode == 'PROP' and projected < 0.92 * S0: why = 'equity buffer 92%'
        elif mode == 'ONESTEP' and projected < hwm - 0.10 * S0 + 0.02 * S0: why = 'floor + 2% buffer'
        elif anchor - projected > daily * S0 + 1e-8: why = f'daily reserve {daily * 100:g}%'
        elif last is not None and (t - last).total_seconds() < 3: why = '3 s entry wait'
        if why: blocked[why] += 1; blocked_ea[r['key']] += 1; continue
        open_[i] = risk; entries += 1; last = t; entry_days.add(d); max_open = max(max_open, len(open_))
    P = [x['pnl'] for x in taken]; gp, gl = sum(v for v in P if v > 0), -sum(v for v in P if v < 0); by = defaultdict(lambda: [0, 0.0, 0])
    for x in taken: by[x['key']][0] += 1; by[x['key']][1] += x['pnl']; by[x['key']][2] += x['pnl'] > 0
    signals = defaultdict(int)
    for r in rows: signals[r['key']] += 1
    eot = [x for x in taken if x['eot']]
    return dict(end_of_test=dict(trades=len(eot), pct=round(sum(x['pnl'] for x in eot) / S0 * 100, 2)), ret_to_oct29=round(sum(x['pnl'] for x in taken if x['c'].astimezone(PRAGUE).date() < date(2026, 10, 30)) / S0 * 100, 2),
                ret=round((bal / S0 - 1) * 100, 2), net=round(bal - S0, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(v > 0 for v in P) / len(P), 1) if P else None,
                signals=len(rows), trades=len(P), per_day=round(len(P) / WEEKDAYS, 2), closed_dd=round(dd, 2), best_day=round(max(day_net.values(), default=0) / S0 * 100, 2),
                worst_day=round(min(day_net.values(), default=0) / S0 * 100, 2), blocked=dict(blocked), max_open=max_open, breach_ftmo_2step=breach2, breach_ftmo_1step=breach1,
                best_day_date=max(day_net, key=day_net.get).isoformat() if day_net else None, min_balance_pct=round((min(S0 + sum(x['pnl'] for x in taken[:n]) for n in range(len(taken) + 1)) / S0 - 1) * 100, 2),
                members={k: dict(signals=signals[k], trades=by[k][0], wins=by[k][2], pct=round(by[k][1] / S0 * 100, 2), blocked=blocked_ea.get(k, 0)) for k in sorted(signals)})


# parity: October '3WG BRK' trades of the all-module market run vs the breakout-only package parity run
par = json.loads(gzip.open(H.parent / 'Edge Portfolio E10 2026-11-04/parity-native/nw-XAUUSD-3-way-gold-WRAP-6m/trades.json.gz').read())
a = sorted(x['open_time'][:16] for x in par if x['open_time'] >= '2026-10-01')
b = sorted(r['o'].strftime('%Y-%m-%dT%H:%M') for r in ledger('3-way-gold', 'NEW', '3WG BRK'))
out = dict(parity_3wg_breakout_only=dict(parity_run=a, filtered=b, same=a == b))
print('3WG breakout parity', a == b, len(a), len(b), flush=True)
for name, m in (('FTMO17', FTMO17), ('E10', E10)):
    out[name] = {mode: replay(m, mode) for mode in ('NONE', 'PROP', 'ONESTEP')}
(H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
L = ['| Portfolio | Version | Return | Net on $10k | PF | Win % | Trades taken (of signals) | Trades / weekday | Closed DD | Best / worst day | Blocked by |', '|---|---|---:|---:|---:|---:|---|---:|---:|---|---|']
NAMES = {'NONE': 'No guard', 'PROP': 'Prop Ready guard', 'ONESTEP': '1-Step guard'}
for n in ('FTMO17', 'E10'):
    for m, x in out[n].items():
        L.append(f"| {n} | {NAMES[m]} | {x['ret']:+.2f}% | {x['net']:+,.0f} | {x['pf']} | {x['win']} | {x['trades']} ({x['signals']}) | {x['per_day']} | {x['closed_dd']}% | {x['best_day']:+.2f}% / {x['worst_day']:+.2f}% | {', '.join(f'{k} {v}' for k, v in x['blocked'].items()) or '-'} |")
for n in ('FTMO17', 'E10'):
    L += ['', f'## {n} per EA (return = % of the $10k start)', '| EA | Signals | No guard: trades / wins / % | Prop guard: trades / wins / % | 1-Step guard: trades / wins / % |', '|---|---:|---|---|---|']
    keys = sorted(out[n]['NONE']['members'], key=lambda k: -out[n]['NONE']['members'][k]['pct'])
    for k in keys:
        c = [out[n][m]['members'][k] for m in ('NONE', 'PROP', 'ONESTEP')]
        L.append(f"| {k} | {c[0]['signals']} | " + ' | '.join(f"{x['trades']} / {x['wins']} / {x['pct']:+.2f}%" for x in c) + ' |')
(H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
