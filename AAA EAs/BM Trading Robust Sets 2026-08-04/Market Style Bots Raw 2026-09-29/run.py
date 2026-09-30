"""Serial, isolated native tester; no live terminal API, no production imports."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import gzip,hashlib,json,os,re,shutil,subprocess,sys,time,msvcrt
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;TESTER=BASE/'_Backtests/MT5-DMC-20260811'
DEST=TESTER/'MQL5/Experts/AAA Research/MarketStyles20260929'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxMarketStyles20260929'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
CFG=json.loads((ROOT/'run-config.json').read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v)),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(msg,**kw):save(ROOT/'status.json',dict(message=msg,**kw));print(msg,json.dumps(kw),flush=True)
def free():
 p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0 and str(TESTER).lower() not in p.stdout.lower(),'Research tester busy; nothing stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in l and 'LISTENING' in l for l in net.splitlines()),'Tester port busy'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def compile_ea():
 free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"MarketStyles.mq5"}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
 assert '0 errors, 0 warnings' in read(log),read(log)
 assert (ROOT/'MarketStyles.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'MarketStyles.ex5',DEST/'MarketStyles.ex5')
 save(ROOT/'BUILD.json',{p:sha(ROOT/p) for p in ['MarketStyles.mq5','MarketStyles.ex5','RULES.md','run-config.json']});status('Compile clean')
def case(bot,window,model,control=False,attempt=0):
 tag=f"{bot['name']}-{'control' if control else 'raw'}-{window}-m{model}";out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text());assert all(sha(ROOT/p)==h for p,h in build.items());assert sha(DEST/'MarketStyles.ex5')==build['MarketStyles.ex5']
 if (out/'run.json').exists():
  old=json.loads((out/'run.json').read_text());assert old['build']==build;return old
 start,end=CFG['smoke'] if window=='smoke' else (CFG['windows'][window],CFG['end'])
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=90)).strftime('%Y.%m.%d')
 vals=dict(InpMode=bot['mode'],InpControl=str(control).lower(),InpRiskPercent=CFG['risk_percent'],InpRR=bot['rr'],InpSeed=CFG['seed'],InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9294400)
 body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n';setname='ms-'+tag+'.set'
 (out/setname).write_text(body,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\MarketStyles20260929\\MarketStyles
ExpertParameters={setname}
Symbol={bot['symbol']}
Period=M1
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\market-styles-20260929\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/market-styles-20260929'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
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
 assert rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report '+tag
 (out/f'report-attempt{attempt}.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 actual=_report_inputs(rp)
 if not actual and 'tester agent authorization error' in journal and attempt<2:return case(bot,window,model,control,attempt+1)
 expected=vals|dict(InpTradeFrom=int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()))
 assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items()),'Report input mismatch '+tag
 rb=_read_report(rp);assert all(x in rb for x in [bot['symbol'],warm,end,'MarketStyles'])
 assert 'testing with execution delay 150 milliseconds' in journal
 fatal=re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|testing start time changed|not enough history)[^\r\n]*',journal,re.I);assert not fatal,fatal[:3]
 for suffix in ['trades.csv','signals.csv','trace.csv']:
  src=COMMON/f'{tag}-{suffix}';assert src.exists() and src.stat().st_mtime>=began-2
  (out/(suffix+'.gz')).write_bytes(gzip.compress(src.read_bytes(),mtime=0))
 d=pd.read_csv(out/'trades.csv.gz');metrics=_native_metrics(rp)
 metrics['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 assert ((d.volume-d.closed_volume).abs()<1e-8).all()
 assert abs(d.net_profit.sum()-metrics['net_profit'])<.02,'Deal/report cash mismatch'
 assert (d.open_epoch>=expected['InpTradeFrom']).all()
 assert (d.actual_risk>0).all()
 p=d.net_profit.to_numpy();gp=sum(max(x,0) for x in p);gl=-sum(min(x,0) for x in p)
 metrics.update(trades=len(p),net_profit=float(sum(p)),profit_factor=float(gp/gl) if gl else None,mean_trade=float(p.mean()) if len(p) else None,mean_net_R=float((d.net_profit/d.actual_risk).mean()) if len(p) else None,return_pct=float(sum(p)/CFG['deposit']*100),win_rate_pct=float(100*(p>0).mean()) if len(p) else 0)
 flags=dict(entry_fail=len(re.findall('MS_ENTRY_FAIL',journal)),close_fail=len(re.findall('MS_CLOSE_FAIL',journal)),invalid_volume=len(re.findall('invalid volume',journal,re.I)),invalid_stops=len(re.findall('invalid stops',journal,re.I)),stopout=len(re.findall('stop out|margin call',journal,re.I)),overnight_positions=int((d.close_epoch//86400>d.open_epoch//86400).sum()),swap_positions=int((d.swap!=0).sum()))
 outdata=dict(tag=tag,bot=bot,control=control,window=window,model=model,start=start,end=end,build=build,inputs=actual,metrics=metrics,flags=flags,seconds=round(time.time()-began,2),tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))),summaries=sorted(set(re.findall(r'MS_SUMMARY[^\r\n]*',journal))),spec=sorted(set(re.findall(r'MS_SPEC[^\r\n]*',journal))),report_sha=sha(rp),attempt=attempt)
 save(out/'run.json',outdata);status('DONE '+tag,n=len(p),PF=round(metrics['profit_factor'],3) if metrics['profit_factor'] is not None else None,net=round(metrics['net_profit'],2),flags=flags);return outdata
def gates():
 rows=[]
 for b in CFG['bots']:
  windows=[]
  for w in ['3y','5y']:
   a=json.loads((ROOT/'native'/f"{b['name']}-raw-{w}-m1/run.json").read_text());c=json.loads((ROOT/'native'/f"{b['name']}-control-{w}-m1/run.json").read_text());m=a['metrics'];cm=c['metrics']
   ok=bool(m['net_profit']>0 and (m['profit_factor'] or 0)>=1.15 and m['trades']>=30 and (m['mean_net_R'] or -999)>(cm['mean_net_R'] or -999) and not any(a['flags'].values()) and not any(c['flags'].values()))
   windows.append(dict(window=w,passed=ok,raw_metrics=m,control_metrics=cm,raw_flags=a['flags'],control_flags=c['flags']))
  rows.append(dict(bot=b,screen_pass=all(x['passed'] for x in windows),windows=windows))
 save(ROOT/'GATES.json',rows);return rows
def main():
 mode=sys.argv[1]
 with (ROOT/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if mode=='compile':compile_ea();return
  if mode=='smoke':
   for b in CFG['bots']:
    for c in [False,True]:case(b,'smoke',4,c)
  elif mode in ['screen','recent']:
   for w in (['3y','5y'] if mode=='screen' else ['6m','1y']):
    for b in CFG['bots']:
     for c in [False,True]:case(b,w,1 if mode=='screen' else 4,c)
   if mode=='screen':gates()
  elif mode=='confirm':
   for g in gates():
    if g['screen_pass']:
     for w in ['3y','5y']:
      for c in [False,True]:case(g['bot'],w,4,c)
  elif mode=='case':case(next(b for b in CFG['bots'] if b['name']==sys.argv[2]),sys.argv[3],int(sys.argv[4]),sys.argv[5]=='control')
  else:raise ValueError(mode)
 status('COMPLETE '+mode)
if __name__=='__main__':main()
