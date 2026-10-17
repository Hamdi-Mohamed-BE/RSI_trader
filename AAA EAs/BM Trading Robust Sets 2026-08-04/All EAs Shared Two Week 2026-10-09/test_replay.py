"""Research-only timing/risk tests. No MT5 or live-account calls."""
import unittest
import publish as p

def row(key,op,cl,r=1.,**extras):
    return dict(key=key,symbol='XAUUSD',news=key.startswith('news-pulse-'),op=p.epoch(p.START)+op,cl=p.epoch(p.START)+cl,
        native_position_id=op,unit_risk=100.,unit_gross=100.*r,unit_comm=0.,unit_swap=0.,
        open_price=4000.,close_price=4001.,initial_sl=3999.,initial_tp=4001.,side='Long',
        lane=key,partial=False,exit_legs=1,exit_comments=[''],risk_reference='fixture',risk_weight=1.,**extras)

class ReplayTests(unittest.TestCase):
    def test_closed_balance_compounds_at_entry(self):
        trades,receipts,_=p.detailed_replay([row('a',1,10),row('b',20,30)])
        self.assertAlmostEqual(receipts[0]['initial_risk_cash'],100)
        self.assertAlmostEqual(receipts[1]['initial_risk_cash'],101)
        self.assertAlmostEqual(sum(t['net_profit'] for t in trades),201)

    def test_no_future_profit_in_entry_size(self):
        _,receipts,_=p.detailed_replay([row('a',1,20,r=5),row('b',2,30)])
        self.assertEqual([r['initial_risk_cash'] for r in receipts],[100,100])

    def test_news_per_order_budget(self):
        _,receipts,_=p.detailed_replay([row('news-pulse-xau',1,10),row('news-pulse-xag',2,11)])
        self.assertEqual([r['initial_risk_cash'] for r in receipts],[10,10])

    def test_nasdaq_existing_multiplier_and_diagnostic(self):
        _,main,_=p.detailed_replay([row('nasdaq-5m-candle-momentum',1,10)])
        _,diagnostic,_=p.detailed_replay([row('nasdaq-5m-candle-momentum',1,10)],False)
        self.assertAlmostEqual(main[0]['effective_percent'],.25)
        self.assertAlmostEqual(diagnostic[0]['effective_percent'],1)

    def test_daily_gate_normal_only_in_existing_model(self):
        _,receipts,info=p.detailed_replay([row('a',1,10,-5),row('b',20,30),row('news-pulse-xau',21,31)])
        self.assertFalse(receipts[1]['admitted'])
        self.assertTrue(receipts[2]['admitted'])
        self.assertEqual(info['skipped_entries'],1)

    def test_loss_streak_risk_reduction(self):
        _,receipts,_=p.detailed_replay([row('a',1,2,-1),row('a',3,4,-1),row('a',5,6,-1),row('a',7,8,-1)])
        self.assertEqual(receipts[-1]['effective_percent'],.5)

    def test_insufficient_period_sharpe_is_missing(self):
        result=p.scenario([row('a',1,2)],True)
        self.assertIsNone(result['stats']['sharpe_ratio'])
        self.assertEqual(len(result['daily']),14)

if __name__=='__main__':unittest.main()
