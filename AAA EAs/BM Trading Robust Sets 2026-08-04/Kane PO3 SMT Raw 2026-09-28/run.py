"""Native MT5 tester only. Never connects to or changes the live terminal."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import csv,gzip,hashlib,json,os,re,shutil,subprocess,sys,time,msvcrt
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
TESTER=BASE/'_Backtests/MT5-DMC-20260811';DEST=TESTER/'MQL5/Experts/AAA Research/Kane20260928'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxKane20260928'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def closed_races(journal):
 """A stop fill can win the 150 ms race against our explicit close request."""
 lines=journal.splitlines();count=0
 for i,line in enumerate(lines):
  if 'CB_FAIL close 10036' not in line:continue
  nearby='\n'.join(lines[max(0,i-12):i])
  position=re.search(r'position #(\d+)[^\r\n]*\[position closed\]',nearby)
  assert position and re.search(r'(?:stop loss|take profit) triggered #'+position[1]+r'\b',nearby),('Unexplained already-closed race',nearby)
  count+=1
 return count
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
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"KaneProxy.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=read(log);assert '0 errors, 0 warnings' in body,body
 assert (ROOT/'KaneProxy.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'KaneProxy.ex5',DEST/'KaneProxy.ex5')
 save(ROOT/'BUILD.json',dict(hashes={p:sha(ROOT/p) for p in ('KaneProxy.mq5','KaneProxy.ex5','RULES.md','run-config.json')},compile=body[-500:]))
 status('Clean compile: 0 errors, 0 warnings')
def case(v,window,model=4,symbol='USTEC',attempt=0):
 # Process-level lease closes the check-then-launch race between queued research batches.
 with (ROOT/'tester.lock').open('r+b') as lease:
  while True:
   try:
    lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);break
   except OSError:time.sleep(1)
  try:return _case(v,window,model,symbol,attempt)
  finally:
   lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_UNLCK,1)

def _case(v,window,model=4,symbol='USTEC',attempt=0):
 smoke=window=='smoke';tag=symbol+'-'+v['name']+'-'+window+f'-m{model}'
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text())
 for p,h in build['hashes'].items():assert sha(ROOT/p)==h,(p,'frozen input changed')
 assert sha(DEST/'KaneProxy.ex5')==build['hashes']['KaneProxy.ex5']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['ok'] and old['build']==build;status('REUSE '+tag);return
 if (out/'invalid.json').exists():
  old=json.loads((out/'invalid.json').read_text());assert old['build']==build;status('REUSE DATA-BLOCKED '+tag);return
 prior=out/'journal.txt.gz'
 if prior.exists() and 'tester agent authorization error' in gzip.decompress(prior.read_bytes()).decode():
  archive=out/f'infrastructure-failure-{len(list(out.glob("infrastructure-failure-*.journal.gz"))):02d}.journal.gz'
  shutil.copy2(prior,archive)
 start,end=(CFG['smoke_start'],CFG['smoke_end']) if smoke else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=60)).strftime('%Y.%m.%d')
 vals=dict(InpMode=v['mode'],InpBoth=str(v['both']).lower(),InpRR=v['rr'],InpProtected=str(v['protected']).lower(),InpFixedRisk=CFG['fixed_risk_money'],InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9282605)
 setname='kn-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Kane20260928\\KaneProxy
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\kane20260928\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/kane20260928'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 for wait_attempt in range(120):
  try:free();break
  except AssertionError:
   if wait_attempt==119:raise
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
 if not actual and 'tester agent authorization error' in journal and attempt<2:
  (out/f'infrastructure-failure-{attempt:02d}.report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
  status('RETRY tester connection only '+tag,attempt=attempt+1)
  time.sleep(5)
  return _case(v,window,model,symbol,attempt+1)
 expected={**vals,'InpTradeFrom':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
 bad=[k for k,v in expected.items() if k not in actual or not _same_setting(str(v),actual[k])];assert not bad,(bad,actual)
 assert all(v in rb for v in (warm,end,symbol,'KaneProxy'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(p,journal,re.I)) for k,p in dict(init_failed=r'initialization failed|INIT_FAILED',critical=r'critical error|access violation',history_shortened=r'testing start time changed|start date changed|no history data|not enough history',invalid_volume=r'invalid volume',invalid_stops=r'invalid stops',order_fail=r'CB_FAIL',market_closed=r'market closed',margin_call=r'stop out|margin call').items()}
 races=closed_races(journal);flags['order_fail']-=races
 if flags['market_closed'] and window in ('3y','5y'):
  (out/'invalid-report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
  for suffix in ['groups.csv','deals.csv','trace.bin','signals.csv','management.csv']:
   src=COMMON/f'{tag}-{suffix}'
   if src.exists() and src.stat().st_mtime>=began-2:(out/('invalid-'+suffix+'.gz')).write_bytes(gzip.compress(src.read_bytes(),mtime=0))
  first=next((line for line in journal.splitlines() if 'CB_FAIL' in line),'')
  save(out/'invalid.json',dict(ok=False,tag=tag,symbol=symbol,variant=v['name'],window=window,model=model,build=build,flags=flags,first_failure=first,
   reason='Historical source/session cutoff execution failure: Market Closed. No valid performance or promotion inference.',report_sha=sha(rp)))
  status('DATA-BLOCKED '+tag,market_closed=flags['market_closed']);return
 assert not any(flags[k] for k in ['init_failed','critical','history_shortened','invalid_volume','invalid_stops','order_fail']),flags
 for suffix in ['groups.csv','deals.csv','trace.bin','signals.csv','management.csv']:
  src=COMMON/f'{tag}-{suffix}';assert src.exists() and src.stat().st_mtime>=began-2
  (out/(suffix+'.gz')).write_bytes(gzip.compress(src.read_bytes(),mtime=0))
 groups=list(csv.DictReader(gzip.decompress((out/'groups.csv.gz').read_bytes()).decode('utf-8-sig').splitlines()))
 deals=list(csv.DictReader(gzip.decompress((out/'deals.csv.gz').read_bytes()).decode('utf-8-sig').splitlines()))
 net=sum(sum(float(d[k]) for k in ['profit','commission','swap','fee']) for d in deals if int(d['type']) in (0,1))
 metrics=_native_metrics(rp);metrics.update(equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')))
 pnl=[float(g['net']) for g in groups];loss=-sum(min(x,0) for x in pnl)
 metrics['idea_pf']=sum(max(x,0) for x in pnl)/loss if loss>0 else None
 assert abs(net-metrics['net_profit'])<.02,('native cash',net,metrics)
 assert abs(sum(float(g['net']) for g in groups)-net)<.02,('group cash',net)
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 result=dict(ok=True,symbol=symbol,variant=v,window=window,model=model,start=start,end=end,warmup_start=warm,build=build,inputs=actual,metrics=metrics,groups=len(groups),flags=flags,report_sha=sha(rp),elapsed_seconds=time.time()-began,
   summaries=sorted(set(re.findall(r'CB_SUMMARY[^\r\n]*',journal))),spec=sorted(set(re.findall(r'CB_SPEC[^\r\n]*',journal))),
   tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))),verified_already_closed_log_lines=races)
 save(out/'run.json',result);status('DONE '+tag,groups=len(groups),net=net,seconds=round(time.time()-began,1))
def main():
 mode=sys.argv[1]
 if mode=='compile':compile_ea();return
 if mode=='smoke':
  for symbol in CFG['symbols']:
   for name in [v['name'] for v in CFG['variants']]:
    case(next(v for v in CFG['variants'] if v['name']==name),'smoke',4,symbol)
 elif mode in ('year','recent','screen'):
  jobs={'year':[(4,'1y')],'recent':[(4,'6m')],'screen':[(1,'3y'),(1,'5y')]}[mode]
  for model,window in jobs:
   for symbol in CFG['symbols']:
    for v in CFG['variants']:case(v,window,model,symbol)
 elif mode=='confirm':
  selection=[]
  for symbol in CFG['symbols']:
   chosen=set()
   for v in CFG['variants']:
    if 'control' not in v:continue
    missing=[f"{symbol}-{n}-{w}-m1" for n in (v['name'],v['control']) for w in ('3y','5y') if not (ROOT/'native'/f"{symbol}-{n}-{w}-m1/run.json").exists()]
    if missing:
     selection.append(dict(symbol=symbol,variant=v['name'],screen_pass=False,evidence_status='blocked',missing_valid_cases=missing));continue
    rs=[json.loads((ROOT/'native'/f"{symbol}-{v['name']}-{w}-m1/run.json").read_text()) for w in ('3y','5y')]
    cs=[json.loads((ROOT/'native'/f"{symbol}-{v['control']}-{w}-m1/run.json").read_text()) for w in ('3y','5y')]
    passed=all(not r['flags']['margin_call'] and not c['flags']['margin_call'] and r['metrics']['net_profit']>0 and (r['metrics']['idea_pf'] or 0)>=1.15 and r['groups']>=30 and r['metrics']['net_profit']>c['metrics']['net_profit'] for r,c in zip(rs,cs))
    selection.append(dict(symbol=symbol,variant=v['name'],screen_pass=passed))
    if passed:chosen.update((v['name'],v['control']))
   for v in CFG['variants']:
    if v['name'] in chosen:
     for w in ('3y','5y'):case(v,w,4,symbol)
  save(ROOT/'SELECTION.json',selection)
 elif mode=='case':case(next(v for v in CFG['variants'] if v['name']==sys.argv[2]),sys.argv[3],int(sys.argv[4]),sys.argv[5])
 else:raise SystemExit('compile | smoke | year | recent | screen | confirm | case name window model symbol')
 status('COMPLETE '+mode)
if __name__=='__main__':main()
