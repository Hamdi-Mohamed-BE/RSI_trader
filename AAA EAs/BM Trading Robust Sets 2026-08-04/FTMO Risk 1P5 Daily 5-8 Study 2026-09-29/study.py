"""Read-only market research using archived source streams; no terminal connectivity."""
from pathlib import Path
from datetime import datetime, timezone
import sys, json, hashlib, time
import numpy as np
import engine

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'Daily Equity Controls Audit 2026-09-29'
sys.path.insert(0,str(OLD))
import simulate as original
import payout_followup as payout

CONFIGS=[
    dict(name='Prior benchmark',risk=50.,fraction=.005,compound=False,loss=200.,target=400.,cap=0.),
    dict(name='Requested',risk=150.,fraction=.015,compound=False,loss=500.,target=800.,cap=0.),
    dict(name='Requested with buffer',risk=150.,fraction=.015,compound=False,loss=400.,target=800.,cap=0.),
    dict(name='Middle-risk diagnostic',risk=100.,fraction=.01,compound=False,loss=300.,target=800.,cap=0.),
    dict(name='Requested equity-sized',risk=150.,fraction=.015,compound=True,loss=500.,target=800.,cap=0.)]

def save(name,x):
    (ROOT/name).write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')

def metrics(v,logs):
    m=dict(zip(engine.FIELDS,map(float,v)))
    m['profit_factor']=float(v[8]/v[9]) if v[9]>0 else None
    m['win_rate']=float(100*v[7]/v[6]) if v[6]>0 else None
    m['max_risk_per_closed_trade']=float(logs[:,5].max()) if len(logs) else 0.
    return m

def execute(data,sp,days,origin,start,end,cfg,case,profit=0.,min_days=0,min_age=0,ftmo=True):
    lo=start-origin;hi=end-origin+1
    return engine.run(data['trades'],data['prices'][:,lo:hi],data['opens'][:,lo:hi],data['fresh'][:,lo:hi],
        sp,start,end,days[lo:hi],ftmo,cfg['loss'],cfg['target'],cfg['cap'],case['stress'],cfg['compound'],False,
        case['delay'],profit,min_days,min_age,case['haircut'],cfg['risk'],cfg['fraction'])

COUNTERS=dict(stages=0,reward_requests=0,closed_trades=0,accounting_max_error=0.)
def stage(data,sp,days,origin,start,end,cfg,case,profit,min_days,min_age):
    v,logs,_,_=execute(data,sp,days,origin,start,end,cfg,case,profit,min_days,min_age)
    m=metrics(v,logs)
    ok=m['stop_minute']>=0 and m['first_ftmo_breach_minute']<0 and m['open_at_end']==0
    assert np.isfinite(v).all()
    if m['open_at_end']==0:
        error=abs(m['balance']-10000.-float(logs[:,4].sum()))
        COUNTERS['accounting_max_error']=max(COUNTERS['accounting_max_error'],error)
        assert error<1e-6
    if len(logs):
        assert np.all(logs[:,2]>=logs[:,1])
        if not cfg['compound']:assert logs[:,5].max()<=cfg['risk']+1e-7
    if ok:
        assert m['balance']>=10000.+profit-1e-7
        opens=np.unique(days[logs[:,1].astype(int)-origin])
        assert len(opens)>=min_days
        assert m['stop_minute']-logs[:,1].min()>=min_age*1440
    COUNTERS['stages']+=1;COUNTERS['closed_trades']+=len(logs)
    return dict(start=start,end=int(m['stop_minute']) if m['stop_minute']>=0 else end,success=bool(ok),
        first_entry=int(logs[:,1].min()) if len(logs) else None,profit=m['balance']-10000.,metrics=m)

def verify_path(p):
    for a,b in zip(p['stages'],p['stages'][1:]):
        assert a['success'] and a['metrics']['first_ftmo_breach_minute']<0
        assert b['start']>a['end']
    if p['breach'] is not None:
        assert p['stages'][-1]['end']==p['breach']
        assert not p['stages'][-1]['success']
    for rw in p['rewards']:
        assert rw['gross']>=50.-1e-8
        assert abs(.8*rw['gross']-rw['trader_share'])<1e-7
        assert p['funded'] is not None and rw['request']>=p['funded']+14*1440
        assert p['breach'] is None or rw['request']<p['breach']
        COUNTERS['reward_requests']+=1

