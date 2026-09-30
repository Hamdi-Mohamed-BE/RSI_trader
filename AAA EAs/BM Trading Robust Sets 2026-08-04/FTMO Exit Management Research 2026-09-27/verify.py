"""Research integrity checks, source identity and account-adapter edge cases."""
from pathlib import Path
import hashlib,json,sys
import analyze as a
ROOT=Path(__file__).resolve().parent
def main():
 results={}
 for source,info in a.CFG['source_files'].items():
  assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==info['sha256'],source
 results['production_source_hashes_unchanged']=len(a.CFG['source_files'])
 original=a.c.read(a.c.SOURCE/'prepared.json')
 results['inherited_tests']=a.six.checks(original)
 rows=[]
 base=original['rows'][a.c.RAW][0]
 for i in range(6):
  op=a.c.START+i*a.c.DAY+12*3600
  rows.append(dict(base,op=op,cl=op+3600,unit_risk=1000.,unit_gross=225/.07+7,unit_comm=-7.,unit_swap=0.,news=False))
 normal=a.protection_engine(False)['replay']([dict(r) for r in rows],[],a.c.START,a.c.START+14*a.c.DAY,detail=True)
 protect=a.protection_engine(True)['replay']([dict(r) for r in rows],[],a.c.START,a.c.START+14*a.c.DAY,detail=True)
 assert normal['log'][4]['initial_risk']==70
 assert protect['log'][4]['initial_risk']==30
 assert len(normal['passes'])==1 and len(protect['passes'])==1
 assert normal['passes'][0]['time']<protect['passes'][0]['time']
 for guard in (False,True):
  rr=a.protection_engine(guard)['replay']([dict(r) for r in rows],[],a.c.START,a.c.START+14*a.c.DAY,detail=True,challenge=False)
  assert all(t['initial_risk']==70 for t in rr['log'])
 results['target_protection_checks']=7
 helper=(ROOT/'ExitManagement.mqh').read_text()
 assert 'if(!MQLInfoInteger(MQL_TESTER))return false;' in helper
 assert 'CopyBuffer(em_atr,0,1,1,atr)' in helper
 assert 'CopyRates(_Symbol,PERIOD_M15,1,1,closed)' in helper
 assert 'if(side*(candidate-sl)<_Point' in helper
 assert 'start+86400-1' in helper
 results['research_safety_and_causality_static_checks']=5
 complete=[]
 for n,e in a.CFG['eas'].items():
  for v in e['variants']:
   done=ROOT/'native'/(n+'-'+v)/'run.json'
   if done.exists():
    rr,pp,m=a.load_case(n,v);complete.append(m['case'])
    assert '0 errors, 0 warnings' in a.read(ROOT/(n+'.build.json'))['compile_tail']
    assert m['binary_sha256']==hashlib.sha256((ROOT/(n+'.ex5')).read_bytes()).hexdigest()
 results['native_cases_validated']=complete
 if (ROOT/'RESULTS.json').exists():
  data=a.read(ROOT/'RESULTS.json')
  for case in data['cases']:
   a.six.reconcile(case['historical'],True)
   for h in case['summary']['horizons']:
    assert sum(h['counts'].values())==1000
    assert h['first_payout_received']<=h['funded']<=h['both_phases_passed']<=h['phase1_passed']
   assert len(case['paths'])==1000
  results['reconciled_portfolio_cases']=len(data['cases'])
 a.save(ROOT/'CHECKS.json',results);print(json.dumps(results,indent=2))
if __name__=='__main__':main()
