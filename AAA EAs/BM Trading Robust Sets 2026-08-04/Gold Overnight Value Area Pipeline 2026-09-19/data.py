"""Connected-account read-only history and causal overnight feature cache."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timedelta,time,timezone
from zoneinfo import ZoneInfo
import numpy as np
import MetaTrader5 as mt
ROOT=Path(__file__).resolve().parent;PACKAGE=ROOT.parent
RAW=PACKAGE/'Overnight Profile Raw Comparison 2026-09-19'
NORMAL='C:/Program Files/MetaTrader 5/terminal64.exe';NY=ZoneInfo('America/New_York')
START=datetime(2021,9,18,tzinfo=timezone.utc);END=datetime(2026,9,19,tzinfo=timezone.utc)
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fetch():
 assert mt.initialize(NORMAL),mt.last_error()
 a=mt.account_info();assert a and mt.terminal_info().connected
 assert a.server.startswith('Exness-'),'Broker clock requires review'
 choices=[s for s in mt.symbols_get() if s.name in ('XAUUSD','GOLD') and s.trade_mode==4];assert len(choices)==1
 s=choices[0];fields=['name','description','path','point','trade_tick_size','trade_tick_value','trade_contract_size','volume_min','volume_step','volume_max','trade_stops_level','swap_long','swap_short','swap_mode']
 meta=dict(captured_utc=datetime.now(timezone.utc).isoformat(),account={k:getattr(a,k) for k in ('login','server','company','currency','leverage','trade_mode','balance','equity')},symbol=s.name,contract={k:getattr(s,k) for k in fields},server_utc_offset=0,protocol_sha256=sha(ROOT/'PROTOCOL.md'))
 assert s.trade_contract_size==100 and s.point==.001
 folder=ROOT/'data';folder.mkdir(exist_ok=True)
 for label,tf in [('M1',mt.TIMEFRAME_M1),('M5',mt.TIMEFRAME_M5)]:
  cached=folder/(label+'.npz')
  if cached.exists():continue
  chunks=[];cursor=START
  while cursor<END:
   finish=min(END,cursor+timedelta(days=90))
   # Repeat request after priming to avoid a stale terminal-tail response.
   mt.copy_rates_range(s.name,tf,cursor,finish)
   b=mt.copy_rates_range(s.name,tf,cursor,finish)
   assert b is not None and len(b)>100,(label,cursor,mt.last_error())
   chunks.append(b);print('HISTORY',label,cursor.date(),len(b),flush=True);cursor=finish
  b=np.concatenate(chunks);_,ix=np.unique(b['time'],return_index=True);b=b[np.sort(ix)];b=b[(b['time']>=START.timestamp())&(b['time']<END.timestamp())]
  assert np.all(np.diff(b['time'])>0) and b['time'][-1]>=END.timestamp()-86400
  assert np.all(b['high']>=np.maximum(b['open'],b['close'])) and np.all(b['low']<=np.minimum(b['open'],b['close']))
  np.savez_compressed(cached,rates=b)
 mt.shutdown()
 meta['files']={n:sha(folder/(n+'.npz')) for n in ('M1','M5')}
 save(ROOT/'manifest.json',meta)
 audit={}
 for name in ('M1','M5'):
  b=np.load(folder/(name+'.npz'))['rates'];dates=np.array([datetime.fromtimestamp(int(t),timezone.utc).strftime('%Y-%m') for t in b['time'][::1]])
  keys,counts=np.unique(dates,return_counts=True)
  audit[name]=dict(rows=len(b),first=datetime.fromtimestamp(int(b['time'][0]),timezone.utc).isoformat(),last=datetime.fromtimestamp(int(b['time'][-1]),timezone.utc).isoformat(),monthly_bars=dict(zip(keys,counts.tolist())),max_gap_minutes=int(np.diff(b['time']).max()/60),zero_volume=int(sum(b['tick_volume']==0)),negative_spread=int(sum(b['spread']<0)),sha256=meta['files'][name])
 save(ROOT/'data-audit.json',audit)
 print('DATA READY',flush=True)
def load():
 return tuple(np.load(ROOT/'data'/(x+'.npz'))['rates'] for x in ('M1','M5'))
def round_tick(x):return np.floor(x/.001+.5)*.001
def features(bins,percent):
 path=ROOT/'data'/f'features-{bins}-{percent}.npz'
 if path.exists():return np.load(path)['days']
 m1,m5=load();rows=[];day=datetime(2021,9,19).date();last=END.date()
 while day<last:
  if day.weekday()<5:
   opening=int(datetime.combine(day,time(9,30),NY).timestamp());start=int(datetime.combine(day-timedelta(days=1),time(18),NY).timestamp())
   a,z=np.searchsorted(m1['time'],[start,opening]);r=m1[a:z]
   if len(r)>=120:
    low=float(r['low'].min());high=float(r['high'].max());width=(high-low)/bins
    if width>0:
     ix=np.clip(np.floor(((r['high']+r['low']+r['close'])/3-low)/width).astype(int),0,bins-1)
     volume=np.bincount(ix,weights=r['tick_volume'],minlength=bins);p=int(volume.argmax());left=right=p;covered=volume[p]
     while covered<volume.sum()*percent/100 and (left>0 or right<bins-1):
      below=volume[left-1] if left else -1;above=volume[right+1] if right<bins-1 else -1
      if above>=below and right<bins-1:right+=1;covered+=volume[right]
      else:left-=1;covered+=volume[left]
     midnight=int(datetime.combine(day,time(),NY).timestamp())
     begin,end=np.searchsorted(m5['time'],[opening,midnight+16*3600])
     rows.append([midnight,opening,high,low,round_tick(low+left*width),round_tick(low+(right+1)*width),round_tick(low+(p+.5)*width),begin,end])
  day+=timedelta(days=1)
 days=np.array(rows,dtype=float);np.savez_compressed(path,days=days);return days
if __name__=='__main__':fetch()
