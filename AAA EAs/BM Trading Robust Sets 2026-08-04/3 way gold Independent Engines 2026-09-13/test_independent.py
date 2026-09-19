import json,unittest
from params import *

class IndependentTests(unittest.TestCase):
    def test_inherited_defaults(self):
        for e in (1,2,3):
            c=effective(DEFAULT,e)
            for k in ('InpATRPeriod','InpDirection','InpManagement','InpTriggerR','InpTrailATR'):self.assertEqual(c[k],DEFAULT[k])
    def test_distinct_atrs(self):
        c=normalize(dict(InpMomentumATRPeriod=10,InpChangeATRPeriod=20,InpBreakoutATRPeriod=14))
        self.assertEqual([effective(c,e)['InpATRPeriod'] for e in (1,2,3)],[10,20,14])
    def test_direction_isolation(self):
        c=normalize(dict(InpDirection=1,InpMomentumDirection=-1,InpChangeDirection=0))
        self.assertEqual([effective(c,e)['InpDirection'] for e in (1,2,3)],[-1,0,1])
    def test_zero_management_overrides_common(self):
        c=normalize(dict(InpManagement=3,InpChangeManagement=0));self.assertEqual(effective(c,2)['InpManagement'],0);self.assertEqual(effective(c,1)['InpManagement'],3)
    def test_trigger_and_trail_independence(self):
        c=normalize(dict(InpMomentumTriggerR=.75,InpBreakoutTrailATR=3.));self.assertEqual(effective(c,1)['InpTriggerR'],.75);self.assertEqual(effective(c,3)['InpTrailATR'],3.)
        self.assertEqual(effective(c,2)['InpTriggerR'],1.)
    def test_input_identity_tracks_overrides(self):self.assertNotEqual(ident(DEFAULT),ident({**DEFAULT,'InpMomentumATRPeriod':10}))
    def test_source_uses_engine_atr(self):
        s=(ROOT/'EA'/'3 way gold Independent.mq5').read_text()
        self.assertIn('EngineStop(engine)*EngineATR(engine)',s)
        self.assertIn('tr,batr[1],batr[2],InpExpansionATR',s)
        self.assertIn('EngineTrail((int)engine)*EngineATR((int)engine)',s)
        self.assertIn('EngineDirection(engine)!=0',s)
    def test_tester_only(self):
        s=(ROOT/'EA'/'3 way gold Independent.mq5').read_text();self.assertIn('if(!MQLInfoInteger(MQL_TESTER))',s);self.assertIn('if(HasEngine(engine))',s)
    def test_no_current_bar_management(self):
        s=(ROOT/'EA'/'3 way gold Independent.mq5').read_text();self.assertIn('b[1].close-entry',s);self.assertNotIn('b[0].close-entry',s)
    def test_frozen_assembly_matches_individual_selections(self):
        assembled=json.loads((ROOT/'assembled-selection.json').read_text())['config']
        selections=json.loads((ROOT/'individual-selection.json').read_text())['engines']
        self.assertEqual(assembled['InpEngine'],0)
        self.assertEqual(assembled['InpRiskPerEnginePercent'],.30)
        for e,name in [(1,'Momentum'),(2,'Change'),(3,'Breakout')]:
            selected=selections[str(e)]['config'];actual=effective(assembled,e)
            for key in ENGINE[e]+['InpATRPeriod','InpDirection','InpManagement','InpTriggerR','InpTrailATR']:
                self.assertEqual(actual[key],selected[key])
            self.assertEqual(assembled['Inp'+name+'StopATR'],selected['InpStopATR'])
            self.assertEqual(assembled['Inp'+name+'RR'],selected['InpRewardRisk'])
            self.assertEqual(assembled['Inp'+name+'RiskWeight'],1.)

if __name__=='__main__':unittest.main(verbosity=2)
