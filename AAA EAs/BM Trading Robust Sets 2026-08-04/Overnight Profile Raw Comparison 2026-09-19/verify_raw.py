"""Independent causal profile/signal checks against connected-broker M1/M5 bars."""
import csv,json,math,unittest
from datetime import datetime,timedelta,time,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import MetaTrader5 as mt5
from run_raw import ROOT,NORMAL,save,sha
NY=ZoneInfo('America/New_York')

def boundaries(day):
    start=datetime.combine(day-timedelta(days=1),time(18),NY)
    end=datetime.combine(day,time(9,30),NY)
    return int(start.timestamp()),int(end.timestamp())

def profile(bars):
    low=float(bars['low'].min());high=float(bars['high'].max());width=(high-low)/64
    if not width>0:raise ValueError('Flat profile')
    levels=np.clip(np.floor(((bars['high']+bars['low']+bars['close'])/3-low)/width).astype(int),0,63)
    bins=np.bincount(levels,weights=bars['tick_volume'],minlength=64)
    p=int(bins.argmax());left=right=p;covered=bins[p]
    while covered<bins.sum()*.7 and (left>0 or right<63):
        below=bins[left-1] if left>0 else -1;above=bins[right+1] if right<63 else -1
        if above>=below and right<63:right+=1;covered+=bins[right]
        else:left-=1;covered+=bins[left]
    return {'high':high,'low':low,'poc':low+(p+.5)*width,'val':low+left*width,'vah':low+(right+1)*width}

def get_bars(symbol,tf,label):
    path=ROOT/'data'/(symbol+'-'+label+'.npz')
    # A first bulk request can return a stale local tail while MT5 downloads it.
    # Prime each final-week day (a recent last bar alone does NOT prove no holes).
    for day in range(12,19):
        for _ in range(2):
            mt5.copy_rates_range(symbol,tf,datetime(2026,9,day,tzinfo=timezone.utc),datetime(2026,9,day+1,tzinfo=timezone.utc))
    rates=mt5.copy_rates_range(symbol,tf,datetime(2025,9,18,tzinfo=timezone.utc),datetime(2026,9,19,tzinfo=timezone.utc))
    assert rates is not None and len(rates)>1000,(symbol,label,mt5.last_error())
    assert np.all(np.diff(rates['time'])>0)
    assert rates['time'][-1]>=datetime(2026,9,18,tzinfo=timezone.utc).timestamp(),(symbol,label,'Incomplete final week')
    path.parent.mkdir(exist_ok=True);np.savez_compressed(path,rates=rates)
    return rates

