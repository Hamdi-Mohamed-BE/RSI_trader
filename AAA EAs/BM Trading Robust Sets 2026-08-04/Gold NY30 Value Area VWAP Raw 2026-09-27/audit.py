"""Independent closed-bar/profile/entry audit; net-of-cost statistics."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from collections import Counter
import gzip,json,re,math,sys,itertools,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent;NY=ZoneInfo("America/New_York")
def load(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding="utf-8")
def dt(s):return datetime.fromisoformat(s.replace(".","-",2)).replace(tzinfo=timezone.utc)
def stats(trades,start,end):
 vals=[t["net_profit"] for t in trades];wins=[v for v in vals if v>0];losses=[v for v in vals if v<0]
 seq=[(k,len(list(g))) for k,g in itertools.groupby(1 if v>0 else -1 if v<0 else 0 for v in vals)]
 w=[n for s,n in seq if s==1];l=[n for s,n in seq if s==-1]
 bal=10000.;peak=bal;dd=0;monthly={}
 for t in trades:
  bal+=t["net_profit"];peak=max(peak,bal);dd=max(dd,(peak-bal)/peak*100)
  m=t["close_time"][:7];z=monthly.setdefault(m,{"trades":0,"net_usd":0,"wins":0})
  z["trades"]+=1;z["net_usd"]+=t["net_profit"];z["wins"]+=int(t["net_profit"]>0)
 for z in monthly.values():z["net_usd"]=round(z["net_usd"],2);z["win_rate_pct"]=100*z["wins"]/z["trades"]
 a=dt(start);b=dt(end);days=(b-a).days;weekdays=int(np.busday_count(a.date(),b.date()))
 gp=sum(wins);gl=-sum(losses)
 return dict(trades=len(vals),net_usd=round(sum(vals),2),return_pct=sum(vals)/100,
  win_rate_pct=100*len(wins)/len(vals) if vals else 0,profit_factor=gp/gl if gl else None,
  trades_per_month=len(vals)/(days/30.4375),trades_per_weekday=len(vals)/weekdays if weekdays else 0,
  max_win_streak=max(w,default=0),max_loss_streak=max(l,default=0),avg_win_streak=sum(w)/len(w) if w else 0,
  avg_loss_streak=sum(l)/len(l) if l else 0,balance_dd_pct=dd,commission=sum(t["commission"] for t in trades),
  swap=sum(t["swap"] for t in trades),monthly=monthly)
def audit(folder):
 meta=load(folder/"run.json");trades=load(folder/"trades.json")
 journal=gzip.decompress((folder/"journal.txt.gz").read_bytes()).decode()
 bars=pd.read_csv(folder/"bars.csv.gz");profiles=pd.read_csv(folder/"profiles.csv.gz")
 bars["dt"]=pd.to_datetime(bars.time,format="%Y.%m.%d %H:%M:%S",utc=True)
 local=bars.dt.dt.tz_convert(NY);bars["day"]=local.dt.strftime("%Y%m%d").astype(int)
 bars["minute"]=local.dt.hour*60+local.dt.minute
 assert not bars.dt.duplicated().any()
 assert ((bars.minute>=570)&(bars.minute<955)).all()
 tick=float(re.search(r"NY30_SPEC[^\r\n]*tick_size=([\d.]+)",journal)[1])
 contract=float(re.search(r"NY30_SPEC[^\r\n]*contract=([\d.]+)",journal)[1])
 sigs={}
 for line in dict.fromkeys(re.findall(r"NY30_SIGNAL\|[^\r\n]+",journal)):
  z=line.split("|");sig=dict(now=dt(z[1]),bar=dt(z[2]),engine=int(z[3]),side=int(z[4]),entry=float(z[5]),stop=float(z[6]),tp=float(z[7]),lot=float(z[8]),risk=float(z[9]),equity=float(z[10]),vwap=float(z[11]),upper=float(z[12]),lower=float(z[13]))
  assert sig["bar"] not in sigs;sigs[sig["bar"]]=sig
 used=set();checked=0;profilechecks=0
 for key,g in bars.groupby("day",sort=False):
  op=g[g.minute<600];ref=profiles[profiles.day==key];expected=None
  if len(op)==30 and list(op.minute)==list(range(570,600)):
   hi=op.high.max();lo=op.low.min();width=(hi-lo)/64
   bins=np.zeros(64);p=(op.high+op.low+op.close)/3
   indices=np.clip(np.floor((p-lo)/width).astype(int),0,63)
   np.add.at(bins,indices,op.tick_volume)
   i=int(np.argmax(bins));left=right=i;covered=bins[i]
   while covered<.7*bins.sum() and (left>0 or right<63):
    below=bins[left-1] if left>0 else -1;above=bins[right+1] if right<63 else -1
    if above>=below and right<63:right+=1;covered+=bins[right]
    else:left-=1;covered+=bins[left]
   expected=(hi,lo,lo+(i+.5)*width,lo+(right+1)*width,lo+left*width,float(bins.sum()))
   assert len(ref)==1,(folder.name,key,len(ref))
   assert np.allclose(ref[["or_high","or_low","poc","vah","val","volume"]].iloc[0].astype(float),expected,rtol=0,atol=1e-6)
   known=dt(ref.iloc[0].known_at)
   assert known==op.dt.iloc[-1].to_pydatetime()+pd.Timedelta(minutes=1)
   profilechecks+=1
  else:assert not len(ref),(folder.name,key,"unexpected profile")
  v=g.tick_volume.to_numpy(float);p=((g.high+g.low+g.close)/3).to_numpy(float)
  sw=np.cumsum(v);mean=np.cumsum(v*p)/sw;sd=np.sqrt(np.maximum(0,np.cumsum(v*p*p)/sw-mean*mean))
  assert np.allclose(g.vwap,mean,rtol=0,atol=1e-6)
  assert np.allclose(g.upper,mean+sd,rtol=0,atol=2e-5)
  assert np.allclose(g.lower,mean-sd,rtol=0,atol=2e-5)
  if expected is None:continue
  hi,lo,poc,vah,val,total=expected;xu=xd=au=ad=None;xh=xl=0.;prev=None
  for b in g.itertuples(index=False):
   t=b.dt.to_pydatetime()
   if b.minute<600:prev=b;continue
   if xu and (t-xu).total_seconds()>900:xu=None
   if xd and (t-xd).total_seconds()>900:xd=None
   if au and ((t-au).total_seconds()>600 or b.close<b.vwap):au=None
   if ad and ((t-ad).total_seconds()>600 or b.close>b.vwap):ad=None
   if xu:xh=max(xh,b.high)
   if xd:xl=min(xl,b.low)
   inside=val<b.close<vah;candidates={}
   if xu and t>xu and inside and b.vwap<b.close<b.upper:candidates[(1,-1)]=xh
   if xd and t>xd and inside and b.lower<b.close<b.vwap:candidates[(1,1)]=xl
   if au and t>au and b.low<=b.upper and b.close>max(b.upper,vah) and b.close>b.open:candidates[(2,1)]=b.low
   if ad and t>ad and b.high>=b.lower and b.close<min(b.lower,val) and b.close<b.open:candidates[(2,-1)]=b.high
   if b.close>hi and prev.close<=hi:candidates[(0,1)]=b.low
   if b.close<lo and prev.close>=lo:candidates[(0,-1)]=b.high
   if t in sigs:
    s=sigs[t];eng=s["engine"];side=s["side"];ident=(eng,side)
    assert ident in candidates,(folder.name,t,s,candidates)
    assert meta["inputs"]["InpMode"]=="0" if eng==0 else int(meta["inputs"]["InpMode"])&eng
    assert t+pd.Timedelta(minutes=1)<=s["now"]<=t+pd.Timedelta(minutes=2)
    n=s["now"].astimezone(NY);assert 600<=n.hour*60+n.minute<930
    expectedstop=candidates[ident]-side*tick
    rounded=(math.floor(expectedstop/tick+1e-8) if side>0 else math.ceil(expectedstop/tick-1e-8))*tick
    assert abs(s["stop"]-rounded)<tick*.01+1e-7
    assert abs(s["tp"]-(s["entry"]+side*3*side*(s["entry"]-s["stop"])))<=tick*.51+1e-7
    assert abs(s["risk"]-abs(s["entry"]-s["stop"])*s["lot"]*contract)<.01
    # OrderCalcProfit rounds account-currency amounts to cents.
    assert s["risk"]>=s["equity"]*.01-.011
    assert np.allclose([s["vwap"],s["upper"],s["lower"]],[b.vwap,b.upper,b.lower],rtol=0,atol=1e-6)
    daily=(key,eng if eng else 10+side);assert daily not in used,(folder.name,daily)
    used.add(daily);checked+=1
   if xu is None and b.high>hi:xu=t;xh=b.high
   if xd is None and b.low<lo:xd=t;xl=b.low
   if au is None and b.close>max(vah,b.upper) and prev.close<=max(vah,prev.upper):au=t
   if ad is None and b.close<min(val,b.lower) and prev.close>=min(val,prev.lower):ad=t
   prev=b
 assert checked==len(sigs),(folder.name,checked,len(sigs))
 byday=Counter();prevexit=None;entryrisk=[];entryslip=[]
 for tr in trades:
  opened=dt(tr["open_time"]);closed=dt(tr["close_time"])
  assert opened<=closed and (prevexit is None or opened>=prevexit),(folder.name,tr,"overlap")
  prevexit=closed;byday[opened.astimezone(NY).date().isoformat()]+=1
  near=[s for s in sigs.values() if 0<=(opened-s["now"]).total_seconds()<=5 and s["side"]==(1 if tr["side"]=="Long" else -1)]
  assert len(near)==1,(folder.name,tr,near);s=near[0]
  assert abs(s["lot"]-tr["volume"])<1e-6
  assert abs((tr["close_price"]-tr["open_price"])*s["side"]*contract*tr["volume"]-tr["gross_profit"])<.011,(folder.name,tr)
  entryrisk.append(abs(tr["open_price"]-s["stop"])*contract*tr["volume"]/s["equity"]*100)
  entryslip.append((tr["open_price"]-s["entry"])*s["side"])
 assert max(byday.values(),default=0)<=2
 bechecks=0;betrades=set()
 for line in dict.fromkeys(re.findall(r"NY30_BE\|[^\r\n]+",journal)):
  z=line.split("|");when=dt(z[1]);entry,be,level,quote=map(float,z[3:])
  active=[tr for tr in trades if dt(tr["open_time"])<=when<=dt(tr["close_time"]) and tr["entry_comment"]=="NY30 R"]
  assert len(active)==1,(folder.name,line,active)
  side=1 if active[0]["side"]=="Long" else -1
  assert abs(entry-active[0]["open_price"])<1e-6 and abs(be-entry)<=tick*.51+1e-7
  assert side*(level-entry)>0 and side*(quote-level)>=-1e-7
  recent=bars[(bars.dt+pd.Timedelta(minutes=1)<=when)&(bars.dt+pd.Timedelta(minutes=3)>=when)]
  assert len(recent) and min(abs(recent.vwap-level))<1e-6
  betrades.add(active[0]["number"])
  bechecks+=1
 st=stats(trades,meta["start"],meta["end"])
 assert abs(st["net_usd"]-meta["metrics"]["net_profit"])<.11
 result=dict(ok=True,case=folder.name,profile_checks=profilechecks,bar_indicator_checks=len(bars),signal_checks=checked,trade_checks=len(trades),breakeven_checks=bechecks,
  volume_type="M1 broker tick volume",bars_with_real_volume=int((bars.real_volume>0).sum()),sessions=len(bars.day.unique()),
  max_actual_initial_risk_pct=max(entryrisk,default=0),median_actual_initial_risk_pct=float(np.median(entryrisk)) if entryrisk else 0,
  entry_delay_slippage_price_median=float(np.median(entryslip)) if entryslip else 0,
  entry_delay_slippage_price_p95=float(np.quantile(entryslip,.95)) if entryslip else 0,
  trades_moved_to_be=len(betrades),be_moved_trades_net_usd=round(sum(t["net_profit"] for t in trades if t["number"] in betrades),2),
  be_moved_trades_net_losses=sum(t["net_profit"]<0 for t in trades if t["number"] in betrades),
  native_win_rate_pct=meta["metrics"]["win_rate_pct"],net_stats=st,
  source_sha256=meta["source_sha256"],report_sha256=meta["report_sha256"])
 save(folder/"AUDIT.json",result)
 print(folder.name,"PASS",len(trades),"trades",round(st["win_rate_pct"],2),"net WR",flush=True)
 return result
if __name__=="__main__":
 targets=[ROOT/"native"/sys.argv[1]] if len(sys.argv)>1 and sys.argv[1] not in ("all","pending") else sorted(p.parent for p in (ROOT/"native").glob("*/run.json"))
 if len(sys.argv)>1 and sys.argv[1]=="pending":targets=[p for p in targets if not (p/"AUDIT.json").exists()]
 for folder in targets:audit(folder)
