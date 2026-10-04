"""Frozen old/new XAU comparison; isolated MT5 only, no active-terminal API.
Generated snapshot/includes/INI/SET/JSON are mechanical build artifacts.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import gzip,hashlib,json,os,re,shutil,subprocess,sys,time
R=Path(__file__).resolve().parent;B=R.parent;REPO=B.parent.parent
T=B/'_Backtests/MT5-DMC-20260811'
SOURCE=B/'AAA Final EAs/AAA Final News Pulse XAU Event Specific EA/AAA Final News Pulse XAU Event Specific EA.mq5'
SET=B/'Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'
DEST=T/'MQL5/Experts/AAA Research/NewsFix20261003'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(B.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_report_inputs,_same_setting
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    data=p.read_bytes();return data.decode('utf-16') if data[:2] in (b'\xff\xfe',b'\xfe\xff') else data.decode('utf-8-sig',errors='replace')
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(s):print(s,flush=True);save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s))
def free():
    out=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert out.returncode==0 and str(T).lower() not in out.stdout.lower(),'Isolated tester busy; not stopping any terminal'
    assert (T/'MQL5/Profiles/Charts/Calyx Research Empty').is_dir()
    assert not list((T/'MQL5/Profiles/Charts/Calyx Research Empty').glob('*.chr'))
def logs():return list((T/'logs').glob('*.log'))+list((T/'Tester/logs').glob('*.log'))+list((T/'Tester').glob('Agent-*/logs/*.log'))
def old_text(path):return subprocess.check_output(['git','show','HEAD:'+path.relative_to(REPO).as_posix()],cwd=REPO).decode('utf-8-sig')
def prepare():
    free();folder=R/'snapshot';folder.mkdir(exist_ok=True)
    # Save exact pre-change source/settings and binary before compiling v2.20.
    for name,p in [('Current.mq5',SOURCE),('Current.set',SET)]:
        dest=folder/name
        if not dest.exists():dest.write_text(old_text(p),encoding='utf-8')
    if not (folder/'Current-original.ex5').exists():shutil.copy2(SOURCE.with_suffix('.ex5'),folder/'Current-original.ex5')
    archived=json.loads((B/'News Pulse Event Parameters Research 2026-09-19/Deployment/OFFICIAL CALENDAR.json').read_text())
    recent=json.loads((R/'recent-calendar-receipt.json').read_text())
    rows={ (x['kind'],x['epoch']):x for x in archived['events'] }
    for row in recent['events']:
        assert row['release_date_confirmed']
        assert row['kind'] in ('NFP','CPI','FOMC')
        if row['epoch']<1788566400:assert (row['kind'],row['epoch']) in rows,'calendar overlap disagreement'
        rows[(row['kind'],row['epoch'])]=row
    lo=int(datetime(2025,10,3,tzinfo=timezone.utc).timestamp());hi=int(datetime(2026,10,3,tzinfo=timezone.utc).timestamp())
    events=sorted([x for x in rows.values() if lo<=x['epoch']<hi],key=lambda x:x['epoch'])
    assert events and events[-1]['epoch']==1790944200
    save(R/'calendar.json',dict(from_date='2025-10-03',to_exclusive='2026-10-03',events=events,counts=dict(Counter(x['kind'] for x in events)),
        provenance='Cached official BLS/Federal Reserve calendar through 2026-09-05 plus current confirmed FXMacroData timestamps; overlap verified',
        value_inputs_used=False,macro_value_vintage_verified=False))
    epoch=','.join(str(x['epoch']) for x in events);kind=','.join('"'+x['kind']+'"' for x in events)
    cal=f'''#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20251003
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261003
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS {len(events)}
long NP_GENERATED_EVENT_UTC_EPOCHS[]={{{epoch}}};
string NP_GENERATED_EVENT_KINDS[]={{{kind}}};
string NP_GeneratedCalendarProvider(){{return "Cached official BLS/Fed plus FXMacroData";}}
string NP_GeneratedCalendarHash(){{return "{sha(R/'calendar.json')}";}}
int NP_GeneratedCalendarEventCount(){{return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}}
'''
    (folder/'NewsPulseTesterCalendar.mqh').write_text(cal)
    helpers=B/'AAA Final EAs/AAA Final News Pulse EA'
    for name in ['AAA_Final_Common.mqh','SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:
        shutil.copy2(helpers/name,folder/name)
    shutil.copy2(B/'_Shared/CalyxAdaptivePortfolio.mqh',folder/'CalyxAdaptivePortfolio.mqh')
    shutil.copy2(SOURCE.parent/'NewsPulsePlacement.mqh',folder/'NewsPulsePlacement.mqh')
    for name,body in [('Current',read(folder/'Current.mq5')),('New-fixed',read(SOURCE))]:
        body=body.replace('\r\n','\n')
        body=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',body)
        body=body.replace('int OnInit()\n{','int OnInit()\n{\n   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;')
        assert 'if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;' in body
        (folder/(name+'-test.mq5')).write_text(body)
    shutil.copy2(R/'GeometryTests.mq5',folder/'GeometryTests.mq5')
    return events
def compile_one(name):
    source=R/'snapshot'/(name+'.mq5');log=R/(name+'.compile.log');began=time.time()
    if name!='GeometryTests' and (R/'BUILD.json').exists() and source.with_suffix('.ex5').exists():
        previous=json.loads((R/'BUILD.json').read_text()).get(name,{})
        if previous.get('source')==sha(source) and previous.get('binary')==sha(source.with_suffix('.ex5')):
            DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),DEST/(name+'.ex5'))
            status('REUSED frozen build '+name);return
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    assert '0 errors, 0 warnings' in read(log),read(log)[-5500:]
    assert source.with_suffix('.ex5').stat().st_mtime>=began-2
    DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),DEST/(name+'.ex5'))
    status('COMPILED '+name)
def run(name,delay=150,start='2025.10.03',end='2026.10.03'):
    tag=f'{name}-{delay}-{start}';out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
    if (out/'result.json').exists():
        result=json.loads((out/'result.json').read_text())
        if name!='GeometryTests':
            assert result['source_sha']==sha(R/'snapshot'/(name+'.mq5')),'Cached case has different source'
            assert result['binary_sha']==sha(DEST/(name+'.ex5')),'Cached case has different binary'
        return result
    settings={l.split('=',1)[0]:l.split('=',1)[1] for l in read(R/'snapshot/Current.set').splitlines() if '=' in l and not l.startswith(';')}
    if name.startswith('New-'):settings={l.split('=',1)[0]:l.split('=',1)[1] for l in read(SET).splitlines() if '=' in l and not l.startswith(';')}
    settings.update(InpTesterFromDateUTC=start.replace('.',''),InpTesterToDateUTC=end.replace('.',''),InpAdaptivePortfolioControls='false')
    if name=='GeometryTests':settings={}
    setname='newsfix-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in settings.items())+'\n'
    (out/'inputs.set').write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
    header=read(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    report=T/'reports/newsfix20261003'/(tag+'.htm');report.parent.mkdir(parents=True,exist_ok=True)
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\NewsFix20261003\\{name}
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode={delay}
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\newsfix20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    free();offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START '+tag)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,startupinfo=si,creationflags=subprocess.CREATE_NO_WINDOW)
    save(R/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),case=tag))
    try:proc.wait(timeout=1200)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise
    journal=''
    for p in logs():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
    (out/'journal.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert report.exists() and report.stat().st_mtime>=began-2,(tag,journal[-3500:])
    assert not re.search(r'initialization failed|critical error|boundary violation=YES',journal,re.I),journal[-3500:]
    if name=='GeometryTests':
        assert 'GEOMETRY_TESTS|failures=0' in journal,journal[-5000:]
        result=dict(tag=tag,passed=True,native_geometry_checks=9)
    else:
        actual=_report_inputs(report)
        assert all(k in actual and _same_setting(v,actual[k]) for k,v in settings.items()),(tag,actual)
        trades=_native_trades(report,tag);native=_native_metrics(report)
        assert len(trades)==native['trades']
        net=sum(x['net_profit'] for x in trades);assert abs(net-native['net_profit'])<.06
        values=[x['net_profit'] for x in trades];gp=sum(x for x in values if x>0);gl=-sum(x for x in values if x<0)
        family=defaultdict(list);unique=Counter();late=[]
        bestwin=bestloss=win=loss=0
        for x in trades:
            parts=x['entry_comment'].split('|');assert len(parts)>=4 and parts[0]=='NP',x
            unique[(parts[1],parts[3])]+=1;family[parts[2]].append(x)
            endtime=int(datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc).timestamp())
            if name.startswith('New-') and endtime>int(parts[1])+30+(delay/1000)+2:late.append(x)
            win=win+1 if x['net_profit']>0 else 0;loss=loss+1 if x['net_profit']<0 else 0
            bestwin=max(bestwin,win);bestloss=max(bestloss,loss)
        assert not any(n>1 for n in unique.values()),'duplicate side/event'
        assert not late,('late owned positions',late)
        audit=re.findall(r'calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(\w+)',journal)
        assert audit,(tag,'missing event audit')
        result=dict(tag=tag,name=name,delay_ms=delay,from_date=start,to_exclusive=end,native=native,
          net_metrics=dict(return_pct=net/100,net_profit=net,pf=gp/gl if gl else None,win_rate_pct=100*sum(x>0 for x in values)/len(values) if values else 0,
              trades=len(trades),max_win_streak=bestwin,max_loss_streak=bestloss,commission=sum(x['commission'] for x in trades),swap=sum(x['swap'] for x in trades)),
          families={k:dict(trades=len(v),net=sum(x['net_profit'] for x in v)) for k,v in family.items()},
          audit=audit[-1],market_fallbacks=journal.count('NP_MARKET_FALLBACK|'),incomplete=journal.count('NP_SETUP_INCOMPLETE|'),
          rejected=journal.count('NP_SIDE_REJECTED|'),uncertain=journal.count('NP_SIDE_UNCERTAIN|'),max_same_side_per_event=max(unique.values(),default=0),
          closure_violations=len(late),source_sha=sha(R/'snapshot'/(name+'.mq5')),binary_sha=sha(DEST/(name+'.ex5')),report_sha=sha(report),seconds=time.time()-began)
        (out/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
        (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
    save(out/'result.json',result);status('DONE '+tag+' '+json.dumps(result.get('net_metrics',result)))
    return result
def main():
    events=prepare();build={}
    for name in ['Current-test','New-fixed-test','GeometryTests']:compile_one(name);build[name]=dict(source=sha(R/'snapshot'/(name+'.mq5')),binary=sha(DEST/(name+'.ex5')))
    save(R/'BUILD.json',build)
    run('GeometryTests',150,'2026.07.01','2026.07.02')
    incident=run('New-fixed-test',150,'2026.10.02','2026.10.03')
    assert list(incident['audit'][1:3])==['1','1'],'Incident straddle was not completely accepted'
    results=[]
    for delay in [150,1000]:
        for name in ['Current-test','New-fixed-test']:results.append(run(name,delay))
    results.append(incident)
    save(R/'SUMMARY.json',dict(results=results,calendar_counts=dict(Counter(x['kind'] for x in events)),risk_per_side=.75,starting_balance=10000,live_deployment=False))
    status('COMPLETE isolated old/new comparison; no active MT5 changes')
if __name__=='__main__':main()
