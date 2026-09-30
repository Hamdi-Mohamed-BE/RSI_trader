"""Reconcile native partial deals and export per-idea floating-equity paths."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import csv,gzip,json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
DT=np.dtype([('ms','<i8'),('group','<i4'),('bal','<f8'),('eq','<f8'),('low','<f8'),('highbal','<f8')])
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def csvread(p):return list(csv.DictReader(gzip.decompress(p.read_bytes()).decode('utf-8-sig').splitlines()))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def stats(values):
 v=np.asarray(values,float);win=v[v>0];loss=v[v<0];ws=ls=mw=ml=0
 for x in v:
  if x>0:ws+=1;ls=0
  elif x<0:ls+=1;ws=0
  else:ws=ls=0
  mw=max(mw,ws);ml=max(ml,ls)
 return dict(ideas=len(v),net=float(v.sum()),win_rate=100*len(win)/len(v) if len(v) else None,pf=float(win.sum()/-loss.sum()) if len(loss) else None,max_win_streak=mw,max_loss_streak=ml)
def process(out):
 run=read(out/'run.json');groups=csvread(out/'groups.csv.gz');deals=csvread(out/'deals.csv.gz')
 trace=np.frombuffer(gzip.decompress((out/'trace.bin.gz').read_bytes()),dtype=DT)
 assert len(trace)==0 or np.all(np.diff(trace['ms'])>=0)
 pos={};gmap={}
 for d in deals:
  if int(d['type']) not in (0,1):continue
  pos.setdefault(d['position'],[]).append(d)
  if int(d['entry'])==0:gmap[int(re.search(r'G(\d+)',d['comment'])[1])]=d['position']
 rows=[];evs=[];offset=0;cash=[];quickp=0.;allp=0.;wholequick=0.;wholeprofits=0.;counts={};details=[]
 old=read(ROOT.parent/'FTMO Fourteen EA Study 2026-09-27/prepared.json');news=np.array(sorted({x['epoch'] for x in old['placements']}))
 for g in groups:
  gid=int(g['group']);ds=pos[gmap[gid]];ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry']) in (1,3)]
  assert len(ins)==1 and outs
  op=float(ins[0]['time_msc'])/1000;cl=max(float(d['time_msc']) for d in outs)/1000
  vol=float(ins[0]['volume']);assert abs(sum(float(d['volume']) for d in outs)-vol)<1e-7
  # Source account charges commission at entry; otherwise trace decomposition must be extended.
  assert all(abs(float(d['commission']))+abs(float(d['fee']))+abs(float(d['swap']))<1e-8 for d in outs)
  commission=float(ins[0]['commission'])+float(ins[0]['fee']);net=commission+sum(float(d['profit']) for d in outs)
  assert abs(net-float(g['net']))<1e-5
  tt=trace[trace['group']==gid];assert len(tt)>0 and abs(tt[-1]['bal']-net)<1e-5
  assert abs(tt[-1]['eq']-net)<1e-5,'Group must finish flat'
  # Synchronous native fills advance the account but SymbolInfoTick can still
  # carry the triggering quote's timestamp (up to the configured 150ms delay).
  # Align a post-fill cash state to its audited deal timestamp, never backdate it.
  adjusted=tt['ms'].copy();ledger=commission
  adjusted=np.maximum(adjusted,int(ins[0]['time_msc']))
  for d in sorted(outs,key=lambda z:int(z['time_msc'])):
   ledger+=float(d['profit']);ms=int(d['time_msc'])
   mask=np.isclose(tt['bal'],ledger,atol=1e-6,rtol=0)&(tt['ms']>=ms-151)&(adjusted<ms)
   adjusted[mask]=ms
  adjusted=np.maximum.accumulate(adjusted)
  assert adjusted[-1]>=max(int(d['time_msc']) for d in outs)
  source_comm=-commission/vol;addfee=max(0.,.7-source_comm)
  gross=tt['bal']/vol-commission/vol;delta=np.diff(np.r_[0,gross]);stressgross=np.cumsum(np.maximum(delta,0)*.9+np.minimum(delta,0)*1.1)
  rb=tt['bal']/vol-addfee;flo=(tt['eq']-tt['bal'])/vol;lo=(tt['low']-tt['bal'])/vol
  sb=stressgross+commission/vol-addfee-2.0
  ss=lambda v:np.where(v>=0,.9*v,1.1*v)
  arr=np.column_stack([adjusted/1000-op,rb,tt['eq']/vol-addfee,tt['low']/vol-addfee,tt['highbal']/vol-addfee,
     sb,sb+ss(flo),sb+ss(lo),np.maximum(sb,np.r_[sb[0],sb[:-1]]),np.zeros((len(tt),4))])
  win=quick=nd=sd=0.;events=[]
  for d in sorted(outs,key=lambda z:int(z['time_msc'])):
   time=float(d['time_msc'])/1000;frac=float(d['volume'])/vol;grosspart=float(d['profit'])/vol
   profit=grosspart+(commission/vol-addfee)*frac
   positive=max(0.,profit);isquick=time-op<=30
   near=bool(np.min(np.abs(news-op))<=300 or np.min(np.abs(news-time))<=300)
   stressprofit=grosspart*(.9 if grosspart>=0 else 1.1)+(commission/vol-addfee-2)*frac
   win+=positive;quick+=positive if isquick else 0.;nd+=positive*.6 if near else 0.
   sd+=max(0.,stressprofit)*(.6 if near else .1)
   events.append([time-op,win,quick,nd,sd]);quickp+=positive*vol if isquick else 0.;allp+=positive*vol
  ee=np.array(events);idx=np.searchsorted(ee[:,0],arr[:,0],side='right')-1;valid=idx>=0
  arr[valid,9:13]=ee[idx[valid],1:5]
  native_close=cl;cl=max(cl,float(adjusted[-1])/1000)
  risk=float(g['risk'])/vol;assert risk>0
  rows.append([op,cl,float(g['fill']),risk,offset,len(arr),net/vol,int(g['setup']),int(g['side']),vol])
  evs.append(arr);offset+=len(arr);cash.append(net);counts[g['setup']]=counts.get(g['setup'],0)+1
  if net>0:wholeprofits+=net;wholequick+=net if native_close-op<=30 else 0
  details.append(dict(group=gid,open=op,close=native_close,net=net,risk=float(g['risk']),setup=int(g['setup']),quick_partial_profit_pct=100*quick/win if win else 0,
   trace_timestamps_adjusted=int(np.sum(adjusted!=tt['ms'])),maximum_timestamp_correction_ms=int(np.max(adjusted-tt['ms']))))
  ny=datetime.fromtimestamp(op,timezone.utc).astimezone(ZoneInfo('America/New_York'));minute=ny.hour*60+ny.minute
  assert 570<=minute<690 or 810<=minute<930,(ny,'entry session')
 st=stats(cash);days=(datetime.strptime(run['end'],'%Y.%m.%d')-datetime.strptime(run['start'],'%Y.%m.%d')).days
 weekdays=int(np.busday_count(run['start'].replace('.','-'),run['end'].replace('.','-')))
 st.update(return_pct=sum(cash)/100,per_month=len(cash)/(days/365.25*12),per_weekday=len(cash)/weekdays,per_week=len(cash)/(days/7),
  equity_dd_pct=run['metrics']['equity_dd_pct'],native_exit_deals=run['metrics']['trades'],setups=counts,
  quick_partial_profit_pct=100*quickp/allp if allp else 0,quick_whole_idea_profit_pct=100*wholequick/wholeprofits if wholeprofits else 0,
  median_hold_seconds=float(np.median([x['close']-x['open'] for x in details])) if details else None,
  max_cash_error=abs(sum(cash)-run['metrics']['net_profit']),tick_quality=run['metrics']['history_quality'])
 save(out/'IDEA_STATS.json',st);save(out/'ideas.json',details)
 np.savez_compressed(out/'prop-ready.npz',groups=np.array(rows,dtype=float).reshape((-1,10)),events=np.concatenate(evs) if evs else np.empty((0,13)))
 return dict(tag=out.name,variant=run['variant']['name'],model=run['model'],start=run['start'],end=run['end'],window=run['window'],stats=st,tick_coverage=run['tick_coverage'])
def main():
 rows=[]
 for p in sorted((ROOT/'native').glob('*/run.json')):rows.append(process(p.parent))
 save(ROOT/'RAW_RESULTS.json',rows)
 for row in rows:print(row['tag'],json.dumps(row['stats']),flush=True)
if __name__=='__main__':main()
