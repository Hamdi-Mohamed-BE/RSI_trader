"""Owner 2026-11-11: UK100 Monday dip (S2, unchanged raw EA and inputs) over the last two months, native Model 4, 2026-09-11 -> 2026-11-11 excl.."""
import gzip, json, sys
from pathlib import Path
sys.argv = [sys.argv[0], 'noop']
import importlib.util
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ftse_run', H / 'run.py'); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
b = R.b
assert not b.isolated_running(), 'Tester is occupied'
b.CONFIG['model'] = 4; b.CONFIG['end_date'] = '2026.11.11'
for per, start in (('2m', '2026.09.11'),):
    b.CONFIG['periods'] = {per: start}
    b.run_case('UK100', 'S2', per)
for per in ('2m',):
    T = json.loads(gzip.open(H / 'native' / f'nw-UK100-S2-{per}' / 'trades.json.gz').read())
    print(per, len(T), [(t['open_time'][:16], t['close_time'][:16], t['side'], round(t['net_profit'], 2), t.get('exit_comment')) for t in T])
