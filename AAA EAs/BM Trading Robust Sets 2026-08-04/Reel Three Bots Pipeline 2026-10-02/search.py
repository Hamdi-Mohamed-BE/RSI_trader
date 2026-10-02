"""Frozen research pipeline. No live deployment. See PROTOCOL.txt."""
from native_runner import *

COMMONCASE=dict(module=0,tf=1,entry=0,offset=0,stop=0,sl=1,rr=0,trail=0,start=1,dist=.1,exit=0,session=0,direction=0,filter=0,day=0,max_day=1,hold=0,flat=0,season=0,p1=175,p2=2.5,p3=.25,range_start=8,range_end=11,range_flat=18,maxpos=1,reentry=0,channel_tf=60,atr_period=200,partial=0,stopbuffer=0,adx_min=20,regime_min=20,regime_max=80)
RAWCASE={'A':dict(COMMONCASE),'B':COMMONCASE|dict(module=1,tf=60,sl=.5,rr=7,max_day=0),'C':COMMONCASE|dict(module=2,sl=.5,rr=2,trail=9,max_day=0)}
DEV=('2021.10.01','2024.04.01');VAL=('2024.04.01','2025.10.01');HOLD=('2019.10.01','2021.04.01')
WEB={'6m':('2026.04.01','2026.10.02'),'1y':('2025.10.01','2026.10.02'),'3y':('2023.10.01','2026.10.02'),'5y':('2021.10.01','2026.10.02')}
SEEDS=[301,307,311,313,317]
STAGES=['timeframe','entry','stop','trailing','exit','session','direction','filters','management','logic']

def parity():
    results={}
    for m,name in zip('ABC',['range','atr','donchian']):
        batch('parity-v2-'+m,[RAWCASE[m]],'2026.09.01','2026.09.15',model=4,optimize=False,warmup=62,risk=0)
        new=read_ledger('parity-v2-'+m);old=pd.read_csv(RAW/'native'/f'{name}-smoke'/'trades.csv')
        keys=['open_epoch','close_epoch','side','open_price','close_price','volume','net_profit']
        key=lambda d:sorted(tuple(round(float(v),6) for v in row) for row in d[keys].itertuples(index=False))
        results[m]=dict(exact=key(old)==key(new),old_trades=len(old),new_trades=len(new),old_net=float(old.net_profit.sum()),new_net=float(new.net_profit.sum()))
    save(ROOT/'PARITY.json',results)
    assert all(v['exact'] for v in results.values()),results
    status('RAW PARITY PASSED',results=results)

def raw():
    summary={}
    for m in 'ABC':
        runs={}
        for label in ['3y','5y']:
            runs['screen-'+label]=batch(f'raw-{m}-{label}-m1',[RAWCASE[m]],*WEB[label],model=1,optimize=False)[0]
        for label in WEB:
            runs[label]=batch(f'raw-{m}-{label}-m4',[RAWCASE[m]],*WEB[label],model=4,optimize=False)[0]
        controls=[batch(f'raw-{m}-control-{seed}',[RAWCASE[m]],*WEB['5y'],model=4,optimize=False,control=True,seed=seed)[0] for seed in SEEDS]
        cpfs=[r['stats']['pf'] or 0 for r in controls];cmeans=[r['stats']['net']/r['stats']['trades'] for r in controls if r['stats']['trades']]
        passed=all(runs[k]['clean'] and runs[k]['stats']['trades']>=30 and runs[k]['stats']['net']>0 and (runs[k]['stats']['pf'] or 0)>=1.15 for k in ['3y','5y'])
        st=runs['5y']['stats'];better=bool(cmeans) and (st['pf'] or 0)>statistics.median(cpfs) and st['net']/max(st['trades'],1)>statistics.median(cmeans)
        summary[m]=dict(runs=runs,controls=controls,gate='PASS' if passed and better else 'FAIL',control_median_pf=statistics.median(cpfs),control_median_mean=statistics.median(cmeans) if cmeans else None,exploratory_override=True)
        save(ROOT/'RAW GATES.json',summary);status('RAW GATE '+m,gate=summary[m]['gate'])
    return summary

