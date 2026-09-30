import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from study import Phase,slot,bootstrap,holm,basic,Market

def fake(start='2023-03-10',end='2023-03-15',symbol='BTCUSD'):
 t=pd.date_range(start,end,freq='5min',tz='UTC',inclusive='left').as_unit('s').asi8
 o=100+np.arange(len(t))*.01
 d=pd.DataFrame(dict(time=t,open=o,high=o+.03,low=o-.03,close=o+.005,spread=np.ones(len(t))*2))
 return SimpleNamespace(data=d,floors=np.ones(48),point=.01,tick=.01,symbol=symbol)
class Tests(unittest.TestCase):
 def test_bid_ask_side(self):
  m=fake();p=Phase(m,0);a=p.trades(30,1).iloc[0];b=p.trades(30,-1).iloc[0]
  self.assertAlmostEqual(a.gross_bps,6);self.assertAlmostEqual(a.net_bps,4)
  self.assertAlmostEqual(b.net_bps,-8);self.assertAlmostEqual(a.stress_bps,0)
 def test_short_charges_exit_spread(self):
  m=fake();m.data.loc[6,'spread']=7;p=Phase(m,0)
  self.assertAlmostEqual(p.trades(30,1).iloc[0].cost_bps,2)
  self.assertAlmostEqual(p.trades(30,-1).iloc[0].cost_bps,7)
 def test_gap_reject(self):
  m=fake();m.data=m.data.drop(index=2);p=Phase(m,0)
  self.assertNotEqual(p.trades(30,1).iloc[0].time,int(pd.Timestamp('2023-03-10',tz='UTC').timestamp()))
 def test_rollover(self):
  p=Phase(fake(),0);d=p.trades(120,1)
  for row in d.itertuples():
   clock=pd.date_range(pd.Timestamp(row.time,unit='s',tz='UTC')+pd.Timedelta(minutes=5),pd.Timestamp(row.exit_time,unit='s',tz='UTC'),freq='5min').tz_convert('America/New_York')
   self.assertFalse(any((clock.hour==17)&(clock.minute==0)))
 def test_dst(self):
  t=np.array([pd.Timestamp(x,tz='UTC').timestamp() for x in ['2023-03-10 14:30','2023-03-13 13:30']])
  np.testing.assert_equal(slot(t,'America/New_York'),[19,19])
  np.testing.assert_equal(slot(t,'UTC'),[29,27])
 def test_fall_back_first_only(self):
  p=Phase(fake('2023-11-05','2023-11-06'),0)
  c=dict(hold_minutes=30,direction=1,clock='America/New_York',slot=3)
  a=p.select(c);self.assertEqual(len(a),1)
  self.assertEqual(a.iloc[0].time,pd.Timestamp('2023-11-05 05:30',tz='UTC').timestamp())
 def test_no_cross_split_exit(self):
  p=Phase(fake('2024-03-26','2024-03-28'),0)
  self.assertTrue((p.trades(120,1).exit_time<pd.Timestamp('2024-03-27',tz='UTC').timestamp()).all())
 def test_weekends(self):
  p=Phase(fake(symbol='EURUSD'),0);d=p.trades(30,1)
  self.assertTrue((pd.to_datetime(d.time,unit='s',utc=True).dt.dayofweek<5).all())
 def test_control_same_day(self):
  p=Phase(fake(),0);d=p.trades(60,1)
  np.testing.assert_allclose(d.groupby('utc_day').excess_bps.mean(),0,atol=1e-12)
 def test_holm(self):np.testing.assert_allclose(holm([.001,.04,.02]),[.003,.04,.04])
 def test_bootstrap_deterministic(self):
  x=np.sin(np.arange(1000))+.3;a=bootstrap(x,42);self.assertEqual(a,bootstrap(x,42));self.assertLess(a['p'],.05);self.assertGreater(a['lower95_bps'],0)
 def test_losses_fail(self):
  a=bootstrap(-np.ones(200),42);self.assertEqual(a['p'],1)
 def test_dd_and_streak(self):
  d=basic([1,1,-3,-2,1,0,-1]);self.assertEqual(d['win_streak'],2);self.assertEqual(d['loss_streak'],2);self.assertEqual(d['closed_dd_pct'],.05)
 def test_marked_dd_covers_closed_dd(self):
  p=Phase(fake(),0);c=dict(hold_minutes=30,direction=-1,clock='UTC',slot=2);d,v=p.metrics(c)
  self.assertGreaterEqual(v['marked_dd_pct']+1e-10,v['closed_dd_pct'])
if __name__=='__main__':unittest.main(verbosity=2)
