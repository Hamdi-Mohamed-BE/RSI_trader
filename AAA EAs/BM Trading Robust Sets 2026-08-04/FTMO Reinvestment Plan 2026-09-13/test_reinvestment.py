import unittest
from datetime import datetime,timedelta
import reinvest as r
import engine as e


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=r.simulate(stress=True,envelope=True)

    def test_seed_is_fee_not_ten_thousand_cash(self):
        self.assertAlmostEqual(self.result['initial_external_cash'],117.06)

    def test_batch_respects_budget_and_requires_100k(self):
        sizes=r.batch(1100,400000)
        self.assertEqual(sum(sizes),130000)
        self.assertIn(100000,sizes)
        self.assertLessEqual(sum(r.fee(s)[2] for s in sizes),1100)
        self.assertEqual(r.batch(700,400000),[])

    def test_headroom(self):
        self.assertEqual(r.batch(1100,125000),[100000,25000])
        self.assertEqual(r.batch(1100,99000),[])

    def test_wallet_conservation(self):
        a=self.result
        self.assertAlmostEqual(a['initial_external_cash']+a['rewards_received']+a['fee_refunds_received']-a['fees_paid'],a['cash_final'])
        self.assertAlmostEqual(a['cash_final']-a['initial_external_cash'],a['net_real_cash_profit'])

    def test_month_and_year_reconcile(self):
        a=self.result
        for key,field in [('rewards','rewards_received'),('refunds','fee_refunds_received'),('fees_paid','fees_paid'),('net_cash','net_real_cash_profit')]:
            self.assertAlmostEqual(sum(m[key] for m in a['monthly']),a[field])
            self.assertAlmostEqual(sum(m[key] for m in a['yearly'].values()),a[field])

    def test_allocations_and_wallet_never_exceed_bounds(self):
        active={}
        for event in self.result['activity']:
            if event['kind']=='purchase':active[event['account']]=event['size']
            if event['kind']=='failed':active.pop(event['account'])
            self.assertLessEqual(sum(active.values()),400000)
            self.assertGreaterEqual(event['wallet_after'],0)

    def test_receipts_are_funded_and_delayed(self):
        for event in self.result['activity']:
            if event['kind']=='receipt':
                account=self.result['accounts'][event['account']-1]
                self.assertLess(e.dt(account['result']['funded_at']),e.dt(event['requested_at']))
                self.assertGreater(e.dt(event['at']),e.dt(event['requested_at']))

    def test_new_accounts_are_not_instantly_funded(self):
        for a in self.result['accounts']:
            if a['result']['funded_at']:
                self.assertGreater(e.dt(a['result']['funded_at']),e.dt(a['bought_at'])+timedelta(days=7))
                self.assertEqual(len(a['result']['phases']),2)

    def test_failures_are_correlated_not_independent_draws(self):
        failures=[x for x in self.result['activity'] if x['kind']=='failed']
        self.assertEqual(len({x['at'] for x in failures}),1)
        self.assertEqual(len(failures),7)

    def test_refund_once_per_account(self):
        refunds=[x['account'] for x in self.result['activity'] if x['kind']=='receipt' and x['refund']>0]
        self.assertEqual(len(refunds),len(set(refunds)))
        self.assertAlmostEqual(self.result['unrecovered_costs'],self.result['failed_unrecovered_fees']+self.result['fx_card_cost'])

    def test_small_account_lot_rounding(self):
        at=datetime(2024,1,2,tzinfo=e.UTC)
        row=dict(slug='ema3',name='EMA3 Safe',news=False,uid='test',opened=at,closed=at+timedelta(seconds=1),
                 source_risk=100.,base_pct=1.,source_balance=10000.,volume=.01,symbol='XAUUSD',open_price=2000.,
                 gross_profit=50.,commission=0.,swap=0.,net_profit=50.)
        p=e.replay([row],at,at+timedelta(days=1),account=10000,stress=False)
        self.assertEqual(p['trades'][0]['volume'],.01)
        self.assertEqual(p['trades'][0]['planned_risk'],100)

    def test_total_floor_scales_with_account(self):
        at=datetime(2024,1,2,tzinfo=e.UTC)
        row=dict(slug='ema3',name='EMA3 Safe',news=False,uid='test',opened=at,closed=at+timedelta(seconds=1),
                 source_risk=100.,base_pct=1.,source_balance=10000.,volume=.01,symbol='XAUUSD',open_price=2000.,
                 gross_profit=-1500.,commission=0.,swap=0.,net_profit=-1500.)
        p=e.replay([row],at,at+timedelta(days=1),account=10000,stress=False)
        self.assertIsNotNone(p['breach'])


if __name__=='__main__':unittest.main()
