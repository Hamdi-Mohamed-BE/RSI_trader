"""US100 9:15 NY ORB raw study (RULES.md). Run from AAA EAs/EA store:
  uv run python "<this>" main      compile + MAIN Model 4 (all / 2023 / 1y) + sensitivities (all) + buy and hold
  uv run python "<this>" controls  MAIN Model 1 + 20 random-direction + 20 random-entry seeds (Model 1, all), rate calibrated on MAIN_M1
  uv run --with numpy --with matplotlib python "<this>" report -> RESULTS.json + balance.png"""
import gzip, json, os, re, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import importlib.util
import buy_hold, data_split, robustness  # noqa: E402
SRC = H / 'EA/US100 915 ORB Research EA.mq5'; SYM = 'USTEC'; END = '2026-11-17'; RISK = 0.01; DEP = 10000.0
PERIODS = {'1y': '2025-11-17', '2023': '2023-01-01', 'all': '2019-07-16'}
SENS = {'NOEMA': dict(InpTrendEMA='0'), 'BODY': dict(InpBodyMode='1'), 'R1': dict(InpRewardRisk='1.0'), 'FLAT': dict(InpFlatMin='955')}
SEEDS = range(1, 21)
BARS_PER_DAY = 25   # signal bars 09:30 .. 15:30 NY


def dot(s): return s.replace('-', '.')


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    b.CONFIG.update(end_date=dot(END), deposit=int(DEP), currency='USD', execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, period='M15',
                    expert_dir='CalyxUS100ORB915', expert_file='orb915.ex5', controls={}, variants={}, common_inputs=dict(InpRiskPercent='1.0'))
    return b


def compile_ea(b):
    log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith(b'\xff\xfe') else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]
    assert SRC.with_suffix('.ex5').stat().st_mtime >= started - 2
    dest = b.TESTER / 'MQL5/Experts/CalyxUS100ORB915'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC.with_suffix('.ex5'), dest / 'orb915.ex5'); print('COMPILED', flush=True)


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
    case(b, 'MAIN', {}, 'all', 4)
    for k, v in SENS.items(): case(b, k, v, 'all', 4)
    for per in ('2023', '1y'): case(b, 'MAIN', {}, per, 4)
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
    T = trades('MAIN_M1'); days = len({t['open_time'][:10] for t in T}); weekdays = sum(1 for i in range((datetime.fromisoformat(END) - datetime.fromisoformat(PERIODS['all'])).days)
                                                                                      if (datetime.fromisoformat(PERIODS['all']) + timedelta(days=i)).weekday() < 5)
    f = len(T) / weekdays; rate = round(1 - (1 - f) ** (1 / BARS_PER_DAY), 5)       # P(at least one entry in 25 bars) = MAIN's entry frequency per weekday
    (H / 'RANDOM_RATE.json').write_text(json.dumps(dict(trades=len(T), entry_days=days, weekdays=weekdays, per_weekday=round(f, 4), rate=rate)), encoding='utf-8')
    print('random-entry rate per M15 bar', rate, flush=True)
    for s in SEEDS:
        case(b, f'RNDDIR{s}', dict(InpControl='1', InpSeed=str(s)), 'all', 1)
        case(b, f'RNDENT{s}', dict(InpControl='2', InpRandomRate=str(rate), InpSeed=str(s)), 'all', 1)
    print('CONTROLS DONE', flush=True)


def rows(key, per='all'):
    out = []; bal = DEP
    for t in trades(key, per):
        out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (RISK * bal), net=t['net_profit'], cost=abs(t['commission']) + max(0.0, -t['swap']))); bal += t['net_profit']
    return out


