"""Bounded, serial native comparison. Never initializes or changes live MT5."""
from pathlib import Path
from datetime import datetime
import os,sys,json,re,gzip,subprocess,time,msvcrt,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;TESTER=BASE/'_Backtests/MT5-DMC-20260811'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_metric,_number,_read_report,_same_setting,_clean
WINDOWS={'dev':('2021.09.27','2024.09.27'),'val':('2024.09.27','2025.09.27'),'1y':('2025.09.27','2026.09.27'),'6m':('2026.03.27','2026.09.27')}
VARIANTS={
 'baseline':{},'di':{'ResearchDI':True},'adx20':{'ResearchADXMinimum':20},'adx25':{'ResearchADXMinimum':25},
 'adx20-di':{'ResearchADXMinimum':20,'ResearchDI':True},'adx25-di':{'ResearchADXMinimum':25,'ResearchDI':True},
 'adx20-di-rising':{'ResearchADXMinimum':20,'ResearchDI':True,'ResearchADXRising':True},
 'exit24h':{'ResearchExitCooldownHours':24},'fresh-signal':{'ResearchFreshSignal':True},
 'adx20-di-exit24h':{'ResearchADXMinimum':20,'ResearchDI':True,'ResearchExitCooldownHours':24},
 'adx20-di-fresh':{'ResearchADXMinimum':20,'ResearchDI':True,'ResearchFreshSignal':True}}
BASE_INPUTS=dict(InpSignalTimeframe=16388,InpHorizonMode=3,InpTrendMode=1,InpAllowLong=True,InpAllowShort=True,InpSessionMinuteUTC=-1,InpStopMode=0,InpStopATR=1.5,InpExitMode=1,InpRewardRisk=6,InpMaximumHoldDays=0,InpManagement=0,InpRiskPercent=1,InpMaximumDeviationPoints=100,InpMagic=969060311,InpTesterOnly=True)
FILTER_DEFAULTS=dict(ResearchADXMinimum=0,ResearchDI=False,ResearchADXRising=False,ResearchExitCooldownHours=0,ResearchFreshSignal=False)
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(s,**kw):print(s,json.dumps(kw),flush=True);save(ROOT/'status.json',dict(message=s,**kw))
def free():
 p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert p.returncode==0 and str(TESTER).lower() not in p.stdout.lower(),'Isolated tester busy; no process stopped'
 net=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(':3000 ' in l and 'LISTENING' in l for l in net.splitlines()),'Tester port busy'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def case(variant,window,model=1,installed=False):
 tag=f'{variant}-{window}-m{model}'+('-installed' if installed else '')
 out=ROOT/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=json.loads((ROOT/'BUILD.json').read_text());assert all(sha(Path(p))==h for p,h in build.items()),'Frozen source changed'
 if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
 expert='InstalledBaseline' if installed else 'SlowFilter'
 params=BASE_INPUTS.copy()
 if not installed:params.update(InpAdaptivePortfolioControls=False,**(FILTER_DEFAULTS|VARIANTS[variant]))
 body='\n'.join(f'{k}={str(v).lower() if isinstance(v,bool) else v}' for k,v in params.items())+'\n'
 setname='slowfilter-'+tag+'.set';(out/setname).write_text(body);(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body)
 start,end=WINDOWS[window]
 header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\SlowFilter20260929\\{expert}
