from pathlib import Path
import gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('hourly_native_helpers',BASE/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
TESTER=h.TESTER;COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 h.free();src=ROOT/'Hourly11.mq5';log=ROOT/'native-compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-1000:]
 dest=TESTER/'MQL5/Experts/AAA Research/Hourly20261003';shutil.copy2(src.with_suffix('.ex5'),dest/'Hourly11.ex5')
 windows={'5y':('2021.10.02','2026.10.02'),'first3y':('2021.10.02','2024.10.02'),'last2y':('2024.10.02','2026.10.02'),'1y':('2025.10.02','2026.10.02'),'6m':('2026.04.02','2026.10.02'),'3m':('2026.07.02','2026.10.02')}
 results=[]
 for name,(start,end) in windows.items():
  folder=ROOT/'native'/name;folder.mkdir(parents=True,exist_ok=True)
  manifest=dict(window=name,start=start,end=end,lots=1.0,deposit=10000,model=4,delay_ms=150,source_sha256=sha(src),protocol_sha256=sha(ROOT/'PROTOCOL.txt'))
  mp=folder/'manifest.json'
  if mp.exists():assert json.loads(mp.read_text())==manifest
  else:save(mp,manifest)
  if (folder/'results.json').exists():results.append(json.loads((folder/'results.json').read_text()));continue
  h.free();tag='hourly11-'+name;values=dict(InpLots=1.0,InpMagic=10031112,InpTag=tag);setname=tag+'.set';setbody='\n'.join(f'{k}={v}' for k,v in values.items())+'\n'
  (folder/setname).write_text(setbody);(TESTER/'MQL5/Profiles/Tester'/setname).write_text(setbody)
  header=h.text(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
  rp=TESTER/'reports/hourly20261003'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
  ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Hourly20261003\\Hourly11
ExpertParameters={setname}
Symbol=USTEC
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\hourly20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
  profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
  offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();print('START native '+name,flush=True)
  si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
  proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
  save(ROOT/'owned-process.json',dict(pid=proc.pid,executable=str(TESTER/'terminal64.exe')))
  try:proc.wait(timeout=3600)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned native hourly test timed out')
  journal=''
  for p in h.logfiles():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
  (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
  flags=re.findall(r'[^\n]*(?:initialization failed|start time changed|invalid volume|stop out|margin call|access violation|array out of range|zero divide)[^\n]*',journal,re.I)
  assert not flags,'Native failure; inspect ignored journal'
  assert 'entry_fail=0 close_fail=0' in journal
  actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(str(v),actual[k]) for k,v in values.items())
  body=h._read_report(rp);assert all(x in body for x in ('USTEC',start,end))
  from app.mt5_evidence_jobs import _number,_metric
  metrics=h._native_metrics(rp);metrics['max_relative_equity_drawdown_pct']=_number(_metric(body,'Equity Drawdown Relative'))
  trades=h._native_trades(rp,tag);assert len(trades)==metrics['trades'];assert abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<.1
  p=COMMON/f'US100Hourly20261003-{tag}-fills.csv';assert p.exists() and p.stat().st_mtime>=began-2
  (folder/'fills.csv.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));(folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
  save(folder/'trades.json',trades)
  result=dict(manifest=manifest,metrics=metrics,report_sha256=sha(rp),binary_sha256=sha(src.with_suffix('.ex5')),seconds=time.time()-began,tick_notes=sorted(set(re.findall(r'[^\n]*(?:real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded)[^\n]*',journal)))[:30])
  save(folder/'results.json',result);results.append(result);print('DONE native '+name+' '+json.dumps(metrics),flush=True)
 save(ROOT/'NATIVE SUMMARY.json',results)
if __name__=='__main__':main()
