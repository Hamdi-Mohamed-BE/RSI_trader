"""October 2026 portfolio check with the new Nasdaq 5M ATR6 stop (owner 2026-11-03: "rebuild the portfolio histories for the five
portfolios, October only for now"). Native MT5 Model 4, 2026-10-01 -> 2026-11-01, $10k, 150 ms, each member standalone at 1% of equity
on the exact Current14 + ORB 0.5R wrapper EX5s and package inputs (the FTMO / Prop ready / Best Prop strategy inputs are the same,
asserted by Current14 Verify-Release). Extra Nasdaq runs: old 0.60% stop (DI ON / DI OFF) and new stop DI OFF.
Run from AAA EAs/EA store:  uv run python "<study>/run.py"      then  python replay.py
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


C14 = PACKAGE / 'Current14 Plus ORB05 Portfolio 2026-10-08'
PKG = json.loads((C14 / 'Package.json').read_text(encoding='utf-8'))
TF = {1: 'M1', 5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
b._native_trades = closing_deals
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.CONFIG.update(periods={'oct': '2026.10.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=3600, expert_dir='CalyxPortfolioOct20261103', controls={}, variants={})


def cases():
    out = []
    for e in PKG['entries']:
        inputs = dict(e['inputs'], InpPortfolioRiskMode='0', InpPortfolioPercent='1.0', InpPortfolioExpectedLogin='0',
                      InpPortfolioExpectedServer='', InpPortfolioExpectedSymbol='', InpPortfolioInstallNonce='')
        out.append((e['key'], 'NEW', e, inputs))
        if e['key'] == 'nasdaq-5m-candle-momentum':
            assert inputs['InpStopMode'] == '0' and inputs['InpInitialStopATR'] == '6.0' and inputs['InpRequireDIAgreement'] == 'true'
            old = dict(inputs, InpStopMode='2', InpInitialStopATR='4.0'); assert old['InpInitialStopPercent'] == '0.60'
            out += [(e['key'], 'OLD', e, old), (e['key'], 'NEWDIOFF', e, dict(inputs, InpRequireDIAgreement='false')),
                    (e['key'], 'OLDDIOFF', e, dict(old, InpRequireDIAgreement='false'))]
    return out


RISK_KEYS = ('InpRiskPercent', 'InpGridRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent')


def full_cases():
    """Full EA portfolio, news EAs removed: the installer's own effective inputs (resolve_full.ps1 -> FULL_ITEMS.json), research risk
    1%, the shared adaptive governor off (replayed at portfolio level instead). Plus funded_v1's ORB VP Volume Confirmed 0.5R preset."""
    items = json.loads((ROOT / 'FULL_ITEMS.json').read_text(encoding='utf-8-sig')); out = []
    for it in items:
        inputs = {k: str(v) for k, v in it['inputs'].items()}
        for k in RISK_KEYS:
            if k in inputs: inputs[k] = '1.0'
        inputs['InpAdaptivePortfolioControls'] = 'false'
        slug = ''.join(c if c.isalnum() else '-' for c in it['label'].lower()).strip('-')
        out.append((slug, 'FULL', it, inputs))
        if it['label'] == 'ORB Volume Profile Volume Confirmed':
            fset = PACKAGE / '_00 Live profiles/Packages/FundedV1/package'
            fv = next(f for f in fset.glob('*.set') if 'Volume Confirmed' in f.name or 'volume-confirmed' in f.name)
            fvals = dict(l.split('=', 1) for l in fv.read_text(encoding='utf-8-sig').splitlines() if '=' in l)
            funded = dict(inputs, **{k: v for k, v in fvals.items() if k in inputs and k not in RISK_KEYS and k != 'InpAdaptivePortfolioControls'})
            assert funded['InpRewardRisk'].split('||')[0] == '0.5', funded['InpRewardRisk']
            out.append((slug, 'FUNDED', it, funded))
    return out


if __name__ == '__main__' and sys.argv[1:] == ['full']:
    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT / 'PLAN.json').read_text())
    for slug, tag, it, inputs in full_cases():
        ex5 = Path(it['expert_path']); name = f'full-{slug}.ex5'; shutil.copy2(ex5, dest / name)
        variant = f'{slug}__{tag}'; sym = it['canonical']; per = TF[int(it['period'])]
        b.CONFIG['variants'][variant] = {'label': f"{it['label']} {tag}", 'inputs': {}}
        b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = per
        if not any(p['key'] == slug and p['tag'] == tag for p in plan):
            plan.append(dict(key=slug, tag=tag, label=it['label'], symbol=sym, period=per, expert=str(ex5), ex5_sha=b.sha(ex5), case=f'nw-{sym}-{variant}-oct'))
        (ROOT / 'PLAN.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
        try:
            b.run_case(sym, variant, 'oct')
        except SystemExit:
            print('CASE FAILED', variant, flush=True)
    b.status(event='STAGE DONE full'); sys.exit(0)

if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    plan = []
    for key, tag, e, inputs in cases():
        ex5 = C14 / e['expert']; name = f'{key}.ex5'; shutil.copy2(ex5, dest / name)
        variant = f'{key}__{tag}'
        b.CONFIG['variants'][variant] = {'label': f'{e["label"]} {tag}', 'inputs': {}}
        b.CONFIG['common_inputs'] = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in inputs.items()}
        b.CONFIG['expert_file'] = name; b.CONFIG['period'] = TF[e['period']]
        sym = e['canonical']
        plan.append(dict(key=key, tag=tag, symbol=sym, period=TF[e['period']], expert=str(ex5.relative_to(PACKAGE)), ex5_sha=b.sha(ex5),
                         case=f'nw-{sym}-{variant}-oct'))
        b.run_case(sym, variant, 'oct')
    (ROOT / 'PLAN.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
    b.status(event='STAGE DONE october')
