"""Independent saved-ledger, selection, cash and Monte Carlo audit."""
from pathlib import Path
from datetime import datetime, timedelta
from html.parser import HTMLParser
from collections import Counter
import hashlib, importlib.util, json, math, statistics

ROOT = Path(__file__).resolve().parent
DAY = 86400

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-7), (a, b)

class HTMLAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.counts = Counter()
    def handle_starttag(self, tag, attrs):
        self.counts[tag] += 1
        if tag not in {'meta', 'link', 'br', 'hr', 'input', 'img', 'source', 'wbr'}:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag, tag

def main():
    d = read(ROOT/'Results.json')
    profile = read(ROOT/'PORTFOLIO.json')
    n = d['paths_per_case']
    syn = datetime.fromisoformat(d['synthetic_start']).timestamp()
    assert n == 1000 and len(d['random_cases']) == 15
    assert len(d['historical']) == 3 and len(d['individual']) == 4
    wanted = {'us100-h1-orb-13utc', 'xau-orb-new-york-m30',
              'xau-orb-london-ny-overlap-m30', 'us100-selective-orb-v3'}
    assert {x['slug'] for x in profile['entries']} == wanted
    assert profile['live_installation'] is False
    assert profile['risk_per_trade_usd'] == 50 and profile['capital_usd'] == 10000
    assert profile['only_opening_range_strategies'] and profile['no_non_orb_eas']
    assert len(d['selection_audit']) == 16
    for x in d['individual']:
        for m in (x['native'], x['ftmo_proxy']):
            assert m['win_rate'] >= 60 and m['pf'] is not None and math.isfinite(m['pf']) and m['pf'] >= 1.15
        assert x['rr'] == (2.0 if x['slug'] == 'us100-selective-orb-v3' else .5)
    for p, h in d['sources'].items():
        assert sha(p) == h, p

    baseline = read(ROOT.parent/'FTMO ORB RR05 Portfolio Simulation 2026-10-08/Results.json')
    prior = next(x for x in baseline['historical'] if x['name'] == 'baseline')
    actual = next(x for x in d['historical'] if x['name'] == 'current_ftmo_14')
    assert actual['portfolio'] == prior['portfolio']
    for x in d['historical']:
        m = x['portfolio']
        profit = m['return_pct'] * 100
        close(sum(z['net'] for z in m['months'].values()), profit)
        close(sum(z['net'] for z in m['contributions'].values()), profit)
        assert sum(z['trades'] for z in m['months'].values()) == m['trades']
        assert sum(z['trades'] for z in m['contributions'].values()) == m['trades']
        close(m['balance_curve'][-1][1] - 10000, profit)
        assert m['cash_reconciled'] and m['open_at_end'] == 0
        assert all(z['trading_days'] >= 4 for z in x['challenge']['passes'])
        if x['name'] != 'current_ftmo_14':
            assert set(m['contributions']) <= wanted
            expect = 119 if x['ea_count'] == 4 else 114
            assert m['trades'] == expect

    checked = 0
    funnels = 0
    for c in d['random_cases']:
        suffix = '-stress' if c['stress'] else '-cooldown' if c['cooldown'] else ''
        paths = read(ROOT/('PATHS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'-'+c['portfolio']+suffix+'.json'))
        assert len(paths) == n
        checked += n
        draws = read(ROOT/('DRAWS-'+str(c['seed'])+'-'+str(c['block_weeks'])+'.json'))
        assert len(draws['draws']) == n and draws['horizon_days'] == 730
        for r in paths:
            assert len(r['passes']) <= 2
            assert all(z['trading_days'] >= 4 for z in r['passes'])
            assert [z['phase'] for z in r['passes']] == list(range(1, len(r['passes'])+1))
            if r['funded_at']:
                assert len(r['passes']) == 2
                assert datetime.fromisoformat(r['funded_at']) > datetime.fromisoformat(r['passes'][1]['time'])
            if r['receipt_at']:
                assert r['funded_at'] and r['request_at']
                assert datetime.fromisoformat(r['receipt_at']) > datetime.fromisoformat(r['request_at']) > datetime.fromisoformat(r['funded_at'])
        for z in c['summary']:
            cut = syn + z['days'] * DAY
            before = lambda v: v is not None and datetime.fromisoformat(v).timestamp() < cut
            p1 = sum(bool(r['passes']) and before(r['passes'][0]['time']) for r in paths)
            both = sum(len(r['passes']) == 2 and before(r['passes'][1]['time']) for r in paths)
            funded = sum(before(r['funded_at']) for r in paths)
            paid = sum(before(r['receipt_at']) for r in paths)
            assert paid <= funded <= both <= p1 <= n
            for count, key in ((p1, 'phase1_pass_pct'), (both, 'both_pass_pct'),
                               (funded, 'funded_pct'), (paid, 'first_reward_received_pct')):
                close(count*100/n, z[key])
            times = [(datetime.fromisoformat(r['passes'][1]['time']).timestamp()-syn)/DAY
                     for r in paths if len(r['passes']) == 2 and before(r['passes'][1]['time'])]
            assert len(times) == z['days_to_pass_both']['n']
            if times:
                close(statistics.mean(times), z['days_to_pass_both']['mean'])
                close(statistics.median(times), z['days_to_pass_both']['median'])
            reward = statistics.mean(r['reward'] if before(r['receipt_at']) else 0 for r in paths)
            close(reward, z['expected_first_reward_usd'])
            for fee in z['expected_net_cash_and_fee_roi']:
                net = reward + paid/n*fee['fee_usd'] - fee['fee_usd']
                close(net, fee['expected_net_cash'])
                close(net/fee['fee_usd']*100, fee['expected_fee_roi_pct'])
            funnels += 1
    assert checked == 15000 and funnels == 60

    end = datetime.fromisoformat(d['window_through']).date() + timedelta(days=1)
    assert len(d['starts']) == 201
    for x in d['starts']:
        start = datetime.fromisoformat(x['start']).date()
        assert start.weekday() == 0 and start + timedelta(days=x['horizon_days']) <= end
        assert datetime.fromisoformat(x['end_exclusive']).date() == start + timedelta(days=x['horizon_days'])
    plan = read(ROOT.parent/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json')
    prod = {p: h for x in plan['setups'] for p, h in x['production_hashes'].items()}
    for p, h in prod.items():
        assert sha(p) == h, p

    spec = importlib.util.spec_from_file_location('pure_orb_run', ROOT/'run.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    engine_checks = mod.s.tests()
    ns = mod.s.engine(cooldown=True)
    t = mod.START
    row = dict(key='a', symbol='USTEC', news=False, op=t+100, cl=t+500,
               unit_risk=1000., unit_gross=100., unit_comm=-.7, unit_swap=0.,
               open_price=25000., close_price=25100., side='Long')
    r = ns['replay']([row, dict(row, key='b', op=t+101)], [], t, t+DAY, challenge=False, detail=True)
    assert r['trades'] == 1 and r['counts']['entry_reconciliation_cooldown'] == 1
    assert all(z['initial_risk'] <= 50 for z in r['log'])
    skipped = ns['replay']([dict(row, unit_risk=6000.)], [], t, t+DAY, challenge=False)
    assert skipped['trades'] == 0 and skipped['counts']['min_lot_over_budget'] == 1

    parser = HTMLAudit()
    parser.feed((ROOT/'Results.html').read_text(encoding='utf-8'))
    assert not parser.stack and parser.counts['table'] == 12 and parser.counts['svg'] == 1
    out = dict(random_path_records_checked=checked, probability_funnels_checked=funnels,
               historical_portfolios_checked=3, historical_start_windows_checked=201,
               sources_unchanged=True, production_files_unchanged=len(prod),
               selection_and_only_orb_membership_checked=True, benchmark_matches_prior=True,
               fee_roi_checked=True, engine_checks=engine_checks,
               initial_stop_budget_min_lot_and_cooldown_checked=True,
               html_balanced=True, report_tables=parser.counts['table'], no_live_changes=True)
    (ROOT/'VERIFICATION.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out))

if __name__ == '__main__':
    main()
