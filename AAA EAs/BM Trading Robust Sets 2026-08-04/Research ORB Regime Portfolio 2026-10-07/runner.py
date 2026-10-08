"""Auditable isolated native MT5 batches; never contacts an active trading API."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,math,msvcrt,os,re,shutil,subprocess,time
import xml.etree.ElementTree as ET
import numpy as np,pandas as pd
import build_engine
R=Path(__file__).resolve().parent;B=R.parent
CONFIG=json.loads((R/'config.json').read_text())
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('orb_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);T=h.TESTER
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
def safe(v):
 if isinstance(v,np.generic):v=v.item()
 if isinstance(v,float) and not math.isfinite(v):return None
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [safe(x) for x in v]
 return v
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(safe(v),indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def status(message,**kw):save(R/'status.json',dict(message=message,utc=datetime.now(timezone.utc).isoformat(),**kw));print(message,json.dumps(kw),flush=True)
def lease():
 f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);return f
def ledger(deals):
 rows=[]
 if deals.empty:return rows
 for pid,d in deals.groupby('position_id',sort=False):
  d=d.sort_values(['epoch','ticket']);a=d[d.entry==0];z=d[d.entry==1]
  assert set(d.entry).issubset({0,1}) and len(a)==1 and len(z)>=1,'Unsupported/incomplete native position'
  assert abs(a.volume.sum()-z.volume.sum())<1e-7,'Native position not fully closed'
  first=a.iloc[0];last=z.iloc[-1]
  rows.append(dict(position_id=int(pid),open_epoch=int(first.epoch),close_epoch=int(last.epoch),
   open_time=pd.Timestamp(first.epoch,unit='s').isoformat(),close_time=pd.Timestamp(last.epoch,unit='s').isoformat(),
   side='buy' if int(first.type)==0 else 'sell',volume=float(first.volume),open_price=float(first.price),
   close_price=float((z.price*z.volume).sum()/z.volume.sum()),profit=float(d.profit.sum()),commission=float(d.commission.sum()),
   swap=float(d.swap.sum()),fee=float(d.fee.sum()),net_profit=float((d.profit+d.commission+d.swap+d.fee).sum()),
   initial_sl=float(first.initial_sl),initial_tp=float(first.initial_tp),exit_reason=int(last.reason)))
 rows.sort(key=lambda x:(x['close_epoch'],x['position_id']))
 assert abs(sum(t['net_profit'] for t in rows)-float((deals.profit+deals.commission+deals.swap+deals.fee).sum()))<1e-6
 return rows
def stats(trades,start,end,native):
 p=np.array([t['net_profit'] for t in trades]);n=len(p);w=l=mw=ml=0
 for v in p:w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(mw,w);ml=max(ml,l)
 days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));daily=pd.Series(0.,index=days)
 for t in trades:daily.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
 prev=(10000+daily.cumsum()).shift(1).fillna(10000);ret=daily/prev
 yearly=[]
 for year,group in daily.groupby(daily.index.year):
  xs=[t['net_profit'] for t in trades if pd.Timestamp(t['close_time']).year==year];loss=-sum(min(v,0) for v in xs)
  yearly.append(dict(year=int(year),trades=len(xs),net=sum(xs),pf=sum(max(v,0) for v in xs)/loss if loss else None))
 loss=-sum(p[p<0]);net=sum(p)
 return dict(trades=n,net=float(net),return_pct=float(net/100),pf=float(sum(p[p>0])/loss) if loss else None,
  win_rate_pct=float(sum(p>0)/n*100) if n else 0,equity_dd=float(native['equity_dd']),balance_dd=float(native['balance_dd']),
  mt5_sharpe=float(native['mt5_sharpe']),daily_closed_balance_sharpe=float(ret.mean()/ret.std(ddof=1)*math.sqrt(365)) if ret.std(ddof=1)>0 else 0,
  max_win_streak=mw,max_loss_streak=ml,average_trade=float(net/n) if n else 0,yearly=yearly)
def xml_profits(path,count):
 ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};header=None;profits={}
 for row in ET.parse(path).getroot().findall('.//s:Row',ns):
  vals=[]
  for cell in row.findall('s:Cell',ns):
   index=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
   if index:
    while len(vals)<int(index)-1:vals.append('')
   data=cell.find('s:Data',ns);vals.append(''.join(data.itertext()) if data is not None else '')
  if 'Pass' in vals and 'InpCase' in vals:header=vals;continue
  if not header or len(header)!=len(vals):continue
  rec=dict(zip(header,vals))
  if rec.get('InpCase','').isdigit():profits[int(rec['InpCase'])]=float(rec['Profit'].replace(' ',''))
 assert sorted(profits)==list(range(count)),('Missing optimization passes',len(profits),count)
 return profits
def batch(name,cases,start,end,model=1,optimize=True,verbose=False,risk=1,delay=150,symbol='USTEC'):
 out=R/'native'/name;out.mkdir(parents=True,exist_ok=True)
 source_text=build_engine.build(cases)
 frozen=dict(name=name,cases=cases,start=start,end=end,model=model,optimize=optimize,verbose=verbose,risk=risk,delay=delay,
  symbol=symbol,deposit=10000,config_sha256=sha(R/'config.json'),engine_sha256=hashlib.sha256(source_text.encode()).hexdigest())
 manifest=out/'manifest.json'
 if manifest.exists():
  assert load(manifest)==frozen,'Frozen batch changed: '+name
  if (out/'results.json').exists():return load(out/'results.json')
 else:save(manifest,frozen)
 assert optimize or len(cases)==1
 h.free();source=out/'OrbSearch.mq5';source.write_text(source_text,encoding='utf-8');build_engine.support(out)
 log=out/'compile.log';began=time.time()
 subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log);assert '0 errors, 0 warnings' in body,body[-7000:]
 binary=source.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
 dest=T/'MQL5/Experts/AAA Research/ORBRegime20261007';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(binary,dest/'OrbSearch.ex5')
 tag='orb-'+name+'-'+digest(frozen)[:10];setname=tag+'.set'
 values=dict(InpCase=f'0||0||1||{len(cases)-1}||Y' if optimize else 0,InpTag=tag,InpVerbose=str(verbose).lower(),InpRiskPct=risk)
 text='\n'.join(f'{k}={v}' for k,v in values.items())+'\n'
 (out/'Parameters.set').write_text(text,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(text,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ext='.xml' if optimize else '.htm';rp=T/'reports/orb-regime-20261007'/(tag+ext);rp.parent.mkdir(exist_ok=True)
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ORBRegime20261007\\OrbSearch
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={delay}
Optimization={1 if optimize else 0}
OptimizationCriterion=6
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
ForwardMode=0
Report=reports\\orb-regime-20261007\\{tag+ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free()
 status('START '+name,cases=len(cases),model=model,from_date=start,end_exclusive=end)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),started=began))
 shutdown_recovered=False
 try:
  while proc.poll() is None:
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:
    elapsed=time.time()-began
    # MT5 can generate a crash dialog AFTER reporting successful tester
    # completion and exit code 0. Recover only our newly launched child,
    # only with a fresh report and explicit post-test shutdown evidence.
    if elapsed>120 and rp.exists() and rp.stat().st_mtime>=began-2:
     terminal_log=''
     for logfile in (T/'logs').glob('*.log'):
      if logfile.stat().st_mtime<began-2:continue
      with logfile.open('rb') as stream:
       stream.seek(offsets.get(logfile,0));terminal_log+=stream.read().decode('utf-16-le',errors='replace')
     if 'successfully finished' in terminal_log and 'exit with code 0' in terminal_log and 'crashlog generated' in terminal_log:
      proc.terminate();proc.wait(timeout=30);shutdown_recovered=True
      save(out/'client-shutdown-recovery.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),
       reason='Owned terminal shutdown hang after explicit successful tester completion and exit code 0',report_fresh=True,
       native_data_reconciliation_still_required=True))
      break
    if elapsed>7200:raise subprocess.TimeoutExpired(proc.args,7200)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned research tester timeout; normal MT5 untouched')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as stream:stream.seek(offsets.get(p,0));journal+=stream.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert (proc.returncode==0 or shutdown_recovered) and rp.exists() and rp.stat().st_mtime>=began-2,'Missing fresh native report'
 assert not re.search(r'initialization failed|start time changed|not enough history|access violation|array out of range|zero divide|not enough money|stop out|margin call|some error after pass finished',journal,re.I),'Native test incomplete/history/runtime/margin failure'
 (out/('report'+ext+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 profits=xml_profits(rp,len(cases)) if optimize else {0:h._native_metrics(rp)['net_profit']}
 if not optimize:
  actual=h._report_inputs(rp);assert all(h._same_setting(str(v),actual.get(k,'')) for k,v in values.items()),'Native input mismatch'
  native_html=h._read_report(rp);assert start.replace('-','.') in native_html and end.replace('-','.') in native_html
 records=[]
 for i,c in enumerate(cases):
  stem=tag+'-'+str(i);dealfile=COMMON/(stem+'-deals.csv');statfile=COMMON/(stem+'-stats.csv')
  assert dealfile.exists() and statfile.exists() and statfile.stat().st_mtime>=began-2,('Missing native pass ledger',stem)
  native=pd.read_csv(statfile).iloc[0].to_dict();deals=pd.read_csv(dealfile);trades=ledger(deals)
  assert abs(sum(t['net_profit'] for t in trades)-profits[i])<max(.051,len(trades)*.001),'Native money reconciliation failed'
  assert abs(native['net']-profits[i])<.03 and abs(native['balance']-10000-profits[i])<.03 and not native['open_position']
  assert len(trades)==int(native['trades'])
  assert all(pd.Timestamp(start).timestamp()<=t['open_epoch']<pd.Timestamp(end).timestamp() for t in trades),'Boundary leak'
  for suffix in ['deals','stats']+(['equity','quotes','decisions'] if verbose else []):
   p=COMMON/(stem+'-'+suffix+'.csv');assert p.exists() and p.stat().st_mtime>=began-2
   (out/(str(i)+'-'+suffix+'.csv.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
  m=stats(trades,start,end,native)
  records.append(dict(index=i,parameters=c,stage=name,start=start,end=end,model=model,metrics=m,native=native,
   clean=native['failed_entries']==0,stop_update_rejections_included=True,
   binary_sha256=sha(binary),report_sha256=sha(rp),trades=trades,live_changes=False,
   client_shutdown_recovered=shutdown_recovered,
   tick_notes=sorted(set(re.findall(rf'{re.escape(symbol)}\s*:\s*real ticks begin from[^\r\n]*',journal)))))
 save(out/'results.json',records);status('DONE '+name,cases=len(cases),seconds=round(time.time()-began,1));return records
def dedupe(cases):return list({digest(c):c for c in cases}.values())
def slim(row):return {k:v for k,v in row.items() if k!='trades'}


