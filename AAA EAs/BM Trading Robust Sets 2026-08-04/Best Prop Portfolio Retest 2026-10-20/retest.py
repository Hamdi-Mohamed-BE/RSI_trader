"""Retest of the built Best Prop Portfolio (2026-10-20): OOS phase replay, block-bootstrap Monte Carlo and continuous
OOS performance. Exact package model: nine EAs, per-entry cap 1% ($100 on $10k), total 4.5%, per symbol 3%, $300 daily
reserve/latch, $9,200 buffer, Nasdaq 5M DI OFF (package default), USDJPY ADX20+DI ON. DI ON shown for comparison.
No MT5 terminal, no trading. Uses the frozen engines of FTMO Faster Portfolio Screen / FTMO Dial Study.

python retest.py prepare | freeze | run
"""
import bisect, copy, gzip, hashlib, importlib.util, json, math, random, statistics, sys, time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'; DIAL = B / 'FTMO Dial Study 2026-10-20'; FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
DIOFF = B / 'FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16' / 'native' / 'allrr05-nasdaq-5m-candle-momentum-core-dioff-long-20261016'
PACKAGE = B / '_00 Live profiles' / 'Best Prop Portfolio 2026-10-20' / 'PACKAGE.json'
NASDAQ = 'nasdaq-5m-candle-momentum'
CAP = 100.0; PATHS = 2000; SEED = 20261020; BLOCK_DAYS = 28; BLOCKS = 7
OOS = (date(2024, 10, 6), date(2026, 10, 6))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def prepare():
    pr = load('pr', OLDER / 'prepare.py')
    src, lookup, hashes = pr.load_sources()
    begin, end = midnight(date(2021, 10, 7)), midnight(date(2026, 10, 6))
    # geometry unit-risk parity on the DI-ON Nasdaq source (USTEC is USD-quoted, contract 1)
    on_case = src[NASDAQ]['case']; diffs = []
    for t in on_case['trades']:
        ref = lookup.get((NASDAQ, t['position_id']))
        if ref:
            diffs.append(abs(abs(t['open_price'] - t['sl']) * 1.0 - ref['unit_risk']))
    assert diffs and max(diffs) < 1e-6, ('geometry unit risk differs from reference rows', max(diffs))
    off_case = json.loads((DIOFF / 'results.json').read_text(encoding='utf-8-sig'))
    assert off_case['inputs'].get('InpRequireDIAgreement') == 'false'
    off_src = dict(row=dict(src[NASDAQ]['row']), case=off_case, folder=DIOFF)
    off_lookup = {(NASDAQ, t['position_id']): dict(unit_risk=abs(t['open_price'] - t['sl']) * 1.0) for t in off_case['trades']}
    streams = {}
    for name, nas_src, nas_lookup in (('DI_OFF', off_src, off_lookup), ('DI_ON', src[NASDAQ], lookup)):
        cands = []
        for slug in pr.SLUGS:
            if slug == NASDAQ:
                cands += pr.candidates(nas_src, nas_lookup, slug, begin, end)
            else:
                cands += pr.candidates(src[slug], lookup, slug, begin, end)
        streams[name] = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=['2021-10-07', '2026-10-06'])
        (R / f'INPUTS-{name}.json').write_text(json.dumps(streams[name], separators=(',', ':')), encoding='utf-8')
    info = dict(geometry_parity_max_abs_diff=max(diffs), geometry_parity_trades=len(diffs), dioff_source=str(DIOFF / 'results.json'),
                dioff_sha256=sha(DIOFF / 'results.json'), dioff_history_quality=off_case['native'].get('history_quality'),
                per_stream={k: dict(Counter(c['ea'] for c in v['candidates'])) for k, v in streams.items()}, source_hashes=hashes)
    (R / 'SOURCES.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    print(json.dumps({k: info[k] for k in ('geometry_parity_max_abs_diff', 'geometry_parity_trades', 'per_stream')}, indent=1))


def freeze():
    files = [Path(__file__), R / 'INPUTS-DI_OFF.json', R / 'INPUTS-DI_ON.json', R / 'SOURCES.json', OLDER / 'prepare.py', DIAL / 'run.py', FASTER / 'core_engine.py', FASTER / 'PLAN.json', PACKAGE]
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def per_trial(t):
    both = t['total_elapsed_to_both']['inclusive_prague_days'] if t['total_elapsed_to_both'] else None
    acc = t.get('access_5bd_illustration_epoch')
    fund = None if not acc else (datetime.fromtimestamp(acc, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1
    p1 = t['phase1']['elapsed_to_terminal']['inclusive_prague_days'] if t['phase1']['status'] == 'passed' else None
    return dict(both=both, funded=fund, p1=p1, breach=t['outcome'].startswith('failed'), trades=len(t['trades']),
                eqdd=t['max_sampled_equity_drawdown_cash'], day=t['max_daily_sampled_equity_loss'], buffer=t['counts'].get('soft_total_buffer9200', 0) > 0)


def q(arr, p):
    s = sorted(arr); return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))] if s else None


