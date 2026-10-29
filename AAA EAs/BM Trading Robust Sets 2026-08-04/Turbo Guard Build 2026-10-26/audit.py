"""Audit of the native Turbo5 tests (native_tests.py). python audit.py -> AUDIT.json, AUDIT.md
parity: original vs pass-through trade lists identical (open, close, side, volume, net).
guard : every TURBO_ADMIT budget recomputed from its logged state with the guard rule (sim.py improved 0.75 profile on $50k);
        risk <= budget and at most one lot step below it (or the EA's own smaller request); profit-cap / minimum rejections justified;
        logged day-start balance / peak / floor vs an INDEPENDENT rebuild from the report ledger + logged withdrawals;
        no TURBO_BREACH; equity never at the floor or the 3% daily limit (TURBO_DAYEND); reward rules re-checked per payout.
"""
import gzip, json, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

R = Path(__file__).resolve().parent; N = R / 'native'
MAN = json.loads((R.parent / '_00 Live profiles/Packages/Turbo5/PACKAGE.json').read_text(encoding='utf-8'))
SIZE = 50000.0; TRADE, TAPER, OPEN, SYM, DSTOP, BUF, DCAP, TRAIL, MINR = .0075 * SIZE, .05, .02 * SIZE, .015 * SIZE, .02 * SIZE, .0025 * SIZE, .0075 * SIZE, .06 * SIZE, .0005 * SIZE


def case(slug, mode, per): return N / f"nw-{'USTEC' if slug == 'nasdaq-5m-candle-momentum' else 'XAUUSD'}-{slug}-{mode}-{per}"
def trades(d): return json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
def journal(d):
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    secs = [s for s in j.split('\n===== ') if 'TURBO_' in s]
    return secs[0] if secs else j
def kv(s): return {k: v for k, v in re.findall(r'(\w+)=([^\s]+)', s)}


def parity():
    out = {}
    for e in MAN['entries']:
        a, b = case(e['slug'], 'orig', '6m'), case(e['slug'], 'pass', '6m')
        if not (a / 'run.json').exists() or not (b / 'run.json').exists(): continue
        key = lambda t: (t['open_time'][:19], t['close_time'][:19], t['side'], round(t['volume'], 2), round(t['net_profit'], 2))  # noqa: E731
        ta, tb = sorted(map(key, trades(a))), sorted(map(key, trades(b)))
        banner = 'Turbo guard PASS-THROUGH' in journal(b)
        out[e['slug']] = dict(pass_through_banner=banner, original=len(ta), pass_through=len(tb), mismatches=sum(x != y for x, y in zip(ta, tb)) + abs(len(ta) - len(tb)),
                              original_net=round(sum(x[4] for x in ta), 2), pass_net=round(sum(x[4] for x in tb), 2),
                              seen_lines=len(re.findall(r'TURBO_SEEN', journal(b))))
    return out


