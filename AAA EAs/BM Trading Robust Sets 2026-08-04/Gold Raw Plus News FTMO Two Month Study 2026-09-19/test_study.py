import unittest
from datetime import datetime,timezone,timedelta
import study as s

def synthetic(profits,dates=None,marks=None):
    trades=[];events=[]
    for i,g in enumerate(profits):
        op=s.dt((dates[i] if dates else f'2026-07-{20+i:02d}')+'T12:00:00Z')
        r=dict(id=i,key='raw',op=op,cl=op+60,open_price=100.,unit_risk=10000.,unit_gross=g/.01,unit_comm=0.,unit_extra=0.,unit_swap=0.)
        trades.append(r);events.extend([(op,1,i,0.),(op+60,3,i,0.)])
        if marks and i in marks:events.append((op+30,2,i,marks[i]/.01))
    return trades,[],events,[[] for _ in range(9)],{}

class ReplayTests(unittest.TestCase):
    def test_round_up(self):
        self.assertAlmostEqual(s.ceil_lot(.025),.03)
        self.assertAlmostEqual(s.ceil_lot(.03),.03)
        self.assertAlmostEqual(s.ceil_lot(.001),.01)
    def test_cash_conservation(self):
        r=s.replay(synthetic([20,-30,80]),0,challenge=False)
        self.assertAlmostEqual(r['balance'],10070)
        self.assertEqual(r['closed_trades'],3)
    def test_floating_daily_breach(self):
        r=s.replay(synthetic([20],marks={0:-510}),0)
        self.assertIsNotNone(r['proxy_breach'])
        self.assertEqual(r['closed_trades'],0)
    def test_four_distinct_days(self):
        r=s.replay(synthetic([600,600]),0)
        self.assertEqual(r['phase'],1)
        self.assertEqual(r['passes'],[])
        r=s.replay(synthetic([300]*4),0)
        self.assertEqual(r['phase'],2)
        self.assertEqual(r['passes'][0]['trading_days'],4)
        self.assertEqual(r['balance'],10000)
    def test_daily_reset(self):
        r=s.replay(synthetic([-400,-400]),.75,challenge=False)
        self.assertIsNone(r['proxy_breach'])
        self.assertEqual(r['balance'],9200)
        r=s.replay(synthetic([-400,-400,-300]),.75,challenge=False)
        self.assertIsNotNone(r['proxy_breach'])
    def test_cash_costs(self):
        d=synthetic([100]);d[0][0].update(unit_comm=-7.,unit_extra=100.)
        r=s.replay(d,0,challenge=False)
        self.assertAlmostEqual(r['balance'],10098.93)
    def test_phase_and_payout_delay(self):
        dates=['2026-07-20','2026-07-21','2026-07-22','2026-07-23',
               '2026-07-28','2026-07-29','2026-07-30','2026-07-31','2026-08-10']
        r=s.replay(synthetic([300]*8+[100],dates),0)
        self.assertEqual(len(r['passes']),2)
        self.assertTrue(r['funded_by_end'])
        self.assertTrue(r['payout_received_by_end'])
        self.assertGreaterEqual(s.dt(r['payout_requested'])-s.dt('2026-08-10T12:00:00Z'),14*s.DAY)
        self.assertAlmostEqual(r['reward'],80.)
    def test_real_source_full_coverage_and_reserve(self):
        d=s.load(False)
        self.assertEqual(len(d[0]),51)
        self.assertEqual(len(d[1]),12)
        r=s.replay(d,.75)
        self.assertEqual(r['counts'].get('news_baskets_accepted',0),0)
        self.assertEqual(r['counts'].get('news_margin_rejected',0),12)
        # Replaying weeks in their original order must be identical.
        b=s.replay(d,.05);c=s.replay(d,.05,sample=list(range(9)))
        self.assertEqual(b,c)
    def test_resampling_retains_new_york_clock_across_dst(self):
        d=synthetic([1])
        weekly=[[(t-s.MONDAY,k,i,v) for t,k,i,v in d[2]]]
        d=(d[0],d[1],d[2],weekly,d[4])
        r=s.replay(d,0,challenge=False,detail=True,sample=[0]*16,
                   end=s.dt('2026-11-10T00:00:00Z'),preserve_ny_clock=True)
        self.assertEqual(r['log'][0]['open'],'2026-07-20T12:00:00+00:00')
        self.assertEqual(r['log'][-1]['open'],'2026-11-02T13:00:00+00:00')
        self.assertEqual(r['closed_trades'],16)

if __name__=='__main__':unittest.main()
