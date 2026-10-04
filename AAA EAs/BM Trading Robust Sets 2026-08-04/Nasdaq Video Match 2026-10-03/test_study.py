import unittest
from pathlib import Path
import pandas as pd
import run as r
class Tests(unittest.TestCase):
 def test_exact_literal_rule(self):
  self.assertEqual(r.VARIANTS['VIDEO_ATR'],dict(body=1,di=False,trail='ATR'))
  self.assertEqual(r.VARIANTS['SYMMETRIC_ATR']['body'],2)
 def test_isolated_one_factor_di(self):
  a=r.VARIANTS['VIDEO_ATR'];b=r.VARIANTS['VIDEO_ATR_DI'];self.assertEqual({k:v for k,v in a.items() if k!='di'},{k:v for k,v in b.items() if k!='di'})
 def test_ma_not_atr(self):
  v=r.values('VIDEO_MA','test',True);self.assertEqual(v['InpUseATRTrailing'],'false');self.assertEqual(v['InpUseMATrailing'],'true');self.assertEqual(v['InpTrailMAPeriod'],'200');self.assertEqual(v['InpTrailMAStartR'],'0.50')
 def test_preserve_risk_no_target_overnight(self):
  for variant in r.VARIANTS:
   v=r.values(variant,'test',True)
   for key,value in dict(InpRiskPercent='1.0',InpInitialStopPercent='0.60',InpUseFixedTarget='false',InpCloseAtSessionEnd='false',InpAdaptivePortfolioControls='false').items():self.assertEqual(v[key],value)
 def test_research_switch_off_baseline(self):self.assertEqual(r.values('CURRENT','test',True)['InpCandleDirectionRule'],'0')
 def test_streaks(self):
  d=r.streaks([1,1,-1,0,-1,-1,-1,1]);self.assertEqual(d['max_win_streak'],2);self.assertEqual(d['max_loss_streak'],3)
 def test_dst_signal(self):
  d=pd.to_datetime(['2026-01-15 14:30Z','2026-07-15 13:30Z']).tz_convert('America/New_York');self.assertEqual(d.hour.tolist(),[9,9]);self.assertEqual(d.minute.tolist(),[30,30])
 def test_six_frozen_configs(self):self.assertEqual(len(r.VARIANTS),6)
 def test_test_only_guard(self):self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',r.SOURCE.read_text())
 def test_calendar_sharpe_includes_sunday(self):
  import report
  import numpy as np
  d=pd.DataFrame(dict(close_time=['2026-10-04T22:00:00'],net_profit=[100.0]));returns=np.array([0,0,0,.01])
  self.assertAlmostEqual(report.sharpe_calendar(d,'2026.10.01','2026.10.05'),returns.mean()/returns.std(ddof=1)*np.sqrt(365.2425))
if __name__=='__main__':unittest.main()
