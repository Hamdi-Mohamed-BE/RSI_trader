"""Gold EMA Ribbon raw study (RULES.md). Run from AAA EAs/EA store:
  uv run python "<this>" main      compile + MAIN Model 4 on 6m / 1y / 2y / 3y / 5y / all + sensitivities (all) + buy and hold
  uv run python "<this>" controls  MAIN Model 1 + 20 random-direction + 20 random-entry seeds (Model 1, all), rate calibrated on MAIN
  uv run --with numpy python "<this>" report -> RESULTS.json"""
import gzip, json, math, os, re, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import importlib.util
import buy_hold, data_split, robustness  # noqa: E402
SRC = H / 'EA/Gold EMA Ribbon Research EA.mq5'; SYM = 'XAUUSD'; END = '2026-11-12'; RISK = 0.0075
PERIODS = {'6m': '2026-05-12', '1y': '2025-11-12', '2y': '2024-11-12', '3y': '2023-11-12', '5y': '2021-11-12', 'all': '2019-01-01'}
SENS = {'STATE': dict(InpEntryMode='1'), 'RIB2': dict(InpE1='5', InpE2='10', InpE3='20', InpE4='30', InpE5='50'),
        'RIB3': dict(InpE1='10', InpE2='20', InpE3='30', InpE4='40', InpE5='50'), 'LONG': dict(InpDirection='0')}
SEEDS = range(1, 21)


def dot(s): return s.replace('-', '.')


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    b.CONFIG.update(end_date=dot(END), deposit=100000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, period='H1',
                    expert_dir='CalyxGoldRibbon', expert_file='gold-ribbon.ex5', controls={}, variants={}, common_inputs=dict(InpRiskPercent='0.75'))
    return b


def compile_ea(b):
    log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith(b'\xff\xfe') else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]
    assert SRC.with_suffix('.ex5').stat().st_mtime >= started - 2
    dest = b.TESTER / 'MQL5/Experts/CalyxGoldRibbon'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC.with_suffix('.ex5'), dest / 'gold-ribbon.ex5'); print('COMPILED', flush=True)


def case(b, key, inputs, period, model):
    if (b.OUT / f'nw-{SYM}-{key}-{period}' / 'trades.json.gz').exists(): return
    b.CONFIG['model'] = model; b.CONFIG['periods'] = {period: dot(PERIODS[period])}; b.CONFIG['variants'] = {key: {'label': key, 'inputs': inputs}}
    for attempt in range(3):
        try:
            b.run_case(SYM, key, period); return
        except SystemExit:
            print('RETRY', key, period, flush=True); time.sleep(30)


def main():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; compile_ea(b)
    for per in PERIODS: case(b, 'MAIN', {}, per, 4)
    for k, v in SENS.items(): case(b, k, v, 'all', 4)
    W = {p: (PERIODS[p], END) for p in PERIODS}
    try:
        ok = all(buy_hold.load(H, SYM, w) for w in W)
    except Exception:
        ok = False
    if not ok:
        try: buy_hold.run(H, SYM, W)
        except Exception as e: print('BUYHOLD FAILED', repr(e)[:200], flush=True)
    print('MAIN DONE', flush=True)


def trades(key, per='all'):
    return sorted(json.loads(gzip.open(H / 'native' / f'nw-{SYM}-{key}-{per}' / 'trades.json.gz').read()), key=lambda t: t['close_time'])


def controls():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; compile_ea(b)
    case(b, 'MAIN_M1', {}, 'all', 1)
    T = trades('MAIN_M1'); bars = (datetime.fromisoformat(END) - datetime.fromisoformat(PERIODS['all'])).days * 24 * 5 / 7
    held = sum((datetime.fromisoformat(t['close_time'][:19]) - datetime.fromisoformat(t['open_time'][:19])).total_seconds() / 3600 for t in T)
    rate = round(len(T) / max(1.0, bars - held), 5); (H / 'RANDOM_RATE.json').write_text(json.dumps(dict(trades=len(T), bars=bars, held_hours=held, rate=rate)), encoding='utf-8')
    print('random-entry rate per flat H1 bar', rate, flush=True)
    for s in SEEDS:
        case(b, f'RNDDIR{s}', dict(InpControl='1', InpSeed=str(s)), 'all', 1)
        case(b, f'RNDENT{s}', dict(InpControl='2', InpRandomRate=str(rate), InpSeed=str(s)), 'all', 1)
    print('CONTROLS DONE', flush=True)


