"""Force historical expiry MID-position, and compare with the unexpired benchmark."""
import json,gzip,shutil,re
from datetime import datetime,timezone,timedelta
from build import ROOT,TESTER,build,sha
import test_native as test
b=test.b

def main():
    assert not b.isolated_running() and not b.port_3000_busy()
    b.ROOT=ROOT;b.OUT=ROOT/'tests-expiry';b.OUT.mkdir(exist_ok=True);b.STATUS=b.OUT/'status.json'
    b.CONFIG.update(expert_dir='CalyxClientExpiryTests',periods={'expiry':'2026.06.30'},end_date='2026.07.15')
    destination=TESTER/'MQL5/Experts'/b.CONFIG['expert_dir'];destination.mkdir(exist_ok=True)
    prod=json.loads((ROOT/'manifest.json').read_text());results=[]
    for row in prod['entries']:
        prior=ROOT/'tests-native'/f"nw-{row['symbol']}-{row['slug']}-fixed-3m"/'trades.json.gz'
        first=json.loads(gzip.decompress(prior.read_bytes()))[0]
        op=datetime.fromisoformat(first['open_time']);cl=datetime.fromisoformat(first['close_time'])
        cutoff=op+(cl-op)/2;cutoff=cutoff.replace(microsecond=0,tzinfo=timezone.utc)
        manifest=build(test_expiry=cutoff.isoformat(),only_slug=row['slug'])
        entry=manifest['entries'][0];ex=ROOT/'build-expiry-test'/entry['expert'];shutil.copy2(ex,destination/ex.name)
        tag=row['slug']+'-expiry';inputs=row['inputs']|{'ClientRiskMode':'0','ClientRiskValue':'100'}
        b.CONFIG.update(expert_file=ex.name,period=row['period'],common_inputs=inputs,variants={tag:{'inputs':{}}})
        m=b.run_case(row['symbol'],tag,'expiry');folder=b.OUT/m['case']
        trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
        assert trades,'Expected position opened before expiry'
        assert all(datetime.fromisoformat(t['open_time']).replace(tzinfo=timezone.utc)<cutoff for t in trades),'Entry after expiry'
        match=next(t for t in trades if t['open_time']==first['open_time'])
        assert match['close_time']==first['close_time'],'Expiry changed protective exit time'
        assert abs(match['net_profit']-first['net_profit'])<.02,'Expiry changed existing-position outcome'
        assert datetime.fromisoformat(match['close_time']).replace(tzinfo=timezone.utc)>cutoff
        j=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
        assert 'CLIENT_EXPIRED' in j and 'CLIENT_ENTRY' in j
        assert not m['journal_flags']['critical'] and not m['journal_flags']['init_failed']
        results.append({'slug':row['slug'],'expiry':cutoff.isoformat(),'trades':len(trades),'no_post_expiry_entry':True,
                        'position_managed_through_expiry':True,'exit_time_and_pnl_match':True,'test_ex5_sha256':sha(ex)})
    (ROOT/'EXPIRY_VERIFICATION.json').write_text(json.dumps(results,indent=2))
    print('PASS: all five preserve existing exits and block later entries')
if __name__=='__main__':main()
