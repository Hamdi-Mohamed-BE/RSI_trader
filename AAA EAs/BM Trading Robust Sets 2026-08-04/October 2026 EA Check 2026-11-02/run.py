"""October 2026 check (owner 2026-11-02): current production EX5 + preset of each EA, 1% risk per trade, adaptive off, standalone
$10,000, native MT5 Model 4 (real ticks), 150 ms, 2026-10-01 -> 2026-11-01 exclusive. ORBs use the live-profile 0.5R presets
(`_00 Live profiles/ORB05 Sets`). Nasdaq 5M is run with the DI filter ON and OFF (only InpRequireDIAgreement differs).
Reuses the audited No Wick harness (isolated tester only, report/input checks) as the Recent EA Shortlist study did.
Run from AAA EAs/EA store:  uv run python "../BM Trading Robust Sets 2026-08-04/October 2026 EA Check 2026-11-02/run.py"
"""
import os, sys, json, importlib.util, shutil, hashlib, inspect
from pathlib import Path
os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
from app.catalog import get_catalog
from app.mt5_evidence_jobs import _set_values, _materialized_values
import app.mt5_evidence_jobs as parser

code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


def closing_deals(path, label):                      # FIFO fragments recombined by exit deal (not extra trades)
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
b.CONFIG.update(periods={'oct': '2026.10.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=3600, expert_dir='CalyxOctober20261102')
ORB05 = PACKAGE / '_00 Live profiles' / 'ORB05 Sets'
RUNS = [('3-way-gold', {}), ('xau-rsi-vwap', {}), ('ema3', {}), ('gold-overnight-value-area', {}),
        ('us100-h1-orb-13utc', 'orb'), ('us100-orb-new-york-m30', 'orb'), ('us100-selective-orb-v3', 'orb'), ('xau-orb-new-york-m30', 'orb'),
        ('xau-orb-london-ny-overlap-m30', 'orb'),
        ('nasdaq-5m-candle-momentum', {'InpRequireDIAgreement': 'true'}), ('nasdaq-5m-candle-momentum', {'InpRequireDIAgreement': 'false'})]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def freeze():
    sel = ROOT / 'selection.json'
    if sel.exists(): return json.loads(sel.read_text(encoding='utf-8'))
    products = {p.slug: p for p in get_catalog()}; rows = []
    for slug, extra in RUNS:
        p = products[slug]
        mode = 'dynamic' if p.recommended_dynamic_mode else 'safe' if p.recommended_safe_mode else 'standard'
        ex = PACKAGE / (p.dynamic_expert_source if mode == 'dynamic' else p.expert_source)
        st = ORB05 / f'{slug}.set' if extra == 'orb' else PACKAGE / (p.dynamic_set_source if mode == 'dynamic' else (p.safe_set_source or p.set_source) if mode == 'safe' else p.set_source)
        inputs = _materialized_values(_set_values(st, mode == 'safe' and extra != 'orb'))
        inputs['InpRiskPercent'] = '1.0'; inputs['InpAdaptivePortfolioControls'] = 'false'
        if 'InpRiskMode' in inputs and slug in ('3-way-gold', 'gold-overnight-value-area'): inputs['InpRiskMode'] = '0'   # 0 = % of equity
        tag = slug
        if isinstance(extra, dict) and extra:
            inputs.update(extra); tag = slug + ('-DI-ON' if extra['InpRequireDIAgreement'] == 'true' else '-DI-OFF')
        if extra == 'orb': assert inputs.get('InpRewardRisk') == '0.5', slug
        dst = ROOT / 'snapshot' / tag; dst.mkdir(parents=True, exist_ok=True); shutil.copy2(ex, dst / 'selected.ex5'); shutil.copy2(st, dst / 'original.set')
        rows.append(dict(tag=tag, slug=slug, label=p.label, mode=mode, symbol=p.canonical, period=p.timeframe, expert=str(ex), set=str(st),
                         ex5_sha256=sha(ex), set_sha256=sha(st), inputs=inputs))
    sel.write_text(json.dumps(rows, indent=1), encoding='utf-8'); return rows


def main():
    rows = freeze()
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    for row in rows:
        dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
        src = ROOT / 'snapshot' / row['tag'] / 'selected.ex5'; assert sha(src) == row['ex5_sha256']
        shutil.copy2(src, dest / (row['slug'] + '.ex5'))
        b.CONFIG.update(expert_file=row['slug'] + '.ex5', period=row['period'], common_inputs=row['inputs'], variants={row['tag']: {'inputs': {}}})
        b.run_case(row['symbol'], row['tag'], 'oct')
    b.status(event='ALL DONE')


if __name__ == '__main__':
    main()