def summarize(rows):
    n = len(rows); passed = [r for r in rows if r['both'] and not r['breach']]
    sh = lambda f: round(sum(1 for r in rows if f(r)) / n, 4)  # noqa: E731
    return dict(n=n, pass_both_180=sh(lambda r: r['both'] and not r['breach']), funded_90=sh(lambda r: r['funded'] and r['funded'] <= 90 and not r['breach']),
                funded_60=sh(lambda r: r['funded'] and r['funded'] <= 60 and not r['breach']), phase1_60=sh(lambda r: r['p1'] and r['p1'] <= 60),
                breach=sh(lambda r: r['breach']), stalled_buffer=sh(lambda r: r['buffer']),
                median_days_both=statistics.median([r['both'] for r in passed]) if passed else None,
                median_days_funded=statistics.median([r['funded'] for r in passed]) if passed else None,
                p25_funded=q([r['funded'] for r in passed], .25) if passed else None, p75_funded=q([r['funded'] for r in passed], .75) if passed else None,
                eqdd_p50=round(q([r['eqdd'] for r in rows], .5), 1), eqdd_p95=round(q([r['eqdd'] for r in rows], .95), 1), eqdd_max=round(max(r['eqdd'] for r in rows), 1),
                day_p95=round(q([r['day'] for r in rows], .95), 1), day_max=round(max(r['day'] for r in rows), 1), median_trades=statistics.median(r['trades'] for r in rows))


def splan_for(window):
    e = D.e; p = copy.deepcopy(e.read(FASTER / 'PLAN.json'))
    p['history'] = dict(p['history'], start_prague=window[0], end_exclusive_prague=window[1]); return p


def oos_starts():
    out, x = [], OOS[0]
    while x < OOS[1]:
        if x.weekday() < 5 and x + timedelta(days=180) <= OOS[1]:
            out.append(dict(date=x.isoformat(), epoch=midnight(x), horizon_date=(x + timedelta(days=180)).isoformat(), horizon_epoch=midnight(x + timedelta(days=180))))
        x += timedelta(days=1)
    return out


def bootstrap_events(pool, mondays, index, rng, start_day, priority):
    rows = []
    for k in range(BLOCKS):
        src = mondays[rng.randrange(len(mondays))]; tgt = start_day + timedelta(days=BLOCK_DAYS * k); shift = (tgt - src).days * 86400
        lo, hi = index[src]
        for c in pool[lo:hi]:
            rows.append(dict(c, id=f"{c['id']}#{k}", op=c['op'] + shift, cl=None if c['cl'] is None else c['cl'] + shift, marks=[(m[0] + shift, m[1]) for m in c['marks']]))
    horizon = midnight(start_day + timedelta(days=180)); ev = []
    for r in rows:
        ev.append((r['op'], 3, priority[r['ea']], r['id'], r, None))
        if r['cl'] is not None and r['cl'] < horizon:
            ev.append((r['cl'], 4 if r['cl'] == r['op'] else 1, priority[r['ea']], r['id'], r, None))
        for m in r['marks']:
            ev.append((m[0], 2, priority[r['ea']], r['id'], r, m))
    x = start_day
    while x < start_day + timedelta(days=180):
        ev.append((midnight(x), 0, -1, '', None, None)); x += timedelta(days=1)
    ev.sort(key=lambda z: z[:4]); return [z for z in ev if z[0] < horizon]


