"""Audit extension: eliminate inactive-management duplicates before final assembly."""
import json,hashlib
from datetime import datetime,timezone
from params import *
from independent_selection import DEST,score,qualifies
import native

def signature(c):
    active=c['InpManagement'] if c['InpTriggerR']<c['InpRewardRisk'] else 0
    return tuple(c[k] for k in ENGINE[2]+['InpDirection','InpATRPeriod','InpStopATR','InpRewardRisk'])+(active, c['InpTriggerR'] if active else 0,c['InpTrailATR'] if active in (2,3) else 0)
def main():
    source=DEST/'individual-selection.json';selection=json.loads(source.read_text());old=DEST/'individual-selection-before-dedup-audit.json'
    if not old.exists():save(old,selection)
    candidates=json.loads((DEST/'Selection'/'engine2-shortlist.json').read_text());rows=json.loads((DEST/'Selection'/'engine2-native.json').read_text())
    seen={signature(r['config']) for r in rows};extra=[]
    for candidate in candidates:
        c=candidate['config'];key=signature(c)
        if key in seen:continue
        seen.add(key);extra.append(c)
        if len(extra)==2:break
    native.prepare()
    for i,c in enumerate(extra):
        t=native.run(c,TRAIN,f'ind2unique{i+1}-train');v=native.run(c,VALID,f'ind2unique{i+1}-valid')
        rows.append(dict(config=c,train=t,validation=v,eligible=qualifies(t,v),rank=min(score(t),score(v,True))))
    chosen=max(rows,key=lambda r:(r['eligible'],r['rank']));selection['engines']['2']=chosen
    selection['frozen_at_utc']=datetime.now(timezone.utc).isoformat();selection['dedup_audit']='Two additional effective parameter sets tested before any combined latest-year result; initial three reversal candidates had identical ledgers because TP0.5R precedes management trigger1.5R.'
    selection['additional_native_tests']=2*len(extra);save(source,selection);save(DEST/'Selection'/'engine2-dedup-native.json',rows)
    print('DEDUP AUDIT FINISHED; INDEPENDENT SELECTION FINAL',ident(chosen['config']),flush=True)

if __name__=='__main__':main()
