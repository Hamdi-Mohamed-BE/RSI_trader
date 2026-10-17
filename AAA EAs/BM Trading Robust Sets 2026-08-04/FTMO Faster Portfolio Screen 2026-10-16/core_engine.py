"""Estimated sampled-equity immutable-signal replay. NO trading/API/native launch."""
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
from zoneinfo import ZoneInfo
from bisect import bisect_left
from collections import Counter
import hashlib,json,math,statistics,time
R=Path(__file__).resolve().parent;Z=ZoneInfo('Europe/Prague');CAPITAL=10000.0
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def day_of(t):return datetime.fromtimestamp(t,Z).date()
def midnight(d):return datetime.combine(d,datetime.min.time(),tzinfo=Z).timestamp()
def business_date(d,n):
 while n:
  d+=timedelta(days=1)
  if d.weekday()<5:n-=1
 return d
def phase2_ready(passed,policy):
 d=day_of(passed)
 return midnight(d+timedelta(days=1) if policy=='next_prague_midnight' else business_date(d,2))
def access_illustration(passed):
 d=datetime.fromtimestamp(passed,Z);return d.replace(year=business_date(d.date(),5).year,month=business_date(d.date(),5).month,day=business_date(d.date(),5).day).timestamp()
def elapsed(start,end):
 return None if start is None or end is None else dict(inclusive_prague_days=(day_of(end)-day_of(start)).days+1,elapsed_24h_days=(end-start)/86400)
def floor_lot(value,step):return max(0.,round(math.floor(value/step+1e-9)*step,8))
def source_then_guard_lots(equity,unit,spec):
 if not math.isfinite(equity) or not math.isfinite(unit) or equity<=0 or unit<=0:return 0.,0.
 raw=equity*.005/unit
 requested=math.ceil((min(raw,spec['maximum'])-1e-12)/spec['step'])*spec['step']
 requested=min(spec['maximum'],max(spec['minimum'],requested))
 guarded=floor_lot(min(requested,50/unit,spec['maximum']),spec['step'])
 return (guarded if guarded>=spec['minimum']-1e-9 else 0.),requested
def stress_per_lot(row,side):
 p=row['open_price'] if side=='entry' else row['close_price']
 return {'USTEC':1.,'XAUUSD':10.,'USDJPY':1000./p}[row['symbol']]
def margin_per_lot(row,spec):return spec['contract']*(1. if row['symbol']=='USDJPY' else row['open_price'])/spec['leverage']
def new_phase(activation=None):
 return dict(status='not_started' if activation is None else 'pending',activation_epoch=activation,pass_epoch=None,fail_epoch=None,first_trade_epoch=None,entry_days=[],entries=0,closed_positions=0,terminal_balance=None,terminal_equity=None,terminal_daily_anchor=None,hard_failure_kind=None)

