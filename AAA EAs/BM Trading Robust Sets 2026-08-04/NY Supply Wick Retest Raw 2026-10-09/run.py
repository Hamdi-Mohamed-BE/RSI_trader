"""NY supply/wick short raw reconstruction: isolated tester, no live writes."""
from pathlib import Path
import gzip, importlib.util, inspect, json, msvcrt, os, re, shutil, sys, traceback

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('ny_supply_native',PRIOR/'run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);n.R=ROOT;n.END='2026.10.09'
SIGNALS=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxNYSupply20261009'

def prepare():
    shutil.copy2(PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh')
    source=inspect.getsource(n.run_case)
    original="inputs['InpRiskPercent']='1.0'"
    assert source.count(original)==1
    source=source.replace(original,"inputs['InpRiskPercent']=row['input_settings']['InpRiskPercent']")
    exec(compile(source,str(ROOT/'run.py')+'::native_helper','exec'),n.__dict__)

def plan():
    source=ROOT/'NY Supply Wick Retest.mq5'
    parameters=dict(InpRiskPercent='0.5',InpATRPeriod='14',InpImpulseBodyATR='1.5',InpMaxImpulseBars='3',InpBullishSearchBars='6',
        InpImpulseCloseBottomFraction='0.25',InpUpperWickBodyRatio='1',InpMinUpperWickFraction='0.25',InpStopBufferATR='0.10',
        InpOpenMinuteNY='570',InpImpulseUntilMinuteNY='630',InpEntryUntilMinuteNY='955',InpCloseMinuteNY='960',
        InpServerUTCOffsetHours='0',InpMagic='26100930',InpDeviationPoints='1000')
    rows=[]
    for window,start in [('3y','2023.10.09'),('2026','2026.01.01')]:
        for label,symbol in [('Gold','XAUUSD'),('US100','USTEC'),('Bitcoin','BTCUSD')]:
            slug='ny-supply-wick-'+symbol.lower()+'-'+window
            inputs={**parameters,'InpSignalAuditTag':slug}
            rows.append(dict(slug=slug,label=label,symbol=symbol,period='M5',window=window,start=start,
                source=str(source),expert=str(source.with_suffix('.ex5')),preset=None,input_settings=inputs,candidate_overrides={},
                production_hashes={str(source):n.sha(source)}))
    value=dict(start='2023.10.09',end_exclusive=n.END,initial_balance=10000,risk_percent_current_balance=.5,cases=rows,
        policy='Raw labelled reconstruction. Defaults frozen before looking at results; no optimisation or deployment.',
        short_only=True,combined_portfolio=False,model=4,execution_delay_ms=150,
        rules=dict(session_anchor='09:30 America/New_York, US daylight saving accounted for, broker UTC 0',
            days='Monday-Friday; no additional US equity holiday filter on these CFDs.',
            displacement='Earliest consecutive bearish M5 leg of 1-3 completed candles within 09:30-10:30; total drop >=1.5x pre-leg ATR14, closing in bottom 25% of combined leg range.',
            zone='Body of the last bullish candle in the six M5 candles before the leg, same NY day and not earlier than 09:00.',
            zone_invalidation='Any later completed M5 close above the origin candle full high retires this first zone for the day; no replacement.',
            retest='A later bearish M5 candle approaches from below, touches the zone with an upper wick, and closes below its lower body edge. Upper wick >= body and >=25% candle range.',
            entry='Market short on first tick after rejection candle closes, until 15:55 ET; at most one successful trade per day.',
            stop='Above max(origin full high, rejection high), plus 0.1x pre-leg ATR.',
            target='Minimum completed M5 low from 09:30 up to the rejection close; locked at entry. Never future/final session low, and NOT fixed 3R.',
            close='First available tick at or after 16:00 ET. No trailing or partials.',
            risk='0.5% closed current balance. Broker lot steps rounded down; undersized or invalid/margin-constrained trades skipped.'),
        reference_clock_sources=['https://www.nyse.com/trade/trading-information','https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst'],
        limitations=['No original code/chart timeframe supplied; impulse, wick thresholds, zone bounds, cutoff, stop buffer and time exit are reconstruction assumptions.',
            'The $50 gold fall is an example, not a transferable fixed threshold.','Pre-2026 broker ticks may be generated; inspect native quality and disclose.',
            'A three-year screen is not untouched out-of-sample evidence.'],live_changes=False)
    path=ROOT/'PLAN.json'
    if path.exists():assert n.read(path)==value,'Frozen reconstruction changed'
    else:n.save(path,value)
    return value

def main():
    prepare();p=plan();state=dict(total=6,complete={},failed={},live_changes=False)
    status=ROOT/'RUN_STATUS.json'
    if status.exists():state=n.read(status)
    for row in p['cases']:
        if row['slug'] in state['complete']:continue
        if sys.argv[1:] and sys.argv[1]!='all' and row['symbol'] not in sys.argv[1:]:continue
        try:
            n.START=row['start'];binary,build=n.build(row)
            result=n.run_case(row,'raw',binary,build)
            folder=ROOT/'native'/result['tag'];signal_file=SIGNALS/(row['slug']+'.csv')
            owned=n.read(folder/'owned-process.json')
            assert signal_file.is_file() and signal_file.stat().st_mtime>=owned['started']-2
            shutil.copy2(signal_file,folder/'signals.csv')
            signals=n.export_rows(folder/'signals.csv')
            assert len(signals)==len(result['trades']),(len(signals),len(result['trades']))
            matched=[]
            for s,t in zip(signals,result['trades']):
                assert int(s['origin_epoch'])<int(s['impulse_end_epoch'])<=int(s['rejection_start_epoch'])<int(s['signal_close_epoch'])<=t['open_epoch']
                assert abs(float(s['target'])-t['tp'])<1e-7 and abs(float(s['stop'])-t['sl'])<1e-7
                assert t['side']=='Short' and t['exit_legs']==1
                assert float(s['lots'])==t['volume']
                matched.append(dict(position_id=t['position_id'],signal=s))
            journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
            diagnostics=sorted(set(re.findall(r'NYSUPPLY_STATS[^\r\n]*',journal)))
            assert len(diagnostics)==1,diagnostics
            result.update(signal_audit=matched,diagnostics=diagnostics,known_target_at_entry_verified=True,
                tester_end_liquidations=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in result['trades']))
            n.save(folder/'results.json',result)
            state['complete'][row['slug']]=dict(path=str(folder/'results.json'),history_quality=result['native']['history_quality'],trades=len(result['trades']))
            state['failed'].pop(row['slug'],None)
        except Exception as error:
            state['failed'][row['slug']]=dict(error=str(error),trace=traceback.format_exc()[-5000:]);print('FAILED '+row['slug']+' '+str(error),flush=True)
        n.save(status,state);print('PROGRESS '+str(len(state['complete']))+'/6; failed='+str(len(state['failed'])),flush=True)
    print('RAW BATCH FINISHED; no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        n.available();main()
