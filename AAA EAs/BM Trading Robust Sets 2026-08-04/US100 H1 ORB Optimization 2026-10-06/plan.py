"""Staged research search. All plans frozen before execution, recent data excluded."""
import json,sys,msvcrt
import native as n
R=n.R
def gate(q,minimum):
 m=q['metrics'];return (not q['operational_failure'] and m['trades']>=minimum and (m['pf'] or 0)>=1.2 and (m['win_rate'] or 0)>=50 and m['net_profit']>0 and q['native']['equity_dd_pct']<=12 and m['win_streak']>m['loss_streak'])
def rank(q):
 m=q['metrics'];return (gate(q,120),m.get('sharpe_daily_equity') or -999,m.get('pf') or 0,m['return_pct'],-q['native']['equity_dd_pct'])
def distinct(qs,count):
 seen=set();out=[]
 for q in sorted(qs,key=rank,reverse=True):
  vals={k:v for k,v in q['inputs'].items() if k!='InpAuditTag'};key=json.dumps(vals,sort_keys=True)
  if key in seen or q['operational_failure']:continue
  seen.add(key);out.append(q)
  if len(out)==count:break
 return out
def execute(file,cases):
 p=R/file
 if p.exists():assert n.read(p)==cases
 else:n.save(p,cases)
 return [n.run(c['tag'],'train',c['overrides'],model=1) for c in cases]
def overrides(q):
 base=n.inputs({},'');return {k:v for k,v in q['inputs'].items() if k!='InpAuditTag' and base.get(k)!=v}
def search():
 cases=[dict(tag='target-'+str(r).replace('.','p'),overrides={'InpRewardRisk':r}) for r in [.5,.6,.75,1,1.25,1.5,2,3,4,6]]
 cases.append(dict(tag='target-off',overrides={'InpUseFixedTarget':False}))
 qs=execute('targets-plan.json',cases);tops=distinct(qs,3)
 cases=[dict(tag=f'flat-{j}-{hour}',overrides={**overrides(q),'InpFlatHour':hour}) for j,q in enumerate(tops) for hour in [16,18,20,22]]
 qs+=execute('exits-plan.json',cases);tops=distinct(qs,2)
 cases=[]
 variants=[{'InpBreakEvenAtR':.5},{'InpBreakEvenAtR':1},{'InpTrailStartAtR':1},{'InpUseEMATrend':True},{'InpRequireVWAP':True},{'InpMinBreakoutRelativeVolume':1.1}]
 for j,q in enumerate(tops):
  for v,extra in enumerate(variants):cases.append(dict(tag=f'confirm-{j}-{v}',overrides={**overrides(q),**extra}))
 qs+=execute('confirmation-plan.json',cases)
 finals=[dict(training_tag=q['tag'],overrides=overrides(q),training_qualified=gate(q,120)) for q in distinct(qs,3)]
 p=R/'finalists-frozen.json'
 if p.exists():assert n.read(p)==finals
 else:n.save(p,finals)
 n.save(R/'SEARCH RESULTS.json',[dict(tag=q['tag'],metrics=q['metrics'],native=q['native'],inputs=q['inputs'],qualified_training=gate(q,120),operational_failure=q['operational_failure']) for q in qs])
 vals=[n.run('final-valid-'+str(j),'valid',c['overrides']) for j,c in enumerate(finals)]
 ranked=sorted(enumerate(vals),key=lambda t:(finals[t[0]]['training_qualified'] and gate(t[1],25),rank(t[1])[1:]),reverse=True)
 j,q=ranked[0];sel=dict(selected=finals[j],validation_tag=q['tag'],training_qualified=finals[j]['training_qualified'],validation_qualified=gate(q,25),qualified_older=finals[j]['training_qualified'] and gate(q,25),note='Frozen before any recent candidate test; retrospective overlapping history, not untouched.')
 p=R/'selection-frozen.json'
 if p.exists():assert n.read(p)==sel
 else:n.save(p,sel)
 print('FROZEN CANDIDATE',json.dumps(sel),flush=True)
 for w in ['train','1y','6m','3m','3y','5y']:n.run('candidate-'+w,w,sel['selected']['overrides'])
if __name__=='__main__':
 with (n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);search()
