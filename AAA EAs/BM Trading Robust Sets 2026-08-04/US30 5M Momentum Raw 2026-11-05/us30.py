"""Nasdaq 5M rules on US30, raw (PLAN.md, frozen before results). Run from AAA EAs/EA store: uv run python "<this>" native, then uv run python "<this>" report."""
import gzip, importlib.util, json, os, shutil, statistics, sys, time
from datetime import date
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness as rb  # noqa: E402
EX5 = PACKAGE / 'Nasdaq 5M Candle Rule 2026-11-05/EA/Nasdaq 5M Candle Rule Research EA.ex5'; SYM = 'US30'
SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']), 'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': ('2019-01-01', '2026-11-01')}
ON = dict(InpRequireDIAgreement='true', InpDirectionRule='0')
VERSIONS = {'ATR6': dict(ON, InpStopMode='0', InpInitialStopATR='6.0'), 'P60': dict(ON, InpStopMode='2', InpInitialStopATR='4.0', InpInitialStopPercent='0.60'),
            'FIXED': dict(ON, InpStopMode='0', InpInitialStopATR='4.0', InpUseFixedTarget='true', InpRewardRisk='2.5', InpUseATRTrailing='false', InpCloseAtSessionEnd='true'),
            'CONTROL': dict(ON, InpStopMode='0', InpInitialStopATR='6.0', InpDirectionRule='2')}
RECENT = {'6m': ('2026-05-01', '2026-11-01'), '1y': ('2025-11-01', '2026-11-01'), '3y': ('2023-11-01', '2026-11-01'), '5y': ('2021-11-01', '2026-11-01')}
YEARS = {str(y): (f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else '2026-11-01') for y in range(2019, 2027)}


