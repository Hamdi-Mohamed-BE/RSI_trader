"""Audit an explicitly retrospective scoreboard, NOT new validation.

Imports only the separately implemented verifier's arithmetic, never simulate or
recent_screen. Original locked failures and their receipt remain immutable.
"""
from pathlib import Path
import argparse
import importlib.util
import json

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_challenge_core',ROOT/'independent_verify.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def verify_recent():
    source=v.read('INPUTS.json')
    plan=v.read('PLAN.json')
    recent_plan=v.read('RECENT-PLAN.json')
    original_frozen=v.read('FROZEN.json')
    recent_frozen=v.read('RECENT-FROZEN.json')
    original_receipt=v.read('VERIFICATION.json')
    development=v.read('DEVELOPMENT.json')
    original_results=v.read('RESULTS.json')
    recent=v.read('RECENT.json')
    v.check(recent['status']=='RETROSPECTIVE, NOT VALIDATION','Supplement must remain retrospective')
    v.check(recent_plan['status']=='SUPPLEMENTAL RETROSPECTIVE SCOREBOARD, not validation','Recent plan status')
    v.check(recent_frozen['before_full_recent_ranking'] is True,'Recent declaration freeze missing')
    v.equivalent(plan['evaluation'],recent_plan['window'],'recent.plan.window')
    for path,wanted in {**original_frozen['files'],**source['source_hashes'],**recent_frozen['files']}.items():
        v.check(v.sha(path)==wanted,'Changed frozen/source file '+path)
    v.equivalent(v.sha(ROOT/'RECENT-FROZEN.json'),recent['recent_frozen_sha256'],'recent_frozen_sha256')
    v.equivalent(v.sha(ROOT/'RESULTS.json'),recent['original_results_sha256'],'recent.original_results_sha256')
    v.equivalent('PASS',original_receipt['status'],'original_verification.status')
    for field,path in [('results_sha256','RESULTS.json'),('selection_sha256','SELECTION.json'),
                       ('frozen_sha256','FROZEN.json'),('development_sha256','DEVELOPMENT.json'),
                       ('inputs_sha256','INPUTS.json'),('plan_sha256','PLAN.json'),
                       ('verifier_sha256','independent_verify.py')]:
        v.equivalent(v.sha(ROOT/path),original_receipt[field],'original_receipt.'+field)
    expected_configs=development['singles']+development['combos']
    fields=('id','keys','risk_pct')
    v.equivalent([{k:c[k] for k in fields} for c in expected_configs],
                 [{k:c[k] for k in fields} for c in recent['configurations']],
                 'exact_unchanged_development_configuration_coverage')
    starts=v.starts(plan['evaluation'])
    cache={}
    def get_events(keys):
        ident=tuple(keys)
        if ident not in cache:
            cache[ident]=v.events_for(source['rows'],set(keys))
        return cache[ident]
    paths_verified=0
    for c in recent['configurations']:
        aa=[v.independent_attempt(get_events(c['keys']),source['symbols'],c['risk_pct'],t,t+365*v.D) for t in starts]
        v.equivalent(aa,c['attempts'],'recent.'+c['id']+'.attempts')
        v.equivalent(v.summary_of(aa),c['summary'],'recent.'+c['id']+'.summary')
        paths_verified+=len(aa)
    selected=[]
    for kind,candidates in [('single',[c for c in recent['configurations'] if len(c['keys'])==1]),
                             ('combo',[c for c in recent['configurations'] if len(c['keys'])>1])]:
        primary=min(candidates,key=v.selection_order)
        hit_candidates=[c for c in candidates if c['summary']['fastest'] is not None]
        fastest=min(hit_candidates,key=lambda c:(c['summary']['fastest']['days'],-c['summary']['hit_pct'],c['id'])) if hit_candidates else primary
        for role,c in [('primary',primary),('fastest_observed',fastest)]:
            selected.append(dict(kind=kind,role=role,id=c['id'],keys=c['keys'],risk_pct=c['risk_pct']))
    v.equivalent(selected,recent['selected'],'retrospective_selection')
    expected_sensitivity={(c['id'],cost) for c in selected for cost in ('recorded','stress')}
    v.equivalent(sorted(expected_sensitivity),sorted((c['id'],c['cost']) for c in recent['sensitivity']),
                 'recent.sensitivity.coverage')
    v.check(len(expected_sensitivity)==len(recent['sensitivity']),'Duplicate recent sensitivity')
    detail_count=0
    sensitivity_attempts=0
    for c in recent['sensitivity']:
        locked=next(x for x in selected if x['id']==c['id'])
        v.equivalent(locked['keys'],c['keys'],'sensitivity.keys')
        v.equivalent(locked['risk_pct'],c['risk_pct'],'sensitivity.risk')
        aa=[v.independent_attempt(get_events(c['keys']),source['symbols'],c['risk_pct'],t,t+365*v.D,
                                 stressed=c['cost']=='stress') for t in starts]
        ss=v.summary_of(aa)
        v.equivalent(aa,c['attempts'],'sensitivity.'+c['id']+'.'+c['cost']+'.attempts')
        v.equivalent(ss,c['summary'],'sensitivity.'+c['id']+'.'+c['cost']+'.summary')
        chosen={sorted(aa,key=lambda x:x['ending_closed_cash'])[len(aa)//2]['start']}
        if ss['fastest'] is not None:
            chosen.add(ss['fastest']['start'])
        dd=[v.independent_attempt(get_events(c['keys']),source['symbols'],c['risk_pct'],t,t+365*v.D,
                                 True,c['cost']=='stress') for t in sorted(chosen)]
        v.equivalent(dd,c['details'],'sensitivity.'+c['id']+'.'+c['cost']+'.details')
        sensitivity_attempts+=len(aa)
        detail_count+=len(dd)
    # The supplemental scoring must reproduce every original recorded-cost
    # locked result that was already exposed; it cannot rewrite that failure.
    by_id={c['id']:c for c in recent['configurations']}
    retained=0
    for c in original_results['results']:
        if c['cost']=='recorded':
            v.equivalent(c['attempts'],by_id[c['id']]['attempts'],'retained_original_attempts.'+c['id'])
            v.equivalent(c['summary'],by_id[c['id']]['summary'],'retained_original_summary.'+c['id'])
            retained+=1
    receipt=dict(status='PASS',interpretation='RETROSPECTIVE SCOREBOARD ONLY, NOT INDEPENDENT VALIDATION',
        checks=v.CHECKS,configurations_verified=len(recent['configurations']),
        full_scoreboard_attempts_verified=paths_verified,starts=len(starts),
        sensitivity_comparisons_verified=len(recent['sensitivity']),
        sensitivity_attempts_verified=sensitivity_attempts,detailed_paths_verified=detail_count,
        original_recorded_results_preserved=retained,core_engine_imported=False,
        recent_sha256=v.sha(ROOT/'RECENT.json'),recent_frozen_sha256=v.sha(ROOT/'RECENT-FROZEN.json'),
        recent_plan_sha256=v.sha(ROOT/'RECENT-PLAN.json'),
        original_results_sha256=v.sha(ROOT/'RESULTS.json'),original_selection_sha256=v.sha(ROOT/'SELECTION.json'),
        original_frozen_sha256=v.sha(ROOT/'FROZEN.json'),
        original_verification_sha256=v.sha(ROOT/'VERIFICATION.json'),
        independent_core_sha256=v.sha(ROOT/'independent_verify.py'),verifier_sha256=v.sha(Path(__file__)),
        limitation='Checks arithmetic and exact search/rank coverage. It does not restore out-of-sample status to candidates selected using the same later-period outcomes, or establish live execution/future success probability.')
    (ROOT/'RECENT-VERIFICATION.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-recent',action='store_true',required=True,
                        help='Run only after root announces that full retrospective scoreboard outcomes exist.')
    parser.parse_args()
    verify_recent()
