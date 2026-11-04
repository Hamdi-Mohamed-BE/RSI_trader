"""Out-of-sample windows + Monte Carlo source for XAU Weakness production vs market fill (owner 2026-11-03: "run monte carlo and out of
sample data"). Windows from the shared data_split.py planner (history 2019-01-01, end 2026-11-01 exclusive):
  dev 2019-01-01 -> 2023-11-01, val 2023-11-01 -> 2024-11-01, oos 2024-11-01 -> 2026-11-01, all 2019-01-01 -> 2026-11-01.
Each window is a separate native run from a fresh $10k; same EX5s, inputs and settings as run.py. The OOS window was already viewed
inside the 5y comparison (previously seen, not untouched). Run from AAA EAs/EA store:  uv run python "<study>/run_split.py"
"""
import importlib.util, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('mf', ROOT / 'run.py'); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r); b = r.b
sys.path.insert(0, str(ROOT.parent.parent / 'Calyx Research Pipeline')); import data_split  # noqa: E402

SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']),
           'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
           'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']),
           'all': (SPLIT['development']['start'], SPLIT['oos']['end_exclusive'])}
assert WINDOWS['oos'] == ('2024-11-01', '2026-11-01') and WINDOWS['dev'][0] == '2019-01-01'
dot = lambda s: s.replace('-', '.')  # noqa: E731
b.CONFIG['periods'] = {k: dot(a) for k, (a, _) in WINDOWS.items()}

if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    (ROOT / 'SPLIT.json').write_text(json.dumps(dict(split=SPLIT, windows=WINDOWS), indent=1), encoding='utf-8')
    for period in ('oos', 'val', 'dev', 'all'):
        for tag in ('PROD', 'ON'):
            ex5 = r.PROD if tag == 'PROD' else r.RESEARCH; name = f'xau-weakness-{tag.lower()}.ex5'; shutil.copy2(ex5, dest / name)
            extra = {} if tag == 'PROD' else {'InpWeaknessMarketIfPast': 'true'}
            b.CONFIG['variants'][tag] = {'label': f'XAU Weakness {tag}', 'inputs': extra}
            b.CONFIG['common_inputs'] = r.INPUTS; b.CONFIG['expert_file'] = name; b.CONFIG['end_date'] = dot(WINDOWS[period][1])
            try:
                b.run_case('XAUUSD', tag, period)
            except SystemExit:
                print('CASE FAILED', tag, period, flush=True)
    print('ALL DONE', flush=True)
