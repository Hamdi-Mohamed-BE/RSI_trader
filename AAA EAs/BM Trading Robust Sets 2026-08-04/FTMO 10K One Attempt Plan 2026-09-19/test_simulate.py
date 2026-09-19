import unittest
from datetime import timedelta
from simulate import dt, events_for, replay, rollover_units, business_days

BASE=dt('2026-01-05T08:00:00+00:00')

def trade(i, day=0, profit=100, duration=1, risk_per_lot=1000):
    op=BASE+timedelta(days=day)
    return dict(uid=str(i),key='test/standard',symbol='USTEC',op=op,cl=op+timedelta(hours=duration),
                news=False,side='Long',volume=1,gross_profit=profit,commission=-1,swap=0,
                risk_per_lot=risk_per_lot,open_price=15000,carry_units=0)

class ReplayTests(unittest.TestCase):
    def test_trade_crossing_horizon_is_admitted_not_dropped(self):
        r=trade(1,duration=100)
        result=replay([r],BASE,BASE+timedelta(days=1))
        self.assertEqual(result['counts']['opened'],1)
        self.assertEqual(result['open_positions'],1)
        self.assertEqual(result['counts'].get('closed',0),0)

    def test_minimum_lot_never_forced_above_budget(self):
        r=trade(1,risk_per_lot=100000)
        result=replay([r],BASE,BASE+timedelta(days=1))
        self.assertEqual(result['counts']['minimum_lot'],1)
        self.assertEqual(result['counts'].get('opened',0),0)

    def test_four_entry_days_not_four_trades(self):
        rows=[]
        for i in range(4):
            r=trade(i,profit=12000,duration=.1)
            r['op']+=timedelta(hours=i);r['cl']+=timedelta(hours=i)
            rows.append(r)
        result=replay(rows,BASE,BASE+timedelta(days=2),severity='source')
        self.assertGreater(result['balance'],11000)
        self.assertIsNone(result['phase1_day'])

    def test_phase_waits_and_funded_reward_delay(self):
        rows=[trade(i,day=i,profit=10000,duration=.1) for i in range(70)]
        result=replay(rows,BASE,BASE+timedelta(days=70),severity='source',detailed=True)
        self.assertEqual(len(result['phases']),2)
        self.assertTrue(all(p['entry_days']>=4 for p in result['phases']))
        funded_op=min(t['op'] for t in result['trades'] if t['phase']==3)
        self.assertGreaterEqual(result['payout_day'],(funded_op-BASE).total_seconds()/86400+14+4)
        self.assertGreaterEqual(result['payout'],100)

    def test_daily_entry_limit(self):
        rows=[]
        for i in range(8):
            r=trade(i,profit=2,duration=.01)
            r['op']+=timedelta(hours=i);r['cl']+=timedelta(hours=i);rows.append(r)
        result=replay(rows,BASE,BASE+timedelta(days=1),severity='source')
        self.assertEqual(result['counts']['opened'],4)

    def test_three_losses_stop_further_entries(self):
        rows=[]
        for i in range(8):
            r=trade(i,profit=-100,duration=.01)
            r['op']+=timedelta(hours=i);r['cl']+=timedelta(hours=i);rows.append(r)
        result=replay(rows,BASE,BASE+timedelta(days=1),severity='source')
        self.assertEqual(result['counts']['opened'],3)

    def test_inactivity_is_not_free_waiting(self):
        result=replay([trade(1)],BASE,BASE+timedelta(days=60),severity='source')
        self.assertEqual(result['inactivity_day'],30)
        self.assertIsNone(result['funded_day'])

    def test_prague_midnight_dst(self):
        for s,expected in [('2026-06-01T12:00:00Z','2026-06-01T22:00:00+00:00'),
                           ('2026-01-05T12:00:00Z','2026-01-05T23:00:00+00:00')]:
            start=dt(s)
            resets=[t.isoformat() for t,kind,_,_ in events_for([],start,start+timedelta(days=1)) if kind==0]
            self.assertIn(expected,resets)

    def test_rollover_triple(self):
        self.assertEqual(rollover_units(dt('2026-01-07T12:00:00Z'),dt('2026-01-08T12:00:00Z'),2),3)
        self.assertEqual(business_days(dt('2026-01-09T12:00:00Z'),2).date().isoformat(),'2026-01-13')

