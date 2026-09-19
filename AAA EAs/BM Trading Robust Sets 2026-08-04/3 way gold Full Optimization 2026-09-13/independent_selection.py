"""Choose each engine independently with native chronological validation."""
import json,math
from datetime import datetime,timezone
from params import *
from data import load
from screen import measure
import native

DEST=ROOT.parent/'3 way gold Independent Engines 2026-09-13'
def score(r,valid=False,proxy=False):
    n=r['trades'];minimum=15 if valid else 50
    if n<minimum:return -10000+n
    dd=r['dd_pct'] if proxy else r['max_equity_dd_pct'];ret=r['return_pct'];pf=max(.01,min(4,r['net_pf'] or .01))
    return 30*math.log(pf)+2*ret/max(1,dd)+.12*ret-.55*dd-.15*max(0,(25 if valid else 80)-n)
def qualifies(t,v):return t['trades']>=50 and v['trades']>=15 and all(r['net_profit']>0 and (r['net_pf'] or 0)>1.05 and r['max_equity_dd_pct']<=15 and not r['native_stopout'] for r in (t,v))

def shortlist(d,e):
    path=DEST/'Selection'/f'engine{e}-shortlist.json'
    if path.exists():return json.loads(path.read_text())
    rows=json.loads((ROOT/'Search'/f'engine{e}.json').read_text());pool=[];seen=set()
    for r in sorted(rows,key=lambda r:r['score'],reverse=True):
        c=r['config'];key=tuple(c[k] for k in ENGINE[e]+['InpATRPeriod','InpDirection','InpManagement'])
        if key in seen:continue
        seen.add(key);pool.append(r)
        if len(pool)==24:break
    results=[]
    for t in pool:
        v=measure(d,t['config'],VALID);results.append(dict(config=t['config'],train=t,validation=v,rank=min(score(t,proxy=True),score(v,True,True))))
    results.sort(key=lambda r:r['rank'],reverse=True);save(path,results);return results

def main():
    d=load();native.prepare();all_results={};selected={}
    for e in (1,2,3):
        candidates=shortlist(d,e)[:3];rows=[]
        for i,f in enumerate(candidates):
            c=f['config'];t=native.run(c,TRAIN,f'ind{e}c{i+1}-train');v=native.run(c,VALID,f'ind{e}c{i+1}-valid')
            rows.append(dict(config=c,train=t,validation=v,eligible=qualifies(t,v),rank=min(score(t),score(v,True))))
            save(DEST/'Selection'/f'engine{e}-native.json',rows)
        chosen=max(rows,key=lambda r:(r['eligible'],r['rank']));selected[str(e)]=chosen;all_results[str(e)]=rows
        print('INDEPENDENT ENGINE FROZEN',e,ident(chosen['config']),'eligible',chosen['eligible'],flush=True)
    lock=dict(engines=selected,frozen_at_utc=datetime.now(timezone.utc).isoformat(),source_hashes=native.hashes(),
        latest_year_used_for_parameter_selection=False,prior_aggregate_history_already_seen=True,selection_inputs='train2021-2024, validation2024-2025 only')
    path=DEST/'individual-selection.json'
    if path.exists():assert json.loads(path.read_text())['engines']==lock['engines']
    else:save(path,lock)
    save(DEST/'native-candidates.json',all_results)
    print('ALL INDIVIDUAL SETTINGS FROZEN. READY TO COMBINE.',flush=True)

if __name__=='__main__':main()