def patches(stage,m,b):
    stops=[dict(stop=0,sl=RAWCASE[m]['sl'])]+[dict(stop=1,sl=v) for v in [.1,.2,.5]]+[dict(stop=2,sl=v) for v in [.5,.75,1,1.5,2,3,4]]+[dict(stop=v) for v in [3,4]]
    trails=[dict(trail=0)]+[dict(trail=1,start=v) for v in [.5,1,1.5]]+[dict(trail=2,start=s,dist=d) for s in [.5,1,1.5,2] for d in [1,1.5,2,3]]+[dict(trail=3,start=1,dist=v) for v in [.1,.2,.5]]+[dict(trail=v,start=1) for v in [4,5,6,7]]
    if m=='C':trails+=[dict(trail=9)]
    rr=[dict(exit=0,rr=v) for v in [0,.5,.75,1,1.25,1.5,2,2.5,3,4,5,6,RAWCASE[m]['rr']]]
    filters=[dict(filter=0),dict(filter=1),dict(filter=2),dict(filter=4),dict(filter=6),dict(filter=7)]+[dict(filter=f,adx_min=v) for f in [3,8] for v in [15,20,25,30]]+[dict(filter=5,regime_min=a,regime_max=z) for a,z in [(0,33),(33,67),(67,100),(20,80)]]
    common={'timeframe':[dict(tf=v) for v in ([1,3,5,15,30,60] if m=='A' else [1,3,5,15,30,60,240])],
            'entry':[dict(entry=0),dict(entry=1)]+[dict(entry=e,offset=v) for e in [2,3] for v in [.1,.25,.5]],
            'stop':stops,'trailing':trails,'exit':rr+[dict(exit=1,hold=v) for v in [8,16,32]]+[dict(flat=1),dict(exit=3)],
            'session':[dict(session=v) for v in range(6)],'direction':[dict(direction=v) for v in range(3)],'filters':filters,
            'management':[dict(day=v) for v in range(4)]+[dict(max_day=v) for v in ([1,2,3] if m=='A' else [0,1,2,3])]+[dict(flat=v) for v in range(3)]+[dict(reentry=v) for v in [0,1]]}
    if m!='A':common['management']+=[dict(maxpos=v) for v in [1,2]]
    else:common['management']+=[dict(range_flat=v) for v in [0,16,18,20]]
    if stage!='logic':return common[stage]
    if m=='A':return [dict(range_start=a,range_end=z) for a,z in [(7,10),(7,11),(8,10),(8,11),(8,12),(9,11),(9,12)]]
    if m=='B':return [dict(p2=v) for v in [1.5,2,2.5,3,3.5,4]]+[dict(atr_period=v) for v in [100,200,400]]+[dict(p3=v) for v in [.1,.25,.35]]
    return [dict(p1=v) for v in [75,100,125,175,250]]+[dict(channel_tf=v) for v in [15,60,240]]

def score(r,minimum=60):
    s=r['stats'];dd=r['net']['equity_dd_pct']
    if not r['clean'] or s['trades']<minimum:return -1000
    if s['net']<=0:return -1-abs(s['net'])/10000-dd/100
    return ((s['pf'] or 0)-1)*math.sqrt(s['trades'])/(1+dd/10)

def eligible(r,minimum=60):return r['clean'] and r['stats']['trades']>=minimum and r['stats']['net']>0 and (r['stats']['pf'] or 0)>=1.15

def search(m):
    leaders=[RAWCASE[m]];summary=[]
    for stage in STAGES:
        cases=dedupe(leaders+[b|p for b in leaders for p in patches(stage,m,b)])
        rows=batch(f'{m}-{stage}',cases,*DEV)
        for r in rows:r['score']=score(r)
        ranked=sorted([r for r in rows if r['clean']],key=lambda r:r['score'],reverse=True)
        assert ranked,'No clean search cases: '+m+' '+stage
        leaders=[r['parameters'] for r in ranked[:3]]
        summary.append(dict(stage=stage,cases=len(cases),leaders=ranked[:3]));save(ROOT/f'STAGES-{m}.json',summary)
    finals=[r for r in ranked if eligible(r)][:3];save(ROOT/f'FINALISTS-{m}.json',finals)
    return finals

def neighbours(m,b):
    axes=[]
    if b['stop'] in [0,1,2]:axes+=['sl']
    if b['rr']>0:axes+=['rr']
    if b['trail'] in [2,3]:axes+=['dist']
    if b['entry'] in [2,3]:axes+=['offset']
    if b['exit']==1:axes+=['hold']
    axes+=({'A':['range_start','range_end'],'B':['p2','p3','atr_period'],'C':['p1','start','dist']}[m])
    axes=list(dict.fromkeys(axes))[:3];cases=[]
    for factors in itertools.product([-.2,0,.2],repeat=len(axes)):
        c=dict(b)
        for k,f in zip(axes,factors):
            v=b[k]*(1+f);c[k]=max(1,round(v)) if k in ['p1','atr_period','hold'] else round(v,6)
        if m=='A' and not(c['range_start']<c['range_end'] and (c['range_flat']==0 or c['range_end']<c['range_flat'])):continue
        cases.append(c)
    return dedupe(cases),axes

