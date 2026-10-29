"""Native tests of the Turbo5 package. Reuses the audited No Wick Candle Raw 2026-09-25 harness (isolated tester only, one test at a time,
report-input checks, resumable) with the FIFO-fragment fix. $50,000 USD, 1:30 (Turbo leverage), Model 4, 150 ms.
  parity : original EX5 vs guarded EX5 in pass-through mode (TurboGuardMode=0), 6m -> trades must be identical (wrapper fidelity)
  guard  : guarded EX5, TurboGuardMode=1, TurboTesterRewards=true, 1y -> journal audit (audit.py)
python native_tests.py parity | guard
"""
import importlib.util, inspect, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent; PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


def closing_deals(path, label):
    grouped = {}
    for t in scope['_native_trades'](path, label):
        g = grouped.get(t['exit_deal'])
        if g is None: grouped[t['exit_deal']] = dict(t); continue
        for f in ('volume', 'gross_profit', 'commission', 'swap', 'total_costs', 'net_profit'): g[f] += t[f]
        g['open_time'] = min(g['open_time'], t['open_time'])
    out = list(grouped.values())
    for i, t in enumerate(out): t['number'] = i + 1; t['result'] = 'Win' if t['net_profit'] > 0 else 'Loss' if t['net_profit'] < 0 else 'Flat'
    return out


b._native_trades = closing_deals
# MT5's HTML report lists only the strategy inputs, not the included guard's inputs. The strategy inputs stay fully checked; the guard
# inputs are taken from the SET, and audit.py proves the applied guard mode from each journal's TURBO banner.
CURRENT = {}
_orig_inputs = b._report_inputs
b._report_inputs = lambda path: {**_orig_inputs(path), **{k: v for k, v in CURRENT.items() if k.startswith('Turbo')}}
PKG = PACKAGE / '_00 Live profiles/Packages/Turbo5'; MAN = json.loads((PKG / 'PACKAGE.json').read_text(encoding='utf-8'))
FULL = PACKAGE / '_00 Live profiles/Full EA portfolio - Recommended Adaptive'
b.TESTER = PACKAGE / '_Backtests/MT5-DMC-20260811'; b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'
END = '2026.10.27'; WINDOWS = {'6m': '2026.04.27', '1y': '2025.10.27'}
GUARD_KEYS = [k for k in ('TurboGuardMode', 'TurboAccountSize', 'TurboExpectedLogin', 'TurboExpectedServer', 'TurboExpectedSymbol', 'TurboExpectedCurrency', 'TurboReferenceBalance',
                          'TurboStartUtcTime', 'TurboKnownFloor', 'TurboRebaseOnWithdrawal', 'TurboTrailEquity', 'TurboTesterRewards')]
BASE_CFG = dict(isolated_tester='_Backtests/MT5-DMC-20260811', profile='Calyx Research Empty', login=472334559, server='Exness-MT5Trial16', deposit=50000, currency='USD',
                leverage='1:30', model=4, execution_delay_ms=150, timeout_seconds=7200, end_date=END)


def read_set(p):
    out = {}
    for line in b.text(p).splitlines():
        if '=' in line and not line.startswith(';'): k, v = line.split('=', 1); out[k.strip()] = v.strip()
    return out


def configure(entry, mode, period):
    tf = entry['timeframe']
    guarded = read_set(PKG / 'package' / entry['settings'])
    if mode == 'orig':
        ex5 = FULL / f"EAs/{Path(entry['source_expert']).name}"
        inputs = {k: v for k, v in guarded.items() if k not in GUARD_KEYS}
        expert_dir, expert_file = 'AAA Research\\Turbo5 Original 20261027', ex5.name
    else:
        ex5 = PKG / 'package' / entry['expert']
        inputs = dict(guarded, TurboGuardMode='0' if mode == 'pass' else '1', TurboTesterRewards='true' if mode == 'guard' else 'false')
        expert_dir, expert_file = 'AAA Research\\Turbo5 Guarded 20261027', entry['expert']
    dest = b.TESTER / 'MQL5/Experts' / expert_dir; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(ex5, dest / expert_file)
    tag = f"{entry['slug']}-{mode}"
    CURRENT.clear(); CURRENT.update(inputs)
    b.CONFIG = dict(BASE_CFG, period=tf, periods={period: WINDOWS[period]}, expert_dir=expert_dir, expert_file=expert_file,
                    common_inputs=inputs, variants={tag: dict(inputs={})}, controls={})
    return tag


def run(mode, period):
    out = []
    for e in MAN['entries']:
        tag = configure(e, mode, period)
        meta = b.run_case({'XAUUSD': 'XAUUSD', 'USTEC': 'USTEC'}[e['symbol']], tag, period); out.append(meta)
    return out


if __name__ == '__main__':
    stage = sys.argv[1]; b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running(): b.fail('Isolated research terminal is already running.')
    if stage == 'parity':
        run('orig', '6m'); run('pass', '6m')
    elif stage == 'orig':
        run('orig', '6m')
    elif stage == 'guard':
        run('guard', '1y')
    elif stage == 'harness':
        ex5 = ROOT / 'harness/Turbo Guard Harness.ex5'; d = 'AAA Research\Turbo Guard Harness 20261027'
        dest = b.TESTER / 'MQL5/Experts' / d; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(ex5, dest / ex5.name)
        inputs = dict(TurboGuardMode='1', TurboAccountSize='50000', TurboTesterRewards='false'); CURRENT.clear(); CURRENT.update(inputs)
        b.CONFIG = dict(BASE_CFG, period='M15', end_date='2026.10.08', periods={'h': '2026.10.06'}, expert_dir=d, expert_file=ex5.name,
                        common_inputs=inputs, variants={'harness': dict(inputs={})}, controls={})
        b.run_case('XAUUSD', 'harness', 'h')
    b.status(event='STAGE DONE ' + stage)
