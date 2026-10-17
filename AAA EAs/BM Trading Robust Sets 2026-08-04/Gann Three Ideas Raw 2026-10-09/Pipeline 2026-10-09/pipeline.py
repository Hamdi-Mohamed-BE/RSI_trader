"""Research pipeline with pre-OOS ranking and one frozen candidate per idea."""
import json, math, sys
import pandas as pd
import numpy as np
import runner as r
import search_plan as sp
R=r.R;CFG=r.CFG

def raw_result(bot,window,control=False):
 code={'gold':'eighth-rejection','us100':'time-cycle','btc':'quartile-control'}[bot]
 if control:code={'gold':'quartile-control','us100':'ema-baseline','btc':'eighth-rejection'}[bot]
 q=r.load(R/'native'/f'allrr05-gp-{sp.SYMBOL[bot].lower()}-{code}-{window}-raw/results.json')
 eq=pd.read_csv(R/'native'/q['tag']/'equity.csv');start,end=[s.replace('.','-') for s in q['window']]
 days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1),tz='UTC')
 daily=pd.Series(eq.equity.to_numpy(),index=pd.to_datetime(eq.epoch,unit='s',utc=True)).resample('D').last().reindex(days).ffill().fillna(10000)
 if bot!='btc':daily=daily[daily.index.weekday<5]
 ret=daily.pct_change();ret.iloc[0]=daily.iloc[0]/10000-1
 q['metrics']['sharpe_daily_equity']=float(ret.mean()/ret.std(ddof=1)*np.sqrt(365 if bot=='btc' else 252)) if ret.std(ddof=1)>0 else None
 q['metrics']['trades_per_month']=len(q['trades'])/((pd.Timestamp(end)-pd.Timestamp(start)).days/30.436875)
 q['metrics']['trades_per_market_day']=len(q['trades'])/len(days if bot=='btc' else days[days.weekday<5])
 return q

def mean_r(q,bot):
 mult=100 if bot=='gold' else 1;out=[]
 for t in q['trades']:
  side=1 if t['side']=='Long' else -1
  expected=side*(t['close_price']-t['open_price'])*t['volume']*mult
  assert abs(expected-t['gross'])<.04*t['exit_legs'],'Broker contract conversion not verified'
  risk=abs(t['open_price']-t['sl'])*t['volume']*mult
  if risk>0:out.append(t['net']/risk)
 return float(np.mean(out)) if out else None

def gates():
 out={}
 for bot in sp.RAW:
  out[bot]={}
  for window in ['3y','5y']:
   a=raw_result(bot,window);b=raw_result(bot,window,True);m=a['metrics'];c=b['metrics']
   checks=dict(positive=m['net_profit']>0,pf_at_least_1_15=(m['pf'] or 0)>=1.15,minimum30=m['trades']>=30,
     better_pf_than_control=(m['pf'] or 0)>(c['pf'] or 0),better_mean_net_R_than_control=mean_r(a,bot)>mean_r(b,bot))
   out[bot][window]=dict(raw=m,control=c,raw_mean_R=mean_r(a,bot),control_mean_R=mean_r(b,bot),checks=checks,passed=all(checks.values()))
  if bot=='us100':
   out[bot]['seeded_clock_control']={}
   for w in ['3y','5y']:
    control=r.load(R/'native'/f'allrr05-gp-ustec-random-cycle-{w}-raw/results.json');a=raw_result(bot,w)
    out[bot]['seeded_clock_control'][w]=control['metrics']
    checks=out[bot][w]['checks'];checks['better_pf_than_seeded_clock']=(a['metrics']['pf'] or 0)>(control['metrics']['pf'] or 0)
    checks['better_mean_R_than_seeded_clock']=mean_r(a,bot)>mean_r(control,bot)
    out[bot][w]['passed']=all(checks.values())
  out[bot]['passed']=all(out[bot][w]['passed'] for w in ['3y','5y'])
 r.save(R/'RAW GATES.json',out);return out

