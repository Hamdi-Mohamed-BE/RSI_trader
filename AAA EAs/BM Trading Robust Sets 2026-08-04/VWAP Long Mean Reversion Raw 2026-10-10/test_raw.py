import math, unittest
from pathlib import Path
import run as r

class RawVerification(unittest.TestCase):
    def test_declared_scope(self):
        p=r.n.read(r.ROOT/'PLAN.json')
        self.assertEqual(len(p['cases']),26)
        self.assertEqual(len(set(x['symbol'] for x in p['cases'])),13)
        self.assertEqual({x['input_settings']['InpRewardRisk'] for x in p['cases']},{'1.0'})
        self.assertEqual({x['input_settings']['InpDiscountATR'] for x in p['cases']},{'2.0'})
        self.assertFalse(p['optimization']);self.assertFalse(p['live_changes'])
    def test_source_causality_and_safety(self):
        s=(r.ROOT/'VWAP Mean Reversion Raw.mq5').read_text()
        for causal in ['CopyBuffer(atr_handle,0,1,1','session[i].time>last','bars[1].time+300!=current','MQLInfoInteger(MQL_TESTER)','MathFloor(']:
            self.assertIn(causal,s)
        self.assertNotIn('trade.Sell(',s)
        self.assertNotIn('PositionModify(',s)
    def test_native_ledger_and_audit(self):
        state=r.n.read(r.ROOT/'RUN_STATUS.json')
        for row in state['complete'].values():
            q=r.n.read(Path(row['path']))
            self.assertTrue(q['signal_audit_verified'])
            self.assertAlmostEqual(sum(t['net'] for t in q['trades']),q['native']['net_profit'],places=2)
            for t in q['trades']:
                s=t['signal'];self.assertEqual(t['side'],'Long')
                self.assertLessEqual(int(s['signal_close_epoch']),t['open_epoch'])
                self.assertGreaterEqual(float(s['discount_atr']),2-1e-7)
                self.assertAlmostEqual(t['net_r']*t['initial_risk_usd'],t['net'],places=5)
                requested=float(s['requested_entry']);stop=float(s['stop']);target=float(s['target'])
                self.assertLess(stop,requested);self.assertLess(requested,target)
                self.assertAlmostEqual(target-requested,requested-stop,places=7)
                self.assertAlmostEqual(float(s['reward_risk']),1,places=6)
    def test_sizing_quote_rounding(self):
        budget=100;step=.01;loss_per_lot=33
        lots=math.floor(budget/loss_per_lot/step)*step
        self.assertLessEqual(lots*loss_per_lot,budget)
        entry=20100.13;stop=20089.77;tick=.01
        target=round((entry+(entry-stop))/tick)*tick
        self.assertAlmostEqual((target-entry)/(entry-stop),1,places=8)
    def test_no_rule_drift(self):
        p=r.n.read(r.ROOT/'PLAN.json')
        for row in p['cases']:
            for file,digest in row['production_hashes'].items():self.assertEqual(r.n.sha(Path(file)),digest)
    def test_export_precision_bound(self):
        vwap=1.0201;close=1.02;atr=.0000300042
        discount=(vwap-close)/atr
        encoded_vwap=round(vwap,8);encoded_close=round(close,8);encoded_atr=round(atr,8);encoded_discount=round(discount,8)
        difference=abs((encoded_vwap-encoded_close)/encoded_atr-encoded_discount)
        bound=(1e-8+abs(encoded_discount)*5e-9)/encoded_atr+2e-8
        self.assertGreater(difference,1e-4)
        self.assertLessEqual(difference,bound)

if __name__=='__main__':unittest.main()