def rows(key, per='all'):
    out = []; bal = 1e5
    for t in trades(key, per):
        out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (RISK * bal), net=t['net_profit'], cost=abs(t['commission']) + max(0.0, -t['swap']))); bal += t['net_profit']
    return out


def stats(x, a, b):
    x = [r for r in x if a <= r['o'][:10] < b]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
    eq = pk = dd = 0.0; bal = 1e5; bpk = 1e5; bdd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); bal += r['net']; bpk = max(bpk, bal); bdd = max(bdd, 1 - bal / bpk); days[r['c'][:10]] += r['net']
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    wins = [r['net'] for r in x if r['net'] > 0]; losses = [r['net'] for r in x if r['net'] < 0]
    wk = sum(1 for r in x if any((datetime.fromisoformat(r['o'][:10]) + timedelta(days=i)).weekday() == 5 for i in range((datetime.fromisoformat(r['c'][:10]) - datetime.fromisoformat(r['o'][:10])).days + 1)))
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_day=round(len(x) / months / 21, 3), total_r=round(sum(r['r'] for r in x), 1), net=round(sum(r['net'] for r in x), 0),
                pf=round(gw / gl, 2) if gl else None, win=round(100 * len(wins) / max(1, len(x)), 1), avg_win=round(sum(wins) / max(1, len(wins)), 0), avg_loss=round(sum(losses) / max(1, len(losses)), 0),
                closed_dd_r=round(dd, 1), closed_dd_pct=round(100 * bdd, 1), worst_day_pct=round(100 * min(days.values()) / 1e5, 2) if days else None, weekend_held=wk)


def report():
    sp = data_split.research_split('2019-01-01', END)
    W = {'all': (PERIODS['all'], END), 'dev': (sp['development']['start'], sp['development']['end_exclusive']), 'val': (sp['validation']['start'], sp['validation']['end_exclusive']),
         'oos': (sp['oos']['start'], sp['oos']['end_exclusive'])}
    out = dict(windows=W, main={}, sens={}, controls={}, buy_hold={})
    for per in PERIODS:
        try: out['main'][per] = stats(rows('MAIN', per), PERIODS[per], END)
        except FileNotFoundError: pass
    A = rows('MAIN', 'all'); out['main_split'] = {w: stats(A, *v) for w, v in W.items()}
    out['main_years'] = {str(y): stats(A, f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else END)['total_r'] for y in range(2019, 2027)}
    for k in SENS:
        try: out['sens'][k] = stats(rows(k), *W['all'])
        except FileNotFoundError: pass
    try:
        m1 = stats(rows('MAIN_M1'), *W['all']); rd = [stats(rows(f'RNDDIR{s}'), *W['all'])['total_r'] for s in SEEDS]; re_ = [stats(rows(f'RNDENT{s}'), *W['all'])['total_r'] for s in SEEDS]
        out['controls'] = dict(main_m1=m1, random_direction=dict(totals=rd, p=round((sum(1 for v in rd if v >= m1['total_r']) + 1) / (len(rd) + 1), 3)),
                               random_entry=dict(totals=re_, p=round((sum(1 for v in re_ if v >= m1['total_r']) + 1) / (len(re_) + 1), 3)))
    except FileNotFoundError: out['controls'] = 'not run'
    seq = [r['r'] for r in A]; tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
    out['mc'] = dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct'])
    j = gzip.open(H / 'native/nw-XAUUSD-MAIN-all/journal.txt.gz').read().decode('utf-8', 'replace')
    ents = [l for l in j.splitlines() if 'RIB_ENTRY' in l and 'Core' in l]; costs = []
    for l, r in zip(ents, A):
        m = re.search(r'stop=([\d.]+) spread_pts=(\d+)', l); spread_r = (int(m.group(2)) * 0.01) / float(m.group(1)) if m else 0.0
        costs.append(spread_r + r['cost'] / max(1e-9, abs(r['net'] / r['r']) if r['r'] else 1e9))
    out['cost_stress'] = robustness.cost_stress([r['r'] for r in A], costs) if len(costs) == len(A) else 'entry log mismatch'
    for w, v in {**{p: (PERIODS[p], END) for p in PERIODS}}.items():
        try: x = buy_hold.load(H, SYM, w); out['buy_hold'][w] = dict(ret=x['return_pct'], dd=x['max_dd_pct'])
        except Exception as e: out['buy_hold'][w] = repr(e)[:80]
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps({k: out[k] for k in ('main', 'main_split', 'main_years', 'sens', 'mc')}, indent=1, default=str)[:6000])


if __name__ == '__main__':
    {'main': main, 'controls': controls}.get(sys.argv[1], report)()