def native():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    item = next(i for i in json.loads((PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8-sig')) if i['label'] == 'Nasdaq 5M Candle Momentum')
    base = {k: str(v) for k, v in item['inputs'].items()}; base.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false', InpMagic='862030')
    dest = b.TESTER / 'MQL5/Experts/CalyxUS30Raw'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'us30-raw.ex5'); dot = lambda s: s.replace('-', '.')  # noqa: E731
    b.CONFIG.update(periods={k: dot(a) for k, (a, _) in WINDOWS.items()}, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxUS30Raw', expert_file='us30-raw.ex5',
                    controls={}, period='M5', common_inputs=base, variants={k: {'label': k, 'inputs': v} for k, v in VERSIONS.items()})
    (H / 'RUN_PLAN.json').write_text(json.dumps(dict(ex5_sha=b.sha(EX5), base=base, versions=VERSIONS, windows=WINDOWS), indent=1), encoding='utf-8')

    def run(v, w):
        b.CONFIG['end_date'] = dot(WINDOWS[w][1])
        for attempt in range(4):                         # the tester agent can time out at startup when the CPU is busy
            try:
                b.run_case(SYM, v, w); return
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', v, w, flush=True); time.sleep(60)
    for w in ('all', 'oos', 'val', 'dev'):
        for v in ('ATR6', 'P60', 'FIXED'): run(v, w)
    run('CONTROL', 'all')
    buy_hold.run(H, SYM, {**WINDOWS, **RECENT, **YEARS}); print('ALL DONE', flush=True)


def ledger(v, w):
    d = H / f'native/nw-{SYM}-{v}-{w}'; meta = json.loads((d / 'run.json').read_text(encoding='utf-8')); T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4
    for t in T: t['r'] = t['net_profit'] / (0.01 * bal); bal += t['net_profit']
    return T, meta, buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz')


def wd(a, b): return sum(1 for o in range(date.fromisoformat(a).toordinal(), date.fromisoformat(b).toordinal()) if date.fromordinal(o).weekday() < 5)


def stats(R, a, b):
    if not R: return dict(n=0)
    v = [x for x in R if x > 0]; l = [x for x in R if x < 0]; gl = -sum(l); avw = statistics.fmean(v) if v else 0; avl = -statistics.fmean(l) if l else 0; d = wd(a, b)
    return dict(n=len(R), pm=round(len(R) / (d / 21.75), 1), pd=round(len(R) / d, 2), win=round(100 * len(v) / len(R), 1), be=round(100 * avl / (avw + avl), 1) if avw + avl else None, avw=round(avw, 2), avl=round(avl, 2), pf=round(sum(v) / gl, 2) if gl else None, tot=round(sum(R), 1), dd=round(rb.max_drawdown(R), 1))


def report():
    out = {}
    for v in VERSIONS:
        T, meta, dd = ledger(v, 'all'); R = [t['r'] for t in T]; row = dict(native={}, recent={}, years={}, flags=meta['journal_flags'], first=T[0]['open_time'] if T else None, all=stats(R, *WINDOWS['all']))
        for name, w in {**RECENT, **YEARS}.items(): row['recent' if name in RECENT else 'years'][name] = stats([t['r'] for t in T if w[0] <= t['close_time'][:10] < w[1]], *w)
        for w in WINDOWS:
            if (H / f'native/nw-{SYM}-{v}-{w}/run.json').exists():
                t2, m2, d2 = ledger(v, w); row['native'][w] = dict(stats([t['r'] for t in t2], *WINDOWS[w]), ret=round(sum(t['net_profit'] for t in t2) / 100, 2), eq_dd=d2, ok=m2['ok'])
        if v != 'CONTROL':
            yr = round(len(R) / ((date(2026, 11, 1) - date(2019, 1, 1)).days / 365.25)); cal = [date.fromordinal(o).isoformat() for o in range(date(2019, 1, 1).toordinal(), date(2026, 11, 1).toordinal()) if date.fromordinal(o).weekday() < 5]
            rows = [dict(close_time=t['close_time'], r=t['r']) for t in T]
            row['mc'] = dict(full=rb.three_monte_carlo(R), one_year=rb.three_monte_carlo(R, horizon=yr), block_12m=rb.day_block_bootstrap(rows, 261, value='r', paths=10000, block_days=5, seed=20261105, calendar_days=cal), dependence=rb.dependence(rows, value='r', time='close_time'),
                             ladder={f'{c:.2f}': rb.three_monte_carlo(R, horizon=yr, extra_cost=c)['randomize']['both']['red_pct'] for c in (0.02, 0.05, 0.10)})
        out[v] = row
    out['buy_hold'] = {w: buy_hold.load(H, SYM, w) for w in {**WINDOWS, **RECENT, **YEARS}}
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    L = ['| Version | Window | Return | PF | Win % | Needed | Trades (/month, /day) | Equity DD |', '|---|---|---:|---:|---:|---:|---|---:|']
    for v in VERSIONS:
        for w, x in out[v]['native'].items(): L.append(f"| {v} | {w} | {x['ret']:+.1f}% | {x['pf']} | {x['win']} | {x['be']} | {x['n']} ({x['pm']}, {x['pd']}) | {x['eq_dd']}% |")
    L += ['', '| Version | Window, R from the all-years ledger | Total R | PF | Win % | Trades |', '|---|---|---:|---:|---:|---:|']
    for v in VERSIONS:
        for w, x in {**out[v]['recent'], **out[v]['years']}.items(): L.append(f"| {v} | {w} | {x.get('tot')} | {x.get('pf')} | {x.get('win')} | {x['n']} |")
    L += ['', '| Version | Total R | Real DD R / shuffle p95 | Real DD worse than | Best day | Resample red 8y / 1y | Randomize red 8y / 1y | 1y red at +0.02 / 0.05 / 0.10R | 12 m block p05 / p50 R, DD p95 |', '|---|---:|---|---:|---|---|---|---|---|']
    for v in ('ATR6', 'P60', 'FIXED'):
        m = out[v]['mc']; f, y, k, a = m['full'], m['one_year'], m['block_12m'], m['ladder']
        L.append(f"| {v} | {f['real']['total']:+.1f} | {f['real']['max_drawdown']:.1f} / {f['reshuffle']['max_drawdown']['p95']:.1f} | {f['reshuffle']['real_drawdown_worse_than_pct']}% | {m['dependence']['verdict']} | {f['resample']['red_pct']}% / {y['resample']['red_pct']}% | {f['randomize']['both']['red_pct']}% / {y['randomize']['both']['red_pct']}% | {a['0.02']} / {a['0.05']} / {a['0.10']}% | {k['total']['p05']:+.1f} / {k['total']['p50']:+.1f}, {k['max_drawdown']['p95']:.1f} |")
    L += ['', '| Buy and hold US30 | Return | Price return | Swap | Equity DD |', '|---|---:|---:|---:|---:|'] + [f"| {w} | {x['return_pct']:+.1f}% | {x['price_return_pct']:+.1f}% | {x['swap_pct']:+.1f}% | {x['max_dd_pct']}% |" for w, x in out['buy_hold'].items()]
    (H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    native() if sys.argv[1] == 'native' else report()
