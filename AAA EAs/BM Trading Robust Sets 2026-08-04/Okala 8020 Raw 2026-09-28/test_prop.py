"""Deterministic accounting and lifecycle checks; no target terminal needed."""
import unittest
import numpy as np
import prop_sim as m

BASE=m.epoch('2025-09-01');START=m.epoch('2025-09-29')
CLOCK=m.clocks(BASE,m.epoch('2027-01-01'))

def fixture(profits,spacing=m.DAY,hold=60.,low=None,price=1000.):
 gs=[];events=[]
 for i,net in enumerate(profits):
  op=START+i*spacing+14*3600;off=len(events)
  es=np.zeros((3,13));es[:,0]=[0.,hold/2,hold]
  es[-1,1:5]=net;es[-1,5:9]=net
  if low is not None:es[1,2:4]=low;es[1,6:8]=low
  es[-1,9]=max(0.,net);es[-1,10]=max(0.,net) if hold<=30 else 0.
  gs.append([op,op+hold,price,10.,off,3,net,2,1,1]);events.extend(es)
 return np.array(gs).reshape((-1,10)),np.array(events).reshape((-1,13))

def run(g,e,instant=False,risk=.0025,margin=.3,days=60):
 return m.run(g,e,START,START+days*m.DAY,BASE,CLOCK,5000. if instant else 10000.,risk,instant,margin,False)

class Checks(unittest.TestCase):
 def test_no_trades(self):
  s,_,_=run(*fixture([]));self.assertEqual(s[m.BAL],10000);self.assertEqual(s[m.REQUEST],-1)
 def test_cash_reconciliation(self):
  s,_,log=run(*fixture([5,-10,20]));self.assertAlmostEqual(s[m.BAL],10000+sum(log[:,3]));self.assertEqual(s[m.TRADES],3)
 def test_four_opening_days_required(self):
  s,_,_=run(*fixture([110]*4,spacing=3600));self.assertGreater(s[m.BAL],11000);self.assertEqual(s[m.P1],-1)
  s,_,_=run(*fixture([110]*4));self.assertGreater(s[m.P1],0);self.assertEqual(s[m.PHASE],2)
 def test_phase_order_and_admin_delay(self):
  s,_,_=run(*fixture([110]*30));self.assertGreater(s[m.P2],s[m.P1]+2*m.DAY);self.assertGreater(s[m.FUNDED],s[m.P2]);self.assertGreater(s[m.REQUEST],s[m.FUNDED]+14*m.DAY)
 def test_floating_loss_checked_before_winning_close(self):
  s,_,_=run(*fixture([100],low=-220),risk=.005);self.assertGreater(s[m.BREACH],0);self.assertEqual(s[m.TRADES],0)
 def test_partial_profit_raises_instant_floor(self):
  g,e=fixture([-100]);e[1,1:5]=200;e[1,5:9]=200
  s,_,_=run(g,e,instant=True);self.assertGreater(s[m.FLOOR],4700);self.assertGreater(s[m.BREACH],0)
 def test_quick_positive_fails_cycle_but_quick_loss_does_not(self):
  s,_,_=run(*fixture([100],hold=15),instant=True);self.assertGreater(s[m.QUICK],0);self.assertEqual(s[m.CASH],0)
  s,_,_=run(*fixture([-5],hold=15),instant=True);self.assertEqual(s[m.QUICK],-1)
 def test_withdrawal_is_not_daily_loss(self):
  s=m.initial(START,10000.,False);s[m.PHASE]=3;s[m.CSTART]=START;s[m.BAL]=11000.;s[m.DBAL]=11000.;s[m.DKEY]=m.key(START+15*m.DAY,BASE,CLOCK,0)
  m.flat_actions(s,START+15*m.DAY,START+15*m.DAY,10000.,False,BASE,CLOCK)
  self.assertEqual(s[m.BAL],10000);self.assertEqual(s[m.DBAL],10000);self.assertEqual(s[m.CASH],800)
 def test_below_minimum_not_rounded_up(self):
  s,r,_=run(*fixture([100]),instant=True,risk=.00001);self.assertEqual(s[m.ACCEPT],0);self.assertEqual(r[0],1)
 def test_margin_sizes_down_and_total_idea_risk(self):
  s,_,log=run(*fixture([20],price=25000.),instant=True);self.assertLessEqual(log[0,2]*25000/5,1500);self.assertAlmostEqual(log[0,4],log[0,2]*10);self.assertLessEqual(log[0,4],12.5)
 def test_horizon_does_not_look_ahead_to_exit(self):
  g,e=fixture([100],hold=m.DAY);s,_,_=run(g,e,days=1);self.assertEqual(s[m.OPEN],1);self.assertEqual(s[m.TRADES],0);self.assertEqual(s[m.REQUEST],-1)
 def test_loss_guard(self):
  s,r,_=run(*fixture([-10]*5,spacing=3600));self.assertEqual(s[m.TRADES],3);self.assertEqual(r[3],2)
 def test_minimum_withdrawal_and_buffer(self):
  s=m.initial(START,5000.,True);s[m.CSTART]=START;s[m.BAL]=5049
  m.flat_actions(s,START+15*m.DAY,START+15*m.DAY,5000.,True,BASE,CLOCK);self.assertEqual(s[m.CASH],0)
  s[m.BAL]=5070;s[m.FLOOR]=4900
  m.flat_actions(s,START+15*m.DAY,START+15*m.DAY,5000.,True,BASE,CLOCK);self.assertEqual(s[m.CASH],0)
 def test_native_paths_nonoverlap_and_cash(self):
  for variant in ('combined','combined-tp15'):
   z=np.load(m.ROOT/'native'/f'{variant}-1y-m4'/'prop-ready.npz');g=z['groups'];e=z['events']
   self.assertTrue(np.all(g[1:,0]>=g[:-1,1]))
   self.assertTrue(np.all(e[:,0]>=-1e-6))
   for x in g:
    final=e[int(x[4]+x[5]-1)];self.assertAlmostEqual(final[1],final[2]);self.assertAlmostEqual(final[5],final[6])
 def test_bootstrap_clock_and_nonoverlap(self):
  z=np.load(m.ROOT/'native/combined-1y-m4/prop-ready.npz')
  for start,g in m.block_paths(z['groups'],n=5):
   self.assertTrue(np.all(g[1:,0]>=g[:-1,1]));self.assertTrue(np.all(g[:,0]>=start))
   for x in g:
    d=m.datetime.fromtimestamp(x[0],m.UTC).astimezone(m.NY);self.assertIn(d.hour,[9,10,11,13,14,15]);self.assertLess(d.weekday(),5)

if __name__=='__main__':unittest.main(verbosity=2)
