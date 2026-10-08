"""Allocation regression in the dedicated portable tester; never initializes a live account API."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,time
R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('five_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def case(entry,cash=False,original=False):
 tag=entry['key']+('-ORIGINAL1' if original else '-USD50' if cash else '-PERCENT1')
 out=R/'NativeTests'/tag;out.mkdir(parents=True,exist_ok=True)
 inputs={}
 for line in (R/entry['settings']).read_text().splitlines():
  if '=' in line:k,v=line.split('=',1);inputs[k]=v
 if original:inputs={k:v for k,v in inputs.items() if not k.startswith('InpPortfolio')}
 if cash:
  inputs['InpPortfolioRiskMode']='1';inputs['InpPortfolioFixedUSD']='50.0'
  if entry['hourly']:inputs['InpSizingMode']='2';inputs['InpFixedRiskMoney']='50.0'
 start='2026-09-01' if cash else '2026-07-07';end='2026-10-07'
 binary=(B/entry['original_source']).with_suffix('.ex5') if original else R/entry['expert']
 manifest=dict(inputs=inputs,binary_sha256=sha(binary),start=start,end_exclusive=end,model=4,delay_ms=150,deposit=10000,live_trading=False)
 mp=out/'manifest.json'
 if mp.exists():
  assert json.loads(mp.read_text())==manifest,'Stale native case; retain it and use a new named case'
  if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
 save(mp,manifest);h.free()
 dest=T/'MQL5/Experts/AAA Research/FiveStandalone20261007';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(binary,dest/(tag+'.ex5'))
 setname='five-standalone-'+tag+'.set';setbody='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
 (T/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8');(out/'Parameters.set').write_text(setbody,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 reportdir=T/'reports/five-standalone-20261007';reportdir.mkdir(exist_ok=True);rp=reportdir/(tag+'.htm')
 tf={1:'M1',5:'M5',60:'H1',240:'H4'}[entry['period']]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\FiveStandalone20261007\\{tag}
ExpertParameters={setname}
Symbol={entry['canonical']}
Period={tf}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
ForwardMode=0
Report=reports\\five-standalone-20261007\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 began=time.time();offsets={p:p.stat().st_size for p in h.logfiles()}
 print('START isolated tester '+tag,flush=True)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe')))
 try:proc.wait(timeout=1500)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Isolated tester timeout')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing native report'
 assert not re.search(r'initialization failed|start time changed|not enough history|stop out|margin call|access violation|array out of range|zero divide|invalid stops|invalid volume|not enough money|order rejected',journal,re.I),'Native test/runtime error'
 actual=h._report_inputs(rp)
 assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'Native risk inputs differ'
 report=h._read_report(rp);assert start.replace('-','.') in report and end.replace('-','.') in report
 native=h._native_metrics(rp);trades=h._native_trades(rp,entry['label'])
 assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.05
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(out/'trades.json',trades)
 result=dict(case=tag,native=native,seconds=round(time.time()-began,1),binary_sha256=manifest['binary_sha256'],no_live_account_access=True)
 if original:
  result['original_production_control']=True
 elif cash:
  if entry['hourly']:
   readings=re.findall(r'HOURLY_HISTORICAL_SIZE budget=([\d.]+)',journal)
   assert readings and all(abs(float(x)-50)<1e-8 for x in readings),'Hourly fixed cash allocation changed'
   balance=10000;levels=[]
   for trade in trades:levels.append(balance);balance+=trade['net_profit']
   assert len(set(levels))>1,'No changing balance states'
   result['fixed_cash_budget_verified']=dict(target=50,readings=len(readings),min_balance=min(levels),max_balance=max(levels))
  else:
   budget_rows=re.findall(r'FIVE_RISK mode=1 target=([\d.]+) equity=([\d.]+)',journal)
   assert budget_rows and all(abs(float(x)-50)<1e-8 for x,y in budget_rows),'Fixed USD changed with equity'
   equities=[float(y) for x,y in budget_rows];assert len(set(equities))>1,'Cash test has no changing equity states'
   result['fixed_cash_budget_verified']=dict(target=50,readings=len(budget_rows),min_equity=min(equities),max_equity=max(equities))
 else:
  reference=case(entry,original=True)['native'];old=R/'NativeTests'/(entry['key']+'-ORIGINAL1')
  for key in ('trades','net_profit','profit_factor','win_rate_pct'):assert abs(native[key]-reference[key])<.011,(tag,key,native[key],reference[key])
  reference_path=out/'reference.htm';reference_path.write_bytes(gzip.decompress((old/'report.htm.gz').read_bytes()))
  ref=h._native_trades(reference_path,entry['label']);assert len(ref)==len(trades)
  fields=('side','volume','open_time','close_time','open_price','close_price','net_profit')
  assert all(all(a[k]==b[k] for k in fields) for a,b in zip(trades,ref)),'Trade-by-trade allocation regression'
  result['percentage_1_trade_for_trade_parity']=True
 save(out/'result.json',result);print('PASS '+tag+' '+json.dumps(result.get('fixed_cash_budget_verified',{'trades':native['trades'],'net_profit':native['net_profit']})),flush=True)
 return result
def main():
 lock=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 try:
  package=json.loads((R/'Package.json').read_text());results=[]
  for entry in package['entries']:results.append(case(entry))
  for entry in package['entries']:results.append(case(entry,True))
  controls=[json.loads((R/'NativeTests'/(e['key']+'-ORIGINAL1')/'result.json').read_text()) for e in package['entries']]
  save(R/'VALIDATION.json',dict(native_cases=len(results)+len(controls),all_passed=True,percent_parity_cases=5,original_control_cases=5,fixed_cash_cases=5,real_tick_model=4,live_account_accessed=False,results=results+controls))
  print('All isolated native checks passed. Live terminal was not changed.',flush=True)
 finally:lock.close()
if __name__=='__main__':main()
