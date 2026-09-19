import unittest
from audit_logic import pivot,rejection,rounded
from run_pipeline import DEFAULT,score,neighbours,signature,annotate_trades

class PipelineTest(unittest.TestCase):
    def test_one_right_bar_is_unavailable_before_close(self):
        b=[{'high':x,'low':0} for x in [1,3,2]]
        self.assertTrue(pivot(b,1,1,True));self.assertFalse(pivot(b[:2],1,1,True))
    def test_two_right_bars_required(self):
        b=[{'high':x,'low':0} for x in [1,2,5,3,4]]
        self.assertTrue(pivot(b,2,2,True));self.assertFalse(pivot(b[:4],2,2,True))
    def test_tie_is_not_swing(self):self.assertFalse(pivot([{'high':x,'low':0} for x in [1,3,3]],1,1,True))
    def test_low_mirrors_high(self):self.assertTrue(pivot([{'low':x,'high':10} for x in [5,1,3]],1,1,False))
    def test_close_rejection_differs_from_body(self):
        b={'open':10.5,'close':12,'low':10.2,'high':13}
        self.assertFalse(rejection(b,1,10,11,0));self.assertTrue(rejection(b,1,10,11,1))
    def test_close_rejection_needs_wick_not_breach(self):
        b={'open':10.5,'close':12,'low':9.9,'high':13}
        self.assertFalse(rejection(b,1,10,11,1))
    def test_rounding_beyond_stop(self):
        self.assertAlmostEqual(rounded(10.1234,.001,False),10.123)
        self.assertAlmostEqual(rounded(10.1234,.001,True),10.124)
    def test_sample_penalty(self):
        r={'trades':14,'net_pf':4,'return_pct':20,'dd_pct':1}
        self.assertEqual(score(r),-9986)
    def test_pf_not_unbounded(self):
        r={'trades':100,'net_pf':8,'return_pct':20,'dd_pct':1}
        self.assertEqual(score(r),score({**r,'net_pf':50}))
    def test_neighbours_change_one_parameter(self):
        ns=neighbours(DEFAULT);self.assertEqual(len(ns),8)
        for n in ns:self.assertEqual(sum(n[k]!=DEFAULT[k] for k in DEFAULT),1)
    def test_unique_deterministic_signature(self):
        self.assertEqual(signature(DEFAULT),signature(dict(reversed(list(DEFAULT.items())))))
        self.assertNotEqual(signature(DEFAULT),signature({**DEFAULT,'InpTargetR':1}))
    def test_risk_not_increased_in_search_defaults(self):self.assertEqual(DEFAULT['InpRiskPercent'],1)
    def test_numeric_representation_is_not_a_new_trial(self):
        self.assertEqual(signature({'InpTargetR':2}),signature({'InpTargetR':2.0}))
        self.assertEqual(signature({'InpStopBufferATR':0}),signature({'InpStopBufferATR':0.0}))
    def test_risk_reference_is_before_entry_costs(self):
        s={'event':'signal','entry':'100','stop':'90','target':'110','risk_cash':'100','equity':'10000','entry_spread_cost':'5'}
        a={**s,'event':'accepted','equity':'9994'}
        t=annotate_trades([{'open_price':100}],[s,a])[0]
        self.assertEqual(t['equity_at_signal'],10000)
        self.assertEqual(t['equity_after_entry'],9994)
if __name__=='__main__':unittest.main()
