"""Independent native-ledger and causal-profile verification; no terminal orders."""
import csv,json,math,unittest
from datetime import datetime,timedelta,time,timezone
import numpy as np
from data import ROOT,RAW,NY,load,save,sha

def boundaries(day):
    return tuple(int(datetime.combine(d,t,NY).timestamp()) for d,t in ((day-timedelta(days=1),time(18)),(day,time(9,30))))

def reference_profile(r,count,percent):
    lo=float(min(r['low']));hi=float(max(r['high']));width=(hi-lo)/count
    if width<=0:raise ValueError('Flat profile')
    hist=[0.]*count
    # Deliberately scalar, separately written implementation of the histogram.
    for bar in r:
        price=(float(bar['high'])+float(bar['low'])+float(bar['close']))/3
        index=max(0,min(count-1,math.floor((price-lo)/width)))
        hist[index]+=int(bar['tick_volume'])
    peak=max(range(count),key=lambda i:hist[i]);left=right=peak;volume=hist[peak]
    while volume<sum(hist)*percent/100 and (left>0 or right<count-1):
        below=hist[left-1] if left>0 else -1;above=hist[right+1] if right<count-1 else -1
        if above>=below and right<count-1:right+=1;volume+=hist[right]
        else:left-=1;volume+=hist[left]
    return dict(high=hi,low=lo,val=lo+left*width,vah=lo+(right+1)*width,poc=lo+(peak+.5)*width)

