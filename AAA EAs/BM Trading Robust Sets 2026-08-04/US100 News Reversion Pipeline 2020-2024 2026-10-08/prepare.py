"""Source-receipted scheduled event chronology; no price or P&L selection."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, re
import requests
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent;B=R.parent;NY=ZoneInfo('America/New_York')
def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def event(kind,local,source,receipt):
 utc=local.astimezone(timezone.utc)
 return dict(kind=kind,epoch=int(utc.timestamp()),release_utc=utc.isoformat(),release_ny=local.isoformat(),source=source,receipt=receipt)
def fed(date):
 url='https://www.federalreserve.gov/newsevents/pressreleases/monetary'+date+'a.htm'
 response=requests.get(url,timeout=40);response.raise_for_status()
 folder=R/'official-source-receipts';folder.mkdir(exist_ok=True)
 body=BeautifulSoup(response.text,'html.parser').get_text(' ',strip=True)
 assert 'Federal Reserve issues FOMC statement' in body,(url,'not FOMC statement')
 match=re.search(r'For release at (\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.)\s*(EST|EDT)',body)
 assert match,(url,'missing official time')
 hour=int(match[1])%12+(12 if match[3]=='p.m.' else 0)
 local=datetime.strptime(date,'%Y%m%d').replace(hour=hour,minute=int(match[2]),tzinfo=NY)
 assert local.tzname()==match[4] and hour==14,(url,'scheduled decision time')
 # Retain fetched public source, never credentials.
 (folder/(date+'.html')).write_text(response.text,encoding='utf-8')
 return event('FOMC',local,url,dict(release_time=match[0],fetched_utc=datetime.now(timezone.utc).isoformat(),response_sha256=hashlib.sha256(response.content).hexdigest()))
def main():
 sources=[B/'News Pulse Full Coverage 2026-09-12/OFFICIAL CALENDAR.json',B/'News Pulse Full Coverage 2026-09-12/bls-source-receipts.json',B/'News Fair Price Reversion Raw 2026-10-08/calendar.json']
 events={}
 for path in [sources[0],sources[2]]:
  for e in json.loads(path.read_text())['events']:
   events[(e['kind'],e['epoch'])]=event(e['kind'],datetime.fromtimestamp(e['epoch'],timezone.utc).astimezone(NY),e['source'],e['receipt'])
 for row in json.loads(sources[1].read_text()):
  m=re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})\s+(\d{2}:\d{2}\s+[AP]M)\s+(Employment Situation|Consumer Price Index) for',row['line'])
  assert m,row
  local=datetime.strptime(m[1]+' '+m[2],'%A, %B %d, %Y %I:%M %p').replace(tzinfo=NY)
  e=event('NFP' if m[3]=='Employment Situation' else 'CPI',local,row['source'],row['line']);events[(e['kind'],e['epoch'])]=e
 # Exact 2020 dates read from the official BLS annual schedule via web API.
 # These are not a first-Friday or weekday approximation.
 days={'NFP':['01-10','02-07','03-06','04-03','05-08','06-05','07-02','08-07','09-04','10-02','11-06','12-04'],
       'CPI':['01-14','02-13','03-11','04-10','05-12','06-10','07-14','08-12','09-11','10-13','11-12','12-10']}
 for kind, dates in days.items():
  for day in dates:
   local=datetime.fromisoformat('2020-'+day+'T08:30:00').replace(tzinfo=NY)
   e=event(kind,local,'https://www.bls.gov/schedule/2020/home.htm',dict(date=local.date().isoformat(),time_et='08:30 AM',release='Employment Situation' if kind=='NFP' else 'Consumer Price Index',access='Official web-tool schedule read 2026-10-08'))
   events[(kind,e['epoch'])]=e
 # 2020 March scheduled meeting was cancelled. Do not manufacture a March
 # 18 decision or use hindsight scheduling for emergency announcements.
 dates2020=['20200129','20200429','20200610','20200729','20200916','20201105','20201216']
 dates2021=['20210127','20210317','20210428','20210616','20210728','20210922','20211103','20211215']
 with ThreadPoolExecutor(max_workers=4) as pool:
  for e in pool.map(fed,dates2020+dates2021):events[(e['kind'],e['epoch'])]=e
 lower=int(datetime(2020,1,1,tzinfo=timezone.utc).timestamp());upper=int(datetime(2026,10,8,tzinfo=timezone.utc).timestamp())
 ordered=sorted([e for e in events.values() if lower<=e['epoch']<upper],key=lambda e:e['epoch'])
 assert len({e['epoch'] for e in ordered})==len(ordered),'Simultaneous duplicate event'
 counts={str(year):dict(Counter(e['kind'] for e in ordered if datetime.fromtimestamp(e['epoch'],timezone.utc).year==year)) for year in range(2020,2027)}
 for year in range(2020,2025):
  assert counts[str(year)]=={'NFP':12,'CPI':12,'FOMC':7 if year==2020 else 8},(year,counts[str(year)])
 for e in ordered:
  dt=datetime.fromisoformat(e['release_ny']);assert (dt.hour,dt.minute)==((14,0) if e['kind']=='FOMC' else (8,30))
 result=dict(events=ordered,counts_by_year=counts,source_files={str(p):sha(p) for p in sources},
  calendar_vintage_verified=False,macro_values_used=False,complete_scheduled_development_years_verified=True,
  excluded_unscheduled_2020_fed_dates=['2020-03-03','2020-03-15','2020-03-23'],
  excluded_source='https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm',
  note='Actual source-receipted scheduled chronology, not a point-in-time vintage calendar or market-consensus archive. Public MCP multi-year calendar returned history_truncated; earlier official receipts and sources used instead.')
 path=R/'calendar.json'
 if path.exists():
  previous=json.loads(path.read_text());assert [(x['kind'],x['epoch']) for x in previous['events']]==[(x['kind'],x['epoch']) for x in ordered],'Calendar altered'
 else:save(path,result)
 print(json.dumps(dict(events=len(ordered),counts_by_year=counts),indent=2),flush=True)
if __name__=='__main__':main()