def guard_one(e):
    d = case(e['slug'], 'guard', '1y')
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text()); j = journal(d); tr = trades(d)
    ev = [(datetime.strptime(t, '%Y.%m.%d %H:%M:%S'), k, kv(rest)) for t, k, rest in re.findall(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+TURBO_(\w+) ([^\r\n]*)', j)]
    bad = defaultdict(list); admits = rejects = 0; reasons = Counter(); pays = []; budgets = []
    for ts, k, x in ev:
        if k == 'ADMIT':
            admits += 1; f = {n: float(x[n]) for n in ('unit', 'step', 'req', 'vol', 'risk', 'budget', 'room', 'bal', 'eq', 'open', 'sym', 'stress', 'anchor', 'peak', 'floor', 'dayreal')}
            exp = min(TRADE, TAPER * f['room'], OPEN - f['open'], SYM - f['sym'], DSTOP - (f['anchor'] - f['stress']), f['room'] - BUF)
            budgets.append(f['risk'])
            if abs(f['floor'] - (f['peak'] - TRAIL)) > .011: bad['floor_not_peak_minus_6pct'].append(str(ts))
            if abs(f['room'] - (f['stress'] - f['floor'])) > .011: bad['room_formula'].append(str(ts))
            if abs(f['budget'] - exp) > .011: bad['budget_formula'].append((str(ts), f['budget'], round(exp, 2)))
            if f['risk'] > f['budget'] + .011: bad['risk_above_budget'].append((str(ts), f['risk'], f['budget']))
            if f['risk'] < f['budget'] - f['unit'] * f['step'] - .011 and f['vol'] < f['req'] - 1e-9: bad['rounded_more_than_one_step'].append(str(ts))
            if f['dayreal'] >= DCAP - 1e-9: bad['admitted_after_profit_cap'].append(str(ts))
            if f['budget'] < MINR - 1e-9: bad['admitted_below_minimum'].append(str(ts))
        elif k == 'REJECT':
            rejects += 1; reasons[x.get('reason', '?')] += 1
            if x.get('reason') == 'profitcap' and float(x['dayreal']) < DCAP - 1e-9: bad['profitcap_unjustified'].append(str(ts))
            if x.get('reason', '').startswith('min_') and float(x['budget']) >= MINR: bad['minimum_unjustified'].append(str(ts))
        elif k == 'PAY':
            pays.append((ts, float(x['amount']), int(x['ok']), int(x['prof_days']), float(x['max_day'])))
            if int(x['ok']) and (int(x['prof_days']) < 3 or float(x['max_day']) > .2 * float(x['amount']) + .01): bad['reward_rule'].append(str(ts))
        elif k == 'BREACH':
            bad['breach'].append(str(ts))
        elif k == 'DAYEND':
            if float(x['min_eq_room']) <= 0: bad['equity_at_floor'].append(x['day'])
            if float(x['min_daily_room']) <= 0: bad['equity_at_daily_limit'].append(x['day'])
    # Independent floor rebuild: closed balance from the report ledger (trades closed before the logged time) minus logged withdrawals.
    closes = sorted((datetime.fromisoformat(t['close_time']), t['net_profit']) for t in tr)
    paid = [(ts, a) for ts, a, ok, _, _ in pays if ok]
    marks = sorted([(ts, 'c', v) for ts, v in closes] + [(ts, 'w', -a) for ts, a in paid], key=lambda z: (z[0], z[1] == 'c'))
    # A stop/target hit on the first tick of a firm day is booked BEFORE TURBO_DAY is logged; a strategy time exit on that tick comes AFTER.
    # So a close at exactly the logged second may be on either side: both orders are accepted.
    def rebuild(ts, inclusive):
        bal = peak = SIZE
        for when, kind, v in marks:
            if when > ts or (when == ts and not inclusive): break
            bal += v; peak = max(peak, bal) if kind == 'c' else bal
        return bal, peak
    dmax, ndays = 0.0, 0
    for ts, k, x in ev:
        if k != 'DAY': continue
        ndays += 1; lb, lp = float(x['bal']), float(x['peak'])
        dmax = max(dmax, min(max(abs(lb - b_), abs(lp - p_)) for b_, p_ in (rebuild(ts, False), rebuild(ts, True))))
    if dmax > 2.0: bad['floor_rebuild_mismatch'].append(round(dmax, 2))
    if 'Turbo guard armed' not in j: bad['guard_not_armed'].append(1)
    net = sum(t['net_profit'] for t in tr); gp = sum(t['net_profit'] for t in tr if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in tr if t['net_profit'] < 0)
    dayend = [kv(m) for m in re.findall(r'TURBO_DAYEND ([^\r\n]*)', j)]
    return dict(trades=len(tr), per_month=round(len(tr) / 12, 2), per_day=round(len(tr) / 261, 3), net=round(net, 2), pf=round(gp / gl, 2) if gl else None,
                admits=admits, rejects=rejects, reject_reasons=dict(reasons), payouts=sum(1 for p in paid), withdrawn=round(sum(a for _, a in paid), 2),
                trader_share_80=round(.8 * sum(a for _, a in paid), 2), avg_risk=round(sum(budgets) / len(budgets), 2) if budgets else None, max_risk=max(budgets, default=None),
                min_equity_room=min((float(x['min_eq_room']) for x in dayend), default=None), min_daily_room=min((float(x['min_daily_room']) for x in dayend), default=None),
                floor_rebuild_days=ndays, floor_rebuild_max_diff=round(dmax, 2), failures={k: v[:5] for k, v in bad.items()}, failure_counts={k: len(v) for k, v in bad.items()},
                passed=not bad, report_ok=meta.get('ok'), journal_flags=meta.get('journal_flags'))


def main():
    out = dict(parity=parity(), guard={e['slug']: guard_one(e) for e in MAN['entries']})
    (R / 'AUDIT.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    md = ['# Turbo5 native test audit (generated by audit.py)', '', '## Wrapper fidelity: original EX5 vs guarded EX5 in pass-through mode (6m, Model 4, $50k, 1:30)', '',
          '| EA | Original trades | Pass-through trades | Mismatches | Original net | Pass-through net |', '|---|---:|---:|---:|---:|---:|']
    for k, v in out['parity'].items():
        md.append(f"| {k} | {v['original']} | {v['pass_through']} | {v['mismatches']} | ${v['original_net']:,.2f} | ${v['pass_net']:,.2f} |")
    md += ['', '## Guard ON, single EA, 1 year (2025-10-27 → 2026-10-27), tester-simulated 14-day rewards', '',
           '| EA | Trades | /month | /day | Net | PF | Admitted | Rejected (reasons) | Avg / max risk | Payouts | Trader 80% | Min equity room over floor | Min daily room | Floor rebuild max diff | Audit |',
           '|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|']
    for k, v in out['guard'].items():
        if not v: continue
        md.append(f"| {k} | {v['trades']} | {v['per_month']} | {v['per_day']} | ${v['net']:,.0f} | {v['pf']} | {v['admits']} | {v['rejects']} {v['reject_reasons']} | "
                  f"${v['avg_risk']} / ${v['max_risk']} | {v['payouts']} | ${v['trader_share_80']:,.0f} | ${v['min_equity_room']:,.0f} | ${v['min_daily_room']:,.0f} | ${v['floor_rebuild_max_diff']} | "
                  f"{'PASS' if v['passed'] else 'FAIL ' + json.dumps(v['failure_counts'])} |")
    (R / 'AUDIT.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