def verify():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert mt5.initialize(str(NORMAL)),mt5.last_error()
    account=mt5.account_info();assert account.login==manifest['account']['login'] and account.server==manifest['account']['server']
    cache={}
    try:
        for asset,symbol in manifest['symbols'].items():
            cache[asset]=(get_bars(symbol,mt5.TIMEFRAME_M1,'M1'),get_bars(symbol,mt5.TIMEFRAME_M5,'M5'))
            print('HISTORY',asset,len(cache[asset][0]),len(cache[asset][1]),flush=True)
    finally:mt5.shutdown()
    results=[]
    for folder in sorted((ROOT/'native').iterdir()):
        if not (folder/'summary.json').exists():continue
        run=json.loads((folder/'run.json').read_text());stats=json.loads((folder/'summary.json').read_text());trades=json.loads((folder/'trades.json').read_text())
        m1,m5=cache[run['asset']];tick=manifest['contracts'][run['asset']]['trade_tick_size']
        audit=list(csv.DictReader((folder/'audit.csv').open(encoding='utf-8-sig')))
        native_profiles={r['ny_day']:r for r in audit if r['kind']=='profile'}
        checked=0;signal_checks=0;diffs=[]
        for day,row in native_profiles.items():
            date=datetime.strptime(day,'%Y%m%d').date();start,end=boundaries(date)
            bars=m1[(m1['time']>=start)&(m1['time']+60<=end)]
            assert len(bars)>=120,(folder.name,date,len(bars))
            expected=profile(bars)
            for field,value in expected.items():
                delta=abs(float(row[field])-value)
                if delta>tick*.501+1e-7:diffs.append(dict(day=day,field=field,native=float(row[field]),reference=value,delta=delta))
            assert int(row['server_epoch'])>=end
            checked+=1
        for row in audit:
            if row['kind'] not in ('entry','invalid_geometry','margin_rejected','order_rejected'):continue
            day=row['ny_day'];date=datetime.strptime(day,'%Y%m%d').date();_,open_epoch=boundaries(date)
            prof=native_profiles[day];cutoff=int(row['cutoff_epoch']);when=int(row['server_epoch'])
            candidates=m5[(m5['time']>=open_epoch)&(m5['time']+300<=when)&(m5['time']+300<cutoff)]
            upper=float(prof['vah'] if run['mode']=='VA' else prof['poc']);lower=float(prof['val'] if run['mode']=='VA' else prof['poc'])
            valid=candidates[(candidates['close']>upper)|(candidates['close']<lower)]
            assert len(valid)>0,(folder.name,day,'No causal signal')
            signal=valid[0];side=1 if signal['close']>upper else -1
            assert side==int(row['side']),(folder.name,day,'Direction differs')
            assert 0<=when-int(signal['time'])-300<300,(folder.name,day,'Did not use first eligible close',when,int(signal['time']))
            expected_sl=float(prof['val'])-tick if side>0 else float(prof['vah'])+tick
            expected_tp=float(prof['high'] if side>0 else prof['low'])
            assert abs(float(row['stop'])-expected_sl)<tick*.51+1e-7
            assert abs(float(row['target'])-expected_tp)<tick*.51+1e-7
            signal_checks+=1
        assert signal_checks==stats['audit']['signals']
        assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.06
        result=dict(case=folder.name,profile_days_checked=checked,signals_checked=signal_checks,profile_differences=diffs,
                    data_first_utc=datetime.fromtimestamp(int(m1['time'][0]),timezone.utc).isoformat(),
                    data_last_utc=datetime.fromtimestamp(int(m1['time'][-1]),timezone.utc).isoformat(),m1_bars=len(m1),m5_bars=len(m5),
                    profile_match=not diffs,passed=not diffs,report_sha256=stats['report_sha256'])
        results.append(result);print('VERIFIED',folder.name,'profile differences',len(diffs),'signals',signal_checks,flush=True)
    save(ROOT/'verification.json',dict(cases=results,all_passed=len(results)==6 and all(r['passed'] for r in results),source_sha256=sha(ROOT/'Overnight Profile Raw.mq5')))

class UnitTests(unittest.TestCase):
    def test_summer_open(self):
        self.assertEqual(datetime.fromtimestamp(boundaries(datetime(2026,7,1).date())[1],timezone.utc).hour,13)
    def test_winter_open(self):
        self.assertEqual(datetime.fromtimestamp(boundaries(datetime(2026,1,5).date())[1],timezone.utc).hour,14)
    def test_monday_starts_sunday(self):
        start,_=boundaries(datetime(2026,9,14).date())
        d=datetime.fromtimestamp(start,NY);self.assertEqual(d.weekday(),6);self.assertEqual(d.hour,18)
    def test_overnight_length(self):
        start,end=boundaries(datetime(2026,9,18).date());self.assertEqual(end-start,15*3600+30*60)
    def test_m1_profile_bounds(self):
        bars=np.array([(1.,3.,2.,100),(2.,4.,3.,200)],dtype=[('low','f8'),('high','f8'),('close','f8'),('tick_volume','i8')])
        p=profile(bars);self.assertTrue(p['low']<=p['val']<=p['poc']<=p['vah']<=p['high'])
    def test_degenerate_profile(self):
        bars=np.array([(1.,1.,1.,1)],dtype=[('low','f8'),('high','f8'),('close','f8'),('tick_volume','i8')])
        with self.assertRaises(ValueError):profile(bars)
    def test_source_tester_only(self):
        code=(ROOT/'Overnight Profile Raw.mq5').read_text()
        self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',code)
        self.assertIn('AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin',code)
        self.assertNotIn('InpUseAdaptive',code)

if __name__=='__main__':
    import sys
    if '--unit' in sys.argv:unittest.main(argv=[sys.argv[0]])
    else:verify()
