"""Video ideas raw test on US100 (PLAN.md, frozen before results). Run from AAA EAs/EA store:
  uv run python "<this>" ea       compile the research EA (no tester)
  uv run python "<this>" native   every strategy and control, Model 4, then buy and hold (one tester job at a time)
  uv run python "<this>" report   -> RESULTS.json, RESULTS.md"""
import gzip, importlib.util, json, os, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, robustness  # noqa: E402
SRC = H / 'EA/Video Ideas Raw EA.mq5'; SYM = 'USTEC'
START, SPLIT, END = '2019-07-16', '2024-01-01', '2026-11-10'
WINDOWS = {'all': (START, END), 'in_sample': (START, SPLIT), 'oos': (SPLIT, END), 'last_year': ('2025-11-10', END)}
YEARS = [(str(y), (f'{y}-01-01' if y > 2019 else START, f'{y + 1}-01-01' if y < 2026 else END)) for y in range(2019, 2027)]
dot = lambda s: s.replace('-', '.')  # noqa: E731
V = {'DRIFT': ('M5', dict(InpStrategy='1')), 'DRIFT_RAND': ('M5', dict(InpStrategy='1', InpRandomDirection='true')),
     'VAULT': ('M30', dict(InpStrategy='2')), 'VWAPADX': ('M1', dict(InpStrategy='3')),
     'ONB': ('M15', dict(InpStrategy='4')), 'ONB_NOBIAS': ('M15', dict(InpStrategy='4', InpUseBias='false')), 'ONB_RAND': ('M15', dict(InpStrategy='4', InpRandomDirection='true')),
     'REEL': ('M15', dict(InpStrategy='5')), 'REEL_NOBIAS': ('M15', dict(InpStrategy='5', InpUseBias='false')), 'REEL_RAND': ('M15', dict(InpStrategy='5', InpRandomDirection='true'))}
CONTROLS = {'DRIFT': ('DRIFT_RAND',), 'ONB': ('ONB_NOBIAS', 'ONB_RAND'), 'REEL': ('REEL_NOBIAS', 'REEL_RAND')}
LABEL = {'DRIFT': 'Drift VWAP Pullback (video 1)', 'VAULT': 'Vault Break (video 2 #1)', 'VWAPADX': 'VWAP pullback + ADX gate (video 2 #2)', 'ONB': 'Overnight Bias ORB (video 2 #3)', 'REEL': 'Reel ORB (overnight thirds, no ADX)'}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    return b


def build_ea():
    editor = harness().TESTER / 'MetaEditor64.exe'; log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{editor}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); text = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); print(text[-1500:])
    assert '0 errors, 0 warnings' in text, 'compile failed'; assert SRC.with_suffix('.ex5').stat().st_mtime >= started - 2; print('COMPILED', flush=True)


