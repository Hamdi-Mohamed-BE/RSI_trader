"""FTSE 100 three-setup pipeline orchestration (PLAN.md + Addendum 1). Isolated tester only.

python pipeline.py freeze | parity | search <s1|s2|s3> | combine | plateau | confirm | oos | mc | transfer
"""
import gzip, json, math, random, statistics, sys
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path
import numpy as np
import engine as en, runner as rn

R = Path(__file__).resolve().parent; B = R.parent; RAW = B / 'FTSE Three Setup Raw 2026-10-27'
DEV, VAL, OOS, FULL, RAW5 = ('2019-08-01', '2023-10-27'), ('2023-10-27', '2024-10-27'), ('2024-10-27', '2026-10-27'), ('2019-08-01', '2026-10-27'), ('2021-10-27', '2026-10-27')
TF = (30, 60, 240); RR = (0, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6); HOLDS = (8, 24, 48, 0); STOPS = (1, 1.5, 2, 2.5, 3)
RSI = {1: (30, 35, 40), 2: (35, 40, 45), 3: (35, 40, 45)}; RSI_KEY = {1: 'p3', 2: 'p2', 3: 'p5'}
MIN_TRADES, MIN_COMBO = 50, 80; RISK_PCT = 0.75


def only(k): return {**en.BASE, **{f's{j}_on': int(j == k) for j in (1, 2, 3)}}
def setk(c, k, **kw): return dict(c, **{f's{k}_{n}': v for n, v in kw.items()})
def g(c, k, n): return c[f's{k}_{n}']


def st_signal(c, k):
    if k == 1: return [setk(c, 1, tf=t, p1=a, p2=d, p3=r) for t in TF for a in (20, 40, 60) for d in (1.5, 2, 2.5) for r in RSI[1]]
    if k == 2: return [setk(c, 2, tf=t, p1=a, p2=r, p3=d) for t in TF for a in (10, 20, 40) for r in RSI[2] for d in (0, 1)]
    return [setk(c, 3, tf=t, p1=a, p4=d, p5=r) for t in TF for a in (50, 100, 200) for d in (1, 1.5, 2) for r in RSI[3]]
def st_signal2(c, k): return [setk(c, 3, p2=s, p3=m) for s in (3, 5, 10) for m in (20, 40, 60)] if k == 3 else [c]
def st_stop(c, k): return [setk(c, k, stop=s) for s in STOPS]
def st_exit(c, k): return [setk(c, k, tp=t, hold=h) for t in RR for h in HOLDS if not (t == 0 and h == 0 and g(c, k, 'tratr') == 0)]
def st_mgmt(c, k): return [setk(c, k, be=b, tratr=a, trstart=s) for b, a, s in ((0, 0, 0), (0.5, 0, 0), (1, 0, 0), (0, 1, 0.5), (0, 1, 1), (0, 2, 0.5), (0, 2, 1))
                           if not (g(c, k, 'tp') == 0 and g(c, k, 'hold') == 0 and a == 0)]
def st_dir(c, k): return [setk(c, k, dir=d) for d in (0, 1, 2)]
def st_sess(c, k): return [setk(c, k, sess=s) for s in (0, 1, 2)]
def st_filter(c, k): return [setk(c, k, adx=a, trend=t) for a, t in ((0, 0), (20, 0), (25, 0), (-20, 0), (-25, 0), (0, 1), (0, 2))]
STAGES = [('signal', st_signal), ('signal2', st_signal2), ('stop', st_stop), ('exit', st_exit), ('mgmt', st_mgmt), ('direction', st_dir), ('session', st_sess), ('filters', st_filter)]


def dedupe(cases): return list({rn.digest(c): c for c in cases}.values())
def slim(r): return {k: v for k, v in r.items() if k != 'trades'}
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def rank(records, n_min=MIN_TRADES, keep=3):
    ok = lambda r: r['metrics']['trades'] >= n_min  # noqa: E731
    elig = [r for r in records if ok(r) and r['metrics']['net'] > 0 and (r['metrics']['pf'] or 0) >= 1.05]
    top = sorted(elig, key=lambda r: (r['metrics']['ret_dd'], r['metrics']['pf'] or 0), reverse=True)[:keep]
    for r in top: r['carry'] = 'eligible'
    if len(top) < keep:
        rest = sorted([r for r in records if ok(r) and r not in top], key=lambda r: r['metrics']['pf'] or 0, reverse=True)[:keep - len(top)]
        for r in rest: r['carry'] = f'not profitable (best PF with >= {n_min} trades)'
        top += rest
    return top


