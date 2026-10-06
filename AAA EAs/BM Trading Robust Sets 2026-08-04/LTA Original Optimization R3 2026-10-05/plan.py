"""Frozen staged search of the unchanged original LTA strategy; isolated MT5 only."""
from pathlib import Path
import hashlib,importlib.util,json,math,msvcrt,sys
import numpy as np
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('lta_opt_native',R/'native.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)

DEV=('2021.10.05','2024.10.05')
VAL=('2024.10.05','2025.10.05')
RECENT=('2025.10.05','2026.10.05')
DEFAULTS=dict(InpExecutionTF=15,InpUseEM1DoubleWick=True,InpUseEM2InternalSwing=False,
 InpUseEM3CME=False,InpUseEM4Continuation=True,InpOptStopMode=0,InpOptStopFactor=1.0,
 InpOptStopATR=1.5,InpOptStopPricePct=.25,InpRewardRisk=3.0,
 InpOptManage=0,InpOptTriggerR=1.0,InpOptTrailATR=1.0,
 InpUseDynamicTrailingSL=False,InpDynamicTriggerFraction=.50,InpDynamicLockFraction=.20,
 InpMoveAllBEAt1R=False,InpOptADXMin=0.0,InpOptDI=False,
 InpResearchSession=0,InpAllowLongs=True,InpAllowShorts=True,InpOptMaxTrades=0,InpOptSkipDays=0)

def models(**kw):
    return {f'InpUseEM{i}{suffix}':i in kw['on'] for i,suffix in [(1,'DoubleWick'),(2,'InternalSwing'),(3,'CME'),(4,'Continuation')]}

STAGES=[
 ('timeframe',[{'InpExecutionTF':x} for x in [5,15,30,60]]),
 ('entry',[models(on=x) for x in [(1,4),(1,),(4,),(2,),(3,),(1,2,3,4)]]),
 ('stop',[dict(InpOptStopMode=0,InpOptStopFactor=x) for x in [1.0,.75,1.25,1.5]]+
          [dict(InpOptStopMode=1,InpOptStopFactor=1.0,InpOptStopATR=x) for x in [1,1.5,2]]+
          [dict(InpOptStopMode=2,InpOptStopFactor=1.0,InpOptStopPricePct=.25)]),
 ('target',[{'InpRewardRisk':x} for x in [.5,.6,.75,1,1.25,1.5,2,2.5,3,4,5,6]]),
 ('management',[dict(InpOptManage=0,InpUseDynamicTrailingSL=False),
   dict(InpOptManage=1,InpOptTriggerR=.5,InpUseDynamicTrailingSL=False),
   dict(InpOptManage=1,InpOptTriggerR=1,InpUseDynamicTrailingSL=False),
   dict(InpOptManage=0,InpUseDynamicTrailingSL=True),
   dict(InpOptManage=2,InpOptTriggerR=1,InpOptTrailATR=1,InpUseDynamicTrailingSL=False),
   dict(InpOptManage=2,InpOptTriggerR=1,InpOptTrailATR=2,InpUseDynamicTrailingSL=False),
   dict(InpOptManage=3,InpOptTriggerR=1,InpUseDynamicTrailingSL=False)]),
 ('session',[{'InpResearchSession':x} for x in [0,1,2,3,4]]),
 ('direction',[dict(InpAllowLongs=l,InpAllowShorts=s) for l,s in [(True,True),(True,False),(False,True)]]),
 ('ADX_DI',[dict(InpOptADXMin=a,InpOptDI=d) for a,d in [(0,False),(20,False),(25,False),(0,True),(20,True),(25,True)]]),
 ('daily_management',[dict(InpOptMaxTrades=t,InpOptSkipDays=d) for t,d in [(0,0),(1,0),(2,0),(0,1),(0,2),(0,3)]])]

def sha_obj(o):return hashlib.sha256(json.dumps(o,sort_keys=True).encode()).hexdigest()[:14]
def save(name,v):n.save(R/name,v)
def slim(q):return {k:q[k] for k in ['case','model','window','inputs','native','metrics','report_sha256','binary_sha256']}
def canonical(p):
    p=dict(p)
    if p['InpOptStopMode']!=1:p['InpOptStopATR']=DEFAULTS['InpOptStopATR']
    if p['InpOptStopMode']!=2:p['InpOptStopPricePct']=DEFAULTS['InpOptStopPricePct']
    if p['InpOptManage']==0:p['InpOptTriggerR']=1.0;p['InpOptTrailATR']=1.0
    elif p['InpOptManage']!=2:p['InpOptTrailATR']=1.0
    return p

def run_params(p,window,model=0,prefix='D'):
    p=canonical(p)
    tag=prefix+'-'+sha_obj(dict(p=p,window=window,model=model))
    n.CASES[tag]=dict(label=tag,mode=0,tf=p['InpExecutionTF'],safe=True,
                       start=window[0],end=window[1],model=model,overrides=p)
    try:q=n.run(tag)
    except Exception as e:
        # A failed native pass is preserved and never ranked as a profitable zero.
        save('rejections/'+tag+'.json',dict(case=tag,settings=p,window=window,model=model,error=str(e)))
        raise
    record=slim(q);record['parameters']=p;record['parameter_id']=sha_obj(p)
    path=R/'SEARCH RESULTS.json'
    records=json.loads(path.read_text()) if path.exists() else []
    if not any(x['case']==tag for x in records):records.append(record);save('SEARCH RESULTS.json',records)
    return record

def rank(r,minimum=60,pfmin=1.10):
    m=r['metrics'];pf=m.get('pf') or 0;wr=m.get('win_rate') or 0
    if m['trades']<minimum or m['net_profit']<=0 or pf<pfmin:return (-1,0,0,0,0)
    match=int(pf>=1.20 and wr>=50)
    dd=max(r['native']['equity_dd_pct'],1.0)
    # Geometric combination penalises isolated return peaks and sparse samples.
    strength=(pf-1)*math.sqrt(m['trades'])*math.sqrt(max(m['return_pct'],0)/dd)
    return (match,strength,m.get('sharpe_daily_equity') or -99,
            m['win_streak']-m['loss_streak'],wr)

def search():
    assert json.loads((R/'PARITY.json').read_text())['passed']
    carry=[dict(DEFAULTS)]
    for stage,changes in STAGES:
        done=R/('stage-'+stage+'.json')
        if done.exists():carry=[x['parameters'] for x in json.loads(done.read_text())['carry']];continue
        trials={sha_obj(canonical({**p,**change})):canonical({**p,**change}) for p in carry for change in changes}
        results=[]
        for p in trials.values():results.append(run_params(p,DEV))
        good=sorted((x for x in results if rank(x)[0]>=0),key=rank,reverse=True)
        assert good,'No positive minimum-sample candidates at stage '+stage
        carry=[x['parameters'] for x in good[:3]]
        save(done.name,dict(stage=stage,tested=len(trials),carry=good[:3],all_cases=[x['case'] for x in results]))
        print('STAGE '+stage+' complete: '+str([(x['metrics']['pf'],x['metrics']['win_rate'],x['metrics']['trades']) for x in good[:3]]),flush=True)
    save('DEVELOPMENT FINALISTS.json',[run_params(p,DEV) for p in carry])

def plateau():
    chosen=json.loads((R/'DEVELOPMENT FINALISTS.json').read_text());checks=[]
    for row in chosen:
        p=row['parameters'];neighbours=[]
        for rr in [.8,1.,1.2]:
            for stop in [.8,1.,1.2]:
                q={**p,'InpRewardRisk':max(.5,p['InpRewardRisk']*rr),'InpOptStopFactor':p['InpOptStopFactor']*stop}
                neighbours.append(run_params(q,DEV))
        unique={r['case']:r for r in neighbours};ns=list(unique.values())
        eligible=[x for x in ns if x['metrics']['trades']>=30]
        fraction=sum(x['metrics']['net_profit']>0 for x in eligible)/len(ns)
        pf=float(np.median([x['metrics']['pf'] or 0 for x in eligible])) if eligible else 0
        checks.append(dict(finalist=row,neighbours=ns,positive_fraction=fraction,median_pf=pf,passed=fraction>=2/3 and pf>=1.10))
    save('PLATEAUS.json',checks)

def choose():
    checks=json.loads((R/'PLATEAUS.json').read_text());allrows=[]
    for check in checks:
        p=check['finalist']['parameters']
        d=run_params(p,DEV,4,'NDEV');v=run_params(p,VAL,4,'NVAL')
        allrows.append(dict(development=d,validation=v,plateau=check['passed']))
    good=[x for x in allrows if x['plateau'] and rank(x['development'])[0]>=0 and rank(x['validation'],20,1.15)[0]>=0]
    save('NATIVE FINALISTS.json',allrows)
    if not good:
        save('SELECTION.json',dict(qualified_validation=False,reason='No finalist passed plateau + native development + validation',candidate=max(allrows,key=lambda x:rank(x['validation'],0,0))))
    else:
        selected=max(good,key=lambda x:rank(x['validation'],20,1.15))
        save('SELECTION.json',dict(qualified_validation=True,candidate=selected))
    print('SELECTION FROZEN before recent-window tests',flush=True)

def confirm():
    selected=json.loads((R/'SELECTION.json').read_text())['candidate']['validation']['parameters']
    windows={'1Y':RECENT,'6M':('2026.04.05','2026.10.05'),'3M':('2026.07.05','2026.10.05'),
             '3Y':('2023.10.05','2026.10.05'),'5Y':('2021.10.05','2026.10.05'),'OLDER':('2019.10.05','2021.10.05')}
    records=[]
    for w,dates in windows.items():
        for variant,p in [('CURRENT',DEFAULTS),('CANDIDATE',selected)]:
            r=run_params(p,dates,4,'T'+w);r.update(period=w,variant=variant);records.append(r)
            save('COMPARISON.json',records)

def parity():
    new=run_params(DEFAULTS,RECENT,4,'PARITY')
    old=json.loads((n.B/'LTA VWAP Developing POC Comparison 2026-10-05/native/SAFE_M15/results.json').read_text())
    q=json.loads((R/'native'/new['case']/'results.json').read_text())
    fields=['position_id','open_epoch','close_epoch','side','volume','open_price','close_price','sl','tp','net','gross','commission','swap','fee']
    assert [{k:t[k] for k in fields} for t in q['trades']]==[{k:t[k] for k in fields} for t in old['trades']], 'Default-OFF parity failed'
    assert q['native']==old['native']
    save('PARITY.json',dict(passed=True,whole_positions=len(q['trades']),same_entry_exit_prices_times_lots_costs=True,reference=old['report_sha256'],new=q['report_sha256']))

if __name__=='__main__':
    # The same lease is shared with the original study; only one owned tester.
    lock=n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock'
    with lock.open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        command=sys.argv[1]
        if command=='compile':n.compile_ea()
        elif command=='parity':parity()
        elif command=='search':search();plateau();choose();confirm()
        elif command=='smoke':run_params(DEFAULTS,('2026.09.01','2026.09.08'),4,'SMOKE')
        else:raise ValueError(command)
