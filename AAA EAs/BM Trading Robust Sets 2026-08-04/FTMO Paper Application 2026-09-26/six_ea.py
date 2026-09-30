"""Six-EA shared-account study: offline, no production imports or MT5 connection."""
from __future__ import annotations
import ast
import hashlib
import html
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
import compare as c
import phase_breakdown as ph
import additions as a

ORB='orb-volume-profile-high-win-0-75r/standard'
OVERNIGHT='nasdaq-overnight/standard'
EMA='ema3/safe'
CORE=[c.RAW]+c.NEWS
SIX=CORE+[OVERNIGHT,EMA,ORB]
CONFIGS=[dict(name='Three-EA core',keys=CORE,risk=500/7,news_risk=10.),
         dict(name='Six EAs together',keys=SIX,risk=500/7,news_risk=10.)]
CACHE=c.ROOT.parent.parent/'EA store/data/evidence-cache/v1'
N=1000

def load_orb():
    source=CACHE.parents[2]/'app/mt5_evidence_jobs.py'
    ns=dict(html=html,re=re,Path=Path,Any=object,TAG_RE=re.compile(r'<[^>]+>'),
            defaultdict=defaultdict,datetime=c.datetime,timezone=c.timezone)
    for p,names in [(source,{'_read_report','_clean','_number','_native_trades','_metric','_percent_in_parentheses','_native_metrics'}),
                    (c.SOURCE/'prepare.py',{'dt','orders'})]:
        tree=ast.parse(p.read_text(encoding='utf-8-sig'))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        assert {n.name for n in nodes}==names
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
    rp=CACHE/'source-runs'/ORB/'5y.htm'
    tp=CACHE/'products'/ORB/'5y.trades.json'
    mp=rp.with_suffix('.meta.json')
    sp=c.ROOT.parent/'Selected Portfolio Settings 2026-09-01/05B ORB Volume Profile High Win 0.75R - DYNAMIC 50-20 - ALL DAY.set'
    meta=c.read(mp)
    assert a.sha(sp)==meta['settings_sha256']
    report=ns['_read_report'](rp)
    assert 'InpRewardRisk=0.75' in report
    trades=ns['_native_trades'](rp,'ORB Volume Profile High Win 0.75R')
    cached=c.read(tp)
    metrics=ns['_native_metrics'](rp)
    orders=ns['orders'](rp)
    assert len(trades)==len(cached)==metrics['trades']==304
    out=[]
    for raw,cache in zip(trades,cached):
        for f in ('open_time','close_time','side','symbol','volume','open_price','close_price'):
            assert raw[f]==cache[f],(f,raw,cache)
        assert abs(raw['net_profit']-cache['net_profit'])<.011
        op,cl=ns['dt'](raw['open_time']),ns['dt'](raw['close_time'])
        match=orders.get((op,raw['symbol'],raw['side']),[])
        assert len(match)==1,(op,match)
        stop=match[0]['stop'];sgn=1 if raw['side']=='Long' else -1
        assert sgn*(raw['open_price']-stop)>0 and cl>op
        assert abs(raw['gross_profit']+raw['commission']+raw['swap']-raw['net_profit'])<.021
        assert abs(sgn*(raw['close_price']-raw['open_price'])*100*raw['volume']-raw['gross_profit'])<.021
        out.append(dict(raw,key=ORB,news=False,symbol='XAUUSD',op=op,cl=cl,stop=stop,target=match[0]['target'],
                        unit_risk=abs(raw['open_price']-stop)*100,risk_quality='native_entry_order',
                        unit_gross=raw['gross_profit']/raw['volume'],unit_comm=raw['commission']/raw['volume'],
                        unit_swap=raw['swap']/raw['volume']))
    assert abs(sum(r['net_profit'] for r in trades)-metrics['net_profit'])<.05
    assert len({r['open_time'] for r in trades})==len(trades),'Unexpected partial exits'
    evidence=dict(full_native_trades=len(trades),full_native_net=metrics['net_profit'],
                  reconstructed_costs=True,unique_initial_stops=len(out),metadata=meta,
                  files={str(p):a.sha(p) for p in (rp,tp,mp,sp,source)},
                  limitation='Saved historical build; no current-binary identity or deployment assertion.')
    return sorted([r for r in out if r['op']<c.END],key=lambda r:r['cl']),evidence

def make_engine(sizing):
    ns=c.engine()
    if sizing=='legacy_round_up':return ns
    assert sizing=='strict_round_down'
    ns['rounded']=lambda v:max(0.,math.floor(v/.01+1e-10)*.01)
    source=(c.SOURCE/'simulate.py').read_text(encoding='utf-8-sig')
    replacements={
        'if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:':'if False:',
        'lot=rounded(news_risk/riskunit);risk=lot*riskunit':
        "lot=rounded(news_risk/riskunit)\n            if lot<.01:\n                counts['news_min_lot_over_budget']+=1;continue\n            risk=lot*riskunit\n            assert risk<=news_risk+1e-7",
        "lot=rounded(RISK/r['unit_risk']);risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])":
        "lot=rounded(RISK/r['unit_risk'])\n                if lot<.01:\n                    counts['min_lot_over_budget']+=1;continue\n                risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])\n                assert risk<=RISK+1e-7",
    }
    for old,new in replacements.items():
        assert source.count(old)==1,old
        source=source.replace(old,new)
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='replay']
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'strict_replay','exec'),ns)
    return ns