def record_search(track, stage, recs):
    p = R / 'SEARCH RESULTS.json'; allr = read(p) if p.exists() else []
    keys = {(x['track'], x['stage'], rn.digest(x['parameters']), x['window'][0], x.get('symbol', 'UK100')) for x in allr}
    for r in recs:
        sym = r.get('symbol', 'UK100'); k = (track, stage, rn.digest(r['parameters']), r['start'], sym)
        if k not in keys:
            allr.append(dict(track=track, stage=stage, window=[r['start'], r['end']], model=r['model'], symbol=sym, parameters=r['parameters'], metrics=r['metrics'], clean=r['clean'],
                             daily_sharpe=daily_sharpe(r['trades'], r['start'], r['end'])))
    rn.save(p, allr)


def daily_rets(trades, start, end):
    d0 = datetime.fromisoformat(start); d1 = datetime.fromisoformat(end); pnl = {}
    for t in trades: k = t['close_time'][:10]; pnl[k] = pnl.get(k, 0) + t['net_profit']
    bal, out, d = 10000., [], d0
    while d < d1:
        k = d.date().isoformat()
        if d.weekday() < 5 or k in pnl: out.append(pnl.get(k, 0) / bal); bal += pnl.get(k, 0)
        d += timedelta(days=1)
    return np.array(out)


def daily_sharpe(trades, start, end):
    r = daily_rets(trades, start, end)
    return float(r.mean() / r.std() * math.sqrt(252)) if len(r) > 5 and r.std() > 0 else 0.0


def freeze():
    files = [R / 'PLAN.md', R / 'engine.py', R / 'runner.py', R / 'pipeline.py']
    rn.save(R / 'FROZEN.json', dict(frozen_at=datetime.now().isoformat(), split=dict(development=DEV, validation=VAL, oos=OOS), files={str(f): rn.sha(f) for f in files}))


def verify():
    for p, h_ in read(R / 'FROZEN.json')['files'].items(): assert rn.sha(Path(p)) == h_, f'changed after freeze: {p}'


