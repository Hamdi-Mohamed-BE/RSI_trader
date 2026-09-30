"""Resumable isolated-native search of all 8 assets x 4 setup versions."""
from __future__ import annotations
import argparse
import itertools
import json
import os
import statistics
import time
from pathlib import Path
import native_engine as e

ROOT=e.ROOT
SYMBOLS=['USTEC','XAUUSD','XAGUSD','BTCUSD','ETHUSD','EURUSD','USDJPY','GBPJPY']
VARIANTS={1:'POC',2:'REV',4:'BRK',7:'ALL'}
STAGES=['timeframe','entry','stop','trailing','rr_exit','session','direction','filters','management','profile']
FIXED={'USTEC':[50,100,200],'XAUUSD':[5,10,20],'XAGUSD':[.1,.25,.5],
       'BTCUSD':[250,500,1000],'ETHUSD':[10,25,50],'EURUSD':[.001,.002,.004],
       'USDJPY':[.1,.2,.4],'GBPJPY':[.2,.4,.8]}

def notify(**info):
    e.dump(ROOT/'overall-progress.json',dict(utc=e.h.now(),**info))
    print(info,flush=True)

def rank(row):
    return float(row['native'].get('Custom',row['native'].get('Result',-9999)))

def changes(stage,symbol,mask):
    if stage=='timeframe': return [{'tf':x} for x in [1,3,5,15,30,16385,16388]]
    if stage=='stop':
        return ([{'stop':0}]+[{'stop':1,'stop_param':v} for v in [.5,.75,1,1.5,2,3,4]]+
                [{'stop':2,'stop_param':v} for v in [.05,.1,.2]]+
                [{'stop':3,'stop_param':v} for v in FIXED[symbol]]+[{'stop':4},{'stop':5}])
    if stage=='rr_exit': return e.patches(stage,symbol)+[{'exit':0,'rr':8}]
    if stage=='profile':
        space={'bins':[32,64,96],'value':[60,70,80],'atr':[7,14,28]}
        if mask&1: space['poc_buffer']=[.1,.2,.5,1]
        if mask&6: space['buffer']=[0,.1,.25,.5]
        if mask&4: space.update(breakout=[.5,1,1.5,2],near=[.25,.5,1],depth=[0,.25,.5])
        return [{k:v} for k,values in space.items() for v in values]
    return e.patches(stage,symbol)

def neighborhood(p):
    exit_key='trail_distance' if p['exit']==1 else 'value' if p['exit']==2 else 'rr'
    stop_key='stop_param' if p['stop'] in (1,2,3) else 'poc_buffer' if p['setups']==1 else 'buffer'
    third='breakout' if p['setups']&4 else 'value' if exit_key!='value' else 'atr'
    a=[max(.25,p[exit_key]*v) for v in [.8,1,1.2]]
    b=[max(0,p[stop_key]+d) for d in [-.05,0,.05]] if p[stop_key]==0 else [p[stop_key]*v for v in [.8,1,1.2]]
    c=[max(1,round(p[third]*v)) if third in ('atr','value') else p[third]*v for v in [.8,1,1.2]]
    return e.dedupe([p|{exit_key:x,stop_key:y,third:z} for x,y,z in itertools.product(a,b,c)])

def parity(symbol):
    cases=[e.BASE|{'setups':mask} for mask in VARIANTS]
    got=e.batch(symbol,'raw-parity',cases,start='2025.09.26',end='2026.09.26',model=4,min_trades=30)
    checks=[]
    for r in got:
        mask=r['parameters']['setups']; variant=VARIANTS[mask]
        old=json.loads((e.q.RAW/'native'/f'3wvp-{symbol}-{variant}-1y'/'run.json').read_text())
        m=old['metrics']; n=r['native']
        check=dict(symbol=symbol,variant=variant,net_equal=abs(m['net_profit']-n['Profit'])<.02,
                   trades_equal=int(m['trades'])==int(n['Trades']),pf_equal=abs(m['profit_factor']-n['Profit Factor'])<.011)
        checks.append(check)
    e.dump(ROOT/f'parity-{symbol}.json',checks)
    if not all(c['net_equal'] and c['trades_equal'] and c['pf_equal'] for c in checks):
        raise RuntimeError('Raw parity failed '+str(checks))

