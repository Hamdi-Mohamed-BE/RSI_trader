import unittest
import numpy as np
import pandas as pd
from research import atr_wilder,bracket,signal_rows,simulate,streaks

def sample():
    n=35;idx=pd.bdate_range('2026-01-01',periods=n)
    d=pd.DataFrame({'open':100.,'high':100.5,'low':99.5,'close':100.,'v_close':20.,'v_low':19.,'v_mean':20.,'spike':False,'atr':2.},index=idx)
    return d

class ResearchTests(unittest.TestCase):
    def test_ambiguity_conservative(self):
        self.assertEqual(bracket(100,110,90,95,105),(95.,'stop',True))
    def test_gap_stop(self):
        self.assertEqual(bracket(90,92,85,95,105),(90.,'gap_stop',False))
    def test_gap_target_no_windfall(self):
        self.assertEqual(bracket(110,112,108,95,105),(105.,'gap_target',False))
    def test_atr_wilder(self):
        a=atr_wilder(np.array([2.,2.,4.,4.]),np.array([0.,0.,0.,0.]),np.array([1.,1.,2.,2.]),2)
        np.testing.assert_allclose(a[1:],[2.,3.,3.5])
    def test_signal_no_same_day(self):
        d=sample();d.iloc[22,d.columns.get_loc('spike')]=True;d.iloc[22,d.columns.get_loc('v_close')]=27;d.iloc[22,d.columns.get_loc('v_low')]=26
        d.iloc[23,d.columns.get_loc('v_close')]=24
        s=signal_rows(d);self.assertFalse(s[22]['signal']);self.assertTrue(s[23]['signal'])
        st,eq,t=simulate(d,d.index[21],d.index[-1]+pd.Timedelta(days=1))
        self.assertEqual(t.entry_date.iloc[0],str(d.index[24].date()))
        self.assertLessEqual(t.initial_risk.iloc[0],100)
    def test_arm_expires(self):
        d=sample();d.iloc[22,d.columns.get_loc('spike')]=True
        d.iloc[28,d.columns.get_loc('v_close')]=18
        self.assertFalse(any(x['signal'] for x in signal_rows(d)))
    def test_prefix_invariance(self):
        d=sample();d.iloc[22,d.columns.get_loc('spike')]=True;d.iloc[22,d.columns.get_loc('v_close')]=27;d.iloc[22,d.columns.get_loc('v_low')]=26;d.iloc[23,d.columns.get_loc('v_close')]=24
        self.assertEqual(signal_rows(d)[:26],signal_rows(d.iloc[:26]))
    def test_scheduled_exit_no_later_day_low(self):
        d=sample();schedule={22:1};d.iloc[23,d.columns.get_loc('low')]=1.
        schedule={22:2}
        st,eq,t=simulate(d,d.index[21],d.index[-1]+pd.Timedelta(days=1),schedule=schedule)
        self.assertEqual(t.exit_reason.iloc[0],'time');self.assertLess(st['assumed_path_intraday_dd_pct'],1)
    def test_cash_cap_and_floor(self):
        d=sample();d['atr']=.001
        st,eq,t=simulate(d,d.index[21],d.index[-1]+pd.Timedelta(days=1),schedule={22:1})
        self.assertEqual(t.qty.iloc[0],100);self.assertGreaterEqual(eq.cash.min(),0)
    def test_exact_control_horizon(self):
        for n in [1,2,5]:
            d=sample();st,eq,t=simulate(d,d.index[21],d.index[-1]+pd.Timedelta(days=1),schedule={22:n})
            self.assertEqual(t.held_sessions.iloc[0],n)
    def test_streaks(self):
        st=streaks([1,1,-1,-1,-1,0,1]);self.assertEqual(st['max_win_streak'],2);self.assertEqual(st['max_loss_streak'],3)

if __name__=='__main__':unittest.main()
