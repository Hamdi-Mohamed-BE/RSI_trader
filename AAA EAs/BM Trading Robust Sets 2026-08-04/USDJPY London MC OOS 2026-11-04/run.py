"""USDJPY London Open Momentum: out-of-sample windows + Monte Carlo source (owner 2026-11-04: "run the monte carlo and out of sample
test on the USDJPY london EA we have and show me its full breakdown"). Production EX5 + the Full EA preset inputs (FULL_ITEMS.json of the
October study: London 08:00, 60-min formation, Wed-Fri, ADX20 + DI, 5 ATR stop, BE at 0.75R, 16:00 London time exit), risk 1%,
adaptive governor off. Native MT5 Model 4, $10k fresh per window, 150 ms, M15.
Windows from the shared data_split.py planner (history 2019-01-01, end 2026-11-01 exclusive):
  dev 2019-01-01 -> 2023-11-01, val 2023-11-01 -> 2024-11-01, oos 2024-11-01 -> 2026-11-01, all 2019-01-01 -> 2026-11-01.
The settings were chosen after viewing most of this history (ADX DI study 2026-10-03, NY-exit study 2026-10-21): the OOS window is
previously seen, not untouched. Run from AAA EAs/EA store:  uv run python "<study>/run.py"
"""
import importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent; PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py')
o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
sys.path.insert(0, str(PACKAGE.parent / 'Calyx Research Pipeline')); import data_split  # noqa: E402
SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']),
           'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
           'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']),
           'all': (SPLIT['development']['start'], SPLIT['oos']['end_exclusive'])}
assert WINDOWS['oos'] == ('2024-11-01', '2026-11-01') and WINDOWS['dev'] == ('2019-01-01', '2023-11-01')
dot = lambda s: s.replace('-', '.')  # noqa: E731
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.CONFIG.update(periods={k: dot(a) for k, (a, _) in WINDOWS.items()}, deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxUsdJpyLondonMC20261104', controls={}, variants={}, period='M15')
item = next(i for i in json.loads((PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8-sig'))
            if i['label'] == 'USDJPY London Open Momentum')
PROD = Path(item['expert_path']); assert int(item['period']) == 15 and PROD.exists()
INPUTS = {k: str(v) for k, v in item['inputs'].items()}
INPUTS['InpRiskPercent'] = '1.0'; INPUTS['InpAdaptivePortfolioControls'] = 'false'
assert INPUTS['InpExitLondonHour'] == '16.0' and INPUTS['InpRequireDIAgreement'] == 'true' and INPUTS['InpTargetMode'] == '0'

if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROD, dest / 'usdjpy-london.ex5')
    (ROOT / 'PLAN.json').write_text(json.dumps(dict(prod_ex5=str(PROD), prod_sha=b.sha(PROD), set_path=item['set_path'], inputs=INPUTS,
                                                    split=SPLIT, windows=WINDOWS), indent=1), encoding='utf-8')
    b.CONFIG['variants']['PROD'] = {'label': 'USDJPY London PROD', 'inputs': {}}
    b.CONFIG['common_inputs'] = INPUTS; b.CONFIG['expert_file'] = 'usdjpy-london.ex5'
    for period in ('oos', 'val', 'dev', 'all'):
        b.CONFIG['end_date'] = dot(WINDOWS[period][1])
        try:
            b.run_case('USDJPY', 'PROD', period)
        except SystemExit:
            print('CASE FAILED', period, flush=True)
    print('ALL DONE', flush=True)
