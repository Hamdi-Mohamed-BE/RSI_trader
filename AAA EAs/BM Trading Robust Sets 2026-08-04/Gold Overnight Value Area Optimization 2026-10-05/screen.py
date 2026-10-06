"""Cached causal payoff screen. No MT5 API, no changes to old research data."""
from pathlib import Path
import ast,hashlib,itertools,json,math
from datetime import datetime,timezone
import numpy as np
from numba import njit
R=Path(__file__).resolve().parent;OLD=R.parent/'Gold Overnight Value Area Pipeline 2026-09-19'
DEFAULT=dict(bins=64,va=70,stop=0,min_r=0.,entry_end=960,exit=960,target_r=0.,be=0.,trail=0.)
TRAIN=('2021.10.05','2024.10.05');VALID=('2024.10.05','2025.10.05')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def epoch(s):return int(datetime.strptime(s,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
def identity(c):return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:12]
def metrics(a,start,end):
 p=a[:,5];w=l=mw=ml=0
 for v in p:
  w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(mw,w);ml=max(ml,l)
 pos=p[p>0];neg=p[p<0]
 return dict(trades=len(p),return_pct=float(p.sum()/100),pf=float(pos.sum()/-neg.sum()) if len(neg) else None,
  win_rate=float(np.mean(p>0)*100) if len(p) else None,dd=float(a[:,7].max()) if len(p) else 0,
  win_streak=mw,loss_streak=ml,avg_win=float(pos.mean()) if len(pos) else None,avg_loss=float(neg.mean()) if len(neg) else None,
  ambiguous_minutes=int(a[:,12].sum()) if len(p) else 0,
  trades_month=len(p)/((epoch(end)-epoch(start))/86400/30.4375))
def eligible(m,minimum):return m['trades']>=minimum and m['return_pct']>0 and (m['pf'] or 0)>=1.2 and (m['win_rate'] or 0)>=60 and m['win_streak']>m['loss_streak'] and m['dd']<=15
def score(m):return 30*math.log(max(.05,min(3.,m['pf'] or .05)))+2*m['return_pct']/max(1,m['dd'])-.5*m['dd']+.15*((m['win_rate'] or 0)-60)-max(0,150-m['trades'])*.2
def main():
 assert not (R/'selection-frozen.json').exists(),'Already frozen; do not silently reselect'
 manifest=json.loads((OLD/'manifest.json').read_text())
 for name,expected in manifest['files'].items():assert sha(OLD/'data'/(name+'.npz'))==expected
 bars=[np.load(OLD/'data'/(n+'.npz'))['rates'] for n in ['M1','M5']]
 assert all(np.all(np.diff(b['time'])>0) for b in bars)
 m1,m5=[np.column_stack([b[n] for n in ['time','open','high','low','close','tick_volume','spread']]).astype(float) for b in bars]
 days=np.load(OLD/'data/features-64-70.npz')['days']
 source=(OLD/'screen.py').read_text();tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='engine')
 code='@njit(cache=False)\n'+ast.get_source_segment(source,node);ns=dict(njit=njit,np=np,math=math);exec(code,ns);engine=ns['engine']
 rows=[];known={}
 def add(c,stage):
  key=identity(c)
  if key in known:return known[key]
  a=engine(m1,m5,days,epoch(TRAIN[0]),epoch(TRAIN[1]),c['stop'],c['min_r'],c['entry_end'],c['exit'],c['target_r'],c['be'],c['trail'])
  m=metrics(a,*TRAIN);r=dict(id=key,config=c,stage=stage,training=m,score=score(m));rows.append(r);known[key]=r;return r
 def top(pool):return sorted({x['id']:x for x in pool}.values(),key=lambda x:x['score'],reverse=True)[:3]
 parents=[add(DEFAULT,'baseline')]
 stages=[('minimum payoff','min_r',[0.,.1,.25,.5,.75,1.]),('target','target_r',[0.,.5,.6,.75,1.,1.25,1.5,2.]),('stop','stop',[0,1]),
  ('management',None,[(0.,0.),(.25,0.),(.5,0.),(.75,0.),(1.,0.),(0.,.25),(0.,.5),(0.,.75),(0.,1.)]),
  ('last entry','entry_end',[630,660,720,780,840,900,960]),('time exit','exit',[900,930,960])]
 for stage,key,values in stages:
  pool=parents[:]
  for parent in parents:
   for v in values:
    c=dict(parent['config']);c.update({key:v} if key else dict(be=v[0],trail=v[1]))
    if c['exit']<c['entry_end']:continue
    if c['target_r']>0 and c['min_r']>c['target_r']:continue
    pool.append(add(c,stage))
  parents=top(pool);print('SCREEN',stage,len(rows),[(x['id'],round(x['training']['pf'] or 0,3),x['training']['trades']) for x in parents],flush=True)
 finalists=top(rows)
 for r in finalists:
  c=r['config'];a=engine(m1,m5,days,epoch(VALID[0]),epoch(VALID[1]),c['stop'],c['min_r'],c['entry_end'],c['exit'],c['target_r'],c['be'],c['trail'])
  r['validation']=metrics(a,*VALID);r['screen_eligible']=eligible(r['training'],150) and eligible(r['validation'],40)
 rank=sorted(finalists,key=lambda r:(r['screen_eligible'],min(score(r['training']),score(r['validation']))),reverse=True)
 chosen=rank[0];neighbours=[]
 for dr,dm in itertools.product([-.1,0,.1],[-30,0,30]):
  if dr==dm==0:continue
  c=dict(chosen['config'],min_r=round(chosen['config']['min_r']+dr,2),entry_end=chosen['config']['entry_end']+dm)
  if c['min_r']<0 or c['entry_end']<600 or c['entry_end']>960 or c['entry_end']>c['exit'] or (c['target_r']>0 and c['min_r']>c['target_r']):continue
  r=add(c,'joint neighbours');a=engine(m1,m5,days,epoch(VALID[0]),epoch(VALID[1]),c['stop'],c['min_r'],c['entry_end'],c['exit'],c['target_r'],c['be'],c['trail']);r['validation']=metrics(a,*VALID);neighbours.append(r)
 save(R/'SEARCH RESULTS.json',dict(evidence='M1 bar approximation, not native',development=TRAIN,validation=VALID,rows=rows,finalists=finalists,neighbours=neighbours,configurations=len(rows),prior_known_configurations=195,
  source_sha=sha(OLD/'screen.py'),data_sha=manifest['files'],protocol_sha=sha(R/'PROTOCOL.md')))
 save(R/'selection-frozen.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),selected=chosen,neighbours=neighbours,
  search_sha=sha(R/'SEARCH RESULTS.json'),configurations=len(rows),selection='Development/validation only, recent results not yet opened; exploratory diagnostic, not promotion'))
 print('FROZEN',json.dumps(chosen,indent=2),flush=True)
if __name__=='__main__':main()
