"""Synthetic accounting tests, explicitly not trading-performance evidence."""
import unittest
import numpy as np
from simulate import run,FIELDS,clock
from datetime import datetime,timezone

class Controls(unittest.TestCase):
    def fixture(self,entries,exits,prices,gains=None):
        n=len(entries);end=len(prices)-1
        tr=np.zeros((n,14))
        for i,(op,cl) in enumerate(zip(entries,exits)):
            tr[i]=[op,cl,i,0,50.,100.,gains[i] if gains is not None else 0.,0.,0.,1.,0.,1.,100.,op*60]
        px=np.zeros((7,end+1,4));op=np.zeros((7,end+1,2));fresh=np.ones((7,end+1),bool)
        for s in range(7):
            px[s,:,0]=prices;px[s,:,2]=prices;px[s,:,3]=prices;op[s,:,0]=prices
        sp=np.zeros((7,10));sp[:,0]=1;sp[:,2:6]=.01
        days=np.ones(end+1,np.int64)
        return tr,px,op,fresh,sp,0,end,days
    def execute(self,args,**kw):
        opt=dict(ftmo=False,loss=0,target=0,cap=0,stress=False,compound=False,lifecycle=False)
        opt.update(kw)
        v,l,d,c=run(*args,**opt);return dict(zip(FIELDS,v)),l
    def test_native_cash_reconciliation(self):
        args=self.fixture([0],[2],[100,102,104,104],[25])
        m,l=self.execute(args)
        self.assertAlmostEqual(m['balance'],10025)
        self.assertAlmostEqual(l[:,4].sum(),m['balance']-10000)
    def test_open_risk_prevents_sixth_trade(self):
        args=self.fixture([0]*6,[9]*6,[100]*5)
        m,l=self.execute(args,cap=250)
        self.assertEqual(m['blocked_risk'],1)
        self.assertEqual(m['max_open_risk'],250)
        self.assertEqual(m['max_concurrent'],5)
    def test_floating_loss_closes_before_native_exit(self):
        args=self.fixture([0]*5,[9]*5,[100,60,50,50,50])
        m,l=self.execute(args,loss=200,target=400)
        self.assertEqual(m['loss_stop_days'],1)
        self.assertEqual(m['forced_closes'],5)
        self.assertTrue(np.all(l[:,2]==2))
        self.assertEqual(m['balance'],9750)
        self.assertEqual(m['max_loss_overshoot'],50)
    def test_floating_goal_underfills_at_next_open(self):
        args=self.fixture([0]*5,[9]*5,[100,180,150,150,150])
        m,l=self.execute(args,loss=200,target=400)
        self.assertEqual(m['goal_days'],1)
        self.assertEqual(m['balance'],10250)
        self.assertEqual(m['max_goal_underfill'],150)
    def test_stop_blocks_reentry_all_day(self):
        args=self.fixture([0]*5+[3],[9]*6,[100,60,50,100,100])
        m,l=self.execute(args,loss=200)
        self.assertEqual(m['blocked_day'],1)
    def test_next_day_unlocks(self):
        args=list(self.fixture([0]*5+[3],[9]*6,[100,60,50,100,100]))
        args[-1]=np.array([1,1,1,2,2],np.int64)
        m,l=self.execute(args,loss=200)
        self.assertEqual(m['blocked_day'],0)
        self.assertEqual(m['open_at_end'],1)
    def test_cap_is_not_daily_loss_stop(self):
        args=self.fixture([0]*5+[3]*5,[2]*5+[5]*5,[100]*7,[-60]*10)
        normal,_=self.execute(args,cap=250)
        ftmo,_=self.execute(args,cap=250,ftmo=True)
        self.assertEqual(normal['balance'],9400)
        self.assertEqual(normal['loss_stop_days'],0)
        self.assertEqual(normal['max_open_risk'],250)
        self.assertEqual(ftmo['first_ftmo_breach_minute'],5)
    def test_carry_crosses_midnight_balance_floor(self):
        args=list(self.fixture([0],[9],[100,50,0,0]))
        args[-1]=np.array([1,1,2,2],np.int64)
        m,l=self.execute(args,loss=75)
        self.assertEqual(m['loss_stop_days'],1)
        self.assertEqual(m['balance'],9900)
    def test_missing_quote_waits(self):
        args=list(self.fixture([0]*5,[9]*5,[100,60,50,40,40]))
        args[3][:,2]=False
        m,l=self.execute(args,loss=200)
        self.assertTrue(np.all(l[:,2]==3))
        self.assertEqual(m['balance'],9700)
    def test_pre_entry_extremes_not_counted(self):
        args=list(self.fixture([.0],[9],[100,100,100]))
        args[0][0,13]=30
        args[1][0,1,2]=-10000
        m,l=self.execute(args)
        self.assertEqual(m['adverse_ftmo_flag_minute'],-1)
    def test_commissions_in_equity(self):
        args=list(self.fixture([0],[3],[100]*5,[20]))
        args[0][0,7]=-4
        m,l=self.execute(args)
        self.assertEqual(m['balance'],10016)
        self.assertEqual(l[0,4],16)
    def test_prague_dst_midnight(self):
        def minute(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()/60)
        start=minute('2026-03-28T00:00:00');end=minute('2026-03-30T00:00:00')
        days=clock(start,end)
        changes=np.flatnonzero(np.diff(days))+1
        self.assertEqual(changes[1]-changes[0],23*60)
    def test_phase_requires_four_distinct_opening_days(self):
        args=list(self.fixture([0,2,4,6],[1,3,5,7],[100]*10,[1100,0,0,0]))
        args[-1]=np.array([1,1,2,2,3,3,4,4,5,5],np.int64)
        m,l=self.execute(args,ftmo=True,lifecycle=True)
        self.assertEqual(m['phase1_minute'],7)
        self.assertEqual(m['balance'],10000)
    def test_equity_risk_compounds_without_oversize(self):
        args=self.fixture([0,2],[1,3],[100]*5,[1000,10])
        m,l=self.execute(args,compound=True)
        self.assertEqual(l[0,5],50)
        self.assertAlmostEqual(l[1,5],55)
    def test_margin_rejects_unaffordable_position(self):
        args=list(self.fixture([0],[2],[100]*4))
        args[4][:,6]=100
        m,l=self.execute(args)
        self.assertEqual(m['blocked_margin'],1)
        self.assertEqual(m['trades'],0)
    def test_ftmo_checks_floating_not_just_balance(self):
        args=self.fixture([0]*5,[9]*5,[100,-10,-10])
        m,l=self.execute(args,ftmo=True)
        self.assertEqual(m['balance'],10000)
        self.assertEqual(m['first_ftmo_breach_minute'],1)
        self.assertEqual(m['ending_equity'],9450)

if __name__=='__main__':unittest.main(verbosity=2)
