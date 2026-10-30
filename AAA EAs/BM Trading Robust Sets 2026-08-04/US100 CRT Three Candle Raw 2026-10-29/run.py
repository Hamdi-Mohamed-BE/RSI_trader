"""US100 CRT three-candle raw study. Runner copied from the Gold 1am NY ORB raw study: reuses the audited No Wick Candle Raw 2026-09-25
harness unchanged (isolated tester only, one test at a time, report-input checks, resumable) with the FIFO-fragment fix.

python run.py compile | smoke | grid | controls | confirm
  grid / controls (RND, S_*) = Model 1 fast screen on 5y; confirm = Model 4 (MAIN_M4 on 6m/1y/3y/5y, SIMPLE_M4 on 5y)
"""
import gzip, importlib.util, inspect, json, os, re, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

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


CFG_PATH = ROOT / 'run-config.json'
b._native_trades = closing_deals
b.CONFIG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
b.TESTER = PACKAGE / b.CONFIG['isolated_tester']
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'
SYM = 'USTEC'


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['model'] = 4; b.CONFIG['periods'] = {'smoke': '2026.10.01'}
        b.run_case(SYM, 'MAIN_M4', 'smoke')
    elif stage == 'grid':
        b.CONFIG['model'] = 1
        for v in b.CONFIG['variants']:
            b.run_case(SYM, v, '5y')
    elif stage == 'controls':
        b.CONFIG['model'] = 1
        for v in ('RND1', 'RND2', 'RND3', 'S_MON', 'S_ASIA', 'S_TWO', 'S_R13'):
            b.run_case(SYM, v, '5y')
    elif stage == 'confirm':
        b.CONFIG['model'] = 4
        for per in ('6m', '1y', '3y', '5y'):
            b.run_case(SYM, 'MAIN_M4', per)
        b.run_case(SYM, 'SIMPLE_M4', '5y')
    elif stage == 'm4more':                       # Addendum 1: Model 4 controls and per-timeframe versions (5y)
        b.CONFIG['model'] = 4
        for v in ('RND1_M4', 'RND2_M4', 'RND3_M4', 'M15_R_B_M4', 'M30_R_B_M4', 'H1_R_B_M4'):
            b.run_case(SYM, v, '5y')
    b.status(event='STAGE DONE ' + stage)
