from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,time,re
R=Path(__file__).resolve().parent;T=R.parent/'_Backtests/MT5-DMC-20260811'
C=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def run(cmd,**kw):return subprocess.run(cmd,creationflags=subprocess.CREATE_NO_WINDOW,**kw)
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def save(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def free():
 a=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True)
 assert a.returncode==0 and str(T).lower() not in a.stdout.lower()
 net=run(['netstat','-ano','-p','TCP'],capture_output=True,text=True).stdout
 assert not any(':3000 ' in x and 'LISTENING' in x for x in net.splitlines())
def main():
 free();src=R/'HourlyAll.mq5';log=R/'native-compile.log'
 run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log)[-2500:]
 dest=T/'MQL5/Experts/AAA Research/IndicesHourly20261003';shutil.copy2(src.with_suffix('.ex5'),dest/'HourlyAll.ex5')
 header=read(R.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 def logs():return list((T/'logs').glob('*.log'))+list((T/'Tester/logs').glob('*.log'))+list((T/'Tester').glob('Agent-*/logs/*.log'))
 results=[]
 for symbol in ['US30','USTEC','US500']:
  for window,start in [('1y','2025.10.03'),('3m','2026.07.03')]:
   for overnight in ([False,True] if symbol=='US500' else [False]):
    tag=f'indices-20261003-{symbol}-{window}'+('-overnight' if overnight else '')
    folder=R/'native'/tag;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'RESULT.json').exists():results.append(json.loads((folder/'RESULT.json').read_text()));continue
    free();setname=tag+'.set';(T/'MQL5/Profiles/Tester'/setname).write_text(f'InpOvernight={str(overnight).lower()}\nInpLots=1.0\nInpTag={tag}\n')
    ini=folder/'tester.ini';report=T/'reports/indices20261003'/(tag+'.htm');report.parent.mkdir(parents=True,exist_ok=True)
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\IndicesHourly20261003\\HourlyAll
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit=1000000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate=2026.10.03
Report=reports\\indices20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in logs()};began=time.time();print('START NATIVE',tag,flush=True)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(R/'owned-process.json',{'pid':proc.pid,'executable':str(T/'terminal64.exe'),'config':str(ini)})
    try:proc.wait(timeout=1200)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only isolated native pass timed out')
    journal=''
    for p in logs():
     if p.stat().st_mtime<began-2:continue
     with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and report.exists() and report.stat().st_mtime>=began-2
    count=re.findall(r'HOUR_NATIVE_COMPLETE errors=(\d+)',journal);assert count,journal[-2000:]
    # A quoted minute need not be tradable. Reject any non-session failure;
    # delayed/rejected session samples are explicitly excluded in statistics.
    failed=[x for x in journal.splitlines() if 'failed market' in x]
    assert all('[Market closed]' in x for x in failed),failed[:5]
    entry_errors=re.findall(r'HOUR_ORDER_ERROR \d+ (\d+)',journal)
    assert all(x=='10018' for x in entry_errors),entry_errors[:5]
    assert not re.search(r'initialization failed|stop out|margin call|access violation|array out of range|zero divide|start time changed',journal,re.I)
    for suffix in ['deals','equity']:
     p=C/f'{tag}-{suffix}.csv';assert p.exists() and p.stat().st_mtime>=began-2
     (folder/f'{suffix}.csv.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    (folder/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
    result={'tag':tag,'symbol':symbol,'window':window,'overnight':overnight,'seconds':time.time()-began,'source_sha256':sha(src),'binary_sha256':sha(src.with_suffix('.ex5')),'report_sha256':sha(report),'model':4,'delay_ms':150,'execution_balance':1000000,'strategy_reference':10000,'session_rejected_requests':int(count[-1]),'session_rejected_entries':len(entry_errors)//2,'tick_notes':sorted(set(x for x in journal.splitlines() if re.search('real ticks begin|real ticks absent|generated ticks|ticks discarded',x)))[:15]}
    save(folder/'RESULT.json',result);results.append(result);save(R/'NATIVE.json',results);print('DONE NATIVE',tag,result['seconds'],flush=True)
if __name__=='__main__':main()
