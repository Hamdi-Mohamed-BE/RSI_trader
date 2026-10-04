"""Apply existing raw evidence audit without optimisation or invented cost stress."""
from pathlib import Path
import importlib.util, json, sys
ROOT=Path(__file__).resolve().parent
pipeline=ROOT.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py'
spec=importlib.util.spec_from_file_location('calyx_raw_pipeline',pipeline)
audit=importlib.util.module_from_spec(spec);sys.modules[spec.name]=audit;spec.loader.exec_module(audit)
for i,symbol in enumerate(('USTEC','US500')):
 report=ROOT.parent/'_Backtests/MT5-DMC-20260811/reports/tierorb-20261002'/f'{symbol}-5y.htm'
 print('RAW STATISTICAL AUDIT '+symbol,flush=True)
 payload=audit.audit_report(report,label=symbol+' raw 5y',paths=10000,block=5,tested_configurations=2,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=None,seed=20261002+i)
 # Two asset candidates are counted conservatively in DSR. Window repeats do not create new strategy parameters.
 run=json.loads((ROOT/'native'/f'{symbol}-5y'/'run.json').read_text())
 assert payload['metrics']['trades']==run['metrics']['trades']
 assert abs(payload['metrics']['net_profit']-run['metrics']['net_profit'])<.1
 payload['scope_note']='Raw statistical screen, no optimisation. Closed-P&L breach probabilities are internal policy proxies, not an FTMO evaluation or payout forecast. No measured extra-cost stress supplied. Historical floating-equity DD is in the native run.'
 folder=ROOT/'audit';folder.mkdir(exist_ok=True)
 (folder/(symbol+'.json')).write_text(json.dumps(audit.json_safe(payload),indent=2,default=str,allow_nan=False),encoding='utf-8')
 (folder/(symbol+'.md')).write_text(audit.markdown(payload),encoding='utf-8')
 print(symbol+' '+payload['verdict']+' '+json.dumps(payload['gates']),flush=True)
