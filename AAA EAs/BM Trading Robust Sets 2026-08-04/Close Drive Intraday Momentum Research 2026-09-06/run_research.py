"""Sequential native MT5 research; never attaches an EA to a live chart."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, subprocess, shutil, time
import numpy as np

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / '_Backtests' / 'MT5-DMC-20260811'
SOURCE = ROOT / 'EA' / 'Close Drive Intraday Momentum EA.mq5'
EXPERT = 'Calyx Close Drive'
spec = importlib.util.spec_from_file_location('report_parser', PACKAGE / 'US100 Momentum Continuation Research 2026-08-31' / 'Analyze-Reports.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
WINDOWS = {'development': ('2023.09.01', '2025.09.01', 1), 'locked': ('2025.09.01', '2026.09.01', 0), 'full': ('2023.09.01', '2026.09.01', 0)}
BASE = dict(InpDecisionTimeframe=5, InpIncludeOvernightReturn=True, InpEntryHourNY=15, InpEntryMinuteNY=30,
    InpMinimumOpeningMoveATR=0.0, InpRequireSameDirectionAtEntry=False, InpUseVWAPConfirmation=False,
    InpAllowLong=True, InpAllowShort=True, InpRiskPercent=1.0, InpStopMode=1, InpATRPeriod=14,
    InpATRTimeframe=15, InpStopATR=1.0, InpStopBufferATR=0.10, InpMaximumStopATR=3.0,
    InpExitMode=0, InpRewardRisk=1.0, InpCloseHourNY=15, InpCloseMinuteNY=55,
    InpUseBreakEven=False, InpBreakEvenAtR=0.5, InpBreakEvenLockR=0.0,
    InpUseATRTrailing=False, InpTrailStartAtR=0.75, InpTrailATR=1.0,
    InpUseDynamicM15Stop=False, InpDynamicTriggerR=0.5, InpDynamicLockR=0.2,
    InpAutoServerUtcOffsetLive=False, InpServerUtcOffsetHours=0,
    InpMaximumSpreadATR=0.20, InpMaximumDeviationPoints=80, InpMagic=969060001)

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')

def compile_ea():
    log = SOURCE.with_suffix('.compile.log')
    p = subprocess.run(f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"', timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding='utf-16') if log.exists() else ''
    if '0 errors, 0 warnings' not in text or not SOURCE.with_suffix('.ex5').exists():
        raise RuntimeError('Compilation did not succeed: '+text[-3000:])
    target = TESTER/'MQL5'/'Experts'/EXPERT
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE.with_suffix('.ex5'), target/SOURCE.with_suffix('.ex5').name)
    print('COMPILE: 0 errors, 0 warnings', flush=True)

def score(row):
    if row['trades'] < 60 or row['history_quality_pct'] < 90:
        return -10000 + row['trades']
    return row['return_pct'] - 2*row['equity_dd_pct'] + 5*(row['profit_factor']-1)

def trade_audit(report):
    from bs4 import BeautifulSoup
    from datetime import datetime
    soup=BeautifulSoup(report.read_text(encoding='utf-16'), 'html.parser')
    inside=False;opened=None;trades=[]
    for tr in soup.find_all('tr'):
        if tr.get_text(' ',strip=True)=='Deals': inside=True;continue
        if not inside: continue
        c=[' '.join(td.get_text(' ',strip=True).split()) for td in tr.find_all('td')]
        if len(c)!=13 or c[4] not in ('in','out'): continue
        when=datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S')
        cash=sum(float(c[i].replace(' ','')) for i in (8,9,10))
        balance=float(c[11].replace(' ',''))
        if c[4]=='in':
            if opened is not None: raise ValueError('Unexpected overlapping positions')
            opened=dict(entry_time=when.isoformat(),entry_price=float(c[6].replace(' ','')),side=c[3],volume=float(c[5]),cash=cash,before=balance-cash)
        else:
            if opened is None: raise ValueError('Unmatched exit')
            net=opened.pop('cash')+cash;before=opened.pop('before')
            trades.append(dict(**opened,exit_time=when.isoformat(),exit_price=float(c[6].replace(' ','')),net=net,return_fraction=net/before,
                holding_minutes=(when-datetime.fromisoformat(opened['entry_time'])).total_seconds()/60))
            opened=None
    if opened is not None: raise ValueError('Unclosed report position')
    return trades

def run(symbol, stage, name, config):
    start,end,model = WINDOWS[stage]
    execution=1 if stage=='development' else -1
    case = f'{symbol.lower()}-{stage}-{name}'
    params = dict(config)
    fingerprint = hashlib.sha256((SOURCE.read_text()+json.dumps(params,sort_keys=True)+start+end+str(model)+symbol).encode()).hexdigest()
    out = ROOT/'Reports'/stage
    out.mkdir(parents=True,exist_ok=True)
    result_path = out/(case+'.json')
    if result_path.exists():
        old=json.loads(result_path.read_text())
        if old.get('fingerprint')==fingerprint and 'trade_audit' in old:
            return old
    set_name=case+'.set'
    set_text='\n'.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}' for k,v in params.items())+'\n'
    (ROOT/'Sets').mkdir(exist_ok=True)
    (ROOT/'Sets'/set_name).write_text(set_text,encoding='utf-8')
    (TESTER/'MQL5'/'Profiles'/'Tester'/set_name).write_text(set_text,encoding='utf-8')
    job=TESTER/'backtest-configs'/'calyx-close-drive'
    job.mkdir(parents=True,exist_ok=True)
    report_dir=TESTER/'reports'/'calyx-close-drive'
    report_dir.mkdir(parents=True,exist_ok=True)
    # A tester terminal can otherwise restore unrelated charts on startup.
    (TESTER/'MQL5'/'Profiles'/'Charts'/'Calyx Research Empty').mkdir(parents=True,exist_ok=True)
    report=report_dir/(case+'.htm')
    # Unique case files are retained; a timestamp prevents stale report reuse.
    if report.exists():
        report.rename(report.with_name(case+f'.old-{time.time_ns()}.htm'))
    ini=f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={EXPERT}\\Close Drive Intraday Momentum EA
ExpertParameters={set_name}
Symbol={symbol}
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={execution}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\calyx-close-drive\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
'''
    config_path=job/(case+'.ini')
    config_path.write_text(ini,encoding='utf-8-sig')
    print(f'START {case} {start}..{end} model={model}',flush=True)
    begin=time.monotonic()
    subprocess.run(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{config_path}"', timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not report.exists():
        raise RuntimeError(f'MT5 produced no report for {case}; inspect isolated terminal logs.')
    for file in report_dir.glob(case+'*'):
        if '.old-' not in file.name:
            shutil.copy2(file,out/file.name)
    row=parser.parse_report(out/report.name)
    audit=trade_audit(out/report.name)
    if len(audit)!=row['trades'] or abs(sum(t['net'] for t in audit)-row['net_profit'])>0.05:
        raise ValueError('Trade ledger does not reconcile to MT5 summary')
    row['trade_audit']=dict(max_holding_minutes=max((t['holding_minutes'] for t in audit),default=0),overnight_trades=sum(t['holding_minutes']>180 for t in audit))
    if row['trade_audit']['overnight_trades']:
        raise ValueError('Unexpected overnight holdings; inspect report before accepting results')
    dump(out/(case+'-trades.json'),audit)
    row.update(symbol=symbol,stage=stage,name=name,config=params,fingerprint=fingerprint,model=model,execution_mode=execution,elapsed_seconds=round(time.monotonic()-begin,2))
    row['score']=score(row)
    if row['bars']<=0 or row['initial_balance']!=10000:
        raise RuntimeError('Invalid native report '+case)
    dump(result_path,row)
    print(f"DONE {case}: return {row['return_pct']:+.2f}% PF {row['profit_factor']:.2f} win {row['win_rate']:.2f}% DD {row['equity_dd_pct']:.2f}% n={row['trades']} ({row['elapsed_seconds']}s)",flush=True)
    return row

def choose(rows):
    return max(rows,key=score)

def research(smoke=False):
    compile_ea()
    selections={}
    for symbol in ('USTEC','US30'):
        rows=[run(symbol,'development','baseline',BASE)]
        if smoke: continue
        for overnight in (True,False):
            for minute in (870,900,930):
                c=dict(BASE,InpIncludeOvernightReturn=overnight,InpEntryHourNY=minute//60,InpEntryMinuteNY=minute%60,
                    InpMinimumOpeningMoveATR=0.5,InpRequireSameDirectionAtEntry=True)
                rows.append(run(symbol,'development',f'signal-{int(overnight)}-{minute}',c))
        selected=choose(rows)
        for label,change in [('vwap',dict(InpUseVWAPConfirmation=True)),('long',dict(InpAllowShort=False)),('short',dict(InpAllowLong=False)),('threshold1',dict(InpMinimumOpeningMoveATR=1.0))]:
            rows.append(run(symbol,'development','filter-'+label,dict(selected['config'],**change)))
        signal=choose(rows)
        stop_rows=[signal]
        for stop in (0,1,2):
            for rr in (0.5,1.0,2.0,4.0):
                c=dict(signal['config'],InpStopMode=stop,InpExitMode=1,InpRewardRisk=rr)
                stop_rows.append(run(symbol,'development',f'stop{stop}-rr{rr:g}',c))
        for mult in (0.5,1.5,2.0):
            stop_rows.append(run(symbol,'development',f'timed-atr{mult:g}',dict(signal['config'],InpStopMode=1,InpStopATR=mult,InpExitMode=0)))
        stop=choose(stop_rows)
        manage=[stop]
        for label,change in [('be',dict(InpUseBreakEven=True)),('trail',dict(InpUseATRTrailing=True)),('dynamic5020',dict(InpUseDynamicM15Stop=True)),('m15',dict(InpDecisionTimeframe=15)),('m30',dict(InpDecisionTimeframe=30))]:
            manage.append(run(symbol,'development','manage-'+label,dict(stop['config'],**change)))
        winner=choose(manage)
        selections[symbol]={'signal':signal['name'],'stop':stop['name'],'selected':winner['name'],'config':winner['config'],
            'development_score':winner['score'],'development_report':winner['report']}
        dump(ROOT/'selection.json',selections)
    if smoke: return
    # Only after freezing BOTH markets do we open the held-out year.
    for symbol,choice in selections.items():
        run(symbol,'locked','baseline',BASE)
        run(symbol,'locked','selected',choice['config'])
        run(symbol,'full','selected',choice['config'])
    build_report()

def build_report():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    rows=[json.loads(p.read_text()) for p in (ROOT/'Reports').glob('*/*.json') if not p.name.endswith('-trades.json')]
    selected=json.loads((ROOT/'selection.json').read_text())
    charts=ROOT/'Charts';charts.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(12,8),constrained_layout=True)
    final=[];mc=[];stress=[]
    for ax,symbol in zip(axes,('USTEC','US30')):
        for name,color in [('baseline','#808080'),('selected','#119966')]:
            r=next(x for x in rows if x['symbol']==symbol and x['stage']=='locked' and x['name']==name)
            final.append(r)
            series=r['series'];dates=[datetime.fromisoformat(x['date']) for x in series]
            ax.step(dates,[x['balance'] for x in series],where='post',label=f"{name}: PF {r['profit_factor']:.2f}, win {r['win_rate']:.1f}%, n={r['trades']}",color=color)
            if name=='selected':
                audit=trade_audit(Path(r['report']));returns=np.array([t['return_fraction'] for t in audit])
                stressed=returns-0.0005
                stress_bal=np.r_[10000,10000*np.cumprod(1+stressed)]
                cash=np.diff(stress_bal)
                losses=-cash[cash<0].sum()
                stress.append(dict(symbol=symbol,additional_cost='0.05R per trade at 1% planned risk',return_pct=float((stress_bal[-1]/10000-1)*100),
                    profit_factor=float(cash[cash>0].sum()/losses) if losses else None,
                    balance_dd_pct=float(np.max(1-stress_bal/np.maximum.accumulate(stress_bal))*100)))
                rng=np.random.default_rng(20260906);paths=np.full((5000,len(returns)+1),10000.0)
                if len(returns):
                    # Five-trade blocks preserve some local streak structure.
                    block=5;starts=rng.integers(0,len(returns),size=(5000,(len(returns)+block-1)//block))
                    ix=(starts[:,:,None]+np.arange(block))%len(returns)
                    sampled=returns[ix.reshape(5000,-1)[:,:len(returns)]]
                    paths[:,1:]=10000*np.cumprod(1+sampled,axis=1)
                dd=np.max(1-paths/np.maximum.accumulate(paths,axis=1),axis=1)*100
                ends=(paths[:,-1]/10000-1)*100
                mc.append(dict(symbol=symbol,paths=5000,return_p5=float(np.percentile(ends,5)),return_median=float(np.median(ends)),return_p95=float(np.percentile(ends,95)),dd_p95=float(np.percentile(dd,95)),profitable_pct=float(np.mean(ends>0)*100)))
                mfig,ma=plt.subplots(figsize=(10,4),constrained_layout=True)
                lo,med,hi=np.percentile(paths,[5,50,95],axis=0)
                ma.fill_between(np.arange(len(lo)),lo,hi,alpha=.25,color='#229988');ma.plot(med,color='#119966')
                ma.set(title=f'{symbol}: 5,000 block-bootstrap paths (held-out net trades)',xlabel='Closed trade',ylabel='USD balance')
                mfig.savefig(charts/f'{symbol}-monte-carlo.png',dpi=140);plt.close(mfig)
        ax.set_title(f'{symbol} — held-out 2025-09-01 to 2026-09-01');ax.set_ylabel('Closed balance USD');ax.legend();ax.grid(alpha=.2);ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        final.append(next(x for x in rows if x['symbol']==symbol and x['stage']=='full'))
    fig.savefig(charts/'held-out-comparison.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,8),constrained_layout=True)
    for ax,symbol in zip(axes,('USTEC','US30')):
        r=next(x for x in final if x['symbol']==symbol and x['stage']=='full')
        ax.step([datetime.fromisoformat(p['date']) for p in r['series']],[p['balance'] for p in r['series']],where='post',color='#159966')
        ax.axvline(datetime(2025,9,1),color='#b87922',ls='--',label='Development ends')
        ax.axhline(10000,color='gray',lw=.7)
        ax.set(title=f"{symbol}: 3-year selected config — {r['return_pct']:+.2f}%, PF {r['profit_factor']:.2f}, win {r['win_rate']:.1f}%",ylabel='Closed balance USD')
        ax.legend();ax.grid(alpha=.2);ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    fig.savefig(charts/'three-year-context.png',dpi=150);plt.close(fig)
    for symbol in ('USTEC','US30'):
        development=[r for r in rows if r['symbol']==symbol and r['stage']=='development']
        fig,ax=plt.subplots(figsize=(12,max(6,len(development)*.25)),constrained_layout=True)
        ax.barh([r['name'] for r in development],[r['return_pct'] for r in development],color=['#159966' if r['return_pct']>0 else '#dd6666' for r in development]);ax.axvline(0,color='black',lw=.6);ax.set(title=f'{symbol}: all development configurations',xlabel='Development net return %');ax.invert_yaxis()
        fig.savefig(charts/f'{symbol}-all-configurations.png',dpi=140);plt.close(fig)
    fields=['symbol','stage','name','return_pct','profit_factor','win_rate','equity_dd_pct','trades','sharpe_ratio','recovery_factor','history_quality_pct']
    import csv
    with (ROOT/'all-results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    dump(ROOT/'summary.json',dict(results=[{k:r[k] for k in fields} for r in final],monte_carlo=mc,cost_stress=stress,selection=selected))
    lines=['# Step 1 — Close-Drive Intraday Momentum','', 'Decision: keep both tested candidates out of the active system. Both selected configurations lost money in the held-out year, with PF below 1. Their small positive three-year returns include the optimization sample and do not establish a reliable edge.','',
        'Completed: 68 native MT5 runs (31 development configurations per market plus baseline/selected held-out tests and selected three-year context). Research only. Default risk: 1% of equity per trade. No production installer or website selection changed.','',
        'Development: 2023-09-01 to 2025-09-01 (M1 OHLC, 1ms execution). Selection frozen before held-out testing: 2025-09-01 to 2026-09-01 (MT5 generated Every Tick, random delay / ExecutionMode=-1). Full three-year runs include the optimization sample and are descriptive. This is not a real-tick test.','',
        'Signal variants: previous cash close to 10:00 New York (paper definition) and 09:30–10:00 only; entries 14:30/15:00/15:30 NY. Exit 15:55 to precede broker break. New York DST handled. Broker clock assumed UTC, following this Exness research environment. July 2–5, December 23–26 and Friday after Thanksgiving excluded conservatively; this is not a full exchange holiday calendar.','',
        'Stops: prior completed candle, M15 ATR, opening-range boundary; all stop distances capped at 3 ATR and broker minimum enforced. Targets: timed close or 0.5/1/2/4R. ATR distances 0.5/1/1.5/2; management none/BE/ATR trail/M15 50–20. Five- and fifteen-/thirty-minute decision bars compared. Sequential search is not an exhaustive joint optimization.','',
        '| Asset | Period | Config | Return | PF | Win rate | Equity DD | Trades | MT5 Sharpe | Recovery |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in final:
        lines.append(f"| {r['symbol']} | {r['stage']} | {r['name']} | {r['return_pct']:+.2f}% | {r['profit_factor']:.2f} | {r['win_rate']:.2f}% | {r['equity_dd_pct']:.2f}% | {r['trades']} | {r['sharpe_ratio']:.2f} | {r['recovery_factor']:.2f} |")
    lines+=['','## Selected settings','', '| Asset | Opening signal | NY entry | Direction | Stop | TP | Management |','|---|---|---|---|---|---|---|']
    for symbol,choice in selected.items():
        c=choice['config'];signal='Previous cash close to 10:00' if c['InpIncludeOvernightReturn'] else '09:30 to 10:00'
        direction='Both' if c['InpAllowLong'] and c['InpAllowShort'] else ('Long only' if c['InpAllowLong'] else 'Short only')
        stop=['Prior decision candle','M15 ATR','Opening-range boundary'][c['InpStopMode']]
        if c['InpStopMode']==1: stop+=f" x {c['InpStopATR']}"
        tp=f"{c['InpRewardRisk']}R" if c['InpExitMode']==1 else 'Timed exit'
        manage=', '.join(k for k,v in [('BE',c['InpUseBreakEven']),('ATR trail',c['InpUseATRTrailing']),('Dynamic 50-20',c['InpUseDynamicM15Stop'])] if v) or 'None'
        lines.append(f"| {symbol} | {signal} | {c['InpEntryHourNY']:02}:{c['InpEntryMinuteNY']:02} | {direction} | {stop} | {tp} | {manage} |")
    lines+=['', 'Exact remaining thresholds and settings are in selection.json and Sets/*-locked-selected.set. All positions have a timed close at 15:55 NY or five minutes before the current broker session ends. The 3-ATR structural-stop cap is a deliberate research adaptation.','',
        'For a 0.5R target, BE at 0.5R, Dynamic 50–20 and trailing activation at 0.75R can be non-binding: the target is reached before management can help. Identical results in those comparisons do not show that trailing never matters on other targets.','',
        'DD above is the native percentage at MT5’s maximal cash equity drawdown event. The plotted lines are realized balance, not reconstructed floating equity.','',
        '## Additional execution-cost stress','', '| Asset | Extra cost | Stressed return | Stressed PF | Closed-balance DD |','|---|---|---:|---:|---:|']
    for s in stress:
        pf=f"{s['profit_factor']:.2f}" if s['profit_factor'] is not None else 'N/A'
        lines.append(f"| {s['symbol']} | 0.05R/trade | {s['return_pct']:+.2f}% | {pf} | {s['balance_dd_pct']:.2f}% |")
    lines+=['','The stress is hypothetical extra friction deducted from held-out trade returns and compounded; it is not a second MT5 execution test.','', '## Monte Carlo','', '| Asset | Return P5 | Median return | Return P95 | DD P95 | Profitable samples |','|---|---:|---:|---:|---:|---:|']
    for m in mc: lines.append(f"| {m['symbol']} | {m['return_p5']:+.2f}% | {m['return_median']:+.2f}% | {m['return_p95']:+.2f}% | {m['dd_p95']:.2f}% | {m['profitable_pct']:.1f}% |")
    lines+=['','Monte Carlo resamples five-trade blocks of held-out net returns with compounding. It does not model unrealized drawdown, changing spreads or future regimes, and its profitable fraction is not a forecast probability. Native MT5 equity DD is reported separately.','',
        'Research basis: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866 . Published ETF evidence motivates this CFD test; it does not establish an edge in these broker instruments.','',
        'See Charts/held-out-comparison.png and the per-asset development and Monte Carlo charts. All native reports and exact inputs are retained.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(json.loads((ROOT/'summary.json').read_text())['results'],indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');ap.add_argument('--report',action='store_true');a=ap.parse_args()
    if a.report: build_report()
    else: research(a.smoke)
