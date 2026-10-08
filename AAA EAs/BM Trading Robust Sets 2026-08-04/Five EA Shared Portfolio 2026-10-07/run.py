"""Isolated native shared-account tester. No live terminal API or production writes."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, importlib.util, io, json, msvcrt, os, re, shutil, subprocess, sys, time
R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('native_shared_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER; SOURCE=R/'SharedPortfolio.mq5'; DEST=T/'MQL5/Experts/AAA Research/FiveShared20261007'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(s,**v):save(R/'status.json',dict(message=s,utc=datetime.now(timezone.utc).isoformat(),**v));print(s,json.dumps(v),flush=True)
def lease():
 f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);return f
def compile_adapter():
 h.free();began=time.time();log=R/'compile.log'
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log);assert '0 errors, 0 warnings' in body,body[-6500:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'BUILD.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')),config_sha256=sha(R/'CONFIG.json'),compile='0 errors, 0 warnings'))
 status('COMPILED frozen five-module shared-account adapter')
def case(index,start='2026-07-07',end='2026-10-07',tag=None,primary=None,production=False):
 config=json.loads((R/'CONFIG.json').read_text());row=config['entries'][index-1] if index else None
 primary=primary or (row['symbol'] if row else 'XAUUSD');tf={1:'M1',5:'M5',16385:'H1',16388:'H4'}[row['timeframe']] if row else 'H1'
 tag=tag or ('combined' if index==0 else row['key']+'-alone')+('-PRODUCTION' if production else '')
 out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 binary=(B/row['source']).with_suffix('.ex5') if production else SOURCE.with_suffix('.ex5')
 inputs=row['inputs'] if production else {'InpCase':str(index)}
 manifest=dict(tag=tag,index=index,primary_symbol=primary,period=tf,start=start,end_exclusive=end,model=4,delay_ms=150,deposit=10000,production=production,binary_sha256=sha(binary),config_sha256=sha(R/'CONFIG.json'),inputs=inputs)
 mp=out/'manifest.json'
 if mp.exists():
  assert json.loads(mp.read_text())==manifest,'Frozen test changed'
  if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 else:save(mp,manifest)
 h.free();DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(binary,DEST/(tag+'.ex5'))
 body='\n'.join(k+'='+v for k,v in inputs.items())+'\n';setname='five20261007-'+tag+'.set'
 (out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 rd=T/'reports/five-shared-20261007';rd.mkdir(parents=True,exist_ok=True);rp=rd/(tag+'.htm')
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\FiveShared20261007\\{tag}
ExpertParameters={setname}
Symbol={primary}
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
Report=reports\\five-shared-20261007\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 began=time.time();offsets={p:p.stat().st_size for p in h.logfiles()};status('START '+tag,start=start,end_exclusive=end)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(T/'terminal64.exe')))
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timeout')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing native report'
 assert not re.search(r'initialization failed|start time changed|not enough history|stop out|margin call|access violation|array out of range|zero divide',journal,re.I),'Invalid native test'
 report=h._read_report(rp)
 assert start.replace('-','.') in report and end.replace('-','.') in report
 if production:
  actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'Wrong production inputs'
 else:assert f'InpCase={index}' in report
 from app.mt5_evidence_jobs import _metric,_number
 native=h._native_metrics(rp);native['floating_dd_relative_pct']=_number(_metric(report,'Equity Drawdown Relative'));native['balance_dd_relative_pct']=_number(_metric(report,'Balance Drawdown Relative'))
 if not production:
  for suffix in ('deals','curve'):
   p=COMMON/f'five20261007-case{index}-{suffix}.csv';assert p.exists() and p.stat().st_mtime>=began-2
   (out/(suffix+'.csv.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
  deals=list(csv.DictReader(io.StringIO(gzip.decompress((out/'deals.csv.gz').read_bytes()).decode('utf-8-sig'))))
  cash=sum(float(d['profit'])+float(d['commission'])+float(d['swap'])+float(d['fee']) for d in deals)
  assert abs(cash-native['net_profit'])<.05,(cash,native)
 else:deals=[]
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 for p in rp.parent.glob(tag+'*.png'):shutil.copy2(p,out/p.name)
 warnings={label:len(re.findall(pattern,journal,re.I)) for label,pattern in {'invalid_stops':'invalid stops','invalid_volume':'invalid volume','market_closed':'market closed','not_enough_money':'not enough money','entry_reject':'ENTRY_REJECT|N5EMA order rejected','hourly_close_reject':'HOURLY_CLOSE_REJECT'}.items()}
 result=dict(manifest=manifest,native=native,seconds=round(time.time()-began,1),warnings=warnings,report_sha256=sha(rp),tick_notes=sorted(set(line.strip() for line in journal.splitlines() if re.search(r'real ticks begin|real ticks absent|ticks discarded',line,re.I)))[:30],audit=re.findall(r'FIVE_COMPLETE[^\r\n]*',journal),raw_deals=len(deals))
 save(out/'results.json',result);status('DONE '+tag,native=native,warnings=warnings);return result
def main():
 held=lease();action=sys.argv[1]
 if action=='compile':compile_adapter()
 elif action=='smoke':case(0,'2026-09-28','2026-10-03','smoke-r2')
 elif action=='case':case(int(sys.argv[2]))
 elif action=='all':
  case(0)
  for i in range(1,6):case(i)
  status('COMPLETE combined native test and five standalone controls')
 elif action=='production':case(int(sys.argv[2]),production=True)
 else:raise ValueError(action)
 held.close()
if __name__=='__main__':main()
