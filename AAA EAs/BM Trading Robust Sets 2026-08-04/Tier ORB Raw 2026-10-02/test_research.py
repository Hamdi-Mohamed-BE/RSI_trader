import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np
from report import streaks, wilson, metrics

def mql_ny(utc):
 y=utc.year
 def nth_sunday(m,n):
  first=datetime(y,m,1,tzinfo=timezone.utc)
  return 1+(6-first.weekday())%7+(n-1)*7
 a=datetime(y,3,nth_sunday(3,2),7,tzinfo=timezone.utc)
 b=datetime(y,11,nth_sunday(11,1),6,tzinfo=timezone.utc)
 return utc+timedelta(hours=-4 if a<=utc<b else -5)
class ResearchTests(unittest.TestCase):
 def test_dst_formula_against_zoneinfo_all_transitions(self):
  for y in range(2021,2027):
   first=datetime(y,1,1,tzinfo=timezone.utc)
   for h in range(0,24*366,1):
    t=first+timedelta(hours=h)
    self.assertEqual(mql_ny(t).replace(tzinfo=None),t.astimezone(ZoneInfo('America/New_York')).replace(tzinfo=None))
 def test_streaks_flat_resets(self):
  s=streaks(np.array([1,1,0,1,-1,-2,-1,1]))
  self.assertEqual(s['max_win'],2);self.assertEqual(s['max_loss'],3)
 def test_wilson_known(self):
  a,b=wilson(50,100)
  self.assertAlmostEqual(a,40.383,places=2);self.assertAlmostEqual(b,59.617,places=2)
 def test_balance_pf_costs(self):
  t=[dict(number=1,net_profit=100,total_costs=-1,open_time='2026-09-01T14:00:00',close_time='2026-09-01T15:00:00'),dict(number=2,net_profit=-50,total_costs=-1,open_time='2026-09-02T14:00:00',close_time='2026-09-02T15:00:00')]
  m,b,d,_=metrics(t,datetime(2026,9,1),datetime(2026,9,3))
  self.assertEqual(m['net'],50);self.assertEqual(m['pf'],2);self.assertEqual(m['win_rate_pct'],50);self.assertEqual(m['carryover_positions'],0)
  self.assertAlmostEqual(d.max(),50/10100*100)
if __name__=='__main__':unittest.main()
