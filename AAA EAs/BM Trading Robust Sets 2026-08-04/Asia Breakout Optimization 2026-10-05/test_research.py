import unittest
import native as n
import plan
class AsiaTests(unittest.TestCase):
 def test_screen_dimension_count(self):
  c=plan.cases();self.assertEqual(len(c),29)
  self.assertEqual({x.get('InpRewardRisk',3) for x in c.values()},{.5,.6,.75,1,1.5,2,3,4})
  self.assertTrue(all('InpStudyDI' not in v for v in c.values()))
 def test_default_preserves_clock_and_risk(self):
  vals=n.inputs({},'unit');self.assertEqual(vals['InpTesterServerClockMode'],'1');self.assertEqual(vals['InpRewardRisk'],'3')
  self.assertEqual(vals['InpRiskPercent'],'1.0');self.assertEqual(vals['InpUseMarkovRegimeFilter'],'true')
 def test_independent_whole_position_net(self):
  start='2025.10.05';epoch=n.n.epoch(start)+86400+3600;signal=epoch-3600
  deals=[dict(deal=1,position_id=1,epoch=epoch,entry=0,type=0,volume=.1,price=2000,gross=0,commission=-.1,swap=0,fee=0,comment='in'),
   dict(deal=2,position_id=1,epoch=epoch+3600,entry=1,type=1,volume=.1,price=2020,gross=200,commission=-.1,swap=-.2,fee=0,comment='out')]
  events=[dict(position_id=1,side=1,volume=.1,sl=1990,tp=2030,requested_risk=100,actual_risk=100,signal_epoch=signal,request_spread=.2)]
  ts,ledger=n.reconstruct(deals,events,start,'2026.10.05',{})
  self.assertEqual(len(ts),1);self.assertAlmostEqual(ts[0]['net'],199.6);self.assertAlmostEqual(ledger[-1]['balance'],10199.6)
  self.assertAlmostEqual(ts[0]['initial_rr'],3)
 def test_reject_future_signal(self):
  epoch=n.n.epoch('2025.10.05')+86400
  deals=[dict(deal=1,position_id=1,epoch=epoch,entry=0,type=0,volume=.1,price=2000,gross=0,commission=0,swap=0,fee=0,comment='in'),
   dict(deal=2,position_id=1,epoch=epoch+3600,entry=1,type=1,volume=.1,price=2010,gross=100,commission=0,swap=0,fee=0,comment='out')]
  events=[dict(position_id=1,side=1,volume=.1,sl=1990,tp=2030,requested_risk=100,actual_risk=100,signal_epoch=epoch,request_spread=.2)]
  with self.assertRaises(AssertionError):n.reconstruct(deals,events,'2025.10.05','2026.10.05',{})
 def test_reject_open_or_partial_position(self):
  epoch=n.n.epoch('2025.10.05')+86400
  deals=[dict(deal=1,position_id=1,epoch=epoch,entry=0,type=0,volume=.1,price=2000,gross=0,commission=0,swap=0,fee=0,comment='in')]
  events=[dict(position_id=1)]
  with self.assertRaises(AssertionError):n.reconstruct(deals,events,'2025.10.05','2026.10.05',{})
 def test_preference_not_winrate_alone(self):
  q=dict(metrics=dict(trades=100,net_profit=20,pf=1.1,win_rate=80,win_streak=8,loss_streak=3),native=dict(equity_dd_pct=3),operational_failure=False)
  self.assertFalse(plan.qualify(q,90));q['metrics']['pf']=1.3;self.assertTrue(plan.qualify(q,90))
  q['operational_failure']=True;self.assertFalse(plan.qualify(q,90))
 def test_test_only_guard(self):
  source=(n.R/'EA/ResearchAudit.mqh').read_text();self.assertIn('MQLInfoInteger(MQL_TESTER)',source)
  code=(n.R/'EA/AAA_Final_Strategy_Engine.mqh').read_text();self.assertIn('CopyRates(_Symbol,PERIOD_D1,1,requested,daily)',code)
  self.assertIn('newer>=1',code)
if __name__=='__main__':unittest.main()