def continuous(plan, events, cost):
    """Funded-style continuous run over the OOS window: no phase targets, same guard, 1% cap."""
    e = D.e

    class Continuous(D.DialTrial):
        def maybe_pass(self, t): return

        def reject_reason(self, row, t, risk, margin):
            m = self.cap_now / 50
            if self.failed: return 'permanent_hard_failure'
            if self.day_stopped: return 'daily_300_latch'
            if self.daily_entries >= 7: return 'daily_7_entry_limit'
            if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
            total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
            if total + risk > 225 * m + 1e-7: return 'aggregate_initial_risk225'
            if same + risk > 150 * m + 1e-7: return 'same_symbol_initial_risk150'
            reserve = sum(1.25 * p['risk'] + 5 for p in self.active.values())
            projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5
            if projected < 9200 - 1e-8: return 'soft_total_buffer9200'
            if self.anchor - projected > 300 + 1e-8: return 'soft_daily_reserve300'
            existing = sum(p['margin'] for p in self.active.values())
            if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
            if t < self.last_entry + 3: return 'entry_reconciliation3s'
            return None

    start = dict(date=OOS[0].isoformat(), epoch=midnight(OOS[0]), horizon_date=OOS[1].isoformat(), horizon_epoch=midnight(OOS[1]))
    epochs = [x[0] for x in events]
    w = events[bisect.bisect_left(epochs, start['epoch']):bisect.bisect_left(epochs, start['horizon_epoch'])]
    m = Continuous(plan, D.BASKET, start, cost, 'next_prague_midnight', [(-1e9, CAP)])
    for t, kind, pr_, key, row, mark in w:
        if kind == 0: m.day_reset(t)
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
    res = m.result()
    trades = res['trades']; nets = [x['net'] for x in trades]
    gp, gl = sum(v for v in nets if v > 0), -sum(v for v in nets if v < 0)
    months = defaultdict(float); by_ea = defaultdict(lambda: [0, 0.0])
    for x in trades:
        months[datetime.fromtimestamp(x['cl'], Z).strftime('%Y-%m')] += x['net']; by_ea[x['ea']][0] += 1; by_ea[x['ea']][1] += x['net']
    days = (OOS[1] - OOS[0]).days; weekdays = sum(1 for i in range(days) if (OOS[0] + timedelta(days=i)).weekday() < 5)
    bal, peak, cdd = 10000.0, 10000.0, 0.0
    for v in nets:
        bal += v; peak = max(peak, bal); cdd = max(cdd, peak - bal)
    return dict(cost=cost, trades=len(nets), per_month=round(len(nets) / (days / 30.4375), 2), per_day=round(len(nets) / weekdays, 3),
                net=round(sum(nets), 2), return_pct=round(sum(nets) / 100, 2), pf=round(gp / gl, 3) if gl else None, win_rate=round(100 * sum(v > 0 for v in nets) / len(nets), 1) if nets else None,
                max_closed_dd=round(cdd, 2), max_sampled_equity_dd=round(res['max_sampled_equity_drawdown_cash'], 2), worst_day=round(res['max_daily_sampled_equity_loss'], 2),
                breached=res['outcome'].startswith('failed'), ending_balance=round(res['ending_balance'], 2),
                positive_months=f"{sum(v > 0 for v in months.values())}/{len(months)}", months={k: round(v, 2) for k, v in sorted(months.items())},
                by_ea={k: dict(trades=v[0], net=round(v[1], 2)) for k, v in sorted(by_ea.items(), key=lambda kv: -kv[1][1])},
                blocked=dict(Counter({k: v for k, v in res['counts'].items() if k.startswith(('daily_', 'aggregate', 'same_', 'soft_', 'proxy', 'entry_', 'minimum'))})))


