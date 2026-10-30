"""Best Prop 15 backtest (owner 2026-10-29): the built Best Prop 15 package (Best Prop 9 + EMA3, 3 Way Gold, Gold Overnight, DMC Current
XAU, DMC Fresh Reaction XAU, DMC Fresh Reaction US100) vs Best Prop 9, in-sample and out-of-sample. Python replay, no MT5 terminal.

Engine: the frozen Best Prop retest engine (FTMO Dial Study trial = the Best Prop guard on $10k: $100 per entry, $450 total open,
$300 per symbol, $300 daily reserve/latch, $9,200 entry buffer, 7 entries / 3 losses a day, lots down), used unchanged.
Signals (five-year native Model-4 runs, 2021-10-07 -> 2026-10-06, older ticks generated):
  * the nine Best Prop EAs = retest INPUTS-DI_OFF (Nasdaq DI OFF, the package default);
  * EMA3, 3 Way Gold (three module lanes, partials collapsed, no intratrade marks), Gold Overnight, DMC Current XAU, DMC Fresh Reaction US100
    = Portfolio Prop Comparison INPUTS-FTMO17 (the FTMO launcher presets = the BP15 SETs);
  * DMC Fresh Reaction XAU = the long-history full-eas native run of preset 21 (the BP15 SET source), built with the same candidate builder.
Split (shared data_split.py): development / validation / OOS = last two years. OOS is PREVIOUSLY VIEWED, not pristine: every EA and
setting was chosen after this history existed, and 3 Way Gold was optimised on 2021-2026 (its untouched holdout was 2019-2021).
Parity: the Best Prop 9 rows must reproduce the retest RESULTS.json exactly (OOS challenge, continuous OOS, Monte Carlo).

python bp15.py prepare | run
"""
import bisect, hashlib, importlib.util, json, random, sys, time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
RETEST = B / 'Best Prop Portfolio Retest 2026-10-20'; COMPARE = B / 'Portfolio Prop Comparison 2026-10-22'
OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'; PACKAGE = B / '_00 Live profiles' / 'Best Prop 15 Portfolio 2026-10-29' / 'PACKAGE.json'
ADDED_FTMO17 = ('ema3', 'gold-overnight-value-area', 'dmc-current-xau', 'dmc-fresh-reaction-us100')
FRESH_XAU = 'dmc-fresh-reaction-xau'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


