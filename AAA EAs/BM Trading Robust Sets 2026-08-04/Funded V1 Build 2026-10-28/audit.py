"""Audit of the funded_v1 native tests (native.py), adapted from Turbo Guard Build 2026-10-26/audit.py. python audit.py -> AUDIT.json, AUDIT.md
parity: original vs pass-through trade lists identical (open, close, side, volume, net) and the pass-through banner present.
guard : every FUNDED_ADMIT budget recomputed from its logged state with the funded_v1 default rule on $50k; risk <= budget and at most one lot
        step below it (or the EA's own smaller request); floor = 50,000 when locked else peak - 3,000; locked exactly when peak - 3,000 >= 50,000;
        no admission on a day-locked day or at/after the daily-win level; minimum / daily-win / day-lock refusals justified; logged day-start
        balance / peak vs an INDEPENDENT rebuild from the report ledger; no FUNDED_BREACH; equity never at the floor or the firm daily limit;
        every FUNDED_CLOSEALL followed by its trigger reason; guard armed banner present.
"""
import gzip, json, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

R = Path(__file__).resolve().parent; N = R / 'native'
MAN = json.loads((R.parent / '_00 Live profiles/Packages/FundedV1/PACKAGE.json').read_text(encoding='utf-8'))
SIZE = 50000.0; TRADE, TAPER, OPEN, SYM, DSTOP, BUF, DWIN, TRAIL, MINR = .005 * SIZE, .05, .02 * SIZE, .015 * SIZE, .02 * SIZE, .0025 * SIZE, .0075 * SIZE, .06 * SIZE, .0005 * SIZE


def case(slug, mode, per): return N / f"nw-{'USTEC' if slug in ('nasdaq-5m-candle-momentum', 'dmc-fresh-reaction-us100') else 'XAUUSD'}-{slug}-{mode}-{per}"
def trades(d): return json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
def journal(d):
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    secs = [s for s in j.split('\n===== ') if 'FUNDED_' in s or 'Funded guard' in s]
    return secs[0] if secs else j
def kv(s): return {k: v for k, v in re.findall(r'(\w+)=([^\s]+)', s)}


def parity():
    out = {}
    for e in MAN['entries']:
        a, b = case(e['slug'], 'orig', '6m'), case(e['slug'], 'pass', '6m')
        if not (a / 'run.json').exists() or not (b / 'run.json').exists(): continue
        key = lambda t: (t['open_time'][:19], t['close_time'][:19], t['side'], round(t['volume'], 2), round(t['net_profit'], 2))  # noqa: E731
        ta, tb = sorted(map(key, trades(a))), sorted(map(key, trades(b)))
        out[e['slug']] = dict(pass_through_banner='Funded guard PASS-THROUGH' in journal(b), original=len(ta), pass_through=len(tb),
                              mismatches=sum(x != y for x, y in zip(ta, tb)) + abs(len(ta) - len(tb)),
                              original_net=round(sum(x[4] for x in ta), 2), pass_net=round(sum(x[4] for x in tb), 2))
    return out