def parity():
    """Base case vs raw ALL 5y (Addendum 2). Entries: (minute, setup, side, initial SL) vs the raw EA's own FTSE3_ENTRY journal lines
    (the raw report pairs overlapping positions FIFO, so its open times are not per-position). Exits: (close, volume) exact, net within $0.02."""
    import re
    from collections import Counter
    verify(); rec = rn.batch('parity-raw5y-m4', [en.BASE], *RAW5, model=4, optimize=False)[0]
    ref = json.loads(gzip.decompress((RAW / 'native' / 'nw-UK100-ALL-5y' / 'trades.json.gz').read_bytes()))
    j = gzip.decompress((RAW / 'native' / 'nw-UK100-ALL-5y' / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    lines = [s for s in j.split('\n===== ') if 'FTSE3_ENTRY' in s][:1]   # the same lines are logged in two journal files; use one
    ents = re.findall(r'(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s+FTSE3_ENTRY FTSE3 (S1|S2|S3L|S3S) (buy|sell) entry=[\d.]+ sl=([\d.]+)', '\n'.join(lines))
    raw_e = Counter((datetime.strptime(x[0], '%Y.%m.%d %H:%M:%S').isoformat()[:16], {'S1': 1, 'S2': 2, 'S3L': 3, 'S3S': 3}[x[1]], x[2], x[3]) for x in ents)
    eng_e = Counter((t['open_time'][:16], t['magic'] - 2710270, t['side'], f"{t['initial_sl']:.2f}") for t in rec['trades'])
    a = sorted((t['close_time'][:19], round(t['volume'], 2), t['net_profit']) for t in rec['trades'])
    b = sorted((datetime.fromisoformat(t['close_time']).isoformat()[:19], round(t['volume'], 2), t['net_profit']) for t in ref)
    exit_diff = sum(x[:2] != y[:2] or abs(x[2] - y[2]) > 0.02 for x, y in zip(a, b)) + abs(len(a) - len(b))
    entry_diff = sum((raw_e - eng_e).values()) + sum((eng_e - raw_e).values())
    out = dict(ALL=dict(engine_trades=len(a), raw_trades=len(b), raw_journal_entries=sum(raw_e.values()), entry_mismatches=entry_diff, exit_mismatches=exit_diff,
                        max_net_diff=round(max((abs(x[2] - y[2]) for x, y in zip(a, b)), default=0), 4), engine_net=round(sum(x[2] for x in a), 2), raw_net=round(sum(x[2] for x in b), 2)))
    out['ALL']['mismatches'] = entry_diff + exit_diff + int(abs(out['ALL']['engine_net'] - out['ALL']['raw_net']) > 0.05)
    print('PARITY', json.dumps(out), flush=True); rn.save(R / 'PARITY.json', out); assert out['ALL']['mismatches'] == 0, 'engine parity failed'


def search(track):
    verify(); assert read(R / 'PARITY.json')['ALL']['mismatches'] == 0, 'run parity first'
    k = int(track[1]); carry = [only(k)]; trail = []
    for stage, gen in STAGES:
        if stage == 'signal2' and k != 3: continue
        cases = dedupe([v for c in carry for v in gen(c, k)])
        recs = rn.batch(f'{track}-{stage}-dev-m1', cases, *DEV, model=1); record_search(track, stage, recs)
        top = rank(recs); carry = [t['parameters'] for t in top]
        trail.append(dict(stage=stage, tested=len(cases), top=[dict(parameters=t['parameters'], metrics=t['metrics'], carry=t['carry']) for t in top]))
        print('STAGE', track, stage, len(cases), [(round(t['metrics']['pf'] or 0, 2), t['metrics']['trades'], round(t['metrics']['return_pct'], 1), t['carry'][:8]) for t in top], flush=True)
    rn.save(R / f'SEARCH-{track}.json', trail)


def merge(parts):
    c = {**en.BASE, **{f's{j}_on': 0 for j in (1, 2, 3)}}
    for k, p in parts.items():
        if p is not None: c.update({f: v for f, v in p.items() if f.startswith(f's{k}_')})
    return c


def combine():
    verify(); finals = {k: [f['parameters'] for f in read(R / f'SEARCH-s{k}.json')[-1]['top']] for k in (1, 2, 3)}
    combos = []
    for pick in product(*[[None] + list(range(len(finals[k]))) for k in (1, 2, 3)]):
        if all(x is None for x in pick): continue
        combos.append(dict(pick=pick, case=merge({k: (finals[k][i] if i is not None else None) for k, i in zip((1, 2, 3), pick)})))
    cases = dedupe([x['case'] for x in combos])
    recs = rn.batch('combine-dev-m1', cases, *DEV, model=1); record_search('combo', 'combine', recs)
    top = rank(recs, MIN_COMBO)
    rn.save(R / 'COMBINE.json', dict(tested=len(cases), top=[dict(parameters=t['parameters'], metrics=t['metrics'], carry=t['carry'],
                                                                    enabled=[k for k in (1, 2, 3) if t['parameters'][f's{k}_on']]) for t in top]))
    print('COMBINE', len(cases), [([k for k in (1, 2, 3) if t['parameters'][f's{k}_on']], round(t['metrics']['pf'] or 0, 2), t['metrics']['trades'], round(t['metrics']['return_pct'], 1)) for t in top], flush=True)


def around(seq, v):
    i = min(range(len(seq)), key=lambda j: abs(seq[j] - v)); return [seq[j] for j in (i - 1, i + 1) if 0 <= j < len(seq)]


def neighbours(c):
    out = [c]
    for k in (1, 2, 3):
        if not c[f's{k}_on']: continue
        for n, grid in ((RSI_KEY[k], RSI[k]), ('stop', STOPS), ('tp', RR), ('hold', HOLDS)):
            for v in around(list(grid), g(c, k, n)):
                x = setk(c, k, **{n: v})
                if g(x, k, 'tp') == 0 and g(x, k, 'hold') == 0 and g(x, k, 'tratr') == 0: continue
                out.append(x)
    return dedupe(out)


def plateau():
    verify(); finals = read(R / 'COMBINE.json')['top']; out = []
    for i, f in enumerate(finals):
        cases = neighbours(f['parameters']); recs = rn.batch(f'plateau{i}-dev-m1', cases, *DEV, model=1); record_search('combo', f'plateau{i}', recs)
        nets = [r['metrics']['net'] for r in recs]; pfs = [r['metrics']['pf'] or 0 for r in recs]
        res = dict(final=i, parameters=f['parameters'], dev=f['metrics'], neighbours=len(recs), positive_share=round(sum(n > 0 for n in nets) / len(nets), 3), median_pf=round(statistics.median(pfs), 3))
        res['passed'] = res['positive_share'] >= 0.70 and res['median_pf'] >= 1.05 and f['carry'] == 'eligible'
        out.append(res); print('PLATEAU', json.dumps({k: v for k, v in res.items() if k != 'parameters'}), flush=True)
    rn.save(R / 'PLATEAU.json', out)


def confirm():
    verify(); finals = [p for p in read(R / 'PLATEAU.json') if p['passed']]; out = dict(finalists=len(finals))
    if not finals:
        out['verdict'] = 'REJECTED_AT_PLATEAU'
    else:
        cases = [f['parameters'] for f in finals]
        dev = rn.batch('confirm-dev-m4', cases, *DEV, model=4); val = rn.batch('confirm-val-m4', cases, *VAL, model=4)
        record_search('combo', 'confirm-dev-m4', dev); record_search('combo', 'confirm-val-m4', val)
        rows = [dict(parameters=c, dev=d['metrics'], val=v['metrics']) for c, d, v in zip(cases, dev, val)]
        ok = [r for r in rows if r['val']['trades'] >= 15 and r['val']['net'] > 0]; out.update(rows=rows)
        if not ok: out['verdict'] = 'REJECTED_AT_VALIDATION'
        else:
            pick = max(ok, key=lambda r: r['val']['pf'] or 0); out.update(verdict='SELECTED', selected=pick['parameters'])
    if out['verdict'] != 'SELECTED':                      # Addendum 1: diagnostic carry of the development rank-1 combination
        out['diagnostic'] = read(R / 'COMBINE.json')['top'][0]['parameters']
    rn.save(R / 'CONFIRM.json', out); print('CONFIRM', out['verdict'], flush=True)


def final_case():
    c = read(R / 'CONFIRM.json'); return (c['selected'], 'SELECTED') if c['verdict'] == 'SELECTED' else (c['diagnostic'], 'DIAGNOSTIC (' + c['verdict'] + ')')


def rob():
    import importlib.util
    s = importlib.util.spec_from_file_location('rob', B.parent / 'Calyx Research Pipeline' / 'robustness.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def oos():
    verify(); case, label = final_case()
    rec = rn.batch('oos-m4', [case], *OOS, model=4, optimize=False)[0]; record_search('combo', 'oos-m4', [rec])
    tr = rec['trades']; half = tr[len(tr) // 2:]; gp = sum(t['net_profit'] for t in half if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in half if t['net_profit'] < 0)
    dep = rob().dependence(tr); m = rec['metrics']
    gate = dict(net_positive=m['net'] > 0, pf=(m['pf'] or 0) >= 1.15, trades=m['trades'] >= 30, recent_half_pf=(gp / gl if gl else 9) > 1, best_day_trade=dep.get('verdict') == 'PASS')
    out = dict(label=label, parameters=case, metrics=m, recent_half_pf=round(gp / gl, 3) if gl else None, dependence=dep, gate=gate,
               passed=all(gate.values()) and label == 'SELECTED', note='retrospective OOS: 2024-10 -> 2026-10 was viewed in the raw study')
    rn.save(R / 'OOS.json', out); print('OOS', label, 'PASS' if out['passed'] else 'FAIL', json.dumps(m), json.dumps(gate), flush=True)


def r_units(trades):
    bal, out = 10000., []
    for t in sorted(trades, key=lambda x: x['close_epoch']):
        risk = RISK_PCT / 100 * bal; out.append(dict(t, R=t['net_profit'] / risk, stopdist=abs(t['open_price'] - t['initial_sl']))); bal += t['net_profit']
    return out


def mc():
    verify(); case, label = final_case()
    rec = rn.batch('full-m4', [case], *FULL, model=4, optimize=False)[0]; record_search('combo', 'full-m4', [rec])
    tr = r_units(rec['trades']); rs = np.array([t['R'] for t in tr]); rng = random.Random(20261027)
    by_day = {}
    for t in tr: by_day.setdefault(t['close_time'][:10], []).append(t['R'])
    d, d1 = datetime.fromisoformat(FULL[0]), datetime.fromisoformat(FULL[1]); days = []
    while d < d1:
        k = d.date().isoformat()
        if d.weekday() < 5 or k in by_day: days.append(by_day.get(k, []))
        d += timedelta(days=1)
    def dd(v):
        c = np.cumsum(v); return float(np.max(np.maximum.accumulate(np.concatenate([[0], c]))[1:] - c)) if len(v) else 0.0
    def streak(v):
        m = n = 0
        for x in v: n = n + 1 if x < 0 else 0; m = max(m, n)
        return m
    tot, dds, sts, wd = [], [], [], []
    for _ in range(10000):
        path = []
        while len(path) < 252:
            s = rng.randrange(len(days)); path += [days[(s + j) % len(days)] for j in range(5)]
        path = path[:252]; flat = [x for day in path for x in day]
        tot.append(sum(flat)); dds.append(dd(flat)); sts.append(streak(flat)); wd.append(min((sum(day) for day in path), default=0))
    q = lambda a, p: round(float(np.percentile(a, p)), 3)  # noqa: E731
    boot = dict(paths=10000, horizon_trading_days=252, block_days=5, source_trades=len(tr),
                year_R=dict(p05=q(tot, 5), p50=q(tot, 50), p95=q(tot, 95)), year_pct_at_075=dict(p05=q(tot, 5) * RISK_PCT, p50=q(tot, 50) * RISK_PCT, p95=q(tot, 95) * RISK_PCT),
                prob_losing_year=round(float(np.mean(np.array(tot) < 0)), 4), max_dd_R=dict(p50=q(dds, 50), p95=q(dds, 95), p99=q(dds, 99)),
                losing_streak=dict(p50=q(sts, 50), p95=q(sts, 95), p99=q(sts, 99)), worst_day_R=dict(p50=q(wd, 50), p05=q(wd, 5)))
    shuf = []
    for _ in range(10000):
        v = list(rs); rng.shuffle(v); shuf.append(dd(v))
    keep = [float(sum(x for x in rs if rng.random() >= 0.2)) for _ in range(1000)]
    cost = np.array([t['R'] - (1.0 / t['stopdist'] if t['stopdist'] > 0 else 0) for t in tr])   # 1 index point per trade, in R of that trade
    # DSR (Addendum 1): dev+val daily returns of a Model-4 run, N = all tested configurations, SR variance across development screens
    dv = rn.batch('devval-m4', [case], DEV[0], VAL[1], model=4, optimize=False)[0]; record_search('combo', 'devval-m4', [dv])
    r = daily_rets(dv['trades'], DEV[0], VAL[1]); sr = r.mean() / r.std() if r.std() > 0 else 0
    allr = read(R / 'SEARCH RESULTS.json'); screens = [x['daily_sharpe'] / math.sqrt(252) for x in allr if x['window'][0] == DEV[0] and x['model'] == 1]
    n_trials = len({rn.digest(x['parameters']) for x in allr if x['model'] == 1}); var = float(np.var(screens)) if len(screens) > 1 else 0
    from scipy.stats import norm, skew, kurtosis
    emax = math.sqrt(var) * ((1 - 0.5772) * norm.ppf(1 - 1 / n_trials) + 0.5772 * norm.ppf(1 - 1 / (n_trials * math.e))) if n_trials > 1 else 0
    sk, ku = float(skew(r)), float(kurtosis(r, fisher=False)); T = len(r)
    dsr = float(norm.cdf((sr - emax) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)))
    out = dict(label=label, parameters=case, full_period=rec['metrics'], full_period_trades=len(tr), mean_R=round(float(rs.mean()), 4), bootstrap=boot,
               reshuffle_max_dd_R=dict(p50=q(shuf, 50), p95=q(shuf, 95), p99=q(shuf, 99), actual=round(dd(list(rs)), 3)),
               random_removal_20pct_total_R=dict(p05=q(keep, 5), p50=q(keep, 50), share_positive=round(float(np.mean(np.array(keep) > 0)), 3)),
               cost_stress_1pt=dict(total_R=round(float(cost.sum()), 2), mean_R=round(float(cost.mean()), 4), base_total_R=round(float(rs.sum()), 2)),
               deflated_sharpe=dict(daily_sr=round(float(sr), 5), annual_sr=round(float(sr * math.sqrt(252)), 3), n_trials=n_trials, sr_var_daily=var, expected_max_sr_daily=round(emax, 5), dsr=round(dsr, 4),
                                    devval=dv['metrics']))
    rn.save(R / 'MC.json', out); print('MC', label, json.dumps({k: v for k, v in out.items() if k not in ('parameters',)}, default=str)[:3000], flush=True)


def transfer():
    verify(); case, label = final_case(); out = dict(label=label, parameters=case, note='never-tested instruments for these rules: genuinely unseen transfer evidence')
    for sym in ('DE30', 'US500'):
        rec = rn.batch(f'transfer-{sym}-5y-m4', [case], *RAW5, model=4, optimize=False, symbol=sym)[0]; rec['symbol'] = sym; record_search('combo', f'transfer-{sym}', [rec])
        out[sym] = rec['metrics']; print('TRANSFER', sym, json.dumps(rec['metrics']), flush=True)
    rn.save(R / 'TRANSFER.json', out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    with rn.lease():
        if cmd == 'freeze': freeze()
        elif cmd == 'search': search(sys.argv[2])
        else: dict(parity=parity, combine=combine, plateau=plateau, confirm=confirm, oos=oos, mc=mc, transfer=transfer)[cmd]()
