import unittest
import numpy as np
import native as n
import plan
import report as r

class ResearchTests(unittest.TestCase):
 def test_contract_and_position_grouping(self):
  opened=n.n.epoch('2026.07.07')+14*3600+15*60;closed=opened+3600
  events=[dict(position_id=8,side=1,volume='.5',sl='99',tp='103',requested_risk='50',actual_risk='50',cash_per_point_lot='100',signal_epoch=opened-900,request_spread='.1',range_width='1',atr='1',open_relvol='1',request_price='100')]
  deals=[dict(deal=2,position_id=8,epoch=opened,entry=0,type=0,volume='.5',price='100',gross=0,commission=-1,swap=0,fee=0,comment='entry'),dict(deal=3,position_id=8,epoch=closed,entry=1,type=1,volume='.5',price='101',gross=50,commission=-1,swap=-2,fee=0,comment='')]
  ts,ledger=n.reconstruct(deals,events,'2026.07.06','2026.10.06',dict(InpSignalTimeframe='15'))
  self.assertEqual(ts[0]['net'],46);self.assertEqual(ledger[-1]['balance'],10046);self.assertEqual(ts[0]['cash_per_point_lot'],100)
 def test_missing_exit_rejected(self):
  with self.assertRaises(AssertionError):n.reconstruct([dict(deal=2,position_id=8,epoch=1,entry=0,type=0,volume=1,price=100,gross=0,commission=0,swap=0,fee=0,comment='')],[],'2026.07.06','2026.10.06',dict(InpSignalTimeframe='15'))
 def test_streaks_and_net_sign(self):
  ts=[dict(net=v,requested_risk=10,actual_risk=10) for v in [5,6,-7,0,-2,-1,9]];m=n.n.metrics(ts)
  self.assertEqual((m['win_streak'],m['loss_streak']),(2,2));self.assertEqual(m['wins'],3);self.assertEqual(m['flat'],1)
 def test_gate_not_only_win_rate(self):
  q=dict(operational_failure=False,native=dict(equity_dd_pct=5),metrics=dict(trades=130,pf=.9,win_rate=90,net_profit=-1,win_streak=8,loss_streak=2))
  self.assertFalse(plan.gate(q,120));q['metrics'].update(pf=1.3,net_profit=10);self.assertTrue(plan.gate(q,120))
  q['operational_failure']=True;self.assertFalse(plan.gate(q,120))
 def test_round_trip_monte_carlo(self):
  q=dict(metrics=dict(net_profit=40),trades=[dict(net=100,open_epoch=1),dict(net=-60,open_epoch=3)])
  x=r.a.position_returns(q);self.assertAlmostEqual((np.prod(1+x)-1)*100,.4)
 def test_production_preserved(self):
  f=n.read(n.R/'frozen.json');self.assertTrue(all(n.sha(n.B/p)==s for p,s in f['production'].items()))
 def test_no_live_api_or_chart_launch(self):
  source=(n.R/'native.py').read_text();self.assertNotIn('import MetaTrader5',source);self.assertIn('AllowLiveTrading=0',source);self.assertIn('Calyx Research Empty',source)
  self.assertEqual(n.inputs({},'t')['InpTesterServerUTCOffsetHours'],'0')
if __name__=='__main__':unittest.main()
