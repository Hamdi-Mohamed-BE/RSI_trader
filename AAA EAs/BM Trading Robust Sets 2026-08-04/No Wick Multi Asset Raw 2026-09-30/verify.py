"""Final evidence checks only: does not launch a terminal or send orders."""
import gzip,hashlib,json
from pathlib import Path
from analyse import trade_statistics
from run_study import tick_notes

ROOT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    cfg=json.loads((ROOT/'run-config.json').read_text())
    analysis=json.loads((ROOT/'ANALYSIS.json').read_text())
    assert analysis['complete'] and analysis['completed_runs']==72
    source=sha(ROOT/cfg['source']);binary=sha((ROOT/cfg['source']).with_suffix('.ex5'))
    build=json.loads((ROOT/'native/build.json').read_text())
    for name,expected in build['dependencies'].items():assert sha(ROOT.parent/name)==expected,name
    expected={(s,v,p) for s,v in cfg['matrix'] for p in cfg['main_periods']}
    expected|={(s,v.replace('S','C'),p) for s,v in cfg['matrix'] for p in cfg['control_periods']}
    expected.add(('EURUSD','S15','smoke'))
    seen=set();trade_count=0;signal_count=0;qualities=set()
    for r in analysis['runs']:
        key=(r['symbol'],r['variant'],r['period']);assert key not in seen,key
        seen.add(key);folder=ROOT/'native'/r['case'];a=r['audit']
        assert a['source_sha256']==source and a['ex5_sha256']==binary,r['case']
        assert a['exact_inputs'] and a['ledger_reconciled'],r['case']
        assert not r['journal_flags']['init_failed'] and not r['journal_flags']['critical'],r['case']
        assert sha(folder/'trades.json.gz')==a['trades_sha256'],r['case']
        report=gzip.decompress((folder/(r['case']+'.htm.gz')).read_bytes())
        assert hashlib.sha256(report).hexdigest()==r['report_sha256'],r['case']
        assert hashlib.sha256((folder/(r['case']+'.set')).read_text().encode()).hexdigest()==r['set_sha256'],r['case']
        ini=(folder/'tester.ini').read_text()
        for setting in ('Model=4','ExecutionMode=150','Enabled=0','AllowLiveTrading=0','UseRemote=0','UseCloud=0'):
            assert setting in ini,(r['case'],setting)
        trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
        net=trade_statistics(trades,r['start'],r['end_exclusive'],r['symbol'])
        assert net==r['net'],r['case']
        assert abs(net['net_profit']-r['metrics']['net_profit'])<=max(.05,len(trades)*.011),r['case']
        journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
        assert tick_notes(journal)==a['tick_notes'],r['case']
        assert a['signals_logged']==a['causal_and_1R_checks'],r['case']
        trade_count+=len(trades);signal_count+=a['causal_and_1R_checks']
        if r['period']=='6m':qualities.add(r['metrics']['history_quality'])
    assert seen==expected,(expected-seen,seen-expected)
    result=dict(passed=True,native_runs=len(seen),planned_runs=72,separate_smoke_runs=1,
        ledger_trades_reconciled=trade_count,logged_placement_checks_including_duplicate_journal_lines=signal_count,
        six_month_quality=sorted(qualities),source_sha256=source,ex5_sha256=binary,
        dependencies_unchanged=True,report_and_ledger_hashes_match=True,postprocessing_tick_note_parity=True,
        live_deployment=False)
    (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
