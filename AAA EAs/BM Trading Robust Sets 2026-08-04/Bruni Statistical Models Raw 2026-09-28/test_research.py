import unittest, importlib.util, sys
from pathlib import Path
import numpy as np
import pandas as pd
import prop_engine as pe
import study as s

class StatisticalChecks(unittest.TestCase):
    def forecasts(self):return {k:np.array([[0.,1.,1.,1.]]) for k in ['XAUUSD','USTEC','USDJPY']}
    def rows(self,n=140):
        out=[]
        for i in range(n):
            # Tradable long enough apart; fixed risk per lot and existing cost fields.
            out.append([i*10,i*10+2,0,1,100,100,130 if i%3 else -100,0,0,0,2,1,0,0])
        return np.array(out,float)
    def test_future_outcomes_do_not_change_earlier_features(self):
        tr=self.rows();a,_=s.feature_table(tr,self.forecasts(),.005)
        tr[110:,6]*=-10;b,_=s.feature_table(tr,self.forecasts(),.005)
        np.testing.assert_array_equal(a[:111],b[:111])
    def test_same_minute_and_still_open_outcomes_unavailable(self):
        tr=self.rows(3);tr[0,1]=tr[1,0];tr[0,6]=-100
        a,d=s.feature_table(tr,self.forecasts(),.005)
        self.assertEqual(d[1]['prior_closed'],0);self.assertEqual(a[1,1],1)
        tr[0,1]=100;a,d=s.feature_table(tr,self.forecasts(),.005)
        self.assertEqual(d[2]['prior_closed'],1)
    def test_per_ea_not_pooled(self):
        tr=self.rows();tr[-1,2]=1;a,d=s.feature_table(tr,self.forecasts(),.005)
        self.assertEqual(d[-1]['prior_closed'],0);self.assertFalse(d[-1]['kelly_trained'])
    def test_minimum_training_and_caps(self):
        a,d=s.feature_table(self.rows(),self.forecasts(),.005)
        self.assertTrue((a[:100,2]==1).all());self.assertTrue((a[:,2]>=.5).all());self.assertTrue((a[:,2]<=1.25).all())
        self.assertTrue((a[:,5]==1).all())
    def test_no_due_win_after_seven_losses(self):
        tr=self.rows();tr[:,6]=-100;a,d=s.feature_table(tr,self.forecasts(),.005)
        self.assertTrue((a[:,5]==1).all())
    def test_garch_recursion_known_answer(self):
        e=np.array([-1.,1.]);p=np.array([.1,.2,.7]);_,v=s.variance_path(e,p)
        self.assertAlmostEqual(v,1.)
    def test_garch_prefix_and_current_close_invariance(self):
        rng=np.random.default_rng(57);f=pd.DataFrame({'time':pd.date_range('2022-01-01',periods=360,tz='UTC').astype('int64')//10**9,
            'close':100*np.exp(np.cumsum(rng.normal(0,.01,360)))})
        a,_=s.garch_forecasts(f);b,_=s.garch_forecasts(f.iloc[:330]);np.testing.assert_allclose(a[:len(b)],b,rtol=0,atol=0,equal_nan=True)
        changed=f.copy();changed.loc[330:,'close']*=1.7;c,_=s.garch_forecasts(changed)
        np.testing.assert_allclose(a[a[:,0]<=f.time[330]],c[c[:,0]<=f.time[330]],rtol=0,atol=0,equal_nan=True)
    def test_stated_arithmetic(self):
        self.assertAlmostEqual(2/6,1/3)
        p=.4;q=2/6;self.assertAlmostEqual(100*(p-q),6.66666666666667)
        self.assertNotEqual(100*(p-q),90)
    def test_reverse_net_is_not_negative_net(self):
        gross=np.array([1.,-1.,-.1]);cost=.2
        original=gross-cost;reverse=-gross-cost
        np.testing.assert_allclose(original+reverse,-2*cost)
    def test_pf_removing_best(self):
        st=s.stats([7000,3000,-5000],365);self.assertEqual(st['pf'],2);self.assertEqual(st['pf_without_best'],.6)

