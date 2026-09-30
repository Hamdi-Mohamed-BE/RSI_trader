"""Shared-account overlay, paired bootstrap, no live imports. Not tick equity."""
from pathlib import Path
import ast,hashlib,json,math,random,statistics,sys
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;OLD=BASE/'FTMO Combination Study 2026-09-19'
sys.path.insert(0,str(BASE/'FTMO Paper Application 2026-09-26'))
import compare as c
import phase_breakdown as ph
DAY=86400;WEEK=DAY*7
BEGIN=datetime(2025,9,27,tzinfo=timezone.utc).timestamp();END=datetime(2026,9,27,tzinfo=timezone.utc).timestamp()
POOL_START=datetime(2025,9,29,tzinfo=timezone.utc).timestamp();WEEKS=51
START=datetime(2026,9,28,tzinfo=timezone.utc).timestamp()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat() if t is not None else None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def engine(risk):
 ns=c.engine();ns['RISK']=risk
 legacy_costs=ns['costs']
 def costs(row,stress=False):
  g,comm,swap,extra=legacy_costs(row,stress)
  # Public current schedule used as an explicit scenario floor, not historical quotes.
  # Apply the quoted charge on EACH leg conservatively; admission cannot see exit price.
  if row['symbol']=='XAUUSD':comm=min(comm,-.000014*100*(row['open_price']+row['close_price']))
  elif row['symbol']=='USDJPY':comm=min(comm,-10.)
  return g,comm,swap,extra
 def entry_charge(row,commission,extra):
  if row['symbol']=='XAUUSD':return -max(3.5,-row['unit_comm']/2,.000014*100*row['open_price'])-extra/2
  if row['symbol']=='USDJPY':return -max(5.,-row['unit_comm']/2)-extra/2
  return (commission-extra)/2
 ns['costs']=costs;ns['entry_charge']=entry_charge
 ns['rounded']=lambda v:max(0.,math.floor(v/.01+1e-10)*.01)
 src=(OLD/'simulate.py').read_text(encoding='utf-8-sig')
 replacements={
 'if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:':'if False:',
 'lot=rounded(news_risk/riskunit);risk=lot*riskunit':"lot=rounded(news_risk/riskunit)\n            if lot<.01:\n                counts['news_min_lot_over_budget']+=1;continue\n            risk=lot*riskunit\n            assert risk<=news_risk+1e-7",
 "lot=rounded(RISK/r['unit_risk']);risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])":
 "lot=rounded(RISK/r['unit_risk'])\n                if lot<.01:\n                    counts['min_lot_over_budget']+=1;continue\n                risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])\n                assert risk<=RISK+1e-7",
 "if p is None:counts['news_not_admitted_fills']+=1;continue":
 "if p is None:counts['news_not_admitted_fills']+=1;continue\n                p['actual_risk']=r.get('actual_unit_risk',r['unit_risk'])*p['lot']\n                p['env']=max(p['env'],p['actual_risk']*(2 if stress else 1.25))",
 "initial_risk=p['risk'],gross_profit": "initial_risk=p['risk'],actual_fill_stop_risk=p.get('actual_risk',p['risk']),gross_profit",
 "model_dd_pct=dd,closed_dd_pct=closeddd": "open_positions=len(active),pending_orders=len(pending),unclosed_entry_costs=sum(p['entryfee'] for p in active.values()),reserve_equity=bal-envelope(),model_dd_pct=dd,closed_dd_pct=closeddd",
 "fee=(47.5 if sym=='XAGUSD' else 7.)*lot": "fee=(max(7.,.000014*100*(p['buy']+p['sell'])) if sym=='XAUUSD' else 47.5 if sym=='XAGUSD' else 7.)*lot",
 }
 for old,new in replacements.items():assert src.count(old)==1,old;src=src.replace(old,new)
 nodes=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='replay']
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'ftmo14_replay','exec'),ns)
 return ns
