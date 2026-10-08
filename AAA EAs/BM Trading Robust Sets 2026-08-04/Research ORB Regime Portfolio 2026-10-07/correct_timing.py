"""Semantics repair only. Keep the originally frozen inputs; no re-selection."""
from datetime import datetime,timezone
import runner as r
def main():
 lock=r.lease();old=r.load(r.R/'FROZEN.json');f=dict(old)
 f.update(created_utc=datetime.now(timezone.utc).isoformat(),engine_sha256=r.sha(r.R/'engine.mq5'),
  parent_freeze_sha256=r.sha(r.R/'FROZEN.json'),unique_tested_configurations=old['unique_tested_configurations']+6,
  correction='Strict two-sided NY entry window. Same original finalist inputs; no OOS tuning. Original preliminary figures withdrawn.',
  oos_status='Retrospective re-evaluation after implementation bug discovery; NOT unseen validation')
 if (r.R/'CORRECTED FROZEN.json').exists():
  prior=r.load(r.R/'CORRECTED FROZEN.json');assert prior['engine_sha256']==f['engine_sha256'];f=prior
 else:r.save(r.R/'CORRECTED FROZEN.json',f)
 corrected={};evaluations={}
 for symbol,z in f['symbols'].items():
  declared={'raw':z['raw'],'breakout':z['selected']['0'],'reversal':z['selected']['1'],'hybrid':z['selected']['2']}
  cases=r.dedupe(list(declared.values()))
  dev=r.batch('timing-v2-development-'+symbol,cases,*r.CONFIG['development'],symbol=symbol)
  val=r.batch('timing-v2-validation-'+symbol,cases,*r.CONFIG['validation'],symbol=symbol)
  corrected[symbol]=dict(development=dev,validation=val);r.save(r.R/'CORRECTED DIAGNOSTICS.json',corrected)
  rows=r.batch('timing-v2-oos-'+symbol,cases,*r.CONFIG['oos'],model=4,optimize=True,verbose=True,symbol=symbol)
  for label,case in declared.items():evaluations[symbol+' '+label]=next(x for x in rows if x['parameters']==case)
  r.save(r.R/'EVALUATION.json',evaluations)
 r.status('Corrected native evaluation complete; no midnight entries accepted; original settings unchanged')
if __name__=='__main__':main()
