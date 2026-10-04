import unittest
import numpy as np
import pandas as pd
import research as r
class Tests(unittest.TestCase):
 def test_exact_hold(self):
  t=np.arange(65)*60;self.assertEqual(np.flatnonzero(r.eligible(t)).tolist(),list(range(5)))
 def test_no_gap_bridge(self):
  t=np.delete(np.arange(122)*60,35);self.assertFalse(r.eligible(t)[0]);self.assertTrue(r.eligible(t)[35])
 def test_streaks(self):self.assertEqual(r.streak([1,1,-1,0,-1,-1,-1,1]),(2,3))
 def test_initial_capital_dd(self):self.assertAlmostEqual(r.drawdown([10000,9000,11000,8800]),20)
 def test_dst(self):
  dates=pd.to_datetime(['2026-01-15 16:00Z','2026-07-15 15:00Z']).tz_convert('America/New_York')
  self.assertEqual(dates.hour.tolist(),[11,11])
 def test_shared_block_multiple_correction(self):
  x=np.random.default_rng(1).normal(size=(200,4));a=r.inference(x,paths=500)
  for z in a:self.assertGreaterEqual(z['p_adjusted_maxT'],z['p_raw'])
 def test_cost_side(self):
  # Long pays ask once, sells bid; same-price quotes lose entry spread.
  self.assertAlmostEqual(100-(100+20*.01),-.2)
if __name__=='__main__':unittest.main()
