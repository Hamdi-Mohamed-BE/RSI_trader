"""Native raw tests; fixed enumerated cases, not optimisation on the year."""
import json
import runner as r
def main():
 frozen=r.load(r.R/'FROZEN.json')
 assert frozen['config_sha256']==r.sha(r.R/'config.json') and frozen['engine_sha256']==r.sha(r.R/'engine.mq5') and frozen['calendar_sha256']==r.sha(r.R/'calendar.json')
 lock=r.lease();results={}
 try:
  for symbol in r.CONFIG['symbols']:
   rows=r.batch('raw-'+symbol,frozen['cases'],r.CONFIG['start'],r.CONFIG['end_exclusive'],model=4,optimize=True,verbose=True,symbol=symbol)
   for label,row in zip(r.CONFIG['variants'],rows):results[symbol+' '+label]=row
   r.save(r.R/'RESULTS.json',results)
  print(json.dumps({k:v['metrics'] for k,v in results.items()},indent=2),flush=True)
 finally:lock.close()
if __name__=='__main__':main()
