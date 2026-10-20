"""Same-period risk ladder for the two retrospectively selected EA families."""
import simulate as s


def main():
    s.verify_freeze()
    assert not (s.ROOT/'RISK-SENSITIVITY.json').exists()
    source,recent,plan=s.read('INPUTS.json'),s.read('RECENT.json'),s.read('PLAN.json')
    primary=[x for x in recent['selected'] if x['role']=='primary']
    protocol=dict(status='RETROSPECTIVE SAME-PERIOD SENSITIVITY, NOT VALIDATION',
        families=primary,risks=plan['risk_percentages'],window=plan['evaluation'],
        rule='All six already-declared risk levels for each selected primary EA family, base/stress; no new family or guard search.',
        before_ladder_stress_outcomes=True,script_sha256=s.digest(__file__),
        recent_sha256=s.digest(s.ROOT/'RECENT.json'),original_frozen_sha256=s.digest(s.ROOT/'FROZEN.json'))
    s.save('RISK-SENSITIVITY-PLAN.json',protocol)
    starts=s.weekly_starts(plan['evaluation'])
    out=[]
    for family in primary:
        events=s.build_events(source['rows'],set(family['keys']))
        for risk in plan['risk_percentages']:
            for stress in (False,True):
                aa=[s.replay(events,source['symbols'],risk,t,t+365*s.DAY,stress=stress) for t in starts]
                out.append(dict(kind=family['kind'],keys=family['keys'],risk_pct=risk,cost='stress' if stress else 'recorded',summary=s.summarize(aa),attempts=aa))
    s.save('RISK-SENSITIVITY.json',dict(status=protocol['status'],results=out,protocol_sha256=s.digest(s.ROOT/'RISK-SENSITIVITY-PLAN.json')))
    print('RISK LADDER COMPLETE '+s.digest(s.ROOT/'RISK-SENSITIVITY.json'))


if __name__=='__main__':
    main()
