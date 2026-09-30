"""Independent clock, order geometry, cash and timing checks on native evidence."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from collections import Counter,defaultdict
import gzip,json,re,hashlib,importlib.util,math
import run as runner
from app.mt5_evidence_jobs import _read_report,_clean,_number
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('net_statistics',ROOT.parent/'Gold NY30 Value Area VWAP Raw 2026-09-27/audit.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
NY=ZoneInfo('America/New_York')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def stamp(s):return datetime.fromisoformat(s.replace('.','-',2).replace(' ','T')).replace(tzinfo=timezone.utc)
def clock(t,mode):return t.astimezone(NY).replace(tzinfo=None)+(timedelta(hours=7) if mode!=4 else timedelta())
def filled_orders(report):
 out=[];s=report;begin=s.lower().find('<b>orders</b>');end=s.lower().find('<b>deals</b>')
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',s[begin:end],re.I|re.S):
  c=[_clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
  if len(c)<11 or c[9]!='filled' or not c[10].startswith('Ideas '):continue
  out.append(dict(placed=stamp(c[0]),filled=stamp(c[8]),side='Long' if c[3].startswith('buy') else 'Short',stop=_number(c[6]) or 0,target=_number(c[7]) or 0,entry=_number(c[5]),ticket=int(c[1])))
 return out
def audit(folder):
 meta=load(folder/'run.json');trades=sorted(load(folder/'trades.json'),key=lambda x:x['close_time']);mode=meta['case']['mode'];control=meta['case']['control']
 raw=gzip.decompress((folder/'report.htm.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==meta['report_sha']
 report=raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
 oo=filled_orders(report);assert len(oo)==len(trades),(folder.name,len(oo),len(trades))
 journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
 order_pat=r'IDEA_ORDER t=([\d.]+ [\d:]+) mode=(\d+) control=(\d+) side=(-?\d+) pending=(\d+) entry=([\d.]+) sl=([\d.]+) tp=([\d.]+) lot=([\d.]+) risk=([\d.]+) eq=([\d.]+) high=([\d.]+) low=([\d.]+) due=([\d.]+ [\d:]+) order=(\d+)'
 logs={}
 for v in re.findall(order_pat,journal):
  at,md,ct,side,pending,entry,sl,tp,lot,risk,eq,hi,lo,due,tid=v
  logs[int(tid)]=dict(time=stamp(at),side=int(side),pending=int(pending),entry=float(entry),stop=float(sl),target=float(tp),lot=float(lot),risk=float(risk),eq=float(eq),hi=float(hi),lo=float(lo))
 sigs={stamp(t):dict(bar=stamp(b),close=float(cl),atr=float(atr),side=int(sd)) for t,b,cl,atr,sd in re.findall(r'IDEA_SIGNAL now=([\d.]+ [\d:]+) bar=([\d.]+ [\d:]+) close=([\d.]+) atr=([\d.]+) side=(-?\d+)',journal)}
 sma={}
 for day,mean,vals in re.findall(r'IDEA_SMA date=(\d+) mean=([\d.]+) closes=([^\r\n]+)',journal):
  pairs=[v.split(':') for v in vals.rstrip(',').split(',')];assert len(pairs)==25 and len({p[0] for p in pairs})==25
  assert all(int(p[0])<int(day) for p in pairs);assert abs(sum(float(p[1]) for p in pairs)/25-float(mean))<1e-5
  sma[int(day)]=float(mean)
 filters={int(day):(float(bid),float(mean),int(passed)) for day,bid,mean,passed in re.findall(r'IDEA_FILTER date=(\d+) bid=([\d.]+) sma=([\d.]+) pass=(\d+)',journal)}
 tick=float(re.search(r'IDEA_SPEC[^\r\n]* tick=([\d.]+)',journal)[1]);contract=float(re.search(r'IDEA_SPEC[^\r\n]*contract=([\d.]+)',journal)[1])
 entries=Counter();late=[];risks=[];notionals=[];rr=[]
 for t in trades:
  op=stamp(t['open_time']);cl=stamp(t['close_time']);local=clock(op,mode);close=clock(cl,mode);side=1 if t['side']=='Long' else -1
  matches=[o for o in oo if o['filled']==op and o['side']==t['side']];assert len(matches)==1,(folder.name,t,matches)
  order=matches[0];log=logs[order['ticket']];assert abs(t['volume']-log['lot'])<1e-7
  entries[local.date()]+=1;assert 0<=local.weekday()<=4
  assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.021
  expected=side*(t['close_price']-t['open_price'])*t['volume']*contract/(t['close_price'] if t['symbol']=='USDJPY' else 1)
  assert abs(expected-t['gross_profit'])<max(.03,abs(expected)*.002)
  if mode in (1,4):
   assert order['stop']>0 and side*(t['open_price']-order['stop'])>0
   exposure=abs(t['open_price']-order['stop'])*t['volume']*contract/(order['stop'] if t['symbol']=='USDJPY' else 1)
   risks.append(100*exposure/log['eq'])
   if order['target']:rr.append(side*(order['target']-t['open_price'])/abs(t['open_price']-order['stop']))
  else:
   assert order['stop']==order['target']==0
   notionals.append(t['open_price']*contract*t['volume']);assert notionals[-1]<=10000*1.001
  if mode==1:
   placed=clock(order['placed'],mode);assert placed.hour==6 and placed.minute==0
   assert 360<=local.hour*60+local.minute<1080
   assert abs(order['stop']-(log['lo'] if side>0 else log['hi']))<=tick+.000001
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
  if mode in (2,3) and not control:assert close>=due,(folder.name,'premature no-stop exit',t)
 assert max(entries.values(),default=0)<=1,(folder.name,'multiple same-day fills',dict(entries))
 assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit'])<.11
 result=dict(ok=True,trades_checked=len(trades),orders_checked=len(oo),sma_checks=len(sma),signal_checks=len(sigs),late_exits=late,
  max_initial_risk_pct=max(risks,default=None),max_notional_usd=max(notionals,default=None),min_notional_usd=min(notionals,default=None),
  realized_entry_target_rr_min=min(rr,default=None),realized_entry_target_rr_max=max(rr,default=None),
  report_sha=meta['report_sha'],net=shared.stats(trades,meta['start'],meta['end']))
 runner.save(folder/'AUDIT.json',result);return result
def main():
 count=0
 for folder in (ROOT/'native').iterdir():
  if (folder/'run.json').exists():
   a=audit(folder);print(folder.name,a['trades_checked'],'checked; late exits',len(a['late_exits']),flush=True);count+=1
 runner.save(ROOT/'AUDIT_SUMMARY.json',dict(ok=True,cases=count))
if __name__=='__main__':main()