class NewsBasketTests(unittest.TestCase):
    def news(self, symbol, side, release, seconds=2, profit=100):
        r=trade(symbol+side,profit=profit,risk_per_lot=400,duration=.001)
        r.update(news=True,symbol=symbol,side=side,news_event_utc=release.isoformat(),
                 key='news-pulse-'+('xau' if symbol=='XAUUSD' else 'xag')+'/standard',
                 op=release+timedelta(seconds=seconds),cl=release+timedelta(seconds=seconds+2),
                 open_price=4348 if symbol=='XAUUSD' else 64.5)
        return r

    def test_no_fill_event_still_reserves_both_assets(self):
        release=BASE+timedelta(minutes=1)
        result=replay([],BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.25,'XAGUSD':.25},news_calendar=[release])
        self.assertEqual(result['counts']['news_events_admitted'],1)
        self.assertAlmostEqual(result['max_open_envelope'],2*(.04*607+.03*650))
        self.assertGreater(result['max_margin'],4000)
        self.assertEqual(result['counts'].get('opened',0),0)

    def test_reserved_opposite_kept_after_first_loss(self):
        release=BASE+timedelta(minutes=1)
        rows=[self.news('XAUUSD','Long',release,profit=-400),self.news('XAUUSD','Short',release,seconds=20,profit=800)]
        result=replay(rows,BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.25},news_calendar=[release],detailed=True)
        self.assertEqual(result['counts']['news_opened'],2)
        self.assertEqual([t['lots'] for t in result['trades']],[.04,.04])

    def test_basket_blocks_atomically_for_correlated_exposure(self):
        release=BASE+timedelta(minutes=1)
        ordinary=trade(1,duration=2)
        ordinary.update(symbol='XAUUSD',open_price=4348)
        result=replay([ordinary],BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.25,'XAGUSD':.25},news_calendar=[release])
        self.assertEqual(result['counts']['news_exposure_cap'],1)
        self.assertEqual(result['counts'].get('news_events_admitted',0),0)

    def test_only_one_release_per_day(self):
        releases=[BASE+timedelta(minutes=1),BASE+timedelta(hours=2)]
        result=replay([],BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.25},news_calendar=releases)
        self.assertEqual(result['counts']['news_events_admitted'],1)
        self.assertEqual(result['counts']['news_daily_stop'],1)

    def test_min_lot_blocks_whole_basket(self):
        result=replay([],BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.05,'XAGUSD':.05},news_calendar=[BASE+timedelta(minutes=1)])
        self.assertEqual(result['counts']['news_minimum_lot'],1)
        self.assertEqual(result['max_open_envelope'],0)

    def test_four_fills_one_event_are_counted(self):
        release=BASE+timedelta(minutes=1)
        rows=[self.news(sym,side,release,seconds=2+4*i) for i,(sym,side) in enumerate([
            ('XAUUSD','Long'),('XAUUSD','Short'),('XAGUSD','Long'),('XAGUSD','Short')])]
        result=replay(rows,BASE,BASE+timedelta(days=1),news_policy={'XAUUSD':.25,'XAGUSD':.25},news_calendar=[release])
        self.assertEqual(result['counts']['news_opened'],4)
        self.assertEqual(result['counts']['closed'],4)
        self.assertLessEqual(result['max_open_envelope'],100)

    def test_funded_news_risk_reduced(self):
        release=BASE+timedelta(minutes=1)
        result=replay([],BASE,BASE+timedelta(days=1),challenge=False,news_policy={'XAUUSD':.25,'XAGUSD':.25},news_calendar=[release])
        self.assertAlmostEqual(result['max_open_envelope'],2*(.02*607+.02*650))

if __name__=='__main__':unittest.main()
