"""Post-selection diagnostics only; never reselect using the validation window."""
import json
import numpy as np
from research import ROOT,ASSETS,save
from search import load,event,batch,portfolio,baseline

for asset in ASSETS:
 events,data,offsets,epochs,spec=load(asset);chosen=json.loads((ROOT/asset/'selected.json').read_text());u=ASSETS[asset]['unit']
 held=set(i for i,e in enumerate(events) if e['release_utc'][:10]>='2026-05-19')
 result={'holdout_cost_stress':{},'neighbors':{}}
 for mode in ('baseline','train'):
  params=np.array([baseline(asset) if mode=='baseline' else chosen[e['kind']][mode]['params_price'] for e in events])
  result['holdout_cost_stress'][mode]={}
  for label,sp,sl,de in [('moderate',u*.25,u*.25,100),('severe',u*.5,u*.75,250)]:
   paths=np.array([event(data[offsets[i]:offsets[i+1]],epochs[i],params[i],spec['point'],spec['commission_price_units'],sp,sl,de) for i in range(len(events))])
   result['holdout_cost_stress'][mode][label]=portfolio(paths,params,spec,held)
 for family in ('NFP','CPI','FOMC'):
  result['neighbors'][family]={}
  for mode in ('full','train'):
   original=np.array(chosen[family][mode]['params_price']);rows=[original]
   for col in (0,2,3,6,7):
    if col==6 and original[5]==0:continue
    for factor in (.8,1.2):
     p=original.copy();p[col]*=factor
     if col in (2,3,6):p[col]=max(spec['point'],round(p[col]/spec['point'])*spec['point'])
     if col==0:p[col]=min(120,max(5,round(p[col])))
     if col==7:p[col]=min(600,max(60,round(p[col])))
     rows.append(p)
   ps=np.unique(np.array(rows),axis=0)
   mask=np.array([e['kind']==family and (mode=='full' or e['release_utc'][:10]<'2026-05-19') for e in events])
   outcomes=batch(data,offsets,epochs,ps,spec['point'],spec['commission_price_units'],u*.25,u*.25,100)
   stats=[portfolio(outcomes[i,mask],p,spec) for i,p in enumerate(ps)]
   returns=[s['return_pct'] for s in stats]
   result['neighbors'][family][mode]=dict(samples=len(stats),min_return=min(returns),median_return=float(np.median(returns)),max_return=max(returns),positive_scenarios=int(sum(r>0 for r in returns)),rows=[dict(params_price=p.tolist(),stats=s) for p,s in zip(ps,stats)])
 save(ROOT/asset/'sensitivity.json',result)
 print(asset,json.dumps(result['holdout_cost_stress']),flush=True)
