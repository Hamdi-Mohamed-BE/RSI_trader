"""Native optimisation over a frozen generated case table; isolated tester only."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv,gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,sys,time
import xml.etree.ElementTree as ET
import pandas as pd
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;EA=ROOT/'EA';OUT=ROOT/'native'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_report_inputs,_same_setting,_read_report,_metric,_number
spec=importlib.util.spec_from_file_location('orb_common_metrics',BASE/'Reel Three Bots Pipeline 2026-10-02/metrics.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
TESTER=BASE/'_Backtests/MT5-DMC-20260811'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/US100ORBExplore20261002'
FIELDS=['opening_minutes','rr','entry_cutoff','direction','ema','adaptive_close']
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(message,**kw):save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),message=message,**kw));print(message,json.dumps(kw),flush=True)
def free():
 cmd="Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
 r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0 and str(TESTER).lower() not in r.stdout.lower(),'Isolated tester occupied; no terminal changed'
 r=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert not any(':3000 ' in l and 'LISTENING' in l for l in r.stdout.splitlines()),'Tester agent port busy; no process touched'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def parse_xml(p,n):
 ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};headers=None;result={}
 for row in ET.parse(p).getroot().findall('.//s:Row',ns):
  vals=[]
  for cell in row.findall('s:Cell',ns):
   i=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
   if i:
    while len(vals)<int(i)-1:vals.append('')
   d=cell.find('s:Data',ns);vals.append(''.join(d.itertext()) if d is not None else '')
  if 'Pass' in vals and 'InpCase' in vals:headers=vals;continue
  if not headers or len(vals)!=len(headers):continue
  rec=dict(zip(headers,vals))
  if rec.get('InpCase','').isdigit():result[int(rec['InpCase'])]=float(rec['Profit'].replace(' ',''))
 assert sorted(result)==list(range(n)),f'Incomplete optimisation: {len(result)}/{n}'
 return result
def batch(name,cases,start,end,model=1,delay=150,warmup=90):
 optimize=len(cases)>1;folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
 frozen=dict(name=name,cases=cases,start=start,end=end,model=model,delay=delay,warmup=warmup,source_main_sha=sha(EA/'Main.mqh'),protocol_sha=sha(ROOT/'PROTOCOL.txt'),risk_percent=1,deposit=10000)
 mp=folder/'manifest.json'
 if mp.exists():
  assert load(mp)==frozen,'Frozen batch changed: '+name
  if (folder/'results.json').exists():return load(folder/'results.json')
 else:save(mp,frozen)
 free()
 table='double Cases[]['+str(len(FIELDS))+']={\n'+',\n'.join('{'+','.join(repr(float(c[f])) for f in FIELDS)+'}' for c in cases)+'\n};\n'
 src=folder/'ORBSearch.mq5'
 src.write_text('#property strict\n#property version "1.00"\n#property description "Tester-only exploratory US100 ORB (generated frozen case table)."\n'+table+'#include "Main.mqh"\n',encoding='utf-8')
 shutil.copy2(EA/'Main.mqh',folder/'Main.mqh')
 log=folder/'compile.log';began=time.time()
 subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=read(log);assert '0 errors, 0 warnings' in body,body[-1800:]
 ex5=src.with_suffix('.ex5');assert ex5.stat().st_mtime>=began-2
 dest=TESTER/'MQL5/Experts/AAA Research/US100ORBExplore20261002';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(ex5,dest/'ORBSearch.ex5')
 tag='orb-'+name+'-'+digest(frozen)[:8]
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=warmup)).strftime('%Y.%m.%d')
 vals=dict(InpCase=f'0||0||1||{len(cases)-1}||Y' if optimize else 0,InpRiskPercent=1.0,InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=10020100)
 setname=tag+'.set';setbody='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n'
 (folder/setname).write_text(setbody,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
 header=read(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ext='.xml' if optimize else '.htm';rp=TESTER/'reports/us100-orb-explore-20261002'/(tag+ext);rp.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\US100ORBExplore20261002\\ORBSearch
ExpertParameters={setname}
Symbol=USTEC
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={delay}
Optimization={1 if optimize else 0}
OptimizationCriterion=6
FromDate={warm}
ToDate={end}
ForwardMode=0
Report=reports\\us100-orb-explore-20261002\\{tag+ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in logs()};began=time.time();free();status('START '+name,cases=len(cases),model=model,window=start+' -> '+end)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(folder/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(TESTER/'terminal64.exe')))
 try:proc.wait(timeout=3600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated batch timeout: '+name)
 journal=''
 for p in logs():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh successful report; inspect local ignored journal'
 fatal=re.findall(r'[^\n]*(?:initialization failed|start time changed|not enough history|access violation|critical error|array out of range|zero divide)[^\n]*',journal,re.I)
 assert not fatal,'History/runtime failure; inspect local ignored journal'
 stopouts=len(re.findall(r'stop out|margin call',journal,re.I))
 (folder/(rp.name+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 t0=datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()
 native_metrics=None
 if optimize:profits=parse_xml(rp,len(cases))
 else:
  actual=_report_inputs(rp);expected=vals|dict(InpTradeFrom=int(t0))
  assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items()),'Frozen input mismatch'
  text=_read_report(rp);assert all(x in text for x in ('USTEC',warm,end))
  native_metrics=_native_metrics(rp);native_metrics['equity_dd_pct']=_number(_metric(text,'Equity Drawdown Relative'));profits={0:native_metrics['net_profit']}
 rows=[]
 for i,c in enumerate(cases):
  stem=f'{tag}-{i}';nj=COMMON/(stem+'-net.json');tp=COMMON/(stem+'-trades.csv')
  assert nj.exists() and tp.exists() and nj.stat().st_mtime>=began-2,'Missing fresh per-pass ledger'
  net=load(nj);d=pd.read_csv(tp)
  assert len(d)==net['trades'] and abs(d.net_profit.sum()-net['net_profit'])<.02,'Ledger totals differ'
  assert (abs(d.volume-d.closed_volume)<1e-7).all(),'Unclosed position'
  assert (d.open_epoch>=t0).all(),'Warmup entry leak'
  assert abs(net['net_profit']-profits[i])<max(.15,len(d)*.001),'Native/ledger P&L mismatch'
  assert (d.actual_risk>0).all() and (d.requested_risk>0).all(),'Missing initial risk'
  for suffix in ('net.json','trades.csv','signals.csv','trace.csv'):
   p=COMMON/f'{stem}-{suffix}'
   if p.exists() and p.stat().st_mtime>=began-2:(folder/f'{i}-{suffix}.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0))
  eqdd=native_metrics['equity_dd_pct'] if native_metrics else net['equity_dd_pct']
  st=metrics.stats(d,start,end,equity_dd=eqdd)
  clean=not any(net[k] for k in ('entry_fail','close_fail','bad_risk')) and stopouts==0
  ticknotes=sorted(set(re.findall(r'[^\n]*(?:real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded)[^\n]*',journal)))[:30]
  rows.append(dict(index=i,parameters=c,parameters_sha=digest(c),stage=name,start=start,end=end,model=model,delay=delay,stats=st,net=net,clean=clean,native_metrics=native_metrics,report_path=str(rp),source_sha=sha(src),binary_sha=sha(ex5),report_sha=sha(rp),stopouts=stopouts,tick_notes=ticknotes))
 save(folder/'results.json',rows);save(folder/'build.json',dict(source=sha(src),binary=sha(ex5),compile_tail=body[-350:]))
 status('DONE '+name,cases=len(cases),seconds=round(time.time()-began,1),stats=[r['stats'] for r in rows] if not optimize else None)
 return rows
def ledger(row):return pd.read_csv(io.BytesIO(gzip.decompress((OUT/row['stage']/f"{row['index']}-trades.csv.gz").read_bytes())))