def unit_tests():
 ns=engine(50.);replay=ns['replay'];t=START
 def row(i=0,**kw):
  r=dict(key='test'+str(i),symbol='XAUUSD',news=False,op=t+3600+i*120,cl=t+3660+i*120,
   unit_risk=1000.,unit_gross=100.,unit_comm=-7.,unit_swap=0.,open_price=4000.,close_price=4001.,side='Long');r.update(kw);return r
 assert ns['rounded'](.0099)==0 and ns['rounded'](.019)==.01
 assert abs(ns['margin']('XAUUSD',.15,4000)*2-8000)<1e-7
 r=replay([row()],[],t,t+DAY,challenge=False,detail=True)
 expected=(100-.000014*100*8001)*.05
 assert r['trades']==1 and abs(r['balance']-10000-expected)<1e-8
 r=replay([row(unit_risk=6000)],[],t,t+DAY,challenge=False);assert r['trades']==0
 p=dict(key='news',symbol='XAUUSD',op=t+3500,epoch=t+3550,until=t+4200,buy=3001.,sell=2999.,sl=2.)
 rr=[row(i,key='news',news=True,event=p['epoch'],unit_risk=200.,actual_unit_risk=200.,side=side) for i,side in enumerate(('Long','Short'))]
 r=replay(rr,[p],t,t+DAY,news_risk=30.,challenge=False,detail=True)
 assert r['trades']==2 and all(x['initial_risk']==30. for x in r['log'])
 pp=dict(p,buy=4501.,sell=4499.)
 r=replay(rr,[pp],t,t+DAY,news_risk=30.,challenge=False)
 assert r['trades']==0 and r['counts']['news_margin_rejected']==1
 # Daily loss anchor is balance (not equity); Prague DST checked independently.
 assert datetime(2026,7,1,tzinfo=ns['PRAGUE']).utcoffset().total_seconds()==7200
 assert datetime(2026,1,1,tzinfo=ns['PRAGUE']).utcoffset().total_seconds()==3600
 # Each phase needs four different opening days, even if target passed earlier.
 rr=[row(i,op=t+i*DAY+3600,cl=t+i*DAY+3700,unit_gross=6007.) for i in range(4)]
 r=replay(rr,[],t,t+5*DAY,detail=True)
 assert r['passes'][0]['trading_days']==4 and r['phase']==2
 # An unguarded overexposed portfolio fails the reserve proxy, not a measured market loss.
 rr=[row(i,op=t+3600,cl=t+7200) for i in range(11)]
 r=replay(rr,[],t,t+DAY,guards=False,challenge=False)
 # Margin itself prevents >3 positions here; use FX with cheap nominal margin.
 rr=[row(i,op=t+3600,cl=t+7200,symbol='USDJPY',open_price=150,close_price=151) for i in range(11)]
 r=replay(rr,[],t,t+DAY,guards=False,challenge=False)
 assert r['breach']
 assert not replay([],[],t,t+180*DAY)['inactive']
 # Full lifecycle: new account capital after each phase, wait, 14-day reward clock.
 rr=[]
 for i in range(4):rr.append(row(i,op=t+i*DAY+3600,cl=t+i*DAY+3700,unit_gross=6007.))
 for i in range(4):rr.append(row(i+4,op=t+(8+i)*DAY+3600,cl=t+(8+i)*DAY+3700,unit_gross=3007.))
 rr.append(row(8,op=t+22*DAY+3600,cl=t+22*DAY+3700,unit_gross=2007.))
 r=replay(rr,[],t,t+60*DAY,detail=True)
 expected_reward=.8*(2007-.000014*100*8001)*.05
 assert len(r['passes'])==2 and r['payout'] and abs(r['reward']-expected_reward)<1e-6
 assert datetime.fromisoformat(r['request_at']).timestamp()>=t+36*DAY+3600
 return dict(local_checks=15,phase_checks=ph.checks(ns))
def reconcile(r):
 assert len(r['log'])==r['trades']==sum(v['trades'] for v in r['by_ea'].values())
 assert abs(sum(x['net_profit'] for x in r['log'])+r['unclosed_entry_costs']-(r['balance']-10000))<1e-6
 for x in r['log']:
  limit=30 if x['ea']=='news-pulse-xau' else r['risk']
  assert 0<x['initial_risk']<=limit+1e-6
def describe(r):
 duration=(END-BEGIN)/DAY;by={};months=defaultdict(lambda:dict(trades=0,net=0.))
 for key,v in r['by_ea'].items():
  xs=[x for x in r['log'] if x['ea']==key];ws=ls=mw=ml=0
  for x in xs:
   ws=ws+1 if x['net_profit']>0 else 0;ls=ls+1 if x['net_profit']<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
  by[key]=dict(v,win_rate=100*v['wins']/v['trades'] if v['trades'] else None,pf=v['positive']/v['negative'] if v['negative'] else None,
   max_win_streak=mw,max_loss_streak=ml,per_month=v['trades']/(duration/30.4375),per_weekday=v['trades']/260)
 for x in r['log']:
  m=x['close'][:7];months[m]['trades']+=1;months[m]['net']+=x['net_profit']
 return dict(by_ea=by,months=dict(months),trades_per_weekday=r['trades']/260,trades_per_month=r['trades']/(duration/30.4375))