def main():
    a=engine.read(OLD/'recent-AUDIT.json');z=np.load(OLD/'recent-prepared.npz')
    data={k:z[k] for k in z.files};origin=a['start'];end=a['end'];sp=engine.specs();days=engine.clock(origin,end)
    assert len(data['trades'])==972 and np.all(data['trades'][:,11]==1)
    assert set(int(k) for k in data['trades'][:,2])==set(a['keys'].index(k) for k in a['ftmo_keys'])
    paths=[OLD/x for x in ['simulate.py','payout_followup.py','recent-prepared.npz','recent-AUDIT.json','MODEL_SPECS.json','PAYOUT_RESULTS.json']]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save('SOURCE_AUDIT.json',dict(hashes=hashes,start=origin,end=end,trades=len(data['trades']),eas=a['ftmo_keys'],
        method='M1 source-trade overlay; copied engine with optional risk parameters only',configs=CONFIGS))
    # Exact default backward compatibility, including every returned log/curve element.
    ref=original.run(data['trades'],data['prices'],data['opens'],data['fresh'],sp,origin,end,days,True,200.,400.,0.,False,False,False)
    got=execute(data,sp,days,origin,origin,end,CONFIGS[0],payout.CASES[0])
    for x,y in zip(ref,got):np.testing.assert_array_equal(x,y)
    old_results=engine.read(OLD/'RESULTS.json')
    saved=[x for x in old_results if x['id']=='recent-FTMO13-1-0-A_loss2_goal4'][0]
    for k,v in zip(engine.FIELDS,got[0]):assert abs(saved['metrics'][k]-float(v))<1e-8,(k,v,saved['metrics'][k])
    print('Exact old-engine and saved-baseline regression passed.',flush=True)
    payout.stage=stage # Research-only dependency injection; old files remain unchanged.
    first=int(datetime(2025,9,29,tzinfo=timezone.utc).timestamp()//60)
    starts=list(range(first,end-30*1440+1,7*1440))
    result=dict(period=a,continuous=[],scenarios=[],starts=starts)
    tic=time.time()
    for ci,cfg in enumerate(CONFIGS):
        for ki,case in enumerate(payout.CASES):
            v,logs,daily,curve=execute(data,sp,days,origin,origin,end,cfg,case)
            m=metrics(v,logs)
            np.savez_compressed(ROOT/f'continuous-{ci}-{ki}.npz',logs=logs,daily=daily,curve=curve)
            result['continuous'].append(dict(config=cfg,case=case,metrics=m))
            pp=[payout.lifecycle(data,sp,days,origin,s,min(end,s+180*1440),cfg,case) for s in starts]
            for p in pp:verify_path(p)
            ss=[payout.summarize(pp,h) for h in [30,60,90,120,180]]
            for s in ss:
                h=s['horizon_days']*1440
                complete=[p for p in pp if p['end']-p['start']>=h]
                s['counts']['reward_and_no_breach']=sum(any(r['request']<=p['start']+h for r in p['rewards']) and (p['breach'] is None or p['breach']>p['start']+h) for p in complete)
            result['scenarios'].append(dict(config=cfg,case=case,paths=pp,summary=ss))
            save('RESULTS.json',result)
            s=ss[-1]
            print(json.dumps(dict(config=cfg['name'],case=case['name'],seconds=round(time.time()-tic,1),
                continuous_return=m['return_pct'],continuous_breach=m['first_ftmo_breach_minute'],
                horizon180=s['counts'],mean_payout=s['total_trader_share_all_starts_usd']['mean'])),flush=True)
    # Original baseline lifecycle must also match saved paths at every scenario start.
    baseline=engine.read(OLD/'PAYOUT_RESULTS.json')
    for item in result['scenarios'][:4]:
        old=next(x for x in baseline['scenarios'] if x['config']['name']=='A loss2 goal4' and x['case']['name']==item['case']['name'])
        assert len(old['paths'])==len(item['paths'])
        for p,q in zip(old['paths'],item['paths']):
            for key in ['start','end','phase1','phase2','funded','breach','envelope_flag','rewards']:assert p[key]==q[key],key
    for p in paths:assert hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p)]
    save('CHECKS.json',dict(**COUNTERS,continuous_runs=len(result['continuous']),paths=len(result['scenarios'])*len(starts),
        exact_engine_regression=True,exact_saved_baseline=True,exact_baseline_lifecycle=True,source_files_unchanged=True,
        runtime_seconds=time.time()-tic))

if __name__=='__main__':main()
