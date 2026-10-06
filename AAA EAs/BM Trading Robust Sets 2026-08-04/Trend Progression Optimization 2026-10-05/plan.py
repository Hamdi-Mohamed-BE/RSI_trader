"""Frozen bounded Trend Progression search; no live access or deployment."""
from pathlib import Path
import hashlib,importlib.util,json,math,msvcrt,sys
import numpy as np
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('trend_native',R/'native.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)
DEV=('2021.10.05','2024.10.05');VAL=('2024.10.05','2025.10.05');RECENT=('2025.10.05','2026.10.05')
DEFAULTS=dict(InpRewardRisk=.6,InpStopMode=1,InpSwingLookback=5,InpStopATR=2.,InpStopBufferATR=.1,
 InpUseBreakEven=True,InpBreakEvenAtR=1.,InpBreakEvenLockR=.05,InpUseATRTrailing=False,InpTrailStartR=1.,InpTrailATR=2.,
 InpUseDynamicM15Stop=False,InpDynamicTriggerR=.5,InpDynamicLockR=.2,InpResearchADXMin=0.,InpResearchDI=False)
STAGES=[
 ('target',[dict(InpRewardRisk=x) for x in [.5,.6,.75,1,1.25,1.5,2,3]]),
 ('stop',[dict(InpStopMode=1,InpSwingLookback=x) for x in [3,5,8]]+[dict(InpStopMode=0)]+
  [dict(InpStopMode=2,InpStopATR=x) for x in [1,1.5,2,3]]),
 ('management',[dict(InpUseBreakEven=True,InpBreakEvenAtR=1.,InpUseATRTrailing=False,InpUseDynamicM15Stop=False),
  dict(InpUseBreakEven=False,InpUseATRTrailing=False,InpUseDynamicM15Stop=False),
  dict(InpUseBreakEven=True,InpBreakEvenAtR=.25,InpUseATRTrailing=False,InpUseDynamicM15Stop=False),
  dict(InpUseBreakEven=True,InpBreakEvenAtR=.5,InpUseATRTrailing=False,InpUseDynamicM15Stop=False),
  dict(InpUseBreakEven=False,InpUseATRTrailing=True,InpTrailStartR=.5,InpTrailATR=1.5,InpUseDynamicM15Stop=False),
  dict(InpUseBreakEven=False,InpUseATRTrailing=False,InpUseDynamicM15Stop=True,InpDynamicTriggerR=.3,InpDynamicLockR=.1)]),
 ('ADX_DI',[dict(InpResearchADXMin=a,InpResearchDI=d) for a,d in [(0,False),(20,False),(25,False),(0,True),(20,True),(25,True)]])]
def save(name,v):n.save(R/name,v)
def sha_obj(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()[:14]
def canonical(p):
 p=dict(p)
 if p['InpStopMode']!=2:p['InpStopATR']=2.
 if p['InpStopMode']!=1:p['InpSwingLookback']=5
 if not p['InpUseBreakEven']:p['InpBreakEvenAtR']=1.;p['InpBreakEvenLockR']=.05
 if not p['InpUseATRTrailing']:p['InpTrailStartR']=1.;p['InpTrailATR']=2.
 if not p['InpUseDynamicM15Stop']:p['InpDynamicTriggerR']=.5;p['InpDynamicLockR']=.2
 return {k:int(v) if k in ['InpStopMode','InpSwingLookback'] else float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else v for k,v in p.items()}
def run_params(p,window,model=0,prefix='D'):
 p=canonical(p);tag=prefix+'-'+sha_obj(dict(p=p,window=window,model=model))
 n.CASES[tag]=dict(label=tag,mode=0,tf=16388,start=window[0],end=window[1],model=model,overrides=p)
 try:q=n.run(tag)
 except Exception as e:save('rejections/'+tag+'.json',dict(case=tag,parameters=p,window=window,model=model,error=str(e)));raise
 row={k:q[k] for k in ['case','model','window','inputs','native','metrics','report_sha256','binary_sha256','disqualified'] if k in q}
 row.update(parameters=p,parameter_id=sha_obj(p))
 file=R/'SEARCH RESULTS.json';records=json.loads(file.read_text()) if file.exists() else []
 if not any(x['case']==tag for x in records):records.append(row);save(file.name,records)
 return row
def rank(r,minimum=45,pfmin=1.1):
 m=r['metrics'];pf=m.get('pf') or 0;wr=m.get('win_rate') or 0
 if r.get('disqualified') or m['trades']<minimum or m['net_profit']<=0 or pf<pfmin:return (-1,0,0,0,0)
 match=2 if pf>=1.2 and wr>=50 and m['win_streak']>m['loss_streak'] else int(pf>=1.2 and wr>=50)
 strength=(pf-1)*math.sqrt(m['trades'])*math.sqrt(max(m['return_pct'],0)/max(r['native']['equity_dd_pct'],1))
 return (match,strength,m.get('sharpe_daily_equity') or -99,m['win_streak']-m['loss_streak'],wr)
def parity():
 n.CASES['ORIGINAL']=dict(label='Shipped0.6R',mode=0,tf=16388,original=True,model=4,start=RECENT[0],end=RECENT[1])
 shipped=n.run('ORIGINAL');research=run_params(DEFAULTS,RECENT,4,'PARITY')
 def legs(tag):
  x=json.loads((R/'native'/tag/'native-trade-legs.json').read_text())
  for t in x:t.pop('ea',None)
  return x
 assert legs('ORIGINAL')==legs(research['case']),'Trade-for-trade parity failed'
 assert research['native']==shipped['native'],'Native metric parity failed'
 save('PARITY.json',dict(passed=True,whole_positions=research['metrics']['trades'],entry_exit_prices_times_lots_costs_equal=True))
def search():
 assert json.loads((R/'PARITY.json').read_text())['passed'];carry=[canonical(DEFAULTS)]
 for stage,changes in STAGES:
  done=R/('stage-'+stage+'.json')
  if done.exists():carry=[r['parameters'] for r in json.loads(done.read_text())['carry']];continue
  trials={sha_obj(canonical({**p,**v})):canonical({**p,**v}) for p in carry for v in changes}
  results=[run_params(p,DEV) for p in trials.values()]
  good=sorted([r for r in results if rank(r)[0]>=0],key=rank,reverse=True)
  if not good:
   seeds=[r for r in results if not r.get('disqualified') and r['metrics']['trades']>=30]
   if not seeds:save('SEARCH FAILURE.json',dict(stage=stage,reason='No execution-valid30trade seed'));raise RuntimeError('No research seed: '+stage)
   good=sorted(seeds,key=lambda r:((r['metrics'].get('pf') or 0),r['metrics']['return_pct']/max(r['native']['equity_dd_pct'],1)),reverse=True)
   save('exploratory-'+stage+'.json',dict(reason='No original development gate pass; research seeds only'))
  carry=[r['parameters'] for r in good[:3]]
  save(done.name,dict(stage=stage,tested=len(trials),carry=good[:3],all_cases=[r['case'] for r in results]))
  print('STAGE '+stage+' complete '+str([(r['metrics']['pf'],r['metrics']['win_rate'],r['metrics']['trades']) for r in good[:3]]),flush=True)
 save('DEVELOPMENT FINALISTS.json',[run_params(p,DEV) for p in carry])
def plateau():
 checks=[]
 for row in json.loads((R/'DEVELOPMENT FINALISTS.json').read_text()):
  p=row['parameters'];key={0:'InpStopBufferATR',1:'InpSwingLookback',2:'InpStopATR'}[p['InpStopMode']];ns={}
  for rr in [.8,1,1.2]:
   for scale in [.8,1,1.2]:
    value=max(2,round(p[key]*scale)) if key=='InpSwingLookback' else max(.05,p[key]*scale)
    r=run_params({**p,'InpRewardRisk':p['InpRewardRisk']*rr,key:value},DEV);ns[r['case']]=r
  neighbours=list(ns.values());eligible=[r for r in neighbours if not r.get('disqualified') and r['metrics']['trades']>=30]
  fraction=sum(r['metrics']['net_profit']>0 for r in eligible)/len(neighbours)
  pf=float(np.median([r['metrics']['pf'] or 0 for r in eligible])) if eligible else 0
  checks.append(dict(finalist=row,neighbours=neighbours,positive_fraction=fraction,median_pf=pf,passed=len(neighbours)>=3 and fraction>=2/3 and pf>=1.1))
 save('PLATEAUS.json',checks)
def choose():
 finals=[]
 for c in json.loads((R/'PLATEAUS.json').read_text()):
  p=c['finalist']['parameters'];d=run_params(p,DEV,4,'NDEV');v=run_params(p,VAL,4,'NVAL')
  finals.append(dict(development=d,validation=v,plateau=c['passed']))
 good=[r for r in finals if r['plateau'] and rank(r['development'])[0]>=0 and rank(r['validation'],20,1.15)[0]>=0]
 chosen=max(good if good else finals,key=lambda r:rank(r['validation'],20,1.15) if good else rank(r['validation'],0,0))
 save('NATIVE FINALISTS.json',finals);save('SELECTION.json',dict(qualified_validation=bool(good),candidate=chosen))
 print('SELECTION FROZEN before recent tests',flush=True)
def confirm():
 p=json.loads((R/'SELECTION.json').read_text())['candidate']['validation']['parameters'];rows=[]
 windows={'1Y':RECENT,'6M':('2026.04.05','2026.10.05'),'3M':('2026.07.05','2026.10.05'),'3Y':('2023.10.05','2026.10.05'),'5Y':('2021.10.05','2026.10.05'),'OLDER':('2019.10.05','2021.10.05')}
 for w,dates in windows.items():
  for label,params in [('CURRENT',DEFAULTS),('OLD3R',{**DEFAULTS,'InpRewardRisk':3.}),('CANDIDATE',p)]:
   r=run_params(params,dates,4,'T'+w);r.update(period=w,variant=label);rows.append(r);save('COMPARISON.json',rows)
if __name__=='__main__':
 with (n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':n.compile_ea()
  elif sys.argv[1]=='smoke':run_params(DEFAULTS,('2026.08.01','2026.09.01'),4,'SMOKE')
  elif sys.argv[1]=='parity':parity()
  elif sys.argv[1]=='search':search();plateau();choose();confirm()
  else:raise ValueError(sys.argv[1])
