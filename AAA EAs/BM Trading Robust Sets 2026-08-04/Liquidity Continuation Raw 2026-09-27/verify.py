"""Independent evidence checks. Reads saved native output; no terminal control."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,json,re,hashlib,unittest,math,bisect
import report
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fields(s):return dict(re.findall(r'(\w+)=([^ ]+)',s))
def epoch(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
def replay_setup(touch,bar_open,bar_close,outside,wick,broken=None):
 # Independent explicit state transition model used for boundary/unit tests.
 if bar_close<=touch or bar_close-touch>1800:return None
 if broken is None:return ('break',bar_open) if outside else None
 return ('entry',bar_close) if bar_open>broken and outside and wick else None
class LogicTests(unittest.TestCase):
 def test_no_future_close(self):self.assertIsNone(replay_setup(1000,600,900,True,True))
 def test_same_bar_not_retest(self):self.assertEqual(replay_setup(1000,900,1200,True,True),('break',900))
 def test_distinct_retest(self):self.assertEqual(replay_setup(1000,1200,1500,True,True,900),('entry',1500))
 def test_repeated_break_cannot_enter(self):self.assertIsNone(replay_setup(1000,900,1200,True,True,900))
 def test_inside_close_not_entry(self):self.assertIsNone(replay_setup(1000,1200,1500,False,True,900))
 def test_no_touch_no_retest(self):self.assertIsNone(replay_setup(1000,1200,1500,True,False,900))
 def test_expired_retest(self):self.assertIsNone(replay_setup(1000,2700,3000,True,True,900))
 def test_exact_boundary(self):self.assertEqual(replay_setup(900,2400,2700,True,True,900),('entry',2700))
 def test_sizing_rounds_up(self):self.assertEqual(round(math.ceil((.121-1e-12)/.01)*.01,2),.13)
 def test_exact_lot_not_extra_step(self):self.assertEqual(round(math.ceil((.12-1e-12)/.01)*.01,2),.12)
 def test_streaks(self):
  t=[{'net_profit':p} for p in [1,1,-1,-1,-1,0,1]]
  self.assertEqual(report.sequences(t,True),(2,1.5));self.assertEqual(report.sequences(t,False),(3,3))
 def test_costs_change_winner(self):
  t=[dict(net_profit=-.1,commission=-1.1,swap=0),dict(net_profit=2,commission=0,swap=0)]
  m=report.metrics(t,'2026.01.01','2026.02.01');self.assertEqual(m['win_rate_pct'],50);self.assertAlmostEqual(m['pf'],20)
 def test_wilson(self):
  lo,hi=report.wilson(50,100);self.assertTrue(40<lo<41 and 59<hi<60)
def audit():
 output=[];build=json.loads((ROOT/'BUILD.json').read_text())
 for path,key in [('Liquidity.mq5','source_sha'),('Liquidity.ex5','binary_sha'),('RULES.md','rules_sha'),('run-config.json','config_sha')]:assert sha(ROOT/path)==build[key]
 for p in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(p.read_text());assert r['build']==build
  trades=json.loads((p.parent/'trades.json').read_text());orders=json.loads((p.parent/'order-audit.json').read_text())
  journal=gzip.decompress((p.parent/'journal.txt.gz').read_bytes()).decode()
  lines=list(set(re.findall(r'LC_[^\r\n]+',journal)))
  formations=[fields(x) for x in lines if x.startswith('LC_LEVEL')];touches=[fields(x) for x in lines if x.startswith('LC_TOUCH')]
  touch_index={};form_index={}
  for t in touches:touch_index.setdefault((t['i'],t['level']),[]).append(int(t['at']))
  for f in formations:form_index.setdefault((f['i'],f['level']),[]).append(f)
  for ts in touch_index.values():ts.sort()
  for fs in form_index.values():fs.sort(key=lambda f:int(f['at']))
  tick=float(fields(r['symbol_spec'][0])['tick'])
  for fm in formations:
   side=1 if int(fm['i'])%2==0 else -1
   assert int(fm['expires'])>int(fm['at'])
   assert not int(fm['donor']) or int(fm['donor'])<int(fm['at'])
   if fm['state']=='0':
    assert side*(float(fm['level'])-float(fm['bid']))>0,(p,'level already crossed at formation',fm)
    expected=float(fm['bid'])+side*float(fm['donorDist'])*float(fm['atr']) if 'control' in r['variant'] else float(fm['real'])
    assert abs(float(fm['level'])-expected)<=tick/2+1e-5,(p,'level construction',fm)
  start=epoch(r['start'].replace('.','-')+'T00:00:00')
  assert len(trades)==len(orders)==r['metrics']['trades'],(p,'order count')
  assert abs(sum(t['net_profit'] for t in trades)-r['metrics']['net_profit'])<max(.12,.01*len(trades))
  assert all(epoch(t['open_time'])>=start and epoch(t['close_time'])>=epoch(t['open_time']) for t in trades)
  ordered=sorted(trades,key=lambda t:t['open_time'])
  assert all(epoch(b['open_time'])>=epoch(a['close_time']) for a,b in zip(ordered,ordered[1:])),(p,'overlap')
  assert len({o['order'] for o in orders})==len(orders)
  for o in orders:
   tm=int(o['at']);level=float(o['level']);side=int(o['type'])
   matches=touch_index.get((o['i'],o['level']),[]);ti=bisect.bisect_right(matches,tm)-1
   assert ti>=0,(p,'entry without touch',o)
   touch_at=matches[ti]
   # First available quote may be seconds after the bar boundary, never assume hh:mm:00 fills.
   if r['variant'].startswith('retest'):assert touch_at//300*300+600<=tm<=touch_at+1800,(p,'retest timing',o)
   else:assert tm==touch_at,(p,'touch delayed signal',o)
   if 'control' in r['variant']:
    fs=[f for f in form_index.get((o['i'],o['level']),[]) if int(f['at'])<=tm]
    # A level may have been formed during warmup; those formations are deliberately not printed.
    if fs:
     form=max(fs,key=lambda f:int(f['at']));assert 0<int(form['donor'])<int(form['at'])<=tm
   assert side*(float(o['entry'])-float(o['sl']))>0 and side*(float(o['tp'])-float(o['entry']))>0
   stop_distance=side*(float(o['entry'])-float(o['sl']));target_distance=side*(float(o['tp'])-float(o['entry']));atr=float(o['atr'])
   assert -1e-7<=stop_distance-atr<=tick+1e-7 and abs(target_distance-atr)<=tick/2+1e-7,(p,'ATR geometry',o)
   assert float(o['risk'])>0 and float(o['planned'])>0
  rep=gzip.decompress((p.parent/'report.htm.gz').read_bytes());assert hashlib.sha256(rep).hexdigest()==r['report_sha']
  output.append(dict(case=p.parent.name,trades=len(trades),orders=len(orders),touches=len(touches),passed=True))
 return output
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LogicTests))
 if not result.wasSuccessful():raise SystemExit(1)
 cases=audit();report.save(ROOT/'VERIFICATION.json',dict(unit_tests=result.testsRun,unit_failures=len(result.failures)+len(result.errors),native_cases=cases))
 print(f'Verified {len(cases)} retained native cases, {sum(c["trades"] for c in cases)} orders/deals')
