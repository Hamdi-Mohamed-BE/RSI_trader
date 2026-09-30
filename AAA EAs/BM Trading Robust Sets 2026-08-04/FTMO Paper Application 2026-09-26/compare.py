"""Offline, matched $10K FTMO scenarios; no terminal, orders or production imports."""
from __future__ import annotations
import ast
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'FTMO Combination Study 2026-09-19'
DAY = 86400
WEEK = 7 * DAY
UTC = timezone.utc
END = datetime(2026, 8, 31, tzinfo=UTC).timestamp()
START = datetime(2026, 9, 28, tzinfo=UTC).timestamp()
SPECS = {'XAUUSD': (100, 15), 'XAGUSD': (5000, 15), 'USTEC': (1, 15),
         'USDJPY': (100000, 30), 'EURUSD': (100000, 30), 'BTCUSD': (1, 1), 'ETHUSD': (10, 1)}
RAW = 'gold-overnight-value-area/standard'
NEWS = ['news-pulse-xau/standard', 'news-pulse-xag/standard']
TOP5 = ['xau-squeeze-momentum-standard/standard', 'usdjpy-london-open-momentum/standard',
        'xau-trend-progression/standard', 'us100-orb-new-york-m30/standard',
        'xau-elliott-wave-1-2-3/standard']
TOP8 = ['usdjpy-london-open-momentum/standard', 'xau-trend-progression/standard',
        'xau-squeeze-momentum-standard/standard', 'us100-selective-orb-v3/standard',
        'orb-volume-profile/safe', 'eth-top-down-fvg-liquidity/safe',
        'xau-elliott-wave-1-2-3/standard', 'us100-orb-new-york-m30/standard']
CONFIGS = [dict(name=name, keys=keys, risk=risk, news_risk=10.) for name, keys, risk in [
    ('Five EAs / $50', TOP5, 50.), ('Five EAs / $71.43', TOP5, 500/7),
    ('Eight EAs / $50', TOP8, 50.), ('Eight EAs / $71.43', TOP8, 500/7),
    ('Eight EAs / $100', TOP8, 100.), ('Raw Gold / $71.43', [RAW], 500/7),
    ('Raw Gold + news / $71.43 + $10', [RAW] + NEWS, 500/7),
    ('High-win + news / $71.43 + $10',
     [RAW, 'xau-rsi-vwap/standard', 'nasdaq-overnight/standard'] + NEWS, 500/7)]]
HASHES = {'prepared.json': '6953e7cc61a4b8697cced13a76a3318ebfb0d323763c2296d120337652638416',
          'prepare.py': '6a8fcfbea8e321cfff2de14763ba27038780f7e1374ba7709942c08b59f1e60f',
          'simulate.py': '1d24d67617483ec4aed546f361087aaf93fcbc71d7fa2b6f50bb91e430d1d7a9'}

def iso(t):
    return datetime.fromtimestamp(t, UTC).isoformat() if t is not None else None

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def save(p, v):
    p.write_text(json.dumps(v, indent=2, allow_nan=False), encoding='utf-8')

def engine(legacy=False):
    """Load ONLY reviewed function definitions; never import prepare's website app."""
    ns = dict(math=math, Counter=Counter, defaultdict=defaultdict, datetime=datetime,
              timedelta=timedelta, timezone=timezone, PRAGUE=ZoneInfo('Europe/Prague'),
              NY=ZoneInfo('America/New_York'), CAPITAL=10000., RISK=500/7,
              SPECS=SPECS, DAY=DAY, WEEK=WEEK, iso=iso)
    for filename, names in [('prepare.py', {'costs'}),
                            ('simulate.py', {'business', 'rounded', 'margin', 'entry_charge', 'replay'})]:
        source = (SOURCE / filename).read_text(encoding='utf-8-sig')
        if filename == 'simulate.py' and not legacy:
            old = 'if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:'
            assert source.count(old) == 1
            # No arbitrary 30-day evaluation failure: reporting horizons are not FTMO deadlines.
            source = source.replace(old, 'if False:')
        tree = ast.parse(source)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in nodes} == names
        exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), ns)
    return ns

def verify_sources():
    actual = {name: hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in HASHES}
    assert actual == HASHES, (actual, HASHES)
    return actual

