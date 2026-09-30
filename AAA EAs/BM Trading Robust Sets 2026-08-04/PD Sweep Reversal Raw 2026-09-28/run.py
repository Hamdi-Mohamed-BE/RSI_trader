"""Sequential isolated native tester. No active-terminal API, trading or deployment."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import csv,gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
DEST=TESTER/'MQL5/Experts/AAA Research/PD Sweep 20260928'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxPDSweep20260928'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(msg,**kwargs):
 save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=msg,**kwargs));print(msg,json.dumps(kwargs),flush=True)
def free():
 p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0,p.stderr
 assert str(TESTER).lower() not in p.stdout.lower(),'Isolated tester occupied; no process stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in l and 'LISTENING' in l for l in net.splitlines()),'Tester port occupied'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def compile_ea():
 free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"Sweep.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=read(log);assert '0 errors, 0 warnings' in body,body
 assert (ROOT/'Sweep.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Sweep.ex5',DEST/'Sweep.ex5')
 build={p:sha(ROOT/p) for p in ('Sweep.mq5','Sweep.ex5','RULES.md','run-config.json')}
 save(ROOT/'BUILD.json',dict(hashes=build,compile=body[-500:],compiled_utc=datetime.now(timezone.utc).isoformat()))
 status('Clean compile: 0 errors, 0 warnings')
def ledger(path):
 rows=list(csv.DictReader(path.read_text(encoding='utf-8-sig').splitlines()));groups={}
 for r in rows:
  if int(r['type']) not in (0,1):continue
  groups.setdefault(r['position'],[]).append(r)
 trades=[]
 for pid,ds in groups.items():
  ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry']) in (1,3)]
  assert ins and outs and len(ins)==1,(pid,'unexpected position structure')
  assert abs(sum(float(d['volume']) for d in ins)-sum(float(d['volume']) for d in outs))<1e-7,(pid,'not fully closed')
  ent=ins[0];ext=max(outs,key=lambda d:int(d['time_msc']))
  cash={k:sum(float(d[k]) for d in ds) for k in ('profit','commission','swap','fee')}
  trades.append(dict(position_id=pid,order=ent['order'],side='Long' if int(ent['type'])==0 else 'Short',volume=float(ent['volume']),
   open_time=datetime.fromtimestamp(int(ent['time']),timezone.utc).replace(tzinfo=None).isoformat(),
   close_time=datetime.fromtimestamp(int(ext['time']),timezone.utc).replace(tzinfo=None).isoformat(),
   open_msc=int(ent['time_msc']),close_msc=int(ext['time_msc']),open_price=float(ent['price']),close_price=float(ext['price']),
   gross_profit=cash['profit'],commission=cash['commission'],swap=cash['swap'],fee=cash['fee'],net_profit=round(sum(cash.values()),8),
   entry_comment=ent['comment'],exit_comment=ext['comment'],magic=int(ent['magic'])))
 return sorted(trades,key=lambda t:(t['close_msc'],int(t['position_id'])))
def case(asset,tf,variant,window,smoke=False):
 symbol=CFG['symbols'][asset];control=variant=='random-direction-control'
 tag=('smoke-' if smoke else '')+f'{asset}-M{tf}-'+('control' if control else 'reversal')+'-'+window
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text())
 for p,h in build['hashes'].items():assert sha(ROOT/p)==h,(p,'modified frozen input')
 assert sha(DEST/'Sweep.ex5')==build['hashes']['Sweep.ex5']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['ok'] and old['build']==build;return
 start,end=(CFG['smoke_start'],CFG['smoke_end']) if smoke else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=CFG['warmup_days'])).strftime('%Y.%m.%d')
 vals=dict(InpTimeframe=tf,InpControl=str(control).lower(),InpRiskPercent=CFG['risk_percent'],InpRR=CFG['rr'],InpSeed=CFG['control_seed'],InpTradeFrom=start+' 00:00:00',InpExportBars=str(not control and window=='5y' and not smoke).lower(),InpTag=tag,InpMagic=9282610)
 setname='pds-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\PD Sweep 20260928\\Sweep
ExpertParameters={setname}
Symbol={symbol}
Period=M{tf}
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\pd-sweep-20260928\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/pd-sweep-20260928'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(120):
  try:free();break
  except AssertionError:
   if attempt==119:raise
   time.sleep(5)
 offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated tester timed out: '+tag)
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2,('No fresh report',journal[-1200:])
 rb=_read_report(rp);actual=_report_inputs(rp)
 expected={**vals,'InpTradeFrom':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
 bad=[k for k,v in expected.items() if k not in actual or not _same_setting(str(v),actual[k])];assert not bad,(bad,actual)
 assert all(v in rb for v in (warm,end,symbol,'Sweep'))
 assert 'testing with execution delay 150 milliseconds' in journal
 flags={k:len(re.findall(p,journal,re.I)) for k,p in {
  'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','export_failed':r'PS_EXPORT_FAIL',
  'history_shortened':r'testing start time changed|start date changed|no history data|not enough history',
  'invalid_volume':r'invalid volume','invalid_stops':r'invalid stops','market_closed':r'market closed','margin_call':r'stop out|margin call'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','export_failed','history_shortened','invalid_volume')),flags
 export=COMMON/f'{tag}-deals.csv';assert export.exists() and export.stat().st_mtime>=began-2
 shutil.copy2(export,out/'deals.csv');trades=ledger(out/'deals.csv');metrics=_native_metrics(rp)
 metrics.update(max_equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),max_balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')),max_equity_dd_usd=_number(_metric(rb,'Equity Drawdown Maximal')))
 assert len(trades)==metrics['trades'],(tag,'trade count',len(trades),metrics['trades'])
 assert abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<max(.12,.01*len(trades)),(tag,'net P&L')
 floor=datetime.strptime(start,'%Y.%m.%d').isoformat();assert all(t['open_time']>=floor for t in trades),'Warmup trades'
 lines=sorted(set(re.findall(r'PS_[^\r\n]+',journal)))
 signals=[dict(re.findall(r'(\w+)=([^ ]+)',l)) for l in lines if l.startswith('PS_SIGNAL')]
 orders=[dict(re.findall(r'(\w+)=([^ ]+)',l)) for l in lines if l.startswith('PS_ORDER')]
 assert len(orders)==len(trades),(tag,'orders versus fully closed positions')
 if vals['InpExportBars']=='true':
  for suffix in ('SIGNAL','D1'):
   data=COMMON/f'{tag}-{suffix}.bin';assert data.exists() and data.stat().st_mtime>=began-2
   (out/f'{suffix}.bin.gz').write_bytes(gzip.compress(data.read_bytes(),mtime=0))
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(out/'trades.json',trades);save(out/'signals.json',signals);save(out/'orders.json',orders)
 result=dict(ok=True,asset=asset,symbol=symbol,timeframe=tf,variant=variant,window=window,smoke=smoke,start=start,end=end,warmup_start=warm,inputs=actual,metrics=metrics,flags=flags,build=build,elapsed_seconds=time.time()-began,
  report_sha=sha(rp),deals_sha=sha(out/'deals.csv'),summary=[l for l in lines if l.startswith('PS_SUMMARY')],symbol_spec=[l for l in lines if l.startswith('PS_SPEC')],
  tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))
 save(out/'run.json',result);status('DONE '+tag,trades=len(trades),net=metrics['net_profit'],seconds=round(time.time()-began,1))
def main():
 cmd=sys.argv[1]
 if cmd=='compile':compile_ea();return
 if cmd=='smoke':
  for tf in CFG['timeframes']:
   for v in CFG['variants']:case('XAU',tf,v,'smoke',True)
 elif cmd=='grid':
  for w in (sys.argv[2:] or list(CFG['windows'])):
   for a in CFG['symbols']:
    for tf in CFG['timeframes']:
     for v in CFG['variants']:case(a,tf,v,w)
 elif cmd=='case':case(sys.argv[2],int(sys.argv[3]),sys.argv[4],sys.argv[5])
 else:raise SystemExit('compile | smoke | grid [windows] | case asset timeframe variant window')
 status('COMPLETE '+cmd)
if __name__=='__main__':main()
