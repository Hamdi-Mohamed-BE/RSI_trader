import unittest,json,hashlib
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from build_engine import BASE,build,validate,FIELDS
from search_plan import PLAN,STAGES
R=Path(__file__).resolve().parent

class TestPipeline(unittest.TestCase):
 def test_dates(self):
  c=json.loads((R/'config.json').read_text())
  self.assertEqual(c['development'],['2020-01-01','2024-01-01'])
  self.assertEqual(c['validation'],['2024-01-01','2025-01-01'])
  self.assertEqual(c['out_of_sample'][0],'2025-01-01')
  self.assertTrue(c['research_only']);self.assertFalse(c['live_changes'])
 def test_calendar(self):
  c=json.loads((R/'calendar.json').read_text())['events'];ny=ZoneInfo('America/New_York')
  self.assertEqual(len(c),214);self.assertEqual(len({x['epoch'] for x in c}),214)
  self.assertEqual([x['epoch'] for x in c],sorted(x['epoch'] for x in c))
  for e in c:
   d=datetime.fromtimestamp(e['epoch'],timezone.utc).astimezone(ny)
   self.assertEqual((d.hour,d.minute),(14,0) if e['kind']=='FOMC' else (8,30))
   self.assertTrue(e['source'].startswith(('https://www.bls.gov/','https://www.federalreserve.gov/')))
 def test_raw_mechanics(self):
  s=build([BASE])
  for text in ['!MQLInfoInteger(MQL_TESTER)','pivot_confirm<=b.time','b.time+60>now',
   'event+window_minutes*60','filled+hold_minutes*60','Events[event_index]+5400',
   'MathFloor(budget/-loss/step','ep+(fair-ep)*target_fraction','PERIOD_M5,14']:
   self.assertIn(text,s)
  self.assertEqual(list(BASE),FIELDS)
  self.assertEqual(BASE['sl_mult'],2);self.assertEqual(BASE['hold_minutes'],60)
 def test_ranges(self):
  for _,key,values in STAGES:
   for v in values:validate(dict(BASE,**{key:v}))
  with self.assertRaises(AssertionError):validate(dict(BASE,allow_longs=0))
  self.assertNotIn('event_mask',str(PLAN))
 def test_lock_order(self):
  s=(R/'run_pipeline.py').read_text()
  self.assertLess(s.index("R/'FROZEN.json'"),s.index("r.batch('holdout'"))
  after=s.split('# No selection occurs below this line.')[1]
  self.assertNotIn('score(',after)
 def test_source_hashes_if_frozen(self):
  f=R/'FROZEN.json'
  if not f.exists():return
  lock=json.loads(f.read_text())['locked']
  for n,k in [('calendar.json','calendar_sha256'),('engine.mq5','engine_sha256'),('trials.json','trials_sha256')]:
   self.assertEqual(hashlib.sha256((R/n).read_bytes()).hexdigest(),lock[k])

if __name__=='__main__':unittest.main()
