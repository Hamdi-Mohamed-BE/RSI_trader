"""Offline replay of native Conte ideas, including overnight floating equity.

No terminal, account, network or order API imports. No live-deployment capability.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json, math, hashlib, time
import numpy as np
from numba import njit

ROOT=Path(__file__).resolve().parent
DAY=86400
UTC=timezone.utc
NY=ZoneInfo('America/New_York')
FIELDS=('balance floor balance_peak ratchet_offset phase ready cycle_start cycle_base cycle_positive cycle_quick '
        'day_balance day_key losses_today opening_days last_open_day entries_today equity_peak dd_pct worst_daily_pct minimum_headroom '
        'closed_ideas wins positive negative phase1_time phase2_time funded_time first_request_time first_cash total_cash '
        'breach_time quick_failure_time payouts win_streak loss_streak max_win_streak max_loss_streak news_deduction '
        'accepted sum_initial_risk max_initial_risk min_initial_risk margin_limited open_position sum_lots breach_reason').split()
(BAL,FLOOR,HIGH,OFFSET,PHASE,READY,CSTART,CBASE,CPOS,CQUICK,DBAL,DKEY,LDAY,ODAYS,LDKEY,ENTRIES,
 PEAK,DD,DAILY,HEAD,TRADES,WINS,POS,NEG,P1,P2,FUNDED,REQUEST,FIRSTCASH,CASH,BREACH,QUICK,PAYOUTS,
 WS,LS,MW,ML,NEWS,ACCEPT,SUMR,MAXR,MINR,MARGIN,OPEN,SUMLOT,BREASON)=range(len(FIELDS))
NFIELDS=len(FIELDS)
REJECT_FIELDS=['below_minimum_lot','headroom_guard','daily_guard','three_losses','phase_wait']
CONFIGS=[
 dict(name='FTMO 10K 0.25% cap / 30% margin',capital=10000.,risk=.0025,instant=False,margin=.3),
 dict(name='FTMO 10K 0.50% cap / 30% margin',capital=10000.,risk=.005,instant=False,margin=.3),
 dict(name='Instant 5K 0.15% cap / 30% margin',capital=5000.,risk=.0015,instant=True,margin=.3),
 dict(name='Instant 5K 0.25% cap / 30% margin',capital=5000.,risk=.0025,instant=True,margin=.3),
]

def epoch(s):return datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def clocks(a,b):
 dates=[datetime.fromtimestamp(t,UTC) for t in range(int(a),int(b)+7200,3600)]
 return np.array([[d.astimezone(ZoneInfo('Europe/Prague')).date().toordinal(),
                   d.astimezone(ZoneInfo('Europe/Helsinki')).date().toordinal(),d.weekday()] for d in dates],dtype=np.int64)

@njit(cache=True)
def key(t,base,clock,col):return clock[int((t-base)//3600),col]

@njit(cache=True)
def next_eod(t,base,clock):
 k=key(t,base,clock,1);u=(math.floor(t/3600)+1)*3600.
 while key(u,base,clock,1)==k:u+=3600.
 return u

@njit(cache=True)
def business_ready(t,n,base,clock):
 while n>0:
  t+=DAY
  if key(t,base,clock,2)<5:n-=1
 return t

@njit(cache=True)
def initial(start,capital,instant):
 s=np.zeros(NFIELDS)
 s[BAL]=s[HIGH]=s[DBAL]=s[PEAK]=s[CBASE]=capital
 s[FLOOR]=capital*(.94 if instant else .90);s[HEAD]=capital-s[FLOOR]
 s[PHASE]=3 if instant else 1;s[READY]=start
 for f in (CSTART,DKEY,LDKEY,P1,P2,FUNDED,REQUEST,BREACH,QUICK):s[f]=-1.
 if instant:s[FUNDED]=start
 s[MINR]=1e100
 return s

@njit(cache=True)
def flat_actions(s,lo,hi,capital,instant,base,clock):
 if s[BREACH]>=0 or s[QUICK]>=0 or s[OPEN]>0:return
 if s[PHASE]==3 and s[FUNDED]<0 and s[READY]<=hi:s[FUNDED]=s[READY]
 if s[PHASE]!=3 or s[CSTART]<0 or s[READY]>hi:return
 t=max(lo,s[CSTART]+14*DAY,s[READY])
 if instant and s[BAL]-s[CBASE]>=.05*capital:
  t=min(t,next_eod(lo,base,clock))
 if t>hi:return
 # Conservative funded-cycle compatibility gate, not a prediction of a firm's discretionary decision.
 if instant and s[CPOS]>0 and s[CQUICK]/s[CPOS]>=.30-1e-12:
  s[QUICK]=t;return
 minimum=capital*.01 if instant else 25.
 eligible=(s[BAL]-s[CBASE]>=.01*capital) if instant else (s[BAL]-capital>=minimum)
 if not eligible:return
 gross=max(0.,s[BAL]-capital)
 if instant:gross=min(gross,max(0.,s[BAL]-s[FLOOR]-.03*capital))
 if gross+1e-9<minimum:return
 paid=gross*(.7 if instant else .8)
 if s[REQUEST]<0:s[REQUEST]=t;s[FIRSTCASH]=paid
 s[BAL]-=gross;s[CASH]+=paid;s[PAYOUTS]+=1
 # A withdrawal is not a trading loss in the daily loss calculation.
 if s[DKEY]==key(t,base,clock,1 if instant else 0):s[DBAL]-=gross
 if instant:
  s[HIGH]=s[FLOOR]+.06*capital;s[OFFSET]=s[HIGH]-s[BAL]
 s[CBASE]=s[BAL];s[CSTART]=-1.;s[CPOS]=s[CQUICK]=0.;s[PEAK]=s[BAL]

@njit(cache=True)
def run(groups,events,start,end,base,clock,capital,risk,instant,margin,stress,minlot=.05,lotstep=.01):
 s=initial(start,capital,instant);reject=np.zeros(5,dtype=np.int64)
 logs=np.zeros((len(groups),7));nlog=0;flat_since=start
 lev=5. if instant else 15.;budget=.0075 if instant else .03 if margin>.5 else .015
 bcol=5 if stress else 1;ndcol=12 if stress else 11
 for i in range(len(groups)):
  g=groups[i];op=g[0]
  if op<start:continue
  if op>end:break
  flat_actions(s,flat_since,op,capital,instant,base,clock)
  if s[BREACH]>=0 or s[QUICK]>=0:break
  if op<s[READY]:reject[4]+=1;continue
  day=key(op,base,clock,1 if instant else 0)
  if day!=s[DKEY]:s[DKEY]=day;s[DBAL]=s[BAL];s[LDAY]=s[ENTRIES]=0
  if s[LDAY]>=3:reject[3]+=1;continue
  head=max(0.,s[BAL]-s[FLOOR]-.002*capital)
  allowance=min(risk*capital,.05*head) if instant else risk*capital
  wanted=allowance/g[3];margin_lots=s[BAL]*margin*lev/g[2]
  lot=math.floor(min(wanted,margin_lots)/lotstep+1e-9)*lotstep
  if lot<minlot-1e-9:reject[0]+=1;continue
  rr=lot*g[3];reserve=1.25*rr+(.0005*capital)
  if s[BAL]-reserve<=s[FLOOR]+(.002 if instant else .02)*capital or (instant and reserve>.2*head):
   reject[1]+=1;continue
  if s[BAL]-reserve<=s[DBAL]-budget*capital:reject[2]+=1;continue
  s[ACCEPT]+=1;s[SUMR]+=rr;s[MAXR]=max(s[MAXR],rr);s[MINR]=min(s[MINR],rr);s[SUMLOT]+=lot
  s[MARGIN]+=int(margin_lots<wanted-1e-9);s[ENTRIES]+=1;s[OPEN]=1
  if s[LDKEY]!=day:s[ODAYS]+=1;s[LDKEY]=day
  if s[PHASE]==3 and s[CSTART]<0:s[CSTART]=op
  before=s[BAL];lastnd=0.;last=-1
  for j in range(int(g[4]),int(g[4]+g[5])):
   e=events[j];t=op+e[0]
   if t>end:break
   eventday=key(t,base,clock,1 if instant else 0)
   if eventday!=s[DKEY]:
    s[DKEY]=eventday;s[DBAL]=s[BAL];s[LDAY]=s[ENTRIES]=0
   last=j;nd=e[ndcol]*lot if instant else 0.
   bal=before+e[bcol]*lot-nd;eq=before+e[bcol+1]*lot-nd;low=before+e[bcol+2]*lot-nd
   if instant:
    # Native partial profits ratchet the balance floor before the idea is fully flat.
    s[HIGH]=max(s[HIGH],before+e[bcol+3]*lot-lastnd+s[OFFSET])
    s[FLOOR]=max(s[FLOOR],min(capital,s[HIGH]-.06*capital))
   s[BAL]=bal;s[PEAK]=max(s[PEAK],eq,bal);s[DD]=max(s[DD],(s[PEAK]-low)/capital*100)
   s[DAILY]=max(s[DAILY],(s[DBAL]-low)/capital*100);s[HEAD]=min(s[HEAD],low-s[FLOOR])
   lastnd=nd
   if low<=s[FLOOR]+1e-9 or (not instant and low<=s[DBAL]-.05*capital+1e-9):
    s[BREACH]=t;s[BREASON]=2 if low<=s[FLOOR]+1e-9 else 1;break
  if s[BREACH]>=0:break
  if last<int(g[4]+g[5])-1:break  # An open idea is not closed using future prices at a horizon.
  s[OPEN]=0;flat_since=g[1];net=s[BAL]-before;s[TRADES]+=1;s[NEWS]+=lastnd
  s[WINS]+=int(net>0);s[POS]+=max(net,0.);s[NEG]+=max(-net,0.)
  if net>0:s[WS]+=1;s[LS]=0
  elif net<0:s[LS]+=1;s[WS]=0;s[LDAY]+=1
  else:s[WS]=s[LS]=0
  s[MW]=max(s[MW],s[WS]);s[ML]=max(s[ML],s[LS])
  if s[PHASE]==3:
   positive=max(0.,events[last,bcol])*lot
   s[CPOS]+=positive;s[CQUICK]+=positive if events[last,10]>0 else 0.
  logs[nlog]=np.array([op,g[1],lot,net,rr,s[BAL],s[FLOOR]]);nlog+=1
  if not instant and s[PHASE]<3 and s[ODAYS]>=4 and s[BAL]>=capital*(1.10 if s[PHASE]==1 else 1.05):
   if s[PHASE]==1:s[P1]=g[1]
   else:s[P2]=g[1]
   s[READY]=business_ready(g[1],2 if s[PHASE]==1 else 5,base,clock);s[PHASE]+=1
   s[BAL]=s[HIGH]=s[DBAL]=s[PEAK]=s[CBASE]=capital;s[FLOOR]=.9*capital
   s[ODAYS]=s[LDAY]=s[ENTRIES]=0.;s[LDKEY]=s[DKEY]=-1;s[CSTART]=-1.;s[CPOS]=s[CQUICK]=0.
 flat_actions(s,flat_since,end,capital,instant,base,clock)
 return s,reject,logs[:nlog]

def summarize(a,rejections,start,capital):
 n=len(a)
 def timing(f):
  v=a[:,f];v=v[v>=0]
  return dict(count=len(v),pct=100*len(v)/n,median_days=float(np.median((v-start)/DAY)) if len(v) else None)
 eligible=a[:,REQUEST]>=0;failed=(a[:,BREACH]>=0)|(a[:,QUICK]>=0)
 return dict(paths=n,phase1=timing(P1),phase2=timing(P2),funded=timing(FUNDED),first_request=timing(REQUEST),
  drawdown_breach=timing(BREACH),quick_failure=timing(QUICK),any_failure_pct=100*float(failed.mean()),
  payout_then_failed=int(np.sum(eligible&failed)),no_request_no_failure_pct=100*float((~eligible&~failed).mean()),
  no_trades=int(np.sum(a[:,ACCEPT]==0)),mean_total_reward=float(a[:,CASH].mean()),
  median_first_reward=float(np.median(a[eligible,FIRSTCASH])) if eligible.any() else None,
  mean_balance=float(a[:,BAL].mean()),median_ideas=float(np.median(a[:,TRADES])),
  median_mean_initial_risk=float(np.median(a[:,SUMR]/np.maximum(a[:,ACCEPT],1))),
  max_initial_risk=float(a[:,MAXR].max()),median_margin_limited_pct=float(np.median(100*a[:,MARGIN]/np.maximum(a[:,ACCEPT],1))),
  paths_encountering_headroom_guard=int(np.sum(rejections[:,1]>0)),
  phase2_duration_median_days=float(np.median((a[a[:,P2]>=0,P2]-a[a[:,P2]>=0,P1])/DAY)) if np.any(a[:,P2]>=0) else None,
  worst_equity_drawdown_pct=float(a[:,DD].max()),median_equity_drawdown_pct=float(np.median(a[:,DD])),
  rejection_counts=dict(zip(REJECT_FIELDS,map(int,rejections.sum(axis=0)))),
  median_known_news_deduction=float(np.median(a[:,NEWS])))

def kwargs(c):return {k:c[k] for k in ('capital','risk','instant','margin')}

def one(groups,events,start,end,base,clock,c,stress,minlot=.05):
 return run(groups,events,start,end,base,clock,stress=stress,minlot=minlot,**kwargs(c))

def block_paths(groups,n=500,seed=9282601):
 """Resample whole 28-day entry blocks; retain full overnight trades.
 Reject a source block if its DST-crossing holding duration cannot be preserved
 with the destination NY wall-clock times. No partial trade truncation.
 """
 rng=np.random.default_rng(seed)
 origin=datetime(2025,9,29,tzinfo=NY);finish=datetime(2026,9,21,tzinfo=NY)
 sources=[origin+timedelta(days=d) for d in range(0,(finish-origin).days-28+1,7)]
 options=[]
 for block in range(7):
  dst=origin+timedelta(days=28*block);candidates=[]
  for src in sources:
   cut=src+timedelta(days=28);part=groups[(groups[:,0]>=src.timestamp())&(groups[:,0]<cut.timestamp())].copy()
   valid=True;shift=(dst-src).days
   for g in part:
    a=datetime.fromtimestamp(g[0],UTC).astimezone(NY);b=datetime.fromtimestamp(g[1],UTC).astimezone(NY)
    newa=(a+timedelta(days=shift)).timestamp();newb=(b+timedelta(days=shift)).timestamp()
    if abs((newb-newa)-(g[1]-g[0]))>.01:valid=False;break
    g[0]=newa;g[1]=newb
   if valid:candidates.append(part)
  assert candidates
  options.append(candidates)
 for _ in range(n):
  # Reject an incompatible whole path, not a trade or part of a holding period.
  # Greedy next-block conditioning can get stuck at a DST/holiday boundary.
  for attempt in range(10000):
   out=np.concatenate([opts[int(rng.integers(len(opts)))] for opts in options])
   if len(out)<2 or np.all(out[1:,0]>=out[:-1,1]):break
  else:raise AssertionError('No non-overlapping whole-block path')
  yield origin.timestamp(),out

def main():
 begun=time.time();base=epoch('2025-09-01');clock=clocks(base,epoch('2027-09-01'))
 begin=epoch('2025-09-27');end=epoch('2026-09-27');output=[];full=[]
 files=[]
 for symbol in ('USTEC','US500'):
  for variant in ('orb-long-1r','orb-long-2r','orb-both-2r','vwap-atr','overnight-atr'):
   tag=f'{symbol}-{variant}';p=ROOT/'native'/f'{tag}-1y-m4'/'prop-ready.npz'
   data=np.load(p);g=data['groups'];ev=data['events'];minlot=.05 if symbol=='USTEC' else .14
   # Do not reuse the artificial tester-end liquidation as a predictive trade.
   ideas=json.loads((p.parent/'ideas.json').read_text())
   keep=np.array(['end of test' not in x['comment'].lower() for x in ideas]);g=g[keep]
   assert len(g)<2 or np.all(g[1:,0]>=g[:-1,1]);assert np.all(ev[:,0]>=-1e-6)
   synthetic=list(block_paths(g));origin=synthetic[0][0];files.append(str(p.relative_to(ROOT)))
   for c in CONFIGS:
    for stress in (False,True):
     label='stress' if stress else 'reference'
     s,r,log=one(g,ev,begin,end,base,clock,c,stress,minlot)
     full.append(dict(variant=tag,profile=c['name'],cost=label,state=dict(zip(FIELDS,map(float,s))),
      rejected=dict(zip(REJECT_FIELDS,map(int,r))),actual_risk_median=float(np.median(log[:,4])) if len(log) else None,
      log=log.tolist()))
     for days in (60,120,180):
      starts=np.arange(epoch('2025-09-29'),end-days*DAY+1,7*DAY);aa=[];rr=[]
      for start in starts:
       ss,re,_=one(g,ev,float(start),float(start+days*DAY),base,clock,c,stress,minlot);aa.append(ss);rr.append(re)
      aa=np.array(aa)
      for f in (P1,P2,FUNDED,REQUEST,BREACH,QUICK):
       mask=aa[:,f]>=0;aa[mask,f]-=starts[mask]-origin
      output.append(dict(variant=tag,profile=c['name'],cost=label,kind='rolling',days=days,stats=summarize(aa,np.array(rr),origin,c['capital'])))
      aa=[];rr=[]
      for start,path in synthetic:
       ss,re,_=one(path,ev,start,start+days*DAY,base,clock,c,stress,minlot);aa.append(ss);rr.append(re)
      output.append(dict(variant=tag,profile=c['name'],cost=label,kind='bootstrap',days=days,stats=summarize(np.array(aa),np.array(rr),origin,c['capital'])))
     print('DONE',tag,c['name'],label,'year balance',round(s[BAL],2),'requests',int(s[PAYOUTS]),flush=True)
 save(ROOT/'PROP_RESULTS.json',output);save(ROOT/'PROP_YEAR.json',full)
 save(ROOT/'PROP_MANIFEST.json',dict(seed=9282601,paths=500,block_days=28,configs=CONFIGS,elapsed_seconds=time.time()-begun,
  files={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files+['prop_sim.py','analyze.py','PROP_PROTOCOL.md']}))
 print('PROP COMPLETE',round(time.time()-begun,1),'seconds',flush=True)
if __name__=='__main__':main()
