"""Extend the frozen raw Germany/Nasdaq transfer to independent 3-/5-year runs.

Research only: no optimisation, production edits, deployment or active-account API.
"""
from datetime import datetime,timezone
from pathlib import Path
import importlib.util,json,msvcrt

R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('germany_transfer',R/'run.py')
transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer)
transfer.WINDOWS={'3y':('2023-10-07','2026-10-07'),'5y':('2021-10-07','2026-10-07')}

def main():
 original={str(p):transfer.sha(p) for p in (transfer.SRC,transfer.SRC.with_suffix('.ex5'),transfer.SET)}
 saved=json.loads((R/'RESULTS.json').read_text())
 assert saved['production_unchanged'] and saved['production_fingerprints']==original
 assert len(saved['results'])==6
 lock=(transfer.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b')
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 try:
  extended=list(saved['results'])
  for window in transfer.WINDOWS:
   for symbol in ('DE30','USTEC'):
    extended.append(transfer.case(symbol,window))
    transfer.save(R/'full-period-progress.json',{'results':extended,'complete':False})
  assert all(transfer.sha(Path(p))==digest for p,digest in original.items()),'Production file changed'
  transfer.save(R/'FULL_RESULTS.json',dict(results=extended,production_unchanged=True,production_fingerprints=original,no_live_deployment=True,no_optimisation=True))
  transfer.save(R/'status.json',dict(message='Complete: ten comparisons including three and five years',completed_utc=datetime.now(timezone.utc).isoformat()))
  print('COMPLETE: ten native comparisons; production files unchanged.',flush=True)
 finally:lock.close()

if __name__=='__main__':main()
