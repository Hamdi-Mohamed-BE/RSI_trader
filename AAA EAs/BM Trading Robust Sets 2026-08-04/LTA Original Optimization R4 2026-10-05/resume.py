"""Continue frozen search, excluding explicitly audited execution-rejected passes."""
from pathlib import Path
import importlib.util,json,msvcrt,re,hashlib,gzip
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('frozen_plan',R/'plan.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
n=p.n
original_run=p.run_params
original_rank=p.rank

def rejected(pvals,window,model,prefix,e,tag):
    out=R/'native'/tag
    report=out/'report.htm';manifest=json.loads((out/'manifest.json').read_text())
    assert report.exists() and manifest['start']==window[0] and manifest['end_exclusive']==window[1] and manifest['model']==model
    events=n.csvrows(out/'events.csv');deals=n.csvrows(out/'deals.csv');trace=n.csvrows(out/'equity.csv')
    trades,ledger=n.reconstruct(deals,events,0)
    audit=n.native_deal_audit(report,deals)
    native=n.h._native_metrics(report);body=n.h._read_report(report)
    from app.mt5_evidence_jobs import _number,_metric
    native['equity_dd_pct']=_number(_metric(body,'Equity Drawdown Relative'))
    native['balance_dd_pct']=_number(_metric(body,'Balance Drawdown Relative'))
    assert abs(sum(t['net'] for t in trades)-native['net_profit'])<.021
    actual=n.h._report_inputs(report)
    assert all(k in actual and n.h._same_setting(v,actual[k]) for k,v in manifest['inputs'].items())
    journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
    assert 'testing with execution delay 150 milliseconds' in journal
    assert not re.search(r'access violation|array out of range|zero divide|initialization failed|stop out|margin call',journal,re.I)
    m=n.metrics(trades,trace)
    days=(n.datetime.strptime(window[1],'%Y.%m.%d')-n.datetime.strptime(window[0],'%Y.%m.%d')).days
    m['trades_month']=len(trades)/(days/30.4375)
    q=dict(case=tag,model=model,window=list(window),inputs=actual,native=native,metrics=m,
       report_sha256=n.sha(report),binary_sha256=manifest['source_hashes']['binary'],
       trades=trades,ledger=ledger,counters=e.args[0],deal_audit=audit,
       disqualified=True,qualification_reason='Execution failure; excluded before ranking')
    n.save(out/'disqualified-results.json',q)
    record=p.slim(q);record.update(parameters=pvals,parameter_id=p.sha_obj(pvals),disqualified=True,
       qualification_reason=q['qualification_reason'])
    records=json.loads((R/'SEARCH RESULTS.json').read_text())
    if not any(x['case']==tag for x in records):records.append(record);p.save('SEARCH RESULTS.json',records)
    return record

def run(pvals,window,model=0,prefix='D'):
    pvals=p.canonical(pvals);tag=prefix+'-'+p.sha_obj(dict(p=pvals,window=window,model=model))
    cached=R/'native'/tag/'disqualified-results.json'
    if cached.exists():
        q=json.loads(cached.read_text());record=p.slim(q)
        record.update(parameters=pvals,parameter_id=p.sha_obj(pvals),disqualified=True,qualification_reason=q['qualification_reason'])
        return record
    try:return original_run(pvals,window,model,prefix)
    except AssertionError as e:
        if not(e.args and isinstance(e.args[0],dict) and 'entries' in e.args[0] and
               any(e.args[0].get(k,0)>0 for k in ['order_failed','close_failed','modify_failed'])):raise
        q=rejected(pvals,window,model,prefix,e,tag)
        print('DISQUALIFIED '+tag+' execution failure; other frozen settings continue',flush=True)
        return q

def rank(r,*args,**kw):
    if r.get('disqualified'):return (-1,0,0,0,0)
    return original_rank(r,*args,**kw)

if __name__=='__main__':
    signature={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['resume.py','RECOVERY.md']}
    frozen=R/'RECOVERY FROZEN.json'
    if frozen.exists():assert json.loads(frozen.read_text())==signature
    else:p.save(frozen.name,signature)
    assert n.freeze()==json.loads((R/'build.json').read_text())['frozen']
    p.run_params=run;p.rank=rank
    lock=n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock'
    with lock.open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        p.search();p.plateau();p.choose();p.confirm()
