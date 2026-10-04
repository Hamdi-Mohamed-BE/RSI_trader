import json,unittest,datetime,calendar
from pathlib import Path
import numpy as np
import pandas as pd
import analyse as a
R=Path(__file__).resolve().parent
def ny_formula(t):
 y=t.year
 def sunday(m,n):return 1+(6-datetime.date(y,m,1).weekday())%7+7*(n-1)
 start=datetime.datetime(y,3,sunday(3,2),7,tzinfo=datetime.timezone.utc);end=datetime.datetime(y,11,sunday(11,1),6,tzinfo=datetime.timezone.utc)
 return t-datetime.timedelta(hours=4 if start<=t<end else 5)
class Tests(unittest.TestCase):
 def test_ny_clock_all_dst_boundaries(self):
  for y in range(2015,2031):
   for m in range(1,13):
    for day in range(1,calendar.monthrange(y,m)[1]+1):
     for h in [0,5,6,7,12,23]:
      t=datetime.datetime(y,m,day,h,tzinfo=datetime.timezone.utc);x=ny_formula(t);z=pd.Timestamp(t).tz_convert('America/New_York')
      self.assertEqual((x.year,x.month,x.day,x.hour),(z.year,z.month,z.day,z.hour))
 def test_selection_exact(self):
  p=json.loads((R/'SELECTED-HOURS.json').read_text());src=Path(p['source']);self.assertEqual(a.sha(src),p['source_sha256']);rows=json.loads(src.read_text());expected=[r for r in rows if r['window']=='1y' and r['pf'] is not None and r['pf']>=1.2 and r['win_rate_pct']>=50];self.assertEqual(expected,p['hours']);self.assertEqual(len(expected),11)
 def test_profile_hours_and_no_conflicts(self):
  expected={'US30':{'buy':[2,6],'sell':[0,15,22]},'US100':{'buy':[2,13,20],'sell':[14,22]},'SP500':{'buy':[],'sell':[22]}}
  rows=json.loads((R/'SELECTED-HOURS.json').read_text())['hours']
  for asset,sides in expected.items():
   for side,hours in sides.items():self.assertEqual([r['hour'] for r in rows if r['asset']==asset and r['side']==side],hours)
   self.assertFalse(set(sides['buy'])&set(sides['sell']))
 def test_no_live_install_and_source_safety(self):
  s=(R/'CalyxHourlyProfiles.mq5').read_text();self.assertIn('InpAllowRealAccount=false',s);self.assertIn('GlobalVariablesFlush()',s);self.assertIn('PositionGetInteger(POSITION_TIME)',s);self.assertIn('Own()',s);self.assertIn('OrderCheck(req,check)',s);self.assertIn('lastDay[ny.hour]=day',s);self.assertNotIn('InpRiskPercent',s)
 def test_mc_additive_not_compounded(self):
  old=a.PATHS;a.PATHS=400
  df=pd.DataFrame([{'exit_utc':'2026-01-05T12:00:00+00:00','net_cash':100},{'exit_utc':'2026-01-05T13:00:00+00:00','net_cash':-50}])
  r=a.bootstrap(df,'2026-01-05','2026-01-06',5,9);self.assertEqual(r['return_p05_p50_p95'],[.5,.5,.5]);self.assertEqual(r['pf_p05_p50_p95'],[2.,2.,2.]);a.PATHS=old
 def test_metrics_net_fees_and_streaks(self):
  d=pd.DataFrame([{'position_id':i,'exit_utc':f'2026-01-0{5+i}T12:00:00+00:00','net_cash':p,'commission':-1.,'swap':0.,'fees':0.,'late_exit_seconds':0.} for i,p in enumerate([10.,20.,-5.])]);m=a.metrics(d,'2026-01-05','2026-01-08');self.assertEqual(m['net_cash'],25.);self.assertEqual(m['pf'],6.);self.assertEqual(m['max_win_streak'],2);self.assertAlmostEqual(m['return_pct'],.25)
 def test_source_binding_all_native_runs(self):
  rows=json.loads((R/'NATIVE.json').read_text());self.assertGreaterEqual(len(rows),27)
  for r in rows:self.assertEqual(r['source_sha256'],a.sha(R/'CalyxHourlyProfiles.mq5'));self.assertEqual(r['binary_sha256'],a.sha(R/'CalyxHourlyProfiles.ex5'));self.assertEqual(r['lots'],1);self.assertEqual(r['model'],4)
if __name__=='__main__':unittest.main()
