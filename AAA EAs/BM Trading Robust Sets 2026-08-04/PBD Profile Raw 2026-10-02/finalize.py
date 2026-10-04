"""Normalize legacy no-loss PF sentinels without altering native trade evidence."""
from native import ROOT,OUT,save,load,ledger
rows=load(ROOT/'SUMMARY.json')
for r in rows:
 d=ledger(r);no_losses=len(d)>0 and not (d.net_profit<0).any()
 r['stats']['pf_no_losses']=bool(no_losses)
 if no_losses:r['stats']['pf']=None
 # OnTester and shared historical metrics use 99 as a legacy no-loss sentinel.
 # Preserve native metric object unchanged, but do not report that as a finite PF.
 save(OUT/r['stage']/'results.json',[r])
save(ROOT/'SUMMARY.json',rows)
print('Finalized',len(rows),'raw native runs; no-loss PF explicitly undefined')
