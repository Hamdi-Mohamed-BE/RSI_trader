"""Owner 2026-11-04: "the usdjpy bot does not trade monday and tuesday ... why and what happens if we trade them, show me the data".
Same production EX5, preset, windows and harness as run.py; only InpTradeMonday / InpTradeTuesday = true (ALL5). Positions close at
16:00 London the same day, so days never overlap: the ALL5 ledger split by weekday shows each day's own trades.
Run from AAA EAs/EA store:  uv run python "<study>/run_days.py" """
import importlib.util, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ujrun', ROOT / 'run.py'); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r); b = r.b

if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(r.PROD, dest / 'usdjpy-london.ex5')
    b.CONFIG['variants']['ALL5'] = {'label': 'USDJPY London Mon-Fri', 'inputs': {'InpTradeMonday': 'true', 'InpTradeTuesday': 'true'}}
    b.CONFIG['common_inputs'] = r.INPUTS; b.CONFIG['expert_file'] = 'usdjpy-london.ex5'
    for period in ('oos', 'val', 'dev', 'all'):
        b.CONFIG['end_date'] = r.dot(r.WINDOWS[period][1])
        try:
            b.run_case('USDJPY', 'ALL5', period)
        except SystemExit:
            print('CASE FAILED', period, flush=True)
    print('ALL DONE', flush=True)
