"""Frozen staged search; development rankings precede recent native evidence."""
import json,math,sys,msvcrt
from pathlib import Path
import native as n
R=Path(__file__).resolve().parent
def score(q):
 m=q['metrics'];return (m['pf'] or 0)*math.sqrt(m['trades'])/(1+q['native']['equity_dd_pct']/10)
def qualify(q,minimum):
 m=q['metrics'];return m['trades']>=minimum and m['net_profit']>0 and (m['pf'] or 0)>=1.2 and m['win_rate']>=50 and m['win_streak']>m['loss_streak'] and q['native']['equity_dd_pct']<=15 and not q['operational_failure']
def cases():
 out={}
 for management in [0,1,2]:
  for rr in [.5,.6,.75,1.,1.5,2.,3.,4.]:out[f'm{management}-r{rr:g}']={'InpResearchManagement':management,'InpRewardRisk':rr}
 out['dynamic-only']={'InpUseTrailing':False}
 for rr in [1.,2.,3.]:out[f'utc-r{rr:g}']={'InpTesterServerClockMode':0,'InpResearchManagement':1,'InpRewardRisk':rr}
 out['utc-original']={'InpTesterServerClockMode':0}
 return out
def screen():
 initial=cases();n.save(R/'initial-plan.json',initial)
 qs={tag:n.run('screen-'+tag,'train',c,1) for tag,c in initial.items()}
 best=max(qs,key=lambda t:(qualify(qs[t],90),score(qs[t]),qs[t]['metrics']['win_rate']))
 anchor=initial[best];refine={}
 for name,k,values in [('buffer','InpAsiaBufferPercent',[0,.01,.06,.1]),('tf','InpResearchSignalTF',[15,30,16386]),('end','InpResearchLastHour',[10,11,12]),
  ('direction','InpResearchDirection',[-1,1]),('stop','InpResearchStop',[1]),('markov','InpUseMarkovRegimeFilter',[False]),('gate','InpMarkovSignalGate',[.10])]:
  for v in values:refine[f'{name}-{v}']={**anchor,k:v}
 # Independent management neighbours only when stable manager was actually selected.
 if anchor.get('InpResearchManagement')==2:
  for v in [1.,1.5,2.5]:refine[f'trailstart-{v}']={**anchor,'InpResearchTrailStart':v}
 n.save(R/'refinement-plan.json',dict(anchor=best,settings=anchor,cases=refine))
 for tag,c in refine.items():
  initial['refine-'+tag]=c;qs['refine-'+tag]=n.run('screen-refine-'+tag,'train',c,1)
 # At most3 distinct strategies; no redundant inactive trail controls.
 ranked=sorted(qs,key=lambda t:(qualify(qs[t],90),score(qs[t]),qs[t]['metrics']['win_rate']),reverse=True)
 finalists=ranked[:3];n.save(R/'finalists-frozen.json',dict(finalists=finalists,settings={t:initial[t] for t in finalists},development_ranking=ranked,configurations=len(initial)))
 confirmed={}
 for tag in finalists:
  c=initial[tag];train=n.run('confirm-'+tag+'-train','train',c,4);valid=n.run('confirm-'+tag+'-valid','valid',c,4)
  confirmed[tag]=dict(train=train['metrics'],validation=valid['metrics'],train_qualifies=qualify(train,90),validation_qualifies=qualify(valid,30),
   qualification=qualify(train,90) and qualify(valid,30),rank_score=score(valid))
 selected=max(finalists,key=lambda t:(confirmed[t]['qualification'],confirmed[t]['validation_qualifies'],confirmed[t]['rank_score']))
 frozen=dict(selected=selected,settings=initial[selected],qualified=confirmed[selected]['qualification'],confirmed=confirmed,configurations=len(initial),
  caveat='Bounded retrospective exploratory optimisation; validation used for selection; recent years already inspected, not untouched holdout.')
 n.save(R/'selection-frozen.json',frozen)
 n.save(R/'SEARCH RESULTS.json',dict(configurations=len(initial),initial=len(cases()),anchor=best,rows=[dict(tag=t,settings=initial[t],metrics=qs[t]['metrics'],equity_dd=qs[t]['native']['equity_dd_pct'],qualified=qualify(qs[t],90),score=score(qs[t]),operational_failure=qs[t]['operational_failure']) for t in ranked]))
 print('FROZEN FINALIST '+json.dumps(frozen),flush=True)
def final():
 selected=n.read(R/'selection-frozen.json');c=selected['settings']
 for w in ['train','valid','1y','6m','3m','3y','5y']:n.run('candidate-'+w,w,c,4)
 # Clock diagnostic compares exact current mechanics; not an inferred live-account result.
 for w in ['1y','3m']:n.run('utc-current-'+w,w,{'InpTesterServerClockMode':0},4)
if __name__=='__main__':
 with (n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='screen':screen()
  elif sys.argv[1]=='final':final()
