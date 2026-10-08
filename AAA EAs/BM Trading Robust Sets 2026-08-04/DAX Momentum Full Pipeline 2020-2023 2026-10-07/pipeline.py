"""Full staged search, frozen pre-2024 selection, then evaluation only."""
from pathlib import Path
import json,math,sys,shutil
import runner as r,build_engine as e,search_plan as p
R=r.R;CFG=r.CONFIG;DEV=CFG['development'];VAL=CFG['validation'];IS=CFG['full_in_sample'];OOS=CFG['out_of_sample']
def init():
 plan=p.freeze();path=R/'SEARCH PLAN.json'
 if path.exists():assert r.load(path)==plan,'Declared search plan changed'
 else:r.save(path,plan)
 original=r.load(R/'PRODUCTION FINGERPRINTS.json')
 assert all(r.sha(Path(path))==digest for path,digest in original.items())
 r.save(R/'SOURCE AUDIT.json',dict(source_fingerprints=e.fingerprints(),entry_body_requirement='NOT in original; optional research-only confirmation',
  train_has_no_real_ticks=True,live_changes=False,date_override=CFG['date_override']))
def parity():
 old=r.load(R/'Original Control/native/DE30-2020-2023/trades.json')
 new=r.batch('parity-2020-2023',[e.RAW],*IS,model=4,optimize=False,verbose=True)[0]
 fields=['open_time','close_time','side','volume','open_price','close_price','commission','swap','net_profit']
 def key(t):
  # The trusted report parser calls sides Long/Short; the CSV export uses
  # buy/sell. Normalize these labels only, never prices, cash or timestamps.
  side={'Long':'buy','Short':'sell','buy':'buy','sell':'sell'}[t['side']]
  return tuple(side if k=='side' else round(float(t[k]),6) if isinstance(t[k],(int,float)) else t[k] for k in fields)
 a=[key(x) for x in old];b=[key(x) for x in new['trades']]
 record=dict(exact=a==b,original_trades=len(a),research_trades=len(b),fields_compared=fields,
  normalized_side_labels={'Long':'buy','Short':'sell'},mismatches=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y],metrics=new['metrics'],
  note='Native tester chart is M1 for all research passes. MT5 Sharpe can differ from an M5 chart despite identical trades; independently computed daily metrics govern selection.')
 r.save(R/'PARITY.json',record);assert record['exact'],'Raw trade parity failed; optimization prohibited'
 r.status('Original-binary parity passed',trades=len(a))
def score(row,minimum=60):
 m=row['metrics'];pf=m['pf'] or 0
 if not row['clean']:return -1e6
 if m['trades']<minimum:return -1000+m['trades']/100
 if m['net']<=0 or pf<=1:return -5+min(0,m['net']/10000)-m['equity_dd']/100
 stability=sum(y['net']>0 for y in m['yearly'])/max(1,len(m['yearly']))
 base=math.log(min(pf,5))*math.sqrt(m['trades'])/(1+m['equity_dd']/15)
 win_bonus=.5*max(-.5,min(.5,m['win_rate_pct']/100-.5))
 streak_bonus=.15*math.log((1+m['max_win_streak'])/(1+m['max_loss_streak']))
 return base*(.5+.5*stability)+win_bonus+streak_bonus+.1*max(-2,min(2,m['daily_closed_balance_sharpe']))
def neighbourhood(c):
 distance='InpInitialStopPercent' if c['InpStopMode']==2 else 'InpInitialStopATR' if c['InpStopMode']==0 else 'InpSignalStopBufferATR'
 second='InpRewardRisk' if c['InpUseFixedTarget'] else 'InpTrailingATR'
 return r.dedupe([c]+[c|{k:max(.01,c[k]*factor)} for k in [distance,second] for factor in [.8,1.2]])
