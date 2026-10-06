"""Frozen Slow Trend staged optimisation; no deployment or live API."""
from pathlib import Path
import hashlib,importlib.util,json,math,msvcrt,sys
import numpy as np
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('slow_native',R/'native.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n)
DEV=('2021.10.05','2024.10.05');VAL=('2024.10.05','2025.10.05');RECENT=('2025.10.05','2026.10.05')
DEFAULTS=dict(InpSignalTimeframe=16388,InpHorizonMode=3,InpTrendMode=1,InpAllowLong=True,InpAllowShort=True,
 InpSessionMinuteUTC=-1,InpStopMode=0,InpStopATR=1.5,InpExitMode=1,InpRewardRisk=1.0,
 InpMaximumHoldDays=0,InpManagement=0,InpResearchConfirmCandle=False,InpResearchVoteMin=0.0,
 InpResearchSession=0,InpResearchSkipDays=0,InpResearchADXMin=0.0,InpResearchDI=False,
 InpResearchCooldownDays=0,InpResearchStopPercent=.5,InpResearchStopPrice=20.0,
 InpResearchTriggerR=0.0,InpResearchTrailATR=2.5,InpResearchTrailPercent=.25,InpResearchLockR=.2,
 InpResearchBrokerGuard=False)
STAGES=[
 ('timeframe',[dict(InpSignalTimeframe=t) for t in [16388,16408,32769]]),
 ('momentum_entry',[dict(InpHorizonMode=h,InpResearchVoteMin=v,InpResearchConfirmCandle=c)
   for h in [3,0,1,2,4] for v,c in [(0,False),(.99,False),(0,True)]]),
 ('trend_filter',[dict(InpTrendMode=v) for v in [0,1,2,3]]),
 ('initial_stop',[dict(InpStopMode=0,InpStopATR=a) for a in [.75,1,1.5,2,3]]+
  [dict(InpStopMode=m) for m in [1,2,5]]+[dict(InpStopMode=3,InpResearchStopPercent=x) for x in [.25,.5]]+
  [dict(InpStopMode=4,InpResearchStopPrice=x) for x in [10,20]]),
 ('management',[dict(InpManagement=0,InpResearchBrokerGuard=False),
   dict(InpManagement=1,InpResearchTriggerR=.5,InpResearchBrokerGuard=True),
   dict(InpManagement=1,InpResearchTriggerR=1,InpResearchBrokerGuard=True),
   dict(InpManagement=2,InpResearchTriggerR=1,InpResearchTrailATR=1.5,InpResearchBrokerGuard=True),
   dict(InpManagement=2,InpResearchTriggerR=1,InpResearchTrailATR=2.5,InpResearchBrokerGuard=True),
   dict(InpManagement=3,InpResearchTriggerR=1,InpResearchBrokerGuard=True),
   dict(InpManagement=4,InpResearchTriggerR=.5,InpResearchLockR=.2,InpResearchBrokerGuard=True),
   dict(InpManagement=5,InpResearchTriggerR=1,InpResearchTrailPercent=.25,InpResearchBrokerGuard=True),
   dict(InpManagement=6,InpResearchTriggerR=1,InpResearchBrokerGuard=True)]),
 ('target_exit',[dict(InpExitMode=1,InpRewardRisk=x,InpMaximumHoldDays=0) for x in [.5,.6,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+
   [dict(InpExitMode=0,InpMaximumHoldDays=0),dict(InpExitMode=3,InpMaximumHoldDays=5),dict(InpExitMode=2,InpMaximumHoldDays=0)]),
 ('session',[dict(InpResearchSession=s,InpSessionMinuteUTC=-1) for s in [0,1,2,3,4]]+
   [dict(InpResearchSession=0,InpSessionMinuteUTC=m) for m in [60,480,810,840]]),
 ('direction',[dict(InpAllowLong=l,InpAllowShort=s) for l,s in [(True,True),(True,False),(False,True)]]),
 ('ADX_DI',[dict(InpResearchADXMin=a,InpResearchDI=d) for a,d in [(0,False),(20,False),(25,False),(0,True),(20,True),(25,True)]]),
 ('daily_management',[dict(InpResearchCooldownDays=c,InpResearchSkipDays=d,InpMaximumHoldDays=h)
   for c,d,h in [(0,0,0),(2,0,0),(3,0,0),(0,1,0),(0,2,0),(0,3,0),(0,0,2),(0,0,5)]])]
def save(name,v):n.save(R/name,v)
def sha_obj(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()[:14]
def canonical(p):
 p=dict(p)
 if p['InpStopMode']!=0:p['InpStopATR']=1.5
 if p['InpStopMode']!=3:p['InpResearchStopPercent']=.5
 if p['InpStopMode']!=4:p['InpResearchStopPrice']=20.
 if p['InpExitMode'] in [0,2,3]:p['InpRewardRisk']=1.0
 if p['InpManagement']==0:
  for k in ['InpResearchTriggerR','InpResearchTrailATR','InpResearchTrailPercent','InpResearchLockR','InpResearchBrokerGuard']:p[k]=DEFAULTS[k]
 else:
  if p['InpManagement']!=2:p['InpResearchTrailATR']=2.5
  if p['InpManagement']!=5:p['InpResearchTrailPercent']=.25
  if p['InpManagement']!=4:p['InpResearchLockR']=.2
 if p['InpHorizonMode'] in [0,1,2]:p['InpResearchVoteMin']=0.0
 if p['InpSignalTimeframe']==32769:p['InpResearchCooldownDays']=0
 # Integer and float representations of the same MT5 number are one setting.
 integers={'InpSignalTimeframe','InpHorizonMode','InpTrendMode','InpSessionMinuteUTC','InpStopMode','InpExitMode','InpMaximumHoldDays','InpManagement','InpResearchSession','InpResearchSkipDays','InpResearchCooldownDays'}
 return {k:int(v) if k in integers else float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else v for k,v in p.items()}
def slim(q):
 keys=['case','model','window','inputs','native','metrics','report_sha256','binary_sha256','disqualified']
 return {k:q[k] for k in keys if k in q}
def run_params(p,window,model=0,prefix='D'):
 p=canonical(p);tag=prefix+'-'+sha_obj(dict(p=p,window=window,model=model))
 n.CASES[tag]=dict(label=tag,mode=0,tf=int(p['InpSignalTimeframe']),start=window[0],end=window[1],model=model,overrides=p)
 try:q=n.run(tag)
 except Exception as e:
  save('rejections/'+tag+'.json',dict(case=tag,parameters=p,window=window,model=model,error=str(e)));raise
 row=slim(q);row.update(parameters=p,parameter_id=sha_obj(p))
 file=R/'SEARCH RESULTS.json';records=json.loads(file.read_text()) if file.exists() else []
 if not any(x['case']==tag for x in records):records.append(row);save(file.name,records)
 return row
def rank(r,minimum=60,pfmin=1.10):
 m=r['metrics'];pf=m.get('pf') or 0;wr=m.get('win_rate') or 0
 if r.get('disqualified') or m['trades']<minimum or m['net_profit']<=0 or pf<pfmin:return (-1,0,0,0,0)
 match=2 if pf>=1.2 and wr>=50 and m['win_streak']>m['loss_streak'] else int(pf>=1.2 and wr>=50)
 strength=(pf-1)*math.sqrt(m['trades'])*math.sqrt(max(m['return_pct'],0)/max(r['native']['equity_dd_pct'],1))
 return (match,strength,m.get('sharpe_daily_equity') or -99,m['win_streak']-m['loss_streak'],wr)
def parity():
 checks=[]
 for label,rr in [('NORMAL',1.),('FTMO_TARGET',.5)]:
  n.CASES['ORIGINAL_'+label]=dict(label='Shipped '+label,mode=0,tf=16388,original=True,model=4,start=RECENT[0],end=RECENT[1],overrides={'InpRewardRisk':rr})
  shipped=n.run('ORIGINAL_'+label)
  research=run_params({**DEFAULTS,'InpRewardRisk':rr},RECENT,4,'PARITY_'+label)
  legs=json.loads((R/'native'/research['case']/'native-trade-legs.json').read_text())
  original=json.loads((R/'native'/('ORIGINAL_'+label)/'native-trade-legs.json').read_text())
  for group in [legs,original]:
   for t in group:t.pop('ea',None)
  assert legs==original,(label,'Off-switch parity failed')
  assert research['native']==shipped['native'],(label,'Native metric parity failed')
  checks.append(dict(reference=label,whole_positions=len(legs),entry_exit_prices_times_lots_costs_equal=True))
 save('PARITY.json',dict(passed=True,checks=checks))
def search():
 assert json.loads((R/'PARITY.json').read_text())['passed'];carry=[canonical(DEFAULTS)]
 for stage,changes in STAGES:
  done=R/('stage-'+stage+'.json')
  if done.exists():carry=[r['parameters'] for r in json.loads(done.read_text())['carry']];continue
  trials={sha_obj(canonical({**p,**v})):canonical({**p,**v}) for p in carry for v in changes}
  results=[run_params(p,DEV) for p in trials.values()]
  good=sorted([r for r in results if rank(r)[0]>=0],key=rank,reverse=True)
  if not good:
   # Requested exploratory optimisation may carry a loser as a research seed,
   # but this never changes the final qualification thresholds.
   seeds=[r for r in results if not r.get('disqualified') and r['metrics']['trades']>=30]
   if not seeds:
    save('SEARCH FAILURE.json',dict(stage=stage,reason='No execution-valid minimum30 research seed',cases=[r['case'] for r in results]))
    raise RuntimeError('No execution-valid research seed: '+stage)
   def seed_rank(r):
    m=r['metrics'];return ((m.get('pf') or 0),m['return_pct']/max(r['native']['equity_dd_pct'],1),m['trades'])
   good=sorted(seeds,key=seed_rank,reverse=True)
   save('exploratory-'+stage+'.json',dict(reason='No candidate met the original development gate; carrying research seeds only',minimum30=True))
   print('EXPLORATORY SEEDS '+stage+'; development gate remains unmet',flush=True)
  carry=[r['parameters'] for r in good[:3]]
  save(done.name,dict(stage=stage,tested=len(trials),carry=good[:3],all_cases=[r['case'] for r in results]))
  print('STAGE '+stage+' complete '+str([(r['metrics']['pf'],r['metrics']['win_rate'],r['metrics']['trades']) for r in good[:3]]),flush=True)
 save('DEVELOPMENT FINALISTS.json',[run_params(p,DEV) for p in carry])
def plateau():
 checks=[]
 for row in json.loads((R/'DEVELOPMENT FINALISTS.json').read_text()):
  p=row['parameters'];active={0:'InpStopATR',3:'InpResearchStopPercent',4:'InpResearchStopPrice'}.get(int(p['InpStopMode']))
  ns={}
  for rr in [.8,1.,1.2] if p['InpExitMode']==1 else [1.]:
   for scale in [.8,1.,1.2] if active else [1.]:
    candidate={**p,'InpRewardRisk':max(.5,p['InpRewardRisk']*rr)}
    if active:candidate[active]=p[active]*scale
    r=run_params(candidate,DEV);ns[r['case']]=r
  neighbours=list(ns.values());eligible=[r for r in neighbours if not r.get('disqualified') and r['metrics']['trades']>=30]
  fraction=sum(r['metrics']['net_profit']>0 for r in eligible)/len(neighbours)
  pf=float(np.median([r['metrics']['pf'] or 0 for r in eligible])) if eligible else 0
  # Structure-only/no-target settings without any sensitive numeric neighbour are not a demonstrated plateau.
  passed=len(neighbours)>=3 and fraction>=2/3 and pf>=1.10
  checks.append(dict(finalist=row,neighbours=neighbours,positive_fraction=fraction,median_pf=pf,passed=passed))
 save('PLATEAUS.json',checks)
def choose():
 finals=[]
 for check in json.loads((R/'PLATEAUS.json').read_text()):
  p=check['finalist']['parameters'];d=run_params(p,DEV,4,'NDEV');v=run_params(p,VAL,4,'NVAL')
  finals.append(dict(development=d,validation=v,plateau=check['passed']))
 good=[r for r in finals if r['plateau'] and rank(r['development'])[0]>=0 and rank(r['validation'],20,1.15)[0]>=0]
 selected=max(good if good else finals,key=lambda r:rank(r['validation'],20,1.15) if good else rank(r['validation'],0,0))
 save('NATIVE FINALISTS.json',finals);save('SELECTION.json',dict(qualified_validation=bool(good),reason='Older dev, neighbour and validation gates' if good else 'No finalist passed all gates',candidate=selected))
 print('SELECTION FROZEN before recent comparisons',flush=True)
def confirm():
 selected=json.loads((R/'SELECTION.json').read_text())['candidate']['validation']['parameters'];rows=[]
 windows={'1Y':RECENT,'6M':('2026.04.05','2026.10.05'),'3M':('2026.07.05','2026.10.05'),'3Y':('2023.10.05','2026.10.05'),'5Y':('2021.10.05','2026.10.05'),'OLDER':('2019.10.05','2021.10.05')}
 for w,dates in windows.items():
  for label,p in [('CURRENT',DEFAULTS),('FTMO_TARGET',{**DEFAULTS,'InpRewardRisk':.5}),('CANDIDATE',selected)]:
   r=run_params(p,dates,4,'T'+w);r.update(period=w,variant=label);rows.append(r);save('COMPARISON.json',rows)
if __name__=='__main__':
 with (n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  command=sys.argv[1]
  if command=='compile':n.compile_ea()
  elif command=='parity':parity()
  elif command=='search':search();plateau();choose();confirm()
  elif command=='smoke':run_params(DEFAULTS,('2026.09.01','2026.09.08'),4,'SMOKE')
  else:raise ValueError(command)
