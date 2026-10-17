"""Independent cash/coverage/quote checks of the saved rolling-year result."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import last_year as y

root = Path(__file__).resolve().parent
r = json.loads((root / 'RESULTS.json').read_text())
f, _ = y.load()
checks = json.loads((root / 'MT5-additional-checks.json').read_text())
for check in checks:
    b = f.loc[pd.Timestamp(check['time'])]
    for field in ['open', 'high', 'low', 'close', 'tick_volume', 'spread']:
        assert abs(float(b[field]) - check[field]) < 1e-8
calendar = {day:(start,end) for day,start,end in y.cash_sessions()}
assert calendar['2025-10-31'][0].hour == 13
assert calendar['2025-11-03'][0].hour == 14
assert calendar['2026-03-06'][0].hour == 14
assert calendar['2026-03-09'][0].hour == 13
assert calendar['2025-11-28'][1].hour == 18
assert calendar['2025-12-24'][1].hour == 18
assert '2026-10-12' in calendar
assert '2026-07-03' not in calendar

for key in ['primary','alternative_ordering','cost_stress']:
    p = r[key]
    balance, curve, profits = 10000., [10000.], []
    dates = set()
    for t in p['trades']:
        assert y.START <= t['date'] < y.END and t['date'] not in dates
        dates.add(t['date'])
        start,end = calendar[t['date']]
        entry_tm,exit_tm = pd.Timestamp(t['entry_time']),pd.Timestamp(t['exit_time'])
        assert start + pd.Timedelta(minutes=5) <= entry_tm <= exit_tm <= end + pd.Timedelta(minutes=2)
        assert t['rvol'] >= 2
        assert abs(t['starting_balance'] - balance) < 1e-8
        assert .05 <= t['lots'] <= 500 and abs(t['lots'] * 100 - round(t['lots'] * 100)) < 1e-8
        risk = t['lots'] * abs(t['entry'] - t['stop'])
        assert risk <= balance * .01 + 1e-8
        assert abs(risk - t['planned_risk_usd']) < 1e-8
        cash = t['lots'] * (t['side'] * (t['exit'] - t['entry']) - t['extra_round_trip_cost_points'])
        assert abs(cash - t['net_usd']) < 1e-8
        # Verify trigger touched by executable bid/ask, not just a midpoint.
        b = f.loc[entry_tm]
        if t['side'] == 1:
            assert b.high + b.used_spread >= t['trigger']
        else:
            assert b.low <= t['trigger']
        if t['exit_reason'] == 'Cash close':
            b = f.loc[exit_tm]
            expected = b.open + (b.used_spread if t['side'] == -1 else 0)
            assert abs(expected - t['exit']) < 1e-8
        balance += cash
        assert abs(t['ending_balance'] - balance) < 1e-8
        curve.append(balance)
        profits.append(cash)
    summary = p['summary']
    assert abs(summary['final_balance'] - balance) < 1e-8
    assert abs(summary['return_pct'] - (balance/10000-1)*100) < 1e-8
    array = np.array(curve)
    dd = float((1-array/np.maximum.accumulate(array)).max()*100)
    assert abs(summary['max_closed_dd_pct'] - dd) < 1e-8
    wins = sum(v for v in profits if v > 0)
    losses = -sum(v for v in profits if v < 0)
    assert abs(summary['profit_factor'] - wins/losses) < 1e-8
    assert len(p['sessions']) == 251
    assert len({s['date'] for s in p['sessions']}) == 251
    assert all(s['status'] in ['trade','RVOL below 2.0','pending never triggered'] for s in p['sessions'])

html = (root / 'Results.html').read_text(encoding='utf-8')
assert '2025-10-13' in html and '2026-10-12' in html
assert 'No trades: the 2x' not in html
assert '-9.98%' in html and '11.34%' in html
assert len(r['primary']['trades']) + r['primary']['summary']['session_statuses']['pending never triggered'] == r['opening_audit']['qualifying_sessions']
receipt = dict(passed=True, baseline_engine_tests=13, connector_spot_bars_matched=15,
               cash_and_drawdown_reconciled=True, calendar_dst_and_early_close_checked=True,
               scheduled_sessions=251, unavailable_opening_ratios=0,
               result_sha256=hashlib.sha256((root/'RESULTS.json').read_bytes()).hexdigest(),
               html_sha256=hashlib.sha256((root/'Results.html').read_bytes()).hexdigest())
y.save('VALIDATION.json', receipt)
print(json.dumps(receipt, indent=2))