def main():
 checks=unit_tests();print('CHECKS '+json.dumps(checks),flush=True)
 if '--test' in sys.argv:return
 audit=read(ROOT/'DATA_AUDIT.json');assert audit['complete'],'All 14 refreshed histories required'
 data=read(ROOT/'prepared.json');keys=[e['slug'] for e in read(ROOT/'FROZEN.json')['entries']]
 assert set(keys)==set(data['rows'])
 c.END=END;c.START=START;ph.HORIZONS=[30,60,120,180]
 weeks=c.pool(data,POOL_START,WEEKS)
 rng=random.Random(20260927);samples=[[rng.randrange(WEEKS) for _ in range(26)] for _ in range(1000)]
 frozen=dict(source_start=iso(BEGIN),source_end_exclusive=iso(END),pool_start=iso(POOL_START),pool_end=iso(POOL_START+WEEKS*WEEK),
  common_complete_weeks=WEEKS,paths=1000,seed=20260927,ordinary_risks=[50,70],news_per_side=30,
  sources={str(ROOT/p):sha(ROOT/p) for p in ('prepared.json','DATA_AUDIT.json','FROZEN.json','PROTOCOL.md','FTMO_PUBLIC_SPECS.json','study.py')},
  dependencies={str(p):sha(p) for p in (OLD/'simulate.py',OLD/'prepare.py',BASE/'FTMO Paper Application 2026-09-26/compare.py',BASE/'FTMO Paper Application 2026-09-26/phase_breakdown.py')})
 save(ROOT/'SIMULATION_FROZEN.json',frozen)
 results=dict(frozen=frozen,checks=checks,cases=[])
 for risk in (50.,70.):
  ns=engine(risk)
  for guards in (False,True):
   for stress in (False,True):
    rr=[]
    for sample in samples:
     rows,pp=c.sample_rows(data,keys,POOL_START,weeks,sample,START,START+180*DAY)
     rr.append(ns['replay'](rows,pp,START,START+180*DAY,news_risk=30.,stress=stress,guards=guards))
    summary=ph.summarize(rr,ns)
    # Reward eligibility and amounts must be deadline-specific, not eventual amounts.
    for h in summary['horizons']:
     cutoff=START+h['days']*DAY
     h['request_eligible_pct']=100*sum(ph.happened(ph.epoch(r['request_at']),cutoff) for r in rr)/len(rr)
     rewards=[r['reward'] if ph.happened(ph.epoch(r['receipt_at']),cutoff) else 0. for r in rr]
     paid=[v for v in rewards if v>0]
     h['mean_first_reward_per_purchase']=statistics.mean(rewards)
     h['median_first_reward_if_paid']=statistics.median(paid) if paid else None
     h['payout_mc_only_interval']=c.wilson(len(paid),len(rr))
    rows=[dict(r) for k in keys for r in data['rows'][k]];pp=[dict(p) for p in data['placements']]
    hist=ns['replay'](rows,pp,BEGIN,END,news_risk=30,stress=stress,guards=guards,challenge=False,detail=True)
    hist['risk']=risk;reconcile(hist)
    hc=ns['replay'](rows,pp,BEGIN,END,news_risk=30,stress=stress,guards=guards,detail=True)
    recent=[]
    for months,start in ((2,datetime(2026,7,27,tzinfo=timezone.utc).timestamp()),(4,datetime(2026,5,27,tzinfo=timezone.utc).timestamp()),(6,datetime(2026,3,27,tzinfo=timezone.utc).timestamp())):
     rws=[dict(r) for k in keys for r in data['rows'][k] if r['op']>=start];pls=[dict(p) for p in pp if p['op']>=start]
     recent.append(dict(months=months,start=iso(start),result=ns['replay'](rws,pls,start,END,news_risk=30,stress=stress,guards=guards,detail=True)))
    path_fields=('passes','funded_at','request_at','receipt_at','breach_at','reward','phase','counts','trades','model_dd_pct','closed_dd_pct','worst_daily_usd')
    result=dict(risk=risk,guards=guards,stress=stress,summary=summary,historical_continuous=hist,historical_details=describe(hist),
     historical_challenge=hc,recent_historical=recent,paths=[{k:r[k] for k in path_fields} for r in rr])
    results['cases'].append(result);save(ROOT/'RESULTS.json',results)
    print(json.dumps(dict(risk=risk,guards=guards,stress=stress,hist_net=hist['balance']-10000,hist_trades=hist['trades'],
     hist_fail=hist['breach'],funded=summary['horizons'][-1]['funded_pct'],paid=summary['horizons'][-1]['payout_pct'],reserve_fail=summary['horizons'][-1]['breach_before_first_reward_pct'])),flush=True)
 save(ROOT/'CHECKS.json',dict(**checks,cases=8,paths=8000,cash_ledgers_checked=8,source_unchanged=all(sha(Path(p))==v for p,v in frozen['sources'].items())))
 print('COMPLETE 8000 paired portfolio scenarios',flush=True)
if __name__=='__main__':main()