class Trial:
 def __init__(self,plan,portfolio,start,cost,handover):
  self.plan=plan;self.portfolio=portfolio;self.start=start;self.cost=cost;self.handover=handover
  self.specs=plan['risk']['specs'];self.active={};self.balance=CAPITAL;self.anchor=CAPITAL;self.eq=CAPITAL
  self.today=None;self.daily_entries=0;self.daily_losses=0;self.day_stopped=False;self.last_entry=-math.inf
  self.phase=1;self.phases={1:new_phase(start['epoch']),2:new_phase()};self.days=set();self.ready=None;self.failed=False;self.finished=False
  self.counts=Counter();self.trades=[];self.mark_observations=0;self.zero_mark_observations=0;self.stale_mark_observations=0;self.max_mark_age=0;self.max_first_mark_lag=0
  self.max_risk=self.max_margin=self.max_daily_loss=0.;self.peak=CAPITAL;self.closed_peak=CAPITAL;self.max_dd=self.max_closed_dd=0.;self.exact_floor_touches=0
 def current(self):return self.phases[self.phase]
 def equity(self,t):
  value=self.balance
  for p in self.active.values():
   value+=p['mark_unit']*p['lots']
  return value
 def observe(self,t):
  self.eq=self.equity(t);self.peak=max(self.peak,self.eq);self.closed_peak=max(self.closed_peak,self.balance)
  self.max_dd=max(self.max_dd,self.peak-self.eq);self.max_closed_dd=max(self.max_closed_dd,self.closed_peak-self.balance)
  self.max_daily_loss=max(self.max_daily_loss,self.anchor-self.eq)
  self.max_risk=max(self.max_risk,sum(p['risk'] for p in self.active.values()));self.max_margin=max(self.max_margin,sum(p['margin'] for p in self.active.values()))
  self.mark_observations+=len(self.active)
  for p in self.active.values():
   if p['mark_epoch'] is None:self.zero_mark_observations+=1;self.max_first_mark_lag=max(self.max_first_mark_lag,t-p['row']['op'])
   else:
    age=max(0,t-p['mark_epoch']);self.max_mark_age=max(self.max_mark_age,age);self.stale_mark_observations+=age>900
  if self.failed or self.finished or self.current()['status']!='pending':return
  if self.eq<=9000.0+1e-8 or self.eq<=self.anchor-500.0+1e-8:
   self.exact_floor_touches+=abs(self.eq-9000)<=1e-8 or abs(self.eq-(self.anchor-500))<=1e-8
   p=self.current();p.update(status='failed',fail_epoch=t,terminal_balance=self.balance,terminal_equity=self.eq,terminal_daily_anchor=self.anchor,hard_failure_kind='static' if self.eq<=9000+1e-8 else 'daily')
   self.failed=True;self.counts['hard_'+p['hard_failure_kind']+'_failure']+=1
  elif self.eq<=self.anchor-300.0+1e-8:
   if not self.day_stopped:self.counts['daily_300_latches']+=1
   self.day_stopped=True
 def maybe_pass(self,t):
  if self.failed or self.finished or self.current()['status']!='pending':return
  target=11000 if self.phase==1 else 10500
  if self.balance>=target-1e-8 and len(self.days)>=4 and not self.active:
   p=self.current();p.update(status='passed',pass_epoch=t,entry_days=sorted(self.days),terminal_balance=self.balance,terminal_equity=self.eq,terminal_daily_anchor=self.anchor)
   if self.phase==1:self.ready=phase2_ready(t,self.handover)
   else:self.finished=True
 def activate(self,t):
  if self.phase==1 and self.phases[1]['status']=='passed' and self.ready is not None and t>=self.ready and t<self.start['horizon_epoch']:
   assert not self.active
   self.phase=2;self.phases[2]=new_phase(self.ready);self.balance=self.anchor=self.eq=CAPITAL;self.days=set();self.daily_entries=self.daily_losses=0;self.day_stopped=False;self.last_entry=-math.inf
   self.peak=self.closed_peak=CAPITAL
 def reject_reason(self,row,t,risk,margin):
  if self.failed:return 'permanent_hard_failure'
  if self.finished:return 'both_phases_completed'
  if self.current()['status']!='pending':return 'phase_review_wait'
  if self.day_stopped:return 'daily_300_latch'
  if self.balance>=(11000 if self.phase==1 else 10500)-1e-8 and len(self.days)>=4:return 'target_entry_gate_await_flat'
  if self.daily_entries>=7:return 'daily_7_entry_limit'
  if self.daily_losses>=3:return 'daily_3_closed_loss_limit'
  total=sum(p['risk'] for p in self.active.values());same=sum(p['risk'] for p in self.active.values() if p['row']['symbol']==row['symbol'])
  if total+risk>225+1e-7:return 'aggregate_initial_risk225'
  if same+risk>150+1e-7:return 'same_symbol_initial_risk150'
  reserve=sum(1.25*p['risk']+5 for p in self.active.values())
  projected=min(self.eq,self.balance-reserve)-1.25*risk-5
  if projected<9200-1e-8:return 'soft_total_buffer9200'
  if self.anchor-projected>300+1e-8:return 'soft_daily_reserve300'
  existing=sum(p['margin'] for p in self.active.values())
  if existing+margin>projected*.8+1e-8 or margin>self.eq-existing+1e-8:return 'proxy_shared_margin'
  if t<self.last_entry+3:return 'entry_reconciliation3s'
  return None
 def opening(self,row,t):
  self.observe(t);self.maybe_pass(t)
  if row['ea'] not in self.plan['baskets'][self.portfolio]:return
  if row['op']<self.start['epoch']:return
  if any(p['row']['ea']==row['ea'] for p in self.active.values()):self.counts['same_ea_exposure']+=1;return
  spec=self.specs[row['symbol']];lot,requested=source_then_guard_lots(self.eq,row['unit_risk'],spec)
  if lot<=0:self.counts['minimum_lot_over50_or_source_request']+=1;return
  risk=lot*row['unit_risk'];margin=lot*margin_per_lot(row,spec);reason=self.reject_reason(row,t,risk,margin)
  if reason:self.counts[reason]+=1;return
  assert risk<=50+1e-7 and lot<=requested+1e-8
  fee=row['entry_unit_cost']*lot-(stress_per_lot(row,'entry')*lot if self.cost=='fixed_cost_stress' else 0.)
  fee=round(fee,2);self.balance=round(self.balance+fee,2);self.active[row['id']]=dict(row=row,lots=lot,requested_lots=requested,risk=risk,margin=margin,mark_unit=0.,mark_epoch=None,entry_cash=fee,phase=self.phase)
  self.last_entry=t;self.daily_entries+=1;self.days.add(str(day_of(t)));p=self.current();p['entries']+=1;p['entry_days']=sorted(self.days)
  if p['first_trade_epoch'] is None:p['first_trade_epoch']=t
  self.counts['opened']+=1;self.observe(t)
 def closing(self,row,t):
  if row['id'] not in self.active:return
  p=self.active.pop(row['id']);swap=row['unit_swap']*(2 if self.cost=='fixed_cost_stress' and row['unit_swap']<0 else 1)
  if p['mark_epoch'] is None:self.max_first_mark_lag=max(self.max_first_mark_lag,t-row['op'])
  cash=(row['unit_gross']+row['unit_commission']+swap-row['entry_unit_cost'])*p['lots']
  if self.cost=='fixed_cost_stress':cash-=stress_per_lot(row,'exit')*p['lots']
  cash=round(cash,2);self.balance=round(self.balance+cash,2);net=round(cash+p['entry_cash'],2);self.daily_losses+=net<-.005;self.phases[p['phase']]['closed_positions']+=1;self.counts['closed']+=1
  self.trades.append(dict(id=row['id'],ea=row['ea'],phase=p['phase'],op=row['op'],cl=t,lots=p['lots'],source_requested_lots=p['requested_lots'],initial_stop_risk=p['risk'],entry_cash=p['entry_cash'],exit_cash=cash,net=net,balance_after_close=self.balance))
  self.observe(t);self.maybe_pass(t)
 def mark(self,row,mark,t):
  if row['id'] in self.active:
   assert row['op']<mark[0]<=t and (row['cl'] is None or mark[0]<row['cl'])
   p=self.active[row['id']];p['mark_unit']=mark[1];p['mark_epoch']=mark[0]
   self.max_first_mark_lag=max(self.max_first_mark_lag,mark[0]-row['op']) if p.get('first_owned_mark',True) else self.max_first_mark_lag
   p['first_owned_mark']=False;self.observe(t)
 def day_reset(self,t):
  self.anchor=self.balance;self.today=str(day_of(t));self.daily_entries=self.daily_losses=0;self.day_stopped=False
  self.activate(t);self.observe(t);self.maybe_pass(t)
 def result(self):
  h=self.start['horizon_epoch'];self.observe(h-1e-4)
  for p in self.phases.values():
   terminal=p['pass_epoch'] or p['fail_epoch'];p['elapsed_to_terminal']=elapsed(p['activation_epoch'],terminal);p['elapsed_first_trade_to_terminal']=elapsed(p['first_trade_epoch'],terminal)
   p['entry_dates']=p['entry_days'];p['entry_days']=len(p['entry_dates'])
  p1,p2=self.phases[1],self.phases[2]
  if self.finished:outcome='horizon_completed_both'
  elif p1['status']=='failed':outcome='failed_phase1'
  elif p2['status']=='failed':outcome='failed_phase2'
  elif p1['status']!='passed':outcome='pending_phase1'
  elif p2['activation_epoch'] is None:outcome='phase2_not_started_wait'
  else:outcome='pending_phase2'
  funded=p2['pass_epoch']
  return dict(portfolio=self.portfolio,start_date=self.start['date'],start_epoch=self.start['epoch'],horizon_date=self.start['horizon_date'],horizon_epoch=h,cost=self.cost,handover=self.handover,phase1=p1,phase2=p2,outcome=outcome,both_pass_epoch=funded,access_5bd_illustration_epoch=access_illustration(funded) if funded else None,total_elapsed_to_both=elapsed(self.start['epoch'],funded),phase2_scheduled_activation_epoch=self.ready,ending_balance=self.balance,ending_sampled_equity=self.eq,open_positions_at_horizon=[dict(id=p['row']['id'],lots=p['lots'],initial_risk=p['risk'],mark_epoch=p['mark_epoch']) for p in self.active.values()],counts=dict(self.counts),mark_coverage=dict(observations=self.mark_observations,initial_zero_observations=self.zero_mark_observations,stale_over900seconds=self.stale_mark_observations,maximum_mark_age_seconds=self.max_mark_age,maximum_initial_zero_segment_seconds=self.max_first_mark_lag),max_sampled_equity_drawdown_cash=self.max_dd,max_closed_drawdown_cash=self.max_closed_dd,max_daily_sampled_equity_loss=self.max_daily_loss,max_initial_open_risk=self.max_risk,max_proxy_margin=self.max_margin,exact_hard_floor_touches=self.exact_floor_touches,trades=self.trades)

