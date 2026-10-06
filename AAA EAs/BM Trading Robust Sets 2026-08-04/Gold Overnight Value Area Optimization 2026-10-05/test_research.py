"""Offline tests of payoff analysis and frozen research safeguards."""
import importlib.util,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gold_report',R/'report.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ResearchChecks(unittest.TestCase):
 def test_search_count_and_selection(self):
  search=a.read('SEARCH RESULTS.json');chosen=a.read('selection-frozen.json')
  self.assertEqual(search['configurations'],len({x['id'] for x in search['rows']}))
  self.assertEqual(chosen['search_sha'],a.sha(R/'SEARCH RESULTS.json'))
  self.assertFalse(chosen['selected']['screen_eligible'])
 def test_source_guard_and_default_parity(self):
  source=(R/'EA/Gold VA Research.mq5').read_text()
  self.assertIn('if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY: tester required");return INIT_FAILED;}',source)
  self.assertEqual(a.read('native/original-3m/native-deals.json'),a.read('native/raw-3m/native-deals.json'))
 def test_pf_and_cost_signs(self):
  self.assertAlmostEqual(a.pf([10,-5,0,20,-5]),3.)
  self.assertIsNone(a.pf([10,0]))
  self.assertEqual(a.a.stats.streaks([1,1,-1,0,-1,-1,1]),(2,2))
 def test_production_preserved(self):
  for p,digest in a.read('frozen.json')['production'].items():self.assertEqual(a.sha(R.parent/p),digest)
 def test_complete_native_reconciliation(self):
  for q in a.read('COMPARISON.json'):self.assertTrue(a.independent(q))
 def test_annual_cash(self):
  rows=a.read('ANNUAL.json')
  for tag in ['raw-5y','candidate-5y']:
   q=a.read('native/'+tag+'/results.json')
   self.assertAlmostEqual(sum(r['net_profit'] for r in rows if r['version']==tag),q['metrics']['net_profit'],places=2)
 def test_rejection_not_silently_promoted(self):
  v=a.read('VERDICT.json');self.assertFalse(v['qualified_native_development_validation']);self.assertTrue(v['no_production_change'])
  self.assertEqual(v['decision'],'NO REPLACEMENT RECOMMENDATION')
 def test_mc_definition(self):
  for r in a.read('ROBUSTNESS.json').values():
   self.assertEqual(r['paths'],10000);self.assertEqual(r['block_length'],5)
   self.assertLessEqual(r['bootstrap']['return_p05_pct'],r['bootstrap']['return_p50_pct'])
   self.assertLessEqual(r['bootstrap']['return_p50_pct'],r['bootstrap']['return_p95_pct'])
if __name__=='__main__':unittest.main()
