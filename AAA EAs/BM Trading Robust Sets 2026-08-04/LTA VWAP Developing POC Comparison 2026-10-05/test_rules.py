import math,unittest
from pathlib import Path
import run
R=Path(__file__).resolve().parent
def qualifies(side,o,h,l,c,vwap,poc,val,vah,entry):
 rg=h-l
 if rg<=0 or not val<=c<=vah or not val<=entry<=vah or abs(c-o)/rg<.6:return False
 loc=(c-l)/rg
 return c>o and loc>=.75 and c>vwap and c>poc if side>0 else c<o and loc<=.25 and c<vwap and c<poc
def half_lots(volume,step,minlot):
 half=math.floor((volume*.5+1e-10)/step)*step
 return half if half>=minlot-1e-9 and volume-half>=minlot-1e-9 else None
class Rules(unittest.TestCase):
 def test_strong_long(self):self.assertTrue(qualifies(1,100,110,100,109,105,106,90,120,109.1))
 def test_strong_short(self):self.assertTrue(qualifies(-1,110,110,100,101,105,104,90,120,100.9))
 def test_weak_body(self):self.assertFalse(qualifies(1,105,110,100,109,106,107,90,120,109.1))
 def test_wrong_close_location(self):self.assertFalse(qualifies(1,100,110,100,107,101,102,90,120,107.1))
 def test_outside_value(self):self.assertFalse(qualifies(1,100,110,100,109,105,106,90,108,109.1))
 def test_entry_outside_value(self):self.assertFalse(qualifies(1,100,110,100,109,105,106,90,110,110.1))
 def test_equal_vwap_no_signal(self):self.assertFalse(qualifies(1,100,110,100,109,109,106,90,120,109.1))
 def test_equal_dev_poc_no_signal(self):self.assertFalse(qualifies(1,100,110,100,109,105,109,90,120,109.1))
 def test_minlot_partial_cannot_close_all(self):self.assertIsNone(half_lots(.01,.01,.01))
 def test_odd_steps_partial_round_down(self):self.assertAlmostEqual(half_lots(.03,.01,.01),.01)
 def test_even_partial(self):self.assertAlmostEqual(half_lots(.10,.01,.01),.05)
 def test_core_has_only_declared_hooks(self):
  src=(run.B/'LTA volume profile/EA/LTA_Concepts_EA.mq5').read_text().strip()+'\n'
  expected=src.replace('#include "..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh"','#include "CalyxAdaptivePortfolio.mqh"')
  expected=expected.replace('int OnInit()','int LTA_BaseInit()').replace('void OnTick()','void LTA_BaseTick()').replace('double OnTester()','double LTA_BaseScore()')
  expected=expected.replace('bool BuildSignal(TradeSignal &signal)','bool BuildLegacySignal(TradeSignal &signal)')
  expected=expected.replace('   return ok;\n}','   FlowAfterOrder(signal, ok);\n   return ok;\n}')
  expected=expected.replace('void ManageOpenPositions()\n{','void ManageOpenPositions()\n{\n   if(InpFlowMode>0) return; // New flow has its own frozen-POC exits.\n')
  expected=expected.replace('   string side = (signal.dir > 0 ? "BUY" : "SELL");','   FlowBeforeOrder(signal);\n   string side = (signal.dir > 0 ? "BUY" : "SELL");')
  self.assertEqual(expected,(R/'EA/LTA Core.mqh').read_text())
 def test_copies_unchanged(self):
  for name in ['SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:
   self.assertEqual((R/'EA'/name).read_text().strip(),(run.B/'LTA volume profile/EA'/name).read_text().strip())
  self.assertEqual((R/'EA/CalyxAdaptivePortfolio.mqh').read_text().strip(),(run.B/'_Shared/CalyxAdaptivePortfolio.mqh').read_text().strip())
 def test_research_and_closed_bar_guards(self):
  s=(R/'EA/LTA Flow Research.mq5').read_text()
  for needle in ['if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED','(datetime)(to-1)','(datetime)(nowbar-1)',
   'today[i].time+300>nowbar','closed<flowEntry','frozenPOC=plannedPD.poc','partialDone=true;partials++','dir*(sl-entry)>=0']:
   self.assertIn(needle,s)
 def test_metrics_count_partial_as_one_position(self):
  m=run.metrics([dict(net=20,partial=True,breakeven=True),dict(net=-10),dict(net=5),dict(net=6)])
  self.assertEqual(m['trades'],4);self.assertEqual(m['win_rate'],75);self.assertEqual(m['win_streak'],2);self.assertAlmostEqual(m['pf'],3.1)
if __name__=='__main__':unittest.main()
