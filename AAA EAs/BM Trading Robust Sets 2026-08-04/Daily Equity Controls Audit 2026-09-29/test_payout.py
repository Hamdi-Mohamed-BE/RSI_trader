import unittest
import numpy as np
from datetime import datetime,timezone
from test_simulate import Controls
from payout_followup import business_ready, summarize, DAY

class PayoutEndpoints(Controls):
    def test_stage_does_not_pass_on_floating_profit(self):
        a=self.fixture([0],[9],[100,1500,1500])
        m,l=self.execute(a,stop_profit=1000,min_days=1)
        self.assertEqual(m['stop_minute'],-1)
    def test_stage_four_distinct_days(self):
        a=list(self.fixture([0,2,4,6],[1,3,5,7],[100]*10,[1100,0,0,0]))
        a[-1]=np.array([1,1,2,2,3,3,4,4,5,5],np.int64)
        m,l=self.execute(a,stop_profit=1000,min_days=4)
        self.assertEqual(m['stop_minute'],7)
        self.assertEqual(m['balance'],11100)
    def test_reward_age_starts_at_first_entry(self):
        a=self.fixture([100],[101],[100.]*(15*DAY+1),[100])
        m,l=self.execute(a,stop_profit=50,min_age_days=14)
        self.assertEqual(m['stop_minute'],100+14*DAY)
    def test_small_profit_not_enough_for_chosen_reward_threshold(self):
        a=self.fixture([0],[1],[100.]*(15*DAY+1),[49])
        m,l=self.execute(a,stop_profit=50,min_age_days=14)
        self.assertEqual(m['stop_minute'],-1)
    def test_pause_entries_while_waiting_to_be_flat(self):
        a=self.fixture([0,0,2],[1,3,4],[100]*6,[1100,0,100])
        m,l=self.execute(a,stop_profit=1000,min_days=1)
        self.assertEqual(m['stop_minute'],3)
        self.assertEqual(m['blocked_day'],1)
        self.assertEqual(m['trades'],2)
    def test_haircut_scales_positive_and_negative_gross(self):
        a=self.fixture([0,2],[1,3],[100]*5,[100,-50])
        m,l=self.execute(a,edge_haircut=.1)
        self.assertAlmostEqual(m['balance'],10035)
    def test_admin_delay_skips_weekend_and_observes_dst(self):
        st=int(datetime(2026,3,27,12,tzinfo=timezone.utc).timestamp()//60)
        en=business_ready(st,2)
        expected=int(datetime(2026,3,31,11,tzinfo=timezone.utc).timestamp()//60)
        self.assertEqual(en,expected)
    def test_incomplete_horizons_excluded(self):
        p=dict(start=0,end=180*DAY,phase1=35*DAY,phase2=60*DAY,funded=67*DAY,breach=None,
               envelope_flag=None,rewards=[dict(request=90*DAY,trader_share=80)],stages=[])
        short=dict(p,end=29*DAY)
        out=summarize([p,short],90)
        self.assertEqual(out['starts'],1)
        self.assertEqual(out['counts']['reward'],1)
        self.assertEqual(out['total_trader_share_all_starts_usd']['mean'],80)

if __name__=='__main__':unittest.main(verbosity=2)
