"""42 frozen native Gann-inspired/control cases; isolated tester only, no live API."""
from pathlib import Path
import gzip, importlib.util, inspect, json, msvcrt, os, re, shutil, sys, traceback

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('gann_native',PRIOR/'run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);n.R=ROOT;n.END='2026.10.09'
SIGNALS=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGann20261009'
IDEAS=[('eighth-rejection',0,'Range box: eighth rejection'),('range-breakout',1,'Range box: breakout/retest'),
       ('swing-fan',2,'Swing-scaled 1x1 fan'),('ema-baseline',3,'EMA cross: unfiltered control'),
       ('time-cycle',4,'Time-cycle gate: 8/16/32 bars'),('random-cycle',5,'Random time-window control'),
       ('quartile-control',6,'Quartile rejection control')]

def prepare():
    shutil.copy2(PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh')
    source=inspect.getsource(n.run_case)
    old="inputs['InpRiskPercent']='1.0'";assert source.count(old)==1
    source=source.replace(old,"inputs['InpRiskPercent']=row['input_settings']['InpRiskPercent']")
    exec(compile(source,str(ROOT/'run.py')+'::native_helper','exec'),n.__dict__)

def plan():
    source=ROOT/'Gann Research.mq5';rows=[]
    common=dict(InpRiskPercent='0.5',InpATRPeriod='14',InpPivotNeighbours='2',InpFanMaxH4Bars='32',
        InpRetestBars='8',InpTargetR='2',InpStopBufferATR='0.25',InpRetestBufferATR='0.10',
        InpCloseMinuteUTC='1255',InpEntryUntilMinuteUTC='1230',InpMaxHoldMinutes='480',
        InpServerUTCOffsetHours='0',InpRandomSeed='26100950',InpMagic='26100950',InpDeviationPoints='1000')
    for window,start in [('3y','2023.10.09'),('2026','2026.01.01')]:
        for asset,symbol,signal,reference in [('Gold','XAUUSD','M15','PERIOD_D1'),('US100','USTEC','M5','PERIOD_D1'),('Bitcoin','BTCUSD','M15','PERIOD_W1')]:
            for code,idea,label in IDEAS:
                period='H1' if idea in [3,4,5] else signal
                slug=f'gann-{symbol.lower()}-{code}-{window}'
                tf_values={'M5':'5','M15':'15','H1':'16385','PERIOD_D1':'16408','PERIOD_W1':'32769'}
                inputs={**common,'InpIdea':str(idea),'InpSignalTF':tf_values[period],'InpReferenceTF':tf_values[reference],'InpSignalAuditTag':slug}
                rows.append(dict(slug=slug,label=label,asset=asset,idea=code,symbol=symbol,period=period,window=window,start=start,
                    source=str(source),expert=str(source.with_suffix('.ex5')),preset=None,input_settings=inputs,
                    candidate_overrides={},production_hashes={str(source):n.sha(source)}))
    value=dict(cases=rows,initial_balance=10000,risk_percent_current_balance=.5,start='2023.10.09',end_exclusive=n.END,
        final_two_year_validation=['2024.10.09',n.END],recent_slices_months=[3,6,12],fresh_real_tick_window=['2026.01.01',n.END],
        model=4,execution_delay_ms=150,live_changes=False,optimized=False,portfolio=False,
        policy='All hypotheses and controls frozen before outcomes. First year is descriptive; final two years are held-out relative to this frozen screen, NOT globally untouched data. No optimisation or candidate selection.',
        rules=dict(reference='Last completed broker-UTC D1 range for gold/US100; last completed Monday-UTC W1 range for BTC. Frozen until next reference period.',
            rejection='Bullish close inside lower eighth after touching its boundary: long to midpoint, stop below min(previous range low, signal low)-0.1 ATR. Mirror shorts in upper eighth. Quartile control changes only fraction from 1/8 to 1/4.',
            range_breakout='Completed close crosses prior range high/low; require a later directional candle to retest boundary within eight signal bars and close outside. Stop beyond boundary/retest wick by 0.25 ATR; target 2R.',
            fan='Confirmed H4 body-independent high/low pivots: strict two completed neighbours on each side. Ascending fan from a higher low, descending from lower high. Slope frozen from price change between latest two confirmed same-type pivots divided by their tradable H4-bar separation (at least four). One 1x1 slope tested, maximum age 32 H4 bars; completed break followed by retest within eight signal bars. Stop wick/line +0.25 ATR; target 2R.',
            cycles='H1 EMA12/26 crossover; stop 1.5 ATR14, target 2R. Gate permits signals at H1 trading-bar ages 8/16/32 +/-1 after latest H4 pivot CONFIRMATION, not its hindsight timestamp. New pivot replaces clock. Baseline has no gate.',
            random_control='Seed 26100950 and pivot confirmation timestamp generate three separated centres in 2..32, +/-1-bar windows: same nine of 33 eligible ages as cycle gate. Fixed before outcomes; one native placebo, not proof from a single random comparison.',
            execution='Next tick after completed signal; at most one successful trade per UTC day and one position per independent account. No additional session/news/ADX/DI filters; BTC weekends included. Entry through 20:30 UTC, close at first tick >=20:55 UTC or after eight hours. No trailing/partials.',
            risk='0.5% current closed balance; volume floored to broker step. Skip below-minimum lots, invalid price geometry or insufficient margin. Cash risk is nominal, not guaranteed maximum loss.'),
        sources=['https://www.tradingview.com/support/solutions/43000518149-gann-square-drawing-tool/',
            'https://www.tradingview.com/support/solutions/43000518152-gann-box-drawing-tool/'],
        limitations=['These are declared Gann-inspired mechanical adaptations, not an exact historical Gann system or evidence of predictive geometry.',
            'Broker pre-2026 ticks may be generated from M1 history. Fresh 2026 quality checked separately.',
            'Seven hypotheses per asset create selection risk. Show all outcomes; no best-set selection on validation.',
            'Daily/session stops and retest/ATR/EMA thresholds are research assumptions. First screening is not a full optimized pipeline.'])
    path=ROOT/'PLAN.json'
    if path.exists():assert n.read(path)==value,'Frozen rules/source changed'
    else:n.save(path,value)
    return value

def verify_signals(result,folder):
    signals=n.export_rows(folder/'signals.csv');trades=sorted(result['trades'],key=lambda t:t['open_epoch'])
    assert len(signals)==len(trades),(len(signals),len(trades))
    balance=10000;matched=[]
    for signal,trade in zip(signals,trades):
        assert int(signal['signal_start_epoch'])<int(signal['signal_close_epoch'])<=trade['open_epoch']
        assert int(signal['feature_known_epoch'])<=int(signal['signal_close_epoch'])
        assert not int(signal['anchor_epoch']) or int(signal['anchor_epoch'])<int(signal['feature_known_epoch'])
        assert abs(float(signal['requested_risk_usd'])-balance*.005)<=.011
        assert abs(float(signal['stop'])-trade['sl'])<1e-7 and abs(float(signal['target'])-trade['tp'])<1e-7
        assert float(signal['lots'])==trade['volume'] and trade['exit_legs']==1
        assert trade['side']==('Long' if int(signal['side'])>0 else 'Short')
        assert float(signal['stop'])<float(signal['requested_entry'])<float(signal['target']) if int(signal['side'])>0 else float(signal['target'])<float(signal['requested_entry'])<float(signal['stop'])
        if int(signal['idea'])==4:assert any(abs(float(signal['age'])-c)<=1 for c in [8,16,32])
        if int(signal['idea'])==5:assert any(abs(float(signal['age'])-int(signal['random'+str(i)]))<=1 for i in [1,2,3])
        matched.append(dict(position_id=trade['position_id'],signal=signal));balance+=trade['net']
    result['signal_audit']=matched;result['known_at_entry_verified']=True

def main():
    prepare();p=plan();state=dict(total=len(p['cases']),complete={},failed={},live_changes=False)
    status=ROOT/'RUN_STATUS.json'
    if status.exists():state=n.read(status)
    for row in p['cases']:
        if row['slug'] in state['complete']:continue
        if len(sys.argv)>1 and sys.argv[1]!='all' and row['symbol'] not in sys.argv[1:]:continue
        try:
            n.START=row['start'];binary,build=n.build(row);result=n.run_case(row,'raw',binary,build)
            folder=ROOT/'native'/result['tag'];signal_file=SIGNALS/(row['slug']+'.csv')
            owned=n.read(folder/'owned-process.json')
            assert signal_file.is_file() and signal_file.stat().st_mtime>=owned['started']-2
            shutil.copy2(signal_file,folder/'signals.csv');verify_signals(result,folder)
            journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
            diagnostics=sorted(set(re.findall(r'GANN_STATS[^\r\n]*',journal)));assert len(diagnostics)==1
            result.update(diagnostics=diagnostics,tester_end_liquidations=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in result['trades']))
            # A stop-distance rejection after the native 150 ms execution delay
            # is realistic execution friction, not a failed simulation. Record it;
            # do not manufacture the rejected trade or change frozen price rules.
            fatal=['init_failed','runtime','history','stopout','invalid_volume','export_failed']
            assert not any(result['flags'][k] for k in fatal),result['flags']
            result['execution_rejections']=int(re.search(r' rejected=(\d+)',diagnostics[0]).group(1))
            if row['window']=='2026':
                assert result['native']['history_quality']=='100% real ticks',result['native']['history_quality']
                assert not re.search('real ticks absent|ticks discarded',journal,re.I)
            n.save(folder/'results.json',result)
            state['complete'][row['slug']]=dict(path=str(folder/'results.json'),history_quality=result['native']['history_quality'],trades=len(result['trades']))
            state['failed'].pop(row['slug'],None)
        except Exception as error:
            state['failed'][row['slug']]=dict(error=str(error),trace=traceback.format_exc()[-5000:]);print('FAILED '+row['slug']+' '+str(error),flush=True)
        n.save(status,state);print('PROGRESS '+str(len(state['complete']))+'/'+str(state['total'])+'; failed='+str(len(state['failed'])),flush=True)
    print('FROZEN GANN RAW BATCH FINISHED; no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);n.available();main()
