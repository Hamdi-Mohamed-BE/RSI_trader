"""Exclusive isolated tester runs, resumable evidence; no live-terminal API."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import gzip,hashlib,json,os,re,shutil,subprocess,sys,time,msvcrt
import pandas as pd
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;TESTER=BASE/'_Backtests/MT5-DMC-20260811'
DEST=TESTER/'MQL5/Experts/AAA Research/GoldClock20260929';COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGoldClock20260929'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False,default=str),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(msg,**kw):save(ROOT/'status.json',dict(message=msg,**kw));print(msg,json.dumps(kw),flush=True)
def free():
 out=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert out.returncode==0 and str(TESTER).lower() not in out.stdout.lower(),'Research terminal busy; nothing stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in x and 'LISTENING' in x for x in net.splitlines()),'Tester port busy'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def compile_ea():
 free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"GoldClock.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log);assert (ROOT/'GoldClock.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'GoldClock.ex5',DEST/'GoldClock.ex5')
 save(ROOT/'BUILD.json',{p:sha(ROOT/p) for p in ['GoldClock.mq5','GoldClock.ex5','PROTOCOL.md','run-config.json']});status('Compile clean')
def case(name,window,model,attempt=0):
 tag=f'{name}-{window}-m{model}';out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text());assert all(sha(ROOT/p)==h for p,h in build.items());assert sha(DEST/'GoldClock.ex5')==build['GoldClock.ex5']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['build']==build;return old
 start,end=CFG['smoke'] if window=='smoke' else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=7)).strftime('%Y.%m.%d')
 vals=dict(InpControl=str(name=='control').lower(),InpLots=.1,InpEntryMinute=1380,InpHoldMinutes=120,InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9292300)
 body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n';setname='gc-'+tag+'.set'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldClock20260929\\GoldClock
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\gold-clock-20260929\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/gold-clock-20260929'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 for a in range(120):
  try:free();break
  except AssertionError:
   if a==119:raise
   time.sleep(5)
 offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15);raise RuntimeError('Owned research test timeout')
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
 (out/f'journal-attempt{attempt}.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report for '+tag
 (out/f'report-attempt{attempt}.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 actual=_report_inputs(rp)
 if not actual and 'tester agent authorization error' in journal and attempt<2:return case(name,window,model,attempt+1)
 expected=vals|dict(InpTradeFrom=int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()))
 assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items()),'Report input mismatch '+tag
 rb=_read_report(rp);assert all(x in rb for x in ['XAUUSD',warm,end,'GoldClock'])
 assert 'testing with execution delay 150 milliseconds' in journal
 fatal=re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|testing start time changed|not enough history)[^\r\n]*',journal,re.I);assert not fatal,fatal[:3]
 for suffix in ['trades.csv','trace.csv']:
  src=COMMON/f'{tag}-{suffix}';assert src.exists() and src.stat().st_mtime>=began-2
  (out/(suffix+'.gz')).write_bytes(gzip.compress(src.read_bytes(),mtime=0))
 trades=pd.read_csv(out/'trades.csv.gz');metrics=_native_metrics(rp);metrics['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 assert len(trades)>0 and ((trades.volume-trades.closed_volume).abs()<1e-8).all()
 assert abs(trades.net_profit.sum()-metrics['net_profit'])<.02,'Deal/report cash mismatch'
 assert (trades.open_epoch>=expected['InpTradeFrom']).all()
 p=trades.net_profit.to_numpy();gp=sum(max(x,0) for x in p);gl=-sum(min(x,0) for x in p)
 metrics.update(trades=len(p),net_profit=float(sum(p)),profit_factor=gp/gl if gl else 999,mean_trade=float(p.mean()),return_pct=float(sum(p)/100),win_rate_pct=float(100*(p>0).mean()))
 flags=dict(entry_fail=len(re.findall('GC_ENTRY_FAIL',journal)),close_fail=len(re.findall('GC_CLOSE_FAIL',journal)),invalid_volume=len(re.findall('invalid volume',journal,re.I)),invalid_stops=len(re.findall('invalid stops',journal,re.I)),stopout=len(re.findall('stop out|margin call',journal,re.I)))
 outdata=dict(tag=tag,variant=name,window=window,model=model,start=start,end=end,build=build,inputs=actual,metrics=metrics,flags=flags,seconds=round(time.time()-began,2),tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))),summaries=sorted(set(re.findall(r'GC_SUMMARY[^\r\n]*',journal))),report_sha=sha(rp))
 save(out/'run.json',outdata);status('DONE '+tag,n=len(p),PF=round(metrics['profit_factor'],3),net=round(metrics['net_profit'],2),flags=flags);return outdata
def main():
 mode=sys.argv[1]
 if mode=='compile':compile_ea();return
 with (ROOT/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if mode=='smoke':case('raw','smoke',4);case('control','smoke',4)
  elif mode=='screen':
   rows=[case(n,w,1) for w in ['3y','5y'] for n in ['raw','control']];passed=True;reasons=[]
   for w in ['3y','5y']:
    a=next(x for x in rows if x['window']==w and x['variant']=='raw');b=next(x for x in rows if x['window']==w and x['variant']=='control');v=a['metrics']
    ok=bool(v['net_profit']>0 and v['profit_factor']>=1.15 and v['trades']>=30 and v['mean_trade']>b['metrics']['mean_trade'] and not any(a['flags'].values()) and not any(b['flags'].values()))
    passed=bool(passed and ok)
    if not ok:reasons.append(w+' native baseline/control/execution gate failed')
   save(ROOT/'RAW_GATE.json',dict(passed=passed,reasons=reasons,runs=rows));status('RAW_GATE',passed=passed)
  elif mode in ['recent','recent-raw']:
   for w in ['6m','1y']:
    case('raw',w,4)
    if mode=='recent':case('control',w,4)
  elif mode=='confirm':
   assert json.loads((ROOT/'RAW_GATE.json').read_text())['passed'] is True,'Raw gate failed: stop, no tuning'
   for w in ['3y','5y']:case('raw',w,4);case('control',w,4)
  else:raise ValueError(mode)
if __name__=='__main__':main()
