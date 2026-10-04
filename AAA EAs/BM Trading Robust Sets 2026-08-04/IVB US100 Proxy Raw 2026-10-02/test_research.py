import unittest
from pathlib import Path
import numpy as np
class Tests(unittest.TestCase):
 def test_equal_quotes_zero(self):
  diff=np.diff([100,101,101,100,100,102]);self.assertEqual(int((diff>0).sum()-(diff<0).sum()),1)
 def test_threshold_200(self):
  ticks=np.arange(201);self.assertEqual(int((np.diff(ticks)>0).sum()),200)
 def test_tester_guard_no_live(self):
  s=(Path(__file__).parent/'EA/Main.mqh').read_text();self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',s)
 def test_no_entry_at_eod_no_cumulative_filter(self):
  s=(Path(__file__).parent/'EA/Main.mqh').read_text();self.assertIn('minute>=840',s);self.assertIn('if(up-down<200)return;',s);self.assertNotIn('CumDelta',s)
if __name__=='__main__':unittest.main()
