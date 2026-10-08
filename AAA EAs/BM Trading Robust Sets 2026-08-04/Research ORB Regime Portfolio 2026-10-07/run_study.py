"""Predeclared development experiments and locked two-year evaluation."""
from datetime import datetime,timezone
from pathlib import Path
import copy,sys
import runner as r,build_engine as e
R=r.R;C=r.CONFIG
def score(row):
 m=row['metrics']
 if not row['clean'] or m['trades']<60:return -1e6
 # PF/DD/trade support and annualised daily P&L, not the largest dollar peak.
 return min(m['pf'] or 0,2.5)+.15*m['daily_closed_balance_sharpe']-.015*m['equity_dd']
def proposals():
 cs=[]
 for mod in [0,1,2]:
  base=e.RAW|dict(module=mod)
  cs.append(base)
  for k,values in dict(range_minutes=[5,30],rvol_min=[.75,1,1.25],stop_atr=[.10,.15],markov=[1]).items():
   cs.extend(base|{k:v} for v in values)
  cs.extend(base|dict(range_min=low,range_max=high) for low,high in [(.03,.35),(.05,.25)])
  if mod!=1:
   cs.extend(base|dict(target_r=v) for v in [.5,1,1.5,3])
   cs.extend(base|dict(trail_atr=v) for v in [2,3,4])
 return r.dedupe(cs)
def main():
 lock=r.lease()
 cases=proposals()
 plan=dict(config=C,development_cases=cases,search='OFAT around the declared M15 2R control; then a combined candidate for each module; no OOS-dependent selection',
  selection='For each module select best clean development PF/Sharpe/DD-supported setting, plus one filtered combination. Validate those finalists before freezing. All inspected trials counted.',
  oos_status=C['oos_status'])
 if (R/'PLAN.json').exists():assert r.load(R/'PLAN.json')==plan
 else:r.save(R/'PLAN.json',plan)
 dev={};val={};freeze={}
 for symbol in C['symbols']:
  rows=r.batch('development-'+symbol,cases,*C['development'],symbol=symbol)
  dev[symbol]=rows
  combined=[]
  for mod in [0,1,2]:
   group=[x for x in rows if x['parameters']['module']==mod]
   best=max(group,key=score)['parameters']
   # Combine only factors that improved their own OFAT result versus raw.
   base=e.RAW|dict(module=mod);raw=next(x for x in group if x['parameters']==base)
   combo=base.copy()
   for keys in [('range_minutes',),('target_r',),('stop_atr',),('rvol_min',),('range_min','range_max'),('markov',),('trail_atr',)]:
    eligible=[x for x in group if all(x['parameters'][k]==base[k] for k in e.FIELDS if k not in keys)]
    if not eligible:continue
    win=max(eligible,key=score)
    if score(win)>score(raw)+.05:
     for k in keys:combo[k]=win['parameters'][k]
   combined.extend([best,combo])
  combined=r.dedupe(combined)
  extra=r.batch('combined-development-'+symbol,combined,*C['development'],symbol=symbol)
  dev[symbol]+=extra
  validation=r.batch('validation-'+symbol,r.dedupe([e.RAW]+combined),*C['validation'],symbol=symbol)
  val[symbol]=validation
  finalists=[]
  for x in validation:
   d=max([z for z in dev[symbol] if z['parameters']==x['parameters']],key=score)
   stability=min(score(x),score(d));finalists.append((stability,x))
  bymodule={}
  for mod in [0,1,2]:
   g=[x for s,x in finalists if x['parameters']['module']==mod]
   win=max(g,key=lambda x:min(score(x),max(score(z) for z in dev[symbol] if z['parameters']==x['parameters'])))
   bymodule[str(mod)]=win['parameters']
  freeze[symbol]=dict(selected=bymodule,raw=e.RAW,validation=[r.slim(x) for x in validation],
    development=[r.slim(x) for x in dev[symbol]],unique_asset_configurations=len(r.dedupe([x['parameters'] for x in dev[symbol]+validation])))
 r.save(R/'DEVELOPMENT.json',{k:[r.slim(x) for x in v] for k,v in dev.items()})
 frozen=dict(created_utc=datetime.now(timezone.utc).isoformat(),symbols=freeze,config_sha256=r.sha(R/'config.json'),
  engine_sha256=r.sha(R/'engine.mq5'),unique_tested_configurations=sum(z['unique_asset_configurations'] for z in freeze.values()),
  selection_finished_before_oos=True,live_changes=False)
 if (R/'FROZEN.json').exists():
  prior=r.load(R/'FROZEN.json');assert prior['symbols']==freeze and prior['engine_sha256']==frozen['engine_sha256'];frozen=prior
 else:r.save(R/'FROZEN.json',frozen)
 r.status('Frozen finalists; beginning retrospective two-year evaluation',trials=frozen['unique_tested_configurations'])
 records={}
 for symbol,z in freeze.items():
  for label,case in [('raw',e.RAW),('breakout',z['selected']['0']),('reversal',z['selected']['1']),('hybrid',z['selected']['2'])]:
   row=r.batch('oos-'+symbol+'-'+label,[case],*C['oos'],model=4,optimize=False,verbose=True,symbol=symbol)[0]
   records[symbol+' '+label]=row;r.save(R/'EVALUATION.json',records)
 r.status('Native evaluation complete; evidence audit next',native_finalists=len(records))
if __name__=='__main__':main()
