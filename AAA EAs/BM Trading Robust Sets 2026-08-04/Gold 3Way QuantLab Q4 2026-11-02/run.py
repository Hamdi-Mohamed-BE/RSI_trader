"""3 Way Gold vs the QuantLab "XAUUSD 3x Speed Q4 Turn" structure (owner 2026-11-02). Plan frozen in PLAN.md before any result.
Research copy `EA/3WG Q4 Research.mq5` = production 3 Way Gold + InpBSeason / InpBTimeframe (breakout module only; bar lengths scaled
to keep the same time span). Native MT5 Model 4, XAUUSD, 0.75% risk per module trade (QuantLab's preset), $10k, 150 ms,
2019-01-01 -> 2026-11-01 (entries from 2019-06-01 after warm-up). Audited No Wick harness (isolated tester only).
Run from AAA EAs/EA store:  uv run python "../BM Trading Robust Sets 2026-08-04/Gold 3Way QuantLab Q4 2026-11-02/run.py" parity|main
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
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
COMMON = dict(InpEnableTrading='true', InpEnableMomentum='true', InpEnableBreakout='true', InpEnableTurnOfMonth='true', InpMarketEntries='false',
              InpRiskPercent='0.75', InpRiskMode='0', InpFixedRiskMoney='0.0', InpAdaptivePortfolioControls='false', InpMagic='930930100',
              # InpTradeFrom = 2019-06-01 00:00 as Unix seconds: the MT5 report prints datetime inputs this way, so the harness input check
              # compares like with like (the first parity run applied '2019.06.01 00:00' correctly but failed that string check)
              InpMaximumDeviationPoints='1000', InpAutoServerUtcOffsetLive='true', InpServerUtcOffsetHours='0', InpTradeFrom='1559347200',
              InpResearchLedger='false', InpBSeason='0', InpBTimeframe='15')
VARIANTS = {'G0': dict(label='production 3 Way Gold (breakout all year, M15)'),
            'G1': dict(label='breakout Q4 only (Oct-Dec), M15', InpBSeason='1'),
            'G2': dict(label='breakout Q4 only, H1 (QuantLab structure)', InpBSeason='1', InpBTimeframe='60'),
            'G3': dict(label='breakout all year, H1', InpBTimeframe='60'),
            'G4': dict(label='breakout OFF (momentum H4 + turn of month)', InpEnableBreakout='false')}
b.CONFIG.update(periods={'full': '2019.01.01', 'parity1y': '2025.11.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4,
                execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxGoldQ420261102', period='M15',
                common_inputs=COMMON, variants={k: {'label': v['label'], 'inputs': {x: y for x, y in v.items() if x != 'label'}} for k, v in VARIANTS.items()},
                controls={})

if __name__ == '__main__':
    stage = sys.argv[1]
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'EA' / '3WG Q4 Research.ex5', dest / 'research.ex5')
    shutil.copy2(PACKAGE / '3 Way Gold EA' / '3 Way Gold EA.ex5', dest / 'production.ex5')
    if stage == 'parity':                         # research copy with default inputs must equal production, trade for trade
        b.CONFIG['expert_file'] = 'production.ex5'
        prod_inputs = {k: v for k, v in COMMON.items() if k not in ('InpBSeason', 'InpBTimeframe')}
        b.CONFIG['common_inputs'] = prod_inputs; b.CONFIG['variants']['PROD'] = {'label': 'production EX5', 'inputs': {}}
        b.run_case('XAUUSD', 'PROD', 'parity1y')
        b.CONFIG['expert_file'] = 'research.ex5'; b.CONFIG['common_inputs'] = COMMON
        b.run_case('XAUUSD', 'G0', 'parity1y')
    elif stage == 'main':
        b.CONFIG['expert_file'] = 'research.ex5'
        for k in VARIANTS: b.run_case('XAUUSD', k, 'full')
    b.status(event='STAGE DONE ' + stage)
