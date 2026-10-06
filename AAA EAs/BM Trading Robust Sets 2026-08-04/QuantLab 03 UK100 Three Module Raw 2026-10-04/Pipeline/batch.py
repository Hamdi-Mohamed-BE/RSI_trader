"""Complete native MT5 case-index optimisation; development screens only."""
from pathlib import Path
import csv,gzip,json,re,shutil,subprocess,time
import runner as n
R=n.R;SOURCE=R/'EA/Calyx UK100 Batch Research.mq5';EXPERT=SOURCE.with_suffix('.ex5')
COLUMNS=["InpEnableDrop","InpEnableMonday","InpEnableTrend","InpATRPeriod","InpDropLookback","InpDropATR","InpRSIPeriod","InpOversoldRSI","InpMondayDipATR","InpPullbackEMA","InpTrendEMA","InpSlowEMA","InpRiskPercent","InpStopATR","InpDropTargetR","InpMondayTargetR","InpTrendTargetR","InpMaxHoldingHours","InpMaxPositions","InpLossesBeforePause","InpPauseHours","InpEntryStartHourLondon","InpEntryEndHourLondon","InpServerUtcOffsetHours","InpBaseMagic","InpDeviationPoints","InpSignalTimeframe","InpEntryMode","InpEntryOffsetATR","InpArmExpiryHours","InpStopMode","InpStopPercent","InpStopPriceUnits","InpExitMode","InpManagement","InpTrailStartR","InpTrailATR","InpTrailPercent","InpSessionMode","InpDirection","InpExcludeDays","InpFilter","InpADXMin","InpMaxSpreadATR","InpPerModuleDay","InpControl","InpControlSeed","InpExportTag","InpCaptureEquity"]
def run(configs,stage,phase='DEV'):
    values=[n.norm(c) for c in configs];identity=n.key(dict(stage=stage,phase=phase,cases=values));folder=R/'batches'/(stage+'-'+identity)
    folder.mkdir(parents=True,exist_ok=True);done=folder/'results.json'
    if done.exists():
        rows=json.loads(done.read_text());assert all(r['source_sha256']==n.sha(SOURCE) for r in rows);return rows
    fname=stage+'-'+identity+'.csv';n.COMMON.mkdir(parents=True,exist_ok=True)
    tags=[f'b-{identity}-{i}-{n.key(v)}' for i,v in enumerate(values)]
    with (folder/'cases.csv').open('w',newline='',encoding='ascii') as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows({**v,'InpExportTag':tag} for v,tag in zip(values,tags))
    shutil.copy2(folder/'cases.csv',n.COMMON/fname)
    start,end=n.PERIODS[phase]
    manifest=dict(stage=stage,phase=phase,start=start,end_exclusive=end,model=1,symbol='UK100',deposit=10000,delay_ms=150,source_sha256=n.sha(SOURCE),binary_sha256=n.sha(EXPERT),cases_sha256=n.sha(folder/'cases.csv'),cases=values,tags=tags)
    n.save(folder/'manifest.json',manifest)
    dest=n.T/'MQL5/Experts/AAA Research/UKTPipeline20261004';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(EXPERT,dest/'Batch.ex5')
    setname='batch-'+identity+'.set';(n.T/'MQL5/Profiles/Tester'/setname).write_text(f'InpConfigIndex=0||0||1||{len(values)-1}||Y\nInpConfigFile={fname}\n',encoding='utf-8')
    header=n.h.text(n.raw.B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\UKTPipeline20261004\\Batch
ExpertParameters={setname}
Symbol=UK100
Period=H1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=150
Optimization=1
OptimizationCriterion=6
FromDate={start}
ToDate={end}
Report=reports\\uk-pipeline20261004\\batch-{identity}.xml
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    n.h.free();offsets={p:p.stat().st_size for p in n.h.logfiles()};began=time.time()
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{n.T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=n.T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    n.save(folder/'owned-process.json',dict(pid=proc.pid,path=str(n.T/'terminal64.exe'),started=began))
    try:proc.wait(timeout=2700)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own batch tester timeout: '+stage)
    journal=''
    for p in n.h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0
    rows=[]
    for inputs,tag in zip(values,tags):
        statsfile=n.COMMON/(tag+'-stats.csv');dealsfile=n.COMMON/(tag+'-deals.csv')
        assert statsfile.exists() and dealsfile.exists() and min(statsfile.stat().st_mtime,dealsfile.stat().st_mtime)>=began-2,(stage,tag,journal[-2500:])
        stats=list(csv.DictReader(statsfile.open()));assert len(stats)==1;stats={k:float(v) for k,v in stats[0].items()}
        trades,ledger=n.position_outcomes(list(csv.DictReader(dealsfile.open())))
        assert abs(sum(t['net_profit'] for t in trades)-stats['profit'])<.05
        assert not stats['entry_errors'] and not stats['close_errors'],(stage,tag,stats)
        case=folder/n.key(inputs);case.mkdir(exist_ok=True);shutil.copy2(statsfile,case/'stats.csv');shutil.copy2(dealsfile,case/'deals.csv')
        rows.append(dict(id=n.key(inputs),stage=stage,phase=phase,model=1,symbol='UK100',start=start,end_exclusive=end,inputs=inputs,source_sha256=n.sha(SOURCE),binary_sha256=n.sha(EXPERT),cases_sha256=manifest['cases_sha256'],export_stats=stats,net_metrics=n.raw.metrics(trades),trades=trades,ledger=ledger,evidence='Native Model1 complete optimisation export; OHLC screen, not final real-tick evidence'))
    for report in (n.T/'reports/uk-pipeline20261004').glob('batch-'+identity+'*'):
        if report.is_file():shutil.copy2(report,folder/report.name)
    n.save(done,rows);return rows
if __name__=='__main__':
    rows=run([{},{}],'parity');old=n.run({},'DEV',1)
    keys=['module','side','volume','open_time','close_time','open_price','close_price','net_profit','commission','swap']
    def clean(t):return [round(t[k],8) if isinstance(t[k],float) else t[k] for k in keys]
    assert [clean(t) for t in rows[0]['trades']]==[clean(t) for t in old['trades']]
    n.save(R/'BATCH PARITY.json',dict(passed=True,positions=len(rows[0]['trades']),equity_dd_pct=rows[0]['export_stats']['equity_dd_pct']));print('Complete optimisation export parity passed')
