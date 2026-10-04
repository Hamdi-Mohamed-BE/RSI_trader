import unittest
from pathlib import Path
from selection import choose
R=Path(__file__).resolve().parent
def allow(mode,level,di,direction,valid,adx,plus,minus):
 if not mode and not di:return True
 return valid and (mode!=1 or adx>=level) and (mode!=2 or adx<=level) and (not di or (plus>minus if direction>0 else minus>plus))
class Tests(unittest.TestCase):
 def test_off_missing(self):self.assertTrue(allow(0,20,False,1,False,0,0,0))
 def test_enabled_missing(self):self.assertFalse(allow(1,20,False,1,False,25,30,20))
 def test_floor_inclusive(self):self.assertTrue(allow(1,20,False,1,True,20,30,20));self.assertFalse(allow(1,20,False,1,True,19.999,30,20))
 def test_ceiling_inclusive(self):self.assertTrue(allow(2,25,False,1,True,25,30,20));self.assertFalse(allow(2,25,False,1,True,25.001,30,20))
 def test_di_directions(self):self.assertTrue(allow(0,20,True,1,True,10,30,20));self.assertTrue(allow(0,20,True,-1,True,10,20,30))
 def test_di_tie(self):self.assertFalse(allow(0,20,True,1,True,20,20,20))
 def test_conjunction(self):self.assertFalse(allow(1,20,True,1,True,30,10,20));self.assertFalse(allow(1,20,True,1,True,19,30,20));self.assertTrue(allow(1,20,True,1,True,25,30,20))
 def test_mql_closed_buffers(self):
  source=(R/'EA/StudyFilter.mqh').read_text();self.assertIn('bar+seconds<=TimeCurrent()',source)
  for b in (0,1,2):self.assertIn(f'CopyBuffer(study_adx,{b},1,1,',source)
  self.assertIn('if(!MQLInfoInteger(MQL_TESTER))',source)
 def test_frozen_minimum_and_baseline_fallback(self):
  results=[]
  for key in ('trend','ema3','asia','london','rsi'):
   for v,n,pf in [('BASE',38,1.24),('DI_ONLY',29,1.42),('ADX20',30,1.30)]:
    results.append(dict(ea=key,label=key,tag=key+'-'+v,variant=v,stats=dict(trades=n,pf=pf,net=500,return_pct=5,equity_dd_pct=4)))
  picked=choose(results);self.assertTrue(all(x['selected_variant']=='ADX20' for x in picked))
  results=[x for x in results if x['variant']!='ADX20'];picked=choose(results);self.assertTrue(all(x['selected_variant']=='BASE' for x in picked))
 def test_bootstrap_small_sample_refused(self):
  from uncertainty import bootstrap
  import numpy as np
  self.assertFalse(bootstrap(np.array([30.,20.,-25.,40.]))['eligible'])
if __name__=='__main__':unittest.main()