def search():
 assert r.load(R/'PARITY.json')['exact']
 beam=[e.RAW];allrows=[];summaries={}
 for stage in p.STAGES:
  cases=r.dedupe(beam+[e.RAW]+[c|v for c in beam for v in p.variants(stage)])
  rows=r.batch('development-'+stage,cases,*DEV)
  allrows+=rows;ranked=sorted(rows,key=score,reverse=True);beam=[x['parameters'] for x in ranked[:2]]
  summaries[stage]=[r.slim(x) for x in ranked[:3]]
  r.save(R/'SEARCH PROGRESS.json',dict(completed_stage=stage,stages=summaries,total_passes=len(allrows)))
  m=ranked[0]['metrics'];r.status('Completed development '+stage,pf=round(m['pf'] or 0,3),win_rate=round(m['win_rate_pct'],2),trades=m['trades'])
 groups=[dict(center=c,neighbours=neighbourhood(c)) for c in r.dedupe(beam+[e.RAW])]
 rows=r.batch('development-neighbours',r.dedupe([c for group in groups for c in group['neighbours']]),*DEV)
 allrows+=rows;lookup={r.digest(x['parameters']):x for x in rows};plateaus=[]
 for group in groups:
  neighbours=[lookup[r.digest(c)] for c in group['neighbours']]
  center=lookup[r.digest(group['center'])]
  plateaus.append(dict(center=group['center'],center_score=score(center),
   positive_neighbour_share=sum(x['metrics']['net']>0 and x['clean'] for x in neighbours)/len(neighbours),
   median_score=sorted(score(x) for x in neighbours)[len(neighbours)//2],
   median_pf=sorted(x['metrics']['pf'] or 0 for x in neighbours)[len(neighbours)//2],neighbours=len(neighbours)))
 plateaus.sort(key=lambda x:(x['positive_neighbour_share']>=.6,x['median_score']),reverse=True)
 finalists=r.dedupe([x['center'] for x in plateaus])[:3]
 validation=[]
 for i,c in enumerate(finalists):validation.append(r.batch('validation-finalist-'+str(i),[c],*VAL,model=4,optimize=False,verbose=True)[0])
 candidates=[]
 plateau_lookup={r.digest(x['center']):x for x in plateaus}
 for row in validation:
  m=row['metrics'];plateau=plateau_lookup[r.digest(row['parameters'])]
  passes=row['clean'] and m['trades']>=20 and m['net']>0 and (m['pf'] or 0)>1 and plateau['positive_neighbour_share']>=.6
  candidates.append((passes,score(row,20),row))
 candidates.sort(key=lambda item:(item[0],item[1]),reverse=True);chosen=candidates[0][2]
 assert chosen['clean'] and chosen['metrics']['trades']>=20,'No valid pre-OOS finalist'
 # Rerun the frozen front runner and baseline on every generated tick in the whole
 # requested in-sample range. Results cannot cause a re-selection of candidates.
 whole=r.batch('selected-2020-2023',[chosen['parameters']],*IS,model=4,optimize=False,verbose=True)[0]
 fingerprints={r.digest(x['parameters']) for x in allrows}
 frozen=dict(parameters=chosen['parameters'],selected_validation=r.slim(chosen),selected_in_sample=r.slim(whole),
  plateaus=plateaus,passed_internal_validation=candidates[0][0],unique_tested_configurations=len(fingerprints),
  native_search_passes=len(allrows),selection_end_exclusive='2024-01-01',holdout_not_used_for_selection=True,
  holdout_label=CFG['holdout_label'],classification='research-only; generated-tick development; not a live promotion')
 path=R/'FROZEN.json'
 if path.exists():assert r.load(path)==frozen,'Cannot change a frozen candidate'
 else:r.save(path,frozen)
 r.save(R/'DEVELOPMENT TABLE.json',[r.slim(x) for x in allrows]);r.save(R/'VALIDATION TABLE.json',[r.slim(x) for x in validation])
 r.status('Candidate frozen before 2024+ evaluation',unique_configurations=len(fingerprints),internal_validation_pf=chosen['metrics']['pf'])
 return frozen
def evaluate():
 frozen=r.load(R/'FROZEN.json');c=frozen['parameters'];records={}
 # Only these fixed candidate/baseline settings may touch holdout data.
 windows={'OOS':OOS,'2024':['2024-01-01','2025-01-01'],'2025':['2025-01-01','2026-01-01'],
  '2026 YTD':['2026-01-01',CFG['end_exclusive']],
  '1 year':['2025-10-08',CFG['end_exclusive']],'6 months':['2026-04-08',CFG['end_exclusive']],
  '3 months':['2026-07-08',CFG['end_exclusive']]}
 for label,dates in windows.items():
  slug=label.lower().replace(' ','-')
  for variant,case in [('candidate',c),('baseline',e.RAW)]:
   records[label+' '+variant]=r.batch(slug+'-'+variant,[case],*dates,model=4,optimize=False,verbose=True)[0]
  r.save(R/'EVALUATION.json',records)
  r.status('Completed frozen evaluation '+label,candidate_pf=records[label+' candidate']['metrics']['pf'],baseline_pf=records[label+' baseline']['metrics']['pf'])
 diagnostics={}
 for delay in [500,1000]:diagnostics['delay '+str(delay)]=r.batch('stress-delay-'+str(delay),[c],*windows['1 year'],model=4,optimize=False,verbose=True,delay=delay)[0]
 diagnostics['half risk']=r.batch('stress-half-risk',[c],*OOS,model=4,optimize=False,verbose=True,risk=.5)[0]
 r.save(R/'DIAGNOSTICS.json',diagnostics)
 export=R/'Frozen Research EA';export.mkdir(exist_ok=True)
 source=R/'native/oos-candidate'
 for filename in ['DaxSearch.mq5','DaxSearch.ex5','SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh','CalyxAdaptivePortfolio.mqh','Parameters.set']:
  shutil.copy2(source/filename,export/filename)
 r.save(export/'FROZEN.json',frozen|dict(tester_only=True,files={x.name:r.sha(x) for x in export.iterdir() if x.is_file() and x.name!='FROZEN.json'}))
def main():
 init();mode=sys.argv[1] if len(sys.argv)>1 else 'all'
 with r.lease():
  if mode in ['all','parity']:parity()
  if mode in ['all','search']:search()
  if mode in ['all','evaluate']:evaluate()
 if mode=='all':
  import finish
  finish.main()
if __name__=='__main__':main()
