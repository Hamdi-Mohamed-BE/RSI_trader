"""Native cash reconciliation and conditional prop path preparation; no trading API."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import csv,gzip,json,re,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
DT=np.dtype([('ms','<i8'),('group','<i4'),('bal','<f8'),('eq','<f8'),('low','<f8'),('highbal','<f8')])
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def csvread(p):return list(csv.DictReader(gzip.decompress(p.read_bytes()).decode('utf-8-sig').splitlines()))
def stats(values):
 v=np.asarray(values,float);ws=ls=mw=ml=0
 for x in v:
  if x>0:ws+=1;ls=0
  elif x<0:ls+=1;ws=0
  else:ws=ls=0
  mw=max(mw,ws);ml=max(ml,ls)
 loss=-v[v<0].sum()
 return dict(trades=len(v),net=float(v.sum()),win_rate=float(100*np.mean(v>0)) if len(v) else None,
  pf=float(v[v>0].sum()/loss) if loss>0 else None,max_win_streak=mw,max_loss_streak=ml)
def process(out):
 signature=hashlib.sha256(Path(__file__).read_bytes()+(out/'run.json').read_bytes()).hexdigest()
 if (out/'analysis-cache.json').exists() and (out/'prop-ready.npz').exists():
  cached=read(out/'analysis-cache.json')
  if cached.get('signature')==signature:return cached['result']
 run=read(out/'run.json');groups=csvread(out/'groups.csv.gz');deals=csvread(out/'deals.csv.gz')
 trace=np.frombuffer(gzip.decompress((out/'trace.bin.gz').read_bytes()),dtype=DT)
 assert len(trace)==0 or np.all(np.diff(trace['ms'])>=0)
 pos={};gmap={}
 for d in deals:
  if int(d['type']) not in (0,1):continue
  pos.setdefault(d['position'],[]).append(d)
  if int(d['entry'])==0:gmap[int(re.search(r'G(\d+)',d['comment'])[1])]=d['position']
 rows=[];evs=[];offset=0;cash=[];details=[];total_comm=total_swap=quickprofits=allprofits=0.
 old=read(ROOT.parent/'FTMO Fourteen EA Study 2026-09-27/prepared.json');news=np.array(sorted({x['epoch'] for x in old['placements']}))
 for g in groups:
  gid=int(g['group']);ds=pos[gmap[gid]];ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry']) in (1,3)]
  assert len(ins)==1 and len(outs)==1,'No partials in frozen study'
  vol=float(ins[0]['volume']);assert abs(float(outs[0]['volume'])-vol)<1e-7
  op=float(ins[0]['time_msc'])/1000;cl=float(outs[0]['time_msc'])/1000
  net=sum(sum(float(d[k]) for k in ['profit','commission','swap','fee']) for d in ds)
  comm=sum(float(d['commission'])+float(d['fee']) for d in ds);swap=sum(float(d['swap']) for d in ds)
  assert abs(net-float(g['net']))<1e-5,(gid,net,g)
  a,z=np.searchsorted(trace['group'],[gid,gid],side='left')[0],np.searchsorted(trace['group'],gid,side='right')
  tt=trace[a:z];assert len(tt)>0 and abs(tt[-1]['bal']-net)<1e-5 and abs(tt[-1]['eq']-net)<1e-5
  adjusted=np.maximum(tt['ms'],int(ins[0]['time_msc']))
  mask=np.isclose(tt['bal'],net,atol=1e-6,rtol=0)&(tt['ms']>=int(outs[0]['time_msc'])-151)
  adjusted[mask]=np.maximum(adjusted[mask],int(outs[0]['time_msc']));adjusted=np.maximum.accumulate(adjusted)
  assert adjusted[-1]>=int(outs[0]['time_msc'])
  price=float(g['fill']);addfee=max(0.,.7+comm/vol)
  rb=tt['bal']/vol-addfee;flo=(tt['eq']-tt['bal'])/vol;lo=(tt['low']-tt['bal'])/vol
  # Source financing remains included. Extra 2bps/day financing is a hypothetical stress, not a measured prop rate.
  elapsed=(adjusted/1000-op)/86400;overnight=run['variant']['mode']==2
  extra_finance=price*.0002*elapsed if overnight else np.zeros(len(tt))
  entrycomm=(float(ins[0]['commission'])+float(ins[0]['fee']))/vol
  gross=tt['bal']/vol-entrycomm;ss=lambda x:np.where(x>=0,.9*x,1.1*x)
  sb=ss(gross)+entrycomm-addfee-price*.0001-extra_finance
  arr=np.column_stack([adjusted/1000-op,rb,tt['eq']/vol-addfee,tt['low']/vol-addfee,tt['highbal']/vol-addfee,
   sb,sb+ss(flo),sb+ss(lo),np.maximum(sb,np.r_[sb[0],sb[:-1]]),np.zeros((len(tt),4))])
  near=bool(np.min(np.abs(news-op))<=300 or np.min(np.abs(news-cl))<=300)
  profit=max(0.,net/vol-addfee);isquick=cl-op<=30
  closed=arr[:,0]>=cl-op
  arr[closed,9]=profit;arr[closed,10]=profit if isquick else 0
  arr[closed,11]=profit*.6 if near else 0
  arr[closed,12]=max(0.,float(sb[-1]))*(.6 if near else .1)
  close=max(cl,float(adjusted[-1])/1000);risk=float(g['risk'])/vol
  if run['variant']['protected']:assert risk>0
  rows.append([op,close,price,risk,offset,len(arr),net/vol,int(g['setup']),int(g['side']),vol])
  evs.append(arr);offset+=len(arr);cash.append(net);total_comm+=comm;total_swap+=swap
  allprofits+=profit*vol;quickprofits+=profit*vol if isquick else 0
  ny=datetime.fromtimestamp(op,timezone.utc).astimezone(ZoneInfo('America/New_York'));minute=ny.hour*60+ny.minute;mode=run['variant']['mode']
  assert ((mode==0 and 605<=minute<930) or (mode in (1,5) and 571<=minute<959) or (mode==2 and 930<=minute<=959) or (mode==3 and minute==570) or (mode==4 and minute==600)),(ny,mode)
  details.append(dict(group=gid,open=op,close=cl,net=net,risk=float(g['risk']),commission=comm,swap=swap,
   side=int(g['side']),volume=vol,fill=price,sl=float(g['sl']),tp=float(g['target']),
   native_reason=int(outs[0]['reason']),comment=outs[0]['comment'],timestamp_correction_ms=int(np.max(adjusted-tt['ms']))))
 st=stats(cash);days=(datetime.strptime(run['end'],'%Y.%m.%d')-datetime.strptime(run['start'],'%Y.%m.%d')).days
 weekdays=int(np.busday_count(run['start'].replace('.','-'),run['end'].replace('.','-')))
 st.update(return_pct=sum(cash)/100,per_month=len(cash)/(days/365.25*12),per_weekday=len(cash)/weekdays,
  equity_dd_pct=run['metrics']['equity_dd_pct'],commission=total_comm,swap=total_swap,
  quick_profit_pct=100*quickprofits/allprofits if allprofits else 0,
  median_hold_minutes=float(np.median([(x['close']-x['open'])/60 for x in details])) if details else None,
  max_cash_error=abs(sum(cash)-run['metrics']['net_profit']),tick_quality=run['metrics']['history_quality'])
 journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
 spreads=np.array([float(b)-float(a) for a,b in re.findall(r'\((\d+\.\d+) / (\d+\.\d+)\)',journal)])
 # Duplicated terminal/agent samples, NOT all ticks or an unbiased spread estimate.
 st['logged_quote_spread']=dict(samples=len(spreads),zero_pct=float(100*np.mean(np.abs(spreads)<1e-8)) if len(spreads) else None,
  median_points=float(np.median(spreads)) if len(spreads) else None,max_points=float(np.max(spreads)) if len(spreads) else None)
 skips=[int(x) for line in run['summaries'] for x in re.findall(r'skips=(\d+)',line)]
 st['native_skipped_signals']=max(skips,default=0)
 st['minimum_closed_balance']=min([10000.]+[float(g['base'])+float(g['net']) for g in groups])
 st['capital_limited']=bool(st['native_skipped_signals']>0 and st['minimum_closed_balance']<=100)
 st['last_closed_utc']=datetime.fromtimestamp(details[-1]['close'],timezone.utc).isoformat() if details else None
 assert st['max_cash_error']<.02
 save(out/'STATS.json',st);save(out/'ideas.json',details)
 np.savez_compressed(out/'prop-ready.npz',groups=np.array(rows,dtype=float).reshape((-1,10)),events=np.concatenate(evs) if evs else np.empty((0,13)))
 result=dict(tag=out.name,symbol=run['symbol'],variant=run['variant']['name'],protected=run['variant']['protected'],model=run['model'],start=run['start'],end=run['end'],window=run['window'],stats=st,tick_coverage=run['tick_coverage'],spec=run['spec'],flags=run['flags'])
 save(out/'analysis-cache.json',dict(signature=signature,result=result))
 return result
def main():
 rows=[]
 for p in sorted((ROOT/'native').glob('*/run.json')):
  row=process(p.parent);rows.append(row);print(row['tag'],json.dumps(row['stats']),flush=True)
 save(ROOT/'RAW_RESULTS.json',rows)
if __name__=='__main__':main()
