import unittest
from pathlib import Path
import sys
import numpy as np
import engine
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Daily Equity Controls Audit 2026-09-29'))
from test_simulate import Controls

class RiskTests(Controls):
    def execute(self,args,**kw):
        opt=dict(ftmo=False,loss=0.,target=0.,cap=0.,stress=False,compound=False,lifecycle=False)
        opt.update(kw)
        v,l,_,_=engine.run(*args,**opt)
        return dict(zip(engine.FIELDS,v)),l
    def test_fixed_risk_triples_notional(self):
        a=self.fixture([0],[2],[100,102,104],[25])
        base,bl=self.execute(a)
        high,hl=self.execute(a,fixed_risk=150.)
        self.assertAlmostEqual(hl[0,3],3*bl[0,3])
        self.assertAlmostEqual(hl[0,5],150.)
        self.assertAlmostEqual(high['balance']-10000,3*(base['balance']-10000))
    def test_current_equity_risk_recalculated(self):
        a=self.fixture([0,2],[1,3],[100]*5,[1000,10])
        m,l=self.execute(a,compound=True,fixed_risk=150.,risk_fraction=.015)
        self.assertEqual(l[0,5],150)
        self.assertAlmostEqual(l[1,5],195)
    def test_minlot_newly_admitted(self):
        a=list(self.fixture([0],[2],[100]*4,[10]))
        a[0][0,4]=100.;a[4][:,2:6]=1.
        base,bl=self.execute(a)
        high,hl=self.execute(a,fixed_risk=150.)
        self.assertEqual(base['blocked_lot'],1)
        self.assertEqual(high['blocked_lot'],0)
        self.assertEqual(hl[0,5],100.)
        self.assertLessEqual(hl[0,5],150.)
    def test_5pct_stop_does_not_avoid_ftmo_failure(self):
        a=self.fixture([0]*2,[9]*2,[100,10,10,10])
        m,l=self.execute(a,ftmo=True,fixed_risk=150.,loss=500.,target=800.)
        self.assertEqual(m['first_ftmo_breach_minute'],1)
        self.assertEqual(m['forced_closes'],0)
        self.assertAlmostEqual(m['ending_equity'],9460)
    def test_exact_limit_then_delayed_close_fails(self):
        a=self.fixture([0],[9],[100,100-500/3,100-510/3])
        m,l=self.execute(a,ftmo=True,fixed_risk=150.,loss=500.,target=800.)
        self.assertEqual(m['loss_stop_days'],1)
        self.assertEqual(m['first_ftmo_breach_minute'],2)
    def test_buffer_can_close_before_limit(self):
        a=self.fixture([0],[9],[100,100-420/3,100-430/3,100-540/3])
        m,l=self.execute(a,ftmo=True,fixed_risk=150.,loss=400.,target=800.)
        self.assertEqual(m['first_ftmo_breach_minute'],-1)
        self.assertEqual(m['forced_closes'],1)
        self.assertAlmostEqual(m['balance'],9570)
    def test_buffer_is_not_gap_guarantee(self):
        a=self.fixture([0],[9],[100,100-420/3,100-540/3])
        m,l=self.execute(a,ftmo=True,fixed_risk=150.,loss=400.,target=800.)
        self.assertEqual(m['first_ftmo_breach_minute'],2)

if __name__=='__main__':unittest.main(verbosity=2)
