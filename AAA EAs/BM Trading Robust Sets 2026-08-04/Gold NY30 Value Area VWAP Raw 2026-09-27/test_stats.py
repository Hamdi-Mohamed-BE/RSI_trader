"""Reporting unit tests: BE-after-cost losses, zero trades and time denominators."""
import unittest
import audit
class StatisticsTests(unittest.TestCase):
 def test_net_cost_streaks(self):
  values=[300,-100,-1,-100,0,300,300,-100]
  trades=[dict(net_profit=v,close_time=f"2026-03-{i+2:02d}T14:00:00",commission=-1.,swap=0.) for i,v in enumerate(values)]
  s=audit.stats(trades,"2026.03.01","2026.04.01")
  self.assertEqual(s["net_usd"],599)
  self.assertEqual(s["win_rate_pct"],37.5)
  self.assertAlmostEqual(s["profit_factor"],900/301)
  self.assertEqual(s["max_win_streak"],2)
  self.assertEqual(s["max_loss_streak"],3)
  self.assertEqual(s["monthly"]["2026-03"]["trades"],8)
  self.assertAlmostEqual(s["trades_per_weekday"],8/22)
 def test_empty(self):
  s=audit.stats([],"2026.03.01","2026.04.01")
  self.assertEqual(s["trades"],0);self.assertEqual(s["win_rate_pct"],0)
  self.assertEqual(s["max_loss_streak"],0);self.assertIsNone(s["profit_factor"])
if __name__=="__main__":unittest.main()

