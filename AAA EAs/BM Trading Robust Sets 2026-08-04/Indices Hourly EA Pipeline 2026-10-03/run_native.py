"""Reproducible isolated native runs; never touches the active MT5 checkout."""
from pathlib import Path
import gzip, hashlib, json, os, re, shutil, subprocess, time
R=Path(__file__).resolve().parent
T=R.parent/'_Backtests/MT5-DMC-20260811'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
SOURCE=R/'CalyxHourlyProfiles.mq5'
DEST=T/'MQL5/Experts/AAA Research/HourlyProfiles20261003'
ASSETS={'US30':('US30',1),'US100':('USTEC',2),'SP500':('US500',3)}
WINDOWS={'5y':'2021.10.03','3y':'2023.10.03','1y':'2025.10.03','6m':'2026.04.03','3m':'2026.07.03','real2026':'2026.01.01'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def run(cmd,**kw):return subprocess.run(cmd,creationflags=subprocess.CREATE_NO_WINDOW,**kw)
def free():
 a=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True)
 assert a.returncode==0 and str(T).lower() not in a.stdout.lower(),'Isolated terminal is already running'
 net=run(['netstat','-ano','-p','TCP'],capture_output=True,text=True).stdout
 assert not any(':3000 ' in s and 'LISTENING' in s for s in net.splitlines()),'Tester agent is busy'
def compile_ea():
 free();log=R/'compile.log';run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',timeout=120)
 txt=read(log);assert '0 errors, 0 warnings' in txt,txt[-3500:]
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'CalyxHourlyProfiles.ex5')
 save(R/'BUILD.json',{'source_sha256':sha(SOURCE),'binary_sha256':sha(SOURCE.with_suffix('.ex5')),'compile_clean':True,'destination':str(DEST),'not_installed_on_active_terminal':True})
def freeze():
 source=R.parent/'Indices Hourly Comparison 2026-10-03/NATIVE-SUMMARY.json';rows=json.loads(source.read_text())
 selected=[r for r in rows if r['window']=='1y' and r['pf'] is not None and r['pf']>=1.2 and r['win_rate_pct']>=50]
 assert len(selected)==11
 save(R/'SELECTED-HOURS.json',{'source':str(source),'source_sha256':sha(source),'pf_threshold':1.2,'win_rate_threshold_pct':50,'selection_window':['2025-10-03','2026-10-03'],'hours':selected,'quarter_is_not_holdout':True})
 for asset,(sym,profile) in ASSETS.items():
  h=[r for r in selected if r['asset']==asset];assert len(set(r['hour'] for r in h))==len(h)
  (R/(asset+'.set')).write_text(f'InpProfile={profile}\nInpBuyHours=\nInpSellHours=\nInpLots=1.0\nInpEntryMinute=0\nInpHoldMinutes=60\nInpMagic=103310\nInpAllowRealAccount=false\nInpAutoServerUTC=true\nInpServerUTCOffsetMinutes=0\nInpAuditTag=hour-profile-{asset}\n',encoding='utf-8')
def one(asset,window,variant='baseline',minute=0,hold=60,delay=150,deposit=10000,expert='CalyxHourlyProfiles'):
 symbol,profile=ASSETS[asset];start=WINDOWS[window];tag=f'hourprof-20261003-{asset}-{window}-{variant}'
 folder=R/'native'/tag;folder.mkdir(parents=True,exist_ok=True)
 signature={'asset':asset,'symbol':symbol,'window':window,'variant':variant,'from':start,'to_exclusive':'2026.10.03','entry_minute':minute,'hold_minutes':hold,'delay_ms':delay,'deposit':deposit,'lots':1,'model':4,'source_sha256':sha(SOURCE),'binary_sha256':sha(SOURCE.with_suffix('.ex5'))}
 if expert!='CalyxHourlyProfiles':signature['expert']=expert
 if (folder/'RESULT.json').exists():
  old=json.loads((folder/'RESULT.json').read_text());assert all(old.get(k)==v for k,v in signature.items()),'Stale cached run';return old
 free();header=read(R.parent/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 setname=tag+'.set';text=(R/(asset+'.set')).read_text().replace('InpEntryMinute=0',f'InpEntryMinute={minute}').replace('InpHoldMinutes=60',f'InpHoldMinutes={hold}').replace(f'InpAuditTag=hour-profile-{asset}',f'InpAuditTag={tag}')
 setpath=T/'MQL5/Profiles/Tester'/setname;setpath.write_text(text);(folder/'inputs.set').write_text(text)
 ini=folder/'tester.ini';report=T/'reports/hourprofiles20261003'/(tag+'.htm');report.parent.mkdir(parents=True,exist_ok=True)
 ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\HourlyProfiles20261003\\{expert}
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit={deposit}
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode={delay}
Optimization=0
FromDate={start}
ToDate=2026.10.03
Report=reports\\hourprofiles20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr'))
 def logs():return list((T/'logs').glob('*.log'))+list((T/'Tester/logs').glob('*.log'))+list((T/'Tester').glob('Agent-*/logs/*.log'))
 offsets={p:p.stat().st_size for p in logs()};began=time.time();print('START',tag,flush=True)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(R/'owned-process.json',{'pid':proc.pid,'executable':str(T/'terminal64.exe'),'config':str(ini)})
 try:proc.wait(timeout=1800)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Only owned isolated pass timed out')
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and report.exists() and report.stat().st_mtime>=began-2
 assert 'HOURLY_COMPLETE' in journal,journal[-2500:]
 assert not re.search(r'initialization failed|access violation|array out of range|zero divide|start time changed',journal,re.I)
 # Stop-outs/margin failures are retained as research failures, not hidden.
 for suffix in ['deals','curve','fills','audit']:
  p=COMMON/f'{tag}-{suffix}.csv';assert p.exists() and p.stat().st_mtime>=began-2
  (folder/f'{suffix}.csv.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0))
 (folder/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 result=signature|{'tag':tag,'seconds':time.time()-began,'set_sha256':sha(folder/'inputs.set'),'report_sha256':sha(report),'account_failure':bool(re.search(r'stop out|margin call',journal,re.I)),'tick_notes':sorted(set(s for s in journal.splitlines() if re.search('real ticks begin|real ticks absent|generated ticks|ticks discarded',s)))[:30]}
 save(folder/'RESULT.json',result);print('DONE',tag,round(result['seconds'],1),flush=True);return result
def main():
 freeze();compile_ea();results=[]
 # Get recent combined-profile evidence first, then long stability extensions.
 for w in ['1y','3m','3y','5y','real2026']:
  for a in ASSETS:results.append(one(a,w));save(R/'NATIVE.json',results)
 for a in ASSETS:
  results.append(one(a,'1y','delay500',delay=500));save(R/'NATIVE.json',results)
  # Predeclared sensitivity, not reoptimization of selected hours.
  for v,m,h in [('entry05',5,60),('hold45',0,45),('hold75',0,75)]:
   results.append(one(a,'1y',v,minute=m,hold=h));save(R/'NATIVE.json',results)
 print('NATIVE PIPELINE COMPLETE',len(results),flush=True)
if __name__=='__main__':main()
