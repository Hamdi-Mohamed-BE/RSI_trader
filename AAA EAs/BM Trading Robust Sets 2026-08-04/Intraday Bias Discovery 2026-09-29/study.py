"""Fixed time-of-day discovery. Independent holdout; no live MT5 access."""
from pathlib import Path
import argparse,hashlib,json,math
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT=Path(__file__).resolve().parent
SYMS='US30 USTEC US500 XAUUSD BTCUSD ETHUSD EURUSD GBPUSD USDJPY AUDUSD NZDUSD USDCAD USDCHF'.split()
CLOCKS=['UTC','America/New_York','Europe/London']
DATES=['2021-09-27','2024-03-27','2025-09-27','2026-09-27']
CUTS=[pd.Timestamp(x,tz='UTC').timestamp() for x in DATES]
PHASES=['development','validation','holdout']
def save(name,x):
 (ROOT/name).write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda y:y.item() if isinstance(y,np.generic) else str(y)),encoding='utf-8')
def shash(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def slot(t,zone):
 x=pd.to_datetime(t,unit='s',utc=True).tz_convert(zone)
 return np.asarray(x.hour*2+x.minute//30,dtype=int)
def streaks(x):
 best=[0,0];cur=[0,0]
 for v in x:
  cur=[cur[0]+1,0] if v>0 else [0,cur[1]+1] if v<0 else [0,0]
  best=[max(best[i],cur[i]) for i in range(2)]
 return best
def basic(x):
 x=np.asarray(x,float);n=len(x)
 if not n:return dict(n=0,mean_bps=0,return_pct=0,pf=0,win_pct=0,t=0,closed_dd_pct=0,win_streak=0,loss_streak=0)
 pos=x[x>0].sum();neg=-x[x<0].sum();eq=np.r_[0,np.cumsum(x)]
 w,l=streaks(x);sd=x.std(ddof=1) if n>1 else 0
 return dict(n=n,mean_bps=float(x.mean()),return_pct=float(x.sum()/100),pf=float(pos/neg) if neg else (999 if pos else 0),win_pct=float(100*np.mean(x>0)),t=float(x.mean()/sd*np.sqrt(n)) if sd else 0,closed_dd_pct=float(np.max(np.maximum.accumulate(eq)-eq)/100),win_streak=w,loss_streak=l)
def bootstrap(x,seed,B=10000,block=5):
 x=np.asarray(x,float);n=len(x)
 if n<10:return dict(mean_bps=0,lower95_bps=0,upper95_bps=0,p=1)
 rng=np.random.default_rng(seed);blocks=math.ceil(n/block);means=[]
 for first in range(0,B,500):
  starts=rng.integers(0,n,size=(min(500,B-first),blocks))
  idx=((starts[:,:,None]+np.arange(block))%n).reshape(len(starts),-1)[:,:n]
  means.extend(x[idx].mean(axis=1))
 means=np.asarray(means);mu=float(x.mean())
 return dict(mean_bps=mu,lower95_bps=float(np.quantile(means,.05)),upper95_bps=float(np.quantile(means,.95)),p=float((1+np.sum(means-mu>=mu))/(B+1)))
def holm(p):
 p=np.asarray(p);order=np.argsort(p,kind='stable');out=np.empty(len(p));running=0.
 for rank,i in enumerate(order):running=max(running,(len(p)-rank)*p[i]);out[i]=min(1.,running)
 return out
class Market:
 def __init__(self,symbol):
  self.symbol=symbol
  self.spec=pd.read_csv(ROOT/'data/specs.csv.gz').set_index('symbol').loc[symbol]
  self.point=float(self.spec['point']);self.tick=float(self.spec['tick_size'])
  d=pd.read_csv(ROOT/'data'/f'{symbol}_M5.csv.gz');d=d.loc[(d.time>=CUTS[0])&(d.time<CUTS[-1])].copy()
  assert not d.time.duplicated().any(),symbol+' duplicated timestamps'
  assert d.time.is_monotonic_increasing and len(d)>10000
  assert ((d[['open','high','low','close']]>0).all().all() and (d.high>=d[['open','close','low']].max(axis=1)).all() and (d.low<=d[['open','close','high']].min(axis=1)).all())
  assert (d.spread>=0).all() and (d.time%300==0).all()
  self.data=d.reset_index(drop=True)
  dev=d.loc[d.time<CUTS[1]];s=dev.spread.to_numpy();bins=slot(dev.time.to_numpy(),'America/New_York')
  assert np.any(s>0),'No usable development spread history '+symbol
  fallback=float(np.median(s[s>0]));floors=[]
  for i in range(48):
   a=s[(bins==i)&(s>0)];floors.append(float(np.median(a)) if len(a)>=20 else fallback)
  self.floors=np.asarray(floors)
  self.audit=dict(symbol=symbol,bars=len(d),first=str(pd.to_datetime(d.time.iloc[0],unit='s',utc=True)),last=str(pd.to_datetime(d.time.iloc[-1],unit='s',utc=True)),zero_spread_pct=float(100*np.mean(d.spread==0)),development_spread_floor_median_points=float(np.median(floors)),development_global_positive_spread_median_points=fallback,point=self.point,tick_size=self.tick,source_sha256=shash(ROOT/'data'/f'{symbol}_M5.csv.gz'),floor_by_new_york_halfhour=floors,year_bar_counts={str(k):int(v) for k,v in d.groupby(pd.to_datetime(d.time,unit='s',utc=True).dt.year).size().items()})
  assert d.time.iloc[0]<=CUTS[0]+3*86400 and d.time.iloc[-1]>=CUTS[-1]-4*86400,'Incomplete five-year coverage '+symbol
 def phase(self,k):return Phase(self,k)
class Phase:
 def __init__(self,m,k):
  self.m=m;self.k=k;self.d=m.data.loc[(m.data.time>=CUTS[k])&(m.data.time<CUTS[k+1])].reset_index(drop=True)
  self.t=self.d.time.to_numpy(dtype=np.int64);self.o=self.d.open.to_numpy(float);self.c=self.d.close.to_numpy(float)
  self.sp=np.maximum(self.d.spread.to_numpy(float),m.floors[slot(self.t,'America/New_York')])*m.point
  local=pd.to_datetime(self.t,unit='s',utc=True).tz_convert('America/New_York')
  self.roll=(np.asarray(local.hour)==17)&(np.asarray(local.minute)==0)
  self.weekday=np.asarray(pd.to_datetime(self.t,unit='s',utc=True).dayofweek)<5
  self.cache={}
 def trades(self,horizon,direction):
  key=(horizon,direction)
  if key in self.cache:return self.cache[key]
  n=len(self.t);steps=horizon//5;i=np.flatnonzero(self.t%1800==0);i=i[i+steps<n];j=i+steps
  # With sorted unique five-minute timestamps, elapsed-time equality proves no missing bars.
  valid=self.t[j]-self.t[i]==horizon*60
  # Entry exactly at rollover is allowed only after it has occurred; holding across it is not.
  rollcs=np.r_[0,np.cumsum(self.roll)];valid &= (rollcs[j+1]-rollcs[i+1])==0
  if self.m.symbol not in ['BTCUSD','ETHUSD']:valid &= self.weekday[i]
  i=i[valid];j=j[valid]
  gross=direction*(self.o[j]-self.o[i])/self.o[i]*10000
  cost=(self.sp[i] if direction==1 else self.sp[j])/self.o[i]*10000
  df=pd.DataFrame(dict(i=i,j=j,time=self.t[i],exit_time=self.t[j],gross_bps=gross,cost_bps=cost,net_bps=gross-cost,stress_bps=gross-2*cost-2*self.m.tick/self.o[i]*10000))
  df['utc_day']=df.time//86400
  # Ex-post comparator only, never an entry signal; same day, horizon, side and costs.
  df['control_bps']=df.groupby('utc_day').net_bps.transform('mean')
  df['excess_bps']=df.net_bps-df.control_bps
  for z in CLOCKS:
   dt=pd.to_datetime(df.time,unit='s',utc=True).dt.tz_convert(z)
   df[z]=dt.dt.hour*2+dt.dt.minute//30
  self.cache[key]=df;return df
 def select(self,c):
  df=self.trades(c['hold_minutes'],c['direction']);df=df.loc[df[c['clock']]==c['slot']].copy()
  dt=pd.to_datetime(df.time,unit='s',utc=True).dt.tz_convert(c['clock']);df['local_day']=dt.dt.strftime('%Y-%m-%d')
  # Fall-back repeated hour: one trade, the first occurrence, never two.
  return df.drop_duplicates('local_day',keep='first').reset_index(drop=True)
 def marked_dd(self,df,direction):
  pnl=0.;peak=0.;dd=0.
  for row in df.itertuples():
   i=int(row.i);j=int(row.j);entry=self.o[i]
   marks=direction*(self.c[i:j]-entry)/entry*10000
   costs=np.repeat(self.sp[i],j-i) if direction==1 else self.sp[i:j]
   values=np.r_[pnl-costs[0]/entry*10000,pnl+marks-costs/entry*10000,pnl+row.net_bps]
   running=np.maximum.accumulate(np.r_[peak,values])[1:];dd=max(dd,float(np.max(running-values)));peak=max(peak,float(np.max(values)));pnl+=row.net_bps
  return dd/100
 def metrics(self,c):
  df=self.select(c);v=basic(df.net_bps);e=basic(df.excess_bps);s=basic(df.stress_bps)
  months=(CUTS[self.k+1]-CUTS[self.k])/86400/30.4375
  days=len(np.unique(self.t//86400))
  half=(CUTS[self.k]+CUTS[self.k+1])/2
  v.update(excess_mean_bps=e['mean_bps'],excess_t=e['t'],stress_mean_bps=s['mean_bps'],stress_pf=s['pf'],stress_return_pct=s['return_pct'],trades_per_month=len(df)/months,trades_per_trading_day=len(df)/days,marked_dd_pct=self.marked_dd(df,c['direction']) if len(df) else 0,half1_mean_bps=basic(df.loc[df.time<half].net_bps)['mean_bps'],half2_mean_bps=basic(df.loc[df.time>=half].net_bps)['mean_bps'])
  return df,v
def candidate_label(c):return f"{'LONG' if c['direction']==1 else 'SHORT'} {c['slot']//2:02d}:{30*(c['slot']%2):02d} {c['clock']} / {c['hold_minutes']}m"
def discover():
 assert not (ROOT/'FINALISTS.json').exists(),'Finalists already frozen; do not rerun selection against observed holdout'
 chosen=[];audits=[];grid=[]
 for symbol in SYMS:
  m=Market(symbol);audits.append(m.audit);p=m.phase(0);best=None;seen=set();count=0
  for h in [30,60,120]:
   for direction in [1,-1]:
    for clock in CLOCKS:
     for sl in range(48):
      c=dict(symbol=symbol,hold_minutes=h,direction=direction,clock=clock,slot=sl)
      d=p.select(c)
      key=hashlib.sha256(d[['time','exit_time']].to_numpy().tobytes()+str(direction).encode()).hexdigest()
      if key in seen:continue
      seen.add(key);count+=1;v=basic(d.net_bps);e=basic(d.excess_bps);score=min(v['t'],e['t']) if v['n']>=400 else -1e9
      grid.append(dict(**c,**v,excess_mean_bps=e['mean_bps'],excess_t=e['t'],score=score))
      if v['n']>=400 and (best is None or score>best['selection_score']):best=dict(**c,selection_score=score,development_net_mean_bps=v['mean_bps'],development_pf=v['pf'])
  assert best is not None,'Insufficient discovery observations: '+symbol
  best['distinct_configurations']=count;chosen.append(best)
  print(symbol,candidate_label(best),'development PF',round(best['development_pf'],3),flush=True)
 pd.DataFrame(grid).to_csv(ROOT/'development-grid.csv',index=False)
 save('DATA_AUDIT.json',audits)
 save('FINALISTS.json',dict(protocol_sha256=shash(ROOT/'RULES.md'),code_sha256=shash(ROOT/'study.py'),selection_data_end=DATES[1],candidates=chosen))
 print('FROZEN: development-only selection saved; validation/holdout metrics not evaluated.',flush=True)
def evaluate():
 frozen=json.loads((ROOT/'FINALISTS.json').read_text());assert frozen['protocol_sha256']==shash(ROOT/'RULES.md')
 rows=[];all_ledgers=[];flat=[]
 for z,c in enumerate(frozen['candidates']):
  m=Market(c['symbol']);row=dict(candidate=c,phases={},neighbors={},failures=[])
  for k,name in enumerate(PHASES):
   p=m.phase(k);df,v=p.metrics(c);row['phases'][name]=v
   ledger=df[['time','exit_time','gross_bps','cost_bps','net_bps','stress_bps','control_bps','excess_bps']].copy();ledger['symbol']=c['symbol'];ledger['phase']=name;all_ledgers.append(ledger)
   flat.append(dict(symbol=c['symbol'],rule=candidate_label(c),phase=name,**v))
   need=[400,200,150][k]
   if v['n']<need:row['failures'].append(name+': sample')
   if v['pf']<1.15:row['failures'].append(name+': PF below 1.15')
   if v['mean_bps']<=0:row['failures'].append(name+': net mean not positive')
   if v['excess_mean_bps']<=0:row['failures'].append(name+': no time-specific excess')
   if k<2:
    neighbors=[]
    for step in [-1,1]:
     cc=dict(c,slot=(c['slot']+step)%48);nd=p.select(cc);ns=basic(nd.net_bps);neighbors.append(dict(offset_minutes=step*30,**ns))
     if ns['n']==0 or ns['mean_bps']<=0:row['failures'].append(name+f': neighbor {step*30:+}m nonpositive/empty')
    row['neighbors'][name]=neighbors
   else:
    row['inference']=dict(net=bootstrap(df.net_bps,290900+z),excess=bootstrap(df.excess_bps,291900+z))
    row['raw_p']=max(row['inference']['net']['p'],row['inference']['excess']['p'])
    if v['stress_mean_bps']<=0:row['failures'].append('holdout: higher costs erase mean')
    if v['half1_mean_bps']<=0 or v['half2_mean_bps']<=0:row['failures'].append('holdout: losing half-year')
    if min(row['inference']['net']['lower95_bps'],row['inference']['excess']['lower95_bps'])<=0:row['failures'].append('holdout: lower confidence bound not positive')
  rows.append(row);print(c['symbol'],'holdout PF',round(row['phases']['holdout']['pf'],3),'initial failures',len(row['failures']),flush=True)
 adjusted=holm([x['raw_p'] for x in rows])
 for row,p in zip(rows,adjusted):
  row['holm_p']=float(p)
  if p>.05:row['failures'].append('holdout: Holm multiple-test threshold')
  row['survives']=not row['failures']
 save('RESULTS.json',dict(finalists_sha256=shash(ROOT/'FINALISTS.json'),bootstrap_paths=10000,bootstrap_block_days=5,results=rows))
 pd.DataFrame(flat).to_csv(ROOT/'period-results.csv',index=False)
 pd.concat(all_ledgers,ignore_index=True).to_csv(ROOT/'selected-trades.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 report(rows)
 print('SURVIVORS:',[x['candidate']['symbol'] for x in rows if x['survives']],flush=True)
def report(rows):
 lines=['# Intraday time-of-day bias: 13-market test','',f"Research as of 29 September 2026. Same-feed Exness CFD five-minute history; {DATES[0]}–{DATES[-1]} (end exclusive).",'',f"**{sum(x['survives'] for x in rows)} of 13 selected candidates survived every frozen gate.** This is a historical research screen, not a live strategy recommendation.",'','## What was tested','','Half-hour entry times × 30/60/120-minute holds × long/short × UTC/New York/London clocks. Daylight saving handled. Exactly one development-ranked candidate per instrument; no replacement after validation or holdout. Development ends 26 March 2024, validation ends 26 September 2025, final holdout is 27 September 2025–26 September 2026. Dates overlap prior unrelated research, so this is untouched by this search, not globally pristine data.','','Baseline deducts a recorded/development-median spread proxy. Stress doubles that spread and adds two minimum price ticks. Commission is not separately modeled. Windows spanning 17:00 New York or missing bars are excluded. Crypto uses available weekends. UTC half-hour same-day, same-horizon/side average is the time-specificity control, used for evaluation only.','','## Final holdout — selected candidates, including failures','','Times below belong to the specified clock; NY/London follow DST, not fixed UTC offsets. A positive holdout alone does not pass an earlier failure.','','| Market | Selected direction / entry / hold | Dev PF | Validation PF | Holdout PF | Holdout net bps/trade | Stress bps/trade | Trades | Adjusted p | Result |','|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
 for r in rows:
  c=r['candidate'];h=r['phases']['holdout'];lines.append(f"| {c['symbol']} | {candidate_label(c)} | {r['phases']['development']['pf']:.2f} | {r['phases']['validation']['pf']:.2f} | {h['pf']:.2f} | {h['mean_bps']:.2f} | {h['stress_mean_bps']:.2f} | {h['n']} | {r['holm_p']:.4f} | {'PASS' if r['survives'] else 'FAIL'} |")
 lines+=['','1 bp = 0.01%. PF = sum of profitable trade returns / absolute sum of losing trade returns. Adjusted p is Holm across 13 finalists, using the worse of net-return and excess-over-control bootstrap tests. It is not the probability the strategy is false.','','## Holdout performance at fixed notional, without leverage','','Return is cumulative net P&L as a percentage of a constant reference notional; no compounding. Drawdown is five-minute-close mark-to-market, not tick-level maximum drawdown. A smaller tick-level path can contain larger adverse excursions. Trades/day divides by available instrument trading days, including weekends for crypto.','','| Market | Trades/month | Trades/day | Return % | Win % | Marked DD % | Max W / L streak | First / second half mean bps |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  h=r['phases']['holdout'];lines.append(f"| {r['candidate']['symbol']} | {h['trades_per_month']:.1f} | {h['trades_per_trading_day']:.2f} | {h['return_pct']:.2f} | {h['win_pct']:.1f} | {h['marked_dd_pct']:.2f} | {h['win_streak']} / {h['loss_streak']} | {h['half1_mean_bps']:.2f} / {h['half2_mean_bps']:.2f} |")
 lines+=['','## Why each one passed or failed','']
 for r in rows:
  ci=r['inference'];lines.append(f"- **{r['candidate']['symbol']}**: "+('; '.join(r['failures']) if r['failures'] else 'All frozen historical gates passed; still needs native execution and independent-feed confirmation.')+f". One-sided 95% lower mean bounds: net {ci['net']['lower95_bps']:.2f} bps, time-specific excess {ci['excess']['lower95_bps']:.2f} bps.")
 lines+=['','## Data and limitations','','All symbols are Exness broker CFDs. US100 = USTEC, SP500 = US500, XAU = XAUUSD; the seven FX majors are EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD and USDCHF. No claim of interchangeability with another broker, index futures or exchange crypto.','','M5 spreads are not executable bid/ask tick histories. Zero spreads use development-only positive-spread floors; this is a proxy, not historical spread reconstruction. The higher-cost scenario is hypothetical, not measured slippage. No financing across the excluded rollover; gaps and missing bars are rejected. Fixed-notional return estimates are not a position-sizing or prop-firm model.','','The bootstrap uses five-day circular blocks, 10,000 paths. It preserves short local dependence but cannot guarantee future regime stability, rule validity, independent-feed replication or data integrity beyond the checks saved here. One selected candidate per asset is a conservative bounded search; a failed winner does not prove no other intraday strategy exists. No news, weekday, volatility or entry-minute refinements were searched after seeing holdout.','','The collector made no orders. These are Python bid-bar replays on native-exported history, **not native strategy backtests**. No survivor is promoted or deployed.','','## Evidence files','','- RULES.md: protocol frozen before outcomes.','- FINALISTS.json: development-only selection and hashes.','- development-grid.csv: all distinct tested development configurations.','- DATA_AUDIT.json / COLLECTION.json: coverage, cost floors and data hashes.','- selected-trades.csv.gz: full selected-candidate trade ledger.','- period-results.csv / RESULTS.json: detailed three-period metrics, bootstrap results and rejection reasons.','','## Research context','','Searching many seasonal trading rules can manufacture impressive in-sample results; this is why this study separates selection, validation and final tests. [Bailey et al., Backtest Overfitting in Financial Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2731886). The paper motivates safeguards; it does not validate any result above.','']
 (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['discover','evaluate']);args=parser.parse_args()
 discover() if args.stage=='discover' else evaluate()
