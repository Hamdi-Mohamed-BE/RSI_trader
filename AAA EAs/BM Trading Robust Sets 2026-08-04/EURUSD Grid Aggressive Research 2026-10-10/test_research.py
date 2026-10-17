import unittest
import run as r
n=r.n

def tick(date,equity):return dict(epoch=int(n.pd.Timestamp(date,tz='UTC').timestamp()),equity=equity)

class TestHighRiskStudy(unittest.TestCase):
    def test_partial_months_not_counted_as_target_success(self):
        trace=[tick('2025-10-10',10000),tick('2025-10-31',12000),tick('2025-11-30',12000),tick('2025-12-09',12000)]
        m=r.monthly_metrics(trace,['2025.10.10','2025.12.10'],2000)
        self.assertEqual(m['full_months'],1);self.assertEqual(m['months_10pct'],0);self.assertEqual(m['average_monthly_pct'],0)

    def test_no_trade_month_kept(self):
        m=r.monthly_metrics([tick('2025-01-01',10000),tick('2025-03-31',11000)],['2025.01.01','2025.04.01'],1000)
        self.assertEqual(m['full_months'],3);self.assertEqual(m['monthly'][1]['return_pct'],0)

    def test_floating_loss_counts_without_closed_loss(self):
        m=r.monthly_metrics([tick('2025-01-01',10000),tick('2025-01-31',5000)],['2025.01.01','2025.02.01'],-5000)
        self.assertEqual(m['average_monthly_pct'],-50)

    def test_arithmetic_average_not_compounded_growth(self):
        trace=[tick('2025-01-01',10000),tick('2025-01-31',15000),tick('2025-02-28',10000)]
        m=r.monthly_metrics(trace,['2025.01.01','2025.03.01'],0)
        self.assertGreater(m['average_monthly_pct'],0);self.assertEqual(m['compounded_equivalent_monthly_pct'],0)

    def test_bankrupt_account_is_not_a_topup(self):
        trace=[tick('2025-01-01',10000),tick('2025-01-31',0),tick('2025-03-31',0)]
        m=r.monthly_metrics(trace,['2025.01.01','2025.04.01'],-10000)
        self.assertTrue(m['capital_depleted']);self.assertEqual(m['monthly'][-1]['equity_end'],0)
        self.assertIsNone(m['compounded_equivalent_monthly_pct'])

    def test_source_guard_lots_and_stops(self):
        s=(r.ROOT/'EURUSD Grid Aggressive Research.mq5').read_text()
        for x in ['!MQLInfoInteger(MQL_TESTER)','orders>=InpMaxOrders','projectedNet<=-budget',
                  'budget=startBalance*InpBasketLossPercent/100.0','InpMaxAgeHours*3600','CopyRates(_Symbol,InpSignalTF,1,3,r)']:
            self.assertIn(x,s)

if __name__=='__main__':unittest.main()
