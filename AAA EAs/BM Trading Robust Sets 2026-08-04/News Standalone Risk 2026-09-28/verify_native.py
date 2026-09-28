"""Compile production binaries and verify custom-risk sizing in the isolated tester only.
No active terminal API or deployment. Old binaries are retained before editing.
"""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,os,re,shutil,subprocess,sys,time
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_trades,_native_metrics,_report_inputs,_same_setting
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
 data=path.read_bytes();return data.decode('utf-16') if data[:2] in (b'\xff\xfe',b'\xfe\xff') else data.decode('utf-8-sig',errors='replace')
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
def free():
 p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0 and str(TESTER).lower() not in p.stdout.lower(),'Isolated tester occupied; no process stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in line and 'LISTENING' in line for line in net.splitlines()),'Tester port occupied'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
r=SimpleNamespace(TESTER=TESTER,free=free,logs=logs,sha=sha,read=read,save=save,_native_metrics=_native_metrics,_report_inputs=_report_inputs,_same_setting=_same_setting)
NAMES={'XAU':'AAA Final News Pulse XAU Event Specific EA','MULTI':'AAA Final News Pulse Multi Asset Event EA'}
SYMBOLS={'XAU':'XAUUSD','XAG':'XAGUSD','BTC':'BTCUSD','EURUSD':'EURUSD'}
SETS={'XAU':'12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set','XAG':'12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set','BTC':'12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set','EURUSD':'12D News Pulse EURUSD Event Specific - HARD 1.5 TOTAL.set'}
DEST=r.TESTER/'MQL5/Experts/AAA Research/News Risk 20260928'
def compile_all():
 r.free();DEST.mkdir(parents=True,exist_ok=True);build={}
 if (ROOT/'BUILD.json').exists():
  cached=json.loads((ROOT/'BUILD.json').read_text())
  if all((DEST/f'{key}-new.ex5').exists() and (DEST/f'{key}-old.ex5').exists() and r.sha(BASE/x['source'])==x['source_sha256'] and r.sha((BASE/x['source']).with_suffix('.ex5'))==x['binary_sha256'] and r.sha(DEST/f'{key}-new.ex5')==x['binary_sha256'] and r.sha(DEST/f'{key}-old.ex5')==x['baseline_binary_sha256'] for key,x in cached.items()):return cached
 for key,name in NAMES.items():
  source=BASE/'AAA Final EAs'/name/(name+'.mq5');old=ROOT/'baseline'/(name+'.mq5');log=ROOT/(key+'.compile.log');began=time.time()
  subprocess.run(f'"{r.TESTER/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
  assert '0 errors, 0 warnings' in r.read(log),r.read(log)
  assert source.with_suffix('.ex5').stat().st_mtime>=began-2
  for version,path in [('new',source.with_suffix('.ex5')),('old',old.with_suffix('.ex5'))]:shutil.copy2(path,DEST/f'{key}-{version}.ex5')
  build[key]=dict(source=str(source.relative_to(BASE)),source_sha256=r.sha(source),baseline_source_sha256=r.sha(old),binary_sha256=r.sha(source.with_suffix('.ex5')),baseline_binary_sha256=r.sha(old.with_suffix('.ex5')),compile='0 errors, 0 warnings')
 r.save(ROOT/'BUILD.json',build)
 return build
def case(asset,version,risk,build):
 key='XAU' if asset=='XAU' else 'MULTI';tag=f'{asset}-{version}-{risk:g}';out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 if (out/'result.json').exists():
  saved=json.loads((out/'result.json').read_text());assert saved['build']==build[key];return saved
 settings=dict(line.split('=',1) for line in (BASE/'Selected Portfolio Settings 2026-09-01'/SETS[asset]).read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith(';'))
 settings.update(InpRiskPercent=str(risk),InpTesterFromDateUTC='20260701',InpTesterToDateUTC='20260801',InpAdaptivePortfolioControls='false')
 setname=f'news-risk-{tag}.set';body='\n'.join(f'{k}={v}' for k,v in settings.items())+'\n'
 (out/'inputs.set').write_text(body);(r.TESTER/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\News Risk 20260928\\{key}-{version}
ExpertParameters={setname}
Symbol={SYMBOLS[asset]}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2026.07.01
ToDate=2026.08.01
Report=reports\\news-risk-20260928\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 report=r.TESTER/'reports/news-risk-20260928'/f'{tag}.htm';report.parent.mkdir(parents=True,exist_ok=True)
 r.free();offsets={p:p.stat().st_size for p in r.logs()};began=time.time();print('START',tag,flush=True)
 proc=subprocess.Popen(f'"{r.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=r.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=900)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise
 journal=''
 for p in r.logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (out/'journal.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert report.exists() and report.stat().st_mtime>=began-2,(tag,journal[-1500:])
 assert not re.search(r'initialization failed|critical error|invalid volume|invalid stops|calendar.*failed|hard-locks',journal,re.I),(tag,'runtime error')
 assert 'testing with execution delay 150 milliseconds' in journal
 inputs=r._report_inputs(report)
 for k,v in settings.items():
  assert k in inputs and r._same_setting(v,inputs[k]),(tag,k,v,inputs.get(k))
 trades=_native_trades(report,asset);metrics=r._native_metrics(report)
 assert len(trades)==metrics['trades'] and len(trades)>0,(tag,'no trades')
 (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 result=dict(asset=asset,version=version,risk=risk,build=build[key],inputs=inputs,metrics=metrics,trades=trades,report_sha256=r.sha(report),seconds=time.time()-began)
 r.save(out/'result.json',result);print('DONE',tag,'trades',len(trades),'net',metrics['net_profit'],'seconds',round(time.time()-began,1),flush=True)
 return result
def main():
 build=compile_all();results=[];checks=[]
 for asset in SYMBOLS:
  rows={}
  for version,risk in [('old',.75),('new',.75),('new',.30),('new',1.25)]:
   row=case(asset,version,risk,build);results.append(row);rows[(version,risk)]=row
  old,new=rows[('old',.75)],rows[('new',.75)]
  assert old['trades']==new['trades'],(asset,'default-risk trade parity failed')
  for key in ('net_profit','trades','profit_factor','win_rate_pct'):
   if key in old['metrics']:assert old['metrics'][key]==new['metrics'][key],(asset,key)
  geometry=lambda row:[{k:t[k] for k in ('side','open_time','close_time','open_price','close_price','entry_comment','exit_comment')} for t in row['trades']]
  assert geometry(rows[('new',.30)])==geometry(new)==geometry(rows[('new',1.25)]),(asset,'custom risk changed trade geometry')
  volumes={str(risk):sum(t['volume'] for t in rows[('new',risk)]['trades']) for risk in (.30,.75,1.25)}
  assert volumes['0.3']<volumes['0.75']<volumes['1.25'],(asset,'risk did not change lots')
  checks.append(dict(asset=asset,default_risk_exact_trade_parity=True,custom_risks_initialized_and_traded=[.30,1.25],custom_risk_geometry_unchanged=True,filled_volume_by_risk=volumes,trade_counts={f'{v}-{risk}':len(x['trades']) for (v,risk),x in rows.items()}))
 r.save(ROOT/'NATIVE_VERIFICATION.json',dict(passed=True,window=['2026-07-01','2026-08-01 exclusive'],model=4,delay_ms=150,build=build,checks=checks,runs=results))
 print('PASS all assets: default-risk exact trade parity and custom-risk execution',flush=True)
if __name__=='__main__':main()
