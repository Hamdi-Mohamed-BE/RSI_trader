"""Frozen native comparisons in isolated MT5; never touches live charts."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;EA=ROOT/'EA'
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('video_native_helper',BASE/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
TESTER=h.TESTER;OUT=ROOT/'native';DEST=TESTER/'MQL5/Experts/AAA Research/VideoMatch20261003';COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
SOURCE=EA/'VideoMatch.mq5';ORIGINAL=BASE/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5'
SET=BASE/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
WINDOWS={'available':('2019.08.01','2026.10.02'),'5y':('2021.10.02','2026.10.02'),'1y':('2025.10.02','2026.10.02'),'3m':('2026.07.02','2026.10.02')}
VARIANTS={
 'CURRENT':dict(body=0,di=True,trail='ATR'),
 'EMA_ONLY':dict(body=0,di=False,trail='ATR'),
 'VIDEO_ATR':dict(body=1,di=False,trail='ATR'),
 'VIDEO_ATR_DI':dict(body=1,di=True,trail='ATR'),
 'SYMMETRIC_ATR':dict(body=2,di=False,trail='ATR'),
 'VIDEO_MA':dict(body=1,di=False,trail='EMA200')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def status(msg):save(ROOT/'status.json',{'utc':datetime.now(timezone.utc).isoformat(),'message':msg});print(msg,flush=True)
def values(variant,tag,research):
 v={}
 for l in SET.read_text().splitlines():
  if '=' in l and not l.startswith(';'):k,x=l.split('=',1);v[k]=x
 v.update(InpRiskPercent='1.0',InpAdaptivePortfolioControls='false',InpCloseAtSessionEnd='false',InpMaximumHoldingMinutes='0',InpUseFixedTarget='false',InpUseDynamicTrailingSL='false',InpUseBreakEven='false',InpUseMarkovRegimeFilter='false')
 s=VARIANTS[variant];v['InpRequireDIAgreement']=str(s['di']).lower()
 v['InpUseATRTrailing']=str(s['trail']=='ATR').lower();v['InpUseMATrailing']=str(s['trail']=='EMA200').lower()
 if research:v.update(InpCandleDirectionRule=str(s['body']),InpStudyTag=tag)
 if s['trail']=='EMA200':v.update(InpTrailMAPeriod='200',InpTrailMAMethod='1',InpTrailMAStartR='0.50')
 return v
def compile_ea():
 if (ROOT/'BUILD.json').exists():
  b=load(ROOT/'BUILD.json');assert b['source_sha256']==sha(SOURCE) and b['binary_sha256']==sha(SOURCE.with_suffix('.ex5')) and b['original_binary_sha256']==sha(ORIGINAL)
  assert b['helpers']=={p.name:sha(p) for p in EA.glob('*.mqh')}
  DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'VideoMatch.ex5');shutil.copy2(ORIGINAL,DEST/'Original.ex5')
  status('Retained verified build; no strategy changes');return
 h.free();log=ROOT/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-1600:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),DEST/'VideoMatch.ex5');shutil.copy2(ORIGINAL,DEST/'Original.ex5')
 save(ROOT/'BUILD.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')),original_binary_sha256=sha(ORIGINAL),set_sha256=sha(SET),protocol_sha256=sha(ROOT/'PROTOCOL.txt'),helpers={p.name:sha(p) for p in EA.glob('*.mqh')},compile_tail=h.text(log)[-500:]))
 status('Compile: 0 errors, 0 warnings; research-only guard active')
def streaks(v):
 groups=[];sign=None;n=0
 for x in v:
  sg=int(np.sign(x))
  if sg==sign:n+=1
  else:
   if sign is not None:groups.append((sign,n))
   sign=sg;n=1
 if sign is not None:groups.append((sign,n))
 wins=[n for s,n in groups if s>0];losses=[n for s,n in groups if s<0]
 return dict(max_win_streak=max(wins,default=0),max_loss_streak=max(losses,default=0),avg_win_streak=float(np.mean(wins)) if wins else 0,avg_loss_streak=float(np.mean(losses)) if losses else 0)
def stats(trades,native,start,end):
 d=pd.DataFrame(trades);v=d.net_profit.to_numpy();gp=v[v>0].sum();gl=-v[v<0].sum()
 op=pd.to_datetime(d.open_time,utc=True);cl=pd.to_datetime(d.close_time,utc=True);nyop=op.dt.tz_convert('America/New_York');nycl=cl.dt.tz_convert('America/New_York')
 holding=(cl-op).dt.total_seconds()/3600
 cal=pd.bdate_range(start.replace('.','-'),pd.Timestamp(end.replace('.','-'))-pd.Timedelta(days=1)).strftime('%Y-%m-%d')
 daily=d.assign(date=d.close_time.str[:10]).groupby('date').net_profit.sum().reindex(cal,fill_value=0).to_numpy();sd=daily.std(ddof=1)
 months=(pd.Timestamp(end.replace('.','-'))-pd.Timestamp(start.replace('.','-'))).days/365.2425*12
 balance=np.r_[10000,10000+np.cumsum(v)];peak=np.maximum.accumulate(balance)
 longs=d.side=='Long';shorts=~longs
 breakdown={}
 for name,m in [('long',longs),('short',shorts)]:
  a=v[m];g=a[a>0].sum();l=-a[a<0].sum();breakdown[name]=dict(trades=len(a),net=float(a.sum()),win_pct=float((a>0).mean()*100) if len(a) else None,pf=float(g/l) if l else None)
 return dict(return_pct=float(v.sum()/100),net=float(v.sum()),pf=float(gp/gl) if gl else None,win_pct=float((v>0).mean()*100),equity_dd_pct=native['equity_dd_pct'],closed_dd_pct=float(np.max((peak-balance)/peak)*100),trades=len(d),trades_month=len(d)/months,trades_weekday=len(d)/len(cal),daily_cash_sharpe=float(daily.mean()/sd*np.sqrt(252)) if sd else None,commission=float(d.commission.sum()),swap=float(d.swap.sum()),gross=float(d.gross_profit.sum()),avg_hold_hours=float(holding.mean()),max_hold_hours=float(holding.max()),overnight_positions=int((nyop.dt.date!=nycl.dt.date).sum()),weekend_positions=int(np.sum([(pd.date_range(a.date(),b.date()).dayofweek>=5).any() for a,b in zip(nyop,nycl)])),history_quality=native['history_quality'],**streaks(v),**breakdown)
def case(variant,window,research=True,diagnostic=False):
 key=('parity-copy' if diagnostic and research else 'parity-original' if diagnostic else variant)+'-'+window;folder=OUT/key
 start,end=WINDOWS[window];tag=key;inputs=values(variant,tag,research);expert='VideoMatch' if research else 'Original'
 manifest=dict(key=key,variant=variant,parameters=VARIANTS[variant],window=window,start=start,end=end,model=4,delay_ms=150,deposit=10000,risk_percent=1,expert=expert,source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')) if research else sha(ORIGINAL),protocol_sha256=sha(ROOT/'PROTOCOL.txt'),inputs=inputs)
 folder.mkdir(parents=True,exist_ok=True);mp=folder/'manifest.json'
 if mp.exists():assert load(mp)==manifest,'Frozen inputs changed: '+key
 else:save(mp,manifest)
 if (folder/'results.json').exists():return load(folder/'results.json')
 h.free();setname='vm-'+key+'.set';body='\n'.join(f'{k}={v}' for k,v in inputs.items())+'\n';(folder/setname).write_text(body);(TESTER/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=h.text(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 rp=TESTER/'reports/video-match20261003'/('vm-'+key+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\VideoMatch20261003\\{expert}
ExpertParameters={setname}
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\video-match20261003\\vm-{key}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+key)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(ROOT/'owned-process.json',dict(pid=proc.pid,executable=str(TESTER/'terminal64.exe'),key=key))
 try:proc.wait(timeout=3600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only owned isolated case timed out: '+key)
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report: '+key
 loglines=journal.splitlines()
 fatal_re=re.compile(r'initialization failed|start time changed|invalid volume|stop out|margin call|access violation|array out of range|zero divide|order rejected',re.I)
 fatal=[l for l in loglines if fatal_re.search(l)]
 assert not fatal,'Case failure; inspect ignored journal: '+key
 report=h._read_report(rp);assert all(x in report for x in ('USTEC',start,end,'M5'))
 actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(str(v),actual[k]) for k,v in inputs.items()),'Input mismatch: '+key
 from app.mt5_evidence_jobs import _metric,_number
 native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
 trades=h._native_trades(rp,key);assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.12
 if research:
  p=COMMON/f'VideoMatch20261003-{tag}-signals.csv';assert p.exists() and p.stat().st_mtime>=began-2
  b=p.read_bytes();audit=pd.read_csv(io.BytesIO(b));filled=audit[audit.retcode==10009]
  assert len(filled)==len(trades),'Signal/deal count mismatch: '+key
  assert (audit.retcode==10009).all(),'Entry attempts failed: '+key
  assert (filled.fill_epoch-filled.signal_epoch>=300).all()
  assert ((filled.direction>0)&(filled.signal_close>filled.ema12)|(filled.direction<0)&(filled.signal_close<filled.ema12)).all()
  if VARIANTS[variant]['body']>=1:assert (filled.loc[filled.direction>0,'signal_close']>filled.loc[filled.direction>0,'signal_open']).all()
  if VARIANTS[variant]['body']==2:assert (filled.loc[filled.direction<0,'signal_close']<filled.loc[filled.direction<0,'signal_open']).all()
  if VARIANTS[variant]['di']:assert ((filled.direction>0)&(filled.plus_di>filled.minus_di)|(filled.direction<0)&(filled.minus_di>filled.plus_di)).all()
  (folder/'signals.csv.gz').write_bytes(gzip.compress(b,mtime=0))
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));(folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
 st=stats(trades,native,start,end)
 tick_re=re.compile(r'real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded',re.I)
 result=dict(manifest=manifest,stats=st,native=native,seconds=time.time()-began,report_sha256=sha(rp),known_stop_modify_rejections=journal.count('stop modification failed'),tick_notes=sorted(set(l for l in loglines if tick_re.search(l)))[:15])
 save(folder/'results.json',result);status('DONE '+key+' '+json.dumps(st));return result
def parity():
 a=case('CURRENT','1y',research=False,diagnostic=True);b=case('CURRENT','1y',research=True,diagnostic=True)
 def ledger(key):return json.loads(gzip.decompress((OUT/key/'trades.json.gz').read_bytes()))
 fields=['open_time','close_time','side','volume','open_price','close_price','commission','swap','net_profit']
 x=ledger(a['manifest']['key']);y=ledger(b['manifest']['key']);assert len(x)==len(y)
 assert all(all(i[k]==j[k] for k in fields) for i,j in zip(x,y)),'Default-off research parity failed'
 save(ROOT/'PARITY.json',dict(trades=len(x),identical_entry_exit_volume_costs=True,production_net=a['stats']['net'],research_net=b['stats']['net'],fields=fields));status('PARITY PASSED: '+str(len(x))+' identical trades')
def main():
 history=load(ROOT/'HISTORY.json');assert any('2019.07.16' in x for x in history['notes'])
 frozen=dict(variants=VARIANTS,windows=WINDOWS,requested_years=9,actual_longest_start='2019.08.01',baseline_set_sha256=sha(SET),baseline_ex5_sha256=sha(ORIGINAL),protocol_sha256=sha(ROOT/'PROTOCOL.txt'),tested_configurations=6)
 frozen=json.loads(json.dumps(frozen))
 config=ROOT/'run-config.json'
 if config.exists():assert load(config)==frozen
 else:save(config,frozen)
 compile_ea();parity();results=[]
 for window in WINDOWS:
  for variant in VARIANTS:
   results.append(case(variant,window));save(ROOT/'PROGRESS.json',results)
 save(ROOT/'SUMMARY.json',results);status('DONE all 24 frozen comparisons; no deployment')
if __name__=='__main__':main()
