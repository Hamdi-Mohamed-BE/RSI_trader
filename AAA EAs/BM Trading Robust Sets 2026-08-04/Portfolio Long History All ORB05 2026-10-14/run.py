"""Restore exact all-0.5R long histories; reuse only verified identical active source/input cases."""
from pathlib import Path
import hashlib,importlib.util,json,msvcrt,sys,traceback
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;OLD=BASE/'Portfolio Long History 2026-10-08'
sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('prior_long_history',OLD/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROOT=ROOT;m.n.R=ROOT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main():
    ROOT.mkdir(exist_ok=True);plan=m.frozen_plan();oldplan=read(OLD/'PLAN.json');oldstate=read(OLD/'RUN_STATUS.json')
    state=dict(window=[m.n.START,m.n.END],total=len(plan['cases']),complete={},failed={},missing={},live_changes=False)
    if (ROOT/'RUN_STATUS.json').exists():state=read(ROOT/'RUN_STATUS.json')
    for row in plan['cases']:
        case=row['case_id']
        if case in state['complete'] or case in state['missing']:continue
        if row['slug']=='gold-news-v9-direction':
            state['missing'][case]='No historical pre-release V9 prediction ledger. Live bridge intentionally not called.';continue
        same_source=[]
        current=m.n.closure(Path(row['source']))
        for prior in oldplan['cases']:
            if prior['source']!=row['source']:continue
            # A path match alone is not sufficient: every production include must still match.
            if all(prior['production_hashes'].get(str(p))==sha(p) for p in current):same_source.append(prior)
        reuse=m.verified_reuse(row,dict(oldplan,cases=same_source),oldstate)
        if reuse:
            state['complete'][case]=dict(reuse,source_closure_identical=True,active_inputs_reconciled=True)
            print('REUSE '+row['slug']+' '+case,flush=True)
    m.n.save(ROOT/'RUN_STATUS.json',state)
    pending=[r for r in plan['cases'] if r['case_id'] not in state['complete'] and r['case_id'] not in state['missing']]
    print('MATCHED '+str(len(state['complete']))+'; PENDING '+json.dumps([r['slug'] for r in pending]),flush=True)
    if '--plan-only' in sys.argv:return
    m.prepare_helpers()
    for row in pending:
        case=row['case_id']
        try:
            reuse=m.verified_reuse(row,plan,state)
            if reuse:
                state['complete'][case]=dict(reuse,source_closure_identical=True,active_inputs_reconciled=True)
                m.n.save(ROOT/'RUN_STATUS.json',state)
                print('REUSE NEW ACTIVE CASE '+case+' <- '+reuse['reused_case'],flush=True)
                continue
            assert not row['slug'].startswith('news-pulse-'),'Changed news source requires separate calendar-parity validation'
            binary,build=m.n.build(row);result=m.n.run_case(row,'long-'+case.split('-')[-1],binary,build)
            p=ROOT/'native'/result['tag']/'results.json'
            state['complete'][case]=dict(path=str(p),sha256=sha(p),trades=len(result['trades']),history_quality=result['native']['history_quality'])
            state['failed'].pop(case,None)
        except Exception as e:
            state['failed'][case]=dict(error=str(e),trace=traceback.format_exc()[-5000:]);print('FAILED '+case+' '+str(e),flush=True)
        m.n.save(ROOT/'RUN_STATUS.json',state)
        print('PROGRESS '+str(len(state['complete']))+'/'+str(state['total']),flush=True)
    assert not state['failed'],state['failed']
    assert all(sha(p)==v for row in plan['cases'] for p,v in row['production_hashes'].items())
    print('Long-history native sources complete; no production/live changes',flush=True)
if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        main()
