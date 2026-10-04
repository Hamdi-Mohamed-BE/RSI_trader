"""Staged development-only selection, then freeze before validation and locked test."""
import math,sys
from pathlib import Path
import pandas as pd
from native import ROOT,OUT,batch,save,load,digest,sha,ledger,status
DEV=('2021.10.02','2024.10.02');VAL=('2024.10.02','2025.10.02');TEST=('2025.10.02','2026.10.02')
RAW=dict(opening_minutes=15,rr=0,entry_cutoff=955,direction=0,ema=0,adaptive_close=0)
SAFE=RAW|dict(adaptive_close=1)
STAGES=[('target','rr',[0,.5,.6,.7,1,1.5,2,3]),('range','opening_minutes',[5,10,15,20,30,45,60]),('cutoff','entry_cutoff',[630,690,750,810,930]),('direction','direction',[0,1,-1]),('ema','ema',[0,50,100,200])]
def register(cases,delay=150):
 p=ROOT/'TRIAL ACCOUNTING.json'
 old=load(p) if p.exists() else {'scope':'Unique configurations in this exploratory campaign, including controls, prior raw US500 candidate and delay sensitivity. Broader prior strategy research is not reconstructed.','configurations':{}}
 old['configurations']['prior-US500-raw']={'source':'Tier ORB Raw 2026-10-02','asset':'US500','parameters':RAW}
 for c in cases:old['configurations'][digest({'parameters':c,'delay':delay})]={'asset':'USTEC','parameters':c,'delay_ms':delay}
 old['total']=len(old['configurations']);save(p,old)
def run(name,cases,window,model=1,delay=150):register(cases,delay);return batch(name,cases,*window,model=model,delay=delay)
def eligible(row):
 s=row['stats'];return row['clean'] and s['trades']>=100 and s['net']>0 and s['pf'] is not None and s['pf']>=1.2 and s['sharpe'] is not None and s['sharpe']>0 and s['equity_dd_pct']<=25
def score(row):
 s=row['stats']
 if not row['clean'] or s['trades']<100 or s['pf'] is None:return -100
 pf=max(.001,s['pf']);n=s['trades'];dd=s['equity_dd_pct'];wr=s['win_pct'] or 0;sr=s['sharpe'] or 0
 return math.log(pf)*math.sqrt(n)*(1+wr/100)/(1+dd/10)+.25*sr
def choose(rows,stage):
 scored=[]
 for i,row in enumerate(rows):
  neighbour=list(range(max(0,i-1),min(len(rows),i+2))) if stage not in ('direction','ema') else [i]
  nearby=[score(rows[j]) for j in neighbour]
  plateau=.7*sorted(nearby)[len(nearby)//2]+.3*score(row)
  scored.append(row|dict(score=score(row),plateau_score=plateau,preferred_screen=eligible(row),neighbour_indices=neighbour))
 pick=max(scored,key=lambda r:(r['preferred_screen'],r['plateau_score'],r['stats']['win_pct'] or 0))
 save(ROOT/('STAGE-'+stage+'.json'),dict(selected=pick,candidates=scored,selection_window=DEV))
 return pick,scored
def main():
 if sys.argv[1]=='smoke':
  run('smoke',[SAFE],('2026.09.21','2026.09.26'),4);return
 if sys.argv[1]=='all':
  original=run('parity-original-1y',[RAW],TEST,4)[0]
  old=load(ROOT.parent/'Tier ORB Raw 2026-10-02/native/USTEC-1y/trades.json')
  d=ledger(original).sort_values('open_epoch')
  assert len(old)==len(d) and abs(sum(t['net_profit'] for t in old)-d.net_profit.sum())<.1,'Original raw parity failed'
  for t,(_,x) in zip(old,d.iterrows()):
   assert abs(pd.Timestamp(t['open_time'],tz='UTC').timestamp()-x.open_epoch)<=1
   assert abs(t['volume']-x.volume)<1e-8 and abs(t['net_profit']-x.net_profit)<.011
  save(ROOT/'PARITY.json',dict(passed=True,trades=len(d),net=round(float(d.net_profit.sum()),2),comparison='Unchanged original raw entry/exit rules; native model 4, latest year'))
  controls=run('development-controls',[RAW,SAFE],DEV)
  selected=SAFE;allrows=[]
  for name,field,values in STAGES:
   cases=[selected|{field:v} for v in values]
   rows=run('development-'+name,cases,DEV)
   chosen,scored=choose(rows,name);selected=chosen['parameters'];allrows.extend(scored)
   status('SELECTED '+name,parameters=selected,stats=chosen['stats'],preferred_screen=chosen['preferred_screen'])
  # Refined final-stage selection must be included; other finalists are independent
  # development alternatives, not picks from validation or the final year.
  byid={}
  for row in allrows:
   key=digest(row['parameters'])
   if key not in byid or row['plateau_score']>byid[key]['plateau_score']:byid[key]=row
  ranked=sorted(byid.values(),key=lambda r:(r['preferred_screen'],r['plateau_score']),reverse=True)
  shortlist=[selected]
  for row in ranked:
   if digest(row['parameters']) not in {digest(c) for c in shortlist}:shortlist.append(row['parameters'])
   if len(shortlist)>=3:break
  save(ROOT/'FROZEN FINALISTS.json',dict(cases=shortlist,based_only_on=DEV,source_main_sha=sha(ROOT/'EA/Main.mqh')))
  confirm=run('development-finalists-m4',shortlist,DEV,4)
  preferred=[r for r in confirm if eligible(r)]
  primary=max(preferred or confirm,key=lambda r:(score(r),r['stats']['win_pct'] or 0))
  frozen=dict(parameters=primary['parameters'],parameters_sha=primary['parameters_sha'],based_only_on=DEV,development=primary,preferred_screen_passed=eligible(primary),trial_count_at_lock=load(ROOT/'TRIAL ACCOUNTING.json')['total'],source_main_sha=sha(ROOT/'EA/Main.mqh'),protocol_sha=sha(ROOT/'PROTOCOL.txt'),warning='Exploratory selection after raw failure. Configuration-locked historical test is not pristine unseen market data.')
  fp=ROOT/'FROZEN PRIMARY.json'
  if fp.exists():assert load(fp)==frozen,'Frozen primary changed; no retuning allowed'
  else:save(fp,frozen)
  status('PRIMARY LOCKED BEFORE VALIDATION/TEST',parameters=primary['parameters'],development=primary['stats'])
  c=[primary['parameters']];records={}
  for name,window in [('validation',VAL),('locked-1y',TEST),('recent-6m',('2026.04.02','2026.10.02')),('full-3y',('2023.10.02','2026.10.02')),('full-5y',('2021.10.02','2026.10.02'))]:records[name]=run(name,c,window,4)[0]
  records['delay-500ms-1y']=run('delay-500ms-1y',c,TEST,4,500)[0]
  for name,window in [('safe-raw-1y',TEST),('safe-raw-5y',('2021.10.02','2026.10.02'))]:records[name]=run(name,[SAFE],window,4)[0]
  save(ROOT/'SUMMARY.json',dict(exploratory=True,primary=frozen,results=records,development_controls=controls,finalists=confirm,trials=load(ROOT/'TRIAL ACCOUNTING.json'),no_live_changes=True,no_other_ideas_started=True))
  status('NATIVE SEARCH COMPLETE; all configuration-locked evidence saved',total_configurations=load(ROOT/'TRIAL ACCOUNTING.json')['total'])
if __name__=='__main__':main()
