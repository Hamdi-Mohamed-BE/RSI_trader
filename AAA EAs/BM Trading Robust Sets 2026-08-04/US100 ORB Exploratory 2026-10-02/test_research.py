import unittest
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from search import eligible,score
from native import ROOT,OUT,load,digest,sha

class ResearchTests(unittest.TestCase):
 def candidate(self,**kw):
  s=dict(trades=200,net=1000,pf=1.3,sharpe=1,equity_dd_pct=12,win_pct=55);s.update(kw)
  return dict(clean=True,stats=s)
 def test_small_sample_not_preferred(self):
  r=self.candidate(trades=99);self.assertFalse(eligible(r));self.assertEqual(score(r),-100)
 def test_profitability_required(self):
  self.assertFalse(eligible(self.candidate(pf=.95,net=-50,win_pct=80)))
  self.assertTrue(eligible(self.candidate()))
 def test_execution_failure_disqualifies(self):
  r=self.candidate();r['clean']=False;self.assertFalse(eligible(r));self.assertEqual(score(r),-100)
 def test_frozen_before_all_test_runs(self):
  f=ROOT/'FROZEN PRIMARY.json';frozen=load(f);self.assertEqual(frozen['source_main_sha'],sha(ROOT/'EA/Main.mqh'))
  for name in ('validation','locked-1y','recent-6m','full-3y','full-5y','delay-500ms-1y'):
   manifest=OUT/name/'manifest.json';self.assertLessEqual(f.stat().st_mtime,manifest.stat().st_mtime)
   self.assertEqual(load(manifest)['cases'][0],frozen['parameters'])
 def test_trial_accounting_not_only_winner(self):
  trials=load(ROOT/'TRIAL ACCOUNTING.json');self.assertEqual(trials['total'],len(trials['configurations']));self.assertGreater(trials['total'],20)
  self.assertIn('prior-US500-raw',trials['configurations'])
 def test_no_missing_cost_promoted(self):
  for name in ('validation','locked-1y','full-3y','full-5y'):
   a=load(ROOT/'audit'/(name+'.json'));self.assertFalse(a['gates']['cost_stress_supplied']);self.assertNotEqual(a['verdict'],'PASS_FOR_FORWARD_TEST')
   self.assertEqual(a['metrics']['tested_configurations'],load(ROOT/'TRIAL ACCOUNTING.json')['total'])
 def test_native_parity_and_signal_audit(self):
  self.assertTrue(load(ROOT/'PARITY.json')['passed']);v=load(ROOT/'VERIFICATION.json');self.assertTrue(v['passed']);self.assertEqual(v['closed_positions_checked'],v['filled_signals_checked'])
 def test_tester_only_guard(self):
  source=(ROOT/'EA/Main.mqh').read_text();self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',source)
if __name__=='__main__':unittest.main()
