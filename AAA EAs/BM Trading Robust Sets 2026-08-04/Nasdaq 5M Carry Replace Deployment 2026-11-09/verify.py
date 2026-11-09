"""Native proof for the deployment (owner rule: one tester job at a time). Run from AAA EAs/EA store: uv run python "<this>" production | edge10
production: the new production EX5 with the Edge 10 inputs, DI OFF and NO InpCarryMode in the SET (so its default is used), 2019-07-16 -> 2026-11-10, Model 4,
            must equal the tested REPLACE ledger of Nasdaq 5M Carry Fix 2026-11-09 trade for trade. Same with DI ON vs REPLACE_DION.
edge10:     the rebuilt Edge 10 wrapper vs the new production EX5 on 2026-05-01 -> 2026-11-10 (the package's own 6-month parity window), DI OFF."""
import gzip, importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent
spec = importlib.util.spec_from_file_location('carry', B / 'Nasdaq 5M Carry Fix 2026-11-09/carry.py'); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
NEW_EX5 = H / 'EA/Nasdaq 5M DI Wide ATR EA.ex5'
key = lambda T: [(t['open_time'], t['close_time'], t['side'], t['volume'], t['net_profit']) for t in sorted(T, key=lambda t: t['open_time'])]  # noqa: E731


def harness(out):
    b = C.harness(); b.ROOT = H; b.OUT = H / out; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'; return b


def production():
    b = harness('native'); res = {}
    for di, ref in ((False, 'REPLACE'), (True, 'REPLACE_DION')):
        C.setup(b, di); dest = b.TESTER / 'MQL5/Experts/CalyxCarry'; shutil.copy2(NEW_EX5, dest / 'deployed.ex5')
        name = 'DEPLOYED' + ('_DION' if di else ''); C.run(b, name, {}, 'deployed.ex5')
        mine = json.loads(gzip.open(H / 'native' / f'nw-USTEC-{name}-all' / 'trades.json.gz').read()); tested = C.ledger(ref)
        res[name] = dict(trades=len(mine), tested=len(tested), identical=key(mine) == key(tested)); print(name, res[name], flush=True)
    (H / 'VERIFY_PRODUCTION.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); assert all(v['identical'] for v in res.values()), 'deployed EX5 differs from the tested REPLACE'


def edge10():
    b = harness('native-edge10'); C.setup(b, False); dest = b.TESTER / 'MQL5/Experts/CalyxCarry'
    pkg = B / '_00 Live profiles/Packages/Edge10'; m = json.loads((pkg / 'Package.json').read_text(encoding='utf-8-sig')); e = next(x for x in m['entries'] if x['key'] == 'nasdaq-5m-candle-momentum')
    shutil.copy2(pkg / e['expert'], dest / 'edge10.ex5'); shutil.copy2(NEW_EX5, dest / 'deployed.ex5')
    wrap = {k: str(v) for k, v in e['inputs'].items()}; wrap.update(InpRequireDIAgreement='false', InpPortfolioRiskMode='0', InpPortfolioPercent='1.0')
    prod = C.edge_inputs(False)
    b.CONFIG['periods'] = {'6m': '2026.05.01'}; b.CONFIG['end_date'] = '2026.11.10'
    for name, ex, inputs in (('EDGE10', 'edge10.ex5', wrap), ('PROD6M', 'deployed.ex5', prod)):
        b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = ex; b.CONFIG['variants'][name] = {'label': name, 'inputs': {}}; b.run_case('USTEC', name, '6m')
    T = {n: json.loads(gzip.open(H / 'native-edge10' / f'nw-USTEC-{n}-6m' / 'trades.json.gz').read()) for n in ('EDGE10', 'PROD6M')}
    sig = lambda T: [(t['open_time'], t['close_time'], t['side']) for t in sorted(T, key=lambda t: t['open_time'])]  # noqa: E731
    res = dict(trades={n: len(v) for n, v in T.items()}, same_signals=sig(T['EDGE10']) == sig(T['PROD6M']), net={n: round(sum(t['net_profit'] for t in v), 2) for n, v in T.items()})
    (H / 'VERIFY_EDGE10.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print(res, flush=True); assert res['same_signals']


if __name__ == '__main__':
    {'production': production, 'edge10': edge10}[sys.argv[1]]()
