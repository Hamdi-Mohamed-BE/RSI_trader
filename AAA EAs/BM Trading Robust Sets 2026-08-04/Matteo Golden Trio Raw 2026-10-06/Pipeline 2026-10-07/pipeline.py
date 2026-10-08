"""Stages 1–6 only. One candidate/bot frozen before the last-two-year retrospective OOS."""
import itertools,json,math,sys
from pathlib import Path
import runner as r
from search_plan import RAW,STAGES,variants,freeze
R=r.R;CFG=r.CONFIG;DEV=CFG['development'];VAL=CFG['validation'];OOS=CFG['oos']
def init():
    plan=freeze();p=R/'SEARCH PLAN.json'
    if p.exists() and r.load(p)!=plan:
        assert not list((R/'native').glob('*-dev-*/results.json')),'Cannot revise plan after development search'
        old=r.load(p);assert old.get('schema')==1 and plan.get('schema')==2
        r.save(R/'SEARCH PLAN v1 - superseded before development search.json',old);r.save(p,plan)
    elif p.exists():assert r.load(p)==plan,'Search plan changed after freezing'
    else:r.save(p,plan)
def parity():
    keys=['open_time','close_time','side','volume','open_price','close_price','net_profit','commission','swap']
    def key(t):
        from pandas import Timestamp
        t=t|dict(side={'Long':'buy','Short':'sell'}.get(t['side'],t['side']),open_time=Timestamp(t['open_time']).isoformat(),close_time=Timestamp(t['close_time']).isoformat())
        return tuple(round(float(t[k]),6) if isinstance(t[k],(int,float)) else str(t[k]) for k in keys)
    records={}
    for bot in RAW:
        start,end=CFG['raw_windows']['3Y'];new=r.batch('parity-final-v2-'+bot,[RAW[bot]],start,end,model=4,optimize=False,verbose=True)[0]
        old=r.load(R/'native'/('raw-'+bot+'-3Y')/'result.json')
        a=[key(t) for t in old['trades']];b=[key(t) for t in new['trades']]
        exact=a==b;r.save(R/('PARITY '+bot+'.json'),dict(exact=exact,original_trades=len(a),parameterized_trades=len(b),differences=[x for x in itertools.zip_longest(a,b) if x[0]!=x[1]][:12]))
        assert exact,'Switches-off raw trade parity failed; optimisation prohibited'
        records[bot]=r.slim(new)
    r.save(R/'PARITY.json',records)
    r.status('Raw defaults reproduced trade for trade; optimisation permitted')
def controls():
    records={}
    for bot,codes in [('vault',[1,2,5]),('overnight',[3,4,6])]:
        for code in codes:
            for phase in (['3Y','5Y'] if code in [5,6] else ['DEV']):
                start,end=CFG['raw_windows'][phase] if phase!='DEV' else DEV
                rec=r.batch(f'control-{bot}-{code}-{phase}',[RAW[bot]],start,end,model=4 if phase!='DEV' else 1,optimize=False,control=code)[0];records[f'{bot}-{code}-{phase}']=r.slim(rec)
    gates={}
    for bot,code in [('vault',5),('overnight',6)]:
        for phase in ['3Y','5Y']:
            original=r.load(R/'native'/('raw-'+bot+'-'+phase)/'result.json');m=original['net_metrics'];c=records[f'{bot}-{code}-{phase}']['metrics']
            import pandas as pd
            dec=pd.read_csv(R/'native'/('raw-'+bot+'-'+phase)/'decisions.csv',encoding='utf-16');sent=dec[dec.reason=='entry_sent'].sort_values('epoch')
            ts=sorted(original['trades'],key=lambda t:t['open_time']);assert len(ts)==len(sent)
            raw_r=sum(t['net_profit']/(x.lots*x.unit_loss) for t,x in zip(ts,sent.itertuples()))/len(ts)
            control_rec=r.load(R/'native'/f'control-{bot}-{code}-{phase}'/'results.json')[0]
            control_r=sum(t['net_profit']/(t['volume']*t['planned_price_risk']) for t in control_rec['trades'])/len(control_rec['trades'])
            checks={'positive':m['net']>0,'pf_1_15':(m['pf'] or 0)>=1.15,'at_least_30':m['trades']>=30,'pf_better_than_ablation':(m['pf'] or 0)>(c['pf'] or 0),'mean_net_R_better_than_ablation':raw_r>control_r}
            gates[bot+' '+phase]=dict(checks=checks,passed=all(checks.values()),raw=m,control=c,raw_mean_net_R=raw_r,control_mean_net_R=control_r,continued_exploratory_by_user=True)
    r.save(R/'RAW GATES.json',dict(gates=gates,controls=records))
