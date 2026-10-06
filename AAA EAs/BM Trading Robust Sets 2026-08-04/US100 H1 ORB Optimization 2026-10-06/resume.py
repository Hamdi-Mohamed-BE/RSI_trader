"""Retry only pre-strategy local-agent infrastructure failures; freeze unchanged."""
import gzip,msvcrt,re,shutil,time
import native as n
import plan
def pending_failure():
 pending=[p.parent for p in (n.R/'native').glob('*/owned-process.json') if not (p.parent/'results.json').exists()]
 if not pending:return None
 out=max(pending,key=lambda p:n.read(p/'owned-process.json')['started'])
 journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode() if (out/'journal.txt.gz').exists() else ''
 if 'tester agent authorization error' not in journal or 'ORB_SUMMARY audit_complete' in journal:return None
 assert re.fullmatch('[a-z0-9.-]+',out.name)
 rp=n.T/'reports/orbopt20261006'/(out.name+'.htm')
 assert not n.h._report_inputs(rp),'Never discard mismatched strategy inputs'
 n.g.free_wait()
 count=len(list(out.glob('failed-attempt-*')))+1
 dest=out/('failed-attempt-'+str(count));assert not dest.exists();dest.mkdir()
 for name in ['journal.txt.gz','owned-process.json','manifest.json']:shutil.copy2(out/name,dest/name)
 shutil.copy2(rp,dest/'report.htm')
 n.save(dest/'EXCLUDED.json',dict(reason='Local tester agent authorization error BEFORE strategy execution. Blank report excluded; unchanged settings retry only.',tag=out.name,attempt=count))
 print('ARCHIVED INFRASTRUCTURE FAILURE',out.name,count,flush=True)
 return out,count
if __name__=='__main__':
 with (n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  failed=pending_failure()
  if failed:time.sleep(15)
  while True:
   try:plan.search();break
   except AssertionError as error:
    if str(error)!='Native inputs mismatch':raise
    failed=pending_failure()
    if failed is None or failed[1]>=3:raise
    time.sleep(15)
