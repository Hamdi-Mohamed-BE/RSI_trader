from pathlib import Path
import json,unittest
import search_plan as s
import build_engine as e
R=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_search_preserves_baseline(self):
  for b in s.RAW:
   self.assertEqual(s.RAW[b]['entry'],0);self.assertEqual(s.RAW[b]['management'],0)
   self.assertEqual(s.RAW[b]['daily_cap'],1);self.assertEqual(s.RAW[b]['width'],1)
 def test_holdout_not_in_selection(self):
  import raw_runner as r
  self.assertEqual(r.CFG['development'][1],r.CFG['validation'][0]);self.assertEqual(r.CFG['validation'][1],r.CFG['oos'][0])
  self.assertEqual(r.CFG['oos'],['2024-10-09','2026-10-09'])
 def test_source_tester_only_and_causal(self):
  code=e.build()
  for x in ['!MQLInfoInteger(MQL_TESTER)','MathFloor(','CopyBuffer(atr_handle,0,1,1','bars[k-InpPivotNeighbours-1].time','current-bars[1].time!=PeriodSeconds']:
   self.assertIn(x,code)
  self.assertNotIn('WebRequest(',code)
 def test_threshold_is_correct_field(self):
  self.assertEqual(s.FIELDS.index('threshold'),15);self.assertIn('C[InpCase][15]',(R/'Extras.mqh').read_text())
 def test_case_table_width(self):
  for c in s.RAW.values():self.assertEqual(set(c),set(s.FIELDS))
 def test_native_evidence_when_present(self):
  for path in (R/'native').glob('*/results.json'):
   rows=json.loads(path.read_text())
   if not isinstance(rows,list):continue
   for q in rows:
    self.assertTrue(q['signal_audit_verified'])
    self.assertAlmostEqual(sum(t['net'] for t in q['trades']),q['native']['net'],delta=.031)
    self.assertEqual(len(q['signals']),len(q['trades']))
if __name__=='__main__':unittest.main()
