"""Overnight Bias ORB multi-asset raw (PLAN.md). Run from AAA EAs/EA store:
  uv run python "<this>" native [SYM,...]   ONB + controls per symbol (Model 4), then buy and hold
  uv run --with numpy python "<this>" report -> RESULTS.json"""
import gzip, importlib.util, json, os, shutil, sys, time
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
EX5 = PACKAGE / 'Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.ex5'
SYMS = ['XAUUSD', 'BTCUSD', 'EURUSD', 'GBPJPY']; START, END = '2019-01-01', '2026-11-11'
SP = data_split.research_split(START, END)
WINDOWS = {'all': (START, END), 'dev': (SP['development']['start'], SP['development']['end_exclusive']), 'val': (SP['validation']['start'], SP['validation']['end_exclusive']),
           'oos': (SP['oos']['start'], SP['oos']['end_exclusive']), '3y': ('2023-11-11', END), 'last_year': ('2025-11-11', END), 'last_6m': ('2026-05-11', END)}
V = {'ONB': dict(InpStrategy='4'), 'ONB_NOBIAS': dict(InpStrategy='4', InpUseBias='false'), 'ONB_RAND': dict(InpStrategy='4', InpRandomDirection='true')}


def dot(s): return s.replace('-', '.')


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def native(syms):
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxVideoIdeas'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'video-ideas.ex5')
    b.CONFIG.update(periods={'all': dot(START)}, end_date=dot(END), deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=21600,
                    expert_dir='CalyxVideoIdeas', expert_file='video-ideas.ex5', controls={}, variants={}, period='M15',
                    common_inputs=dict(InpRiskPercent='1.0', InpSeed='1', InpServerUtcOffsetHours='0'))
    for sym in syms:
        for key, inputs in V.items():
            if (H / 'native' / f'nw-{sym}-{key}-all' / 'trades.json.gz').exists(): continue
            b.CONFIG['variants'][key] = {'label': key, 'inputs': inputs}
            for attempt in range(3):
                try:
                    b.run_case(sym, key, 'all'); break
                except SystemExit:
                    print('RETRY' if attempt < 2 else 'CASE FAILED', sym, key, flush=True); time.sleep(60)
        try:
            ok = all(buy_hold.load(H, sym, w) for w in WINDOWS)
        except Exception:
            ok = False
        if not ok:
            try:
                res = buy_hold.run(H, sym, dict(WINDOWS)); print('BUYHOLD', sym, {k: (v['return_pct'], v['max_dd_pct']) for k, v in res.items()}, flush=True)
            except Exception as e:
                print('BUYHOLD FAILED', sym, repr(e)[:300], flush=True)
    print('ALL DONE', flush=True)


def rows_of(sym, key):
    T = json.loads(gzip.open(H / 'native' / f'nw-{sym}-{key}-all' / 'trades.json.gz').read()); bal = 1e4; rows = []
    for t in sorted(T, key=lambda t: t['close_time']):
        rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'])); bal += t['net_profit']
    return rows


def stats(x, a, b):
    x = sorted((r for r in x if a <= r['o'][:10] < b), key=lambda r: r['c']); gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
    eq = pk = dd = 0.0; bal = 1e4; bpk = 1e4; bdd = 0.0
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); bal *= 1 + r['r'] / 100; bpk = max(bpk, bal); bdd = max(bdd, 1 - bal / bpk)
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_day=round(len(x) / months / 21, 3), total_r=round(sum(r['r'] for r in x), 1), ret_pct=round((bal / 1e4 - 1) * 100, 1),
                pf=round(gw / gl, 2) if gl else None, win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 1), closed_dd_pct=round(bdd * 100, 1))


def report():
    out = {}
    for sym in SYMS:
        try:
            rows = {k: rows_of(sym, k) for k in V}
        except FileNotFoundError:
            continue
        s = dict(first_trade=min(r['o'] for r in rows['ONB'])[:10] if rows['ONB'] else None, windows={k: {w: stats(rows[k], *v) for w, v in WINDOWS.items()} for k in V},
                 years={str(y): stats(rows['ONB'], f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else END)['total_r'] for y in range(2019, 2027)})
        seq = [r['r'] for r in rows['ONB']]
        if len(seq) > 30:
            tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
            s['mc'] = dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct'])
        try:
            s['buy_hold'] = {w: dict(ret=buy_hold.load(H, sym, w)['return_pct'], dd=buy_hold.load(H, sym, w)['max_dd_pct']) for w in WINDOWS}
        except Exception as e:
            s['buy_hold'] = repr(e)[:200]
        a = s['windows']['ONB']['all']; t3 = s['windows']['ONB']['3y']; mc = s.get('mc', {})
        s['gate'] = dict(all_pos=a['total_r'] > 0, y3_pos=t3['total_r'] > 0, pf=bool(a['pf'] and a['pf'] >= 1.15), n=a['trades'] >= 100,
                         beats_controls=all(a['total_r'] > s['windows'][c]['all']['total_r'] for c in ('ONB_NOBIAS', 'ONB_RAND')),
                         mc=bool(mc) and mc['resample_red'] <= 5 and mc['randomize_red'] <= 10)
        s['verdict'] = 'PASS' if all(s['gate'].values()) else 'FAIL'
        out[sym] = s
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps({k: (v['verdict'], v['gate']) for k, v in out.items()}, indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    native(a[1].split(',') if len(a) > 1 else SYMS) if a[0] == 'native' else report()
