"""Noise Band raw study (RULES.md + Addendum 1). Run from AAA EAs/EA store:  uv run python "<this>" build | parity | main | report"""
import gzip, importlib.util, json, math, os, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent; PIPE = B.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
EA = H / 'EA'; SRC = EA / 'Noise Band Research EA.mq5'; OLD = EA / 'Noise Band Research EA.v1.00.mq5'
START, END = '2019-07-16', '2026-11-21'
ASSETS = {'USTEC': dict(InpMarketClock='0', InpOpenMin='570', InpLastCheckMin='900', InpFlatMin='955'),
          'US500': dict(InpMarketClock='0', InpOpenMin='570', InpLastCheckMin='900', InpFlatMin='955'),
          'DE30': dict(InpMarketClock='2', InpOpenMin='540', InpLastCheckMin='990', InpFlatMin='1045')}
WIDE = dict(InpK='1.4', InpStopATR='2.0', InpTrailATR='2.0', InpTrailStartR='1.0', InpATRPeriod='14', InpRiskPercent='1.0', InpRandomDirection='false', InpSeed='1',
            InpServerUtcOffsetHours='0', InpDeviationPoints='50', InpMagic='2911120')
PAPER = dict(WIDE, InpK='0.6', InpStopATR='1.5')
VERSIONS = {'WIDE': WIDE, 'PAPER': PAPER, **{f'RND{s}': dict(WIDE, InpRandomDirection='true', InpSeed=str(s)) for s in range(1, 6)}}


def harness(out='native'):
    s = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(s); s.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / out; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def build():
    b = harness()
    for src in (OLD, SRC):
        log = src.with_suffix('.compile.log'); started = time.time()
        subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith(b'\xff\xfe') else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]
        assert src.with_suffix('.ex5').stat().st_mtime >= started - 2
    print('BUILT', flush=True)


def stage(b):
    d = b.TESTER / 'MQL5/Experts/CalyxNoiseBand'; d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC.with_suffix('.ex5'), d / 'nb110.ex5'); shutil.copy2(OLD.with_suffix('.ex5'), d / 'nb100.ex5')


