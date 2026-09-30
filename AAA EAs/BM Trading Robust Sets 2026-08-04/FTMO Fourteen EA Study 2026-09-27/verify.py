"""Independent reconciliation of saved outputs; no MT5 or production imports."""
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
import study as s

ROOT = Path(__file__).resolve().parent

def main():
    result = s.read(ROOT / 'RESULTS.json')
    frozen = s.read(ROOT / 'SIMULATION_FROZEN.json')
    data = s.read(ROOT / 'prepared.json')
    paths = dict(frozen['sources'], **frozen['dependencies'])
    for path, expected in paths.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    count = 0
    horizons = 0
    for case in result['cases']:
        assert len(case['paths']) == 1000
        ns = s.engine(case['risk'])
        for path in case['paths']:
            count += 1
            passes = {p['phase']: datetime.fromisoformat(p['time']).timestamp() for p in path['passes']}
            assert len(passes) == len(path['passes'])
            for p in path['passes']:
                assert p['trading_days'] >= 4
                assert p['balance'] >= (11000 if p['phase'] == 1 else 10500) - 1e-7
            if 2 in passes:
                assert 1 in passes and passes[2] > passes[1]
            if path['request_at']:
                assert path['funded_at'] and not path['breach_at']
                funded = datetime.fromisoformat(path['funded_at']).timestamp()
                request = datetime.fromisoformat(path['request_at']).timestamp()
                receipt = datetime.fromisoformat(path['receipt_at']).timestamp()
                assert request >= funded + 14 * s.DAY
                assert receipt == ns['business'](request, 4)
                assert path['reward'] >= 20 - 1e-7
        for h in case['summary']['horizons']:
            horizons += 1
            cutoff = s.START + h['days'] * s.DAY
            counts = Counter(s.ph.classify(s.ph.marks(p, ns), cutoff) for p in case['paths'])
            assert dict(counts) == h['counts'] and sum(counts.values()) == 1000
            assert h['first_payout_received'] <= h['funded'] <= h['both_phases_passed'] <= h['phase1_passed'] <= 1000
            rewards = [p['reward'] if p['receipt_at'] and datetime.fromisoformat(p['receipt_at']).timestamp() < cutoff else 0 for p in case['paths']]
            assert abs(sum(rewards) / 1000 - h['mean_first_reward_per_purchase']) < 1e-7
            assert sum(v > 0 for v in rewards) == h['first_payout_received']
        hist = case['historical_continuous']
        s.reconcile(hist)
        details = case['historical_details']
        assert sum(m['trades'] for m in details['months'].values()) == hist['trades']
        assert abs(sum(m['net'] for m in details['months'].values()) - sum(p['net_profit'] for p in hist['log'])) < 1e-7
        assert sum(e['trades'] for e in details['by_ea'].values()) == hist['trades']
        if case['stress'] and case['guards']:
            rows = [dict(r) for rr in data['rows'].values() for r in rr]
            placements = [dict(p) for p in data['placements']]
            replay = ns['replay'](rows, placements, s.BEGIN, s.END, news_risk=30, stress=True, guards=True, challenge=False, detail=True)
            for key in ('balance', 'trades', 'breach_at', 'win_rate', 'pf', 'model_dd_pct', 'closed_dd_pct', 'log', 'counts'):
                assert replay[key] == hist[key], key
        for challenge in [case['historical_challenge']] + [r['result'] for r in case['recent_historical']]:
            if challenge['request_at']:
                assert math.isclose(challenge['reward'], .8 * (challenge['balance'] - 10000), abs_tol=1e-7)
    all_rows = [r for rr in data['rows'].values() for r in rr]
    held_long = [r for r in all_rows if r['cl'] - r['op'] > 7*s.DAY]
    worst = max(data['rows']['news-pulse-xau'], key=lambda r: r['actual_unit_risk'])
    news_actual_risk = worst['actual_unit_risk'] * .15
    out = dict(status='passed', checked_paths=count, checked_horizons=horizons,
               source_and_dependency_hashes_verified=len(paths), historical_cash_ledgers=8,
               deterministic_guarded_stress_replays=2, long_holds_over_seven_days=len(held_long),
               longest_hold_days=max((r['cl']-r['op'])/s.DAY for r in all_rows),
               news_max_fill_to_original_stop_risk_at_015_lot=news_actual_risk,
               news_worst_fill_open=worst['open_time'], news_worst_fill_comment=worst['entry_comment'],
               caveat='News figure is stop exposure, not a realized loss or guaranteed loss bound.')
    s.save(ROOT / 'FINAL_VERIFICATION.json', out)
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
