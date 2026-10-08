"""Chronological search -> validation -> persisted freeze -> fixed holdout."""
from pathlib import Path
from datetime import datetime,timezone
import itertools,json
import runner as r
from build_engine import BASE
from search_plan import PLAN,STAGES,score
R=r.R

def append_trials(rows):
 p=R/'trials.json';old=r.load(p) if p.exists() else []
 keys={(x['stage'],x['index']) for x in old}
 old.extend(rows[i] for i in range(len(rows)) if (rows[i]['stage'],rows[i]['index']) not in keys)
 r.save(p,old)

def main():
 lock=r.lease()
 try:
  plan=R/'SEARCH-PLAN.json'
  if plan.exists():assert r.load(plan)==json.loads(json.dumps(PLAN))
  else:r.save(plan,PLAN)
  # Parity precedes optimisation; same symbol/dates/delay as the prior raw.
  parity=r.batch('parity',[BASE],'2025-10-08','2026-10-08',model=4,optimize=False,verbose=True)[0]
  old=r.load(R.parent/'News Fair Price Reversion Raw 2026-10-08/native/raw-USTEC/results.json')[1]
  keys=['open_epoch','close_epoch','side','volume','open_price','close_price','net_profit','initial_sl','initial_tp']
  assert [[t[k] for k in keys] for t in parity['trades']]==[[t[k] for k in keys] for t in old['trades']],'Raw reproduction mismatch'
  r.save(R/'PARITY.json',dict(passed=True,trades=len(parity['trades']),net=parity['metrics']['net'],fields=keys))
  gates=[]
  for name,start in [('raw-3y','2022-01-01'),('raw-5y','2020-01-01')]:
   row=r.batch(name,[BASE],start,'2025-01-01',model=4,optimize=False,verbose=True)[0]
   m=row['metrics'];checks=dict(pf_at_least_1_15=(m['pf'] or 0)>=1.15,trades_at_least_30=m['trades']>=30,positive_net=m['net']>0)
   gates.append(dict(stage=name,metrics=m,checks=checks,passed=all(checks.values())))
  r.save(R/'RAW-GATES.json',dict(rows=gates,passed=all(x['passed'] for x in gates),exploratory_authorized=True))
  beam=[BASE];pool=[]
  base=r.batch('development-base-single',[BASE],'2020-01-01','2024-01-01',model=4,optimize=False)[0]
  append_trials([base]);pool.append(base)
  for label,key,values in STAGES:
   cases=r.dedupe([dict(c,**{key:v}) for c in beam for v in values])
   rows=r.batch('development-'+label,cases,'2020-01-01','2024-01-01',model=4)
   append_trials(rows);pool.extend(rows)
   beam=[x['parameters'] for x in sorted(rows,key=score,reverse=True)[:2]]
   r.status('DEVELOPMENT '+label,top=[dict(parameters=x['parameters'],score=score(x),metrics=x['metrics']) for x in sorted(rows,key=score,reverse=True)[:2]])
  # Development-only neighbourhood; median score, not isolated peak.
  centres=r.dedupe(beam+[x['parameters'] for x in sorted(pool,key=score,reverse=True)[:3]])
  cases=[]
  for c in centres:
   cases.append(c)
   for k in PLAN['neighbourhood']:
    for factor in [.8,1.2]:
     v=round(c[k]*factor,4)
     if k=='hold_minutes':v=int(min(90,max(5,v)))
     cases.append(dict(c,**{k:v}))
  neighbours=r.batch('development-plateau',r.dedupe(cases),'2020-01-01','2024-01-01',model=4)
  append_trials(neighbours)
  lookup={r.digest(x['parameters']):x for x in neighbours}
  stability=[]
  for c in centres:
   family=[lookup[r.digest(c)]]
   for k in PLAN['neighbourhood']:
    for f in [.8,1.2]:
     v=round(c[k]*f,4)
     if k=='hold_minutes':v=int(min(90,max(5,v)))
     family.append(lookup[r.digest(dict(c,**{k:v}))])
   scores=sorted(score(x) for x in family);s=scores[len(scores)//2]
   stability.append(dict(parameters=c,plateau_median_score=s,positive_neighbours=sum(x['metrics']['net']>0 for x in family),neighbours=len(family)))
  stability.sort(key=lambda x:x['plateau_median_score'],reverse=True)
  finalists=[x['parameters'] for x in stability[:3]]
  validation=r.batch('validation-2024',finalists,'2024-01-01','2025-01-01',model=4,verbose=True)
  ranked=[]
  for row in validation:
   stable=next(x for x in stability if x['parameters']==row['parameters'])
   combined=(stable['plateau_median_score']+score(row,10))/2
   ranked.append(dict(parameters=row['parameters'],development_plateau=stable,validation_metrics=row['metrics'],selection_score=combined))
  ranked.sort(key=lambda x:x['selection_score'],reverse=True);selected=ranked[0]['parameters']
  r.save(R/'SELECTION.json',dict(stability=stability,validation_ranked=ranked,selected=selected,research_only=True))
  frozen=dict(parameters=selected,baseline=BASE,calendar_sha256=r.sha(R/'calendar.json'),engine_sha256=r.sha(R/'engine.mq5'),
   config_sha256=r.sha(R/'config.json'),search_plan_sha256=r.sha(plan),trials_sha256=r.sha(R/'trials.json'),
   selection_sha256=r.sha(R/'SELECTION.json'),holdout_label=r.CONFIG['holdout_label'],research_only=True)
  fp=R/'FROZEN.json'
  if fp.exists():assert r.load(fp)['locked']==frozen,'Selection freeze changed'
  else:r.save(fp,dict(locked=frozen,frozen_at_utc=datetime.now(timezone.utc).isoformat()))
  # No selection occurs below this line.
  r.batch('in-sample-selected',[selected],'2020-01-01','2025-01-01',model=4,optimize=False,verbose=True)
  r.batch('holdout',[BASE,selected],'2025-01-01','2026-10-08',model=4,verbose=True)
  for name,start in [('recent-1y','2025-10-08'),('recent-6m','2026-04-08'),('recent-3m','2026-07-08')]:
   r.batch(name,[BASE,selected],start,'2026-10-08',model=4,verbose=True)
  for delay in [500,1000]:
   r.batch('delay-'+str(delay),[selected],'2025-01-01','2026-10-08',model=4,optimize=False,verbose=True,delay=delay)
  r.batch('generated-tick-diagnostic',[BASE,selected],'2025-01-01','2026-10-08',model=0,verbose=True)
  r.status('NATIVE COMPLETE: frozen evidence audit next')
 finally:lock.close()

if __name__=='__main__':main()
