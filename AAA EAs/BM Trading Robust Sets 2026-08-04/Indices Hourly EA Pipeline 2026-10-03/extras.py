"""Full-horizon diagnostic and separate native functional test."""
import gzip,json,shutil
import run_native as n
def main():
 rows=json.loads((n.R/'NATIVE.json').read_text());assert len(rows)>=27
 for asset in n.ASSETS:
  tag=f'hourprof-20261003-{asset}-5y-coverage1m'
  if not any(r['tag']==tag for r in rows):rows.append(n.one(asset,'5y','coverage1m',deposit=1000000))
  n.save(n.R/'NATIVE.json',rows)
 src=n.R/'FaultTrials.mq5';log=n.R/'fault-compile.log'
 n.run(f'"{n.T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',timeout=120)
 assert '0 errors, 0 warnings' in n.read(log),n.read(log)[-3000:]
 shutil.copy2(src.with_suffix('.ex5'),n.DEST/'FaultTrials.ex5')
 original=n.SOURCE;n.SOURCE=src
 result=n.one('US30','3m','fault',expert='FaultTrials');n.SOURCE=original
 j=gzip.decompress((n.R/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
 assert 'HOURLY_FAULT_COMPLETE exercised=true passed=true' in j,j[-2500:]
 n.save(n.R/'FUNCTIONAL.json',{'native_fault_pass':True,'test':result,'production_source_sha256':n.sha(original),'evidence_scope':'tester-only volatile restart / broker-position recovery / simulated manual close inside entry minute; not an actual live reattachment','live_global_persistence_review':'consumed hour/day stored and flushed before request, scoped by account/server/symbol/magic','active_terminal_not_installed':True})
 print('EXTRAS COMPLETE',flush=True)
if __name__=='__main__':main()
