"""Applies the PRE-FROZEN descriptive screen; never promotes or mutates production."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
def choose(results):
 out=[]
 for key in ('trend','ema3','asia','london','rsi'):
  rows=[x for x in results if x['ea']==key];base=next(x for x in rows if x['variant']=='BASE');s=base['stats'];eligible=[];assessment=[]
  for x in rows:
   if x['variant']=='BASE':continue
   t=x['stats'];fail=[]
   if t['trades']<30:fail.append('fewer than 30 trades')
   if t['trades']<.5*s['trades']:fail.append('retains less than half the baseline trade count')
   if t['pf'] is None or t['pf']<1.2:fail.append('PF below 1.20')
   if t['pf'] is None or s['pf'] is None or t['pf']<s['pf']+.05:fail.append('PF improvement below 0.05')
   if t['net']<=0:fail.append('non-positive net')
   if t['return_pct']<s['return_pct']:fail.append('return below baseline')
   if t['equity_dd_pct']>s['equity_dd_pct']:fail.append('equity DD worse than baseline')
   if not fail:eligible.append(x)
   assessment.append(dict(variant=x['variant'],fails=fail))
  selected=max(eligible,key=lambda x:(x['stats']['pf'],x['stats']['return_pct'])) if eligible else base
  strongest=max((x for x in rows if x['variant']!='BASE'),key=lambda x:(x['stats']['pf'] or -1,x['stats']['return_pct']))
  out.append(dict(ea=key,label=base['label'],baseline=base['tag'],selected=selected['tag'],selected_variant=selected['variant'],passes_descriptive_screen=bool(eligible),highest_filtered_pf=strongest['tag'],assessment=assessment,promotion='NOT APPROVED: same-year search and partial real-tick coverage'))
 return out
if __name__=='__main__':
 results=json.loads((R/'SUMMARY.json').read_text());out=choose(results);(R/'DECISION.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
