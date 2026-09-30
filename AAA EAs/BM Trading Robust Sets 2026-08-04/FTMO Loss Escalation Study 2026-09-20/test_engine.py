import unittest
from engine import replay,DAY,RISK
from run_study import old_engine,parity

START=1783296000.
def trade(i,net=100,**kw):
    row=dict(key='gold',symbol='XAUUSD',op=START+i*DAY+3600,cl=START+i*DAY+3700,
             news=False,unit_risk=1000.,unit_gross=net+7,unit_comm=-7.,unit_swap=0.,
             open_price=1000.,close_price=1001.,side='Long')
    row.update(kw);return row

class Checks(unittest.TestCase):
    def test_flat_parity(self):
        rr=[trade(i,v) for i,v in enumerate([-100,100,0,-100])]
        parity(old_engine().replay(rr,[],START,START+5*DAY,challenge=False,detail=True),
               replay(rr,[],START,START+5*DAY,challenge=False,detail=True))
    def test_multiply_net_losses_and_reset(self):
        rr=[trade(i,v) for i,v in enumerate([-100,-100,200,-100])]
        r=replay(rr,[],START,START+5*DAY,base_risk=50,risk_profile='loss_1_5x',challenge=False,detail=True)
        self.assertEqual([x['requested_risk'] for x in r['log']],[50,75,112.5,50])
    def test_zero_keeps_state(self):
        rr=[trade(i,v) for i,v in enumerate([-100,0,100])]
        r=replay(rr,[],START,START+4*DAY,base_risk=50,risk_profile='loss_1_5x',challenge=False,detail=True)
        self.assertEqual([x['requested_risk'] for x in r['log']],[50,75,75])
    def test_blocked_risk_does_not_reset_or_clip(self):
        rr=[trade(i,-100) for i in range(40)]
        r=replay(rr,[],START,START+42*DAY,risk_profile='loss_1_5x',detail=True)
        self.assertEqual(r['trades'],2)
        self.assertTrue(r['inactive'])
        self.assertFalse(r['breach'])
        self.assertAlmostEqual(r['rejections'][0]['requested_risk_per_side'],RISK*2.25)
        self.assertGreater(r['counts']['escalated_rejections'],0)
    def test_future_outcomes_do_not_change_current_order(self):
        a=replay([trade(0,-100),trade(1,200)],[],START,START+3*DAY,detail=True,risk_profile='loss_1_5x')
        b=replay([trade(0,-100),trade(1,-200)],[],START,START+3*DAY,detail=True,risk_profile='loss_1_5x')
        self.assertEqual([r['lots'] for r in a['log']],[r['lots'] for r in b['log']])
    def test_portfolio_counter_crosses_eas(self):
        rr=[trade(0,-100,key='A'),trade(1,200,key='B'),trade(2,100,key='A')]
        r=replay(rr,[],START,START+4*DAY,detail=True,risk_profile='loss_1_5x')
        self.assertEqual([x['risk_factor'] for x in r['log']],[1,1.5,1])
    def test_pending_news_size_is_frozen(self):
        p=dict(key='news',symbol='XAUUSD',op=START+2*DAY+3500,epoch=START+2*DAY+3590,until=START+2*DAY+3900,buy=1001,sell=999,sl=2.)
        rr=[trade(0,-100),trade(1,-100),trade(2,200,key='news',news=True,event=p['epoch'],unit_risk=200),
            trade(2,100,key='news',news=True,event=p['epoch'],unit_risk=200,op=START+2*DAY+3800,cl=START+2*DAY+3850,side='Short'),trade(3,100)]
        r=replay(rr,[p],START,START+5*DAY,detail=True,risk_profile='loss_1_5x',news_risk=10)
        self.assertEqual([x['risk_factor'] for x in r['log']],[1,1.5,2.25,2.25,1])
        self.assertEqual(r['trades'],5)
    def test_phase_transition_resets_counter(self):
        rr=[trade(0,10),trade(1,10),trade(2,14000),trade(3,-100),trade(8,10)]
        r=replay(rr,[],START,START+10*DAY,detail=True,risk_profile='loss_1_5x')
        self.assertEqual(r['passes'][0]['trading_days'],4)
        self.assertEqual(r['log'][-1]['phase'],2)
        self.assertEqual(r['log'][-1]['risk_factor'],1)

if __name__=='__main__':unittest.main()