def sample_rows(data, keys, pool_start, weeks, sample, start, end):
    """Joint weekly blocks, same draws for all EAs; preserve NY wall-clock timing."""
    rr, pp = [], []
    ny = ZoneInfo('America/New_York')
    for i, j in enumerate(sample):
        src = pool_start + j*WEEK
        target = start + i*WEEK
        so = datetime.fromtimestamp(src + 2*DAY + 43200, ny).utcoffset().total_seconds()
        to = datetime.fromtimestamp(target + 2*DAY + 43200, ny).utcoffset().total_seconds()
        offset = target - src + so - to
        for key in keys:
            for r in weeks[key][j]:
                if start <= r['op']+offset < end:
                    rr.append(dict(r, op=r['op']+offset, cl=r['cl']+offset,
                                   event=r.get('event', 0)+offset))
        for p in weeks['placements'][j]:
            if p['key'] in keys and start <= p['op']+offset < end:
                pp.append(dict(p, op=p['op']+offset, until=p['until']+offset, epoch=p['epoch']+offset))
    return rr, pp

def pool(data, start, n):
    out = {key: [[] for _ in range(n)] for key in data['rows']}
    out['placements'] = [[] for _ in range(n)]
    for key, rows in data['rows'].items():
        for r in rows:
            j = int((r['op']-start)//WEEK)
            if 0 <= j < n and r['cl'] < END:
                out[key][j].append(r)
    for p in data['placements']:
        j = int((p['op']-start)//WEEK)
        if 0 <= j < n:
            out['placements'][j].append(p)
    return out

def wilson(k, n):
    z = 1.96
    p = k/n
    den = 1+z*z/n
    mid = (p+z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [100*(mid-half), 100*(mid+half)]

def summarize(rows, horizon):
    n = len(rows)
    received = [r['reward'] if r['payout'] else 0. for r in rows]
    paid = [r for r in rows if r['payout']]
    p = len(paid)/n
    funded_days = [(datetime.fromisoformat(r['funded_at']).timestamp()-START)/DAY for r in rows if r['funded']]
    fees = [r for r in rows if r['breach']]
    return dict(paths=n, horizon_days=horizon,
                funded_pct=100*sum(r['funded'] for r in rows)/n, payout_pct=100*p,
                payout_mc_interval=wilson(len(paid), n), breach_pct=100*len(fees)/n,
                unfinished_pct=100*sum(not r['payout'] and not r['breach'] for r in rows)/n,
                median_days_to_fund_if_funded=statistics.median(funded_days) if funded_days else None,
                median_first_reward_if_paid=statistics.median(r['reward'] for r in paid) if paid else None,
                mean_first_reward_per_purchase=statistics.mean(received),
                illustrative_net_cash_at_100_fee=statistics.mean(received)-100*(1-p),
                illustrative_fee_lost_on_breaches=100*len(fees)/n,
                illustrative_fee_still_unrecovered=100*sum(not r['payout'] and not r['breach'] for r in rows)/n,
                breakeven_fee_by_horizon=statistics.mean(received)/(1-p) if p<1 else None,
                median_trades=statistics.median(r['trades'] for r in rows),
                p95_stop_envelope_dd_pct=sorted(r['model_dd_pct'] for r in rows)[int(.95*(n-1))],
                max_stop_envelope_dd_pct=max(r['model_dd_pct'] for r in rows),
                max_daily_model_loss=max(r['worst_daily_usd'] for r in rows),
                mean_skipped_margin=statistics.mean(sum(v for k,v in r['counts'].items() if 'margin' in k) for r in rows))

def tests(data):
    ns = engine()
    assert ns['rounded'](500/7/1000) == .08
    assert abs(ns['margin']('XAUUSD', .01, 3000)-200)<1e-9
    assert ns['business'](datetime(2026,9,25,tzinfo=UTC).timestamp(), 2) == datetime(2026,9,29,tzinfo=UTC).timestamp()
    assert datetime(2026,7,1,tzinfo=ns['PRAGUE']).utcoffset().total_seconds()==7200
    assert datetime(2026,1,1,tzinfo=ns['PRAGUE']).utcoffset().total_seconds()==3600
    empty = ns['replay']([], [], START, START+180*DAY)
    assert not empty['inactive'] and not empty['breach'] and not empty['payout']
    assert engine(True)['replay']([], [], START, START+180*DAY)['inactive']
    # Check exact parity to the previously saved historical raw+news stress study.
    old = read(SOURCE/'results.json')
    cell = next(x for x in old['results'] if x['plan']['name']=='Raw + XAU/XAG news, $10/order' and x['months']==4)
    start = datetime.fromisoformat(cell['start']).timestamp()
    keys = [RAW]+NEWS
    rr = [dict(r) for k in keys for r in data['rows'][k] if start<=r['op']<END]
    pp = [dict(p) for p in data['placements'] if p['key'] in keys and start<=p['op']<END]
    got = engine(True)['replay'](rr, pp, start, END, stress=True, detail=True)
    want = cell['cases']['stress']['historical']
    for key in ('trades','funded_at','receipt_at','payout','breach','win_rate','model_dd_pct','reward'):
        assert got[key] == want[key], (key, got[key], want[key])
    # Re-run original 9 engine unit tests in an isolated module facade.
    import types
    import unittest
    module = types.ModuleType('simulate')
    module.__dict__.update(engine())
    test_source = (SOURCE/'test_simulate.py').read_text(encoding='utf-8-sig')
    sys.modules['simulate'] = module
    facade = types.ModuleType('prepare')
    facade.costs = module.costs
    facade.DAY = DAY
    sys.modules['prepare'] = facade
    test_namespace = {'__name__': 'original_tests'}
    exec(compile(test_source.replace("if __name__=='__main__':", "if False:"), 'original_tests', 'exec'), test_namespace)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_namespace['Checks'])
    checked = unittest.TextTestRunner(verbosity=1).run(suite)
    assert checked.wasSuccessful()
    return {'source_hashes': verify_sources(), 'new_checks': 7, 'historical_parity_fields': 8,
            'legacy_tests_passed': checked.testsRun}

def main(paths=1000):
    verify_sources()
    data = read(SOURCE/'prepared.json')
    ns = engine()
    # Freeze all choices before obtaining results.
    save(ROOT/'FROZEN.json', dict(configs=CONFIGS, paths=paths, seed=20260926,
                                synthetic_start=iso(START), horizons=[30,60,120,180]))
    checks = tests(data)
    save(ROOT/'CHECKS.json', checks)
    results = []
    for pool_name, pool_start, n in [('recent26', datetime(2026,3,2,tzinfo=UTC).timestamp(), 26),
                                    ('long101', datetime(2024,9,23,tzinfo=UTC).timestamp(), 101)]:
        assert pool_start+n*WEEK == END
        weeks = pool(data, pool_start, n)
        rng = random.Random(20260926)
        samples = [[rng.randrange(n) for _ in range(26)] for _ in range(paths)]
        for config in CONFIGS:
            if pool_name=='long101' and any(k in NEWS for k in config['keys']):
                continue  # No invented news history for the missing year.
            ns['RISK'] = config['risk']
            for stressed in (False, True):
                cases = {d: [] for d in (30,60,120,180)}
                for sample in samples:
                    for d in cases:
                        rr, pp = sample_rows(data, config['keys'], pool_start, weeks,
                                             sample[:math.ceil(d/7)], START, START+d*DAY)
                        result = ns['replay'](rr, pp, START, START+d*DAY, news_risk=10., stress=stressed)
                        cases[d].append(result)
                # Matching historical 180-day continuous account: actual chronology, not resampled.
                hs = END-180*DAY
                rr = [dict(r) for k in config['keys'] for r in data['rows'][k] if hs<=r['op']<END and r['cl']<END]
                pp = [dict(p) for p in data['placements'] if p['key'] in config['keys'] and hs<=p['op']<END]
                hist = ns['replay'](rr, pp, hs, END, news_risk=10., stress=stressed, challenge=False, detail=True)
                historical_challenge = ns['replay'](rr, pp, hs, END, news_risk=10., stress=stressed, detail=True)
                rec = dict(pool=pool_name, pool_start=iso(pool_start), pool_end=iso(END), source_weeks=n,
                           config=config, stress=stressed,
                           source_entries=sum(len(r) for k in config['keys'] for r in weeks[k]),
                           outcomes=[summarize(cases[d], d) for d in cases],
                           historical_continuous=hist, historical_challenge=historical_challenge)
                results.append(rec)
                save(ROOT/'RESULTS.json', dict(results=results, checks=checks, paths=paths))
                print(pool_name, config['name'], 'stress' if stressed else 'reference',
                      'paid', [round(x['payout_pct'],1) for x in rec['outcomes']], flush=True)
    print('COMPLETE', len(results), 'scenarios', flush=True)

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv)>1 else 1000)
