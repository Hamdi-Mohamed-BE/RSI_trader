"""Independent read-only evidence checks; does not connect to MT5."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import gzip, hashlib, json, re, unittest
import search

ROOT=Path(__file__).resolve().parent
NY=ZoneInfo('America/New_York')

def must_flat(c,epoch):
    t=datetime.fromtimestamp(epoch,timezone.utc)
    return bool((c['flat'] and t.hour>=21)
        or (not c['weekend'] and (t.weekday()>=5 or (t.weekday()==4 and t.hour>=20)))
        or (c['exit']==3 and t.astimezone(NY).hour>=16))

def streaks(pnl):
    wins=[];losses=[];current=0;sign=0
    for p in pnl+[0]:
        s=1 if p>0 else -1 if p<0 else 0
        if s!=sign:
            if current:(wins if sign==1 else losses).append(current)
            current=0
        if s:current+=1
        sign=s
    return dict(max_win=max(wins,default=0),max_loss=max(losses,default=0),
                average_win=sum(wins)/len(wins) if wins else 0,
                average_loss=sum(losses)/len(losses) if losses else 0)

class Helpers(unittest.TestCase):
    def test_streaks_zero_breaks(self):
        self.assertEqual(streaks([1,1,0,-1,-1,-1,1,-1]),dict(max_win=2,max_loss=3,average_win=1.5,average_loss=2))
    def test_flat_boundaries(self):
        c=search.DEFAULT|dict(flat=1)
        for value,expected in [('2026-09-23T20:59:59',False),('2026-09-23T21:00:00',True),('2026-09-24T00:00:00',False)]:
            self.assertEqual(must_flat(c,datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()),expected)
    def test_weekend_boundaries(self):
        c=search.DEFAULT|dict(weekend=0)
        for value,expected in [('2026-09-25T19:59:59',False),('2026-09-25T20:00:00',True),('2026-09-26T01:00:00',True),('2026-09-27T23:59:59',True),('2026-09-28T00:00:00',False)]:
            self.assertEqual(must_flat(c,datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()),expected)
    def test_ny_dst_boundaries(self):
        c=search.DEFAULT|dict(exit=3)
        for value,expected in [('2026-01-09T20:59:59',False),('2026-01-09T21:00:00',True),('2026-07-10T19:59:59',False),('2026-07-10T20:00:00',True)]:
            self.assertEqual(must_flat(c,datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()),expected)
    def test_active_axes(self):
        for strategy in [0,2]:
            for stop in range(6):
                for exit_mode in range(5):
                    c=search.DEFAULT|dict(stop=stop,exit=exit_mode,trail=2 if exit_mode==1 else 0)
                    cases,axes=search.neighborhood(c,strategy)
                    self.assertGreaterEqual(len(axes),2)
                    self.assertNotIn('ttl',axes if strategy==0 else [])
                    self.assertNotIn('sl',axes if stop>=3 else [])
                    self.assertNotIn('rr',axes if exit_mode not in [0,4] else [])
                    self.assertIn(c,cases)
                    self.assertEqual(len(cases),len({search.digest(x) for x in cases}))
    def test_source_safety(self):
        core=(ROOT/'EA/RawCore.mqh').read_text()
        logic=(ROOT/'EA/SearchLogic.mqh').read_text()
        self.assertIn('MQL_TESTER',core)
        self.assertIn('if(MustFlat(now))return false;',logic)
        self.assertIn('bool flat=MustFlat(now);',logic)
        self.assertIn('ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',logic)
        self.assertIn('savedPeak[k]-side*C(8)*atr',logic)
        self.assertEqual(search.sha(ROOT/'EA/RawCore.mqh'),search.sha(search.RAW/'Liquidity.mq5'))
    def test_stage_space(self):
        for symbol in ['XAUUSD','BTCUSD','US30']:
            for stage in ['timeframe','entry','stop','trailing','rr_exit','session','direction','filters','management','levels']:
                for p in search.patches(stage,symbol):
                    self.assertTrue(set(p)<=set(search.FIELDS))
                    self.assertTrue(all(isinstance(v,(int,float)) for v in p.values()))

def audit():
    folders=[]
    for folder in sorted(search.OUT.iterdir()):
        if not (folder/'results.json').exists():continue
        manifest=json.loads((folder/'manifest.json').read_text())
        assert manifest['logic']==search.sha(folder/'SearchLogic.mqh')
        assert manifest['core']==search.sha(folder/'RawCore.mqh')==search.sha(search.RAW/'Liquidity.mq5')
        assert manifest['protocol']==search.sha(ROOT/'PROTOCOL.md')
        assert '0 errors, 0 warnings' in search.read(folder/'compile.log')
        ini=(folder/'tester.ini').read_text(encoding='utf-8-sig')
        assert all(s in ini for s in ['Enabled=0','AllowLiveTrading=0','AllowDllImport=0','UseRemote=0','UseCloud=0','ExecutionMode=150'])
        rows=json.loads((folder/'results.json').read_text());assert len(rows)==len(manifest['cases'])
        assert {r['index'] for r in rows}==set(range(len(rows)))
        for r in rows:
            assert r['parameters']==manifest['cases'][r['index']]
            assert r['source_sha']==search.sha(folder/'Liquidity Search.ex5')
            assert r['net']==json.loads((folder/f"net-{r['index']}.json").read_text())
        rec=dict(batch=folder.name,cases=len(rows),native_model=manifest['model'],compile_clean=True)
        if not manifest['optimize']:
            trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
            ids=[t['position_id'] for t in trades];assert len(ids)==len(set(ids))
            n=rows[0]['net'];assert len(trades)==n['trades']
            assert abs(sum(t['net_profit'] for t in trades)-n['net_profit'])<1e-5
            for t in trades:
                assert abs(t['net_profit']-sum(t[k] for k in ['gross_profit','commission','swap','fee']))<1e-5
                assert t['open_epoch']<=t['close_epoch']
                assert t['volume']>0 and abs(t['volume']-t['closed_volume'])<1e-7
                assert t['magic'] in ([9278120,9278121] if manifest['strategy']==2 else [9278120])
                assert t['open_time']>=manifest['start'].replace('.','-')
            pnl=[t['net_profit'] for t in trades];gp=sum(p for p in pnl if p>0);gl=-sum(p for p in pnl if p<0)
            pf=gp/gl if gl else 99 if gp else 0
            assert abs(pf-n['profit_factor'])<1e-7
            assert abs(100*sum(p>0 for p in pnl)/max(1,len(pnl))-n['win_rate_pct'])<1e-7
            # Native equity DD intentionally remains native, not reconstructed from closes.
            rec.update(trades=len(trades),grouped_net=round(sum(pnl),2),engines={str(m):sum(t['magic']==m for t in trades) for m in sorted({t['magic'] for t in trades})},streaks=streaks(pnl))
            # Second-resolution histories cannot order instantaneous round trips;
            # exclude those and close before open on ties for a lower-bound peak.
            events=[]
            for t in trades:
                if t['close_epoch']>t['open_epoch']:
                    events.extend([(t['open_epoch'],1,t['magic']),(t['close_epoch'],-1,t['magic'])])
            counts={};peak=0;both=0
            for _,change,magic in sorted(events):
                counts[magic]=counts.get(magic,0)+change
                assert 0<=counts[magic]<=manifest['cases'][0]['max_pos']
                peak=max(peak,sum(counts.values()))
                both+=int(counts.get(9278120,0)>0 and counts.get(9278121,0)>0)
            assert not any(counts.values())
            rec.update(max_overlapping_positions_lower_bound=peak,combined_engine_overlap_observed=bool(both))
            journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
            requests=set(re.findall(r'LC_EXT_ORDER level=(\d+) engine=(\d+) at=(\d+) risk=([.\d]+) budget=([.\d]+)',journal))
            c=manifest['cases'][0]
            assert all(not must_flat(c,int(x[2])) for x in requests),'Entry request after forced-flat cutoff'
            ratios=[float(x[3])/float(x[4]) for x in requests if float(x[4])>0]
            rec.update(unique_entry_requests=len(requests),max_planned_risk_over_budget_ratio=max(ratios,default=None),risk_rounding='UP preserved from raw; not a guaranteed monetary cap')
        folders.append(rec)
    result=dict(scope='completed native-v2 evidence only',batches=len(folders),cases=sum(r['cases'] for r in folders),checks=folders)
    search.save(ROOT/'VERIFICATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Helpers)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    audit()
