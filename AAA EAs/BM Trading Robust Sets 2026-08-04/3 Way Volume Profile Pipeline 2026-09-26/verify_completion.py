"""Final evidence-only consistency checks, no tester starts."""
import json
from pathlib import Path
import sys
import run_qualification as q
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Optimization'))
import search

def main():
    result=json.loads((ROOT/'FINAL RESULTS.json').read_text())
    ledger=json.loads((ROOT/'Optimization'/'SEARCH RESULTS.json').read_text())
    checks={
        'source_dependencies_unchanged':bool(q.verified_build()),
        'qualification_parity':all(json.loads((ROOT/'parity.json').read_text())[k] for k in ('metrics_equal','trades_equal')),
        'optimization_parity':all(json.loads((ROOT/'Optimization'/'parity.json').read_text()).values()),
        'all_native_raw_reports_verified':all(r['ok'] for r in q.rows()),
        'raw_ledger_reconciliation':all(r['audit']['reconciled'] for r in json.loads((ROOT/'AUDIT.json').read_text())),
        'native_validation_cashflows_exact':all(r['detail']['cashflow_reconciled'] for r in result['validation'].values()),
        'search_pass_count':len(ledger)==415,
        'unique_parameter_count':len({search.digest(r['parameters']) for r in ledger})==385,
        'three_finalists_failed':all(r['metrics']['profit_factor']<1.15 for name,r in result['validation'].items() if 'BRK-validation' in name),
        'reserved_holdout_not_used':not any((ROOT/'Optimization'/'native').glob('*holdout*')),
        'research_lock_released':not (ROOT/'.qualification.lock').exists(),
        'isolated_terminal_closed':not q.h.isolated_running(),
    }
    for folder in (ROOT/'Optimization'/'native').iterdir():
        manifest=folder/'manifest.json'
        if not manifest.exists(): continue
        spec=json.loads(manifest.read_text()); rows=json.loads((folder/'results.json').read_text())
        if spec['optimize']:
            checks[folder.name+'_indices']=len(rows)==len(spec['cases']) and {r['index'] for r in rows}==set(range(len(spec['cases'])))
        checks[folder.name+'_compile']=bool(__import__('re').search(r'0 errors?, 0 warnings?',q.h.text(folder/'search.compile.log')))
    q.dump(ROOT/'verification.json',dict(passed=all(checks.values()),checks=checks))
    print(json.dumps(dict(passed=all(checks.values()),checks=len(checks),failed=[k for k,v in checks.items() if not v]),indent=2))
    if not all(checks.values()): raise SystemExit(1)

if __name__=='__main__': main()
