import json,hashlib,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
SOURCE=PACKAGE/'AAA Final EAs'/'AAA Final News Pulse EA'/'AAA Final News Pulse EA.mq5'
START,END='2025-09-19','2026-09-19'
old=json.loads((PACKAGE/'News Pulse Full Coverage 2026-09-12'/'OFFICIAL CALENDAR.json').read_text())
events={(r['epoch'],r['kind']):r for r in old['events'] if START<=r['release_utc'][:10]<END}
receipts=json.loads((ROOT/'fxmacro-receipts.json').read_text())
for indicator,kind in [('inflation','CPI'),('non_farm_payrolls','NFP'),('policy_rate','FOMC')]:
 for r in receipts[indicator]['result']['data']:
  key=(r['announcement_datetime'],kind)
  if key not in events:events[key]=dict(kind=kind,epoch=key[0],release_utc=r['announcement_datetime_utc'],source=r['source_url'],receipt=r,calendar_vintage_verified=False)
events=sorted(events.values(),key=lambda r:r['epoch'])
(ROOT/'calendar.json').write_text(json.dumps(events,indent=2))
epochs=','.join(str(r['epoch']) for r in events);kinds=','.join(json.dumps(r['kind']) for r in events)
header=f'''#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20250919
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20260919
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS {len(events)}
long NP_GENERATED_EVENT_UTC_EPOCHS[]={{{epochs}}};
string NP_GENERATED_EVENT_KINDS[]={{{kinds}}};
string NP_GeneratedCalendarProvider() {{return "Saved official BLS/Fed receipts + FXMacroData official-calendar extension";}}
string NP_GeneratedCalendarHash() {{return "{hashlib.sha256(epochs.encode()).hexdigest()}";}}
string NP_GeneratedCalendarFetchedAt() {{return "2026-09-19";}}
int NP_GeneratedCalendarEventCount() {{return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}}
'''
(ROOT/'Calendar.mqh').write_text(header)
code=SOURCE.read_text(encoding='utf-8-sig')
for name in ('AAA_Final_Common.mqh','SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh'):
 code=code.replace('#include "'+name+'"','#include "..\\AAA Final EAs\\AAA Final News Pulse EA\\'+name+'"')
code=code.replace('"NewsPulseTesterCalendar.mqh"','"Calendar.mqh"').replace('"..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh"','"..\\_Shared\\CalyxAdaptivePortfolio.mqh"')
(ROOT/'Base.mqh').write_text(code,encoding='utf-8')
manifest={'start':START,'end_exclusive':END,'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'counts':{k:sum(e['kind']==k for e in events) for k in ('NFP','CPI','FOMC')},'scope':'Research-only. Event families, not separate hindsight settings for individual release dates. Both pending sides stay enabled. No production changes.'}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest)