def run():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    D.e.verify_freeze(); out = dict(oos={}, bootstrap={}, continuous={}); began = time.time()
    for name in ('DI_OFF', 'DI_ON'):
        data = json.loads((R / f'INPUTS-{name}.json').read_text(encoding='utf-8'))
        plan = splan_for(data['window']); events = D.e.master_events(plan, data); epochs = [x[0] for x in events]
        # A. OOS phase replay
        for sc in plan['scenarios']:
            rows = []
            for s in oos_starts():
                w = events[bisect.bisect_left(epochs, s['epoch']):bisect.bisect_left(epochs, s['horizon_epoch'])]
                rows.append(per_trial(D.replay(plan, s, sc['cost'], sc['handover'], w, [(-1e9, CAP)])))
            out['oos'][f"{name}|{sc['cost']}|{sc['handover']}"] = summarize(rows)
            print('OOS', name, sc, json.dumps(out['oos'][f"{name}|{sc['cost']}|{sc['handover']}"]), f'{time.time() - began:.0f}s', flush=True)
        # C. continuous OOS performance
        for cost in ('recorded_exness', 'fixed_cost_stress'):
            out['continuous'][f'{name}|{cost}'] = continuous(plan, events, cost)
            c = out['continuous'][f'{name}|{cost}']
            print('CONT', name, cost, {k: c[k] for k in ('trades', 'return_pct', 'pf', 'win_rate', 'max_sampled_equity_dd', 'positive_months')}, flush=True)
        # B. Monte Carlo block bootstrap over the 5-year pool
        priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
        pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
        mondays, m = [], date(2021, 10, 11)
        while m + timedelta(days=BLOCK_DAYS) <= date(2026, 10, 6):
            mondays.append(m); m += timedelta(days=7)
        index = {m: (bisect.bisect_left(ops, midnight(m)), bisect.bisect_left(ops, midnight(m + timedelta(days=BLOCK_DAYS)))) for m in mondays}
        rng = random.Random(SEED); start_day = date(2030, 1, 7)
        start = dict(date=start_day.isoformat(), epoch=midnight(start_day), horizon_date=(start_day + timedelta(days=180)).isoformat(), horizon_epoch=midnight(start_day + timedelta(days=180)))
        rows = {c: [] for c in ('recorded_exness', 'fixed_cost_stress')}
        for i in range(PATHS):
            ev = bootstrap_events(pool, mondays, index, rng, start_day, priority)
            for c in rows:
                rows[c].append(per_trial(D.replay(plan, start, c, 'next_prague_midnight', ev, [(-1e9, CAP)])))
            if i % 500 == 0:
                print('MC', name, i, f'{time.time() - began:.0f}s', flush=True)
        for c, v in rows.items():
            out['bootstrap'][f'{name}|{c}'] = summarize(v)
            print('MC', name, c, json.dumps(out['bootstrap'][f'{name}|{c}']), flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(dict(seconds=round(time.time() - began), cap=CAP, paths=PATHS, seed=SEED, oos_window=[str(OOS[0]), str(OOS[1])], **out), indent=1), encoding='utf-8')
    print('done', round(time.time() - began), 's')


D = load('dial', DIAL / 'run.py'); D.BASKET = 'CORE4_PLUS_FIVE_ORBS_05R'

if __name__ == '__main__':
    {'prepare': prepare, 'freeze': freeze, 'run': run}[sys.argv[1]]()
