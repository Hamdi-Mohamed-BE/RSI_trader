"""Owner 2026-11-19: "if I bought this account by October start, show me a breakdown day by day till today". Same method as Best 1-Step Last Month 2026-11-18/study.py. Best 1-Step BEST1STEP-20261118, no-guard package EX5s + package inputs
(no-opposite OFF, news block OFF), each EA alone, $10k, InpPortfolioPercent 1.0 (InpRiskPercent 0.5 calibration), Model 4 real ticks, 150 ms,
2026-10-18 -> tester data end (2026-11-17 23:59 UTC). Positions still open at the end are closed by the tester at the last price ("end of test").
Combined view = R per trade (net / $100 = 1% of $10k), Nasdaq 5M x0.75 as installed, then $ on one $100k account at 0.75% and 0.5%.
Not applied: guard limits, weekend / holiday flat helper, news guard, no-opposite rule (single-EA tester runs).
python study.py run | report"""
import gzip, importlib.util, json, os, shutil, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent; PKG = B / '_00 Live profiles/Packages/Best1Step'
START, END = '2026.10.01', '2026.11.20'   # the tester stops at its last complete day (2026-11-18 23:59 UTC)
TF = {5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
FACTOR = {'nasdaq-5m-candle-momentum': 0.75}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def entries(): return json.loads((PKG / 'Package.json').read_text(encoding='utf-8-sig'))['entries']


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; dest = b.TESTER / 'MQL5/Experts/CalyxB1October'; dest.mkdir(parents=True, exist_ok=True)
    for e in entries():
        name = e['key']; final = H / 'native' / f'nw-{name}'
        if (final / 'trades.json.gz').exists(): continue
        fn = f'{name}.ex5'; shutil.copy2(PKG / e['expert'], dest / fn)
        inp = dict(e['inputs'], InpPortfolioPercent='1.0', InpCalyxNoOpposite='false', InpCalyxNewsBlock='false')
        b.CONFIG.update(model=4, end_date=END, periods={'m': START}, deposit=10000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                        timeout_seconds=7200, period=TF[int(e['period'])], expert_dir='CalyxB1October', expert_file=fn, controls={}, common_inputs={}, variants={name: {'label': name, 'inputs': inp}})
        try: b.run_case(e['canonical'], name, 'm')
        except SystemExit as x: print('run_case exit', x)
        src = H / 'native' / f"nw-{e['canonical']}-{name}-m"
        if src.exists(): shutil.move(str(src), str(final))
        print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


def pf(w, l): return round(w / -l, 2) if l < 0 else None


def report():
    rows, per = [], {}
    for e in entries():
        p = H / 'native' / f"nw-{e['key']}" / 'trades.json.gz'
        T = json.loads(gzip.open(p).read()) if p.exists() else None
        if T is None: per[e['key']] = None; continue
        f = FACTOR.get(e['key'], 1.0); R = [t['net_profit'] / 100.0 * f for t in T]
        w = sum(x for x in R if x > 0); l = sum(x for x in R if x < 0)
        per[e['key']] = dict(label=e['label'], symbol=e['canonical'], trades=len(T), wins=sum(x > 0 for x in R), win_rate=round(100 * sum(x > 0 for x in R) / len(T), 1) if T else None,
                             total_r=round(sum(R), 2), pf=pf(w, l), net_usd_10k_1pct=round(sum(t['net_profit'] for t in T), 2), factor=f,
                             open_at_end=sum(1 for t in T if 'end' in str(t.get('comment', '')).lower() or t.get('close_reason') == 'end_of_test'))
        for t, r in zip(T, R): rows.append((t['close_time'][:19], e['key'], r, t['open_time'][:19]))
    rows.sort(); n = len(rows); R = [r[2] for r in rows]
    eq, peak, dd = 0.0, 0.0, 0.0
    for r in R: eq += r; peak = max(peak, eq); dd = max(dd, peak - eq)
    days = defaultdict(float)
    for c, k, r, o in rows: days[c[:10]] += r
    first = datetime.strptime(START, '%Y.%m.%d'); last = datetime(2026, 11, 18); span = (last - first).days
    w = sum(x for x in R if x > 0); l = sum(x for x in R if x < 0)
    tot = dict(trades=n, trades_per_month=round(n / span * 30.4375, 1), trades_per_day=round(n / span, 2), wins=sum(x > 0 for x in R),
               win_rate=round(100 * sum(x > 0 for x in R) / n, 1) if n else None, total_r=round(sum(R), 2), pf=pf(w, l), closed_dd_r=round(dd, 2),
               best_day=max(days.items(), key=lambda x: x[1]) if days else None, worst_day=min(days.items(), key=lambda x: x[1]) if days else None,
               usd_100k_075=round(sum(R) * 750, 0), usd_100k_050=round(sum(R) * 500, 0), dd_usd_100k_075=round(dd * 750, 0),
               best_day_share_pct=round(100 * max(days.values()) / sum(R), 1) if days and sum(R) > 0 else None)
    out = dict(window=[START, 'tester data end 2026-11-17 23:59 UTC'], per_ea=per, combined=tot, daily_r={k: round(v, 2) for k, v in sorted(days.items())},
               equity_r=[(c, round(sum(R[:i + 1]), 2)) for i, (c, *_ ) in enumerate(rows)])
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(dict(per_ea=per, combined=tot), indent=1))


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