def search(bot):
    beam=[RAW[bot]];allrows=[];stages={}
    for stage in STAGES:
        cases=r.dedupe(beam+[RAW[bot]]+[c|v for c in beam for v in variants(stage,bot)])
        rows=r.batch(bot+'-dev-'+stage,cases,*DEV);allrows+=rows
        ranked=sorted(rows,key=r.score,reverse=True);beam=[x['parameters'] for x in ranked[:3]]
        stages[stage]=[r.slim(x) for x in ranked[:3]];r.save(R/(bot+' SEARCH.json'),dict(stages=stages,completed=stage,all_recorded_passes=len(allrows)))
        r.status('Development stage selected: '+bot+' '+stage,best_pf=ranked[0]['metrics']['pf'],trades=ranked[0]['metrics']['trades'])
    neighbours=[];groups=[]
    for center in beam:
        n=r.dedupe([center|dict(sl=center['sl']*s,rr=center['rr']*q,noise=center['noise']*a) for s,q,a in itertools.product([.8,1,1.2],[.8,1,1.2],[.8,1,1.2] if bot=='vault' else [1])])
        groups.append(dict(center=center,hashes=[r.digest(x) for x in n]));neighbours+=n
    rows=r.batch(bot+'-dev-plateau',r.dedupe(neighbours),*DEV);allrows+=rows;lookup={r.digest(x['parameters']):x for x in rows}
    plateaus=[]
    for group in groups:
        ns=[lookup[k] for k in group['hashes']];valid=[x for x in ns if x['clean'] and x['metrics']['trades']>=30]
        positive=sum(x['metrics']['net']>0 for x in valid)/len(ns);scores=sorted(r.score(x) for x in ns)
        p=dict(center=group['center'],positive_neighbour_share=positive,neighbours=len(ns),median_score=scores[len(scores)//2],median_pf=sorted((x['metrics']['pf'] or 0) for x in ns)[len(ns)//2])
        plateaus.append(p)
    plateaus.sort(key=lambda p:(p['positive_neighbour_share']>=.6,p['median_score']),reverse=True)
    finals=r.dedupe([p['center'] for p in plateaus])[:3]
    val=[]
    for i,c in enumerate(finals):val.append(r.batch(f'{bot}-validation-{i}',[c],*VAL,model=4,optimize=False,verbose=True)[0])
    valid_lookup={r.digest(p['center']):p for p in plateaus}
    val.sort(key=lambda x:(valid_lookup[r.digest(x['parameters'])]['positive_neighbour_share']>=.6,r.score(x,15)),reverse=True)
    chosen=val[0];unique=len({r.digest(x['parameters']) for x in allrows})
    frozen=dict(bot=bot,parameters=chosen['parameters'],selected_validation=r.slim(chosen),plateaus=plateaus,
        tested_unique_configurations=unique+3,development_passes=len(allrows),selection_is_pre_oos=True,
        classification='research-only, exploratory',oos_label=CFG['oos_label'])
    path=R/(bot+' FROZEN.json')
    if path.exists():assert r.load(path)==frozen,'Candidate changed after freezing'
    else:r.save(path,frozen)
    r.save(R/(bot+' DEVELOPMENT TABLE.json'),[r.slim(x) for x in allrows]);r.save(R/(bot+' VALIDATION.json'),[r.slim(x) for x in val])
    r.status('Candidate frozen from older data: '+bot,unique_configurations=unique,validation_pf=chosen['metrics']['pf'])
    return frozen
def evaluate(bot):
    frozen=r.load(R/(bot+' FROZEN.json'));c=frozen['parameters'];records={}
    # This is evaluation only. No alternative candidate can be selected after this call.
    records['OOS']=r.batch(bot+'-candidate-OOS',[c],*OOS,model=4,optimize=False,verbose=True)[0]
    records['Raw OOS']=r.batch(bot+'-raw-OOS',[RAW[bot]],*OOS,model=4,optimize=False,verbose=True)[0]
    for phase,dates in CFG['raw_windows'].items():records[phase]=r.batch(bot+'-candidate-'+phase,[c],*dates,model=4,optimize=False,verbose=True)[0]
    records['3M']=r.batch(bot+'-candidate-3M',[c],'2026-07-07',CFG['end_exclusive'],model=4,optimize=False,verbose=True)[0]
    records['Raw 3M']=r.batch(bot+'-raw-3M',[RAW[bot]],'2026-07-07',CFG['end_exclusive'],model=4,optimize=False,verbose=True)[0]
    r.save(R/(bot+' EVALUATION.json'),records)
    diagnostics={}
    diagnostics['USTEC 0.5% risk']=r.batch(bot+'-risk-half',[c],*OOS,model=4,optimize=False,verbose=True,risk=.5)[0]
    for symbol in ['US500','US30']:
        diagnostics[symbol]=r.batch(bot+'-transfer-'+symbol,[c],*OOS,model=4,optimize=False,verbose=True,symbol=symbol)[0]
    r.save(R/(bot+' DIAGNOSTICS.json'),diagnostics)
    # The candidate case table is fixed in this tester-only binary; risk remains an input.
    import shutil
    final=R/'Frozen Research EAs'/bot;final.mkdir(parents=True,exist_ok=True)
    source=R/'native'/(bot+'-candidate-5Y')
    for filename in ['GoldenSearch.mq5','GoldenSearch.ex5','Logic.mqh','Parameters.set']:
        shutil.copy2(source/filename,final/filename)
    r.save(final/'FROZEN.json',frozen|dict(tester_only=True,files={p.name:r.sha(p) for p in final.iterdir() if p.is_file() and p.name!='FROZEN.json'}))
def main():
    init()
    with r.lease():
        mode=sys.argv[1] if len(sys.argv)>1 else 'all'
        if mode in ['parity','all']:parity()
        if mode in ['controls','all']:controls()
        if mode in ['search','all']:
            for bot in ([sys.argv[2]] if len(sys.argv)>2 else RAW):search(bot)
        if mode in ['evaluate','all']:
            for bot in ([sys.argv[2]] if len(sys.argv)>2 else RAW):evaluate(bot)
    if mode=='all':
        import finish
        finish.main()
        import verify
        verify.main()
if __name__=='__main__':main()
