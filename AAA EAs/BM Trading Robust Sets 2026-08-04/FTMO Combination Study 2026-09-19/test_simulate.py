"""Deterministic safety/accounting regression checks; no MT5 connection."""
import unittest
from datetime import datetime,timezone
from simulate import replay,rounded,margin,entry_charge,business,PRAGUE,RISK
from prepare import costs,DAY

START=datetime(2026,7,6,tzinfo=timezone.utc).timestamp()

def trade(i=0,**kw):
    r=dict(key=f'test-{i}',symbol='XAUUSD',op=START+3600+i*120,cl=START+3660+i*120,
           news=False,unit_risk=1000.,unit_gross=100.,unit_comm=-7.,unit_swap=0.,
           open_price=4000.,close_price=4001.,side='Long')
    r.update(kw);return r

def placement(**kw):
    p=dict(key='news',symbol='XAUUSD',op=START+3600,epoch=START+3605,until=START+7200,
           buy=4001.,sell=3999.,sl=2.)
    p.update(kw);return p

class Checks(unittest.TestCase):
    def test_round_up_and_minimum(self):
        self.assertEqual(rounded(.0001),.01)
        self.assertAlmostEqual(rounded(RISK/1000)*1000,80.)
        self.assertAlmostEqual(margin('XAUUSD',.05,4000),1333.3333333333333)

    def test_round_trip_costs_reconcile(self):
        r=trade(unit_swap=-12.)
        result=replay([r],[],START,START+DAY,challenge=False,detail=True)
        self.assertEqual(result['trades'],1)
        self.assertAlmostEqual(result['balance']-10000,result['log'][0]['net_profit'])
        self.assertAlmostEqual(result['balance']-10000,(100-7-12)*.08)

    def test_crypto_admission_does_not_see_exit_price(self):
        r=trade(symbol='ETHUSD',open_price=2000.,close_price=4000.)
        c=costs(r)[1];a=entry_charge(r,c,0)
        r['close_price']=10000.;b=entry_charge(r,costs(r)[1],0)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a,-6.5)

    def test_both_news_sides_require_margin_before_fill(self):
        p=placement()
        r=trade(key='news',news=True,event=p['epoch'],op=p['epoch']+1,cl=p['epoch']+2,unit_risk=200.)
        result=replay([r],[p],START,START+DAY,news_risk=RISK)
        self.assertEqual(result['trades'],0)
        self.assertEqual(result['counts']['news_margin_rejected'],1)

    def test_pending_sides_reserve_daily_entry_slots(self):
        rr=[trade(i,op=START+100+i*120,cl=START+160+i*120) for i in range(6)]
        result=replay(rr,[placement()],START,START+DAY,news_risk=10.)
        self.assertEqual(result['trades'],6)
        self.assertEqual(result['counts']['daily_trade_limit'],1)
        self.assertLessEqual(result['max_daily_entries'],7)

    def test_opposite_order_is_kept(self):
        p=placement()
        rr=[trade(key='news',news=True,event=p['epoch'],op=p['epoch']+j*120+1,
                  cl=p['epoch']+j*120+30,unit_risk=200.,side=side) for j,side in enumerate(('Long','Short'))]
        result=replay(rr,[p],START,START+DAY,news_risk=10.,detail=True)
        self.assertEqual(result['trades'],2)

    def test_four_trading_days_before_phase_pass(self):
        rr=[trade(i,op=START+i*DAY+3600,cl=START+i*DAY+3700,unit_gross=6257.) for i in range(4)]
        result=replay(rr,[],START,START+5*DAY,detail=True)
        self.assertEqual(result['passes'][0]['trading_days'],4)
        self.assertEqual(len(result['passes']),1)
        self.assertFalse(result['payout'])
        self.assertEqual(result['reward'],0)
        self.assertEqual(result['phase'],2)

    def test_prague_reset_is_dst_aware(self):
        summer=datetime(2026,7,6,tzinfo=PRAGUE).astimezone(timezone.utc)
        winter=datetime(2026,1,6,tzinfo=PRAGUE).astimezone(timezone.utc)
        self.assertEqual((summer.hour,winter.hour),(22,23))

    def test_review_wait_excludes_weekends(self):
        friday=datetime(2026,7,10,12,tzinfo=timezone.utc).timestamp()
        self.assertEqual(datetime.fromtimestamp(business(friday,2),timezone.utc).weekday(),1)

if __name__=='__main__':unittest.main()
