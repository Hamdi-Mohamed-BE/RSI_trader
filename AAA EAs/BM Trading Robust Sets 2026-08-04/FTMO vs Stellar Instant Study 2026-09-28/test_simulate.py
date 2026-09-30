import unittest
import numpy as np
import simulate as s

class ModelChecks(unittest.TestCase):
    def setup_rows(self,orders):
        start=s.epoch(2026,9,28);rows=[];pc=[];offset=0
        for day,gross,riskunit in orders:
            op=start+day*s.DAY+600;length=2
            # Low notional USTEC unit used only in synthetic engine checks.
            rows.append([op,op+length,0,1,riskunit,100,gross,0,0,offset,length,1,0,0]);pc +=[0,gross];offset+=length
        return start,np.array(rows,dtype=float),np.array(pc,dtype=np.float32),np.minimum(np.array(pc,dtype=np.float32),0)
    def call(self,orders,cfg,h=60,**kwargs):
        st,tr,pc,pl=self.setup_rows(orders)
        r=s.invoke(tr,pc,pl,st,st+h*s.DAY,s.clocks(st,st+h*s.DAY),cfg,False,horizons=np.array([h]),**kwargs)
        return dict(zip(s.FIELDS,r[0][0])),r
    def test_cash_reconciliation_and_round_down(self):
        cfg=s.CONFIGS[1]
        row,res=self.call([(0,150,101),(1,-101,101)],cfg,lifecycle=False)
        self.assertAlmostEqual(10000+sum(res[3][:,4]),row['balance'],places=6)
        self.assertTrue(all(res[3][:,5]<=50))
        self.assertAlmostEqual(res[3][0,3],.49)
    def test_minimum_lot_never_upsize(self):
        row,res=self.call([(0,100,6000)],s.CONFIGS[1],lifecycle=False)
        self.assertEqual(row['trades'],0);self.assertEqual(res[2][0,0],1)
    def test_funding_phases_and_payout_is_not_daily_loss(self):
        orders=[(d,6010,1000) for d in range(4)]
        orders +=[(d,3010,1000) for d in range(8,12)]
        orders +=[(22,14010,1000)]
        row,_=self.call(orders,s.CONFIGS[2])
        self.assertGreaterEqual(row['phase1_minute'],3*s.DAY)
        self.assertGreaterEqual(row['phase2_minute'],11*s.DAY)
        self.assertGreater(row['funded_minute'],row['phase2_minute'])
        self.assertGreaterEqual(row['first_request_minute'],36*s.DAY)
        self.assertGreater(row['total_cash'],500)
        self.assertEqual(row['breach_minute'],-1)
        self.assertAlmostEqual(row['balance'],10000,places=6)
    def test_one_day_cannot_pass_ftmo(self):
        row,_=self.call([(0,30000,1000)],s.CONFIGS[2])
        self.assertEqual(row['phase1_minute'],-1)
    def test_instant_all_profit_withdrawal_can_breach(self):
        row,_=self.call([(0,40000,1000)],s.CONFIGS[6])
        self.assertGreater(row['total_cash'],200)
        self.assertGreaterEqual(row['breach_minute'],0)
        self.assertEqual(row['first_request_minute'],row['breach_minute'])
    def test_instant_retained_buffer_survives_same_trade(self):
        row,_=self.call([(0,40000,1000)],s.CONFIGS[5])
        self.assertEqual(row['breach_minute'],-1)
        self.assertAlmostEqual(row['balance'],5150,places=6)
    def test_no_future_trades_or_payout_without_profit(self):
        row,_=self.call([(50,-100,1000)],s.CONFIGS[5],h=30)
        self.assertEqual(row['trades'],0);self.assertEqual(row['first_request_minute'],-1)
    def test_prague_dst(self):
        a=s.epoch(2026,7,1);b=s.epoch(2026,1,1)
        self.assertNotEqual(s.clocks(a,a+s.DAY)[22*60,0],s.clocks(a,a+s.DAY)[0,0])
        self.assertEqual(s.clocks(b,b+s.DAY)[22*60,0],s.clocks(b,b+s.DAY)[0,0])
    def test_breach_absorbing(self):
        row,res=self.call([(0,-30000,1000),(5,40000,1000)],s.CONFIGS[2])
        self.assertGreaterEqual(row['breach_minute'],0)
        self.assertEqual(row['first_request_minute'],-1)
        self.assertEqual(sum(res[1]),1)
    def test_floating_loss_before_winning_exit_breaches(self):
        st,tr,pc,pl=self.setup_rows([(0,500,100)])
        pl[0]=-3000
        result=s.invoke(tr,pc,pl,st,st+30*s.DAY,s.clocks(st,st+30*s.DAY),s.CONFIGS[2],False,horizons=np.array([30]))
        row=dict(zip(s.FIELDS,result[0][0]))
        self.assertGreaterEqual(row['breach_minute'],0)
        self.assertEqual(row['trades'],0)
    def test_instant_floor_does_not_fall_after_loss(self):
        row,_=self.call([(0,10000,1000),(1,-1000,1000)],s.CONFIGS[4],lifecycle=False)
        self.assertAlmostEqual(row['ending_loss_floor'],4799.993,places=3)
        self.assertGreater(row['ending_loss_floor'],4700)
    def test_no_fee_recovery_claim_from_account_balance(self):
        row,_=self.call([(0,10000,1000)],s.CONFIGS[4],h=10)
        self.assertGreater(row['balance'],5000)
        self.assertEqual(row['total_cash'],0)
    def test_news_positive_profit_discount_only(self):
        st,tr,pc,pl=self.setup_rows([(0,1000,1000),(1,-1000,1000)])
        tr[:,12]=1
        result=s.invoke(tr,pc,pl,st,st+30*s.DAY,s.clocks(st,st+30*s.DAY),s.CONFIGS[4],False,lifecycle=False,horizons=np.array([30]))
        self.assertAlmostEqual(result[3][0,4],(1000-.7)*.01*.4,places=6)
        self.assertAlmostEqual(result[3][1,4],(-1000-.7)*.01,places=6)

if __name__=='__main__':unittest.main(verbosity=2)