class PropChecks(unittest.TestCase):
    def setup_rows(self,orders,symbol=1):
        start=pe.epoch(2026,9,28);rows=[];pc=[]
        for day,gross,unitrisk in orders:
            op=start+day*1440+600;rows.append([op,op+2,0,symbol,unitrisk,100,gross,0,0,len(pc),2,1,0,0,1]);pc.extend([0.,gross])
        return start,np.array(rows,float),np.array(pc,np.float32),np.minimum(np.array(pc,np.float32),0)
    def call(self,orders,instant=False,symbol=1,edit=None,h=60,lifecycle=True):
        st,tr,pc,pl=self.setup_rows(orders,symbol)
        if edit:edit(tr,pc,pl)
        cfg=dict(capital=5000 if instant else 10000,risk=.0025 if instant else .005,firm='Instant' if instant else 'FTMO',existing=False,withdraw_all=False)
        rr=pe.invoke(tr,pc,pl,st,st+h*1440,pe.clocks(st,st+h*1440),cfg,False,lifecycle=lifecycle,horizons=np.array([h]))
        return dict(zip(pe.FIELDS,rr[0][0])),rr
    def test_cash_and_floor_lots(self):
        d,r=self.call([(0,150,101),(1,-101,101)],lifecycle=False)
        self.assertAlmostEqual(10000+sum(r[3][:,4]),d['balance']);self.assertAlmostEqual(r[3][0,3],.49)
    def test_ustec_minimum_no_upsize(self):
        d,r=self.call([(0,1000,1200)],lifecycle=False);self.assertEqual(d['trades'],0);self.assertEqual(r[2][0,0],1)
    def test_risk_multiplier(self):
        d,r=self.call([(0,150,100)],edit=lambda tr,pc,pl:tr.__setitem__((0,14),.5),lifecycle=False)
        self.assertEqual(r[3][0,3],.25)
    def test_phase1_four_days_and_phase2(self):
        orders=[(d,7000,1000) for d in range(4)]+[(d,3500,1000) for d in range(8,12)]+[(22,20000,1000)]
        d,r=self.call(orders);self.assertGreaterEqual(d['phase1_minute'],3*1440);self.assertGreaterEqual(d['phase2_minute'],11*1440)
        self.assertGreater(d['total_cash'],500);self.assertEqual(d['breach_minute'],-1)
    def test_one_day_cannot_pass(self):
        d,r=self.call([(0,30000,1000)]);self.assertEqual(d['phase1_minute'],-1)
    def test_floating_breach_before_winning_exit(self):
        d,r=self.call([(0,1000,100)],edit=lambda tr,pc,pl:pl.__setitem__(0,-3000))
        self.assertGreaterEqual(d['breach_minute'],0);self.assertEqual(d['trades'],0)
    def test_quickstrike_block_not_drawdown_breach(self):
        def edit(tr,pc,pl):tr[0,13]=1
        d,r=self.call([(0,8000,100)],instant=True,edit=edit)
        self.assertGreaterEqual(d['compliance_block_minute'],0);self.assertEqual(d['breach_minute'],-1);self.assertEqual(d['total_cash'],0)
    def test_instant_floor_and_retained_buffer(self):
        d,r=self.call([(0,8000,100)],instant=True)
        self.assertGreater(d['total_cash'],0);self.assertAlmostEqual(d['balance']-d['ending_loss_floor'],150)
        self.assertEqual(d['breach_minute'],-1)
    def test_dst(self):
        a=pe.epoch(2026,7,1);b=pe.epoch(2026,1,1)
        self.assertNotEqual(pe.clocks(a,a+1440)[1320,0],pe.clocks(a,a+1440)[0,0]);self.assertEqual(pe.clocks(b,b+1440)[1320,0],pe.clocks(b,b+1440)[0,0])
    def test_parity_with_prior_engine_above_minlot(self):
        path=s.SOURCE/'simulate.py';spec=importlib.util.spec_from_file_location('simulate',path);old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        st,tr,pc,pl=self.setup_rows([(0,150,100),(1,-100,100),(3,200,100)])
        args=(pc,pl,st,st+30*1440,pe.clocks(st,st+30*1440),10000.,.005,False,False,False,False,True,False,np.array([30]))
        a=pe.run(tr,*args);b=old.run(tr[:,:14].copy(),*args)
        np.testing.assert_allclose(a[0][:,:26],b[0],rtol=0,atol=0);np.testing.assert_array_equal(a[3],b[3])

if __name__=='__main__':unittest.main(verbosity=2)
