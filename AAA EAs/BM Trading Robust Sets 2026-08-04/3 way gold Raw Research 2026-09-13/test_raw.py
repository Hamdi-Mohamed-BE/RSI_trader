import unittest
from pathlib import Path
from run_raw import raw_signals, group_stats

class RawTests(unittest.TestCase):
    def setUp(self):
        self.x=dict(c1=110,c2=99,e20_1=105,e20_2=100,e50=106,e200=101,adx=25,plus=30,minus=10,
            e9_1=99,e9_2=99,e21_1=100,e21_2=100,rsi=50,prior20_high=115,prior20_low=90,tr=10,atr1=10,atr2=10)
    def test_momentum_long(self):self.assertEqual(raw_signals(self.x),(1,0,0))
    def test_momentum_weak_adx(self):
        self.x['adx']=24.99;self.assertEqual(raw_signals(self.x)[0],0)
    def test_momentum_requires_new_cross(self):
        self.x['c2']=101;self.assertEqual(raw_signals(self.x)[0],0)
    def test_momentum_short(self):
        self.x.update(c1=90,c2=101,e20_1=95,e50=94,e200=99,plus=10,minus=30)
        self.assertEqual(raw_signals(self.x)[0],-1)
    def test_change_long(self):
        self.x.update(e9_1=102,e21_1=101,rsi=51);self.assertEqual(raw_signals(self.x)[1],1)
    def test_change_short(self):
        self.x.update(e9_1=98,e9_2=101,e21_1=99,rsi=49);self.assertEqual(raw_signals(self.x)[1],-1)
    def test_change_rsi_midline(self):
        self.x.update(e9_1=102,e21_1=101,rsi=50);self.assertEqual(raw_signals(self.x)[1],0)
    def test_breakout_long(self):
        self.x.update(c1=116,tr=15,atr1=11);self.assertEqual(raw_signals(self.x)[2],1)
    def test_breakout_short(self):
        self.x.update(c1=89,tr=15,atr1=11);self.assertEqual(raw_signals(self.x)[2],-1)
    def test_touch_not_breakout(self):
        self.x.update(c1=115,tr=15,atr1=11);self.assertEqual(raw_signals(self.x)[2],0)
    def test_range_expansion_required(self):
        self.x.update(c1=116,tr=14.99,atr1=11);self.assertEqual(raw_signals(self.x)[2],0)
    def test_atr_expansion_required(self):
        self.x.update(c1=116,tr=15,atr1=10);self.assertEqual(raw_signals(self.x)[2],0)
    def test_costs_classify_net_loss(self):
        t=dict(position_id='1',close_time='2026.01.02 00:00:00',net=-1,commission=-2,swap=0,fee=0,direction=1)
        r=group_stats([t]);self.assertEqual((r['wins'],r['losses'],r['net_profit']),(0,1,-1))
    def test_tester_guard_and_raw_limits(self):
        src=(Path(__file__).parent/'EA'/'3 way gold.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))',src)
        self.assertIn('ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',src)
        self.assertNotIn('PositionModify(',src)
        self.assertIn('quote.ask<quote.bid',src) # Zero spread is a valid quote.
        self.assertIn('if(HasEngine(engine))',src)
    def test_simulator_disables_live_and_optimization(self):
        src=(Path(__file__).parent/'run_raw.py').read_text()
        self.assertIn('AllowLiveTrading=0',src);self.assertIn('Optimization=0',src)

if __name__=='__main__':unittest.main(verbosity=2)
