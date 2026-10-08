"""Post-freeze audit only. No parameter changes, trading or network calls."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import gzip,html,importlib.util,math,re,sys
import numpy as np,pandas as pd
import runner as r
R=r.R
spec=importlib.util.spec_from_file_location('news_pipeline_evidence',R.parent.parent/'Calyx Research Pipeline/calyx_pipeline.py')
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
CAL=r.load(R/'calendar.json')['events'];NY=ZoneInfo('America/New_York')

def csv(row,suffix):return pd.read_csv(R/'native'/row['stage']/f"{row['index']}-{suffix}.csv.gz")
def utc(epoch):return datetime.fromtimestamp(int(epoch),timezone.utc).isoformat()
def ny(epoch):return datetime.fromtimestamp(int(epoch),timezone.utc).astimezone(NY).isoformat()
def pf(p):
 loss=-sum(min(v,0) for v in p)
 return sum(max(v,0) for v in p)/loss if loss else None

def enrich(row):
 d=csv(row,'decisions')
 ent=d[d.reason.isin(['entry_displacement','entry_structure'])]
 ts=[]
 for t0 in row['trades']:
  t=dict(t0);m=ent[(ent.epoch-t['open_epoch']).abs()<=1]
  assert len(m)==1,('Unmatched entry',row['stage'],t['position_id'])
  x=m.iloc[0];budget=float(x.risk_budget)
  t.update(event=x.kind,event_epoch=int(x.event_epoch),event_time_ny=ny(x.event_epoch),
   open_time_ny=ny(t['open_epoch']),close_time_ny=ny(t['close_epoch']),signal=x.reason.removeprefix('entry_'),
   risk_budget=budget,planned_risk=float(x.lots*x.unit_loss),realised_r=t['net_profit']/budget,
   pre_atr=float(x.pre_atr),fair=float(x.fair),hold_minutes=(t['close_epoch']-t['open_epoch'])/60,
   fill_rr=abs(t['initial_tp']-t['open_price'])/abs(t['initial_sl']-t['open_price']),
   exit_label={3:'Time',4:'SL',5:'TP'}.get(t['exit_reason'],str(t['exit_reason'])))
  ts.append(t)
 assert len(ts)==len(ent)
 return ts,d

def curve(row):
 df=csv(row,'equity');assert len(df)>0 and df.epoch.is_monotonic_increasing
 assert abs(df.iloc[-1].balance-10000-row['metrics']['net'])<.03
 df['day']=pd.to_datetime(df.epoch,unit='s').dt.normalize()
 last=min(pd.Timestamp(row['end'])-pd.Timedelta(days=1),pd.Timestamp(row['native']['last_quote_epoch'],unit='s').normalize())
 days=pd.date_range(row['start'],last)
 e=df.groupby('day')[['balance','equity']].last().reindex(days).ffill().fillna(10000)
 returns=e.equity.pct_change().fillna(e.equity.iloc[0]/10000-1)
 return df,e,returns

def mc(pnl,returns,seed):
 # Trade-cash and daily returns are different resamples, not one reexecution.
 rng=np.random.default_rng(seed);p=np.asarray(pnl,float);rs=np.asarray(returns,float)
 if not len(p):return dict(status='no_trades',paths=0,return_p05_p50_p95=[None]*3,pf_p05_p50_p95=[None]*3,
  closed_dd_p05_p50_p95=[None]*3,probability_profit_pct=0,total_10pct_breach_proxy_pct=None,daily_5pct_breach_proxy_pct=None)
 paths=10000;block=5;finals=[];dds=[];pfs=[];breach=[];daily=[]
 def ix(n,size):
  starts=rng.integers(0,n,(size,math.ceil(n/block)))
  return ((starts[:,:,None]+np.arange(block))%n).reshape(size,-1)[:,:n]
 for _ in range(10):
  v=p[ix(len(p),1000)];gl=-np.minimum(v,0).sum(axis=1);gp=np.maximum(v,0).sum(axis=1)
  pfs.extend(np.divide(gp,gl,out=np.full(1000,np.nan),where=gl>0))
  x=rs[ix(len(rs),1000)];c=np.cumprod(np.maximum(0,1+x),axis=1)
  peaks=np.maximum.accumulate(np.c_[np.ones(1000),c],axis=1)[:,1:]
  finals.extend((c[:,-1]-1)*100);dds.extend(np.max((peaks-c)/peaks,axis=1)*100)
  breach.extend(np.any(c<=.9,axis=1));daily.extend(np.any(x<=-.05,axis=1))
 def q(v):return np.nanquantile(v,[.05,.5,.95]).tolist()
 return dict(paths=paths,block_length=block,seed=seed,return_p05_p50_p95=q(finals),pf_p05_p50_p95=q(pfs),
  closed_dd_p05_p50_p95=q(dds),probability_profit_pct=float(np.mean(np.asarray(finals)>0)*100),
  total_10pct_breach_proxy_pct=float(np.mean(breach)*100),daily_5pct_breach_proxy_pct=float(np.mean(daily)*100),
  scope='Circular blocks of five trades and, separately, five UTC calendar-day closed-balance returns; fixed historical cash P&L. No synthetic lot resizing, floating/intraday extremes or actual FTMO pass-probability simulation.')

def cost(row,ts):
 q=csv(row,'quotes');q=q[(q.entry==0)&(q.volume>0)&(q.spread_cash>=0)]
 real=q[q.epoch>=pd.Timestamp('2026-01-01').timestamp()]
 positive=real[real.spread_cash>0]
 zero=int((real.ask==real.bid).sum())
 allmedian=float((real.spread_cash/real.volume).median()) if len(real) else None
 out=dict(entry_quotes_2026=len(real),zero_spread_observations=zero,median_all_2026_usd_per_lot=allmedian,
  source_mode='Model 4 available real ticks' if row['model']==4 else 'Model 0 generated ticks; not real',
  positive_observations=len(positive),execution_data_gate=False,
  caveat='2020-2025 generated fallback. Many 2026 real-tick entry quotes have zero bid/ask spread. Positive-quote sensitivity cannot establish accurate historical news fills.')
 if len(positive):
  unit=float((positive.spread_cash/positive.volume).median())
  p=[t['net_profit']-unit*t['volume'] for t in ts]
  out.update(positive_quote_median_usd_per_lot=unit,extra_spread_net=sum(p),extra_spread_return_pct=sum(p)/100,
   extra_spread_pf=pf(p),extra_spread_win_rate_pct=sum(v>0 for v in p)/len(p)*100,
   stress_scope='Add one extra full spread per round trip from the median of strictly positive 2026 native entry quotes for this tick model. Fixed lots, additional to existing costs; sensitivity only, not exact widened-quote reexecution. Median excludes zero artifacts explicitly.')
 else:out['stress_scope']='No positive 2026 entry quote available; no cost invented.'
 return out

def verify_row(row,ts,d):
 checks=0
 def check(x,why):
  nonlocal checks
  assert bool(x),(row['stage'],why);checks+=1
 c=row['parameters'];n=row['native']
 check(n['open_position']==0,'Open final position')
 check(n['failed_entries']==0,'Rejected entry')
 check(n['failed_updates']==0,'Rejected time exit')
 check(abs(sum(t['net_profit'] for t in ts)-n['net'])<.03,'Ledger net')
 for t in ts:
  m=d[d.reason.isin(['entry_displacement','entry_structure']) & ((d.epoch-t['open_epoch']).abs()<=1)].iloc[0]
  check(t['open_epoch']>=t['event_epoch']+120,'Entry before second complete candle')
  check(m.bar_epoch+60<=t['open_epoch'],'Unclosed signal candle')
  check(t['open_epoch']<t['event_epoch']+c['window_minutes']*60,'Entry outside window')
  check(t['hold_minutes']<=c['hold_minutes']+.5,'Late time exit')
  check(t['close_epoch']<=t['event_epoch']+5400+30,'Event hard-close limit')
  check(t['planned_risk']<=t['risk_budget']+.001,'Planned risk exceeds budget')
  check(abs(t['volume']-m.lots)<1e-7,'Fill volume differs')
  check(abs(t['initial_sl']-m.sl)<.011 and abs(t['initial_tp']-m.tp)<.011,'Broker SL/TP differs')
  check((t['side']=='sell' and m.spike==1) or (t['side']=='buy' and m.spike==-1),'Wrong reversion side')
  check(abs(m.first_news_close-m.fair)+.001>=c['impulse_mult']*m.pre_atr,'Weak initial impulse')
  if t['signal']=='structure':check(m.pivot_confirm<=m.bar_epoch and m.pivot_epoch>=m.event_epoch,'Unconfirmed/future pivot')
  else:
   size=m.high-m.low;body=abs(m.close-m.open)
   check(body+.001>=c['body_mult']*m.pre_atr and body/size+.0001>=c['body_fraction'],'Displacement threshold')
  check(c['signal_mode']!=1 or t['signal']=='displacement','Displacement-only mode')
  check(c['signal_mode']!=2 or t['signal']=='structure','Structure-only mode')
 check(len({t['event_epoch'] for t in ts})==len(ts),'Duplicate event trades')
 start=pd.Timestamp(row['start']).timestamp();end=pd.Timestamp(row['end']).timestamp()
 events=[e for e in CAL if start<=e['epoch']<end]
 evlog=d[(d.event_epoch>=start)&(d.event_epoch<end)]
 accounted=set(evlog.event_epoch.astype(int))
 check({e['epoch'] for e in events}.issubset(accounted),'Unaccounted scheduled event')
 return dict(checks=checks,passed=True,scheduled_releases=len(events),accounted_releases=len(accounted))

def group(ts):
 p=[t['net_profit'] for t in ts];w,l=a.streaks(p)
 return dict(trades=len(p),net=sum(p),return_contribution_pct=sum(p)/100,pf=pf(p),
  win_rate_pct=sum(v>0 for v in p)/len(p)*100 if p else None,win_streak=w,loss_streak=l)

def analyse(row,trials,seed):
 ts,d=enrich(row);checks=verify_row(row,ts,d);df,e,ret=curve(row)
 p=[t['net_profit'] for t in ts];metrics=dict(row['metrics'])
 metrics['daily_equity_sharpe']=float(ret.mean()/ret.std(ddof=1)*math.sqrt(365)) if ret.std(ddof=1)>0 else 0
 metrics['actual_last_quote_utc']=utc(row['native']['last_quote_epoch'])
 metrics['win_rate_wilson95_pct']=[100*v for v in a.wilson_interval(sum(v>0 for v in p),len(p))] if p else [None,None]
 metrics['mean_hold_minutes']=float(np.mean([t['hold_minutes'] for t in ts])) if ts else 0
 metrics['max_hold_minutes']=max(t['hold_minutes'] for t in ts) if ts else 0
 cash=pd.Series(0.,index=e.index)
 for t in ts:cash.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
 closed=cash/(10000+cash.cumsum()).shift(1).fillna(10000)
 boot=mc(p,closed,seed);spread=cost(row,ts);sharpe=a.sharpe_statistics(ret.tolist(),trials,365)
 thirds=a.subperiods([a.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit']) for t in ts]) if ts else []
 half=pf(p[len(p)//2:])
 gates=dict(minimum_30_trades=len(ts)>=30,positive_return=metrics['net']>0,pf_above_1=(metrics['pf'] or 0)>1,
  bootstrap_return_p05_positive=(boot['return_p05_p50_p95'][0] or 0)>0,bootstrap_pf_p05_above_1=(boot['pf_p05_p50_p95'][0] or 0)>1,
  deflated_sharpe_95pct=sharpe['deflated_sharpe_pct']>=95,recent_half_pf_above_1=(half or 0)>1,
  two_of_three_parts_positive=sum(x['net_profit']>0 for x in thirds)>=2,
  total_10pct_proxy_below_5pct=boot['total_10pct_breach_proxy_pct'] is not None and boot['total_10pct_breach_proxy_pct']<5,
  measured_positive_quote_stress_pf_above_1=(spread.get('extra_spread_pf') or 0)>1,
  reliable_event_level_bid_ask=False,clean_native_execution=checks['passed'])
 eventrows=[]
 for ev in CAL:
  if not pd.Timestamp(row['start']).timestamp()<=ev['epoch']<pd.Timestamp(row['end']).timestamp():continue
  logs=d[d.event_epoch==ev['epoch']];tr=[t for t in ts if t['event_epoch']==ev['epoch']]
  meaningful=logs[~logs.reason.isin(['event_start','event_end','impulse_confirmed','pivot_confirmed'])]
  reason='traded' if tr else str(meaningful.iloc[-1].reason) if len(meaningful) else 'no qualifying reversal'
  eventrows.append(dict(kind=ev['kind'],release_ny=ev['release_ny'],disposition=reason,**group(tr)))
 return dict(stage=row['stage'],index=row['index'],parameters=row['parameters'],start=row['start'],end_exclusive=row['end'],
  metrics=metrics,verification=checks,monte_carlo=boot,cost_stress=spread,sharpe=sharpe,thirds=thirds,recent_half_pf=half,
  annual_contributions={str(y):group([t for t in ts if pd.Timestamp(t['close_time']).year==y]) for y in e.index.year.unique()},
  events={kind:group([t for t in ts if t['event']==kind]) for kind in ['CPI','NFP','FOMC']},
  gates=gates,all_gates_pass=all(gates.values()),verdict='RESEARCH_ONLY_WATCH' if metrics['net']>0 and (metrics['pf'] or 0)>1 else 'RESEARCH_ONLY_REJECT',
  trades=ts,event_dispositions=eventrows,daily_curve=[dict(date=str(day.date()),balance=float(v.balance),equity=float(v.equity)) for day,v in e.iterrows()])

def main():
 frozen=r.load(R/'FROZEN.json')['locked']
 for name,key in [('engine.mq5','engine_sha256'),('calendar.json','calendar_sha256'),('config.json','config_sha256'),('trials.json','trials_sha256'),('SELECTION.json','selection_sha256')]:
  assert r.sha(R/name)==frozen[key],('Frozen input changed',name)
 trials=r.load(R/'trials.json');unique=len({r.digest(x['parameters']) for x in trials})
 features=r.load(R/'FEATURE-VERIFICATION.json')
 assert features['observations']>=150 and features['fair_matches']==features['observations'] and features['atr_matches']==features['observations'],'Independent feature mismatch'
 # Include the prior short-only/mirrored decision at least once; does not
 # account for all unenumerated researcher asset/model choices.
 correction=unique+1;summary={}
 stages=['raw-3y','raw-5y','in-sample-selected','holdout','recent-1y','recent-6m','recent-3m','delay-500','delay-1000','generated-tick-diagnostic']
 for k,stage in enumerate(stages):
  rows=r.load(R/'native'/stage/'results.json')
  for row in rows:
   key=stage+'-'+str(row['index']);r.status('AUDIT '+key)
   summary[key]=analyse(row,correction,20261008+k*10+row['index'])
 selection=r.load(R/'SELECTION.json')
 selected=selection['selected']
 picked=next(x for x in selection['validation_ranked'] if x['parameters']==selected)
 development=next(x for x in trials if x['parameters']==selected)['metrics']
 plateau=picked['development_plateau']
 durability=dict(raw_3y_5y_gates_pass=r.load(R/'RAW-GATES.json')['passed'],
  selected_development_positive=development['net']>0,
  selected_2024_validation_positive=picked['validation_metrics']['net']>0,
  selected_2024_validation_pf_above_1=(picked['validation_metrics']['pf'] or 0)>1,
  majority_neighbours_profitable=plateau['positive_neighbours']>plateau['neighbours']/2,
  delay_500ms_pf_above_1=(summary['delay-500-0']['metrics']['pf'] or 0)>1,
  delay_1000ms_pf_above_1=(summary['delay-1000-0']['metrics']['pf'] or 0)>1)
 # Pre-2025 failures remain visible regardless of recent holdout profits.
 summary['holdout-1']['gates'].update(durability)
 summary['holdout-1']['all_gates_pass']=all(summary['holdout-1']['gates'].values())
 if not all(list(durability.values())[:5]):
  summary['holdout-1']['verdict']='RESEARCH_ONLY_REJECT_DURABILITY'
 verification=dict(passed=True,checks=sum(x['verification']['checks'] for x in summary.values())+features['observations']*2,unique_searched_configurations=unique,
  independent_feature_checks=features['observations']*2,feature_verification_sha256=r.sha(R/'FEATURE-VERIFICATION.json'),
  dsr_tested_configurations=correction,raw_parity=r.load(R/'PARITY.json'),frozen_inputs_unchanged=True,
  development_validation_gates=durability,selection_parameters=selected,
  normal_mt5_untouched=True,live_changes=False,research_only=True,
  limitations=['Current-vintage official calendar, no point-in-time schedule archive.','Past 2025/2026 results informed asset/model choice: retrospective holdout.',
   'Generated ticks before 2026; many zero-spread event quotes in 2026.','Minute equity sampled; native full-tick floating DD is authoritative.',
   'Monte Carlo and extra-spread subtraction are not a trade reexecution or prop challenge probability.'])
 r.save(R/'SUMMARY.json',summary);r.save(R/'VERIFICATION.json',verification)
 r.status('AUDIT COMPLETE',checks=verification['checks'],unique_configs=unique)
 return summary

if __name__=='__main__':main()
