import unittest
import numpy as np
import pandas as pd
import run as e


def fixture(blocks=1, win=False, ambiguous=False, symbols=None, start_hour=0):
    symbols=symbols or ['BTCUSD']
    start=int(pd.Timestamp(f'2026-10-12 {start_hour:02d}:00',tz='UTC').timestamp())
    rows=[]
    for k in range(blocks):
        for j,price in enumerate([100.,78.,88.,89.]):
            i=4*k+j
            high,low,close=price,price,price
            if j==3:
                high=120. if win or ambiguous else 90.
                low=75. if not win or ambiguous else 80.
                close=100. if win else 88.
            rows.append([start+60*i,price,high,low,close,1.,10.])
    rows.append([e.END,100.,100.,100.,100.,1.,10.])
    data={s:np.array(rows,dtype=float) for s in symbols}
    spec=dict(trade_contract_size=1.,trade_tick_size=.01,point=.01,volume_min=.01,
              volume_step=.01,volume_max=200.,swap_mode=1,swap_long=-2.,swap_short=0.,swap_rollover3days=5)
    meta={'files':{s:{'specification':spec.copy()} for s in symbols}}
    return data,meta


class EngineTests(unittest.TestCase):
    def test_long_excursion_then_recovery(self):
        s=e.Event()
        self.assertIsNone(s.update(100,10));self.assertIsNone(s.update(78,10))
        self.assertIsNone(s.update(70,10));self.assertIsNone(s.update(79,10))
        self.assertEqual(s.update(80,10),(1,70))
        self.assertEqual(s.armed,0)

    def test_short_excursion_then_recovery(self):
        s=e.Event()
        for p in [100,121,130,121]:self.assertIsNone(s.update(p,10))
        self.assertEqual(s.update(120,10),(-1,130))

    def test_no_excursion_no_signal(self):
        s=e.Event()
        for p in [100,105,99,110,98]:self.assertIsNone(s.update(p,10))

    def test_wilder_seed_and_step(self):
        a=e.wilder(np.r_[np.arange(1,15),28.])
        self.assertTrue(np.isnan(a[12]));self.assertEqual(a[13],7.5)
        self.assertAlmostEqual(a[14],(7.5*13+28)/14)

    def test_signal_next_open_not_signal_close(self):
        data,meta=fixture();r=e.simulate(data,meta,['BTCUSD'],'2026-10-12')
        self.assertEqual(len(r['trades']),1)
        t=r['trades'][0]
        self.assertEqual(t['entry'],90.) # 89 bid + 1 spread
        self.assertEqual(t['signal_extreme'],78.)
        self.assertEqual(t['stop'],77.99)
        self.assertEqual(t['entry_epoch'],int(data['BTCUSD'][3,0]))
        self.assertLessEqual(t['initial_risk_usd'],50)

    def test_four_entries_and_risk_budget(self):
        data,meta=fixture(blocks=6);r=e.simulate(data,meta,['BTCUSD'],'2026-10-12')
        self.assertEqual(len(r['trades']),4)
        self.assertGreater(r['summary']['skipped_signals']['four entries per day'],0)
        self.assertLessEqual(sum(t['initial_risk_usd'] for t in r['trades']),200)

    def test_both_levels_stop_first_and_alternative(self):
        data,meta=fixture(ambiguous=True)
        a=e.simulate(data,meta,['BTCUSD'],'2026-10-12')
        b=e.simulate(data,meta,['BTCUSD'],'2026-10-12',target_first=True)
        self.assertAlmostEqual(a['trades'][0]['net_r'],-1)
        self.assertAlmostEqual(b['trades'][0]['net_r'],1.5,places=2)
        self.assertTrue(a['trades'][0]['ambiguous'])

    def test_concurrent_entry_sizes_do_not_use_future_winner(self):
        data,meta=fixture(win=True,symbols=['BTCUSD','XAUUSD'])
        r=e.simulate(data,meta,['BTCUSD','XAUUSD'],'2026-10-12')
        self.assertEqual(len(r['trades']),2)
        self.assertEqual([t['entry_balance'] for t in r['trades']],[10000.,10000.])
        self.assertEqual(r['trades'][0]['lots'],r['trades'][1]['lots'])

    def test_long_stop_gap_is_adverse(self):
        p=dict(side=1,stop=90.,target=115.)
        b=np.array([0,85,89,80,83,1,10])
        self.assertEqual(e.opening_exit(p,b),(85.,'SL gap',False))

    def test_short_uses_ask_not_bid(self):
        p=dict(side=-1,stop=110.,target=85.)
        b=np.array([0,109.5,109.5,109.,109.2,1,10])
        self.assertEqual(e.opening_exit(p,b),(110.5,'SL gap',False))

    def test_tp_gap_not_optimistically_slipped(self):
        p=dict(side=1,stop=90.,target=115.)
        self.assertEqual(e.opening_exit(p,np.array([0,120,125,118,121,1,10])),(115.,'TP gap',False))

    def test_stale_pending_is_not_filled_after_holiday_gap(self):
        data,meta=fixture();data['BTCUSD'][3,0]+=600
        r=e.simulate(data,meta,['BTCUSD'],'2026-10-12')
        self.assertEqual(len(r['trades']),0)
        self.assertEqual(r['summary']['skipped_signals']['stale next quote'],1)

    def test_financing_and_end_close_reconcile(self):
        data,meta=fixture(start_hour=20)
        a=data['BTCUSD']
        a[:,0]+=55*60;a[-1,0]=e.END
        a[3,2:5]=[91,89,90] # Open trade survives.
        extra=np.array([[int(pd.Timestamp('2026-10-12 21:01',tz='UTC').timestamp()),90,91,89,90,1,10]])
        data['BTCUSD']=np.concatenate([a[:-1],extra,a[-1:]])
        r=e.simulate(data,meta,['BTCUSD'],'2026-10-12',stress=True)
        t=r['trades'][0]
        self.assertEqual(t['rollovers'],1)
        self.assertAlmostEqual(t['swap_usd'],-2*.01*t['lots'])
        self.assertAlmostEqual(r['summary']['final_balance_usd'],10000+sum(t['net_usd'] for t in r['trades']))


if __name__=='__main__':unittest.main()
