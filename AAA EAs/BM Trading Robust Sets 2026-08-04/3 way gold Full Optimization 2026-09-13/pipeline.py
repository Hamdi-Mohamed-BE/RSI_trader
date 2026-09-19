"""Native finalist selection, frozen diagnostics and allocation/risk stresses."""
import argparse,json,math
from datetime import datetime,timezone
from params import *
import native

def score(r,valid=False):
    n=r['trades'];minimum=20 if valid else 60
    if n<minimum:return -10000+n
    pf=max(.01,min(4,r['net_pf'] or .01));ret=r['return_pct'];dd=max(1,r['max_equity_dd_pct'])
    return 30*math.log(pf)+2*ret/dd+.12*ret-.55*dd-.2*max(0,(30 if valid else 90)-n)

def eligible(t,v):
    return all(r['net_profit']>0 and (r['net_pf'] or 0)>1.05 and r['max_equity_dd_pct']<=20 and not r['native_stopout'] for r in (t,v)) and t['trades']>=60 and v['trades']>=20

def select():
    frozen=ROOT/'frozen-selection.json'
    if frozen.exists():return json.loads(frozen.read_text())
    finalists=json.loads((ROOT/'Search'/'finalists.json').read_text());rows=[]
    for i,f in enumerate(finalists):
        c=f['config'];t=native.run(c,TRAIN,f'c{i+1}-train');v=native.run(c,VALID,f'c{i+1}-valid')
        rows.append(dict(config=c,id=ident(c),train=t['period'],validation=v['period'],eligible=eligible(t,v),rank=min(score(t),score(v,True)),
            train_stats={k:t[k] for k in ('return_pct','trades','net_win_rate','net_pf','max_equity_dd_pct')},validation_stats={k:v[k] for k in ('return_pct','trades','net_win_rate','net_pf','max_equity_dd_pct')}))
        save(ROOT/'native-finalists.json',rows)
    for name,window in [('train',TRAIN),('valid',VALID)]:native.run(DEFAULT,window,'raw-'+name)
    chosen=max(rows,key=lambda r:(r['eligible'],r['rank']))
    lock=dict(**chosen,frozen_at_utc=datetime.now(timezone.utc).isoformat(),holdout_seen_during_selection=False,
        historical_aggregate_previously_seen=True,source_hashes=native.hashes(),selection_rule='eligible first, worst chronological split score')
    save(frozen,lock)
    save(ROOT/'selected-config.json',chosen['config'])
    path=ROOT/'Sets'/'3 way gold - OPTIMIZED RESEARCH - 0.30pct per engine.set'
    path.write_text(''.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}\n' for k,v in chosen['config'].items()),encoding='utf-8')
    print('NATIVE SETTINGS FROZEN',chosen['id'],'eligible',chosen['eligible'],flush=True)
    return lock

def diagnostics(lock):
    c=lock['config'];assert lock['source_hashes']==native.hashes()
    out={}
    # The first call opens the previously locked latest-year diagnostic.
    for name in ('1y','6m','3y','5y','2019-2026'):
        out[name]=native.run(c,WINDOWS[name],'selected-'+name)
        save(ROOT/'main-results.json',out)
    stresses=[]
    for delay in (100,500):stresses.append(native.run(c,LOCKED,'delay',delay=delay))
    risks=[]
    for risk in (.15,.50):risks.append(native.run({**c,'InpRiskPerEnginePercent':risk},WINDOWS['5y'],'risk'))
    allocations=[]
    for mask in (1,2,4,3,5,6):
        cc=dict(c)
        for i,n in enumerate(('Momentum','Change','Breakout')):cc['Inp'+n+'RiskWeight']=float(bool(mask&(1<<i)))
        allocations.append(native.run(cc,WINDOWS['5y'],'allocation'+str(mask)))
    save(ROOT/'stress-results.json',dict(delay=stresses,risk=risks,allocations=allocations))
    print('ALL NATIVE VALIDATION AND STRESSES FINISHED',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--select-only',action='store_true');a=p.parse_args()
    assert json.loads((ROOT/'raw-parity.json').read_text())['passed']
    native.prepare();lock=select()
    if not a.select_only:diagnostics(lock)
