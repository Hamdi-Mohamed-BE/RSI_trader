import unittest
from datetime import datetime, timedelta
import simulate as s


def row(n, at, pnl, duration=1, news=False, volume=.1, commission=0):
    slug = 'news-pulse-xau' if news else 'ema3'
    return dict(slug=slug, name=s.EAS[slug][0], news=news, uid=str(n), opened=at,
                closed=at+timedelta(seconds=duration), source_risk=100., base_pct=1.,
                source_balance=10000., volume=volume, symbol='XAUUSD', open_price=2000.,
                gross_profit=pnl, commission=commission, swap=0., net_profit=pnl+commission)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2024, 1, 1, tzinfo=s.UTC)
        self.end = datetime(2024, 4, 1, tzinfo=s.PRAGUE).astimezone(s.UTC)

    def test_same_second_sources_do_not_leave_positions_open(self):
        r = s.replay(s.ROWS, s.START, s.END)
        self.assertEqual(r['open_at_stop'], 0)
        self.assertEqual(r['closed_trades'], sum(v for k,v in r['counters'].items() if k.startswith('accepted:')))

    def test_cash_and_commission_conservation(self):
        r = s.replay([row(1,self.start+timedelta(days=1),200,commission=-7)],self.start,self.end,stress=False)
        t = r['trades'][0]
        self.assertAlmostEqual(t['gross']+t['commission']+t['swap'],t['net'])
        self.assertAlmostEqual(100000+r['net']-r['distribution'],r['balance'])

    def test_deficit_is_recovered_before_payout(self):
        rows = [row(1,self.start+timedelta(days=1),-500),row(2,self.start+timedelta(days=36),300)]
        r = s.replay(rows,self.start,self.end,stress=False,buffer=0)
        self.assertLess(r['net'],0)
        self.assertEqual(r['payout'],0)

    def test_stop_is_terminal(self):
        rows = [row(1,self.start+timedelta(days=1),-5000,news=True),row(2,self.start+timedelta(days=5),5000,news=True)]
        r = s.replay(rows,self.start,self.end,stress=False)
        self.assertIsNotNone(r['breach'])
        self.assertEqual(r['closed_trades'],1)
        self.assertEqual(r['payout'],0)

    def test_shared_margin_blocks_second_position(self):
        at = self.start+timedelta(days=1)
        rows = [row(1,at,100,duration=60,volume=.8), row(2,at+timedelta(seconds=1),100,duration=60,volume=.8)]
        r = s.replay(rows,self.start,self.end,stress=False)
        self.assertEqual(r['closed_trades'],1)
        self.assertEqual(r['counters']['shared Swing margin reserve'],1)

    def test_four_distinct_days_not_four_trades(self):
        rows = [row(i,self.start+timedelta(hours=1,minutes=i),1000) for i in range(4)]
        r = s.replay(rows,self.start,self.end,stress=False,challenge=True)
        self.assertEqual(r['phases'],[])
        self.assertEqual(r['payout'],0)

    def test_news_bypasses_normal_daily_gate(self):
        at = self.start+timedelta(days=1)
        rows = [row(1,at,-400),row(2,at+timedelta(minutes=1),100),row(3,at+timedelta(minutes=2),100,news=True)]
        r = s.replay(rows,self.start,self.end,stress=False)
        self.assertEqual(r['counters']['normal daily entry stop'],1)
        self.assertEqual(r['counters']['accepted:news-pulse-xau'],1)

    def test_prague_dst_month_dates(self):
        self.assertEqual(s.month(datetime(2024,3,31,22,30,tzinfo=s.UTC)),'2024-04')
        self.assertEqual(s.month(datetime(2024,1,31,22,30,tzinfo=s.UTC)),'2024-01')


if __name__ == '__main__':
    unittest.main()
