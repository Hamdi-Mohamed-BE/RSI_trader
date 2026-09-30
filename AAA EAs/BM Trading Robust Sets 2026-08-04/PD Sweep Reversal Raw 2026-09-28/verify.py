"""Independent signal, timing, ledger and native historical-bar verification."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,json,math,re,unittest
import numpy as np
import run as runner
ROOT=runner.ROOT;CFG=runner.CFG
DT=np.dtype([('time','<i8'),('open','<f8'),('high','<f8'),('low','<f8'),('close','<f8'),('tick_volume','<i8')])
def fields(s):return dict(re.findall(r'(\w+)=([^ ]+)',s))
def random_side(bar,level,seed=9282026):
 x=(bar//60)^seed^((level*2654435761)&0xffffffff)
 x=(((x>>16)^x)*0x45d9f3b)&0xffffffff
 x=(((x>>16)^x)*0x45d9f3b)&0xffffffff
 x=(x>>16)^x
 return 1 if not x&1 else -1
def rejection(high,low,close,pdh,pdl):
 if not pdl<close<pdh:return None
 hi=high>pdh;lo=low<pdl
 if hi==lo:return None
 return 0 if hi else 1
def fresh(bar,now,tf):return bar>=now//86400*86400 and 0<=now-(bar+tf*60)<60 and now%86400<85800
def minute_present(times,requested):
 idx=np.searchsorted(times,requested)
 return (idx<len(times))&(times[np.minimum(idx,len(times)-1)]==requested)
def streaks(values,positive):
 runs=[];n=0
 for x in values:
  ok=x>0 if positive else x<0
  if ok:n+=1
  elif n:runs.append(n);n=0
 if n:runs.append(n)
 return max(runs,default=0),sum(runs)/len(runs) if runs else 0
class Tests(unittest.TestCase):
 def test_short(self):self.assertEqual(rejection(111,102,109,110,100),0)
 def test_long(self):self.assertEqual(rejection(108,99,101,110,100),1)
 def test_touch_not_sweep(self):self.assertIsNone(rejection(110,102,109,110,100))
 def test_boundary_close(self):self.assertIsNone(rejection(111,102,110,110,100))
 def test_close_outside(self):self.assertIsNone(rejection(111,102,110.5,110,100))
 def test_double_sweep(self):self.assertIsNone(rejection(111,99,105,110,100))
 def test_open_outside_allowed(self):self.assertEqual(rejection(112,108,109,110,100),0)
 def test_future_bar(self):self.assertFalse(fresh(900,1199,5))
 def test_first_tick(self):self.assertTrue(fresh(900,1200,5))
 def test_late_tick(self):self.assertFalse(fresh(900,1260,5))
 def test_midnight(self):self.assertFalse(fresh(86100,86400,5))
 def test_cutoff(self):self.assertFalse(fresh(85500,85800,5))
 def test_m15(self):self.assertTrue(fresh(1800,2700,15))
 def test_missing_first_minute(self):
  # A nominal 18:50 M5 bar can exist although its first quote is at 18:52.
  self.assertEqual(minute_present(np.array([1120,1180,1300]),np.array([1000,1120,1240,1360])).tolist(),[False,True,False,False])
 def test_zero_breaks_streak(self):self.assertEqual(streaks([1,1,0,1,-1,-1,-1],True),(2,1.5))
 def test_lot_rounding(self):self.assertAlmostEqual(math.ceil((.121-1e-12)/.01)*.01,.13)
 def test_seed_stable_and_mixed(self):
  a=[random_side(1759104000+i*300,i%2) for i in range(1000)]
  self.assertEqual(a,[random_side(1759104000+i*300,i%2) for i in range(1000)])
  self.assertTrue(400<a.count(1)<600)
 def test_source_safety(self):
  s=(ROOT/'Sweep.mq5').read_text();self.assertIn('MQLInfoInteger(MQL_TESTER)',s)
  self.assertNotIn('mt5.initialize', (ROOT/'run.py').read_text())
def audit():
 build=json.loads((ROOT/'BUILD.json').read_text());results=[];bar_results=[];total_signals=total_orders=0
 bar_cache={};candidate_cache={};bar_provenance={};minute_cache={};minute_provenance={}
 for name,h in build['hashes'].items():assert runner.sha(ROOT/name)==h,(name,'changed frozen source')
 for p in sorted((ROOT/'native').glob('*/run.json')):
  r=json.loads(p.read_text());assert r['ok'] and r['build']==build
  ini=(p.parent/'tester.ini').read_text(encoding='utf-8-sig')
  for required in ('Enabled=0','AllowLiveTrading=0','AllowDllImport=0','Model=4','ExecutionMode=150','Optimization=0','UseRemote=0','UseCloud=0'):
   assert required in ini,(p,required)
  assert hashlib.sha256(gzip.decompress((p.parent/'report.htm.gz').read_bytes())).hexdigest()==r['report_sha']
  assert runner.sha(p.parent/'deals.csv')==r['deals_sha']
  trades=json.loads((p.parent/'trades.json').read_text());signals=json.loads((p.parent/'signals.json').read_text());orders=json.loads((p.parent/'orders.json').read_text())
  spec=fields(r['symbol_spec'][0]);tick=float(spec['tick']);tf=r['timeframe'];control=r['variant']=='random-direction-control'
  floor=int(datetime.strptime(r['start'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
  assert len(orders)==len(trades)==r['metrics']['trades']
  assert abs(sum(t['net_profit'] for t in trades)-r['metrics']['net_profit'])<max(.12,.01*len(trades))
  by_order={o['order']:o for o in orders};by_signal={(s['bar'],s['level']):s for s in signals};seen=set()
  assert len(by_order)==len(orders) and len(by_signal)==len(signals)
  for s in signals:
   at=int(s['at']);bt=int(s['bar']);pd=int(s['pd']);level=int(s['level']);day=at//86400*86400
   assert at>=floor and fresh(bt,at,tf),(p,'stale/future signal',s)
   assert pd+86400<=day,(p,'incomplete prior daily bar',s)
   assert rejection(float(s['high']),float(s['low']),float(s['close']),float(s['pdh']),float(s['pdl']))==level,(p,'rejection geometry',s)
   expected=random_side(bt,level) if control else (-1 if level==0 else 1)
   assert int(s['side'])==expected,(p,'direction/seed',s)
   assert (day,level) not in seen,(p,'repeated level that day');seen.add((day,level))
  for t in trades:
   o=by_order[t['order']];s=by_signal[(o['bar'],o['level'])];side=int(o['side'])
   assert t['open_msc']>=int(o['at'])*1000 and t['close_msc']>=t['open_msc']
   assert t['magic']==9282610 and (t['side']=='Long')==(side==1)
   assert abs(t['volume']-float(o['lots']))<1e-7
   assert abs(t['open_price']-float(o['fill']))<max(tick/100,1e-7)
   assert abs(t['net_profit']-(t['gross_profit']+t['commission']+t['swap']+t['fee']))<1e-6
   stop=(float(s['low'])-tick) if side==1 else (float(s['high'])+tick)
   assert abs(stop-float(o['sl']))<max(tick/100,1e-7),(p,'not one tick beyond candle',o)
   distance=side*(float(o['entry'])-float(o['sl']));reward=side*(float(o['tp'])-float(o['entry']))
   assert distance>0 and abs(reward-2*distance)<=tick/2+1e-7,(p,'2R geometry',o)
   raw=float(o['planned'])/(float(o['risk'])/float(o['lots']));step=float(spec['step'])
   expected=max(float(spec['min']),min(float(spec['max']),math.ceil((raw-1e-8)/step)*step))
   assert abs(expected-float(o['lots']))<1e-6,(p,'round-up volume',o)
  ordered=sorted(trades,key=lambda t:t['open_msc'])
  assert all(b['open_msc']>=a['close_msc'] for a,b in zip(ordered,ordered[1:])),(p,'overlapping positions')
  deals=list(csv.DictReader((p.parent/'deals.csv').read_text(encoding='utf-8-sig').splitlines()));opens={t['position_id']:t['open_msc']//1000 for t in trades}
  for d in deals:
   if int(d['entry']) not in (1,3) or int(d['type']) not in (0,1) or int(d['reason'])!=3:continue
   at=int(d['time']);ot=opens[d['position']]
   assert at%86400>=85800 or at//86400>ot//86400,(p,'unexpected early expert close',d)
  results.append(dict(case=p.parent.name,signals=len(signals),trades=len(trades),passed=True))
  total_signals+=len(signals);total_orders+=len(orders)
  export=ROOT/'native'/f'{r["asset"]}-M{tf}-reversal-5y'
  if not (export/'SIGNAL.bin.gz').exists():continue
  bar_key=(r['asset'],tf)
  if bar_key not in bar_cache:
   bars=np.frombuffer(gzip.decompress((export/'SIGNAL.bin.gz').read_bytes()),dtype=DT);daily=np.frombuffer(gzip.decompress((export/'D1.bin.gz').read_bytes()),dtype=DT)
   bar_cache[bar_key]=(bars,daily)
   bar_provenance[export.name]={name:dict(sha256=runner.sha(export/name),rows=len(data),first=int(data['time'][0]),last=int(data['time'][-1])) for name,data in (('SIGNAL.bin.gz',bars),('D1.bin.gz',daily))}
  bars,daily=bar_cache[bar_key]
  if r['asset'] not in minute_cache:
   minute_path=ROOT/'minute-audit'/f'{r["asset"]}-M1.bin.gz'
   minutes=np.frombuffer(gzip.decompress(minute_path.read_bytes()),dtype=DT)['time'].copy()
   assert len(minutes)>0 and np.all(np.diff(minutes)>0)
   minute_cache[r['asset']]=minutes
   minute_provenance[r['asset']]=dict(sha256=runner.sha(minute_path),rows=len(minutes),first=int(minutes[0]),last=int(minutes[-1]))
  minutes=minute_cache[r['asset']]
  assert minutes[0]<floor
  assert np.all(np.diff(bars['time'])>0) and np.all(np.diff(daily['time'])>0)
  assert bars['time'][0]<floor and daily['time'][0]<floor
  for s in signals:
   bt=int(s['bar']);j=np.searchsorted(bars['time'],bt);day=int(s['at'])//86400*86400;k=np.searchsorted(daily['time'],day)-1
   assert bool(minute_present(minutes,np.array([bt+tf*60]))[0]),(p,'signal without a fresh first minute',s)
   assert j<len(bars) and bars[j]['time']==bt and k>=0,(p,'missing exported signal bar',s)
   b=bars[j];d=daily[k]
   for key in ('high','low','close'):assert abs(float(b[key])-float(s[key]))<max(1e-6,tick/100),(p,'signal bar reconstruction',key,s)
   assert d['time']==int(s['pd']) and abs(d['high']-float(s['pdh']))<max(1e-6,tick/100) and abs(d['low']-float(s['pdl']))<max(1e-6,tick/100),(p,'PDH/PDL reconstruction',s)
  # Rebuild *all* first eligible daily signals; do not only validate those the EA chose to print.
  bt=bars['time'];next_open=np.append(bt[1:],2**62);start=floor;end=int(datetime.strptime(r['end'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
  candidate_key=(r['asset'],tf,start,end)
  if candidate_key not in candidate_cache:
   selected=(bt+tf*60>=start)&(bt+tf*60<end)&(next_open==bt+tf*60)&(bt//86400==(bt+tf*60)//86400)&((bt+tf*60)%86400<85800)
   daily_idx=np.searchsorted(daily['time'],((bt+tf*60)//86400)*86400)-1;safe_idx=np.maximum(daily_idx,0)
   hi=bars['high']>daily['high'][safe_idx];lo=bars['low']<daily['low'][safe_idx]
   inside=(bars['close']<daily['high'][safe_idx])&(bars['close']>daily['low'][safe_idx])
   selected &= (daily_idx>=0)&inside&(hi^lo)
   # Signal bars are labelled by nominal open, not by the first quote time.
   # The frozen <60s freshness guard also requires the first M1 to exist.
   selected &= minute_present(minutes,bt+tf*60)
   eligible=[];used=set()
   for j in np.flatnonzero(selected):
    b=bars[j];at=int(b['time'])+tf*60;day=at//86400*86400;d=daily[daily_idx[j]]
    level=rejection(b['high'],b['low'],b['close'],d['high'],d['low'])
    assert level is not None
    key=(day,level)
    if key in used:continue
    used.add(key);eligible.append((str(int(b['time'])),str(level)))
   candidate_cache[candidate_key]=set(eligible)
  actual=set(by_signal);potential=candidate_cache[candidate_key]
  # Reconstruct using independent M1 availability, including historical quote gaps.
  extras=actual-potential;omissions=potential-actual
  assert not extras,(p,'EA signals not in independent reconstruction',list(extras)[:5])
  bar_results.append(dict(case=p.parent.name,recorded_signals=len(signals),rebuilt_signals=len(potential),extra_signals=len(extras),unresolved_omissions=len(omissions),omission_examples=sorted(omissions)[:5]))
 omissions=sum(x['unresolved_omissions'] for x in bar_results)
 runner.save(ROOT/'VERIFICATION.json',dict(helper_tests=18,completed_cases=results,total_signals=total_signals,total_orders=total_orders,historical_bar_checks=bar_results,unresolved_omissions=omissions,native_bar_provenance=bar_provenance,native_minute_provenance=minute_provenance,auditor_sha256=runner.sha(ROOT/'verify.py')))
 assert omissions==0,('Unexplained missing eligible signals',omissions)
 return len(results),len(bar_results),total_orders
if __name__=='__main__':
 tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 if not tests.wasSuccessful():raise SystemExit(1)
 print('Native audit:',audit())