def parity():
 if (R/'PARITY.json').exists() and not (R/'PARITY v1 - target rounding diagnosed.json').exists():
  r.save(R/'PARITY v1 - target rounding diagnosed.json',r.load(R/'PARITY.json'))
 results={}
 keys=['open_epoch','close_epoch','side','volume','open_price','close_price','net','commission','swap','sl','tp','exit_legs']
 def signature(t):return tuple(round(t[k],6) if isinstance(t[k],float) else t[k] for k in keys)
 for bot in sp.RAW:
  q=r.batch('parity-v2-'+bot,[sp.RAW[bot]],bot,'2023-10-09',CFG['end_exclusive'],model=4,optimize=False)[0]
  original=raw_result(bot,'3y');fresh=R/'native'/('allrr05-gp-fresh-original-'+bot+'-parity-raw')/'results.json'
  a=r.load(fresh) if fresh.exists() else original
  left=[signature(t) for t in a['trades']];right=[signature(t) for t in q['trades']]
  exact=left==right
  results[bot]=dict(exact=exact,raw_count=len(left),parameterised_count=len(right),first_differences=[(x,y) for x,y in zip(left,right) if x!=y][:10],
   comparator=str(fresh) if fresh.exists() else original['tag'],original_dated_cash_difference=sum(t['net'] for t in a['trades'])-sum(t['net'] for t in original['trades']),
   cost_drift_note='Fresh original-source replay distinguishes broker swap snapshot drift from a source-rule change; initial dated reports remain immutable.')
  r.save(R/'PARITY.json',results);assert exact,'Raw switches-off trade parity failed: '+bot
 r.status('Exact raw parity verified for all three strategies')

def search(bot):
 frozen_path=R/(bot+' FROZEN.json')
 if frozen_path.exists():return r.load(frozen_path)
 beam=[sp.RAW[bot]];allrows=[];stages={}
 for stage in sp.STAGES:
  cases=r.dedupe(beam+[sp.RAW[bot]]+[c|v for c in beam for v in sp.variants(stage,bot)])
  rows=r.batch(bot+'-dev-'+stage,cases,bot,*CFG['development']);allrows+=rows
  ranked=sorted(rows,key=r.score,reverse=True);beam=[x['parameters'] for x in ranked[:3]]
  stages[stage]=[r.slim(x) for x in ranked[:3]]
  r.save(R/(bot+' SEARCH.json'),dict(stages=stages,last_stage=stage,completed_passes=len(allrows)))
  r.status('Selected development stage '+bot+' '+stage,best=ranked[0]['metrics'])
 groups=[dict(center=c,hashes=[r.digest(x) for x in sp.neighbours(c,bot)]) for c in beam]
 rows=r.batch(bot+'-dev-plateau',r.dedupe([x for c in beam for x in sp.neighbours(c,bot)]),bot,*CFG['development']);allrows+=rows
 lookup={r.digest(x['parameters']):x for x in rows};plateaus=[]
 for g in groups:
  ns=[lookup[k] for k in g['hashes']]
  good=[x for x in ns if x['clean'] and x['metrics']['trades']>=30 and x['metrics']['net_profit']>0 and (x['metrics']['pf'] or 0)>1]
  plateaus.append(g|dict(profitable_neighbour_share=len(good)/len(ns),median_score=float(np.median([r.score(x) for x in ns])),median_pf=float(np.median([x['metrics']['pf'] or 0 for x in ns]))))
 plateaus.sort(key=lambda p:(p['profitable_neighbour_share']>=.6,p['median_score']),reverse=True)
 finals=r.dedupe([p['center'] for p in plateaus])[:3];val=[]
 for i,c in enumerate(finals):val.append(r.batch(f'{bot}-validation-{i}',[c],bot,*CFG['validation'],model=4,optimize=False)[0])
 pl={r.digest(p['center']):p for p in plateaus}
 def rank(x):
  m=x['metrics'];valid=x['clean'] and m['trades']>=30 and m['net_profit']>0 and (m['pf'] or 0)>1 and pl[r.digest(x['parameters'])]['profitable_neighbour_share']>=.6
  return valid,r.score(x)
 val.sort(key=rank,reverse=True);chosen=val[0];valid=bool(rank(chosen)[0])
 unique=len({r.digest(x['parameters']) for x in allrows})
 frozen=dict(bot=bot,parameters=chosen['parameters'],validation=r.slim(chosen),validation_eligible=valid,
  status='Research finalist' if valid else 'Insufficient/failed older validation; diagnostic finalist only',
  plateaus=plateaus,unique_development_configurations=unique,total_screening_passes=len(allrows),
  counted_trials=unique+42+len(finals)+7,prior_raw_trials=42,selection_excludes_oos=True,
  oos_label=CFG['oos_label'],raw_gate_passed=r.load(R/'RAW GATES.json')[bot]['passed'],live_changes=False)
 r.save(R/(bot+' DEVELOPMENT TABLE.json'),[r.slim(x) for x in allrows]);r.save(R/(bot+' VALIDATION.json'),[r.slim(x) for x in val]);r.save(frozen_path,frozen)
 r.status('Frozen from older validation '+bot,eligible=valid,parameters=chosen['parameters'],validation=chosen['metrics']);return frozen