def verify():
    m1,m5=load();build=json.loads((ROOT/'build.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text())
    import frozen_parser
    parser_meta=json.loads((ROOT/'parser-isolation.json').read_text())
    assert sha(ROOT/'frozen_parser.py')==parser_meta['parser_sha256']
    for name in ('M1','M5'):assert sha(ROOT/'data'/(name+'.npz'))==manifest['files'][name]
    assert sha(ROOT/'Gold Overnight Value Area Research.mq5')==build['source_sha256']
    assert sha(ROOT/'Gold Overnight Value Area Research.ex5')==build['binary_sha256']
    cached={};results=[]
    for folder in sorted((ROOT/'native').iterdir()):
        if not (folder/'summary.json').exists():continue
        stats=json.loads((folder/'summary.json').read_text());run=json.loads((folder/'run.json').read_text());trades=json.loads((folder/'trades.json').read_text());c=run['config']
        replay={};frozen_parser.save=lambda path,obj:replay.update({str(path):obj})
        parsed=frozen_parser.parse_case(folder)
        assert replay[str(folder/'trades.json')]==trades,(folder.name,'Parser replay ledger differs')
        for key in ('trades','net_profit','commission','swap','profit_factor','return_pct','max_drawdown_pct'):
            assert parsed[key]==stats[key],(folder.name,'Parser replay metric differs',key)
        journal=(folder/'journal.txt').read_text()
        assert f"testing with execution delay {run['delay']} milliseconds" in journal,(folder.name,'Execution delay not confirmed by tester')
        assert run['build']['source_sha256']==build['source_sha256'] and run['build']['binary_sha256']==build['binary_sha256']
        audit=list(csv.DictReader((folder/'audit.csv').open(encoding='utf-8-sig')))
        profiles={r['ny_day']:r for r in audit if r['kind']=='profile'};diffs=[];signals=0
        for day,row in profiles.items():
            date=datetime.strptime(day,'%Y%m%d').date();start,opening=boundaries(date);key=(day,c['bins'],c['va'])
            if key not in cached:
                a,b=np.searchsorted(m1['time'],[start,opening]);bars=m1[a:b];assert len(bars)>=120
                assert bars['time'][-1]+60<=opening
                cached[key]=reference_profile(bars,c['bins'],c['va'])
            for field,expected in cached[key].items():
                if abs(float(row[field])-expected)>.000501:
                    diffs.append(dict(day=day,field=field,native=float(row[field]),expected=expected))
            assert int(row['server_epoch'])>=opening
        for r in audit:
            if r['kind'] not in ('entry','invalid_geometry','margin_rejected','order_rejected'):continue
            day=r['ny_day'];date=datetime.strptime(day,'%Y%m%d').date();_,opening=boundaries(date);when=int(r['server_epoch']);p=profiles[day]
            deadline=int(datetime.combine(date,time(c['entry_end']//60,c['entry_end']%60),NY).timestamp())
            assert when<deadline and when<int(r['cutoff_epoch'])
            a,b=np.searchsorted(m5['time'],[opening,when-299]);bars=m5[a:b]
            # A carried position can block early signals; account for its actual close.
            previous=[t for t in trades if datetime.fromisoformat(t['open_time']).timestamp()<opening and datetime.fromisoformat(t['close_time']).timestamp()>opening]
            if previous:
                free=max(datetime.fromisoformat(t['close_time']).timestamp() for t in previous)
                bars=bars[bars['time']+300>=free]
            bars=bars[(bars['close']>float(p['vah']))|(bars['close']<float(p['val']))]
            assert len(bars),(folder.name,day,'No causal M5 signal')
            first=bars[0];side=1 if first['close']>float(p['vah']) else -1
            assert side==int(r['side']) and 0<=when-first['time']-300<300,(folder.name,day,'Not first causal signal')
            anchor=float(p['poc']) if c['stop']==1 else float(p['val'] if side==1 else p['vah'])
            expected_sl=anchor-side*.001;entry=float(r['requested_entry'])
            expected_tp=entry+side*c['target_r']*abs(entry-expected_sl) if c['target_r']>0 else float(p['high'] if side==1 else p['low'])
            assert abs(float(r['stop'])-expected_sl)<.000501,(folder.name,day,'SL')
            assert abs(float(r['target'])-expected_tp)<.000501,(folder.name,day,'TP')
            if r['kind']=='entry':
                assert side*(entry-float(r['stop']))>0 and side*(float(r['target'])-entry)>0
                assert abs(float(r['target'])-entry)/abs(entry-float(r['stop']))+1e-9>=c['min_r']
            signals+=1
        assert signals==stats['audit']['signals']
        assert len(trades)==stats['trades']
        for field in ('net_profit','commission','swap'):
            assert abs(sum(t[field] for t in trades)-stats[field])<.061,(folder.name,field)
        assert abs(stats['initial_balance']+stats['net_profit']-stats['final_balance'])<.061
        for t in trades:
            side=1 if t['side']=='Long' else -1
            gross=side*(t['close_price']-t['open_price'])*100*t['volume']
            assert abs(gross-t['gross_profit'])<.061,(folder.name,'contract P/L')
            assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.061
        result=dict(case=folder.name,profiles=len(profiles),signals=signals,trades=len(trades),profile_differences=diffs,passed=not diffs)
        results.append(result);print('CHECKED',folder.name,len(profiles),signals,'differences',len(diffs),flush=True)
    save(ROOT/'verification.json',dict(all_passed=bool(results) and all(r['passed'] for r in results),cases=results,source_sha256=build['source_sha256'],unique_profiles_checked=len(cached)))

class Tests(unittest.TestCase):
    def test_summer_winter(self):
        for date,hour in [(datetime(2026,7,1),13),(datetime(2026,1,5),14)]:
            self.assertEqual(datetime.fromtimestamp(boundaries(date.date())[1],timezone.utc).hour,hour)
    def test_monday_sunday(self):
        start,_=boundaries(datetime(2026,9,14).date());d=datetime.fromtimestamp(start,NY)
        self.assertEqual((d.weekday(),d.hour),(6,18))
    def test_dst_monday(self):
        for date in (datetime(2026,3,9),datetime(2026,11,2)):
            a,b=boundaries(date.date());self.assertEqual(b-a,55800)
    def test_histogram_bounds(self):
        r=np.array([(1.,3.,2.,100),(2.,4.,3.,200)],dtype=[('low','f8'),('high','f8'),('close','f8'),('tick_volume','i8')])
        for bins in (32,64,96):
            for va in (60,70,80):
                p=reference_profile(r,bins,va);self.assertTrue(p['low']<=p['val']<=p['poc']<=p['vah']<=p['high'])
    def test_tester_safety(self):
        source=(ROOT/'Gold Overnight Value Area Research.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',source)
        self.assertIn('AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin',source)
    def test_baseline_parity(self):
        self.assertTrue(json.loads((ROOT/'raw-parity.json').read_text())['passed'])
    def test_lot_round_up(self):
        for distance in (1.,4.,53.797,150.):
            desired=100.;lot=max(.01,math.ceil(desired/(distance*100)/.01-1e-10)*.01)
            self.assertGreaterEqual(lot*distance*100+1e-8,desired)
        self.assertEqual(max(.01,math.ceil(50/(150*100)/.01-1e-10)*.01),.01)
    def test_synthetic_screen_stop_first(self):
        from screen import engine
        # Profile signal long, then one minute touches both stop and target.
        m5=np.array([[34200,100,106,99,105,1,0],[34500,105,120,80,105,1,0]],dtype=float)
        m1=np.array([[34500,105,120,80,105,1,0],[34560,105,106,104,105,1,0]],dtype=float)
        day=np.array([[0,34200,115,90,100,104,102,0,1]],dtype=float)
        a=engine(m1,m5,day,0,86400,0,0.,960,960,0.,0.,0.)
        self.assertEqual(len(a),1);self.assertEqual(a[0,12],1);self.assertLess(a[0,5],0)
        self.assertAlmostEqual(a[0,3],99.999)
    def test_invalid_consumes_signal(self):
        from screen import engine
        m5=np.array([[34200,100,116,99,116,1,0],[34500,100,106,99,105,1,0]],dtype=float)
        m1=np.array([[34500,116,117,114,116,1,0],[34800,105,106,104,105,1,0]],dtype=float)
        day=np.array([[0,34200,115,90,100,104,102,0,2]],dtype=float)
        self.assertEqual(len(engine(m1,m5,day,0,86400,0,0.,960,960,0.,0.,0.)),0)
    def test_short_uses_ask(self):
        from screen import engine
        m5=np.array([[34200,100,101,94,95,1,0]],dtype=float)
        m1=np.array([[34500,95,95.9,92,93,1,200],[34560,93,94,92,93,1,200]],dtype=float)
        day=np.array([[0,34200,110,85,96,100,98,0,1]],dtype=float)
        a=engine(m1,m5,day,0,86400,0,0.,960,576,0.,0.,0.)
        self.assertAlmostEqual(a[0,3],93.2)

if __name__=='__main__':
    import sys
    if '--unit' in sys.argv:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        save(ROOT/'unit-tests.json',dict(tests_run=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)))
        if not result.wasSuccessful():sys.exit(1)
    else:verify()
