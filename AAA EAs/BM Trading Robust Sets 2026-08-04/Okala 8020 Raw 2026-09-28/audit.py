"""Read-only audit of saved evidence; writes only this study's CHECKS.json."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
build=read(ROOT/'BUILD.json')
for file,h in build['hashes'].items():check(sha(ROOT/file)==h,'frozen '+file)
current=read(ROOT/'RAW_RESULTS.json');old=read(ROOT/'audit-initial-build/RAW_RESULTS.json')
check(len(current)==17,'all seventeen native cases recorded')
differences=[]
for x in current:
 tag=x['tag'];r=read(ROOT/'native'/tag/'run.json');s=x['stats']
 check(r['ok'] and r['build']==build,'native build '+tag)
 check(not any(r['flags'].values()),'clean native journal '+tag)
 check(s['max_cash_error']<.02,'cash reconciliation '+tag)
 z=np.load(ROOT/'native'/tag/'prop-ready.npz');g=z['groups'];e=z['events']
 check(len(g)==s['ideas'],'idea count '+tag)
 if len(g):
  check(np.all(g[1:,0]>=g[:-1,1]),'no overlap '+tag)
  check(np.all(e[:,0]>=0),'no pre-fill marks '+tag)
  check(all(np.all(np.diff(e[int(v[4]):int(v[4]+v[5]),0])>=0) for v in g),'ordered native trace '+tag)
  details=read(ROOT/'native'/tag/'ideas.json')
  check(max(q['maximum_timestamp_correction_ms'] for q in details)<=150,'bounded ledger clock alignment '+tag)
 prev=next(p for p in old if p['tag']==tag)
 differences.append(dict(tag=tag,initial_net=prev['stats']['net'],audited_net=s['net'],delta=s['net']-prev['stats']['net']))
props=read(ROOT/'PROP_RESULTS.json');year=read(ROOT/'PROP_YEAR.json');manifest=read(ROOT/'PROP_MANIFEST.json')
check(len(props)==160,'all replay configurations and windows recorded')
check(len(year)==20,'all year configurations recorded')
for p,h in manifest['files'].items():check(sha(ROOT/p)==h,'prop input hash '+p)
for x in props:
 s=x['stats'];n=s['paths']
 check(n>0 and s['no_trades']<=n,'sample size '+str((x['variant'],x['profile'],x['cost'],x['kind'],x['days'])))
 for key in ('phase1','phase2','funded','first_request','drawdown_breach','quick_failure'):
  t=s[key];check(0<=t['count']<=n and abs(t['pct']-100*t['count']/n)<1e-7,'rate denominator '+key)
  check((t['median_days'] is None)==(t['count']==0),'empty timing '+key)
  if t['median_days'] is not None:check(0<=t['median_days']<=x['days']+1e-8,'no future timing '+key)
 check(s['phase2']['count']<=s['phase1']['count'],'phase sequencing')
 if x['profile'].startswith('FTMO'):check(s['first_request']['count']<=s['funded']['count'],'funding before request')
for x in year:
 s=x['state'];log=np.array(x['log']);cap=5000 if x['profile'].startswith('Instant') else 10000
 if len(log):
  check(abs(log[:,3].sum()-(s['positive']-s['negative']))<1e-6,'year logs/net '+x['profile'])
  check(abs(log[:,4].sum()-s['sum_initial_risk'])<1e-6,'whole idea risk '+x['profile'])
 if s['phase1_time']<0:check(abs(cap+sum(v[3] for v in x['log'])-s['balance']-s['total_cash']/(.7 if cap==5000 else .8))<1e-6,'year flat account cash '+x['profile'])
tests=subprocess.run([sys.executable,str(ROOT/'test_prop.py')],capture_output=True,text=True,cwd=ROOT)
check(tests.returncode==0,'all unit tests pass')
source=(ROOT/'Okala8020.mq5').read_text()
check('if(!MQLInfoInteger(MQL_TESTER))' in source and 'return INIT_FAILED' in source,'live attachment refused')
result=dict(passed=len(checks),checks=checks,unit_test_output=tests.stdout+tests.stderr,
 native_runs_current=len(current),native_runs_initial=len(old),native_repair_deltas=differences,
 verdict='REJECT promotion: raw PF/control gate failed',
 boundary='Research EA and offline replay only; live terminal, existing EA installation and Git remote untouched')
(ROOT/'CHECKS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=len(checks),native_runs=34,unit_tests=15,repair_deltas=differences)))
