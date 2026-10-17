"""Frozen 2-ATR VWAP discount reconstruction, user-requested 1R, isolated MT5 only."""
from pathlib import Path
import gzip, importlib.util, json, math, msvcrt, os, re, shutil, sys, traceback

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('vwap_native',PRIOR/'run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.R=ROOT;n.END='2026.10.10'
SIGNALS=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxVWAPRaw20261010'
ASSETS=[('US30','US30'),('US100','USTEC'),('UK100','UK100'),('Gold','XAUUSD'),('Ethereum','ETHUSD'),('Bitcoin','BTCUSD'),
        ('EURUSD','EURUSD'),('GBPUSD','GBPUSD'),('USDJPY','USDJPY'),('USDCHF','USDCHF'),('USDCAD','USDCAD'),('AUDUSD','AUDUSD'),('NZDUSD','NZDUSD')]

def prepare():
    shutil.copy2(PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh')

def plan():
    source=ROOT/'VWAP Mean Reversion Raw.mq5';rows=[]
    common=dict(InpRiskPercent='1.0',InpATRPeriod='14',InpDiscountATR='2.0',InpStopATR='1.0',InpRewardRisk='1.0',
        InpMinSessionBars='15',InpEntryUntilMinuteUTC='1430',InpCloseMinuteUTC='1435',InpServerUTCOffsetHours='0',
        InpMagic='26101021',InpDeviationPoints='1000')
    for window,start in [('1y','2025.10.10'),('3y','2023.10.10')]:
        for label,symbol in ASSETS:
            slug=f'vwap-2atr-1r-{symbol.lower()}-{window}'
            rows.append(dict(slug=slug,label=label,symbol=symbol,period='M5',window=window,start=start,
                source=str(source),expert=str(source.with_suffix('.ex5')),preset=None,
                input_settings={**common,'InpSignalAuditTag':slug},candidate_overrides={},production_hashes={str(source):n.sha(source)}))
    value=dict(cases=rows,initial_balance_usd=10000,risk_percent_current_closed_balance=1,
        start='2023.10.10',end_exclusive=n.END,windows=['1y','3y'],model=4,execution_delay_ms=150,
        interpretation='Raw mechanical reconstruction, NOT exact source replication or optimisation. User explicitly requested 1:1 RR.',
        directions='Long only',combined_portfolio=False,optimization=False,live_changes=False,
        source_corroboration='https://www.linkedin.com/posts/pickmytrade_vwap-pickmytrade-activity-7510312610387640320-fq9G',
        source_status='A matching secondary repost transcribes 2 ATR, not literal 280R. Original code/complete rules unavailable; reported returns unverified.',
        rules=dict(timeframe='Completed M5 candles; enter at next available tick, never signal close fill.',
            vwap='UTC 00:00 daily reset. Sum of completed M5 HLC3 times broker tick volume divided by cumulative tick volume, INCLUDING signal bar. Minimum 15 positive-volume bars. Same anchor on every asset.',
            signal='First completed close with (VWAP-close)/ATR14 >= 2 while armed; no reversal/bullish/RSI/DI/ADX/news filter.',
            rearm='After a completed close back inside the 2-ATR boundary or new UTC session. One attempt per excursion; signals while a position is open skipped, no queue.',
            stop='1x completed signal M5 ATR14 below requested ask entry; rounded to nearest broker tick.',
            target='1x actual requested-entry-to-rounded-stop distance above requested ask entry. Fixed 1R, NOT a full return to VWAP.',
            session='All broker tradable sessions, entries through 23:50 UTC; flat on first available tick >=23:55 UTC, or next UTC day if no closing tick. Crypto weekends included.',
            management='No trailing, partials, breakeven, pyramiding or opposite-side hedge. One open position per independent asset account.',
            sizing='1% current closed balance nominal stop risk. OrderCalcProfit converts to USD; floor broker lot step. Skip below minimum size, invalid stops or margin constraint.',
            costs='Native broker bid/ask, commission, swap and 150ms delay. Stops/targets sent with order relative to requested quote; realised R can differ due to fills/gaps/costs.'),
        limitations=['Timeframe, ATR period/stop, VWAP/session anchor, warmup, rearming and time exit are reconstruction assumptions.',
            'Broker tick volume is not consolidated exchange traded volume, including on crypto CFDs; not NQ futures replication.',
            'Older real-tick availability varies by asset and is disclosed; Model4 can include generated ticks.',
            'One frozen parameter set on all assets; no best-parameter search, holdout claim or live promotion.',
            'Individual independently funded accounts, not summed or shared portfolio results. Nominal 1% risk is not a guaranteed maximum loss.'])
    path=ROOT/'PLAN.json'
    if path.exists():assert n.read(path)==value,'Frozen plan changed'
    else:n.save(path,value)
    return value

def verify(result,folder):
    signals=n.export_rows(folder/'signals.csv');trades=sorted(result['trades'],key=lambda x:x['open_epoch'])
    assert len(signals)==len(trades),(len(signals),len(trades))
    balance=10000;net_r=[]
    for s,t in zip(signals,trades):
        assert int(s['session_start_epoch'])<=int(s['signal_start_epoch'])<int(s['signal_close_epoch'])<=t['open_epoch']
        assert int(s['signal_start_epoch'])+300==int(s['signal_close_epoch'])
        assert float(s['discount_atr'])>=2-1e-7 and int(s['positive_session_bars'])>=15
        # MQL serialises price and ATR to 8 decimals. Propagate that bounded
        # rounding error; 1e-4 alone is too strict for small FX ATR values.
        atr=float(s['atr']);discount=float(s['discount_atr'])
        serialization_bound=(1e-8+abs(discount)*5e-9)/atr+2e-8
        assert abs((float(s['vwap'])-float(s['signal_close_price']))/atr-discount)<=serialization_bound
        assert t['side']=='Long' and t['exit_legs']==1 and float(s['lots'])==t['volume']
        assert abs(float(s['stop'])-t['sl'])<1e-7 and abs(float(s['target'])-t['tp'])<1e-7
        assert abs(float(s['fill_price'])-t['open_price'])<1e-7
        assert abs(float(s['requested_risk_usd'])-balance*.01)<=.011
        risk=float(s['initial_risk_usd']);assert risk>0
        t['initial_risk_usd']=risk;t['net_r']=t['net']/risk;t['signal']=s
        net_r.append(t['net_r']);balance+=t['net']
    result['signal_audit_verified']=True
    result['metrics']['total_net_r']=sum(net_r)
    result['metrics']['mean_net_r']=sum(net_r)/len(net_r) if net_r else None
    # Recalculate Sharpe on all UTC calendar days, including no-trade days,
    # with both endpoint balances; one consistent annualisation for all assets.
    trace=n.export_rows(folder/'equity.csv')
    start=n.pd.Timestamp(result['window'][0].replace('.','-'),tz='UTC')
    end=n.pd.Timestamp(result['window'][1].replace('.','-'),tz='UTC')
    if trace:
        ser=n.pd.Series([float(x['equity']) for x in trace],index=n.pd.to_datetime([int(x['epoch']) for x in trace],unit='s',utc=True))
        daily=ser.resample('D').last().reindex(n.pd.date_range(start,end-n.pd.Timedelta(days=1),freq='D')).ffill().fillna(10000)
        daily.iloc[-1]=balance
        changes=daily/n.pd.concat([n.pd.Series([10000],index=[start-n.pd.Timedelta(days=1)]),daily]).shift(1).reindex(daily.index)-1
        result['metrics']['sharpe_calendar_daily_equity']=math.sqrt(365)*changes.mean()/changes.std(ddof=1) if changes.std(ddof=1)>0 else None
    result['metrics']['avg_trades_per_calendar_day']=len(trades)/(end-start).days
    result['tester_end_liquidations']=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in trades)
    result['tiny_initial_risk_positions']=sum(t['initial_risk_usd']<.01 for t in trades)

def main():
    prepare();p=plan();state=dict(total=len(p['cases']),complete={},failed={},no_live_changes=True)
    status=ROOT/'RUN_STATUS.json'
    if status.exists():state=n.read(status)
    for row in p['cases']:
        if row['slug'] in state['complete']:continue
        if len(sys.argv)>1 and sys.argv[1]!='all' and row['symbol'] not in sys.argv[1:]:continue
        try:
            n.START=row['start'];binary,build=n.build(row);result=n.run_case(row,'raw',binary,build)
            folder=ROOT/'native'/result['tag'];signal_file=SIGNALS/(row['slug']+'.csv');owned=n.read(folder/'owned-process.json')
            assert signal_file.is_file() and signal_file.stat().st_mtime>=owned['started']-2
            shutil.copy2(signal_file,folder/'signals.csv');verify(result,folder)
            journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
            result['diagnostics']=sorted(set(re.findall(r'VWAPRAW_STATS[^\r\n]*',journal)))
            assert len(result['diagnostics'])==1,result['diagnostics']
            fatal=['init_failed','runtime','history','stopout','invalid_volume','export_failed']
            assert not any(result['flags'][k] for k in fatal),result['flags']
            n.save(folder/'results.json',result)
            state['complete'][row['slug']]=dict(path=str(folder/'results.json'),trades=len(result['trades']),history_quality=result['native']['history_quality'],seconds=result['seconds'])
            state['failed'].pop(row['slug'],None)
        except Exception as e:
            state['failed'][row['slug']]=dict(error=str(e),trace=traceback.format_exc()[-5000:]);print('FAILED '+row['slug']+' '+str(e),flush=True)
        n.save(status,state);print('PROGRESS '+str(len(state['complete']))+'/'+str(state['total'])+'; failed='+str(len(state['failed'])),flush=True)
    print('FROZEN VWAP RAW BATCH FINISHED; no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        n.available();main()
