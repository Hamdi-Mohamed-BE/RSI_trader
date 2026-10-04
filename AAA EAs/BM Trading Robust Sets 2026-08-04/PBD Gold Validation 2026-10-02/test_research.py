import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from rules import classify,profile,signal,context

class Rules(unittest.TestCase):
 def test_classification(self):
  self.assertEqual(classify(.8,.7,.5),1);self.assertEqual(classify(.2,.3,-.5),-1)
  self.assertEqual(classify(.5,.5,0),0);self.assertEqual(classify(.8,.7,-.5),9)
 def test_profile_conservation(self):
  # One full-range bar plus a concentrated flat-price cluster, no invented trade volume.
  f=pd.DataFrame(dict(open=[10.]*60,high=[20.]+[18.]*59,low=[0.]+[18.]*59,close=[10.]+[18.]*59,tick_volume=[64.]+[100.]*59))
  p=profile(f);self.assertEqual(p['volume'],5964);self.assertTrue(p['val']<=18<=p['vah']);self.assertEqual(p['shape'],1)
 def test_reclaim_and_mirror(self):
  p=dict(val=10,vah=20,poc=17,shape=1)
  r=dict(open=10,close=12,high=13,low=9,tick_volume=100)
  self.assertEqual(signal(r,12,p,1,100,1),1)
  p['shape']=-1;self.assertEqual(signal(r,12,p,1,100,1),0)
  self.assertEqual(signal(r,12,p,1,100,2),1)
 def test_conviction(self):
  p=dict(val=10,vah=20,poc=17,shape=1)
  r=dict(open=20,close=21,high=21.5,low=19.5,tick_volume=150)
  self.assertEqual(signal(r,19,p,1,100,3),1)
  r['tick_volume']=149;self.assertEqual(signal(r,19,p,1,100,3),0)
  r['tick_volume']=150;self.assertEqual(signal(r,21,p,1,100,3),0)
 def test_prior_context_excludes_signal(self):
  f=pd.DataFrame(dict(open=np.ones(22),high=np.ones(22)*2,low=np.zeros(22),close=np.ones(22),tick_volume=np.ones(22)*100))
  a,v=context(f);f.loc[21,['high','tick_volume']]=1e8
  self.assertEqual(context(f),(a,v))
 def test_live_guard_and_causal_source(self):
  s=(Path(__file__).parent/'EA/Head.mqh').read_text()
  self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',s)
  self.assertIn('start,end-1,r',s);self.assertIn('r[21].time+300!=bar',s)
  self.assertIn('minute>=930',s);self.assertIn('MathFloor',s)

if __name__=='__main__':unittest.main()
