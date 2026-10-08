"""Same frozen strategy settings, independent native accounts run in parallel."""
import runner as r
def main():
 lock=r.lease();f=r.load(r.R/'FROZEN.json');records={}
 assert f['engine_sha256']==r.sha(r.R/'engine.mq5')
 for symbol,settings in f['symbols'].items():
  declared={'raw':settings['raw'],'breakout':settings['selected']['0'],'reversal':settings['selected']['1'],'hybrid':settings['selected']['2']}
  cases=r.dedupe(list(declared.values()));rows=[]
  previous=r.R/'native/oos-USTEC-raw/results.json'
  if symbol=='USTEC' and previous.exists():
   rows=r.load(previous);cases=[z for z in cases if z!=settings['raw']]
  if cases:rows+=r.batch('locked-grouped-'+symbol,cases,*r.CONFIG['oos'],model=4,optimize=True,verbose=True,symbol=symbol)
  for label,case in declared.items():records[symbol+' '+label]=next(z for z in rows if z['parameters']==case)
  r.save(r.R/'EVALUATION.json',records)
  # Identical raw/breakout settings reuse the same verified account, not fake extra tests.
  if symbol=='USTEC':
   repeat=r.R/'native/oos-USTEC-breakout/results.json'
   if repeat.exists():
    old=r.load(repeat)[0];control=records['USTEC raw'];assert old['trades']==control['trades']
    r.save(r.R/'CONTROL REPEAT PARITY.json',dict(identical_native_ledger=True,trades=len(control['trades']),native_net=control['metrics']['net']))
 r.status('Grouped native evaluations complete; frozen parameters unchanged',unique_final_native_accounts=sum(len(r.dedupe([z['raw']]+list(z['selected'].values()))) for z in f['symbols'].values()))
if __name__=='__main__':main()
