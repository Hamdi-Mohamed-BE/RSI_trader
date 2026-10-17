import unittest
import run as r

class TestGridAccounting(unittest.TestCase):
    def trade(self,magic,pid,side,net,opened,closed,comment='normal'):
        return dict(magic=magic,position_id=pid,side=side,net=net,open_epoch=opened,close_epoch=closed,
            exit_comments=[comment],volume=.01)

    def test_basket_not_individual_order_win_rate(self):
        trades=[self.trade(261010001,1,'Long',-20,0,100),self.trade(261010001,2,'Long',30,20,100)]
        baskets=r.basket_groups(trades,[dict(position_id=1,entry=1,reason=3),dict(position_id=2,entry=1,reason=3)])
        self.assertEqual(len(baskets),1);self.assertEqual(baskets[0]['net'],10)
        self.assertEqual(r.stats([b['net'] for b in baskets])['win_rate'],100)
        self.assertEqual(r.stats([t['net'] for t in trades])['win_rate'],50)

    def test_terminal_loss_included(self):
        trades=[self.trade(261010001,1,'Long',10,0,100),self.trade(261010002,2,'Short',-100,200,300,'end of test')]
        baskets=r.basket_groups(trades,[dict(position_id=1,entry=1,reason=3),dict(position_id=2,entry=1,reason=3)])
        self.assertEqual(baskets[-1]['reason'],'TEST_END')
        self.assertEqual(sum(b['net'] for b in baskets),-90)
        self.assertAlmostEqual(r.stats([b['net'] for b in baskets])['pf'],.1)

    def test_stopout_is_not_a_target_exit(self):
        ts=[self.trade(261010001,1,'Long',-100,0,100)]
        self.assertEqual(r.basket_groups(ts,[dict(position_id=1,entry=1,reason=6)])[0]['reason'],'STOPOUT')

    def test_streaks_include_terminal_loss(self):
        s=r.stats([10,10,10,-100]);self.assertEqual((s['win_streak'],s['loss_streak']),(3,1))

    def test_no_losses_pf_is_not_fabricated(self):
        self.assertIsNone(r.stats([10,12])['pf'])

    def test_source_causal_research_guard_and_no_stops(self):
        source=(r.ROOT/'EURUSD EMA Volume Grid Raw.mq5').read_text()
        for fragment in ['!MQLInfoInteger(MQL_TESTER)','CopyRates(_Symbol,InpSignalTF,1,3,r)',
                         'CopyBuffer(ema,0,1,1,e)','r[0].tick_volume<r[1].tick_volume','r[1].tick_volume<r[2].tick_volume',
                         'nearest+1e-7<InpGridPoints','InpLotIncrement*orders','trade.Buy(lots,_Symbol,0,0,0,comment)',
                         'nextSide=InpAlternateAfterBasket?-side:0']:
            self.assertIn(fragment,source)

if __name__=='__main__':unittest.main()