def master_events(plan,data):
 priority={ea:i for i,ea in enumerate(plan['candidate_priority'])};events=[]
 for row in data['candidates']:
  events.append((row['op'],3,priority[row['ea']],row['id'],row,None))
  if row['cl'] is not None and row['cl']<data['year_end_exclusive_epoch']:
   events.append((row['cl'],4 if row['cl']==row['op'] else 1,priority[row['ea']],row['id'],row,None))
  for mark in row['marks']:events.append((mark[0],2,priority[row['ea']],row['id'],row,mark))
 d=date.fromisoformat(plan['history']['start_prague']);end=date.fromisoformat(plan['history']['end_exclusive_prague'])
 while d<end:events.append((midnight(d),0,-1,'',None,None));d+=timedelta(days=1)
 events.sort(key=lambda e:e[:4]);return events
def replay(plan,portfolio,start,cost,handover,events):
 model=Trial(plan,portfolio,start,cost,handover)
 for t,kind,priority,key,row,mark in events:
  if kind==0:model.day_reset(t)
  elif kind in (1,4):model.closing(row,t)
  elif kind==2:model.mark(row,mark,t)
  else:model.opening(row,t)
 return model.result()
def median(v):return statistics.median(v) if v else None
def aggregate(trials):
 n=len(trials);p1=[t for t in trials if t['phase1']['status']=='passed'];p2started=[t for t in trials if t['phase2']['activation_epoch'] is not None and t['phase2']['activation_epoch']<t['horizon_epoch']];p2pass=[t for t in p2started if t['phase2']['status']=='passed'];both=[t for t in trials if t['outcome']=='horizon_completed_both']
 def elapsed_values(rows,key):return [t[key]['elapsed_to_terminal']['inclusive_prague_days'] for t in rows]
 total=[t['total_elapsed_to_both']['inclusive_prague_days'] for t in both]
 return dict(starts=n,outcome_counts=dict(Counter(t['outcome'] for t in trials)),phase1_passes=len(p1),phase1_pass_fraction=len(p1)/n if n else None,phase1_median_prague_days_among_passes=median(elapsed_values(p1,'phase1')),phase2_started=len(p2started),phase2_passes=len(p2pass),phase2_conditional_pass_fraction=len(p2pass)/len(p2started) if p2started else None,phase2_unconditional_pass_fraction=len(p2pass)/n if n else None,phase2_median_prague_days_among_passes=median(elapsed_values(p2pass,'phase2')),both_completed=len(both),both_completion_fraction=len(both)/n if n else None,total_median_prague_days_among_completed=median(total),overall_time_to50pct_prague_days=sorted(total)[math.ceil(n/2)-1] if n and len(total)>=math.ceil(n/2) else None,median_trade_count=median([len(t['trades']) for t in trials]),worst_sampled_equity_drawdown_cash=max((t['max_sampled_equity_drawdown_cash'] for t in trials),default=None),worst_daily_sampled_equity_loss=max((t['max_daily_sampled_equity_loss'] for t in trials),default=None),maximum_mark_age_seconds=max((t['mark_coverage']['maximum_mark_age_seconds'] for t in trials),default=0),soft_total_buffer_blocked_trials=sum(t['counts'].get('soft_total_buffer9200',0)>0 for t in trials),soft_daily_blocked_trials=sum(t['counts'].get('soft_daily_reserve300',0)>0 or t['counts'].get('daily_300_latches',0)>0 for t in trials),exact_hard_floor_touches=sum(t['exact_hard_floor_touches'] for t in trials))
