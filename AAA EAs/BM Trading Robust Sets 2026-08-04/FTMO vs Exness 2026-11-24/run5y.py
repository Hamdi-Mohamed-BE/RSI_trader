"""FTMO vs Exness, 5-year pass-rate rerun (owner 2026-11-24: "run the overall full simulation test and show me pass rate, does it change or stay the same?").
Same Best 1-Step no-guard package EX5s + inputs as compare2m.py, each EA alone, $100k (lot rounding small), 1% of balance, 150 ms, native MODEL 1 (1-minute OHLC) on BOTH feeds:
FTMO custom symbols only have M1 bars before 2026-09-21, so Exness is run on the same model for a like-for-like price-feed comparison.
Test 2021-08-01 -> 2026-10-07 (warm-up before the sim window 2021-10-07 -> 2026-10-06, the window of INPUTS_N75). Run from AAA EAs/EA store: uv run python "<this>" run"""
import importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c2m', H / 'compare2m.py'); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
START, END = '2021.08.01', '2026.10.07'
OUT = H / 'native5y'


def run():
    b = C.harness(); b.OUT = OUT; b.STATUS = OUT / 'status.json'; OUT.mkdir(exist_ok=True)
    assert not b.isolated_running(), 'Tester is occupied'; dest = b.TESTER / 'MQL5/Experts/CalyxFTMOvsExness'; dest.mkdir(parents=True, exist_ok=True)
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    for e in C.entries():
        if only and e['key'] not in only: continue
        for feed in ('EXNESS', 'FTMO'):
            sym = e['canonical'] if feed == 'EXNESS' else C.FTMO[e['canonical']]
            name = f"{e['key']}-{feed}"; final = OUT / f'nw-{name}'
            if (final / 'trades.json.gz').exists(): continue
            fn = f"{e['key']}.ex5"; shutil.copy2(C.PKG / e['expert'], dest / fn)
            inp = dict(e['inputs'], InpPortfolioPercent='1.0', InpCalyxNoOpposite='false', InpCalyxNewsBlock='false')
            b.CONFIG.update(model=1, end_date=END, periods={'y': START}, deposit=100000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                            timeout_seconds=14400, period=C.TF[int(e['period'])], expert_dir='CalyxFTMOvsExness', expert_file=fn, controls={}, common_inputs={},
                            variants={name: {'label': name, 'inputs': inp}})
            try: b.run_case(sym, name, 'y')
            except SystemExit as x: print('run_case exit', x, flush=True)
            src = OUT / f'nw-{sym}-{name}-y'
            if src.exists(): shutil.move(str(src), str(final))
            print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


if __name__ == '__main__':
    {'run': run}[sys.argv[1]]()
