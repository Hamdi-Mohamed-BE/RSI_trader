"""Small independent numerical fixtures; no terminal or account access."""
import unittest
import numpy as np
import pandas as pd
import runner as r
import finish
class AnalysisTests(unittest.TestCase):
    def test_whole_position_partial_and_both_side_costs(self):
        fields='ticket position_id epoch entry type volume price profit commission swap fee reason initial_sl initial_tp'.split()
        rows=[[2,2,100,0,0,2,100,0,-2,0,0,3,90,120],
              [3,2,110,1,1,1,110,10,-1,0,0,0,0,0],
              [4,2,120,1,1,1,90,-10,-1,-.5,0,4,0,0]]
        t=r.ledger(pd.DataFrame(rows,columns=fields))
        self.assertEqual(len(t),1);self.assertEqual(t[0]['exit_deals'],2)
        self.assertAlmostEqual(t[0]['net_profit'],-4.5);self.assertAlmostEqual(t[0]['closed_volume'],2)
        self.assertEqual(t[0]['close_epoch'],120)
    def test_samples_reproducible_and_block_preserving(self):
        a=finish.samples([1,2,3,4,5,6,7],paths=100,block=5,seed=7)
        self.assertTrue(np.array_equal(a,finish.samples([1,2,3,4,5,6,7],paths=100,block=5,seed=7)))
        self.assertTrue(np.all((a[:,1:5]-a[:,:4])%7==1))
    def test_open_boundary_position_is_not_a_closed_trade(self):
        fields='ticket position_id epoch entry type volume price profit commission swap fee reason initial_sl initial_tp'.split()
        rows=[[2,2,100,0,0,2,100,0,-2,0,0,3,90,120]]
        deals=pd.DataFrame(rows,columns=fields)
        self.assertEqual(r.ledger(deals,allow_open=True),[])
        with self.assertRaises(AssertionError):r.ledger(deals)
    def test_constant_returns_have_exact_compounding(self):
        d=finish.summary_paths(np.full((10,10),.01))
        self.assertAlmostEqual(d['return_p50_pct'],(1.01**10-1)*100)
        self.assertAlmostEqual(d['max_drawdown_p50_pct'],0);self.assertEqual(d['probability_profit_pct'],100)
    def fixture(self,value):
        days=pd.date_range('2024-10-07',periods=730);eq=10000;tr=[]
        for day in days:
            pnl=eq*value;eq+=pnl;tr.append(dict(open_time=day.isoformat(),close_time=day.isoformat(),net_profit=pnl))
        return dict(start='2024-10-07',end='2026-10-07',trades=tr)
    def test_prop_two_phase_reset_and_minimum_days(self):
        result=finish.ftmo(self.fixture(.01),7,handover_override=(0,0))
        self.assertEqual(result['closed_pnl_two_phase_pass_pct'],100)
        self.assertEqual(result['median_calendar_days_to_pass'],15)
        self.assertEqual(result['closed_pnl_breach_pct'],0)
    def test_prop_negative_path_breaches(self):
        result=finish.ftmo(self.fixture(-.01),7)
        self.assertEqual(result['closed_pnl_two_phase_pass_pct'],0)
        self.assertEqual(result['closed_pnl_breach_pct'],100)
    def test_existing_prop_engine_matches_simple_reference(self):
        a=finish.ftmo(self.fixture(.01),7,handover_override=(0,0));b=finish.ftmo_reference(self.fixture(.01),7)
        self.assertEqual(a['closed_pnl_two_phase_pass_pct'],b['closed_pnl_two_phase_pass_pct'])
        self.assertEqual(a['median_calendar_days_to_pass'],b['median_calendar_days_to_pass'])
    def test_no_trades_is_not_a_pass(self):
        result=finish.bootstrap(dict(trades=[]),7)
        self.assertEqual(result['status'],'insufficient_data');self.assertEqual(result['probability_profit_pct'],0)
if __name__=='__main__':unittest.main()