def checks(data):
    out=c.tests(data);out['phase_tests']=ph.checks(c.engine())
    ns=make_engine('strict_round_down')
    assert ns['rounded'](.0099)==0 and ns['rounded'](.01)==.01
    assert abs(ns['rounded']((500/7)/1000)-.07)<1e-9
    assert abs(c.engine()['rounded']((500/7)/1000)-.08)<1e-9
    # Exact minimum lot and no zero-lot trades: verify ordinary admission and news.
    row=dict(data['rows'][c.RAW][0],op=c.START+3600,cl=c.START+7200,unit_risk=8000.)
    r=ns['replay']([row],[],c.START,c.START+c.DAY,challenge=False,detail=True)
    assert r['trades']==0 and r['counts'].get('min_lot_over_budget')==1
    row['unit_risk']=1000.
    r=ns['replay']([row],[],c.START,c.START+c.DAY,challenge=False,detail=True)
    assert r['trades']==1 and r['log'][0]['initial_risk']==70.
    p=dict(key=c.NEWS[1],kind='CPI',epoch=c.START+3600,op=c.START+3590,
           until=c.START+4000,buy=30.,sell=29.9,sl=1.,symbol='XAGUSD')
    r=ns['replay']([], [p],c.START,c.START+c.DAY,challenge=False)
    assert r['counts'].get('news_min_lot_over_budget')==1 and not r['counts'].get('news_baskets')
    for riskunit in (1.,99.9,1000.,2000.,5000.,10000.,20000.):
        lot=ns['rounded']((500/7)/riskunit)
        assert lot*riskunit<=500/7+1e-7
    out['strict_sizing_checks']=14
    return out

def reconcile(r,strict):
    assert r['trades']==len(r['log'])==sum(v['trades'] for v in r['by_ea'].values())
    assert abs(sum(t['net_profit'] for t in r['log'])-(r['balance']-10000))<1e-7
    for t in r['log']:
        if strict:assert 0<t['initial_risk']<=(10 if t['ea'] in c.NEWS else 500/7)+1e-7

def main():
    c.verify_sources()
    data=c.read(c.SOURCE/'prepared.json')
    data['rows'][ORB],evidence=load_orb()
    validation=checks(data)
    weeks=c.pool(data,ph.POOL_START,26)
    source_entries={k:sum(map(len,weeks[k])) for k in SIX}
    lot_min={k:sorted({p['sl']*c.SPECS[p['symbol']][0]*.01 for p in data['placements'] if p['key']==k and ph.POOL_START<=p['op']<c.END}) for k in c.NEWS}
    print('AUDIT',json.dumps(dict(orb=evidence,source_entries=source_entries,minimum_news_risk=lot_min,checks=validation)),flush=True)
    if '--audit-only' in sys.argv:return
    rng=random.Random(20260926)
    samples=[[rng.randrange(26) for _ in range(26)] for _ in range(N)]
    out=dict(as_of='2026-09-27',configs=CONFIGS,paths=N,seed=20260926,
             source_start=c.iso(ph.POOL_START),source_end=c.iso(c.END),historical_start=c.iso(c.END-180*c.DAY),
             orb=evidence,source_entries=source_entries,minimum_news_risk=lot_min,checks=validation,cases=[])
    c.save(c.ROOT/'SIX_EA_FROZEN.json',{k:v for k,v in out.items() if k!='cases'})
    controls={}
    prior=c.read(c.ROOT/'PHASE_RESULTS.json')['cases']
    for sizing in ('legacy_round_up','strict_round_down'):
        ns=make_engine(sizing)
        for config in CONFIGS:
            for stress in (False,True):
                ns['RISK']=config['risk'];rr=[]
                for sample in samples:
                    rows,places=c.sample_rows(data,config['keys'],ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
                    rr.append(ns['replay'](rows,places,c.START,c.START+180*c.DAY,news_risk=10.,stress=stress))
                summary=ph.summarize(rr,ns)
                if config==CONFIGS[0]:
                    controls[sizing,stress]=rr
                    if sizing=='legacy_round_up':
                        old=next(r for r in prior if r['config']['keys']==CORE and r['stress']==stress)
                        assert summary['horizons']==old['summary']['horizons'],'Baseline parity failed'
                hs=c.END-180*c.DAY
                rows=[dict(r) for k in config['keys'] for r in data['rows'][k] if hs<=r['op']<c.END and r['cl']<c.END]
                places=[dict(p) for p in data['placements'] if p['key'] in config['keys'] and hs<=p['op']<c.END]
                hist=ns['replay'](rows,places,hs,c.END,news_risk=10.,stress=stress,challenge=False,detail=True)
                reconcile(hist,sizing=='strict_round_down')
                challenge=ns['replay'](rows,places,hs,c.END,news_risk=10.,stress=stress,detail=True)
                matched={label:a.paired(controls[sizing,stress],rr,field,180) for label,field in [('funded','funded_at'),('paid','receipt_at')]}
                case=dict(config=config,sizing=sizing,stress=stress,summary=summary,
                          aggregate180=c.summarize(rr,180),historical_continuous=hist,historical_challenge=challenge,
                          paired180=matched,paths=a.compact_paths(rr))
                out['cases'].append(case)
                c.save(c.ROOT/'SIX_EA_RESULTS.json',out)
                print(sizing,config['name'],'stress' if stress else 'reference',json.dumps(dict(
                    funded=summary['horizons'][-1]['funded_pct'],paid=summary['horizons'][-1]['payout_pct'],
                    hist_net=hist['balance']-10000,hist_trades=hist['trades'],hist_wr=hist['win_rate'],
                    hist_dd=hist['model_dd_pct'],funded_median=summary['timing']['funded_days_from_purchase']['median'])),flush=True)
    print('COMPLETE: 8000 paths and eight historical replays',flush=True)

if __name__=='__main__':main()
