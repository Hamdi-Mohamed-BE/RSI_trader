"""Tester-only, equivalent fixed-calendar search; no timer or trade changes."""
from bisect import bisect_right
from itertools import product
import json, random
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VERSION='immutable-utc-calendar-binary-search-v1'
OLD='''   int total=NP_GeneratedCalendarEventCount();
   for(int i=0;i<total;i++)
   {
      string candidate_kind=NP_GENERATED_EVENT_KINDS[i];
      if(!NP_TesterKindEnabled(candidate_kind)) continue;
      datetime candidate=AAA_ToServer((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]);
      if(candidate<=now || candidate>now+NP_LeadSeconds(candidate_kind)) continue;
      if(best==0 || candidate<best)
      {
         best=candidate;
         best_kind=candidate_kind;
      }
   }'''
NEW='''   // Tester-only acceleration of an immutable UTC schedule. Original
   // one-second timer, all callbacks, lifecycle and placement logic retained.
   if(InpTesterServerClockMode==0)
   {
      static bool cache_ready=false;
      static datetime cache_times[];
      static string cache_kinds[];
      static int cache_leads[];
      static int cache_count=0,cache_max_lead=0;
      if(!cache_ready)
      {
         int total=NP_GeneratedCalendarEventCount();
         ArrayResize(cache_times,total);ArrayResize(cache_kinds,total);ArrayResize(cache_leads,total);
         for(int i=0;i<total;i++)
         {
            string k=NP_GENERATED_EVENT_KINDS[i];
            if(!NP_TesterKindEnabled(k)) continue;
            datetime t=AAA_ToServer((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]);
            // The fixed chronology is asserted by the research runner.
            if(cache_count>0 && t<=cache_times[cache_count-1])
            {Print("NP_RESEARCH_BAD_CALENDAR_ORDER");ExpertRemove();return false;}
            cache_times[cache_count]=t;cache_kinds[cache_count]=k;
            cache_leads[cache_count]=NP_LeadSeconds(k);
            cache_max_lead=MathMax(cache_max_lead,cache_leads[cache_count]);cache_count++;
         }
         cache_ready=true;
      }
      int left=0,right=cache_count;
      while(left<right)
      {
         int middle=(left+right)/2;
         if(cache_times[middle]<=now) left=middle+1;else right=middle;
      }
      // A later event can have a longer lead: inspect all within max lead,
      // not merely the nearest release, to preserve the original predicate.
      for(int i=left;i<cache_count && cache_times[i]<=now+cache_max_lead;i++)
      {
         if(cache_times[i]>now+cache_leads[i]) continue;
         best=cache_times[i];best_kind=cache_kinds[i];break;
      }
   }
   else
   {
'''+OLD+'''
   }'''


def rewrite(body):
    body=body.replace('\r\n','\n')
    start=body.index('bool NP_FindTesterEvent(')
    finish=body.index('\nbool ',start+5)
    segment=body[start:finish]
    assert segment.count(OLD)==1,'Unexpected calendar search; refuse patch'
    return body[:start]+segment.replace(OLD,NEW,1)+body[finish:]


def proof():
    events=json.loads((ROOT/'Calendar.json').read_text())['events']
    assert all(a['epoch']<b['epoch'] for a,b in zip(events,events[1:]))
    kinds=['NFP','CPI','FOMC']; rng=random.Random(20261008);checks=0
    # Include every second around release/lead boundaries, random idle epochs,
    # all watch masks and deliberately overlapping/different lead windows.
    for lead_values in [(10,5,60),(60,60,60),(1,1,1),(172800,1,400000)]:
        leads=dict(zip(kinds,lead_values))
        times={e['epoch']+offset for e in events for offset in range(-65,3)}
        times|={e['epoch']-leads[e['kind']]+offset for e in events for offset in (-1,0,1)}
        times|={rng.randrange(events[0]['epoch']-86400,events[-1]['epoch']+86400) for _ in range(2000)}
        for mask in product([False,True],repeat=3):
            enabled={k for k,on in zip(kinds,mask) if on}
            candidates=[e for e in events if e['kind'] in enabled]; epochs=[e['epoch'] for e in candidates]
            max_lead=max((leads[e['kind']] for e in candidates),default=0)
            for now in times:
                old=next((e for e in candidates if now<e['epoch']<=now+leads[e['kind']]),None)
                fast=None
                for e in candidates[bisect_right(epochs,now):]:
                    if e['epoch']>now+max_lead:break
                    if e['epoch']<=now+leads[e['kind']]:fast=e;break
                assert old==fast,(now,mask,leads)
                checks+=1
    receipt=dict(version=VERSION,equivalent_search_checks=checks,timer_cadence_changed=False,
        callbacks_changed=False,trading_logic_changed=False,calendar_data_changed=False)
    (ROOT/'Calendar Search Proof.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':proof()
