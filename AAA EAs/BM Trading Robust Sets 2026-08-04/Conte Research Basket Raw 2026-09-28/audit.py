"""Evidence audit: every native case, cash path, timing and untouched live terminal."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
from run import closed_races
import numpy as np
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cfg=read(ROOT/'run-config.json');build=read(ROOT/'BUILD.json');checks=[];errors=[];notes=[]
 def check(name,condition):
  checks.append(name)
  if not condition:errors.append(name)
 for p,h in build['hashes'].items():check('frozen '+p,sha(ROOT/p)==h)
 raw=read(ROOT/'RAW_RESULTS.json')
 for row in raw:
  tag=row['tag'];out=ROOT/'native'/tag;run=read(out/'run.json');ideas=read(out/'ideas.json')
  check(tag+' clean execution flags',all(v==0 for k,v in run['flags'].items() if k!='margin_call'))
  if run['flags']['margin_call']:
   check(tag+' stop-out is recorded economic failure',run['metrics']['net_profit']<0 and any(x['native_reason']==6 for x in ideas))
  journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
  check(tag+' verified closed races',closed_races(journal)==run.get('verified_already_closed_log_lines',0))
  check(tag+' build',run['build']==build)
  check(tag+' cash',abs(sum(x['net'] for x in ideas)-run['metrics']['net_profit'])<.02)
  data=np.load(out/'prop-ready.npz');g=data['groups'];e=data['events']
  check(tag+' ordered',len(g)<2 or np.all(g[1:,0]>=g[:-1,1]))
  check(tag+' no future entry',not len(g) or g[0,0]>=datetime.strptime(run['start'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
  check(tag+' no future exits',not len(g) or g[-1,1]<=datetime.strptime(run['end'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
  for x in g:
   final=e[int(x[4]+x[5]-1)]
   check(tag+f' flat {int(x[4])}',abs(final[1]-final[2])<1e-6 and abs(final[5]-final[6])<1e-6)
   if run['variant']['protected']:
    check(tag+f' positive risk {int(x[4])}',x[3]>0)
  check(tag+' net trade counts',len(g)==run['groups']==len(ideas))
  if run['variant']['mode'] in (0,4):
   old=ROOT/'audit-initial-build/native'/tag/'run.json'
   if old.exists():
    earlier=read(old)
    same_period=all(earlier[k]==run[k] for k in ('start','end','warmup_start'))
    if same_period:
     check(tag+' same ORB rules for parity',earlier['variant']==run['variant'])
     check(tag+' ORB parity after time amendment',abs(earlier['metrics']['net_profit']-run['metrics']['net_profit'])<.02 and earlier['groups']==run['groups'])
    else:
     check(tag+' changed period restricted to smoke',run['window']=='smoke')
     notes.append(tag+': no cross-build cash parity comparison; original smoke was '+earlier['start']+' to '+earlier['end']+', final winter-Friday regression is '+run['start']+' to '+run['end']+'.')
 for symbol in cfg['symbols']:
  for v in cfg['variants']:
   for model,window in [(4,'1y'),(4,'6m'),(1,'3y'),(1,'5y')]:
    folder=ROOT/'native'/f'{symbol}-{v["name"]}-{window}-m{model}'
    check(f'required {symbol} {v["name"]} {model} {window}',(folder/'run.json').exists() or (folder/'invalid.json').exists())
 for p in (ROOT/'native').glob('*/invalid.json'):
  bad=read(p);check(bad['tag']+' invalid excluded',not (p.parent/'run.json').exists())
  check(bad['tag']+' blocked build',bad['build']==build)
  check(bad['tag']+' documented data error',bad['window'] in ('3y','5y') and bad['flags']['market_closed']>0)
  check(bad['tag']+' no promoted invalid input',all(r['tag']!=bad['tag'] for r in raw))
 if (ROOT/'PROP_RESULTS.json').exists():
  manifest=read(ROOT/'PROP_MANIFEST.json')
  for path,expected in manifest['files'].items():check('prop hash '+path,sha(ROOT/path)==expected)
  for path in manifest['files']:
   if path.endswith('/prop-ready.npz'):
    source=read((ROOT/path).parent/'run.json');stats=read((ROOT/path).parent/'STATS.json')
    check('prop source not capital censored '+path,not stats['capital_limited'] and source['flags']['margin_call']==0)
  for x in read(ROOT/'PROP_RESULTS.json'):
   s=x['stats'];tag=x['variant']+x['profile']+x['cost']+x['kind']+str(x['days'])
   check(tag+' payout counts',s['first_request']['count']<=s['paths'])
   check(tag+' outcomes partition',abs(s['first_request']['pct']+s['any_failure_pct']-100*s['payout_then_failed']/s['paths']+s['no_request_no_failure_pct']-100)<1e-7)
   if x['profile'].startswith('FTMO'):
    check(tag+' stage ordering',s['first_request']['count']<=s['funded']['count']<=s['phase2']['count']<=s['phase1']['count'])
 result=dict(checks=len(checks),errors=errors,notes=notes,passed=not errors,source_hashes={p:sha(ROOT/p) for p in ['ConteBasket.mq5','run-config.json','RULES.md','prop_sim.py','analyze.py','run.py']})
 (ROOT/'AUDIT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2));assert not errors
if __name__=='__main__':main()
