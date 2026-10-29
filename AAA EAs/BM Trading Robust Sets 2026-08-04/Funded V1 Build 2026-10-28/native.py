"""Native MT5 runs for the funded_v1 build. Reuses the audited No Wick Candle Raw 2026-09-25 harness (isolated tester only, one test at a
time, report-input checks, resumable) with the FIFO-fragment fix; guard inputs are proven from each journal's banner (MT5 reports list only
the strategy inputs).
  volconf  : ORB Volume Profile Volume Confirmed at 0.5R, original EX5, 5y, $10k 1:2000 (ledger for the simulation)
  parity   : original EX5 vs guarded EX5 in pass-through mode, 6m, $50k 1:30 -> identical trades
  guard    : guarded EX5, guard ON (defaults), 1y, $50k 1:30 -> audit.py
  harness  : the guard rule harness (harness/Funded Guard Harness.mq5)
python native.py volconf | parity | guard | harness
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
CURRENT = {}
_orig_inputs = b._report_inputs
b._report_inputs = lambda path: {**_orig_inputs(path), **{k: v for k, v in CURRENT.items() if k.startswith(('Funded', 'Harness'))}}
b.TESTER = PACKAGE / '_Backtests/MT5-DMC-20260811'; b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'
FULL = PACKAGE / '_00 Live profiles/Full EA portfolio - Recommended Adaptive'
END = '2026.10.27'; WINDOWS = {'6m': '2026.04.27', '1y': '2025.10.27', '5y': '2021.10.27'}
BASE = dict(isolated_tester='_Backtests/MT5-DMC-20260811', profile='Calyx Research Empty', login=472334559, server='Exness-MT5Trial16', currency='USD',
            model=4, execution_delay_ms=150, timeout_seconds=7200, end_date=END)


def read_set(p):
    out = {}
    for line in b.text(p).splitlines():
        if '=' in line and not line.startswith(';'): k, v = line.split('=', 1); out[k.strip()] = v.strip().split('||')[0]   # optimizer fields -> current value
    return out


def run(symbol, tf, tag, ex5, expert_dir, inputs, period, deposit, leverage):
    dest = b.TESTER / 'MQL5/Experts' / expert_dir; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(ex5, dest / ex5.name)
    CURRENT.clear(); CURRENT.update(inputs)
    b.CONFIG = dict(BASE, deposit=deposit, leverage=leverage, period=tf, periods={period: WINDOWS[period]}, expert_dir=expert_dir, expert_file=ex5.name,
                    common_inputs=inputs, variants={tag: dict(inputs={})}, controls={})
    return b.run_case(symbol, tag, period)


def package():
    pkg = PACKAGE / '_00 Live profiles/Packages/FundedV1'
    return pkg, json.loads((pkg / 'PACKAGE.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    stage = sys.argv[1]; b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running(): b.fail('Isolated research terminal is already running.')
    if stage == 'volconf':
        inp = read_set(FULL / 'Sets/05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set')
        inp.update(InpRewardRisk='0.5', InpRiskPercent='1.0', InpAdaptivePortfolioControls='false')
        run('XAUUSD', 'M5', 'volconf-05R', FULL / 'EAs/ORB Volume Data EA.ex5', 'AAA Research\\FundedV1 Original 20261028', inp, '5y', 10000, '1:2000')
    elif stage in ('parity', 'guard'):
        pkg, man = package(); only = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None   # optional slug filter
        for e in man['entries']:
            if only and e['slug'] not in only: continue
            guarded = read_set(pkg / 'package' / e['settings']); sym = 'USTEC' if e['symbol'] == 'USTEC' else 'XAUUSD'
            if stage == 'parity':
                orig = {k: v for k, v in guarded.items() if not k.startswith('Funded')}
                run(sym, e['timeframe'], f"{e['slug']}-orig", FULL / 'EAs' / Path(e['source_expert']).name, 'AAA Research\\FundedV1 Original 20261028', orig, '6m', 50000, '1:30')
                run(sym, e['timeframe'], f"{e['slug']}-pass", pkg / 'package' / e['expert'], 'AAA Research\\FundedV1 Guarded 20261028', dict(guarded, FundedGuardMode='0'), '6m', 50000, '1:30')
            else:
                run(sym, e['timeframe'], f"{e['slug']}-guard", pkg / 'package' / e['expert'], 'AAA Research\\FundedV1 Guarded 20261028', dict(guarded, FundedGuardMode='1'), '1y', 50000, '1:30')
    elif stage == 'harness':
        ex5 = ROOT / 'harness/Funded Guard Harness.ex5'
        run('XAUUSD', 'M15', 'harness', ex5, 'AAA Research\\FundedV1 Harness 20261028', dict(FundedGuardMode='1', FundedAccountSize='50000', HarnessMode='1'), '6m', 50000, '1:30')
        run('XAUUSD', 'M15', 'harness-loss', ex5, 'AAA Research\\FundedV1 Harness 20261028',
            dict(FundedGuardMode='1', FundedAccountSize='50000', HarnessMode='2', FundedMaxDailyWinPercent='0'), '6m', 50000, '1:30')
    b.status(event='STAGE DONE ' + stage)
