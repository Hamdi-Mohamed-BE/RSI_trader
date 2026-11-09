"""Core 9 guarded builds hold the Sell Nasdaq stop in the EA and sell at market (see ../build.py). This compares that change with production: same inputs, no guard, native Model 4, 150 ms, $10k, 1%,
2021-10-07 -> 2026-11-01. Declared before running: PASS needs >= 98% of production trade days also traded, and net profit within 10% of production. Entry slippage and R are reported per trade.
The tester is used one job at a time; run it only when no other tester job is running.
Run from AAA EAs/EA store: uv run python "<this>" native, then uv run python "<this>" report -> PARITY.json"""
import gzip, importlib.util, json, shutil, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent; LIVE = H.parents[1]; PACKAGE = LIVE.parent
EDGE = json.loads((LIVE / 'Packages/Edge10/Package.json').read_text(encoding='utf-8-sig')); E = next(x for x in EDGE['entries'] if x['key'] == 'sell-nasdaq-15min')
CASES = {'PROD': Path(E['production_source']).with_suffix('.ex5'), 'HELD': H / 'Sell Nasdaq Held Stop EA.ex5'}


def native():
    spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py'); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    inputs = {k: str(v) for k, v in E['inputs'].items()}; inputs['InpRiskPercent'] = '1.0'
    b.CONFIG.update(periods={'5y': '2021.10.07'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxCore9Parity', controls={}, variants={}, common_inputs=inputs, period='M15')
    dest = b.TESTER / 'MQL5/Experts/CalyxCore9Parity'; dest.mkdir(parents=True, exist_ok=True)
    for key, ex5 in CASES.items():
        name = f'{key}.ex5'; shutil.copy2(ex5, dest / name); b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['expert_file'] = name
        for attempt in range(4):
            try:
                b.run_case(E['canonical'], key, '5y'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
    print('ALL DONE', flush=True)


def report():
    T = {k: json.loads(gzip.open(H / 'native' / f"nw-{E['canonical']}-{k}-5y" / 'trades.json.gz').read()) for k in CASES}
    day = lambda x: x['open_time'][:10]; P = {day(x): x for x in T['PROD']}; Q = {day(x): x for x in T['HELD']}; both = sorted(set(P) & set(Q))  # noqa: E731
    slip = sorted(P[d]['open_price'] - Q[d]['open_price'] for d in both); net = {k: round(sum(x['net_profit'] for x in v), 2) for k, v in T.items()}
    share = len(both) / max(1, len(P)); close = abs(net['HELD'] - net['PROD']) <= 0.10 * abs(net['PROD'])
    out = dict(trades={k: len(v) for k, v in T.items()}, net=net, same_days=len(both), only_prod=sorted(set(P) - set(Q)), only_held=sorted(set(Q) - set(P)), shared_share=round(share, 4), entry_price_diff_median=slip[len(slip) // 2] if slip else None, entry_price_diff_max=max(map(abs, slip)) if slip else None, verdict='PASS' if share >= .98 and close else 'FAIL')
    (H / 'PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    native() if sys.argv[1] == 'native' else report()