def run_symbol(symbol):
    parity(symbol)
    leaders={mask:[e.BASE|{'setups':mask}] for mask in VARIANTS}
    ledger=[]
    for stage in STAGES:
        notify(state='development',symbol=symbol,stage=stage,completed_assets=completed_assets())
        cases=e.dedupe([p for mask,prior in leaders.items() for p in prior]+[
            p|change for mask,prior in leaders.items() for p in prior for change in changes(stage,symbol,mask)])
        results=e.batch(symbol,stage,cases)
        ledger.extend(dict(stage=stage,**r) for r in results)
        for mask in VARIANTS:
            selected=sorted([r for r in results if r['parameters']['setups']==mask],key=rank,reverse=True)[:2]
            leaders[mask]=[r['parameters'] for r in selected]
        e.dump(ROOT/f'development-{symbol}.json',ledger)
        e.dump(ROOT/f'leaders-{symbol}.json',dict(stage=stage,leaders=leaders))
    cases=e.dedupe([n for group in leaders.values() for p in group for n in neighborhood(p)])
    results=e.batch(symbol,'stability',cases)
    ledger.extend(dict(stage='stability',**r) for r in results)
    e.dump(ROOT/f'development-{symbol}.json',ledger)
    finalists=[]
    for mask,group in leaders.items():
        for p in group:
            ids={e.digest(c) for c in neighborhood(p)}
            rows=[r for r in results if e.digest(r['parameters']) in ids]
            finalists.append(dict(parameters=p,neighborhood_count=len(rows),
                median_neighbor_score=statistics.median(rank(r) for r in rows),
                profitable_neighbor_fraction=sum(rank(r)>0 for r in rows)/len(rows)))
    # Freeze all finalists before validation. Stability is descriptive, not an early stop.
    e.dump(ROOT/f'finalists-{symbol}.json',finalists)
    val=e.batch(symbol,'validation',[f['parameters'] for f in finalists],
                start='2024.09.26',end='2025.09.26',model=4,min_trades=30)
    selection=[]
    for mask in VARIANTS:
        candidates=[r for r in val if r['parameters']['setups']==mask]
        best=max(candidates,key=rank)
        matched=next(f for f in finalists if f['parameters']==best['parameters'])
        selection.append(dict(variant=VARIANTS[mask],validation=best,stability=matched))
    e.dump(ROOT/f'selection-{symbol}.json',selection)
    confirmed=[]
    for selected in selection:
        tag=selected['variant']; p=selected['validation']['parameters']
        notify(state='native confirmation',symbol=symbol,variant=tag,completed_assets=completed_assets())
        valid=e.batch(symbol,tag+'-validation-confirm',[p],start='2024.09.26',end='2025.09.26',model=4,optimize=False,min_trades=30)[0]
        last=e.batch(symbol,tag+'-last-year',[p],start='2025.09.26',end='2026.09.26',model=4,optimize=False,min_trades=30)[0]
        # Same chosen settings, not a second search on the final comparison year.
        if abs(valid['metrics']['net_profit']-selected['validation']['native']['Profit'])>.02:
            raise RuntimeError('Validation optimization vs single-run net P/L mismatch')
        pm=valid['position_metrics']
        qualified=pm['net_profit']>0 and pm['profit_factor']>=1.15 and pm['trades']>=30 and pm['equity_dd_pct']<=20
        confirmed.append(dict(symbol=symbol,variant=tag,validation_qualified=qualified,
                              validation=valid,last_year=last,selection=selected,
                              passes=sum(r['parameters']['setups']==p['setups'] for r in ledger),
                              unique=len({e.digest(r['parameters']) for r in ledger if r['parameters']['setups']==p['setups']})))
        e.dump(ROOT/f'confirmed-{symbol}.json',confirmed)
        try:
            import make_report
            make_report.build()
        except ImportError: pass
    notify(state='asset complete',symbol=symbol,completed_assets=completed_assets())

def completed_assets():
    return [s for s in SYMBOLS if (ROOT/f'confirmed-{s}.json').exists() and len(json.loads((ROOT/f'confirmed-{s}.json').read_text()))==4]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--symbols',nargs='*',default=SYMBOLS); a=ap.parse_args()
    if any(s not in SYMBOLS for s in a.symbols): raise ValueError('Unknown asset')
    lock=e.q.ROOT/'.qualification.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,str(os.getpid()).encode()); os.close(fd)
    try:
        for symbol in a.symbols: run_symbol(symbol)
        notify(state='complete',completed_assets=completed_assets())
    except BaseException as exc:
        notify(state='failed',error=str(exc),completed_assets=completed_assets()); raise
    finally: lock.unlink(missing_ok=True)

if __name__=='__main__': main()
