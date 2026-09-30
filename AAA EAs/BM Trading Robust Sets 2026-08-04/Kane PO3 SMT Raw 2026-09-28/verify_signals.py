"""Independent review of every recorded native decision and one-way BE adjustment."""
import csv,gzip,json,math
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
NY=ZoneInfo('America/New_York')
def rows(p):return list(csv.DictReader(gzip.decompress(p.read_bytes()).decode('utf-8-sig').splitlines()))
def audit_case(path):
 r=json.loads((path/'run.json').read_text());mode=r['variant']['mode'];g=rows(path/'groups.csv.gz');signals=rows(path/'signals.csv.gz');be=rows(path/'management.csv.gz')
 assert len(g)==len(signals)
 perday={};smap={};checks=0
 for raw in signals:
  x={k:float(v) for k,v in raw.items()};side=x['side'];gid=int(x['group']);smap[gid]=x
  now=datetime.fromtimestamp(x['now'],NY);key=now.date();perday[key]=perday.get(key,0)+1
  assert now.weekday()<5 and 600<=now.hour*60+now.minute<690
  assert x['gap_time']<=x['end']-180 and x['end']<=x['now']<x['end']+180
  assert x['hour_start']<=x['end']-180
  h4=datetime.fromtimestamp(x['h4_start'],NY);assert h4.hour==10 and h4.minute==0
  assert x['aligned_bars']>=20 and x['gap_hi']>x['gap_lo']
  assert (side<0 and x['close']<x['gap_lo']) or (side>0 and x['close']>x['gap_hi'])
  assert abs(x['eq']-(max(x['nh'],x['ch'])+min(x['nl'],x['cl']))/2)<1e-7
  if mode:
   if side<0:
    assert (x['ch']>=x['nh']+.01-1e-8)!=(x['csh']>=x['sh']+.01-1e-8)
    assert x['c4h']>=x['n4h']+.01-1e-8 or x['cs4h']>=x['s4h']+.01-1e-8
    assert x['close']>max(x['day_eq'],x['h4_eq'])
   else:
    assert (x['cl']<=x['nl']-.01+1e-8)!=(x['csl']<=x['sl']-.01+1e-8)
    assert x['c4l']<=x['n4l']-.01+1e-8 or x['cs4l']<=x['s4l']-.01+1e-8
    assert x['close']<min(x['day_eq'],x['h4_eq'])
  else:
   assert (side<0 and x['ch']>=x['nh']+.01-1e-8) or (side>0 and x['cl']<=x['nl']-.01+1e-8)
  checks+=12
 assert max(perday.values(),default=0)<=2
 seen=set()
 for raw in be:
  x={k:float(v) for k,v in raw.items()};gid=int(x['group']);side=smap[gid]['side'];assert gid not in seen;seen.add(gid)
  assert mode>=2 and x['time']>=smap[gid]['now']
  assert side*(x['new_sl']-x['old_sl'])>0 and side*(x['new_sl']-x['fill'])>0
  assert side*(x['price']-x['new_sl'])>0
  if mode==3:assert side*(x['price']-x['fill'])>=abs(x['fill']-x['initial_sl'])-1e-7
  checks+=6
 summary=r['summaries'][0] if r['summaries'] else ''
 return dict(signals=len(signals),be_moves=len(be),checks=checks,summary=summary)

