"""Assemble fully independent frozen engines and run native diagnostics."""
import json
from datetime import datetime,timezone
from params import *
import native

def trades(r):return json.loads((ROOT/'Audit'/f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}-trades.json").read_text())
def inheritance_parity():
    native.parity()
    shared=json.loads((OPT/'frozen-selection.json').read_text())['config'];r=native.run(shared,WINDOWS['6m'],'shared-parity')
    old=json.loads((OPT/'main-results.json').read_text())['6m'];original=json.loads((OPT/'Audit'/f"{old['period']}-engine0-d1-trades.json").read_text())
    assert original==trades(r),'Inherited shared settings changed native trades'
    save(ROOT/'inheritance-parity.json',dict(raw_ledger_exact=True,raw_trades=185,shared_ledger_exact=True,shared_trades=len(original),source_hashes=native.hashes()))
    print('BOTH INHERITANCE PARITIES PASS',flush=True)

def assemble():
    selection=json.loads((ROOT/'individual-selection.json').read_text());c=normalize({})
    for e,name in [(1,'Momentum'),(2,'Change'),(3,'Breakout')]:
        chosen=selection['engines'][str(e)]['config']
        for k in ENGINE[e]:c[k]=chosen[k]
        for suffix in ('ATRPeriod','Direction','Management','TriggerR','TrailATR'):c['Inp'+name+suffix]=chosen['Inp'+suffix]
        c['Inp'+name+'StopATR']=chosen['InpStopATR'];c['Inp'+name+'RR']=chosen['InpRewardRisk']
    lock=dict(config=c,config_id=ident(c),frozen_at_utc=datetime.now(timezone.utc).isoformat(),source_hashes=native.hashes(),
        input_selection_time=selection['frozen_at_utc'],all_three_qualified=all(v['eligible'] for v in selection['engines'].values()),latest_year_used_for_selection=False)
    path=ROOT/'assembled-selection.json'
    if path.exists():
        old=json.loads(path.read_text());assert old['config']==c and old['source_hashes']==native.hashes();lock=old
    else:save(path,lock)
    for label,engine in [('ALL THREE INDEPENDENT',0),('MOMENTUM ONLY',1),('TREND CHANGE ONLY',2),('BREAKOUT ONLY',3)]:
        cfg={**c,'InpEngine':engine};setfile=ROOT/'Sets'/f'3 way gold - {label} - RESEARCH 0.30pct.set'
        setfile.write_text(''.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}\n' for k,v in cfg.items()),encoding='utf-8')
    return lock

def main():
    native.prepare();inheritance_parity();lock=assemble();c=lock['config'];out={}
    for name,window in [('train',TRAIN),('validation',VALID)]:native.run(c,window,'combined-'+name)
    for p in ('1y','6m','3y','5y','2019-2026'):
        out[p]=native.run(c,WINDOWS[p],'combined-'+p);save(ROOT/'main-results.json',out)
    standalone=[]
    for e in (1,2,3):standalone.append(native.run({**c,'InpEngine':e},WINDOWS['5y'],'standalone'+str(e)))
    delays=[]
    for delay in (100,500):delays.append(native.run(c,LOCKED,'delay',delay=delay))
    save(ROOT/'diagnostics.json',dict(standalone=standalone,delay=delays))
    print('INDEPENDENT ENGINE COMPARISON COMPLETE',flush=True)

if __name__=='__main__':main()
