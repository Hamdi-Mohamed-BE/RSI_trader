"""Deterministic consistency checks, not evidence of future trading success."""
import hashlib
import numpy as np
from simulate import ROOT, read, save, run, clock, specs, FIELDS
from payout_followup import DAY,business_ready

def main():
    result=read(ROOT/'PAYOUT_RESULTS.json');a=read(ROOT/'recent-AUDIT.json')
    assert result['source_sha256']==hashlib.sha256((ROOT/'recent-prepared.npz').read_bytes()).hexdigest()
    n=0;stages=0;rewards=0
    for scenario in result['scenarios']:
        for p in scenario['paths']:
            n+=1
            for s in p['stages']:
                stages+=1;m=s['metrics']
                if s['success']:
                    assert m['open_at_end']==0 and m['first_ftmo_breach_minute']<0
                    assert s['profit']>=({1:1000,2:500,3:50}[s['phase']])-1e-6
                assert m['max_open_risk']<=250+1e-6 or scenario['config']['cap']==0
                if s['phase']==3 and s['success']:
                    assert s['end']-s['first_entry']>=14*DAY
            if p['phase2'] is not None:assert p['phase2']>=business_ready(p['phase1'],2)
            if p['funded'] is not None:assert p['funded']==business_ready(p['phase2'],5)
            for r in p['rewards']:
                rewards+=1
                assert abs(r['trader_share']-.8*r['gross'])<1e-8
                assert r['request']>=p['funded']+14*DAY
                assert r['request']<=p['end']
    # The new optional endpoints must not change the prior continuous audit.
    z=np.load(ROOT/'recent-prepared.npz');d=clock(a['start'],a['end']);sp=specs();old=read(ROOT/'RESULTS.json')
    defaults=[]
    for policy in ['Baseline','A loss2 goal4']:
        original=next(x for x in old if x['period']=='recent-' and x['account']=='FTMO Swing' and not x['stress'] and x['config']['name']==policy)
        c=original['config']
        v,*_=run(z['trades'],z['prices'],z['opens'],z['fresh'],sp,a['start'],a['end'],d,True,c['loss'],c['target'],c['cap'],False,False,False)
        err=max(abs(float(v[i])-original['metrics'][key]) for i,key in enumerate(FIELDS))
        assert err<1e-6,(policy,err)
        defaults.append(dict(policy=policy,max_absolute_metric_change=err))
    save(ROOT/'PAYOUT_CHECKS.json',dict(paths_checked=n,stages_checked=stages,rewards_checked=rewards,
         source_hash_unchanged=True,default_continuous_regression=defaults,passed=True))
    print(read(ROOT/'PAYOUT_CHECKS.json'))

if __name__=='__main__':main()
