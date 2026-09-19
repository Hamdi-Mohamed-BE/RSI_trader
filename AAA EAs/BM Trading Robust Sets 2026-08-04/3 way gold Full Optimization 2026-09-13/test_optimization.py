import unittest,json
import numpy as np
from params import *
from data import ema,indicators
from screen import simulate
from pipeline import eligible

class OptimizationTests(unittest.TestCase):
    def sample(self,direction=1,low=99.8,high=100.2,spread=0.,atr=1.,price=100.,risk=.3,management=0):
        h=np.array([[0,price,price,price,price,spread,2],[3600,price,high,low,price,spread,2],[7200,price,price,price,price,spread,2]],float)
        m=h[:,:6].copy();start=np.array([0,1,2]);end=start+1;roll=np.zeros(3);sig=np.zeros((3,3),np.int8);sig[0,0]=direction
        return simulate(h,m,start,end,roll,sig,np.full(3,atr),1,3,risk,np.array([1.,0,0]),np.ones(3),np.full(3,2.),management,1.,2.,5.5,53.49)
    def test_same_minute_stop_first(self):self.assertLess(self.sample(low=98,high=103)[0],-30)
    def test_target_with_costs(self):
        r=self.sample(low=99.8,high=103);self.assertGreater(r[0],55);self.assertLess(r[0],60);self.assertEqual(r[1],1);self.assertEqual(r[2],100)
    def test_short_mirrored_stop(self):self.assertLess(self.sample(direction=-1,low=97,high=102)[0],-30)
    def test_short_target(self):self.assertGreater(self.sample(direction=-1,low=97,high=100.2)[0],55)
    def test_spread_cost(self):
        a=self.sample();b=self.sample(spread=100);self.assertLess(b[0],a[0])
    def test_minimum_lot_can_overshoot(self):
        r=self.sample(price=5000,low=5000,high=5000,atr=200,risk=.15);self.assertGreater(r[8],1.9)
    def test_fee_recorded_without_price_change(self):
        r=self.sample(low=100,high=100);self.assertLess(r[0],0);self.assertAlmostEqual(r[0],r[6])
    def test_no_future_indicator_dependency(self):
        h=np.zeros((250,7));h[:,4]=100+np.sin(np.arange(250)/9);h[:,2]=h[:,4]+1;h[:,3]=h[:,4]-1
        h2=h.copy();h2[170:,4]+=100;h2[170:,2]+=100;h2[170:,3]+=100
        for a,b in zip(indicators(h,14),indicators(h2,14)):np.testing.assert_array_equal(a[:170],b[:170])
        np.testing.assert_array_equal(ema(h[:,4],50)[:170],ema(h2[:,4],50)[:170])
    def test_native_eligibility_rejects_weak_pf(self):
        t=dict(net_profit=10,net_pf=1.04,max_equity_dd_pct=1,native_stopout=False,trades=100)
        self.assertFalse(eligible(t,t))
    def test_native_eligibility_requires_validation_sample(self):
        t=dict(net_profit=10,net_pf=1.3,max_equity_dd_pct=1,native_stopout=False,trades=100);v={**t,'trades':19}
        self.assertFalse(eligible(t,v));self.assertTrue(eligible(t,t))
    def test_configs_stable(self):self.assertEqual(ident(DEFAULT),ident(normalize({})))
    def test_source_safety(self):
        text=(ROOT/'EA'/'3 way gold Optimized.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))',text);self.assertIn('ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',text)
        self.assertIn('b[1].close-entry',text);self.assertNotIn('b[0].close-entry',text)
        self.assertIn('if(HasEngine(engine))',text)
        runner=(ROOT/'native.py').read_text();self.assertIn('AllowLiveTrading=0',runner);self.assertIn('UseCloud=0',runner)
    def test_default_native_parity(self):self.assertTrue(json.loads((ROOT/'raw-parity.json').read_text())['full_trade_ledger_identical'])
    def test_finalists_do_not_use_locked_window(self):
        for r in json.loads((ROOT/'Search'/'finalists.json').read_text()):
            self.assertEqual(tuple(r['train']['window']),TRAIN);self.assertEqual(tuple(r['validation']['window']),VALID)

if __name__=='__main__':unittest.main(verbosity=2)
