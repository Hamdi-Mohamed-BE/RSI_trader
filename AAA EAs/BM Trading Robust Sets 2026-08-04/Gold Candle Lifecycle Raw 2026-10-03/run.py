"""Isolated raw native tests and no-order price export. No live terminal API."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent;EA=R/'EA';OUT=R/'native'
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('lifecycle_native_helpers',B/'ADX DI Five Bot Review 2026-10-03/run.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v);h=v.h;T=h.TESTER
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files';DEST=T/'MQL5/Experts/AAA Research/GoldLifecycle20261003'
START='2025.10.03';END='2026.10.03';TFS={'H1':16385,'H4':16388,'D1':16408}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,z):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(z,indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def status(s):save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s));print(s,flush=True)
def compile_all():
 h.free();DEST.mkdir(parents=True,exist_ok=True);build={}
 for name in ('Lifecycle','Export'):
  src=EA/(name+'.mq5');log=EA/(name+'.compile.log');began=time.time()
  subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
  assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-2500:]
  assert src.with_suffix('.ex5').stat().st_mtime>=began-2
  shutil.copy2(src.with_suffix('.ex5'),DEST/(name+'.ex5'));build[name]=dict(source=sha(src),binary=sha(src.with_suffix('.ex5')),compile_tail=h.text(log)[-350:])
 save(R/'BUILD.json',build);status('COMPILED two tester-only EAs: 0 errors, 0 warnings')
def launch(tag,expert,inputs,start,end,model):
 folder=OUT/tag;folder.mkdir(parents=True,exist_ok=True)
 frozen=dict(tag=tag,expert=expert,inputs=inputs,start=start,end=end,model=model,delay_ms=150,deposit=10000,symbol='XAUUSD',period='M1',protocol_sha=sha(R/'PROTOCOL.txt'),build=load(R/'BUILD.json')[expert])
 if (folder/'manifest.json').exists():assert load(folder/'manifest.json')==frozen,'Frozen manifest differs'
 else:save(folder/'manifest.json',frozen)
 if (folder/'result.json').exists():return load(folder/'result.json')
 h.free();setname='lifecycle-'+tag+'.set';body='\n'.join(f'{k}={x}' for k,x in inputs.items())+'\n'
 (folder/setname).write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 rp=T/'reports/gold-lifecycle20261003'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldLifecycle20261003\\{expert}
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\gold-lifecycle20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+tag)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(R/'owned-process.json',dict(pid=proc.pid,key=tag,executable=str(T/'terminal64.exe')))
 try:proc.wait(timeout=1200)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated test timed out '+tag)
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh successful report '+tag
 lines=journal.splitlines();fatal_re=re.compile(r'initialization failed|start time changed|access violation|array out of range|zero divide',re.I)
 assert not any(fatal_re.search(l) for l in lines),'Invalid run; inspect journal '+tag
 failure_codes=[int(m.group(1)) for l in lines if (m:=re.search(r'LIFECYCLE_(?:ENTRY|CLOSE)_FAILURE (\d+)',l))]
 assert all(x in (10016,10018,10019) for x in failure_codes),'Unexpected order failure '+tag
 rb=h._read_report(rp);assert all(x in rb for x in ('XAUUSD','M1',start,end))
 actual=h._report_inputs(rp)
 for k,x in inputs.items():
  expected=x
  if k in ('InpTradeFrom','InpFrom','InpTo'):expected=int(pd.Timestamp(x.replace('.','-'),tz='UTC').timestamp())
  assert k in actual and h._same_setting(str(expected),actual[k]),(tag,k,actual.get(k))
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 if expert=='Export':
  assert 'LIFECYCLE_EXPORT_OK' in journal
  files=[]
  for tf in ('M1','H1','H4','D1','spec'):
   p=COMMON/f'GoldLifecycle20261003-{tf}.csv';assert p.exists() and p.stat().st_mtime>=began-2
   raw=p.read_bytes();out=R/'data'/(tf+'.csv.gz');out.parent.mkdir(exist_ok=True);out.write_bytes(gzip.compress(raw,mtime=0));files.append(dict(name=out.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
  result=dict(tag=tag,export=True,files=files,seconds=time.time()-began,notes=[l for l in lines if 'LIFECYCLE_EXPORT ' in l]);save(folder/'result.json',result);status('DONE no-order price export');return result
 from app.mt5_evidence_jobs import _metric,_number
 native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 trades=h._native_trades(rp,tag);assert len(trades)==native['trades'];assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.2
 p=COMMON/f'GoldLifecycle20261003-{tag}.csv';assert p.exists() and p.stat().st_mtime>=began-2
 raw=p.read_bytes();audit=pd.read_csv(io.BytesIO(raw));attempts=audit[audit.event=='entry'];entries=attempts[attempts.retcode==10009];exits=audit[audit.event=='exit']
 assert len(entries)==len(trades) and attempts.retcode.isin([10009,10016,10018,10019]).all() and exits.retcode.isin([10009,10018]).all(),('Unexpected execution failure',tag)
 assert (entries.prior_close<entries.prior_open).all()
 assert (entries.epoch>=entries.signal_epoch+60).all() and (entries.signal_epoch>=entries.midpoint).all()
 assert (entries.epoch<entries.end_epoch).all() and (entries.observed_until==entries.signal_epoch).all()
 assert (entries.stop>entries.decision_ask).all() and (entries.actual_risk>0).all()
 assert not entries.parent_epoch.duplicated().any()
 if not inputs['InpControl']=='true':
  ticksize=pd.read_csv(R/'data/spec.csv.gz').tick_size.iloc[0]
  assert (entries.first_high>=entries.parent_open+ticksize*.5-1e-7).all()
  assert (entries.signal_close<entries.parent_open).all() and (entries.decision_bid<entries.parent_open).all()
 close=pd.to_datetime([t['close_time'] for t in trades],utc=True).to_numpy(dtype='datetime64[ns]').astype('int64')/1e9
 late=np.maximum(0,close-entries.end_epoch.to_numpy())
 v.START=start;v.END=end;st=v.stats(trades,native)
 (folder/'audit.csv.gz').write_bytes(gzip.compress(raw,mtime=0));(folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
 tick_re=re.compile(r'real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded',re.I)
 result=dict(tag=tag,timeframe=next(k for k,x in TFS.items() if str(x)==inputs['InpParentTF']),control=inputs['InpControl']=='true',stats=st,native=native,seconds=time.time()-began,audit=dict(entries=len(entries),entry_attempts=len(attempts),market_closed_entries=int((attempts.retcode==10018).sum()),invalid_stop_entries=int((attempts.retcode==10016).sum()),insufficient_funds_entries=int((attempts.retcode==10019).sum()),time_exit_events=len(exits),market_closed_exit_retries=int((exits.retcode==10018).sum()),late_exits_over_60s=int((late>60).sum()),max_exit_delay_hours=float(late.max()/3600) if len(late) else 0,max_actual_vs_selected_risk_ratio=float((entries.actual_risk/entries.requested_risk).max()) if len(entries) else None),tick_notes=sorted(set(l for l in lines if tick_re.search(l)))[:15],stopout_or_margin_flags=sum(bool(re.search(r'stop out|margin call',l,re.I)) for l in lines),report_sha=sha(rp))
 save(folder/'result.json',result);status('DONE '+tag+' '+json.dumps(st));return result
def trade(tf,control=False,start=START,end=END,tag=None):
 tag=tag or tf+('-control' if control else '-model')
 return launch(tag,'Lifecycle',dict(InpParentTF=str(TFS[tf]),InpControl=str(control).lower(),InpRiskPercent='1.0',InpTag=tag,InpMagic='100303710',InpTradeFrom=start+' 00:00:00'),start,end,4)
def main():
 frozen=dict(start=START,end=END,timeframes=TFS,configurations=6,source=sha(EA/'Lifecycle.mq5'),collector=sha(EA/'Export.mq5'),protocol=sha(R/'PROTOCOL.txt'))
 if (R/'run-config.json').exists():assert load(R/'run-config.json')==frozen
 else:save(R/'run-config.json',frozen)
 if not (R/'BUILD.json').exists():compile_all()
 else:
  build=load(R/'BUILD.json')
  for name in ('Lifecycle','Export'):assert sha(EA/(name+'.mq5'))==build[name]['source'] and sha(EA/(name+'.ex5'))==build[name]['binary']
 launch('export','Export',dict(InpFrom='2025.09.25 00:00:00',InpTo=END+' 00:00:00'),'2025.09.25',END,1)
 smoke=trade('H1',start='2026.09.21',end='2026.09.28',tag='smoke-H1');assert smoke['stats']['trades']>0
 rows=[]
 for tf in TFS:
  for control in (False,True):rows.append(trade(tf,control));save(R/'PROGRESS.json',rows)
 save(R/'SUMMARY.json',rows);status('COMPLETE six raw cases; no optimisation or live changes')
if __name__=='__main__':main()
