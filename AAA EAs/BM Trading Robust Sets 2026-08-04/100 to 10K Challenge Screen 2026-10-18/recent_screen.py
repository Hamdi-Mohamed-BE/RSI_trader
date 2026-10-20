"""Explicit ex-post scoreboard; cannot overwrite original selection/results."""
import simulate as s


def main():
    s.verify_freeze()
    assert not (s.ROOT/'RECENT.json').exists()
    names=['RECENT-PLAN.json','recent_screen.py','DEVELOPMENT.json','RESULTS.json','SELECTION.json','FROZEN.json']
    s.save('RECENT-FROZEN.json',{'before_full_recent_ranking':True,'files':{str(s.ROOT/n):s.digest(s.ROOT/n) for n in names}})
    source,dev,plan=s.read('INPUTS.json'),s.read('DEVELOPMENT.json'),s.read('PLAN.json')
    starts=s.weekly_starts(plan['evaluation'])
    out=[]
    cache={}
    for i,c in enumerate(dev['singles']+dev['combos']):
        k=tuple(c['keys'])
        if k not in cache:
            cache[k]=s.build_events(source['rows'],set(k))
        aa=[s.replay(cache[k],source['symbols'],c['risk_pct'],t,t+365*s.DAY) for t in starts]
        out.append(dict(id=c['id'],keys=c['keys'],risk_pct=c['risk_pct'],summary=s.summarize(aa),attempts=aa))
        if (i+1)%100==0:
            print('Recent descriptive configs '+str(i+1),flush=True)
    selected=[]
    for kind,cc in [('single',[c for c in out if len(c['keys'])==1]),('combo',[c for c in out if len(c['keys'])>1])]:
        best=min(cc,key=s.rank)
        hh=[c for c in cc if c['summary']['fastest']]
        fast=min(hh,key=lambda c:(c['summary']['fastest']['days'],-c['summary']['hit_pct'],c['id'])) if hh else best
        for role,c in [('primary',best),('fastest_observed',fast)]:
            selected.append(dict(kind=kind,role=role,id=c['id'],keys=c['keys'],risk_pct=c['risk_pct']))
    sensitivity=[]
    for c in {x['id']:x for x in selected}.values():
        events=cache[tuple(c['keys'])]
        for stress in (False,True):
            aa=[s.replay(events,source['symbols'],c['risk_pct'],t,t+365*s.DAY,stress=stress) for t in starts]
            summary=s.summarize(aa)
            chosen={sorted(aa,key=lambda x:x['ending_closed_cash'])[len(aa)//2]['start']}
            if summary['fastest']:
                chosen.add(summary['fastest']['start'])
            dd=[s.replay(events,source['symbols'],c['risk_pct'],t,t+365*s.DAY,True,stress) for t in sorted(chosen)]
            sensitivity.append(dict(id=c['id'],keys=c['keys'],risk_pct=c['risk_pct'],cost='stress' if stress else 'recorded',summary=summary,attempts=aa,details=dd))
    s.save('RECENT.json',dict(status='RETROSPECTIVE, NOT VALIDATION',configurations=out,selected=selected,sensitivity=sensitivity,
        recent_frozen_sha256=s.digest(s.ROOT/'RECENT-FROZEN.json'),original_results_sha256=s.digest(s.ROOT/'RESULTS.json')))
    print('RECENT COMPLETE '+s.digest(s.ROOT/'RECENT.json'))


if __name__=='__main__':
    main()
