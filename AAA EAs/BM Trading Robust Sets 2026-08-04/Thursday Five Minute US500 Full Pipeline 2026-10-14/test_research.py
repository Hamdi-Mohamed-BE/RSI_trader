import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import research as r
def fixture(side=1):
    c=dict(id=0,weekday=3,entry_minute_et=610,hold_minutes=5,side=side)
    t=pd.date_range('2023-07-06T14:10:00Z',periods=6,freq='min')
    f=pd.DataFrame(dict(open=np.arange(100.,106.),high=np.arange(100.,106.)+1,low=np.arange(100.,106.)-1,close=np.arange(100.,106.)+.5,used_spread=[.8,.7,.6,.5,.4,.3]),index=t)
    return f,c
class Checks(unittest.TestCase):
    def test_long_ask_entry(self):
        f,c=fixture();p=r.panel(f,'2023-07-06','2023-07-07',[c]);self.assertAlmostEqual(p['net'][0,0],4.2)
    def test_short_ask_exit(self):
        f,c=fixture(-1);p=r.panel(f,'2023-07-06','2023-07-07',[c]);self.assertAlmostEqual(p['net'][0,0],-5.3)
    def test_future_closes_do_not_fill(self):
        f,c=fixture();a=r.panel(f,'2023-07-06','2023-07-07',[c]);f.close=999;f.high=999;f.low=-999;b=r.panel(f,'2023-07-06','2023-07-07',[c]);np.testing.assert_array_equal(a['net'],b['net'])
    def test_exit_bar_future_extreme_not_mae(self):
        f,c=fixture();a=r.records(f,c,'2023-07-06','2023-07-07');f.iloc[-1,f.columns.get_loc('low')]=-999;f.iloc[-1,f.columns.get_loc('high')]=999;b=r.records(f,c,'2023-07-06','2023-07-07');self.assertEqual(a,b)
    def test_missing_intermediate_minute_rejected(self):
        f,c=fixture();p=r.panel(f.drop(f.index[2]),'2023-07-06','2023-07-07',[c]);self.assertTrue(np.isnan(p['net'][0,0]));self.assertEqual(r.matrix_stats(p)['missing'][0],1)
    def test_missing_exit_rejected(self):
        f,c=fixture();p=r.panel(f.iloc[:-1],'2023-07-06','2023-07-07',[c]);self.assertTrue(np.isnan(p['net'][0,0]))
    def test_non_scheduled_days_are_real_zeros(self):
        f,c=fixture();p=r.panel(f,'2023-07-05','2023-07-07',[c]);self.assertEqual(p['net'][0,0],0);self.assertFalse(p['applicable'][0,0])
    def test_missing_scheduled_not_zero_sharpe(self):
        f,c=fixture();p=r.panel(f.iloc[:2],'2023-07-05','2023-07-07',[c]);self.assertEqual(np.isfinite(p['net'][:,0]).sum(),1)
    def test_cost_stress_only_scheduled(self):
        f,c=fixture();p=r.panel(f,'2023-07-05','2023-07-07',[c]);self.assertAlmostEqual(r.matrix_stats(p,.6)['net'][0],3.6)
    def test_grid_unique_includes_primary(self):
        self.assertEqual(len(r.CONFIGS),8500);self.assertEqual(r.CONFIGS[r.ORIGINAL]['entry_minute_et'],610)
    def test_neighbors_do_not_change_two_factors(self):
        c=r.CONFIGS[r.ORIGINAL]
        for j in r.neighbors(c):self.assertEqual(sum(c[k]!=r.CONFIGS[j][k] for k in r.KEYS),1)
    def test_dst_winter_and_summer(self):
        self.assertEqual(pd.Timestamp('2023-01-05 10:10',tz='America/New_York').tz_convert('UTC').hour,15)
        self.assertEqual(pd.Timestamp('2023-07-06 10:10',tz='America/New_York').tz_convert('UTC').hour,14)
    def test_oos_forbidden_without_freeze(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'R',Path(d)):
            with self.assertRaisesRegex(AssertionError,'before final freeze'):r.source('OOS')
    def test_oos_exact_twoyears(self):
        a,z=r.PROTO['oos'];self.assertEqual(pd.Timestamp(a)+pd.DateOffset(years=2),pd.Timestamp(z))
    def test_canonical_records_panel_agree(self):
        for side in [1,-1]:
            f,c=fixture(side);p=r.panel(f,'2023-07-06','2023-07-07',[c]);v=r.records(f,c,'2023-07-06','2023-07-07')[0]['net_points'];self.assertAlmostEqual(v,p['net'][0,0])
if __name__=='__main__':unittest.main()
