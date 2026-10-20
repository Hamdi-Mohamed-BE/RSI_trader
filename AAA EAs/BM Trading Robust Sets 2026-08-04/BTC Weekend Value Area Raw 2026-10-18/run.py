"""BTC weekend value-area raw study. Reuses the audited No Wick Candle Raw 2026-09-25 harness unchanged
(isolated tester only, one test at a time, report-input checks, resumable).

python run.py compile | smoke | main | control
"""
import gzip, importlib.util, inspect, json, os, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

# Recombine FIFO fragments by exit deal (same fix as Recent EA Shortlist 2026-09-30).
code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


def closing_deals(path, label):
    grouped = {}
    for t in scope['_native_trades'](path, label):
        g = grouped.get(t['exit_deal'])
        if g is None:
            grouped[t['exit_deal']] = dict(t); continue
        for f in ('volume', 'gross_profit', 'commission', 'swap', 'total_costs', 'net_profit'):
            g[f] += t[f]
        g['open_time'] = min(g['open_time'], t['open_time'])
    out = list(grouped.values())
    for i, t in enumerate(out):
        t['number'] = i + 1; t['result'] = 'Win' if t['net_profit'] > 0 else 'Loss' if t['net_profit'] < 0 else 'Flat'
    return out


b._native_trades = closing_deals
b.CONFIG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
b.TESTER = PACKAGE / b.CONFIG['isolated_tester']
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'

if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['periods'] = {'smoke': '2026.09.01'}
        b.run_case('BTCUSD', 'WVA', 'smoke')
    elif stage == 'main':
        b.main_grid()
    elif stage == 'control':
        b.control_grid()
    b.status(event='STAGE DONE ' + stage)