def guard_one(e):
    d = case(e['slug'], 'guard', '1y')
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text()); j = journal(d); tr = trades(d)
    ev = [(datetime.strptime(t, '%Y.%m.%d %H:%M:%S'), k, kv(rest)) for t, k, rest in re.findall(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+FUNDED_(\w+) ([^\r\n]*)', j)]
    bad = defaultdict(list); admits = rejects = 0; reasons = Counter(); risks = []; closeall = Counter(); locked_days = set()
    for ts, k, x in ev:
        if k == 'ADMIT':
            admits += 1; f = {n: float(x[n]) for n in ('unit', 'step', 'req', 'vol', 'risk', 'budget', 'room', 'bal', 'eq', 'open', 'sym', 'stress', 'dayref', 'peak', 'floor')}
            exp = min(TRADE, TAPER * f['room'], OPEN - f['open'], SYM - f['sym'], DSTOP - (f['dayref'] - f['stress']), f['room'] - BUF)
            risks.append(f['risk']); lock = int(x['locked']) == 1
            if lock != (f['peak'] - TRAIL >= SIZE - 1e-6): bad['lock_state'].append(str(ts))
            if abs(f['floor'] - (SIZE if lock else f['peak'] - TRAIL)) > .011: bad['floor_rule'].append(str(ts))
            if abs(f['room'] - (f['stress'] - f['floor'])) > .011: bad['room_formula'].append(str(ts))
            if abs(f['budget'] - exp) > .011: bad['budget_formula'].append((str(ts), f['budget'], round(exp, 2)))
            if f['risk'] > f['budget'] + .011: bad['risk_above_budget'].append(str(ts))
            if f['risk'] < f['budget'] - f['unit'] * f['step'] - .011 and f['vol'] < f['req'] - 1e-9: bad['rounded_more_than_one_step'].append(str(ts))
            if f['eq'] - f['dayref'] >= DWIN - 1e-9: bad['admitted_at_daily_win'].append(str(ts))
            if f['budget'] < MINR - 1e-9: bad['admitted_below_minimum'].append(str(ts))
            if x['day'] in locked_days: bad['admitted_on_locked_day'].append(str(ts))
        elif k == 'REJECT':
            rejects += 1; reasons[x.get('reason', '?')] += 1
            if x.get('reason', '').startswith('min_') and float(x['budget']) >= MINR: bad['minimum_unjustified'].append(str(ts))
            if x.get('reason') == 'dailywin' and float(x['eq']) - float(x['dayref']) < DWIN - 1e-9: bad['dailywin_unjustified'].append(str(ts))
            if x.get('reason') == 'daylock' and x['day'] not in locked_days: bad['daylock_unjustified'].append(str(ts))
        elif k in ('DAILYWIN', 'DAILYLOSS', 'FLOORSTOP'):
            locked_days.add(x['day'])
            if k == 'DAILYWIN' and float(x['eq']) - float(x['dayref']) < DWIN - 1e-6: bad['dailywin_trigger'].append(str(ts))
            if k == 'DAILYLOSS' and float(x['dayref']) - float(x['eq']) < DSTOP - 1e-6: bad['dailyloss_trigger'].append(str(ts))
        elif k == 'CLOSEALL':
            closeall[x.get('reason', '?')] += 1
        elif k == 'BREACH':
            bad['breach'].append(str(ts))
        elif k == 'DAYEND':
            if float(x['min_eq_room']) <= 0: bad['equity_at_floor'].append(x['day'])
            if float(x['min_daily_room']) <= 0: bad['equity_at_firm_daily'].append(x['day'])
    closes = sorted((datetime.fromisoformat(t['close_time']), t['net_profit']) for t in tr)

    def rebuild(ts, inclusive):
        bal = peak = SIZE
        for when, v in closes:
            if when > ts or (when == ts and not inclusive): break
            bal += v; peak = max(peak, bal)
        return bal, peak
    dmax, ndays = 0.0, 0
    for ts, k, x in ev:
        if k != 'DAY': continue
        ndays += 1; lb, lp = float(x['bal']), float(x['peak'])
        dmax = max(dmax, min(max(abs(lb - b_), abs(lp - p_)) for b_, p_ in (rebuild(ts, False), rebuild(ts, True))))
    if dmax > 2.0: bad['floor_rebuild_mismatch'].append(round(dmax, 2))
    if 'Funded guard armed' not in j: bad['guard_not_armed'].append(1)
    net = sum(t['net_profit'] for t in tr); gp = sum(t['net_profit'] for t in tr if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in tr if t['net_profit'] < 0)
    dayend = [kv(m) for m in re.findall(r'FUNDED_DAYEND ([^\r\n]*)', j)]
    return dict(trades=len(tr), per_month=round(len(tr) / 12, 2), per_day=round(len(tr) / 261, 3), net=round(net, 2), pf=round(gp / gl, 2) if gl else None,
                admits=admits, rejects_logged=rejects, reject_reasons=dict(reasons), close_all=dict(closeall), locked_days=len(locked_days),
                avg_risk=round(sum(risks) / len(risks), 2) if risks else None, max_risk=max(risks, default=None),
                min_equity_room=min((float(x['min_eq_room']) for x in dayend), default=None), min_daily_room=min((float(x['min_daily_room']) for x in dayend), default=None),
                floor_rebuild_days=ndays, floor_rebuild_max_diff=round(dmax, 2), failures={k: v[:5] for k, v in bad.items()}, failure_counts={k: len(v) for k, v in bad.items()},
                passed=not bad, report_ok=meta.get('ok'), journal_flags=meta.get('journal_flags'))


def main():
    out = dict(parity=parity(), guard={e['slug']: guard_one(e) for e in MAN['entries']})
    (R / 'AUDIT.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    md = ['# funded_v1 native test audit (generated by audit.py)', '', '## Wrapper fidelity: original EX5 vs guarded EX5 in pass-through mode (6m, Model 4, $50k, 1:30)', '',
          '| EA | Original trades | Pass-through trades | Mismatches | Original net | Pass-through net |', '|---|---:|---:|---:|---:|---:|']
    for k, v in out['parity'].items():
        md.append(f"| {k} | {v['original']} | {v['pass_through']} | {v['mismatches']} | ${v['original_net']:,.2f} | ${v['pass_net']:,.2f} |")
    md += ['', '## Guard ON (defaults), single EA, 1 year (2025-10-27 → 2026-10-27), $50k, 1:30', '',
           '| EA | Trades | /month | /day | Net | PF | Admitted | Refusals logged (reasons) | Close-all events | Avg / max risk | Min equity room over floor | Min room to firm daily | Floor rebuild max diff | Audit |',
           '|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|']
    for k, v in out['guard'].items():
        if not v: continue
        md.append(f"| {k} | {v['trades']} | {v['per_month']} | {v['per_day']} | ${v['net']:,.0f} | {v['pf']} | {v['admits']} | {v['rejects_logged']} {v['reject_reasons']} | {v['close_all'] or '-'} | "
                  f"${v['avg_risk']} / ${v['max_risk']} | ${v['min_equity_room']:,.0f} | ${v['min_daily_room']:,.0f} | ${v['floor_rebuild_max_diff']} | "
                  f"{'PASS' if v['passed'] else 'FAIL ' + json.dumps(v['failure_counts'])} |")
    (R / 'AUDIT.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