def verify_freeze():
 f=read(R/'FROZEN.json');assert all(sha(p)==v for p,v in f['files'].items());assert all(sha(p)==v for p,v in f['source_files'].items())
 assert str(R/'run.py') in f['files'],'Freeze engine before any outcome computation'
 return f
def main():
 verify_freeze();plan=read(R/'PLAN.json');data=read(R/'INPUTS.json');all_events=master_events(plan,data);epochs=[e[0] for e in all_events];trials=[];began=time.time()
 for index,start in enumerate(data['starts']):
  events=all_events[bisect_left(epochs,start['epoch']):bisect_left(epochs,start['horizon_epoch'])]
  for scenario in plan['scenarios']:
   for portfolio in ('CORE3','CORE4'):trials.append(replay(plan,portfolio,start,scenario['cost'],scenario['handover'],events))
  if index%10==0:print('Paired start',index+1,'of',len(data['starts']),flush=True)
 summary=[]
 for scenario in plan['scenarios']:
  for portfolio in ('CORE3','CORE4'):
   subset=[t for t in trials if t['portfolio']==portfolio and t['cost']==scenario['cost'] and t['handover']==scenario['handover']]
   summary.append(dict(portfolio=portfolio,**scenario,all_starts=aggregate(subset),jan2026_plus=aggregate([t for t in subset if t['start_date']>='2026-01-01'])))
 save(R/'OUTCOMES.json',dict(trials=trials,summary=summary,elapsed_seconds=time.time()-began,model='Estimated sampled-five-minute-equity immutable-signal historical replay, not native simultaneous FTMO execution.',plan_sha256=sha(R/'PLAN.json'),inputs_sha256=sha(R/'INPUTS.json'),engine_sha256=sha(Path(__file__)),frozen_sha256=sha(R/'FROZEN.json')))
 save(R/'SUMMARY.json',dict(meta=dict(title='CORE3 versus CORE4: estimated historical FTMO phase timing',history=plan['history'],risk=plan['risk'],model='Estimated sampled-equity immutable-signal replay; not genuine FTMO execution or forward pass probabilities.',live_changes=False,optimization=False,jan2026_plus_eligible_starts=71),results=summary,scenarios=plan['scenarios'],baskets=plan['baskets'],rules=plan['guard'],phases=plan['phases'],float_model=plan['float_model'],costs=plan['costs'],source_coverage=read(R/'SOURCE-COVERAGE.json')['coverage'],outcomes_path=str(R/'OUTCOMES.json'),outcomes_sha256=sha(R/'OUTCOMES.json'),plan_sha256=sha(R/'PLAN.json'),engine_sha256=sha(Path(__file__)),frozen_sha256=sha(R/'FROZEN.json'),limitations=['All cohort starts overlap; fractions are descriptive, not independent probability estimates.','Full180-day follow-up excludes127laterstarts; available starts end9April2026.','Five-year source reports15%real ticks; a portion of latestyearisgenerated; Jan1+subgroupshown.','All four strategies retain historical exit paths and only observed filled-source candidates; skipped sources may omit counterfactual new signals.','First-owned5-minute mark lag uses0floating untilavailable; past marks carried with staleness flags, no future interpolation.','Broker lots, margins, commissions and zero-spread archives are Exness proxies, not validated current FTMO contracts.','No complete SL-management cooldown/request-limit state; retained initial risk substitutes tighteningSLpath; extra open-swap reserve cannotbeisolated.','Guard<=floors is conservative versus official strictly-below failure wording; exacttouchesreported.','180days is analytical horizon, not anFTMO deadline; accountreview/accesswaitingillustrationsnotguarantees.']))
 print(json.dumps(dict(results=summary,seconds=time.time()-began,summary_sha256=sha(R/'SUMMARY.json')),indent=2))
if __name__=='__main__':main()
