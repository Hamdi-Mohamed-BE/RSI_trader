"""Preserve broker market-closed rejects; relax only the zero-reject analysis assertion."""
import inspect,json,msvcrt,shutil,sys
import run as extension
n=extension.n;R=extension.R;P=extension.P
source=inspect.getsource(n.run)
old="assert not any(counters[k] for k in ['order_failed','close_failed'])"
new="""assert counters['close_failed']==0
  rejected=[x for x in events if x['event']=='order_failed']
  assert len(rejected)==counters['order_failed']
  assert all(x['note']=='market closed' for x in rejected),'Unexpected rejected entry'"""
assert source.count(old)==1
exec(compile(source.replace(old,new),str(R/'resume.py')+' [analysis assertion]', 'exec'),n.__dict__)
n.save(R/'ANALYSIS_EXCEPTION.json',dict(reason='Retain actual broker market-closed rejects in all rows without fictional fills',
 source_and_binary_unchanged=True,original_runner_hash=n.sha(P/'run.py'),extension_runner_hash=n.sha(R/'run.py'),
 analysis_resume_hash=n.sha(R/'resume.py'),only_changed_assertion=old,replacement=new))
with (P/'tester.lock').open('a+b') as lease:
 lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
 for tag in sys.argv[1:]:
  assert json.loads((R/'PARITY.json').read_text())['passed']
  out=R/'native'/tag
  archived=(out/'report.htm').exists() and not (out/'results.json').exists()
  n.run(tag,reanalyze=archived)
  began=json.loads((out/'owned-process.json').read_text())['started']
  for kind in ['gate','daily']+(['adx'] if extension.CASES[tag]['range_mode'] else []):
   target=out/(kind+'.csv')
   if not target.exists():
    origin=n.COMMON/(tag+'-'+kind+'.csv')
    assert origin.exists() and origin.stat().st_mtime>=began-2
    shutil.copy2(origin,target)
