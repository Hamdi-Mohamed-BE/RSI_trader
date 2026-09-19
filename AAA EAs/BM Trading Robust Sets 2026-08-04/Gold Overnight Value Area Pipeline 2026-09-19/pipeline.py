"""Native finalists -> freeze choice -> evaluation/stress. Research only."""
import json,math
from datetime import datetime,timezone
from data import ROOT,save,sha
from native import run,ident
from screen import score,simulate

def normalized_score(m,years,minimum):
    normalized=dict(m,return_pct=100*((max(.001,1+m['return_pct']/100))**(1/years)-1))
    return score(normalized,minimum)

def main():
    raw=json.loads((ROOT/'raw-results.json').read_text())
    assert all(k in raw for k in ('train','validation','6m','1y','3y','5y')),'Finish baseline batch first'
    frozen=json.loads((ROOT/'finalists-frozen.json').read_text());final=[]
    for row in frozen['finalists']:
        c=row['config'];a=run(c,'train','finalist');b=run(c,'validation','finalist')
        reasons=[]
        for label,m,count in [('training',a,300),('validation',b,60)]:
            if m['trades']<count:reasons.append(f'{label}: fewer than {count} trades')
            if m['return_pct']<=0:reasons.append(f'{label}: net loss')
            if m['profit_factor']<1.1:reasons.append(f'{label}: PF below 1.10')
            if m['max_drawdown_pct']>20:reasons.append(f'{label}: equity DD over 20%')
        final.append(dict(id=ident(c),config=c,train=a,validation=b,eligible=not reasons,reasons=reasons,
            worst_normalized_score=min(normalized_score(a,3,300),normalized_score(b,1,60))))
        save(ROOT/'native-finalists.json',final)
    ordered=sorted(final,key=lambda x:(x['eligible'],x['worst_normalized_score']),reverse=True)
    choice=ordered[0]
    selection=dict(selected=choice,all_finalists=ordered,any_eligible=any(r['eligible'] for r in final),
        recommendation='RESEARCH CANDIDATE ONLY' if choice['eligible'] else 'NO PROMOTION: all finalists failed predeclared validation gates',
        frozen_before_latest_year_evaluation=True,frozen_utc=datetime.now(timezone.utc).isoformat(),finalists_sha256=sha(ROOT/'native-finalists.json'))
    save(ROOT/'selection-frozen.json',selection);print('FROZEN SELECTION',choice['id'],selection['recommendation'],flush=True)
    c=choice['config'];results={}
    for period in ('1y','6m','3y','5y'):
        results[period]=run(c,period,'selected');save(ROOT/'selected-results.json',results)
    stress=[]
    for delay in (500,1000):
        stress.append(run(c,'1y','delay-stress',delay=delay));save(ROOT/'native-stress.json',stress)
    stress.append(run(c,'5y','half-risk',risk=.5));save(ROOT/'native-stress.json',stress)
    # Predefined local sensitivity. No neighbor is substituted after evaluation.
    neighbors=[]
    for key,values in [('bins',(32,64,96)),('va',(60,70,80)),('min_r',(0.,.25,.5))]:
        for value in values:
            if value==c[key]:continue
            other=dict(c,**{key:value})
            neighbors.append(dict(parameter=key,value=value,config=other,training=simulate(other,'train'),validation=simulate(other,'validation')))
    save(ROOT/'neighbor-screen.json',dict(approximation=True,neighbors=neighbors))
    # Two geometry neighbors also checked natively, validation only, no reranking.
    checks=[]
    for key in ('bins','va'):
        nearest=min((n for n in neighbors if n['parameter']==key),key=lambda n:abs(n['value']-c[key]))
        checks.append(dict(parameter=key,value=nearest['value'],result=run(nearest['config'],'validation','neighbor')))
        save(ROOT/'native-neighbors.json',checks)
    save(ROOT/'progress.json',dict(state='native-complete',completed_utc=datetime.now(timezone.utc).isoformat()))

if __name__=='__main__':main()
