"""Independent same-period risk-ladder audit; no engine imports or selection."""
from pathlib import Path
import argparse
import importlib.util
import json

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_risk_ladder_core',ROOT/'independent_verify.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def verify_risk():
    plan=v.read('PLAN.json')
    frozen=v.read('FROZEN.json')
    source=v.read('INPUTS.json')
    recent=v.read('RECENT.json')
    recent_receipt=v.read('RECENT-VERIFICATION.json')
    protocol=v.read('RISK-SENSITIVITY-PLAN.json')
    outcomes=v.read('RISK-SENSITIVITY.json')
    v.equivalent('RETROSPECTIVE SAME-PERIOD SENSITIVITY, NOT VALIDATION',protocol['status'],'protocol.status')
    v.equivalent(protocol['status'],outcomes['status'],'outcomes.status')
    v.equivalent(v.sha(ROOT/'RISK-SENSITIVITY-PLAN.json'),outcomes['protocol_sha256'],'protocol_sha256')
    v.equivalent(v.sha(ROOT/'risk_sensitivity.py'),protocol['script_sha256'],'script_sha256')
    v.equivalent(v.sha(ROOT/'RECENT.json'),protocol['recent_sha256'],'recent_sha256')
    v.equivalent(v.sha(ROOT/'FROZEN.json'),protocol['original_frozen_sha256'],'original_frozen_sha256')
    v.equivalent(plan['risk_percentages'],protocol['risks'],'same_risks')
    v.equivalent(plan['evaluation'],protocol['window'],'same_window')
    v.check(protocol['before_ladder_stress_outcomes'] is True,'Before-sensitivity declaration required')
    v.equivalent('PASS',recent_receipt['status'],'recent_receipt.status')
    v.equivalent(v.sha(ROOT/'RECENT.json'),recent_receipt['recent_sha256'],'recent_receipt.binding')
    primary=[c for c in recent['selected'] if c['role']=='primary']
    v.equivalent(primary,protocol['families'],'same_primary_families')
    for path,wanted in {**frozen['files'],**source['source_hashes']}.items():
        v.check(v.sha(path)==wanted,'Changed original evidence '+path)
    fields=('kind','keys','risk_pct','cost')
    coverage=[dict(kind=f['kind'],keys=f['keys'],risk_pct=r,cost=cost)
        for f in primary for r in plan['risk_percentages'] for cost in ('recorded','stress')]
    v.equivalent(coverage,[{k:c[k] for k in fields} for c in outcomes['results']],
                 'exact_family_risk_cost_coverage')
    starts=v.starts(plan['evaluation'])
    cache={}
    attempts_verified=0
    for c in outcomes['results']:
        ident=tuple(c['keys'])
        if ident not in cache:
            cache[ident]=v.events_for(source['rows'],set(c['keys']))
        attempts=[v.independent_attempt(cache[ident],source['symbols'],c['risk_pct'],t,t+365*v.D,
                                       stressed=c['cost']=='stress') for t in starts]
        label=f"risk.{c['kind']}.{c['risk_pct']}.{c['cost']}"
        v.equivalent(attempts,c['attempts'],label+'.attempts')
        v.equivalent(v.summary_of(attempts),c['summary'],label+'.summary')
        if c['cost']=='recorded':
            original=next(x for x in recent['configurations']
                          if x['keys']==c['keys'] and x['risk_pct']==c['risk_pct'])
            v.equivalent(original['attempts'],c['attempts'],label+'.retained_scoreboard_attempts')
            v.equivalent(original['summary'],c['summary'],label+'.retained_scoreboard_summary')
        attempts_verified+=len(attempts)
    receipt=dict(status='PASS',checks=v.CHECKS,
        interpretation='RETROSPECTIVE SAME-PERIOD RISK SENSITIVITY, NOT NEW VALIDATION',
        comparisons_verified=len(outcomes['results']),attempts_verified=attempts_verified,starts=len(starts),
        core_engine_imported=False,risk_sha256=v.sha(ROOT/'RISK-SENSITIVITY.json'),
        protocol_sha256=v.sha(ROOT/'RISK-SENSITIVITY-PLAN.json'),recent_sha256=v.sha(ROOT/'RECENT.json'),
        original_results_sha256=v.sha(ROOT/'RESULTS.json'),original_frozen_sha256=v.sha(ROOT/'FROZEN.json'),
        recent_verification_sha256=v.sha(ROOT/'RECENT-VERIFICATION.json'),
        independent_core_sha256=v.sha(ROOT/'independent_verify.py'),verifier_sha256=v.sha(Path(__file__)))
    (ROOT/'RISK-VERIFICATION.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-risk',action='store_true',required=True)
    parser.parse_args()
    verify_risk()