def stats(x, a, b):
    x = [r for r in x if a <= r['o'][:10] < b]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
    eq = pk = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    wins = [r['r'] for r in x if r['r'] > 0]; losses = [r['r'] for r in x if r['r'] < 0]
    over = sum(1 for r in x if r['c'][:10] != r['o'][:10])
    wk = sum(1 for r in x if any((datetime.fromisoformat(r['o'][:10]) + timedelta(days=i)).weekday() == 5 for i in range((datetime.fromisoformat(r['c'][:10]) - datetime.fromisoformat(r['o'][:10])).days + 1)))
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_day=round(len(x) / months / 21, 3), total_r=round(sum(r['r'] for r in x), 1),
                avg_r=round(sum(r['r'] for r in x) / max(1, len(x)), 3), pf=round(gw / gl, 2) if gl else None, win=round(100 * len(wins) / max(1, len(x)), 1),
                avg_win_r=round(sum(wins) / max(1, len(wins)), 3), avg_loss_r=round(sum(losses) / max(1, len(losses)), 3), closed_dd_r=round(dd, 1),
                worst_day_r=round(min(days.values()), 2) if days else None, overnight=over, weekend_held=wk)


def native(key, per):
    m = json.loads((H / 'native' / f'nw-{SYM}-{key}-{per}' / 'run.json').read_text())['metrics']
    return {k: m.get(k) for k in ('return_pct', 'profit_factor', 'max_drawdown_pct', 'history_quality', 'total_trades')}


def report():
    sp = data_split.research_split(PERIODS['all'], END)
    W = {'all': (PERIODS['all'], END), 'dev': (sp['development']['start'], sp['development']['end_exclusive']), 'val': (sp['validation']['start'], sp['validation']['end_exclusive']),
         'oos': (sp['oos']['start'], sp['oos']['end_exclusive']), 'since_2023': ('2023-01-01', END), 'last_12m': ('2025-11-17', END), '2026': ('2026-01-01', END),
         'last_2m': ('2026-09-17', END)}
    out = dict(windows=W, main_native={}, sens={}, controls={}, buy_hold={})
    for per in PERIODS:
        try: out['main_native'][per] = native('MAIN', per)
        except FileNotFoundError: pass
    A = rows('MAIN', 'all'); out['main_split'] = {w: stats(A, *v) for w, v in W.items()}
    out['main_years'] = {str(y): stats(A, f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else END) for y in range(2019, 2027)}
    out['summary_journal'] = re.findall(r'ORB_SUMMARY[^\r\n]*', gzip.open(H / f'native/nw-{SYM}-MAIN-all/journal.txt.gz').read().decode('utf-8', 'replace'))[:1]
    for k in SENS:
        try: out['sens'][k] = dict(all=stats(rows(k), *W['all']), oos=stats(rows(k), *W['oos']), dev=stats(rows(k), *W['dev']), native=native(k, 'all'))
        except FileNotFoundError: pass
    try:
        m1 = stats(rows('MAIN_M1'), *W['all']); rd = [stats(rows(f'RNDDIR{s}'), *W['all'])['total_r'] for s in SEEDS]; re_ = [stats(rows(f'RNDENT{s}'), *W['all'])['total_r'] for s in SEEDS]
        out['controls'] = dict(main_m1=m1, random_direction=dict(totals=rd, mean=round(sum(rd) / len(rd), 1), p=round((sum(1 for v in rd if v >= m1['total_r']) + 1) / (len(rd) + 1), 3)),
                               random_entry=dict(totals=re_, mean=round(sum(re_) / len(re_), 1), p=round((sum(1 for v in re_ if v >= m1['total_r']) + 1) / (len(re_) + 1), 3)))
    except FileNotFoundError: out['controls'] = 'not run'
    seq = [r['r'] for r in A]; tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
    out['mc'] = dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct'])
    j = gzip.open(H / f'native/nw-{SYM}-MAIN-all/journal.txt.gz').read().decode('utf-8', 'replace')
    ents = [l for l in j.splitlines() if 'ORB_ENTRY' in l and 'Core' in l]; costs = []
    for l, r in zip(ents, A):
        m = re.search(r'stop=([\d.]+) spread=([\d.]+)', l); spread_r = float(m.group(2)) / float(m.group(1)) if m and float(m.group(1)) > 0 else 0.0
        risk_usd = abs(r['net'] / r['r']) if r['r'] else 0.0
        costs.append(spread_r + (r['cost'] / risk_usd if risk_usd else 0.0))
    out['entry_log_lines'] = len(ents); out['cost_stress'] = robustness.cost_stress([r['r'] for r in A], costs) if len(costs) == len(A) else f'entry log mismatch {len(ents)} vs {len(A)}'
    for w in PERIODS:
        try: x = buy_hold.load(H, SYM, w); out['buy_hold'][w] = dict(ret=x['return_pct'], dd=x['max_dd_pct'])
        except Exception as e: out['buy_hold'][w] = repr(e)[:80]
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(11, 5))
        for k in ['MAIN'] + list(SENS):
            try:
                x = rows(k); eq = 0.0; xs = []; ys = []
                for r in x: eq += r['r']; xs.append(datetime.fromisoformat(r['c'][:19])); ys.append(eq)
                ax.plot(xs, ys, label=k, lw=2.2 if k == 'MAIN' else 1)
            except FileNotFoundError: pass
        for w in ('val', 'oos'): ax.axvline(datetime.fromisoformat(W[w][0]), color='grey', ls='--', lw=0.8)
        ax.set_title('US100 9:15 NY ORB (M15, 0.5R, EMA 200) - cumulative R, native Model 4'); ax.set_ylabel('R'); ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(H / 'balance.png', dpi=110)
    except Exception as e: print('plot failed', e)
    print(json.dumps({k: out[k] for k in ('main_native', 'main_split', 'sens', 'mc', 'cost_stress', 'buy_hold')}, indent=1, default=str)[:9000])


