"""XAU Weakness: enter at market when price is already past the breakout level (owner 2026-11-03: "fix it to enter at market and
backtest 5 years and october"). In October 2026 both signals failed with "Invalid price": the EA sends a sell stop below support, but
price was already below it. The research copy EA/XAU Weakness Market Fill Research.mq5 adds only InpWeaknessMarketIfPast (default
false): when true and a stop order would be rejected because price is at/through the level (within the stop level), it sends a market
order with the same structure stop and the same R target (AAA_SendMarket, risk sized from the fill price). Production files untouched.

Native MT5 Model 4, $10k, 150 ms, Full EA preset inputs (FULL_ITEMS.json of the October study), risk 1%, adaptive governor off.
  PROD  = production EX5 (49094a2aae10), OFF = research EX5 with the switch off (parity), ON = switch on.
  Windows: 5y 2021-11-01 -> 2026-11-01 (end exclusive), oct 2026-10-01 -> 2026-11-01.
Run from AAA EAs/EA store:  uv run python "<study>/run.py"
"""
import importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent; PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py')
o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.CONFIG.update(periods={'5y': '2021.11.01', 'oct': '2026.10.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4,
                execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxXauWeaknessMarket20261103',
                controls={}, variants={}, period='M30')

PROD = PACKAGE / 'AAA Final EAs/AAA Final XAU Weakness EA/AAA Final XAU Weakness EA.ex5'
RESEARCH = ROOT / 'EA/XAU Weakness Market Fill Research.ex5'
item = next(i for i in json.loads((PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8-sig'))
            if i['label'] == 'AAA Final XAU Weakness')
assert Path(item['expert_path']) == PROD and int(item['period']) == 30
INPUTS = {k: str(v) for k, v in item['inputs'].items()}
for k in o.RISK_KEYS:
    if k in INPUTS: INPUTS[k] = '1.0'
INPUTS['InpAdaptivePortfolioControls'] = 'false'
assert INPUTS['InpRewardRisk'] == '4.00' and INPUTS['InpWeaknessTimeframe'] == '30'

CASES = [('ON', 'oct'), ('OFF', 'oct'), ('ON', '5y'), ('PROD', '5y'), ('OFF', '5y')]

if __name__ == '__main__':
    assert not b.isolated_running(), 'Tester is occupied'
    b.OUT.mkdir(exist_ok=True)
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
    plan = dict(prod_ex5=str(PROD), prod_sha=b.sha(PROD), research_ex5=str(RESEARCH), research_sha=b.sha(RESEARCH), inputs=INPUTS, cases=CASES)
    (ROOT / 'PLAN.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
    for tag, period in CASES:
        ex5 = PROD if tag == 'PROD' else RESEARCH; name = f'xau-weakness-{tag.lower()}.ex5'; shutil.copy2(ex5, dest / name)
        extra = {} if tag == 'PROD' else {'InpWeaknessMarketIfPast': 'true' if tag == 'ON' else 'false'}
        b.CONFIG['variants'][tag] = {'label': f'XAU Weakness {tag}', 'inputs': extra}
        b.CONFIG['common_inputs'] = INPUTS; b.CONFIG['expert_file'] = name
        try:
            b.run_case('XAUUSD', tag, period)
        except SystemExit:
            print('CASE FAILED', tag, period, flush=True)
    b.status(event='STAGE DONE xau weakness market fill'); print('ALL DONE', flush=True)