def case(b, sym, key, expert, inputs, period, start, end):
    if (b.OUT / f'nw-{sym}-{key}-{period}' / 'trades.json.gz').exists(): return
    b.CONFIG.update(model=4, end_date=end.replace('-', '.'), periods={period: start.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150,
                    profile='Calyx Research Empty', timeout_seconds=14400, period='M30', expert_dir='CalyxNoiseBand', expert_file=expert, controls={}, common_inputs={},
                    variants={key: {'label': key, 'inputs': inputs}})
    for _ in range(3):
        try: b.run_case(sym, key, period); break
        except SystemExit: print('RETRY', sym, key, flush=True); time.sleep(30)
    print('DONE', sym, key, period, flush=True)


def parity():
    b = harness('parity'); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    old = {k: v for k, v in WIDE.items()}
    case(b, 'USTEC', 'V100', 'nb100.ex5', old, '6m', '2026-05-21', END)
    case(b, 'USTEC', 'V110', 'nb110.ex5', dict(WIDE, **ASSETS['USTEC']), '6m', '2026-05-21', END)
    k = lambda p: [(t['open_time'], t['close_time'], t['side'], t['net_profit']) for t in json.loads(gzip.open(H / 'parity' / f'nw-USTEC-{p}-6m' / 'trades.json.gz').read())]  # noqa: E731
    res = dict(n=len(k('V100')), identical=k('V100') == k('V110')); (H / 'PARITY.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print('PARITY', res, flush=True)
    assert res['identical'] and res['n'] > 0


def main():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    for key in VERSIONS:
        for sym, clock in ASSETS.items():
            case(b, sym, key, 'nb110.ex5', dict(VERSIONS[key], **clock), 'all', START, END)
    for sym in ASSETS:
        try:
            if not buy_hold.load(H, sym, 'all'): raise ValueError
        except Exception:
            try: buy_hold.run(H, sym, {'all': (START, END)})
            except Exception as e: print('BUYHOLD FAILED', sym, repr(e)[:200], flush=True)
    print('MAIN DONE', flush=True)


# ---------------------------------------------------------------- report
def local(utc_s, clock):
    u = datetime.fromisoformat(utc_s); y = u.year
    if clock == '2':
        def ls(m):
            d = datetime(y, m, 31)
            while d.weekday() != 6: d -= timedelta(days=1)
            return d + timedelta(hours=1)
        return u + timedelta(hours=2 if ls(3) <= u < ls(10) else 1)
    def ns(m, n):
        d = datetime(y, m, 1)
        while d.weekday() != 6: d += timedelta(days=1)
        return d + timedelta(days=7 * (n - 1))
    return u - timedelta(hours=4 if ns(3, 2) + timedelta(hours=7) <= u < ns(11, 1) + timedelta(hours=6) else 5)


def overnight(sym, key):
    """Trades not closed by the flat time on their entry day (rule: never overnight)."""
    c = ASSETS[sym]; flat = int(c['InpFlatMin']); n = 0
    for t in json.loads(gzip.open(H / 'native' / f'nw-{sym}-{key}-all' / 'trades.json.gz').read()):
        o, e = local(t['open_time'], c['InpMarketClock']), local(t['close_time'], c['InpMarketClock'])
        if e.date() != o.date() or e.hour * 60 + e.minute > flat + 5: n += 1
    return n


def ledger(sym, key):
    T = sorted(json.loads(gzip.open(H / 'native' / f'nw-{sym}-{key}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; out = []
    for t in T:
        out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'], cost=-(t['commission'] + min(0.0, t['swap'])) / (0.01 * bal),
                        side=t['side'], sym=sym)); bal += t['net_profit']
    return out


def streaks(v):
    w, l = [], []; cur = 0
    for x in v:
        if x > 0: cur = cur + 1 if cur > 0 else 1
        else: cur = cur - 1 if cur < 0 else -1
        if cur > 0 and (not w or cur == 1): w.append(1) if cur == 1 else None
        if cur > 0 and cur > 1: w[-1] = cur
        if cur < 0 and cur == -1: l.append(1)
        if cur < 0 and cur < -1: l[-1] = -cur
    return (round(sum(w) / len(w), 2) if w else 0, round(sum(l) / len(l), 2) if l else 0, max(w or [0]), max(l or [0]))


def stats(x, a, b):
    x = [r for r in x if a <= r['o'][:10] < b]; R = [r['r'] for r in x]
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375; wd = sum(1 for i in range((datetime.fromisoformat(b) - datetime.fromisoformat(a)).days)
                                                                                                if (datetime.fromisoformat(a) + timedelta(days=i)).weekday() < 5)
    if not R: return dict(trades=0)
    gw = sum(v for v in R if v > 0); gl = -sum(v for v in R if v < 0)
    eq = pk = dd = 0.0
    for v in R: eq += v; pk = max(pk, eq); dd = max(dd, pk - eq)
    mon = defaultdict(float); day = defaultdict(float)
    for r in x: mon[r['c'][:7]] += r['r']; day[r['c'][:10]] += r['r']
    allm = [f'{y}-{m:02d}' for y in range(int(a[:4]), int(b[:4]) + 1) for m in range(1, 13) if a[:7] <= f'{y}-{m:02d}' < b[:7] or f'{y}-{m:02d}' == b[:7] and b[8:] > '01']
    dv = [day.get((datetime.fromisoformat(a) + timedelta(days=i)).strftime('%Y-%m-%d'), 0.0) for i in range((datetime.fromisoformat(b) - datetime.fromisoformat(a)).days)
          if (datetime.fromisoformat(a) + timedelta(days=i)).weekday() < 5]
    mu = sum(dv) / len(dv); sd = math.sqrt(sum((d - mu) ** 2 for d in dv) / max(1, len(dv) - 1))
    aw, al, mw, ml = streaks(R)
    return dict(trades=len(R), per_month=round(len(R) / months, 1), per_day=round(len(R) / wd, 2), r=round(sum(R), 1), ret_pct_1R1pct=round(sum(R), 1), pf=round(gw / gl, 2) if gl else None,
                win=round(100 * sum(v > 0 for v in R) / len(R), 1), avg_r=round(sum(R) / len(R), 3), consistency=round(100 * sum(1 for m in allm if mon.get(m, 0) > 0) / max(1, len(allm)), 1),
                avg_win_streak=aw, avg_loss_streak=al, max_win_streak=mw, max_loss_streak=ml, sharpe=round(mu / sd * math.sqrt(252), 2) if sd else None, closed_dd_r=round(dd, 1))


def report():
    sp = data_split.research_split(START, END)
    W = {'all': (START, END), 'dev': (sp['development']['start'], sp['development']['end_exclusive']), 'val': (sp['validation']['start'], sp['validation']['end_exclusive']),
         'oos': (sp['oos']['start'], sp['oos']['end_exclusive']), 'last12m': ('2025-11-21', END)}
    out = dict(windows={k: list(v) for k, v in W.items()}, cases={})
    for sym in ASSETS:
        for key in VERSIONS:
            try: A = ledger(sym, key)
            except FileNotFoundError: continue
            run = json.loads((H / 'native' / f'nw-{sym}-{key}-all' / 'run.json').read_text())
            m = run['metrics']; years = defaultdict(float)
            for r in A: years[r['o'][:4]] += r['r']
            row = dict(native=dict(ret=m['return_pct'], pf=m['profit_factor'], mt5_dd=m['max_drawdown_pct'], trades=m['trades'], flags=run.get('journal_flags'), ticks=run.get('real_tick_lines')),
                       win={k: stats(A, *v) for k, v in W.items()}, years={y: round(v, 1) for y, v in sorted(years.items())}, held_past_flat=overnight(sym, key))
            try:
                rq = buy_hold.relative_equity_dd(next((H / 'native' / f'nw-{sym}-{key}-all').glob('*.htm.gz')))
                row['native']['equity_dd_relative'] = rq
            except Exception: pass
            if not key.startswith('RND') and len(A) >= 30:
                mc = robustness.three_monte_carlo([r['r'] for r in A], runs=1000, seed=20261104)
                row['mc'] = dict(resample=mc['resample']['red_pct'], randomize=mc['randomize']['both']['red_pct'], clumped=mc['reshuffle']['real_drawdown_worse_than_pct'])
                row['dependence'] = robustness.dependence([dict(net_profit=r['r'], close_time=r['c']) for r in A])
                row['cost_stress'] = robustness.cost_stress([r['r'] for r in A], [r['cost'] for r in A])
            out['cases'][f'{sym} {key}'] = row
        rnd = [out['cases'][f'{sym} RND{s}']['win']['all']['r'] for s in range(1, 6) if f'{sym} RND{s}' in out['cases']]
        if f'{sym} WIDE' in out['cases']: out['cases'][f'{sym} WIDE']['random_direction_r'] = rnd
        try: out[f'{sym} buy&hold'] = buy_hold.load(H, sym, 'all')
        except Exception as e: out[f'{sym} buy&hold'] = repr(e)[:120]
    for key in ('WIDE', 'PAPER'):   # combined: one account trading all three, 1 R each
        try: A = sorted(sum((ledger(s, key) for s in ASSETS), []), key=lambda r: r['c'])
        except FileNotFoundError: continue
        mc = robustness.three_monte_carlo([r['r'] for r in A], runs=1000, seed=20261104)
        out['cases'][f'ALL3 {key}'] = dict(win={k: stats(A, *v) for k, v in W.items()}, mc=dict(resample=mc['resample']['red_pct'], randomize=mc['randomize']['both']['red_pct']),
                                           years={y: round(sum(r['r'] for r in A if r['o'][:4] == y), 1) for y in sorted({r['o'][:4] for r in A})})
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    for k, v in out['cases'].items():
        a = v['win']['all']; print(f"{k:14s} n {a.get('trades')} /m {a.get('per_month')} R {a.get('r')} PF {a.get('pf')} win {a.get('win')} DD {a.get('closed_dd_r')} | dev {v['win']['dev'].get('r')} val {v['win']['val'].get('r')} oos {v['win']['oos'].get('r')} 12m {v['win']['last12m'].get('r')} | yrs {v.get('years')} | mc {v.get('mc')}")
    graph(out)


def graph(out):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for sym, col in (('USTEC', '#2a6fdb'), ('US500', '#1a9e77'), ('DE30', '#d95f02')):
        for key, ls in (('WIDE', '-'), ('PAPER', ':')):
            try: A = ledger(sym, key)
            except FileNotFoundError: continue
            x = [datetime.fromisoformat(r['c']) for r in A]; y = []; s = 0
            for r in A: s += r['r']; y.append(s)
            ax.plot(x, y, ls, color=col, lw=1.6 if key == 'WIDE' else 1.1, label=f'{sym} {key}')
    try:
        A = sorted(sum((ledger(s, 'WIDE') for s in ASSETS), []), key=lambda r: r['c']); y = []; s = 0
        for r in A: s += r['r']; y.append(s)
        ax.plot([datetime.fromisoformat(r['c']) for r in A], y, '-', color='#222', lw=2.2, label='All 3 WIDE (1 R each)')
    except FileNotFoundError: pass
    ax.axhline(0, color='#999', lw=0.8); ax.set_ylabel('Cumulative R (1 R = 1% of balance at entry)'); ax.set_title('Noise Band raw - native MT5 Model 4, 2019-07 to 2026-11')
    ax.grid(alpha=0.25); ax.legend(ncol=3, fontsize=8, frameon=False); fig.tight_layout(); fig.savefig(H / 'BALANCE.png', dpi=130); print('GRAPH', H / 'BALANCE.png')


if __name__ == '__main__':
    {'build': build, 'parity': parity, 'main': main}.get(sys.argv[1], report)()
