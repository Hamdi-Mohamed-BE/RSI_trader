"""Native MT5 tester only. Never connects to or changes the live terminal."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import csv,gzip,hashlib,json,os,re,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
TESTER=BASE/'_Backtests/MT5-DMC-20260811';DEST=TESTER/'MQL5/Experts/AAA Research/Okala802020260928'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/Calyx802020260928'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(msg,**extra):save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=msg,**extra));print(msg,json.dumps(extra),flush=True)
def free():
 p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0 and str(TESTER).lower() not in p.stdout.lower(),'Isolated tester in use; no process stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in line and 'LISTENING' in line for line in net.splitlines()),'Tester port occupied'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def compile_ea():
 free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"Okala8020.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=read(log);assert '0 errors, 0 warnings' in body,body
 assert (ROOT/'Okala8020.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Okala8020.ex5',DEST/'Okala8020.ex5')
 save(ROOT/'BUILD.json',dict(hashes={p:sha(ROOT/p) for p in ('Okala8020.mq5','Okala8020.ex5','RULES.md','run-config.json')},compile=body[-500:]))
 status('Clean compile: 0 errors, 0 warnings')
def case(v,window,model=4):
 smoke=window=='smoke';tag=v['name']+'-'+window+f'-m{model}'
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text())
 for p,h in build['hashes'].items():assert sha(ROOT/p)==h,(p,'frozen input changed')
 assert sha(DEST/'Okala8020.ex5')==build['hashes']['Okala8020.ex5']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['ok'] and old['build']==build;status('REUSE '+tag);return
 start,end=(CFG['smoke_start'],CFG['smoke_end']) if smoke else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=2)).strftime('%Y.%m.%d')
 vals=dict(InpSetup=v['setup'],InpGridShift=v['grid_shift'],InpExit=v['exit'],InpFixedRisk=CFG['fixed_risk_money'],InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9288020)
 setname='o8-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Okala802020260928\\Okala8020
ExpertParameters={setname}
Symbol={CFG['symbol']}
Period=M1
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\okala802020260928\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/okala802020260928'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(120):
  try:free();break
  except AssertionError:
   if attempt==119:raise
   time.sleep(5)
 offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned research test timed out: '+tag)
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2,('No fresh report',journal[-1500:])
 rb=_read_report(rp);actual=_report_inputs(rp)
 expected={**vals,'InpTradeFrom':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
 bad=[k for k,v in expected.items() if k not in actual or not _same_setting(str(v),actual[k])];assert not bad,(bad,actual)
 assert all(v in rb for v in (warm,end,CFG['symbol'],'Okala8020'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(p,journal,re.I)) for k,p in dict(init_failed=r'initialization failed|INIT_FAILED',critical=r'critical error|access violation',history_shortened=r'testing start time changed|start date changed|no history data|not enough history',invalid_volume=r'invalid volume',invalid_stops=r'invalid stops',order_fail=r'O8_FAIL',market_closed=r'market closed',margin_call=r'stop out|margin call').items()}
 assert not any(flags[k] for k in ['init_failed','critical','history_shortened','invalid_volume','order_fail']),flags
 for suffix in ['groups.csv','deals.csv','trace.bin']:
  src=COMMON/f'{tag}-{suffix}';assert src.exists() and src.stat().st_mtime>=began-2
  (out/(suffix+'.gz')).write_bytes(gzip.compress(src.read_bytes(),mtime=0))
 groups=list(csv.DictReader(gzip.decompress((out/'groups.csv.gz').read_bytes()).decode('utf-8-sig').splitlines()))
 deals=list(csv.DictReader(gzip.decompress((out/'deals.csv.gz').read_bytes()).decode('utf-8-sig').splitlines()))
 net=sum(sum(float(d[k]) for k in ['profit','commission','swap','fee']) for d in deals if int(d['type']) in (0,1))
 metrics=_native_metrics(rp);metrics.update(equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')))
 assert abs(net-metrics['net_profit'])<.02,('native cash',net,metrics)
 assert abs(sum(float(g['net']) for g in groups)-net)<.02,('group cash',net)
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 result=dict(ok=True,variant=v,window=window,model=model,start=start,end=end,warmup_start=warm,build=build,inputs=actual,metrics=metrics,groups=len(groups),flags=flags,report_sha=sha(rp),elapsed_seconds=time.time()-began,
   summaries=sorted(set(re.findall(r'O8_SUMMARY[^\r\n]*',journal))),spec=sorted(set(re.findall(r'O8_SPEC[^\r\n]*',journal))),
   tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))
 save(out/'run.json',result);status('DONE '+tag,groups=len(groups),net=net,seconds=round(time.time()-began,1))
def main():
 mode=sys.argv[1]
 if mode=='compile':compile_ea();return
 if mode=='smoke':case(CFG['variants'][3],'smoke');return
 if mode=='year':
  for v in CFG['variants']:case(v,'1y')
 elif mode=='history':
  for model,windows in [(1,['3y','5y']),(4,['6m','3y','5y'])]:
   for w in windows:
    for v in CFG['variants'][3:5]:case(v,w,model)
 elif mode=='case':case(next(v for v in CFG['variants'] if v['name']==sys.argv[2]),sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else 4)
 else:raise SystemExit('compile | smoke | year | history | case variant window [model]')
 status('COMPLETE '+mode)
if __name__=='__main__':main()
