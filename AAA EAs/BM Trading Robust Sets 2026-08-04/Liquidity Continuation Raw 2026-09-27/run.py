"""Sequential native research only; never initialize the active terminal or a trading API."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import gzip,hashlib,json,os,re,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;TESTER=BASE/'_Backtests/MT5-DMC-20260811'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text());DEST=TESTER/'MQL5/Experts/AAA Research/Liquidity 20260927'
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(msg,**kw):save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=msg,**kw));print(msg,flush=True)
def free():
 out=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert str(TESTER).lower() not in out.stdout.lower(),'Isolated tester occupied; no other process stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in l and 'LISTENING' in l for l in net.splitlines()),'Tester agent port occupied'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def compile_ea():
 free();source=ROOT/'Liquidity.mq5';log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=read(log);assert '0 errors, 0 warnings' in body,body
 assert source.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),DEST/'Liquidity.ex5')
 save(ROOT/'BUILD.json',dict(source_sha=sha(source),binary_sha=sha(source.with_suffix('.ex5')),rules_sha=sha(ROOT/'RULES.md'),config_sha=sha(ROOT/'run-config.json'),compile=body[-400:]))
 status('Clean compile: 0 errors, 0 warnings')
def run(asset,symbol,variant,window,smoke=False):
 tag=('-'.join([asset,variant['name'],window]));tag=('smoke-' if smoke else '')+tag
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True);build=json.loads((ROOT/'BUILD.json').read_text())
 for p,k in [('Liquidity.mq5','source_sha'),('Liquidity.ex5','binary_sha'),('RULES.md','rules_sha'),('run-config.json','config_sha')]:assert sha(ROOT/p)==build[k]
 assert sha(DEST/'Liquidity.ex5')==build['binary_sha']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['ok'] and old['build']==build;return
 start,end=(CFG['smoke_start'],CFG['smoke_end']) if smoke else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=CFG['warmup_days'])).strftime('%Y.%m.%d')
 vals=dict(InpEntry=variant['entry'],InpControl=str(variant['control']).lower(),InpRiskPercent=CFG['risk_percent'],InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9278120)
 setname='lc-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 # Reuse only the pre-existing research account header, not the active terminal/account.
 common=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Liquidity 20260927\\Liquidity
ExpertParameters={setname}
Symbol={symbol}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\liquidity-20260927\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/liquidity-20260927'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(120):
  try:free();break
  except AssertionError:
   if attempt==119:raise
   time.sleep(5)
 offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:
  proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated test timed out: '+tag)
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2,('No fresh report',journal[-3500:])
 actual=_report_inputs(rp)
 expected={**vals,'InpTradeFrom':int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
 bad=[k for k,v in expected.items() if k not in actual or not _same_setting(str(v),actual[k])];assert not bad,(tag,bad,actual)
 rb=_read_report(rp);assert all(v in rb for v in (warm,end,symbol))
 assert 'testing with execution delay 150 milliseconds' in journal
 # Terminal and agent repeat messages. EA summary and audit lines deduplicated.
 lines=sorted(set(re.findall(r'LC_[^\r\n]+',journal)))
 flags={k:len(re.findall(p,journal,re.I)) for k,p in {'init_failed':r'initialization failed|INIT_FAILED','critical':r'critical error|access violation','invalid_stops':r'invalid stops','invalid_volume':r'invalid volume','market_closed':r'market closed','margin_call':r'stop out|margin call'}.items()}
 assert not any(flags[k] for k in ('init_failed','critical','invalid_volume')),flags
 trades=_native_trades(rp,tag);metrics=_native_metrics(rp)
 metrics.update(max_equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),max_balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')),max_equity_dd_usd=_number(_metric(rb,'Equity Drawdown Maximal')))
 assert len(trades)==metrics['trades'] and abs(sum(t['net_profit'] for t in trades)-metrics['net_profit'])<max(.12,.01*len(trades))
 floor=datetime.strptime(start,'%Y.%m.%d').isoformat();assert all(t['open_time']>=floor for t in trades),'Warmup trade leak'
 audits=[]
 for line in lines:
  if line.startswith('LC_LEVEL'):
   values=dict(re.findall(r'(\w+)=([^ ]+)',line));dt=int(values['donor']);now=int(values['at'])
   assert not dt or dt<now,'Future control donor'
  if line.startswith('LC_TOUCH'):
   v=dict(re.findall(r'(\w+)=([^ ]+)',line));s=1 if int(v['i'])%2==0 else -1
   assert s*(float(v['previous'])-float(v['level']))<1e-7 and s*(float(v['bid'])-float(v['level']))>=-1e-7,'Touch geometry mismatch'
  if line.startswith('LC_ORDER'):
   v=dict(re.findall(r'(\w+)=([^ ]+)',line));s=int(v['type'])
   assert s*(float(v['entry'])-float(v['sl']))>0 and s*(float(v['tp'])-float(v['entry']))>0
   audits.append(v)
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));save(out/'trades.json',trades);save(out/'order-audit.json',audits)
 result=dict(ok=True,asset=asset,symbol=symbol,variant=variant['name'],window=window,smoke=smoke,start=start,end=end,warmup_start=warm,inputs=actual,metrics=metrics,flags=flags,build=build,elapsed_seconds=time.time()-began,
  report_sha=sha(rp),summary=[l for l in lines if l.startswith('LC_SUMMARY')],symbol_spec=[l for l in lines if l.startswith('LC_SPEC')],
  tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))
 save(out/'run.json',result);status('DONE '+tag+' '+json.dumps(metrics))
def main():
 cmd=sys.argv[1]
 if cmd=='compile':compile_ea();return
 if cmd=='smoke':
  for v in CFG['models']:run('XAU','XAUUSD',v,'smoke',True)
 elif cmd=='grid':
  windows=sys.argv[2:] or list(CFG['windows'])
  for w in windows:
   for a,s in CFG['symbols'].items():
    for v in CFG['models']:run(a,s,v,w)
 elif cmd=='case':
  a,v,w=sys.argv[2:];run(a,CFG['symbols'][a],next(m for m in CFG['models'] if m['name']==v),w)
 status('COMPLETE '+cmd)
if __name__=='__main__':main()
