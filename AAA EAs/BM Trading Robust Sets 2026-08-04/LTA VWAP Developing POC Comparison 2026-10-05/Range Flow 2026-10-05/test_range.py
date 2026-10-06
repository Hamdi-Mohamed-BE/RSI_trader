import unittest,importlib.util
from pathlib import Path
import run as extension
R=Path(__file__).resolve().parent;P=R.parent
def state(latest,older):
 r=latest/older-1
 return 2 if r>.05 else 0 if r<-.05 else 1
def admits(mode,s,adx,hour_ready=True):
 return mode==0 or (s==1 and (mode==1 or (hour_ready and 0<=adx<20)))
class RangeTests(unittest.TestCase):
 def test_bull(self):self.assertEqual(state(106,100),2)
 def test_bear(self):self.assertEqual(state(94,100),0)
 def test_sideways(self):self.assertEqual(state(102,100),1)
 def test_range_combo(self):self.assertTrue(admits(2,1,19.9))
 def test_adx_equal_twenty_blocked(self):self.assertFalse(admits(2,1,20))
 def test_strong_local_trend_blocked(self):self.assertFalse(admits(2,1,30))
 def test_bull_blocked_even_low_adx(self):self.assertFalse(admits(2,2,10))
 def test_bear_blocked_even_low_adx(self):self.assertFalse(admits(2,0,10))
 def test_missing_adx_blocked(self):self.assertFalse(admits(2,1,-1))
 def test_uncompleted_h1_blocked(self):self.assertFalse(admits(2,1,12,False))
 def test_daily_ablation_does_not_use_adx(self):self.assertTrue(admits(1,1,30))
 def test_off_switch(self):self.assertTrue(admits(0,2,30))
 def test_dependencies_unchanged(self):
  for p in (R/'EA').glob('*.mqh'):self.assertEqual(p.read_bytes(),(P/'EA'/p.name).read_bytes())
 def test_closed_only_native_guard(self):
  s=(R/'EA/LTA Flow Research.mq5').read_text()
  for needle in ['CopyClose(_Symbol,PERIOD_D1,1,requested,closes)','CopyBuffer(rangeADX,0,1,1,values)',
   'h1+3600<=TimeCurrent()','rangeState==1','adx<InpRangeADXMax','if(!RangeAllows(dir))return false;',
   'if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED','if(InpRangeMode>0 && InpFlowMode!=1)']:
   self.assertIn(needle,s)
 def test_exit_management_unchanged(self):
  a=(P/'EA/LTA Flow Research.mq5').read_text().split('void ManageFlow()')[1].split('int OnInit()')[0]
  b=(R/'EA/LTA Flow Research.mq5').read_text().split('void ManageFlow()')[1].split('int OnInit()')[0]
  self.assertEqual(a,b)
 def test_flow_signal_only(self):
  self.assertTrue(all(c['mode']==1 and not c['safe'] for c in extension.CASES.values()))
if __name__=='__main__':unittest.main()
