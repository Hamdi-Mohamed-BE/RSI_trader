import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def trail(levels,direction,entry,old,c1,c2,buffer):
    candidate=old
    for i,level in enumerate(levels):
        prev=i-direction
        if not 0<=prev<len(levels) or direction*(level-entry)<=0:continue
        threshold=level+direction*buffer
        if direction*(c1-threshold)<=0 or direction*(c2-threshold)>0:continue
        proposed=levels[prev]-direction*buffer
        if direction*(proposed-candidate)>0:candidate=proposed
    return candidate

class Rules(unittest.TestCase):
    def test_long_preceding_level(self):self.assertEqual(trail([90,100,110,120],1,99,80,111,109,.5),99.5)
    def test_short_preceding_level(self):self.assertEqual(trail([90,100,110,120],-1,111,130,99,101,.5),110.5)
    def test_gap_uses_furthest_crossed(self):self.assertEqual(trail([90,100,110,120],1,99,80,125,99,.5),109.5)
    def test_never_loosen(self):self.assertEqual(trail([90,100,110,120],1,99,105,111,109,.5),105)
    def test_no_cross_no_change(self):self.assertEqual(trail([90,100,110,120],1,99,80,111,111,.5),80)
    def test_not_already_behind_entry(self):self.assertEqual(trail([90,100,110,120],1,115,80,111,109,.5),80)
    def test_no_preceding_rung(self):self.assertEqual(trail([100,110,120],1,95,80,101,99,.5),80)
    def test_equal_close_not_break(self):self.assertEqual(trail([90,100,110],1,99,80,110.5,109,.5),80)
    def test_core_fidelity(self):
        original=(ROOT.parent/'LTA volume profile'/'EA'/'LTA_Concepts_EA.mq5').read_text()
        expected=original.replace('#include "..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh"','#include "CalyxAdaptivePortfolio.mqh"')
        expected=expected.replace('int OnInit()','int LTA_BaseInit()').replace('void OnTick()','void LTA_BaseTick()').replace('double OnTester()','double LTA_BaseScore()')
        expected=expected.replace('      tp = NormalizePrice(tp);','      tp = NormalizePrice(tp);\n\n      if(!AOI_AdjustTarget(dir, entry, sl, tp))\n         continue;')
        expected=expected.replace('if(MathAbs(tp - entry) < MinimumStopDistance())','if(tp > 0.0 && MathAbs(tp - entry) < MinimumStopDistance())')
        expected=expected.replace('   return ok;','   AOI_AfterOrder(signal, ok);\n\n   return ok;')
        self.assertEqual(expected,(ROOT/'EA'/'LTA Original Core.mqh').read_text())
    def test_research_guard(self):
        text=(ROOT/'EA'/'LTA AOI Research.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',text)
        self.assertIn('(datetime)(to-1)',text)
        self.assertIn('closedBar>=entryTime',text)
    def test_shared_includes_unchanged(self):
        for name in ['SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:
            self.assertEqual((ROOT/'EA'/name).read_bytes(),(ROOT.parent/'LTA volume profile'/'EA'/name).read_bytes())
        self.assertEqual((ROOT/'EA'/'CalyxAdaptivePortfolio.mqh').read_bytes(),(ROOT.parent/'_Shared'/'CalyxAdaptivePortfolio.mqh').read_bytes())
if __name__=='__main__':unittest.main()
