"""Deterministic checks of the frozen comparison and risk/phase bookkeeping."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
import run_study as study


class StudyTests(unittest.TestCase):
    def test_seven_active_orbs_have_distinct_ids(self):
        self.assertEqual(len(study.EAS),7)
        self.assertEqual(len({e[0] for e in study.EAS}),7)
        self.assertEqual({e[2] for e in study.EAS},{'XAUUSD','USTEC'})

    def test_original_rr_and_risk(self):
        expected={'vp':2.5,'vpc':2.5,'xny':1.5,'xov':1.0,'uny':4.0,'uh1':6.0,'usel':2.0}
        for slug,label,symbol,period,expert,path in study.EAS:
            config=study.settings(path)
            self.assertAlmostEqual(float(config['InpRewardRisk']),expected[slug])
            self.assertEqual(float(config['InpRiskPercent']),1.0)
            self.assertEqual(config['InpTesterServerUTCOffsetHours'],'0')

    def test_saved_high_win_is_same_rr075_hypothesis(self):
        base=study.settings(study.SELECTED/'05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set')
        saved=study.settings(study.SELECTED/'05B ORB Volume Profile High Win 0.75R - DYNAMIC 50-20 - ALL DAY.set')
        for key,value in base.items():
            if key not in ('InpRewardRisk','InpMagic'):
                self.assertEqual(value,saved[key],key)
        self.assertEqual(float(saved['InpRewardRisk']),0.75)

    def test_verification_starts_next_business_day(self):
        friday=int(datetime(2026,9,4,19,0,tzinfo=timezone.utc).timestamp())
        monday=int(datetime(2026,9,7,19,0,tzinfo=timezone.utc).timestamp())
        self.assertEqual(study.next_business_day(friday),'2026.09.07')
        self.assertEqual(study.next_business_day(monday),'2026.09.08')

    def test_wrapper_is_tester_only_and_keeps_strategy(self):
        for name in ('ORB Volume Audit','Selective ORB Audit'):
            wrapper=(study.ROOT/(name+'.mq5')).read_text()
            self.assertIn('if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;',wrapper)
            self.assertIn('CalyxBaseTick();',wrapper)
            self.assertIn('CalyxBaseTimer();',wrapper)
            self.assertNotIn('OrderSend(',wrapper)
        audit=(study.ROOT/'TrialAudit.mqh').read_text()
        self.assertNotIn('OrderSend(',audit)
        self.assertIn('trial_day_balance-500.000001',audit)
        self.assertIn('8999.999999',audit)
        self.assertIn('trial_entry_days>=4',audit)
        self.assertIn('PositionsTotal()==0 && OrdersTotal()==0',audit)


if __name__=='__main__':
    unittest.main()
