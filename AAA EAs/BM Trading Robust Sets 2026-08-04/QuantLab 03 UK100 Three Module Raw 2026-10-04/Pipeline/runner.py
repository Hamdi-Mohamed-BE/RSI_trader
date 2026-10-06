"""Native isolated UK100 pipeline. Exact position-ID aggregation supports partial exits."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,time
import pandas as pd
import baseline
R=Path(__file__).resolve().parent;raw=baseline.raw;h=raw.h;T=raw.T
SOURCE=R/'EA/Calyx UK100 Pipeline Research.mq5';EXPERT=SOURCE.with_suffix('.ex5')
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxUKTPipeline20261004'
BASE=dict(l.split('=',1) for l in (R/'RAW.set').read_text().splitlines() if '=' in l)
BASE.update(InpSignalTimeframe='16385',InpEntryMode='0',InpEntryOffsetATR='0.25',InpArmExpiryHours='6',InpStopMode='0',InpStopPercent='0.5',InpStopPriceUnits='50',InpExitMode='0',InpManagement='0',InpTrailStartR='1',InpTrailATR='1',InpTrailPercent='0.25',InpSessionMode='0',InpDirection='0',InpExcludeDays='0',InpFilter='0',InpADXMin='20',InpMaxSpreadATR='0.08',InpPerModuleDay='1',InpControl='false',InpControlSeed='20261004',InpCaptureEquity='false')
FRAMES={1:'M1',3:'M3',5:'M5',15:'M15',30:'M30',16385:'H1',16388:'H4',16408:'D1'}
PERIODS={'DEV':('2021.10.04','2024.10.01'),'VAL':('2024.10.08','2025.09.28'),'HOLD':('2019.10.04','2021.09.27'),'1Y':('2025.10.04','2026.10.04'),'3M':('2026.07.04','2026.10.04'),'6M':('2026.04.04','2026.10.04'),'3Y':('2023.10.04','2026.10.04'),'5Y':('2021.10.04','2026.10.04'),'SMOKE':('2026.09.01','2026.10.04')}
def save(p,v):raw.save(p,v)
def sha(p):return raw.sha(p)
def norm(changes):
    d={**BASE,**changes}
    return {k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in d.items()}
def key(d):return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()[:12]
def position_outcomes(rows):
    entries={};trades=[];ledger=[];balance=10000.
    for x in rows:
        e=int(x['entry']);pid=int(x['position']);vol=round(float(x['volume']),8);cash=sum(float(x[k]) for k in ['profit','commission','swap','fee']);balance+=cash
        when=datetime.fromtimestamp(int(x['time']),timezone.utc).replace(tzinfo=None).isoformat()
        ledger.append(dict(deal=int(x['deal']),position_id=pid,time=when,cash_flow=round(cash,2),balance=round(balance,2)))
        if e==0:
            assert pid not in entries
            entries[pid]=dict(position_id=pid,module=int(x['module']),module_name=raw.LABELS[int(x['module'])],side='Long' if int(x['type'])==0 else 'Short',volume=vol,remaining=vol,open_time=when,open_price=float(x['price']),net_profit=cash,commission=float(x['commission']),swap=float(x['swap']),fee=float(x['fee']),gross_profit=float(x['profit']),entry_deal=int(x['deal']),partial_exits=0)
        else:
            assert e==1 and pid in entries
            t=entries[pid];assert vol<=t['remaining']+1e-7
            t['remaining']-=vol;t['net_profit']+=cash;t['commission']+=float(x['commission']);t['swap']+=float(x['swap']);t['fee']+=float(x['fee']);t['gross_profit']+=float(x['profit'])
            if t['remaining']>1e-7:t['partial_exits']+=1;continue
            entries.pop(pid);t.update(close_time=when,close_price=float(x['price']),exit_deal=int(x['deal']),exit_comment=x['comment'],boundary_exit='end of test' in x['comment'].lower())
            for k in ['net_profit','commission','swap','fee','gross_profit']:t[k]=round(t[k],2)
            t['result']='Win' if t['net_profit']>0 else 'Loss' if t['net_profit']<0 else 'Flat';t['number']=len(trades)+1
            t['hold_hours']=(pd.Timestamp(t['close_time'])-pd.Timestamp(t['open_time'])).total_seconds()/3600;trades.append(t)
    assert not entries
    assert abs(sum(t['net_profit'] for t in trades)-sum(x['cash_flow'] for x in ledger))<.05
    return trades,ledger
def run(changes,phase='DEV',model=1,symbol='UK100'):
    inputs=norm(changes);cid=key(inputs);tag=f'{symbol}-{phase}-m{model}-{cid}';folder=R/'native'/tag
    if (folder/'result.json').exists():
        result=json.loads((folder/'result.json').read_text());assert result['source_sha256']==sha(SOURCE) and result['binary_sha256']==sha(EXPERT);return result
    folder.mkdir(parents=True,exist_ok=True);start,end=PERIODS[phase];values={**inputs,'InpExportTag':tag}
    frame=FRAMES[int(inputs['InpSignalTimeframe'])]
    manifest=dict(id=cid,tag=tag,phase=phase,start=start,end_exclusive=end,symbol=symbol,timeframe=frame,model=model,delay_ms=150,deposit=10000,inputs=inputs,source_sha256=sha(SOURCE),binary_sha256=sha(EXPERT))
    save(folder/'manifest.json',manifest)
    dest=T/'MQL5/Experts/AAA Research/UKTPipeline20261004';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(EXPERT,dest/'Pipeline.ex5')
    setname=tag+'.set';body='\n'.join(k+'='+v for k,v in values.items())+'\n';(folder/'inputs.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
    header=h.text(raw.B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\UKTPipeline20261004\\Pipeline
ExpertParameters={setname}
Symbol={symbol}
Period={frame}
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\uk-pipeline20261004\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    rp=T/'reports/uk-pipeline20261004'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
    h.free();offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time()
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(folder/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
    try:proc.wait(timeout=1800)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own isolated tester timed out: '+tag)
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,(tag,journal[-3000:])
    bad=re.findall(r'initialization failed|start time changed|not enough history|invalid volume|access violation|array out of range|zero divide|UKT_ENTRY_FAILED|UKT_CLOSE_FAILED|UKT_EXPORT_FAILED|UKT_AUDIT_FAILED|UKT_REQUIRES_HEDGING',journal,re.I)
    assert not bad,(tag,bad[:15],journal[-2000:])
    actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in values.items()),(tag,{k:actual.get(k) for k,v in values.items() if k not in actual or not h._same_setting(v,actual[k])})
    rb=h._read_report(rp);assert start in rb and end in rb and symbol in rb
    for suffix in ['stats','deals']:
        path=COMMON/(tag+'-'+suffix+'.csv');assert path.exists() and path.stat().st_mtime>=began-2;shutil.copy2(path,folder/(suffix+'.csv'))
    stats=list(csv.DictReader((folder/'stats.csv').open(encoding='utf-8-sig')));assert len(stats)==1
    stats={k:float(v) for k,v in stats[0].items()};assert not stats['entry_errors'] and not stats['close_errors']
    rows=list(csv.DictReader((folder/'deals.csv').open(encoding='utf-8-sig')));trades,ledger=position_outcomes(rows)
    from app.mt5_evidence_jobs import _metric,_number
    native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
    assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.05 and abs(stats['profit']-native['net_profit'])<.05
    assert abs(stats['equity_dd_pct']-native['equity_dd_pct'])<.02
    for t in trades:
        assert pd.Timestamp(start.replace('.','-'))<=pd.Timestamp(t['open_time'])<pd.Timestamp(end.replace('.','-'))
        assert pd.Timestamp(t['close_time'])<pd.Timestamp(end.replace('.','-'))
    active=[];maxactive=0
    for t in sorted(trades,key=lambda t:t['entry_deal']):
        active=[x for x in active if x['exit_deal']>t['entry_deal']];assert all(x['module']!=t['module'] for x in active)
        active.append(t);maxactive=max(maxactive,len(active));assert maxactive<=int(inputs['InpMaxPositions'])
    result=dict(**manifest,native=native,export_stats=stats,net_metrics=raw.metrics(trades),trades=trades,ledger=ledger,module_metrics={str(i):raw.metrics([t for t in trades if t['module']==i]) for i in raw.LABELS},max_simultaneous=maxactive,seconds=round(time.time()-began,1),report_sha256=sha(rp),tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*',journal,re.I)))[:8])
    (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(folder/'result.json',result)
    return result
def compile_ea():
    old=(raw.SOURCE,raw.EXPERT);raw.SOURCE=SOURCE;raw.EXPERT=EXPERT
    try:raw.compile_ea()
    finally:raw.SOURCE,raw.EXPERT=old
if __name__=='__main__':
    import sys
    if sys.argv[1]=='compile':compile_ea()
    elif sys.argv[1]=='parity':
        r=run({},'SMOKE',4);old=json.loads((R.parent/'native/SMOKE/results.json').read_text())
        keys=['module','side','volume','open_time','close_time','open_price','close_price','net_profit','commission','swap']
        def clean(t):return [round(t[k],8) if isinstance(t[k],float) else t[k] for k in keys]
        assert [clean(t) for t in r['trades']]==[clean(t) for t in old['trades']]
        assert abs(r['native']['equity_dd_pct']-old['native']['equity_dd_pct'])<.02
        save(R/'PARITY.json',dict(passed=True,positions=len(r['trades']),frozen_baseline=True));print('Baseline-off parity passed: complete trades, execution, costs, equity DD')