def reel():
    """Addendum 1: RETEST3 on the reel window only (2023-01-01 -> END)."""
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; compile_ea(b)
    case(b, 'RETEST3', dict(InpMaxTrades='3', InpRetest='1'), '2023', 4)
    print('REEL DONE', flush=True)


def vol():
    """Addendum 4: the volatility-filter prompt (no EMA, skip if range > 1.5 x ATR14 M15), reel window + all years."""
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; compile_ea(b)
    for per in ('2023', 'all'): case(b, 'VOL', dict(InpTrendEMA='0', InpAtrMult='1.5', InpAtrPeriod='14'), per, 4)
    print('VOL DONE', flush=True)


def reel_report():
    a, e = PERIODS['2023'], END; out = {}
    for k in ('MAIN', 'RETEST3'):
        x = rows(k, '2023'); out[k] = dict(native=native(k, '2023'), since_2023=stats(x, a, e), y2023=stats(x, '2023-01-01', '2024-01-01'), y2024=stats(x, '2024-01-01', '2025-01-01'),
                                          y2025=stats(x, '2025-01-01', '2026-01-01'), y2026=stats(x, '2026-01-01', e), last_12m=stats(x, '2025-11-17', e))
        per_day = defaultdict(int)
        for r in x: per_day[r['o'][:10]] += 1
        out[k]['trades_per_day_hist'] = {n: sum(1 for v in per_day.values() if v == n) for n in (1, 2, 3)}
        out[k]['by_trade_number'] = {}
        seen = defaultdict(int)
        for r in x:
            seen[r['o'][:10]] += 1; out[k]['by_trade_number'].setdefault(seen[r['o'][:10]], []).append(r['r'])
        out[k]['by_trade_number'] = {n: dict(trades=len(v), total_r=round(sum(v), 1), win=round(100 * sum(1 for q in v if q > 0) / len(v), 1), avg_r=round(sum(v) / len(v), 3)) for n, v in out[k]['by_trade_number'].items()}
    (H / 'REEL_RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'main': main, 'controls': controls, 'reel': reel, 'reel_report': reel_report, 'vol': vol}.get(sys.argv[1], report)()