def evaluate(bot):
 p=R/(bot+' EVALUATION.json')
 if p.exists():return r.load(p)
 f=r.load(R/(bot+' FROZEN.json'));c=f['parameters'];records={}
 for label,dates in [('OOS',CFG['oos']),('DEV',CFG['development']),('VALIDATION',CFG['validation']),
  ('5y',['2021-10-09',CFG['end_exclusive']]),('3y',['2023-10-09',CFG['end_exclusive']]),
  ('1y',['2025-10-09',CFG['end_exclusive']]),('6m',['2026-04-09',CFG['end_exclusive']]),('3m',['2026-07-09',CFG['end_exclusive']]),('2026',['2026-01-01',CFG['end_exclusive']])]:
  records[label]=r.batch(bot+'-final-'+label,[c],bot,*dates,model=4,optimize=False)[0]
 records['Raw OOS']=r.batch(bot+'-raw-OOS',[sp.RAW[bot]],bot,*CFG['oos'],model=4,optimize=False)[0]
 for key in ['5y','3y','1y','6m']:records['Raw '+key]=raw_result(bot,key)
 for label,dates in [('3m',['2026-07-09',CFG['end_exclusive']]),('2026',['2026-01-01',CFG['end_exclusive']])]:
  records['Raw '+label]=r.batch(bot+'-raw-'+label,[sp.RAW[bot]],bot,*dates,model=4,optimize=False)[0]
 records['Risk 0.5%']=r.batch(bot+'-risk-half',[c],bot,*CFG['oos'],model=4,optimize=False,risk=.5)[0]
 records['Delay 300ms']=r.batch(bot+'-delay-double',[c],bot,*CFG['oos'],model=4,optimize=False,delay=300)[0]
 r.save(p,records)
 final=R/'Frozen Research Files'/bot;final.mkdir(parents=True,exist_ok=True)
 folder=R/'native'/records['5y']['stage']
 for filename in ['GannSearch.mq5','GannSearch.ex5','Logic.mqh','Parameters.set']:__import__('shutil').copy2(folder/filename,final/filename)
 r.save(final/'FROZEN.json',f|dict(tester_only=True,hashes={p.name:r.sha(p) for p in final.iterdir() if p.is_file() and p.name!='FROZEN.json'}))
 return records

def main():
 sp.freeze();r.rr.prepare();gates()
 mode=sys.argv[1] if len(sys.argv)>1 else 'all'
 if mode in ['search','evaluate','all'] and not (R/'EXPLORATORY APPROVAL.json').exists():
  failed=[b for b,g in r.load(R/'RAW GATES.json').items() if not g['passed']]
  if failed:raise RuntimeError('Saved raw gate requires stopping failed candidates. Exploratory approval has not been recorded: '+', '.join(failed))
 with r.lease():
  if mode in ['parity','all']:parity()
  if mode in ['search','all']:
   for bot in ([sys.argv[2]] if len(sys.argv)>2 else sp.RAW):search(bot)
  if mode in ['evaluate','all']:
   for bot in ([sys.argv[2]] if len(sys.argv)>2 else sp.RAW):evaluate(bot)
 if mode in ['finish','all']:
  import finish
  finish.main()
if __name__=='__main__':main()
