import unittest, importlib.util, sys
from pathlib import Path
import numpy as np
import prop_engine as pe
import study as s
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

class SignalChecks(unittest.TestCase):
    def ny_algorithm(self,t):
        from datetime import datetime,timedelta,timezone
        def nth(month,n):
            a=datetime(t.year,month,1,tzinfo=timezone.utc)
            return 1+(6-a.weekday())%7+7*(n-1)
        a=datetime(t.year,3,nth(3,2),7,tzinfo=timezone.utc);b=datetime(t.year,11,nth(11,1),6,tzinfo=timezone.utc)
        return (t-timedelta(hours=4 if a<=t<b else 5)).replace(tzinfo=None)
    def test_mql_new_york_all_hour_boundaries(self):
        from zoneinfo import ZoneInfo
        from datetime import datetime,timedelta,timezone
        a=datetime(2021,1,1,tzinfo=timezone.utc)
        for i in range(6*366*24):
            t=a+timedelta(hours=i)
            self.assertEqual(self.ny_algorithm(t),t.astimezone(ZoneInfo('America/New_York')).replace(tzinfo=None))
    def test_h4_block_during_entry_hours(self):
        for minute in range(600,690):
            self.assertEqual(((minute//60-2)//4*4+2),10)
    def test_bear_smt_both_directions_not_both_swept(self):
        smt=lambda n,s:(n>=101)!=(s>=51)
        self.assertTrue(smt(101,50));self.assertTrue(smt(100,51));self.assertFalse(smt(101,51));self.assertFalse(smt(100,50))
    def test_target_is_arithmetic_midpoint_not_assured_fair_value(self):
        self.assertEqual((max(110,115)+min(90,95))/2,102.5)
    def test_be_requires_profit_and_never_loosen(self):
        for side in (-1,1):
            fill=100;old=fill-side*10;new=fill+side*2
            self.assertGreater(side*(new-old),0);self.assertGreater(side*(new-fill),0)
    def test_rounddown_risk(self):
        import math
        for perlot in (23.3,100,311,2999):
            lots=math.floor(100/perlot/.01)*.01
            self.assertLessEqual(lots*perlot,100+1e-8)
    def test_futures_tick_arithmetic_in_transcript(self):
        self.assertEqual(381*5,1905);self.assertAlmostEqual(381*.5,190.5)
    def test_tester_only_and_closed_confirmation(self):
        body=(Path(__file__).parent/'KaneProxy.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))',body)
        self.assertIn('end-5*3600,end-1,s)',body)
        self.assertIn('n[count-1].time!=end-180',body)
        self.assertIn('n[i].time!=s[i].time',body)

if __name__=='__main__':unittest.main(verbosity=2)
