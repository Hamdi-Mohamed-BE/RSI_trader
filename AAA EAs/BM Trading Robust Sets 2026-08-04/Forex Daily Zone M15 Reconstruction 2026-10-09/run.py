"""Approved raw reconstruction. Isolated tester only; no live-account API."""
from pathlib import Path
import copy, gzip, importlib.util, inspect, json, msvcrt, os, re, shutil, sys, traceback

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('zone_native_helper',PRIOR/'run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.R=ROOT;n.START='2023.10.09';n.END='2026.10.09'

def prepare():
    shutil.copy2(PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh')
    source=inspect.getsource(n.run_case)
    old="inputs['InpRiskPercent']='1.0'"
    assert source.count(old)==1
    source=source.replace(old,"inputs['InpRiskPercent']=row['input_settings']['InpRiskPercent']")
    # MT5 reports datetime inputs as Unix epochs, not the human-readable SET date.
    original_same=n.h._same_setting
    def same_setting(a,b):
        if re.match(r'^\d{4}\.\d{2}\.\d{2} ',str(a)) and str(b).isdigit():
            return int(n.pd.Timestamp(str(a).replace('.','-'),tz='UTC').timestamp())==int(b)
        return original_same(a,b)
    n.h._same_setting=same_setting
    exec(compile(source,str(ROOT/'run.py')+'::native_runner','exec'),n.__dict__)
    # A completed native run can be adopted after fixing this representation-only
    # verifier. Reconcile its original manifest, source, report, journal and CSVs;
    # never substitute another run or skip input/warmup/cash checks.
    tail=source[source.index(' actual=h._report_inputs(report)'):]
    code='def recover_tail(row,variant,binary,build_info,tag,out,inputs,report,journal,flags,began,slug):\n'+tail
    exec(compile(code,str(ROOT/'run.py')+'::recover_verifier','exec'),n.__dict__)

def recover_finished(row,variant,binary,build):
    tag='allrr05-'+row['slug']+'-'+variant;out=ROOT/'native'/tag
    if not (out/'journal.txt.gz').exists():return None
    report=n.T/'reports/rr05-all-20261008'/(tag+'.htm')
    owned=n.read(out/'owned-process.json');began=owned['started']
    assert report.is_file() and report.stat().st_mtime>=began-2
    manifest=n.read(out/'manifest.json')
    assert manifest['build']==build and manifest['start']==n.START and manifest['end_exclusive']==n.END
    inputs={**row['input_settings'],'InpRR05AuditTag':tag}
    assert manifest['inputs']==inputs and manifest['symbol']==row['symbol']
    journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
    flags={key:len(re.findall(pattern,journal,re.I)) for key,pattern in {
        'init_failed':'initialization failed','runtime':'access violation|array out of range|zero divide',
        'history':'testing start time changed|not enough history','stopout':'stop out|margin call',
        'invalid_stops':'invalid stops','invalid_volume':'invalid volume','export_failed':'RR05_EXPORT_FAILED'}.items()}
    assert not any(flags.values()),flags
    assert 'RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal
    return n.recover_tail(row,variant,binary,build,tag,out,inputs,report,journal,flags,began,row['slug'])

def plan():
    source=ROOT/'Daily Zone Reconstruction.mq5'
    common=dict(InpRiskPercent='0.5',InpStopBufferPips='6',InpRewardRisk='2',InpLookbackCalendarDays='730',
        InpMinZonePips='5',InpMaxZonePips='60',InpMagic='26100915',InpDeviationPoints='30')
    rows=[]
    for window,analysis_start,engine_start in [('3y','2023.10.09','2021.10.09'),('2026','2026.01.01','2024.01.01')]:
        for symbol in ('EURUSD','GBPUSD','USDJPY'):
            for high_water in (False,True):
                mode='high-water' if high_water else 'current-balance'
                slug='forex-daily-zone-'+symbol.lower()+'-'+mode+'-full-warmup-'+window
                inputs={**common,'InpHighWaterSizing':str(high_water).lower(),'InpTradingFrom':analysis_start+' 00:00:00'}
                rows.append(dict(slug=slug,label=symbol+' '+mode,symbol=symbol,period='M15',source=str(source),
                    expert=str(source.with_suffix('.ex5')),preset=None,input_settings=inputs,candidate_overrides={},
                    production_hashes={str(source):n.sha(source)},mode=mode,window=window,analysis_start=analysis_start,engine_start=engine_start))
    result=dict(version=2,start='2023.10.09',end_exclusive=n.END,cases=rows,initial_balance=10000,risk_percent=0.5,
        interpretation='Approved mechanical reconstruction, NOT exact published-study replication.',
        source_video='https://www.youtube.com/watch?v=HzVSi9ux1NU',original_rules_video='https://www.youtube.com/watch?v=nFIJ0z8_01w',
        source_rules=dict(daily_body_zones=True,min_independent_touches=3,zone_width_pips=[5,60],zone_age_calendar_days=730,
            entry='M15 closes inside a zone after the previous completed close was outside. Approach from above buys, from below sells.',
            stop_buffer_pips=6,target_r=2,no_bias_trend_pattern_retest_or_session_filters=True,no_active_trade_management=True),
        reconstruction_assumptions=dict(pivot_confirmation='2 completed D1 bars on either side of body high/low; never wicks.',
            zone_clustering='Price-sorted pivots greedily clustered into disjoint bands of maximum 60 pips; minimum 5-pip centered padding.',
            duplicate_touches='Multiple pivots from a single daily candle count once within each band.',
            aging='Daily rebuild from only the last 730 calendar days; breaks do not invalidate bands.',
            target='Fixed 2R proxy, not the original nearest-structure variable target.',
            concurrency='One open position per pair; signals during an open position skipped, no queue.',
            high_water='Highest observed closed account balance per isolated pair, not floating equity or a combined FX account.'),
        model=4,delay_ms=150,broker='Exness research feed',live_changes=False,optimization=False,unseen_oos_claim=False)
    file=ROOT/'PLAN-V2.json'
    if file.exists():assert n.read(file)==result,'Frozen plan changed'
    else:n.save(file,result)
    return result

def main():
    prepare();p=plan();state=dict(total=12,complete={},failed={},no_live_changes=True)
    state_path=ROOT/'RUN_STATUS-V2.json'
    if state_path.exists():state=n.read(state_path)
    for row in p['cases']:
        if row['slug'] in state['complete']:continue
        if sys.argv[1:] and sys.argv[1]!='all' and row['symbol'] not in sys.argv[1:]:continue
        try:
            n.START=row['engine_start']
            binary,build=n.build(row)
            variant='raw-'+row['window']
            result=recover_finished(row,variant,binary,build) or n.run_case(row,variant,binary,build)
            journal=gzip.decompress((ROOT/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
            assert 'ZONE_HISTORY_INSUFFICIENT' not in journal,'Insufficient two-year zone warmup'
            assert 'ZONE_WARMUP' in journal and 'ZONE_STATS' in journal,'Missing reconstruction diagnostics'
            first=n.pd.Timestamp(row['analysis_start'].replace('.','-'),tz='UTC').timestamp()
            assert all(t['open_epoch']>=first for t in result['trades']),'An order was placed in the no-trade warmup'
            result['analysis_window']=[row['analysis_start'],n.END]
            result['warmup_engine_start']=row['engine_start']
            active_trace=[t for t in n.export_rows(ROOT/'native'/result['tag']/'equity.csv') if int(t['epoch'])>=first]
            result['metrics']=n.metrics(result['trades'],active_trace,result['native'])
            result['zone_diagnostics']=re.findall(r'ZONE_(?:WARMUP|STATS)[^\r\n]*',journal)
            result['tester_end_liquidations']=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in result['trades'])
            n.save(ROOT/'native'/result['tag']/'results.json',result)
            state['complete'][row['slug']]=dict(path=str(ROOT/'native'/result['tag']/'results.json'),trades=len(result['trades']),
                history_quality=result['native']['history_quality'],seconds=result['seconds'])
            state['failed'].pop(row['slug'],None)
        except Exception as error:
            state['failed'][row['slug']]=dict(error=str(error),trace=traceback.format_exc()[-5000:])
            print('FAILED '+row['slug']+' '+str(error),flush=True)
        n.save(state_path,state)
        print('PROGRESS '+str(len(state['complete']))+'/12; failures='+str(len(state['failed'])),flush=True)
    print('RAW RECONSTRUCTION BATCH FINISHED; no deployment',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        n.available();main()
