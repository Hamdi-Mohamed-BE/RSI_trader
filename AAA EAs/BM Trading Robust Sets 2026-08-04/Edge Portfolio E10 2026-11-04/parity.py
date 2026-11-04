"""Native parity of the Edge 10 package (owner 2026-11-04 build): each wrapped EX5 (_00 Live profiles/Packages/Edge10, RiskSupport at
its default 0.5% of equity -> multiplier 1) vs the untouched production EX5 with the same strategy inputs and InpRiskPercent 0.5.
Model 4, $10k, 150 ms, 2026-05-01 -> 2026-11-01 (real ticks). Trade lists must match (open time, side, volume, net). -> PARITY.json
Run from AAA EAs/EA store:  uv run python "<this>" """
import gzip, importlib.util, json, os, shutil
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PKG = H.parent / '_00 Live profiles/Packages/Edge10'
spec = importlib.util.spec_from_file_location('octrun', H.parent / 'Portfolio October 2026 ATR6 2026-11-03/run.py')
o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
b.ROOT = H; b.OUT = H / 'parity-native'; b.STATUS = b.OUT / 'status.json'
b.CONFIG.update(periods={'6m': '2026.05.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxEdge10Parity20261104', controls={}, variants={})
TF = {1: 'M1', 5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
PORTFOLIO = {'InpPortfolioRiskMode', 'InpPortfolioPercent', 'InpPortfolioFixedUSD', 'InpPortfolioExpectedLogin', 'InpPortfolioExpectedServer',
             'InpPortfolioExpectedSymbol', 'InpPortfolioInstallNonce'}


def trades(case):
    T = json.loads(gzip.open(b.OUT / case / 'trades.json.gz').read())
    return [(t['open_time'], t['side'], t['volume'], t['net_profit']) for t in sorted(T, key=lambda t: (t['open_time'], t['side']))]


if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True); dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    pkg = json.loads((PKG / 'Package.json').read_text(encoding='utf-8')); out = {}
    for e in pkg['entries']:
        wrap, prod = f"wrap-{e['key']}.ex5", f"prod-{e['key']}.ex5"
        shutil.copy2(PKG / e['expert'], dest / wrap); shutil.copy2(Path(e['production_source']).with_suffix('.ex5'), dest / prod)
        sym = {'USTEC': 'USTEC', 'XAUUSD': 'XAUUSD', 'USDJPY': 'USDJPY'}[e['canonical']]
        b.CONFIG['period'] = TF[e['period']]
        res = {}
        for tag, ex5, inputs in (('WRAP', wrap, dict(e['inputs'])), ('PROD', prod, {k: v for k, v in e['inputs'].items() if k not in PORTFOLIO})):
            b.CONFIG['variants'][tag] = {'label': f"{e['key']} {tag}", 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = ex5
            name = f"{e['key']}-{tag}"; b.CONFIG['variants'][name] = b.CONFIG['variants'].pop(tag)
            try:
                b.run_case(sym, name, '6m'); res[tag] = trades(f'nw-{sym}-{name}-6m')
            except SystemExit:
                res[tag] = None; print('CASE FAILED', name, flush=True)
        out[e['key']] = dict(trades=len(res['PROD'] or []), identical=res['WRAP'] is not None and res['WRAP'] == res['PROD'],
                             wrap_net=round(sum(t[3] for t in res['WRAP'] or []), 2), prod_net=round(sum(t[3] for t in res['PROD'] or []), 2))
        print('PARITY', e['key'], out[e['key']], flush=True)
        (H / 'PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('ALL DONE', flush=True)
