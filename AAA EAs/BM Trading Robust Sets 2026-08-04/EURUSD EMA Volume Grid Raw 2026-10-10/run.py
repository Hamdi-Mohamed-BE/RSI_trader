"""Native tester-only EURUSD grid reconstruction, not a risk-percent EA."""
from pathlib import Path
import gzip, importlib.util, json, math, msvcrt, os, re, shutil, subprocess, time, traceback

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('grid_native',PRIOR/'run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.R=ROOT;n.END='2026.10.10'
CUSTOM=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxEURGridRaw20261010'

def plan():
    source=ROOT/'EURUSD EMA Volume Grid Raw.mq5'
    common=dict(InpSignalTF='5',InpEMAPeriod='5',InpStartingLot='0.01',InpLotIncrement='0.01',
        InpGridPoints='300',InpBasketTargetUSD='10.0',InpAlternateAfterBasket='true',InpMagicBase='261010000')
    cases=[]
    for window,start in [('1y','2025.10.10'),('3y','2023.10.10')]:
        slug='eurusd-ema-volume-grid-'+window
        cases.append(dict(slug=slug,label='EURUSD EMA5 + rising volume grid',symbol='EURUSD',period='M5',window=window,start=start,
            source=str(source),expert=str(source.with_suffix('.ex5')),input_settings={**common,'InpGridAuditTag':slug},
            candidate_overrides={},production_hashes={str(source):n.sha(source)}))
    value=dict(cases=cases,end_exclusive=n.END,deposit_usd=10000,leverage='1:2000',model=4,delay_ms=150,
        scope='User-approved mechanical reconstruction, research only',no_live_changes=True,optimization=False,
        risk_percent=None,sl=False,max_orders=None,protocol_sha256=n.sha(ROOT/'PROTOCOL.txt'))
    p=ROOT/'PLAN.json'
    if p.exists():assert n.read(p)==value,'Frozen plan changed'
    else:n.save(p,value)
    return value

def run_case(row,binary,build):
    tag='allrr05-'+row['slug']+'-raw';out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
    inputs={**row['input_settings'],'InpRR05AuditTag':tag}
    manifest=dict(tag=tag,inputs=inputs,start=row['start'],end_exclusive=n.END,deposit=10000,leverage='1:2000',
        model=4,delay_ms=150,symbol=row['symbol'],period=row['period'],build=build)
    if (out/'manifest.json').exists():assert n.read(out/'manifest.json')==manifest,'Case changed'
    else:n.save(out/'manifest.json',manifest)
    if (out/'results.json').exists():return n.read(out/'results.json')
    n.available();destination=n.T/'MQL5/Experts/AAA Research/EURGrid20261010';destination.mkdir(parents=True,exist_ok=True)
    shutil.copy2(binary,destination/(row['slug']+'.ex5'))
    preset=tag+'.set';body='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
    (out/'inputs.set').write_text(body,encoding='utf-8');(n.T/'MQL5/Profiles/Tester'/preset).write_text(body,encoding='utf-8')
    header=n.h.text(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    report=n.T/'reports/eur-grid-20261010'/(tag+'.htm');report.parent.mkdir(exist_ok=True)
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port={n.PORT}
Expert=AAA Research\\EURGrid20261010\\{row['slug']}
ExpertParameters={preset}
Symbol={row['symbol']}
Period={row['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={row['start']}
ToDate={n.END}
Report=reports\\eur-grid-20261010\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=n.T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in n.h.logfiles()};began=time.time()
    print('START '+row['window']+' native EURUSD grid',flush=True)
    proc=subprocess.Popen(f'"{n.T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=n.T,creationflags=subprocess.CREATE_NO_WINDOW)
    n.save(out/'owned-process.json',dict(pid=proc.pid,executable=str(n.T/'terminal64.exe'),started=began))
    try:proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned tester timed out; other processes untouched')
    journal=''
    for p in n.h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as stream:stream.seek(offsets.get(p,0));journal+=stream.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and report.is_file() and report.stat().st_mtime>=began-2,('No fresh report',journal[-1000:])
    flags={key:len(re.findall(pattern,journal,re.I)) for key,pattern in {
        'init_failed':'initialization failed','runtime':'access violation|array out of range|zero divide',
        'history':'testing start time changed|not enough history','stopout':'stop out|margin call',
        'invalid_volume':'invalid volume','export_failed':'RR05_EXPORT_FAILED'}.items()}
    # Insolvency/stopout is a genuine grid outcome, never discarded as a bad test.
    assert not any(flags[k] for k in ['init_failed','runtime','history','export_failed']),flags
    assert 'RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal
    actual=n.h._report_inputs(report)
    assert not [k for k,v in inputs.items() if k not in actual or not n.h._same_setting(v,actual[k])],actual
    native=n.h._native_metrics(report);text=n.h._read_report(report)
    assert row['start'] in text and n.END in text and 'EURUSD' in text
    native.update(equity_dd_pct=n._number(n._metric(text,'Equity Drawdown Relative')),
        balance_dd_pct=n._number(n._metric(text,'Balance Drawdown Relative')),
        equity_dd_usd=n._number(n._metric(text,'Equity Drawdown Maximal')))
    shutil.copy2(report,out/'report.htm')
    for suffix in ['deals','equity']:
        file=n.COMMON/(tag+'-'+suffix+'.csv');assert file.is_file() and file.stat().st_mtime>=began-2
        shutil.copy2(file,out/(suffix+'.csv'))
    for suffix in ['signals','trace','stats']:
        file=CUSTOM/(row['slug']+'-'+suffix+'.csv');assert file.is_file() and file.stat().st_mtime>=began-2
        shutil.copy2(file,out/(suffix+'.csv'))
    deals=n.export_rows(out/'deals.csv');trades,ledger=n.trades_from_deals(deals)
    assert abs(sum(t['net'] for t in trades)-native['net_profit'])<.031,('Native cash mismatch',native)
    result=dict(tag=tag,window=[row['start'],n.END],inputs=actual,native=native,flags=flags,trades=trades,ledger=ledger,
        seconds=time.time()-began,binary_sha256=n.sha(binary),report_sha256=n.sha(report),no_live_changes=True,
        diagnostics=sorted(set(re.findall(r'GRID_CONFIG[^\r\n]*|GRID_STATS[^\r\n]*',journal))),
        tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:20])
    verify(result,out,deals)
    n.save(out/'results.json',result)
    print('DONE '+row['window']+' '+json.dumps(result['summary']),flush=True)
    return result

def basket_groups(trades,deals):
    reasons={int(d['position_id']):int(d['reason']) for d in deals if int(d['entry'])==1}
    groups={}
    for t in trades:groups.setdefault(t['magic'],[]).append(t)
    result=[]
    for magic,ts in sorted(groups.items()):
        sides={t['side'] for t in ts};assert len(sides)==1
        terminal=any(any('end of test' in c.lower() for c in t['exit_comments']) for t in ts)
        so=any(reasons[t['position_id']]==6 for t in ts)
        opened=min(t['open_epoch'] for t in ts);closed=max(t['close_epoch'] for t in ts)
        result.append(dict(id=magic-261010000,magic=magic,side=next(iter(sides)),orders=len(ts),net=round(sum(t['net'] for t in ts),2),
            open_epoch=opened,close_epoch=closed,duration_days=(closed-opened)/86400,
            reason='STOPOUT' if so else ('TEST_END' if terminal else 'TARGET'),
            total_lots=sum(t['volume'] for t in ts),terminal=terminal,stopout=so))
    return result

def stats(values):
    wins=[v for v in values if v>0];losses=[v for v in values if v<0]
    w=l=mw=ml=0
    for v in values:w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(mw,w);ml=max(ml,l)
    return dict(count=len(values),wins=len(wins),losses=len(losses),win_rate=100*len(wins)/len(values) if values else None,
        pf=sum(wins)/-sum(losses) if losses else None,win_streak=mw,loss_streak=ml,
        avg_win=sum(wins)/len(wins) if wins else None,avg_loss=sum(losses)/len(losses) if losses else None)

def verify(result,out,deals):
    signals=n.export_rows(out/'signals.csv');trades=result['trades']
    bydeal={int(d['deal']):d for d in deals}
    assert len(signals)==len(trades)
    groups={}
    for s in signals:
        bid=int(s['basket']);idx=int(s['order_index']);epoch=int(s['epoch']);dir=int(s['side'])
        assert int(s['signal_start'])+300==int(s['signal_close'])<=epoch
        assert int(s['v_old'])<int(s['v_mid'])<int(s['v_new'])
        assert (float(s['close'])>float(s['ema'])) if dir>0 else (float(s['close'])<float(s['ema']))
        assert abs(float(s['lots'])-.01*idx)<1e-7
        if idx>1:assert float(s['nearest_points'])>=300-1e-4
        d=bydeal[int(s['deal'])];assert int(d['magic'])==int(s['magic'])==261010000+bid
        assert int(d['entry'])==0 and int(d['type'])==(0 if dir>0 else 1)
        assert abs(float(d['volume'])-float(s['lots']))<1e-7
        assert abs(float(d['price'])-float(s['fill_price']))<1e-7
        groups.setdefault(bid,[]).append(s)
    for ss in groups.values():assert [int(s['order_index']) for s in ss]==list(range(1,len(ss)+1))
    baskets=basket_groups(trades,deals)
    assert all(b['id']==i+1 for i,b in enumerate(baskets))
    for a,b in zip(baskets,baskets[1:]):
        assert a['side']!=b['side'] and a['close_epoch']<=b['open_epoch']
    assert all(t['sl']==0 and t['tp']==0 for t in trades)
    net=round(sum(b['net'] for b in baskets),2);assert abs(net-result['native']['net_profit'])<.031
    trace=n.export_rows(out/'trace.csv');v={s['metric']:float(s['value']) for s in n.export_rows(out/'stats.csv')}
    assert v['digits']==5 and abs(v['point']-.00001)<1e-10 and v['grid_points']==300
    # AccountInfo observed before/after delayed trade calls and MT5's report
    # update cadence need not produce identical maxima. Preserve BOTH measured
    # values; headline uses the more conservative drawdown, not a fabricated match.
    assert 0<=v['max_equity_dd_pct']<=100 and 0<=result['native']['equity_dd_pct']<=100
    start=n.pd.Timestamp(result['window'][0].replace('.','-'),tz='UTC');end=n.pd.Timestamp(result['window'][1].replace('.','-'),tz='UTC')
    series=n.pd.Series([float(x['equity']) for x in trace],index=n.pd.to_datetime([int(x['epoch']) for x in trace],unit='s',utc=True))
    daily=series.resample('D').last().reindex(n.pd.date_range(start,end-n.pd.Timedelta(days=1),freq='D')).ffill().fillna(10000)
    daily.iloc[-1]=10000+net
    previous=n.pd.concat([n.pd.Series([10000],index=[start-n.pd.Timedelta(days=1)]),daily]).shift(1).reindex(daily.index)
    changes=daily/previous-1
    sharpe=math.sqrt(365)*changes.mean()/changes.std(ddof=1) if changes.std(ddof=1)>0 else None
    natural=[b for b in baskets if b['reason']=='TARGET'];terminal=[b for b in baskets if b['terminal']]
    result['baskets']=baskets;result['instrumentation']=v;result['signal_audit_verified']=True
    result['summary']=dict(net_profit=net,return_pct=net/100,final_balance=10000+net,orders=len(trades),
        baskets=stats([b['net'] for b in baskets]),positions=stats([t['net'] for t in trades]),natural_baskets=stats([b['net'] for b in natural]),
        natural_net=round(sum(b['net'] for b in natural),2),test_end_baskets=len(terminal),test_end_net=round(sum(b['net'] for b in terminal),2),
        terminal_orders=sum(b['orders'] for b in terminal),terminal_duration_days=max([b['duration_days'] for b in terminal],default=0),
        stopout_baskets=sum(b['stopout'] for b in baskets),equity_dd_pct=max(v['max_equity_dd_pct'],result['native']['equity_dd_pct']),
        equity_dd_usd=max(v['max_equity_dd_usd'],result['native']['equity_dd_usd']),max_daily_equity_dd_usd=v['max_daily_equity_dd_usd'],
        balance_dd_pct=result['native']['balance_dd_pct'],sharpe_calendar_daily_equity=sharpe,
        max_positions=int(v['max_positions']),max_lots=v['max_lots'],max_margin_usd=v['max_margin_usd'],worst_floating_pnl=v['worst_floating_pnl_usd'],
        max_basket_days=max([b['duration_days'] for b in baskets],default=0),
        commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),fee=sum(t['fee'] for t in trades))

def main():
    shutil.copy2(PRIOR/'ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh');p=plan();results={}
    for row in p['cases']:
        binary,build=n.build(row);results[row['window']]=run_case(row,binary,build)
        n.save(ROOT/'SUMMARY.json',dict(plan=p,results=results,completed=len(results),no_live_changes=True))
    n.save(ROOT/'VERIFICATION.json',dict(completed=len(results),zero_compile_errors_warnings=True,signals_causal_and_lots_verified=True,
        distance_and_alternation_verified=True,native_cash_reconciled=True,terminal_losses_included=True,
        native_and_tick_observed_equity_dd_separately_preserved=True,no_live_changes=True,source_sha256=n.sha(ROOT/'EURUSD EMA Volume Grid Raw.mq5')))
    print('EURUSD GRID RAW FINISHED — no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);n.available();main()