def native():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxVideoIdeas'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC.with_suffix('.ex5'), dest / 'video-ideas.ex5')
    b.CONFIG.update(periods={'all': dot(START)}, end_date=dot(END), deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=21600,
                    expert_dir='CalyxVideoIdeas', expert_file='video-ideas.ex5', controls={}, variants={}, common_inputs=dict(InpRiskPercent='1.0', InpSeed='1', InpServerUtcOffsetHours='0'))
    keys = [k for k in (sys.argv[2].split(',') if len(sys.argv) > 2 else V)]       # owner 2026-11-09: one strategy at a time, e.g. native DRIFT,DRIFT_RAND
    for key, (tf, inputs) in ((k, V[k]) for k in keys):
        b.CONFIG['period'] = tf; b.CONFIG['variants'][key] = {'label': key, 'inputs': inputs}
        for attempt in range(4):
            try:
                b.run_case(SYM, key, 'all'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
        print('DONE', key, flush=True)
    try:
        done = all(buy_hold.load(H, SYM, w) for w in WINDOWS)
    except Exception:
        done = False
    if not done:
        res = buy_hold.run(H, SYM, {k: v for k, v in WINDOWS.items()}); print('BUYHOLD', {k: (v['return_pct'], v['max_dd_pct']) for k, v in res.items()}, flush=True)
    print('ALL DONE', datetime.now(timezone.utc).isoformat(), flush=True)


def smoke():
    """Pre-run check, not a result: each of the five rules on 2026-08-01 -> 2026-11-10 must trade and log no rejected orders. Kept in smoke/."""
    b = harness(); b.OUT = H / 'smoke'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxVideoIdeas'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC.with_suffix('.ex5'), dest / 'video-ideas.ex5')
    b.CONFIG.update(periods={'smoke': '2026.08.01'}, end_date=dot(END), deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=7200,
                    expert_dir='CalyxVideoIdeas', expert_file='video-ideas.ex5', controls={}, variants={}, common_inputs=dict(InpRiskPercent='1.0', InpSeed='1', InpServerUtcOffsetHours='0'))
    for key in LABEL:
        tf, inputs = V[key]; b.CONFIG['period'] = tf; b.CONFIG['variants'][key] = {'label': key, 'inputs': inputs}
        meta = b.run_case(SYM, key, 'smoke'); T = json.loads(gzip.open(b.OUT / f'nw-{SYM}-{key}-smoke' / 'trades.json.gz').read())
        print('SMOKE', key, len(T), 'trades', meta.get('journal_flags'), [(t['open_time'][5:16], t['side'], t.get('exit_comment')) for t in T[:3]], flush=True)


def rows_of(key):
    T = json.loads(gzip.open(H / 'native' / f'nw-{SYM}-{key}-all' / 'trades.json.gz').read()); bal = 1e4; rows = []
    for t in sorted(T, key=lambda t: t['close_time']):
        rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'], side=t['side'])); bal += t['net_profit']
    return rows


def stats(rows, a, b_):
    x = [r for r in rows if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = peak = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; peak = max(peak, eq); dd = max(dd, peak - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b_) - datetime.fromisoformat(a)).days / 30.4375
    tot = sum(r['r'] for r in x)
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / (months * 21.74), 3), total_r=round(tot, 2), mean_r=round(tot / max(1, len(x)), 4),
                pf=round(gw / gl, 3) if gl else None, win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 2), ret_dd=round(tot / dd, 2) if dd else None,
                worst_day_r=round(min(days.values()), 2) if days else None, without_best5=round(tot - sum(sorted(days.values(), reverse=True)[:5]), 2),
                longs=sum(r['side'].lower() in ('buy', 'long') for r in x), shorts=sum(r['side'].lower() in ('sell', 'short') for r in x))


def report():
    out = dict(windows=WINDOWS, variants={}, failed=[])
    for k in V:
        d = H / 'native' / f'nw-{SYM}-{k}-all'
        if not (d / 'run.json').exists() or not json.loads((d / 'run.json').read_text(encoding='utf-8')).get('ok'): out['failed'].append(k); continue
        rows = rows_of(k); meta = json.loads((d / 'run.json').read_text(encoding='utf-8'))
        out['variants'][k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, years={y: stats(rows, *v)['total_r'] for y, v in YEARS},
                                  native_return_pct=round(sum(r['net'] for r in rows) / 100, 2), equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'), flags=meta.get('journal_flags'),
                                  three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104) if len(rows) >= 30 else None)
    try:
        out['buy_hold'] = {w: {x: buy_hold.load(H, SYM, w)[x] for x in ('return_pct', 'max_dd_pct')} for w in WINDOWS}
    except Exception as e:
        out['buy_hold'] = f'not available: {e}'
    Vv = out['variants']
    for k, v in Vv.items():
        a = v['windows']['all']; w = v['windows']
        v['gate'] = dict(pf=(a['pf'] or 0) >= 1.15, in_sample=w['in_sample']['total_r'] > 0, oos=w['oos']['total_r'] > 0, without_best5=a['without_best5'] > 0, freq=a['per_month'] >= 1,
                         controls=all(a['total_r'] > Vv[c]['windows']['all']['total_r'] for c in CONTROLS.get(k, ()) if c in Vv))
        v['passes'] = k in LABEL and all(v['gate'].values())
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps({k: (v['windows']['all'], v['passes']) for k, v in Vv.items()}, default=str)[:4000])


if __name__ == '__main__':
    {'ea': build_ea, 'smoke': smoke, 'native': native, 'report': report}[sys.argv[1]]()