def validate(m,finals):
    allcases=[];groups=[]
    for r in finals:
        cases,axes=neighbours(m,r['parameters']);groups.append((r,axes,len(allcases),len(cases)));allcases+=cases
    rows=batch(f'{m}-plateau',allcases,*DEV) if allcases else [];plats=[]
    for r,axes,a,n in groups:
        group=rows[a:a+n];positive=sum(v['clean'] and v['stats']['net']>0 for v in group)/n;median=statistics.median((v['stats']['pf'] or 0) for v in group)
        plats.append(dict(parameters=r['parameters'],axes=axes,neighbours=n,positive_fraction=positive,median_pf=median,passed=len(axes)==3 and positive>=2/3 and median>1))
    save(ROOT/f'PLATEAUS-{m}.json',plats);passed=[p['parameters'] for p in plats if p['passed']]
    val=batch(f'{m}-validation',passed,*VAL,model=4) if passed else []
    clean=[r for r in val if eligible(r,30)]
    if clean:pick=max(clean,key=lambda r:score(r,30));verdict='PASSED_VALIDATION'
    elif val:pick=max(val,key=lambda r:score(r,30));verdict='REJECTED_VALIDATION'
    elif finals:pick=finals[0];verdict='REJECTED_PLATEAU'
    else:pick=None;verdict='REJECTED_DEVELOPMENT'
    result=dict(verdict=verdict,parameters=pick['parameters'] if pick else None,validation=pick if pick in val else None)
    save(ROOT/f'PICK-{m}.json',result);return result

def confirm(picks):
    result={}
    for m,p in picks.items():
        if p['parameters'] is None:result[m]=p;continue
        periods={label:batch(f'frozen-{m}-{label}',[p['parameters']],*dates,model=4,optimize=False)[0] for label,dates in WEB.items()}
        periods['development']=batch(f'frozen-{m}-development',[p['parameters']],*DEV,model=4,optimize=False)[0]
        try:periods['holdout']=batch(f'frozen-{m}-holdout',[p['parameters']],*HOLD,model=4,optimize=False)[0]
        except AssertionError as e:
            # Missing older history blocks qualification, but preserves all evidence.
            save(ROOT/f'HOLDOUT-BLOCK-{m}.json',dict(error=str(e)));periods['holdout']=None
        verdict=p['verdict']
        if verdict=='PASSED_VALIDATION':
            verdict='PASSED_NATIVE_CHECKS' if periods['holdout'] and eligible(periods['holdout'],30) and eligible(periods['1y'],30) else 'REJECTED_FROZEN_CHECKS'
        result[m]=p|dict(verdict=verdict,periods=periods)
        save(ROOT/'FROZEN PICKS.json',result)
    return result

def combos(frozen):
    members=[m for m in 'ABC' if frozen[m]['parameters'] is not None];sets={'all-exploratory':members}
    survivors=[m for m in members if frozen[m]['verdict']=='PASSED_NATIVE_CHECKS']
    if 2<=len(survivors)<len(members):sets['native-survivors']=survivors
    result={}
    for label,mods in sets.items():
        if len(mods)<2:continue
        cases=[frozen[m]['parameters'] for m in mods];periods={}
        for per,dates in list(WEB.items())+[('validation',VAL),('holdout',HOLD)]:
            try:r=batch(f'combo-{label}-{per}',cases,*dates,model=4,optimize=False,slots=list(range(len(cases))))[0]
            except AssertionError:
                if per=='holdout':continue
                raise
            periods[per]=r
        result[label]=dict(members=mods,periods=periods)
    base_periods={}
    for per in ['6m','1y','5y']:
        base_periods[per]=batch(f'combo-raw-baseline-{per}',[RAWCASE[m] for m in 'ABC'],*WEB[per],model=4,optimize=False,slots=[0,1,2])[0]
    result['raw-baseline']=dict(members=list('ABC'),periods=base_periods)
    save(ROOT/'COMBINATIONS.json',result);return result

def main():
    with (TESTER/'reel-pipeline.lock').open('a+b') as handle:
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        try:
            cmd=sys.argv[1]
            if cmd=='parity':parity();return
            assert all(v['exact'] for v in load(ROOT/'PARITY.json').values())
            if cmd=='raw':raw();return
            if cmd=='all':raw()
            picks=load(ROOT/'PICKS.json') if (ROOT/'PICKS.json').exists() else {}
            if cmd in ['all','search']:
                for m in (sys.argv[2:] if cmd=='search' and len(sys.argv)>2 else list('ABC')):
                    finals=search(m);picks[m]=validate(m,finals);save(ROOT/'PICKS.json',picks)
            if cmd in ['all','finish']:
                frozen=confirm(picks);combos(frozen)
                trials=sum(len(load(p)['cases']) for p in OUT.glob('*/manifest.json'));save(ROOT/'TRIAL ACCOUNTING.json',dict(passes=trials,scope='All frozen native attempts including repeated configurations, controls, parity and failed compilation; conservative DSR trial count'))
                status('NATIVE SEARCH COMPLETE; ROBUSTNESS PENDING',passes=trials)
        finally:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__':main()
