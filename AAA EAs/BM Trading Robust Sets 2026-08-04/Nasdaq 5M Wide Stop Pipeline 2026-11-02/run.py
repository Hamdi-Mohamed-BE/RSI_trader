"""Nasdaq 5M wide-stop optimisation (PLAN.md). Production EX5 + preset, inputs only, native MT5 via the audited No Wick harness
(isolated tester only, report/input checks, FIFO fix). Model 1 search over 2019-01-01 -> 2026-11-01; Model 4 confirmation.
Run from AAA EAs/EA store:  uv run python "../BM Trading Robust Sets 2026-08-04/Nasdaq 5M Wide Stop Pipeline 2026-11-02/run.py" search|confirm
"""
import gzip, importlib.util, inspect, json, os, shutil, sys, hashlib
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


EX5 = PACKAGE / 'Nasdaq 5M DI ATR Deployment 2026-09-28' / 'EA' / 'Nasdaq 5M DI Wide ATR EA.ex5'
BASE = json.loads((PACKAGE / 'October 2026 EA Check 2026-11-02' / 'selection.json').read_text(encoding='utf-8'))
BASE = next(r for r in BASE if r['tag'] == 'nasdaq-5m-candle-momentum-DI-ON')['inputs']
assert hashlib.sha256(EX5.read_bytes()).hexdigest().startswith('fe9f391db5af')
MGMT = {'M1': dict(InpUseATRTrailing='true', InpTrailingATR='6.0', InpTrailStartR='1.0', InpUseFixedTarget='false', InpCloseAtSessionEnd='false'),
        'M2': dict(InpUseATRTrailing='true', InpTrailingATR='4.0', InpTrailStartR='1.0', InpUseFixedTarget='false', InpCloseAtSessionEnd='false'),
        'M3': dict(InpUseATRTrailing='true', InpTrailingATR='10.0', InpTrailStartR='1.0', InpUseFixedTarget='false', InpCloseAtSessionEnd='false'),
        'M4': dict(InpUseATRTrailing='false', InpUseFixedTarget='true', InpRewardRisk='2.0', InpCloseAtSessionEnd='false'),
        'M5': dict(InpUseATRTrailing='false', InpUseFixedTarget='true', InpRewardRisk='1.0', InpCloseAtSessionEnd='false'),
        'M6': dict(InpUseATRTrailing='false', InpUseFixedTarget='false', InpCloseAtSessionEnd='true', InpCloseHourNY='15', InpCloseMinuteNY='55'),
        'M7': dict(InpUseATRTrailing='true', InpTrailingATR='6.0', InpTrailStartR='0.5', InpUseFixedTarget='false', InpCloseAtSessionEnd='false')}
STOPS = ['0.40', '0.60', '0.80', '1.00', '1.15', '1.30', '1.50', '2.00']


def variants():
    v = {}
    for di in ('ON', 'OFF'):
        for m, mi in MGMT.items():
            for st in STOPS:
                v[f"P{st.replace('.', '')}_{m}_DI{di}"] = dict(InpStopMode='2', InpInitialStopPercent=st, InpRequireDIAgreement='true' if di == 'ON' else 'false', **mi)
        for atr in ('6.0', '9.0', '12.0'):
            for m in ('M1', 'M4'):
                v[f"A{atr.split('.')[0]}_{m}_DI{di}"] = dict(InpStopMode='0', InpInitialStopATR=atr, InpRequireDIAgreement='true' if di == 'ON' else 'false', **MGMT[m])
    return v


b._native_trades = closing_deals
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
VARS = variants()
b.CONFIG.update(periods={'full': '2019.01.01', 'oct': '2026.10.01', '6m': '2026.05.01', '1y': '2025.11.01', '3y': '2023.11.01', '5y': '2021.11.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=1, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxNasdaqWide20261102', expert_file='nasdaq5m.ex5',
                period='M5', common_inputs=BASE, variants={k: {'label': k, 'inputs': x} for k, x in VARS.items()}, controls={})

if __name__ == '__main__':
    stage = sys.argv[1]
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'nasdaq5m.ex5')
    (ROOT / 'VARIANTS.json').write_text(json.dumps(VARS, indent=1), encoding='utf-8')
    if stage == 'search':
        for k in VARS: b.run_case('USTEC', k, 'full')
    elif stage == 'confirm':
        b.CONFIG['model'] = 4
        names = sys.argv[2:]
        for k in names:
            b.CONFIG['variants'][k + '_M4'] = {'label': k + ' Model 4', 'inputs': VARS[k]}
            b.run_case('USTEC', k + '_M4', 'full')
    elif stage == 'oct':                          # October 2026 month only, Model 4 (owner 2026-11-02)
        b.CONFIG['model'] = 4
        for k in sys.argv[2:]:
            b.CONFIG['variants'][k + '_M4'] = {'label': k + ' Model 4', 'inputs': VARS[k]}
            b.run_case('USTEC', k + '_M4', 'oct')
    elif stage == 'website':                      # deployment evidence: production SET with only the two stop lines changed (A6_M1_DION)
        b.CONFIG['model'] = 4
        old = PACKAGE / 'Selected Portfolio Settings 2026-09-01' / '11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
        canon = dict(l.split('=', 1) for l in old.read_text().splitlines() if '=' in l)
        assert canon['InpStopMode'] == '2' and canon['InpInitialStopPercent'] == '0.60' and canon['InpTrailingATR'] == '6.0'
        canon.update(InpStopMode='0', InpInitialStopATR='6.0')
        assert all(canon[k] == v for k, v in VARS['A6_M1_DION'].items())
        b.CONFIG['common_inputs'] = canon; b.CONFIG['variants']['DEPLOY'] = {'label': 'Nasdaq 5M DI ATR6 stop (deployed preset)', 'inputs': {}}
        for per in ('6m', '1y', '3y', '5y'): b.run_case('USTEC', 'DEPLOY', per)
    b.status(event='STAGE DONE ' + stage)
