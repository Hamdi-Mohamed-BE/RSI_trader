"""Freeze raw assumptions and actual official event timestamps, without tuning."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import hashlib,json,re
from urllib.request import urlopen,Request
from urllib.error import URLError,HTTPError
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent;B=R.parent
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cfg=json.loads((R/'config.json').read_text());source=B/'News Pulse Event Parameters Research 2026-09-19/calendar.json'
 cached=json.loads(source.read_text());receipts=json.loads((R/'provider-receipts.json').read_text())
 extension=receipts['calendar_extension']['result']['data']
 events={e['epoch']:e for e in cached}
 for e in extension:
  assert e['release_date_confirmed'] and e['time_announced']
  stamp=e['announcement_datetime'];events[stamp]=dict(kind='NFP',epoch=stamp,release_utc=e['announcement_datetime_utc'],source=e['source_url'],receipt=e)
 low=int(datetime.fromisoformat(cfg['start']).replace(tzinfo=timezone.utc).timestamp());high=int(datetime.fromisoformat(cfg['end_exclusive']).replace(tzinfo=timezone.utc).timestamp())
 events=sorted([e for e in events.values() if low<=e['epoch']<high],key=lambda e:e['epoch'])
 assert dict(Counter(e['kind'] for e in events))=={'CPI':11,'NFP':12,'FOMC':8}
 for e in events:
  dt=datetime.fromtimestamp(e['epoch'],timezone.utc)
  from zoneinfo import ZoneInfo
  ny=dt.astimezone(ZoneInfo('America/New_York'))
  assert (ny.hour,ny.minute)==((14,0) if e['kind']=='FOMC' else (8,30))
  e['release_utc']=dt.isoformat();e['release_ny']=ny.isoformat()
 # Current official schedules are an ex-post chronology cross-check, NOT a
 # vintage-confirmed calendar or a forecast/consensus surprise classifier.
 checks=[]
 for year in [2025,2026]:
  url=f'https://www.bls.gov/schedule/{year}/home.htm'
  try:
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:body=response.read().decode('utf-8')
   text=BeautifulSoup(body,'html.parser').get_text(' ',strip=True)
   (R/f'bls-{year}-current.html').write_text(body,encoding='utf-8')
   for e in events:
    dt=datetime.fromisoformat(e['release_ny'])
    if dt.year!=year or e['kind']=='FOMC':continue
    title='Consumer Price Index' if e['kind']=='CPI' else 'Employment Situation'
    date=rf'{dt.strftime("%A")},\s*{dt.strftime("%B")}\s*0?{dt.day},\s*{year}\s*08:30\s*AM\s*{title}'
    assert re.search(date,text,re.I),(e['release_ny'],title,'Official schedule disagreement')
   checks.append(dict(url=url,status='Exact dates/times matched',current_schedule_not_historical_vintage=True))
  except (URLError,HTTPError,TimeoutError) as exc:
   checks.append(dict(url=url,status='HTTP access unavailable; browser research and cached official receipts used',error=str(exc)))
 save(R/'calendar.json',dict(events=events,counts=dict(Counter(e['kind'] for e in events)),cached_source=str(source),cached_source_sha256=sha(source),official_schedule_checks=checks,
  value_inputs_used=False,calendar_vintage_verified=False,coverage='31 actual CPI/NFP/FOMC releases, not every high-impact USD announcement; current schedules / saved official receipts.'))
 freeze=dict(created_utc=datetime.now(timezone.utc).isoformat(),config_sha256=sha(R/'config.json'),engine_sha256=sha(R/'engine.mq5'),build_sha256=sha(R/'build_engine.py'),calendar_sha256=sha(R/'calendar.json'),
  cases=[{'allow_longs':0},{'allow_longs':1}],optimisation=False,research_only=True,live_changes=False)
 path=R/'FROZEN.json'
 if path.exists():
  old=json.loads(path.read_text());assert all(old[k]==v for k,v in freeze.items() if k!='created_utc'),'Frozen inputs changed'
 else:save(path,freeze)
 print(json.dumps(dict(frozen=True,events=len(events),counts=dict(Counter(e['kind'] for e in events)),checks=checks)),flush=True)
if __name__=='__main__':main()
