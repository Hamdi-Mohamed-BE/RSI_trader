"""Offline verification of native Nasdaq results, including historical carryovers."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'Market Style Bots Raw 2026-09-29'


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, allow_nan=False,
        default=lambda x: x.item() if isinstance(x, np.generic) else str(x)), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(epoch):
    return pd.to_datetime(int(epoch), unit='s', utc=True).isoformat()


def streaks(p):
    w = l = maxw = maxl = 0
    for x in p:
        w, l = (w + 1, 0) if x > 0 else (0, l + 1) if x < 0 else (0, 0)
        maxw, maxl = max(w, maxw), max(l, maxl)
    return maxw, maxl


def main():
    spec = importlib.util.spec_from_file_location('signal_oracle', SOURCE / 'verify_signals.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    build = json.loads((ROOT / 'BUILD.json').read_text())
    assert all(sha(ROOT / k) == v == sha(SOURCE / k) for k, v in build.items())
    bars = pd.read_csv(SOURCE / 'data/USTEC-H1.csv.gz').set_index('time')
    bar_times = pd.to_datetime(bars.index, unit='s', utc=True)
    evidence = {}
    results, carryovers, verified = [], [], []
    ledgers = {}
    for window, model in [('6m', 4), ('1y', 4), ('3y', 1), ('5y', 1), ('3y', 4), ('5y', 4)]:
        for control in [False, True]:
            tag = f"nasdaq-trend-{'control' if control else 'raw'}-{window}-m{model}"
            fresh = window in ['3y', '5y'] and model == 4
            out = (ROOT if fresh else SOURCE) / 'native' / tag
            r = json.loads((out / 'run.json').read_text())
            assert r['build'] == build
            attempt = r['attempt']
            archived = out / f'report-attempt{attempt}.htm.gz'
            assert hashlib.sha256(gzip.decompress(archived.read_bytes())).hexdigest() == r['report_sha']
            d = pd.read_csv(out / 'trades.csv.gz').sort_values(['open_epoch', 'position_id'])
            signals = pd.read_csv(out / 'signals.csv.gz')
            trace = pd.read_csv(out / 'trace.csv.gz')
            assert trace.time.is_monotonic_increasing and trace.time.is_unique
            p = d.net_profit.to_numpy()
            m = r['metrics']
            assert len(d) == len(signals) == m['trades']
            assert d.position_id.is_unique and signals.position_id.is_unique
            assert np.allclose(d.volume, d.closed_volume, atol=1e-8)
            assert np.allclose(d.net_profit, d[['gross_profit', 'commission', 'swap', 'fee']].sum(axis=1), atol=.011)
            assert abs(sum(p) - m['net_profit']) < .02
            assert abs(10000 + sum(p) - m['final_balance']) < .02
            assert (d.actual_risk > 0).all()
            assert (d.side * (d.open_price - d.initial_sl) > 0).all()
            assert (d.side * (d.initial_tp - d.open_price) > 0).all()
            assert (d.open_epoch % 3600 < 301).all()
            assert not (d.open_epoch // 86400).duplicated().any()
            assert (d.open_epoch.to_numpy()[1:] >= d.close_epoch.to_numpy()[:-1]).all()
            previous_balance = 10000 + np.r_[0, np.cumsum(p)[:-1]]
            assert np.allclose(d.requested_risk, .01 * previous_balance, atol=.011)
            journal = gzip.decompress((out / f'journal-attempt{attempt}.txt.gz').read_bytes()).decode()
            assert 'testing with execution delay 150 milliseconds' in journal
            assert 'demo=1' in journal and 'Exness-MT5Trial16' in journal
            assert not re.search('position closed due end of test', journal)
            start = pd.Timestamp(r['start'].replace('.', '-'), tz='UTC')
            end = pd.Timestamp(r['end'].replace('.', '-'), tz='UTC')
            assert (d.open_epoch >= start.timestamp()).all() and (d.close_epoch < end.timestamp()).all()
            eligible = (bar_times >= start) & (bar_times < end) & (bar_times.hour >= 7) & (bar_times.hour <= 16) & (bar_times.dayofweek < 5)
            days = len(set(bar_times[eligible].date))
            months = (end - start).days / 30.4375
            equity = np.r_[10000, 10000 + np.cumsum(p)]
            peak = np.maximum.accumulate(equity)
            w, l = streaks(p)
            m.update(trades_per_month=len(d) / months, trades_per_eligible_day=len(d) / days,
                eligible_days=days, win_streak=w, loss_streak=l,
                balance_dd_pct=float(100 * np.max((peak - equity) / peak)),
                median_initial_risk_pct=float(np.median(d.actual_risk / previous_balance * 100)),
                max_initial_risk_pct=float(np.max(d.actual_risk / previous_balance * 100)),
                max_hold_hours=float(((d.close_epoch - d.open_epoch) / 3600).max()))
            checks = 0
            for s in signals.itertuples():
                i = bars.index.get_indexer([int(s.signal_time)])[0]
                assert i >= 399, 'Missing signal warmup'
                v = oracle.oracle(bars.iloc[i-399:i+1], 0)
                assert v['side'] == s.raw_side
                assert np.isclose(v['atr'], s.atr, rtol=1e-8, atol=1e-8)
                expected = 1 if oracle.hash32(int(s.fill_time)//86400 + 290929) & 1 else -1
                assert s.actual_side == (expected if control else s.raw_side)
                assert 3600 <= s.fill_time - s.signal_time < 3901
                checks += 1
            verified.append(dict(tag=tag, signals=checks, fresh=fresh))
            for row in d.itertuples():
                deadline = min(int(row.open_epoch) + 8*3600, int(row.open_epoch)//86400*86400 + 20*3600)
                if row.close_epoch <= deadline + 120 and row.close_epoch//86400 == row.open_epoch//86400:
                    continue
                before = trace[trace.time < deadline].iloc[-1]
                after = trace[trace.time >= deadline].iloc[0]
                carryovers.append(dict(tag=tag, position_id=int(row.position_id),
                    open_utc=stamp(row.open_epoch), close_utc=stamp(row.close_epoch),
                    hours_held=(row.close_epoch-row.open_epoch)/3600,
                    nominal_deadline_utc=stamp(deadline),
                    last_minute_trace_before_deadline=stamp(before.time),
                    first_minute_trace_at_or_after_deadline=stamp(after.time),
                    minute_trace_gap_hours=(after.time-before.time)/3600,
                    close_minus_first_trace_seconds=int(row.close_epoch-after.time),
                    net_profit=row.net_profit, swap=row.swap,
                    crossed_utc_date=bool(row.close_epoch//86400 > row.open_epoch//86400)))
            r.update(evidence_root=str(out), fresh_run=fresh, metrics=m,
                costs={k:float(d[k].sum()) for k in ['gross_profit','commission','swap','fee','net_profit']})
            results.append(r)
            ledgers[tag] = d
            for f in [out/'run.json', archived, out/'trades.csv.gz', out/'signals.csv.gz', out/'trace.csv.gz', out/f'journal-attempt{attempt}.txt.gz']:
                evidence[str(f)] = sha(f)
    matched, failures = [], []
    for r in results:
        if r['control']:
            continue
        c = next(x for x in results if x['tag'] == r['tag'].replace('-raw-', '-control-'))
        a, b = ledgers[r['tag']].copy(), ledgers[c['tag']].copy()
        a['date'], b['date'] = a.open_epoch//86400, b.open_epoch//86400
        pair = a.merge(b, on='date', suffixes=('_raw','_control'), validate='1:1')
        assert len(pair) == len(a) == len(b), 'Control opportunities differ'
        delta = pair.net_profit_raw/pair.actual_risk_raw - pair.net_profit_control/pair.actual_risk_control
        matched.append(dict(raw_tag=r['tag'], trades=len(pair), all_dates_matched=True,
            max_entry_seconds=float(abs(pair.open_epoch_raw-pair.open_epoch_control).max()),
            mean_net_R_delta=float(delta.mean())))
        if r['window'] in ['3y', '5y'] and r['model'] == 4:
            m = r['metrics']
            w = r['window']
            if m['net_profit'] <= 0: failures.append(w + ': net profit <= 0')
            if m['profit_factor'] < 1.15: failures.append(w + ': PF < 1.15')
            if m['trades'] < 30: failures.append(w + ': fewer than 30 positions')
            if m['mean_net_R'] <= c['metrics']['mean_net_R']: failures.append(w + ': mean net R does not beat control')
            if any(r['flags'].values()): failures.append(w + ': unresolved raw execution/carry flags')
            if any(c['flags'].values()): failures.append(w + ': unresolved control execution/carry flags')
    save('RESULTS.json', dict(runs=results, matched_controls=matched))
    save('CARRYOVER_AUDIT.json', dict(positions=carryovers,
        note='Minute OnTick trace gaps establish missing recorded tester activity across deadlines, not the exact historical holiday cause or a possible unrecorded live fill. Deadlines here use 8h/20UTC; the broker session rule can require an earlier exit. Overlapping windows repeat some positions. No rows removed from performance.'))
    save('GATE.json', dict(status='RAW_GATE_REJECTED' if failures else 'RAW_GATE_PASSED',
        failures=failures, fresh_native_runs=4, reused_native_runs=8, parameter_variants_tested=0,
        optimization_run=False, monte_carlo_run=False, production_changed=False, gold_changed=False))
    save('VERIFICATION.json', dict(passed=True, runs=verified,
        signal_checks=sum(x['signals'] for x in verified),
        fresh_signal_checks=sum(x['signals'] for x in verified if x['fresh']),
        source_h1_sha256=sha(SOURCE / 'data/USTEC-H1.csv.gz'),
        independent_oracle_sha256=sha(SOURCE / 'verify_signals.py'), evidence=evidence,
        note='Evidence integrity pass, not strategy acceptance. Complete deal costs, balances, source/report hashes, risk sizing, entry timing, causal signal logic, control dates and closed volume checked.'))
    print(json.dumps(dict(failures=failures, fresh_rows=[dict(tag=r['tag'],metrics=r['metrics'],flags=r['flags']) for r in results if r['fresh_run']],
        carryovers_five_year=[x for x in carryovers if x['tag']=='nasdaq-trend-raw-5y-m4']), indent=2))


if __name__ == '__main__':
    main()
