"""Native parity for BEST1STEP-20261118 (no-guard package, Packages/Best1Step). Model 4, 150 ms, $10k, 1%, 2026-08-16 -> 2026-11-16 (real ticks), each EA alone.
  asia-breakout: OLD = production AAA Final Asia Breakout EX5 with the Full EA inputs (InpRiskPercent 1, adaptive off) vs NEW = the new RiskSupport + CNO wrapper
                 (InpPortfolioPercent 1.0, InpRiskPercent 0.5 calibration), no-opposite OFF, news block OFF -> must be identical.
  nasdaq-5m-candle-momentum, overnight-bias-orb: NEW (recompiled with CNO v2) vs the 2026-11-17 OFF runs in ../../Calyx No Opposite/parity/native -> must be identical.
  NEWSON: the new Asia wrapper with InpCalyxNewsBlock=true and no Calyx News Guard running (no CNB_ variables) -> must equal NEW.
The Nasdaq 0.75x factor is an installer input change only (InpPortfolioPercent), not tested natively here. python parity.py run | report"""
import gzip, importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; L = H.parents[1]; B = L.parent; PKG = L / 'Packages/Best1Step'; CNO = L / 'Calyx No Opposite/parity/native'
START, END = '2026-08-16', '2026-11-16'
TF = {5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
ASIA_EX5 = B / 'AAA Final EAs/AAA Final Asia Breakout EA/AAA Final Asia Breakout EA.ex5'


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def entry(key): return next(e for e in json.loads((PKG / 'Package.json').read_text(encoding='utf-8-sig'))['entries'] if e['key'] == key)


def cases():
    a = entry('asia-breakout'); new = dict(a['inputs'], InpPortfolioPercent='1.0', InpCalyxNoOpposite='false', InpCalyxNewsBlock='false')
    full = json.loads((B / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8'))
    old = {k: str(v) for k, v in next(i for i in full if i['label'] == 'AAA Final Asia Breakout')['inputs'].items()}; old['InpAdaptivePortfolioControls'] = 'false'
    yield a, 'OLD', ASIA_EX5, old
    yield a, 'NEW', PKG / a['expert'], new
    yield a, 'NEWSON', PKG / a['expert'], dict(new, InpCalyxNewsBlock='true')
    for k in ('nasdaq-5m-candle-momentum', 'overnight-bias-orb'):
        e = entry(k); yield e, 'NEW', PKG / e['expert'], dict(e['inputs'], InpPortfolioPercent='1.0', InpCalyxNoOpposite='false', InpCalyxNewsBlock='false')


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; dest = b.TESTER / 'MQL5/Experts/CalyxB10Parity'; dest.mkdir(parents=True, exist_ok=True)
    for e, tag, ex5, inp in cases():
        name = f"{e['key']}-{tag}"; final = H / 'native' / f'nw-{name}'
        if (final / 'trades.json.gz').exists(): continue
        fn = f'{name}.ex5'; shutil.copy2(ex5, dest / fn)
        b.CONFIG.update(model=4, end_date=END.replace('-', '.'), periods={'p': START.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                        timeout_seconds=7200, period=TF[int(e['period'])], expert_dir='CalyxB10Parity', expert_file=fn, controls={}, common_inputs={}, variants={name: {'label': name, 'inputs': inp}})
        try: b.run_case(e['canonical'], name, 'p')
        except SystemExit as x: print('run_case exit', x)
        src = H / 'native' / f"nw-{e['canonical']}-{name}-p"
        if src.exists(): shutil.move(str(src), str(final))
        print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


def key(t): return (t['open_time'][:19], t['side'], round(t['volume'], 4), t['close_time'][:19], round(t['net_profit'], 2))


def load(p): return [key(t) for t in sorted(json.loads(gzip.open(p).read()), key=lambda t: (t['open_time'], t['close_time']))] if p.exists() else None


def report():
    T = {f"{e['key']}-{tag}": load(H / 'native' / f"nw-{e['key']}-{tag}" / 'trades.json.gz') for e, tag, _, _ in cases()}
    for k in ('nasdaq-5m-candle-momentum', 'overnight-bias-orb'): T[f'{k}-PREV_OFF'] = load(CNO / f'nw-{k}-OFF' / 'trades.json.gz')
    out = {k: (dict(trades=len(v), net=round(sum(x[4] for x in v), 2)) if v is not None else None) for k, v in T.items()}
    out['asia NEW == OLD'] = T['asia-breakout-NEW'] is not None and T['asia-breakout-NEW'] == T['asia-breakout-OLD']
    out['asia NEWSON == NEW'] = T['asia-breakout-NEWSON'] is not None and T['asia-breakout-NEWSON'] == T['asia-breakout-NEW']
    for k in ('nasdaq-5m-candle-momentum', 'overnight-bias-orb'): out[f'{k} NEW == 11-17 OFF'] = T[f'{k}-NEW'] is not None and T[f'{k}-NEW'] == T[f'{k}-PREV_OFF']
    (H / 'PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
