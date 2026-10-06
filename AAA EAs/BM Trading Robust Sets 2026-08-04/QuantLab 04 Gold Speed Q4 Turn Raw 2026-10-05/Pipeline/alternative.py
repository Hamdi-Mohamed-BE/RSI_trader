"""Validation-frozen tuned comparator, diagnostic only, never selects on recent data."""
import json,sys,msvcrt
import search as n
R=n.ROOT
f=n.load(R/'FROZEN FINAL.json')
cs=[r for r in f['combinations'] if r.get('variant')!='UNCHANGED_RAW']
pick=max(cs,key=lambda r:n.score(r['result']))
frozen=dict(cases=f['cases'],slots=pick['slots'],validation=pick['result'],qualified=pick['qualified'],scope='Best TUNED combination on validation only; diagnostic, no future retuning',plan_sha256=n.sha(R/'ALTERNATIVE PLAN.txt'))
path=R/'FROZEN TUNED COMPARATOR.json'
if path.exists():assert n.load(path)==frozen
else:n.save(path,frozen)
results={}
with (n.TESTER/'gold-speed-pipeline.lock').open('a+b') as lease:
    lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
    if frozen['slots']==f['slots']:
        allres=n.load(R/'FINAL RESULTS.json');results={k:allres[k] for k in ['5Y','3Y','1Y','6M','3M']}
    else:
        for label,window in [('5Y',n.WEB['5y']),('3Y',n.WEB['3y']),('1Y',n.RECENT),('6M',n.WEB['6m']),('3M',n.WEB['3m'])]:
            results[label]=n.batch('tuned-comparator-'+label,frozen['cases'],*window,model=4,optimize=False,slots=frozen['slots'])[0];n.save(R/'TUNED COMPARATOR RESULTS.json',results)
n.save(R/'TUNED COMPARATOR RESULTS.json',results)
trials=[]
for path in sorted(n.OUT.glob('*/results.json')):trials+=n.load(path)
n.save(R/'SEARCH RESULTS.json',trials)
count=n.load(R/'TRIAL ACCOUNTING.json');count['total_native_passes']=len(trials)
configs=set()
for r in trials:
    if r['parameters'] is not None:configs.add(n.digest(r['parameters']))
    else:
        receipt=n.load(n.OUT/r['stage']/'manifest.json')
        configs.update(n.digest(receipt['cases'][i]) for i in r['slots'] or [])
count['unique_parameter_vectors']=len(configs)
count['failed_native_attempts']=len(list(n.OUT.glob('*/FAILED-ATTEMPT-*-empty.htm')))
count['all_included_in_DSR']=len(trials)+81+count['failed_native_attempts'];n.save(R/'TRIAL ACCOUNTING.json',count)
n.status('TUNED COMPARATOR COMPLETE',passes=len(trials))
