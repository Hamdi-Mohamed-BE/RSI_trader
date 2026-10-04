import unittest
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
class Tests(unittest.TestCase):
 def test_dst(self):
  def sunday(y,m,n):
   d=datetime(y,m,1,tzinfo=timezone.utc);return 1+(6-d.weekday())%7+(n-1)*7
  t=datetime(2021,1,1,tzinfo=timezone.utc)
  while t<datetime(2027,1,1,tzinfo=timezone.utc):
   a=datetime(t.year,3,sunday(t.year,3,2),7,tzinfo=timezone.utc);b=datetime(t.year,11,sunday(t.year,11,1),6,tzinfo=timezone.utc)
   offset=-4 if a<=t<b else -5
   self.assertEqual(offset,t.astimezone(ZoneInfo('America/New_York')).utcoffset().total_seconds()/3600);t+=timedelta(hours=1)
 def test_weighted_sd(self):
  weight=mean=m2=0.;p=np.array([100,102,101,105,106.]);v=np.array([3,1,6,2,4.])
  for i,(x,w) in enumerate(zip(p,v)):
   delta=x-mean;weight+=w;mean+=w/weight*delta;m2+=w*delta*(x-mean)
   expected=np.average(p[:i+1],weights=v[:i+1]);sd=np.sqrt(np.average((p[:i+1]-expected)**2,weights=v[:i+1]))
   self.assertAlmostEqual(mean,expected);self.assertAlmostEqual(np.sqrt(m2/weight),sd)
 def test_execution_guard(self):
  s=(Path(__file__).parent/'EA/Main.mqh').read_text();self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',s)
  self.assertNotIn('MathMax(lo',s)
 def test_signal_reclaim(self):
  vwap=100;sd=2
  self.assertTrue(95<=vwap-2*sd and vwap-2*sd<98<vwap)
  self.assertFalse(95<=vwap-2*sd and vwap-2*sd<95.5<vwap)
if __name__=='__main__':unittest.main()