ExpertParameters={setname}
Symbol=XAUUSD
Period=H4
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\slow-filter-20260929\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=TESTER/'reports/slow-filter-20260929'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 for attempt in range(36):
  try:free();break
  except AssertionError:
   if attempt==35:raise
   time.sleep(5)
 offsets={p:p.stat().st_size for p in logs()};began=time.time();status('START',case=tag)
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=1800)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15);raise RuntimeError('Owned research test timed out')
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report'
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 text=_read_report(rp)
 actual={}
 for raw in re.findall(r'<b>((?:Inp|Research)[^<]+)</b>',text):
  cleaned=_clean(raw).replace('\n','').replace('\r','');k,v=cleaned.split('=',1);actual[k]=v
 assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in params.items()),[(k,v,actual.get(k)) for k,v in params.items() if k not in actual or not _same_setting(str(v),actual[k])]
 assert _metric(text,'Expert')==expert and _metric(text,'Symbol')=='XAUUSD'
 assert start in _metric(text,'Period') and end in _metric(text,'Period')
 assert 'testing with execution delay 150 milliseconds' in journal
 fatal=re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|not enough history|testing start time changed|tester agent authorization error)[^\r\n]*',journal,re.I)
 assert not fatal, 'Tester error: '+str(fatal[:2])
 trades=_native_trades(rp,variant);save(out/'trades.json',trades)
 m=_native_metrics(rp);m['equity_dd_pct']=_number(_metric(text,'Equity Drawdown Relative'))
 pnls=[float(t['net_profit']) for t in trades]
 assert len(trades)==m['trades'] and abs(sum(pnls)-m['net_profit'])<.05,'Ledger/report mismatch'
 gain=sum(max(p,0) for p in pnls);loss=-sum(min(p,0) for p in pnls)
 m['profit_factor']=gain/loss if loss else None
 win=lose=maxwin=maxlose=0
 for p in pnls:
  win=win+1 if p>0 else 0;lose=lose+1 if p<0 else 0;maxwin=max(maxwin,win);maxlose=max(maxlose,lose)
 days=(datetime.strptime(end,'%Y.%m.%d')-datetime.strptime(start,'%Y.%m.%d')).days
 weekdays=int(np.busday_count(start.replace('.','-'),end.replace('.','-')))
 m.update(trades_per_month=len(trades)/(days/365.25*12),trades_per_weekday=len(trades)/weekdays,max_win_streak=maxwin,max_loss_streak=maxlose)
 flags={s:len(re.findall(s,journal,re.I)) for s in ['invalid stops','invalid volume','not enough money','stop out','market closed']}
 result=dict(case=tag,variant=variant,window=window,start=start,end=end,model=model,installed=installed,inputs=actual,metrics=m,flags=flags,seconds=round(time.time()-began,2),build=build,report_sha=sha(rp),tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))
 save(out/'result.json',result);status('DONE',case=tag,return_pct=m['return_pct'],PF=m['profit_factor'],DD=m['equity_dd_pct'],trades=m['trades']);return result
def score(row):
 m=row['metrics'];return m['return_pct']/max(m['equity_dd_pct'],1)
def parity():
 a=case('baseline','1y',1,True);b=case('baseline','1y',1)
 ta=json.loads((ROOT/'native'/a['case']/'trades.json').read_text());tb=json.loads((ROOT/'native'/b['case']/'trades.json').read_text())
 # Strip label fields only; preserve times, prices, volume and money.
 def core(ts):return [{k:v for k,v in t.items() if k not in ('ea','label','strategy','id')} for t in ts]
 ok=core(ta)==core(tb)
 save(ROOT/'PARITY.json',dict(passed=ok,installed=a['metrics'],research=b['metrics'],installed_case=a['case'],research_case=b['case'],differences=[(x,y) for x,y in zip(core(ta),core(tb)) if x!=y][:3]))
 assert ok,'Installed/source parity failed; investigate before any search'
 status('PARITY PASS',trades=len(ta))
def main():
 with (TESTER/'research-serial.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  mode=sys.argv[1]
  if mode=='parity':parity();return
  if mode=='case':case(sys.argv[2],sys.argv[3],int(sys.argv[4]));return
  assert json.loads((ROOT/'PARITY.json').read_text())['passed']
  dev=[case(v,'dev') for v in VARIANTS]
  eligible=[r for r in dev if r['variant']!='baseline' and r['metrics']['trades']>=20 and r['metrics']['return_pct']>0 and (r['metrics']['profit_factor'] or 0)>=1.15]
  finalists=sorted(eligible,key=score,reverse=True)[:3]
  selected_dev=sorted([r for r in dev if r['variant']!='baseline'],key=score,reverse=True)[0]
  val=[case('baseline','val')]+[case(r['variant'],'val') for r in finalists]
  eligible_val=[r for r in val if r['variant']!='baseline' and r['metrics']['trades']>=10 and r['metrics']['return_pct']>0 and (r['metrics']['profit_factor'] or 0)>=1.1]
  winner=max(eligible_val,key=score) if eligible_val else selected_dev
  save(ROOT/'SELECTION.json',dict(dev_eligible=[r['variant'] for r in eligible],finalists=[r['variant'] for r in finalists],validation_pass=bool(eligible_val),chosen=winner['variant'],reason='validation return/DD' if eligible_val else 'development leader only; validation failed or no eligible finalist'))
  for w in ('1y','6m'):
   for v in ('baseline',winner['variant']):case(v,w,4)
  status('COMPLETE',selected=winner['variant'],validation_pass=bool(eligible_val))
if __name__=='__main__':main()
