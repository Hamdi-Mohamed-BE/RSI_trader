"""Extended evidence audit. Does not modify signals, deals, or original study files.

USDJPY gross P&L converts from JPY at the tester conversion quote, which need not
equal the execution price (especially Model 1 stop fills). Record the difference
from a close-price approximation instead of rejecting otherwise reconciled deals.
Large differences require review; exact net cash/deal-report reconciliation remains.
"""
from pathlib import Path
from collections import Counter
from datetime import timedelta
import gzip,hashlib,math,re,json,sys
ROOT=Path(__file__).resolve().parent
RAW=ROOT.parent/'Four Screenshot Ideas Raw 2026-09-27'
sys.path.insert(0,str(RAW))
import audit as old

def audit(folder):
 meta=old.load(folder/'run.json');trades=sorted(old.load(folder/'trades.json'),key=lambda t:t['close_time'])
 mode=meta['case']['mode'];control=meta['case']['control']
 rb=gzip.decompress((folder/'report.htm.gz').read_bytes());assert hashlib.sha256(rb).hexdigest()==meta['report_sha']
 body=rb.decode('utf-16') if rb[:2] in (b'\xff\xfe',b'\xfe\xff') else rb.decode('utf-8-sig')
 oo=old.filled_orders(body);assert len(oo)==len(trades)
 journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
 pat=r'IDEA_ORDER t=([\d.]+ [\d:]+) mode=(\d+) control=(\d+) side=(-?\d+) pending=(\d+) entry=([\d.]+) sl=([\d.]+) tp=([\d.]+) lot=([\d.]+) risk=([\d.]+) eq=([\d.]+) high=([\d.]+) low=([\d.]+) due=([\d.]+ [\d:]+) order=(\d+)'
 logs={}
 for v in re.findall(pat,journal):
  at,md,ct,side,pending,entry,sl,tp,lot,risk,eq,hi,lo,due,tid=v
  assert int(md)==mode and int(ct)==control
  logs[int(tid)]=dict(time=old.stamp(at),side=int(side),pending=int(pending),entry=float(entry),stop=float(sl),target=float(tp),lot=float(lot),risk=float(risk),eq=float(eq),hi=float(hi),lo=float(lo))
 sigs={old.stamp(t):dict(bar=old.stamp(b),close=float(cl),atr=float(atr),side=int(sd)) for t,b,cl,atr,sd in re.findall(r'IDEA_SIGNAL now=([\d.]+ [\d:]+) bar=([\d.]+ [\d:]+) close=([\d.]+) atr=([\d.]+) side=(-?\d+)',journal)}
 sma={}
 for day,mean,vals in re.findall(r'IDEA_SMA date=(\d+) mean=([\d.]+) closes=([^\r\n]+)',journal):
  pairs=[v.split(':') for v in vals.rstrip(',').split(',')]
  assert len(pairs)==25 and len({p[0] for p in pairs})==25
  assert all(int(p[0])<int(day) for p in pairs)
  assert abs(sum(float(p[1]) for p in pairs)/25-float(mean))<1e-5
  sma[int(day)]=float(mean)
 filters={int(d):(float(b),float(m),int(p)) for d,b,m,p in re.findall(r'IDEA_FILTER date=(\d+) bid=([\d.]+) sma=([\d.]+) pass=(\d+)',journal)}
 tick=float(re.search(r'IDEA_SPEC[^\r\n]* tick=([\d.]+)',journal)[1]);contract=float(re.search(r'IDEA_SPEC[^\r\n]*contract=([\d.]+)',journal)[1])
 entries=Counter();late=[];risks=[];notionals=[];rr=[];conversion=[];forced=[]
 for t in trades:
  op=old.stamp(t['open_time']);cl=old.stamp(t['close_time']);local=old.clock(op,mode);close=old.clock(cl,mode);side=1 if t['side']=='Long' else -1
  matches=[o for o in oo if o['filled']==op and o['side']==t['side']];assert len(matches)==1
  order=matches[0];log=logs[order['ticket']]
  assert abs(t['volume']-log['lot'])<1e-7 and side==log['side']
  entries[local.date()]+=1;assert 0<=local.weekday()<=4
  assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.021
  numerator=side*(t['close_price']-t['open_price'])*t['volume']*contract
  expected=numerator/(t['close_price'] if t['symbol']=='USDJPY' else 1)
  if t['symbol']=='USDJPY':
   discrepancy=abs(expected-t['gross_profit'])
   if discrepancy>max(.03,abs(expected)*.002):
    conversion.append(dict(trade=t['number'],difference_usd=discrepancy,execution_price=t['close_price'],implied_conversion_price=numerator/t['gross_profit'] if t['gross_profit'] else None))
   assert discrepancy<max(.10,abs(expected)*.02),(folder.name,t,'unexplained FX conversion >2%')
  else:assert abs(expected-t['gross_profit'])<.04,(folder.name,t,expected)
  if mode in (1,4):
   assert order['stop']>0 and side*(t['open_price']-order['stop'])>0
   exposure=abs(t['open_price']-order['stop'])*t['volume']*contract/(order['stop'] if t['symbol']=='USDJPY' else 1)
   risks.append(100*exposure/log['eq'])
   if order['target']:rr.append(side*(order['target']-t['open_price'])/abs(t['open_price']-order['stop']))
  else:
   assert order['stop']==order['target']==0
   notionals.append(t['open_price']*contract*t['volume']);assert notionals[-1]<=10000*1.001
  if mode==1:
   placed=old.clock(order['placed'],mode);assert placed.hour==6 and placed.minute==0
   assert 360<=local.hour*60+local.minute<1080
   assert abs(order['stop']-(log['lo'] if side>0 else log['hi']))<=tick+1e-6
   assert order['target']==0
   if not control:assert abs(order['entry']-(log['hi'] if side>0 else log['lo']))<=tick*.51+1e-7
   due=local.replace(hour=18,minute=0,second=0,microsecond=0)
  elif mode==2:
   assert local.weekday()==0 and local.hour==1 and local.minute==5
   day=int(local.strftime('%Y%m%d'));assert filters[day][2]==1
   if not control:assert filters[day][0]<sma[day] and abs(filters[day][1]-sma[day])<1e-6
   due=local.replace(hour=23,minute=50,second=0,microsecond=0)+timedelta(days=1)
  elif mode==3:
   if control:continue
   assert local.hour==1 and local.minute==5
   due=local.replace(hour=23,minute=50,second=0,microsecond=0)
  else:
   signal=sigs[log['time']];assert timedelta(minutes=5)<=log['time']-signal['bar']<timedelta(minutes=6)
   assert 590<=local.hour*60+local.minute<=900
   if not control:assert side*(signal['close']-(log['hi'] if side>0 else log['lo']))>0
   else:assert local.hour*60+local.minute==590
   intended=log['lo']-.25*signal['atr'] if side>0 else log['hi']+.25*signal['atr']
   rounded=(math.floor(intended/tick+1e-8) if side>0 else math.ceil(intended/tick-1e-8))*tick
   assert abs(order['stop']-rounded)<1e-6
   tp=log['hi']+2*(log['hi']-log['lo']) if side>0 else log['lo']-2*(log['hi']-log['lo'])
   assert abs(order['target']-tp)<=tick*.51+1e-7
   due=local.replace(hour=15,minute=55,second=0,microsecond=0)
  if close>due+timedelta(minutes=1):late.append(dict(open=t['open_time'],close=t['close_time'],due=str(due)))
  if mode in (2,3) and not control and close<due:
   assert 'end of test' in t['exit_comment'].lower(),(folder.name,t)
   forced.append(t['number'])
 assert max(entries.values(),default=0)<=1
 assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit'])<.11
 result=dict(ok=True,trades_checked=len(trades),orders_checked=len(oo),sma_checks=len(sma),signal_checks=len(sigs),late_exits=late,
  max_initial_risk_pct=max(risks,default=None),max_notional_usd=max(notionals,default=None),min_notional_usd=min(notionals,default=None),
  realized_entry_target_rr_min=min(rr,default=None),realized_entry_target_rr_max=max(rr,default=None),
  conversion_approximation_exceptions=conversion,forced_end_exits=forced,report_sha=meta['report_sha'],net=old.shared.stats(trades,meta['start'],meta['end']))
 old.runner.save(folder/'AUDIT.json',result)
 return result