RT = load('retest', RETEST / 'retest.py'); D = RT.D
DS = load('data_split', B.parent / 'Calyx Research Pipeline' / 'data_split.py')
SPLIT = DS.research_split('2021-10-07', '2026-10-06')
SEG = {k: (date.fromisoformat(SPLIT[n]['start']), date.fromisoformat(SPLIT[n]['end_exclusive']))
       for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
SEG['all'] = (date(2021, 10, 7), date(2026, 10, 6))


def prepare():
    pr = load('pr', OLDER / 'prepare.py')
    base = json.loads((RETEST / 'INPUTS-DI_OFF.json').read_text(encoding='utf-8'))
    ftmo = json.loads((COMPARE / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    assert base['window'] == ftmo['window'] == ['2021-10-07', '2026-10-06']
    added = [c for c in ftmo['candidates'] if c['ea'] in ADDED_FTMO17 or c['ea'].startswith('3-way-gold#')]
    # DMC Fresh Reaction XAU from the long-history full-eas run (preset 21 = the BP15 SET source)
    long_dir = pr.LONG; plan = pr.read(long_dir / 'PLAN.json'); state = pr.read(long_dir / 'RUN_STATUS.json'); rows = pr.read(long_dir / 'RISK_ROWS.json')
    cid = plan['mappings']['full-eas'][FRESH_XAU]; case_row = next(x for x in plan['cases'] if x['case_id'] == cid); receipt = state['complete'][cid]
    assert Path(case_row['preset']).name == '21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set'
    for file, digest in case_row['production_hashes'].items():
        assert sha(file) == digest, ('production source changed', file)
    path = Path(receipt['path']); assert sha(path) == receipt['sha256']
    src = dict(row=case_row, case=pr.read(path), folder=path.parent)
    lookup = {(x['key'], x['position_id']): x for x in rows['full-eas']}
    fresh = pr.candidates(src, lookup, FRESH_XAU, base['year_begin_epoch'], base['year_end_exclusive_epoch'])
    # the package roster must be exactly these streams
    pkg = json.loads(PACKAGE.read_text(encoding='utf-8')); slugs = {e['slug'] for e in pkg['entries']}
    have = {c['ea'].split('#')[0] for c in base['candidates'] + added + fresh}
    assert have == slugs and len(slugs) == 15, (sorted(have ^ slugs))
    data = dict(base, candidates=base['candidates'] + added + fresh)
    (R / 'INPUTS-BP15.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    info = dict(per_ea=dict(Counter(c['ea'] for c in data['candidates'])), fresh_xau_case=cid, fresh_xau_sha256=receipt['sha256'],
                fresh_xau_history_quality=src['case'].get('native', {}).get('history_quality'),
                sources={'INPUTS-DI_OFF': sha(RETEST / 'INPUTS-DI_OFF.json'), 'INPUTS-FTMO17': sha(COMPARE / 'INPUTS-FTMO17.json')},
                package_sha256=sha(PACKAGE), split={k: [str(a), str(b)] for k, (a, b) in SEG.items()})
    (R / 'SOURCES.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    print(json.dumps(info['per_ea'], indent=1), len(data['candidates']))


def setup(name):
    data = json.loads(((RETEST / 'INPUTS-DI_OFF.json') if name == 'BP9' else (R / 'INPUTS-BP15.json')).read_text(encoding='utf-8'))
    plan = RT.splan_for(data['window'])
    eas = sorted({c['ea'] for c in data['candidates']})
    plan['baskets']['BP15'] = sorted(set(plan['baskets'][RT.D.BASKET if name == 'BP9' else 'CORE4_PLUS_FIVE_ORBS_05R']) | set(eas))
    plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
    events = D.e.master_events(plan, data)
    return data, plan, events


def starts(a, b):
    out, x = [], a
    while x < b:
        if x.weekday() < 5 and x + timedelta(days=180) <= b:
            out.append(dict(date=x.isoformat(), epoch=RT.midnight(x), horizon_date=(x + timedelta(days=180)).isoformat(), horizon_epoch=RT.midnight(x + timedelta(days=180))))
        x += timedelta(days=1)
    return out


def run():
    began = time.time(); out = dict(split={k: [str(a), str(b)] for k, (a, b) in SEG.items()}, challenge={}, continuous={}, bootstrap={})
    for name, basket in (('BP9', 'CORE4_PLUS_FIVE_ORBS_05R'), ('BP15', 'BP15')):
        data, plan, events = setup(name); epochs = [x[0] for x in events]; D.BASKET = basket
        # A. FTMO 2-step challenge from every weekday start (180-day horizon) inside each segment
        for seg in ('dev', 'val', 'oos', 'all'):
            for cost in ('recorded_exness', 'fixed_cost_stress'):
                rows = []
                for s in starts(*SEG[seg]):
                    w = events[bisect.bisect_left(epochs, s['epoch']):bisect.bisect_left(epochs, s['horizon_epoch'])]
                    rows.append(RT.per_trial(D.replay(plan, s, cost, 'next_prague_midnight', w, [(-1e9, RT.CAP)])))
                out['challenge'][f'{name}|{seg}|{cost}'] = RT.summarize(rows) if rows else None
                print('CH', name, seg, cost, json.dumps(out['challenge'][f'{name}|{seg}|{cost}']), f'{time.time() - began:.0f}s', flush=True)
        # B. continuous funded-style run: fresh $10k at each segment start, no targets, same guard
        for seg in ('dev', 'val', 'oos', 'all'):
            for cost in ('recorded_exness', 'fixed_cost_stress'):
                RT.OOS = SEG[seg]
                out['continuous'][f'{name}|{seg}|{cost}'] = c = RT.continuous(plan, events, cost)
                print('CONT', name, seg, cost, {k: c[k] for k in ('trades', 'return_pct', 'pf', 'win_rate', 'max_closed_dd', 'max_sampled_equity_dd', 'positive_months')}, flush=True)
        RT.OOS = (date(2024, 10, 6), date(2026, 10, 6))
        # C. Monte Carlo block bootstrap over the whole five-year pool (identical procedure / seed to the retest)
        priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
        pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
        mondays, m = [], date(2021, 10, 11)
        while m + timedelta(days=RT.BLOCK_DAYS) <= date(2026, 10, 6):
            mondays.append(m); m += timedelta(days=7)
        index = {m: (bisect.bisect_left(ops, RT.midnight(m)), bisect.bisect_left(ops, RT.midnight(m + timedelta(days=RT.BLOCK_DAYS)))) for m in mondays}
        rng = random.Random(RT.SEED); start_day = date(2030, 1, 7)
        start = dict(date=start_day.isoformat(), epoch=RT.midnight(start_day), horizon_date=(start_day + timedelta(days=180)).isoformat(),
                     horizon_epoch=RT.midnight(start_day + timedelta(days=180)))
        rows = {c: [] for c in ('recorded_exness', 'fixed_cost_stress')}
        for i in range(RT.PATHS):
            ev = RT.bootstrap_events(pool, mondays, index, rng, start_day, priority)
            for c in rows:
                rows[c].append(RT.per_trial(D.replay(plan, start, c, 'next_prague_midnight', ev, [(-1e9, RT.CAP)])))
            if i % 500 == 0: print('MC', name, i, f'{time.time() - began:.0f}s', flush=True)
        for c, v in rows.items():
            out['bootstrap'][f'{name}|{c}'] = RT.summarize(v); print('MC', name, c, json.dumps(out['bootstrap'][f'{name}|{c}']), flush=True)
    # parity with the frozen retest (Best Prop 9)
    ref = json.loads((RETEST / 'RESULTS.json').read_text(encoding='utf-8'))
    par = dict(oos_challenge=out['challenge']['BP9|oos|recorded_exness'] == ref['oos']['DI_OFF|recorded_exness|next_prague_midnight'],
               continuous_oos=out['continuous']['BP9|oos|recorded_exness'] == ref['continuous']['DI_OFF|recorded_exness'],
               monte_carlo=out['bootstrap']['BP9|recorded_exness'] == ref['bootstrap']['DI_OFF|recorded_exness'])
    out['parity_vs_retest'] = par; print('PARITY', par, flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(dict(seconds=round(time.time() - began), **out), indent=1), encoding='utf-8')
    print('done', round(time.time() - began), 's')


if __name__ == '__main__' and sys.argv[1] in ('prepare', 'run'):
    {'prepare': prepare, 'run': run}[sys.argv[1]]()


def diag():
    """DIAGNOSTIC (not the package): continuous runs with the guard's static 92% entry buffer removed, so a loss early in a window does
    not freeze the account for the rest of it. Everything else (caps, daily reserve, 7/3 per day, lots down) is the frozen engine."""
    import inspect
    src = inspect.getsource(RT.continuous).replace('def continuous(', 'def continuous_nobuffer(', 1)
    line = "            if projected < 9200 - 1e-8: return 'soft_total_buffer9200'\n"
    assert src.count(line) == 1
    exec(compile(src.replace(line, ''), 'continuous_nobuffer', 'exec'), RT.__dict__)
    res = json.loads((R / 'RESULTS.json').read_text(encoding='utf-8')); res['continuous_nobuffer_diagnostic'] = {}
    for name, basket in (('BP9', 'CORE4_PLUS_FIVE_ORBS_05R'), ('BP15', 'BP15')):
        data, plan, events = setup(name); D.BASKET = basket
        for seg in ('dev', 'val', 'oos', 'all'):
            for cost in ('recorded_exness', 'fixed_cost_stress'):
                RT.OOS = SEG[seg]
                res['continuous_nobuffer_diagnostic'][f'{name}|{seg}|{cost}'] = c = RT.continuous_nobuffer(plan, events, cost)
                print('NOBUF', name, seg, cost, {k: c[k] for k in ('trades', 'per_month', 'per_day', 'return_pct', 'pf', 'win_rate', 'max_closed_dd',
                                                                  'max_sampled_equity_dd', 'worst_day', 'positive_months', 'breached')}, flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(res, indent=1), encoding='utf-8')


if __name__ == '__main__' and sys.argv[1] == 'diag':
    diag()
