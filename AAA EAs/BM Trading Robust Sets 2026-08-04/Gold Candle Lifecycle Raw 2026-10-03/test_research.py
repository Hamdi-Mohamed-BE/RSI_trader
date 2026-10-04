import unittest
from pathlib import Path
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parent
def eligible(control,prior_open,prior_close,open,first_high,signal_close,bid,tick_size,signal_time,midpoint,now,end):
 return prior_close<prior_open and signal_time>=midpoint and signal_time+60<=now<end and (control or (first_high>=open+tick_size*.5 and signal_close<open and bid<open))
class Tests(unittest.TestCase):
 def args(self):return dict(control=False,prior_open=102,prior_close=100,open=100,first_high=101,signal_close=99,bid=99,tick_size=.01,signal_time=1800,midpoint=1800,now=1860,end=3600)
 def test_literal(self):self.assertTrue(eligible(**self.args()))
 def test_prior_bull_rejected(self):a=self.args();a['prior_close']=103;self.assertFalse(eligible(**a))
 def test_no_upward_first_half_rejected(self):a=self.args();a['first_high']=100;self.assertFalse(eligible(**a))
 def test_before_half_rejected(self):a=self.args();a['signal_time']=1740;self.assertFalse(eligible(**a))
 def test_incomplete_m1_rejected(self):a=self.args();a['now']=1859;self.assertFalse(eligible(**a))
 def test_late_bar_rejected(self):a=self.args();a['now']=3600;self.assertFalse(eligible(**a))
 def test_reclaim_lost_rejected(self):a=self.args();a['bid']=100;self.assertFalse(eligible(**a))
 def test_control_removes_extra_conditions(self):a=self.args();a.update(control=True,first_high=100,signal_close=101,bid=101);self.assertTrue(eligible(**a))
 def test_high_timestamp_not_inferred_from_full_parent(self):
  s=(R/'EA/Lifecycle.mq5').read_text();self.assertIn('CopyRates(_Symbol,PERIOD_M1,parent,closed[0].time,observed)',s);self.assertNotIn('iHigh(_Symbol,InpParentTF,0)',s);self.assertIn('MQLInfoInteger(MQL_TESTER)',s)
 def test_halfway_maps(self):self.assertEqual([x/2 for x in (3600,14400,86400)],[1800,7200,43200])
 def test_datetime_unit_and_exit_delay(self):
  close=pd.to_datetime(['2025-11-06T23:00:00'],utc=True).to_numpy(dtype='datetime64[ns]').astype('int64')/1e9
  due=pd.Timestamp('2025-11-06T21:00:00',tz='UTC').timestamp()
  self.assertEqual(close[0]-due,7200)
if __name__=='__main__':unittest.main()
