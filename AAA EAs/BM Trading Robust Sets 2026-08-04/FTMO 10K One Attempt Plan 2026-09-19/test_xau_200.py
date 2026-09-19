import unittest
from datetime import timedelta
from simulate import dt
from xau_200 import challenge,performance,MARGIN_ONE,LOT

BASE=dt('2026-01-05T08:00:00Z')

def make(i,release,side='Long',seconds=1,profit=400,duration=2):
    op=release+timedelta(seconds=seconds)
    return dict(uid=str(i),key='news-pulse-xau/standard',symbol='XAUUSD',news=True,side=side,
                op=op,cl=op+timedelta(seconds=duration),news_event_utc=release.isoformat(),
                volume=1.,gross_profit=profit,commission=-7.,swap=0.,risk_per_lot=400.,
                carry_units=0,open_price=4348.)

class FixedNewsTests(unittest.TestCase):
    def test_fixed_100_not_previous_cost_budget_or_taper(self):
        e=BASE+timedelta(minutes=1)
        r=performance([make(1,e)],BASE,BASE+timedelta(days=1),'source')
        self.assertAlmostEqual(r['net'],98.25)
        self.assertEqual(LOT*400,100)

    def test_both_directions_remain_after_loss(self):
        e=BASE+timedelta(minutes=1)
        rows=[make(1,e,profit=-400),make(2,e,'Short',seconds=20,profit=800)]
        r=challenge(rows,[e],BASE,BASE+timedelta(days=1),'source','on_fill')
        self.assertEqual(r['counts']['opened'],2)
        self.assertAlmostEqual(r['balance'],10096.50)

    def test_overlap_can_reject_second_activation(self):
        e=BASE+timedelta(minutes=1)
        rows=[make(1,e,duration=40),make(2,e,'Short',seconds=20)]
        r=challenge(rows,[e],BASE,BASE+timedelta(days=1),'source','on_fill')
        self.assertEqual(r['counts']['opened'],1)
        self.assertEqual(r['counts']['activation_margin_rejected'],1)

    def test_full_reservation_is_distinct_from_on_fill(self):
        e=BASE+timedelta(minutes=1)
        r=challenge([make(1,e)],[e],BASE,BASE+timedelta(days=1),'source','gross_reservation')
        self.assertEqual(r['counts']['margin_blocked'],1)
        self.assertLess(MARGIN_ONE,10000)
        self.assertGreater(MARGIN_ONE*2,10000)

    def test_four_separate_days_needed_for_each_phase(self):
        releases=[BASE+timedelta(days=i*3,minutes=1) for i in range(20)]
        rows=[make(i,e,profit=4400) for i,e in enumerate(releases)]
        r=challenge(rows,releases,BASE,BASE+timedelta(days=65),'source')
        self.assertEqual(len(r['phases']),2)
        self.assertTrue(all(p['entry_days']>=4 for p in r['phases']))
        self.assertGreaterEqual(r['payout'],100)

    def test_intraday_endpoint_breach_detected(self):
        e=BASE+timedelta(minutes=1)
        r=challenge([make(1,e,profit=-2200)],[e],BASE,BASE+timedelta(days=1),'source')
        self.assertEqual(r['breach_reason'],'daily')

    def test_trade_across_horizon_not_removed(self):
        e=BASE+timedelta(minutes=1)
        r=challenge([make(1,e,duration=100)],[e],BASE,BASE+timedelta(seconds=65),'source')
        self.assertEqual(r['counts']['opened'],1)
        self.assertEqual(r['open_positions'],1)

if __name__=='__main__':unittest.main()
