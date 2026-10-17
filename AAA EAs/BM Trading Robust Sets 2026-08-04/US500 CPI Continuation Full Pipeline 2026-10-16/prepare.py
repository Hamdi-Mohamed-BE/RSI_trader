"""Chronological/source preregistration before development performance is read."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json
from search_plan import PLAN
R=Path(__file__).resolve().parent; B=R.parent

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def stable(path,obj):
    if path.exists(): assert json.loads(path.read_text(encoding='utf-8'))==obj, f'Frozen preparation changed: {path.name}'
    else: path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def main():
    raw=B/'US500 CPI Continuation vs Reversion Raw 2026-10-16'
    calendar=json.loads((raw/'calendar.json').read_text())
    stable(R/'calendar.json',calendar)
    helper=B.parent/'Calyx Research Pipeline/data_split.py'
    spec=importlib.util.spec_from_file_location('cpi_split',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    split=module.research_split('2020-01-01','2026-10-16');module.validate_split(split)
    stable(R/'DATA-SPLIT.json',split)
    stable(R/'SEARCH-PLAN.json',json.loads(json.dumps(PLAN)))
    locked={name:sha(R/name) for name in ['config.json','calendar.json','DATA-SPLIT.json','SEARCH-PLAN.json','engine.mq5','build_engine.py','search_plan.py']}
    receipt=R/'PREREGISTRATION.json'
    if receipt.exists(): assert json.loads(receipt.read_text())['locked']==locked
    else: receipt.write_text(json.dumps(dict(locked=locked,registered_at_utc=datetime.now(timezone.utc).isoformat(),
             raw_results_sha256=sha(raw/'RESULTS.json'),policy_sha256=sha(B.parent/'Calyx Research Pipeline/pipeline-policy.json'),
             exploratory_authorization='Continue exploratory optimization; research-only',prior_raw_results_viewed=True,
             genuinely_untouched_oos=False,live_changes=False),indent=2),encoding='utf-8')
    print('PREREGISTERED',json.dumps(split),flush=True)

if __name__=='__main__': main()
