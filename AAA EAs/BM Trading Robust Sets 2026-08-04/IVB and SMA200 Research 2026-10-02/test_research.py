import unittest
import numpy as np
import pandas as pd
from sma200 import states,backtest,load,ROOT
from ivb_rules import IVB
class Tests(unittest.TestCase):
 def test_ivb_threshold_range_one_trade(self):
  b=IVB()
  for m in [35,40,45,50,55]:self.assertIsNone(b.step(f'2026-07-01T12:{m}:00Z',100,90,99,100,50))
  self.assertIsNone(b.step('2026-07-01T13:00:00Z',102,91,99,100,0))
  self.assertIsNone(b.step('2026-07-01T13:05:00Z',103,100,103,199,0))
  x=b.step('2026-07-01T13:10:00Z',105,102,104,210,10)
  self.assertEqual(x['initial_sl'],90);self.assertEqual(x['initial_tp'],118);self.assertEqual(x['contracts'],1)
  self.assertIsNone(b.step('2026-07-01T13:15:00Z',106,103,105,300,0))
 def test_ivb_source_boundary_hazard(self):
  b=IVB();b.step('2026-07-01T12:35:00Z',100,90,99,0,0)
  x=b.step('2026-07-01T18:00:00Z',103,100,102,200,0);self.assertTrue(x['entry_at_eod_hazard'])
 def test_ivb_ohlcv_never_fake_delta(self):
  from ivb_rules import validate_export
  with self.assertRaises(AssertionError):validate_export(pd.DataFrame({'close':[100]}))
 def test_sma_warmup_equality(self):
  d=pd.DataFrame({'adj_close':[2.,2.,3.,1.],'sma':[np.nan,2.,2.,1.]})
  self.assertEqual(list(states(d)),[False,False,True,True])
 def test_next_open_causal(self):
  idx=pd.date_range('2025-01-01',periods=4,freq='B');d=pd.DataFrame({'adjusted_open':[100.,110.,120.,130.],'adj_close':[105.,115.,90.,140.],'sma':[100.,100.,100.,100.]},index=idx)
  s,e,t=backtest(d,idx[0],end=idx[-1]+pd.Timedelta(days=1));self.assertEqual(t.iloc[0].entry_date,idx[1]);self.assertEqual(t.iloc[0].exit_date,idx[3]);self.assertAlmostEqual(s['final_marked_equity'],10000*130/110)
 def test_data_warmup_no_preinception(self):
  d=load('TQQQ');self.assertGreaterEqual(d.index[0],pd.Timestamp('2010-02-09'));self.assertEqual(d.sma.iloc[:199].isna().sum(),199)
 def test_recurrence_independent(self):
  for symbol in ['QQQ','TQQQ']:
   d=load(symbol);s,eq,t=backtest(d,pd.Timestamp('2010-10-02'));signal=states(d).shift(1,fill_value=False);z=d.loc[eq.index]
   # Independent fractional-allocation recurrence, without using trade-ledger code.
   capital=10000.;was=False;prevclose=None
   for date,x in z.iterrows():
    hold=bool(signal.loc[date])
    if prevclose is not None and was:capital*=x.adjusted_open/prevclose
    if hold:capital*=x.adj_close/x.adjusted_open
    self.assertAlmostEqual(capital,float(eq.loc[date,'equity']),places=6)
    prevclose=x.adj_close;was=hold
if __name__=='__main__':unittest.main()
