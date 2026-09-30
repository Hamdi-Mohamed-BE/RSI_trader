"""Native staged parameter research; requires parent gate and exact raw parity."""
from pathlib import Path
import sys,json,gzip,time,subprocess,shutil,hashlib,xml.etree.ElementTree as ET,itertools
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import pipeline as p
h=p.h
FIELDS=['tf','entry','stop','stop_distance','trail','start_r','trail_distance','exit','rr','range_start','range_end','flat','direction','filter','day','max_day','reentry','max_bars','buffer','atr']
BASE=dict(zip(FIELDS,[5,0,0,2,0,1,1.5,0,2,180,360,1080,0,0,0,1,0,0,0,14]))
def save(path,obj):p.save(path,obj)
def load(path):return json.loads(path.read_text())
def status(message,**kw):print(message,kw,flush=True);save(ROOT/'status.json',dict(message=message,**kw))
def unique(cases):return list({json.dumps(c,sort_keys=True):c for c in cases}.values())
def build(cases,folder):
 p.original.free()
 table=',\n'.join('{'+','.join(str(c[f]) for f in FIELDS)+'}' for c in cases)
 src=ROOT/'Search.mq5';src.write_text('#property strict\ndouble Cases[][20]={\n'+table+'\n};\n#include "SearchLogic.mqh"\n',encoding='utf-8')
 log=ROOT/'compile.log';started=time.time()
 subprocess.run(f'"{p.TESTER/"MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 text=h.text(log);assert '0 errors, 0 warnings' in text,text[-5000:]
 assert src.with_suffix('.ex5').stat().st_mtime>=started-2
 dest=p.TESTER/'MQL5/Experts/AAA Research/Four Ideas Search 20260927';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src.with_suffix('.ex5'),dest/'Search.ex5')
 for path in (src,src.with_suffix('.ex5'),log,ROOT/'SearchLogic.mqh'):shutil.copy2(path,folder/path.name)
 return h.sha(src.with_suffix('.ex5'))
def xml_rows(path,cases):
 ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};tree=ET.parse(path);headers=None;out=[]
 for row in tree.findall('.//s:Row',ns):
  v=[]
  for cell in row.findall('s:Cell',ns):
   ix=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
   if ix:
    while len(v)<int(ix)-1:v.append('')
   d=cell.find('s:Data',ns);v.append(''.join(d.itertext()) if d is not None else '')
  if 'Pass' in v and 'InpCase' in v:headers=v;continue
  if not headers or len(v)!=len(headers):continue
  r=dict(zip(headers,v))
  if not r.get('InpCase','').isdigit():continue
  idx=int(r['InpCase']);assert 0<=idx<len(cases)
  data={}
  for k,value in r.items():
   try:data[k]=float(value.replace(' ',''))
   except ValueError:data[k]=value
  out.append(dict(index=idx,parameters=cases[idx],native=data))
 assert len(out)==len(cases) and len({r['index'] for r in out})==len(cases),(len(out),len(cases),headers)
 return out
def batch(name,cases,start='2021.09.27',end='2024.03.27',model=1,opt=True,force=False):
 folder=ROOT/'native'/name;folder.mkdir(parents=True,exist_ok=True)
 manifest=dict(cases=cases,start=start,end=end,model=model,optimization=opt,force_extended=force,logic_sha=h.sha(ROOT/'SearchLogic.mqh'),protocol_sha=h.sha(ROOT/'PROTOCOL.md'),raw_source_sha=h.sha(p.RAW/'FourIdeas.mq5'))
 if (folder/'manifest.json').exists():
  assert load(folder/'manifest.json')==manifest,'Batch changed '+name
  if (folder/'results.json').exists():return load(folder/'results.json')
 else:save(folder/'manifest.json',manifest)
 binary=build(cases,folder)
 tag='four-search-'+name;setname=tag+'.set'
 setbody=f'InpCase=0||0||1||{len(cases)-1}||'+('Y' if opt else 'N')+f'\nInpForceExtended={str(force).lower()}\nInpMode=1\nInpControl=false\nInpRiskPercent=1.0\nInpNotionalUSD=10000.0\nInpServerUtcOffsetHours=0\nInpMagic=9274040\nInpTag={tag}\n'
 (folder/setname).write_text(setbody);(p.TESTER/'MQL5/Profiles/Tester'/setname).write_text(setbody)
 template=(p.ROOT/'native/usdjpy-morning-3y-m1/tester.ini').read_text(encoding='utf-8-sig')
 overrides={'Expert':'AAA Research\\Four Ideas Search 20260927\\Search','ExpertParameters':setname,'Model':model,'Optimization':1 if opt else 0,'FromDate':start,'ToDate':end,'Report':'reports\\four-pipeline-20260927\\'+tag+('.xml' if opt else '.htm')}
 lines=[(k+'='+str(overrides[k]) if k in overrides else line) for line in template.splitlines() for k in [line.split('=')[0]]]
 lines+=['OptimizationCriterion=6','ForwardMode=0']
 ini=folder/'tester.ini';ini.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
 p.original.free();offsets={x:x.stat().st_size for x in h.logfiles()};started=time.time()
 status('START '+name,cases=len(cases),model=model)
 proc=subprocess.Popen(f'"{p.TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=p.TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:proc.wait(timeout=21600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise
 journal=''
 for path in h.logfiles():
  if path.stat().st_mtime<started-2:continue
  with path.open('rb') as file:file.seek(offsets.get(path,0));journal+='\n'+file.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 report=p.TESTER/overrides['Report'].replace('\\','/')
 assert proc.returncode==0 and report.exists() and report.stat().st_mtime>=started-2, journal[-4000:]
 fatal=[line for line in journal.splitlines() if any(w in line.lower() for w in ('initialization failed','start time changed','not enough history','critical error','access violation'))]
 assert not fatal,fatal[:10]
 (folder/('report'+report.suffix+'.gz')).write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 if opt:result=xml_rows(report,cases)
 else:
  actual=h._report_inputs(report);rb=h._read_report(report)
  assert actual.get('InpCase')=='0' and actual.get('InpForceExtended')==str(force).lower()
  assert all(v in rb for v in (start,end,'USDJPY'))
  assert 'testing with execution delay 150 milliseconds' in journal
  trades=h._native_trades(report,name);m=h._native_metrics(report)
  assert len(trades)==m['trades'] and abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<.11
  m['equity_dd_pct']=p._number(p._metric(rb,'Equity Drawdown Relative'))
  net=p.audit.shared.stats(trades,start,end)
  result=[dict(parameters=cases[0],metrics=m,net=net,report_sha=h.sha(report),binary_sha=binary)]
  save(folder/'trades.json',trades)
 save(folder/'results.json',result)
 save(folder/'run_metadata.json',dict(elapsed=time.time()-started,binary_sha=binary,report_sha=h.sha(report)))
 status('DONE '+name,cases=len(cases),seconds=round(time.time()-started,1))
 return result
def score(r):
 if 'native' in r:return r['native'].get('Result',-1000)
 n=r['net'];dd=r['metrics']['equity_dd_pct'];pf=n['profit_factor'] or 0
 return min(pf,3)*(n['trades']/100)**.5*(n['return_pct']/100)/(.05+dd/100) if n['trades']>=30 and n['net_usd']>0 and pf>1 else -1000
def patches(stage):
 if stage=='timeframe_entry':return [dict(tf=tf,entry=e) for tf,e in itertools.product([1,3,5,15,30,16385,16388],[1,2,3,4])]
 if stage=='entry':return [dict(entry=e) for e in range(5)]
 if stage=='stop':return ([dict(stop=0)]+[dict(stop=1,stop_distance=x) for x in [.5,.75,1,1.5,2,3,4]]+[dict(stop=2,stop_distance=x) for x in [100,300,600]]+[dict(stop=3,stop_distance=x) for x in [.05,.1,.2]]+[dict(stop=4),dict(stop=5)])
 if stage=='trailing':return ([dict(trail=0)]+[dict(trail=1,start_r=x) for x in [.5,1,1.5]]+[dict(trail=2,start_r=s,trail_distance=d) for s,d in itertools.product([.5,1,1.5,2],[1,1.5,2])]+[dict(trail=3,trail_distance=d) for d in [.05,.1,.2]]+[dict(trail=x) for x in [4,5,7]]+[dict(trail=6,trail_distance=d) for d in [1.5,2,3]])
 if stage=='exit':return ([dict(exit=1,rr=x) for x in [.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+[dict(exit=0,trail=2,trail_distance=d) for d in [1,1.5,2,3]]+[dict(exit=2),dict(exit=0,trail=0),dict(exit=5,rr=2,trail=2,start_r=1)])
 if stage=='session':return [dict(range_start=a,range_end=b,flat=c) for a,b,c in [(0,180,660),(180,360,1080),(420,600,1080),(600,780,1200),(780,960,1320),(900,990,1320)]]
 if stage=='direction':return [dict(direction=x) for x in [0,1,-1]]
 if stage=='filters':return [dict(filter=x) for x in range(6)]
 if stage=='management':return ([dict(day=x) for x in range(4)]+[dict(max_day=x,reentry=int(x>1)) for x in [1,2,3]]+[dict(max_bars=x) for x in [0,12,24,48]]+[dict(buffer=x) for x in [0,.1,.25]])
 if stage=='range_duration':return [dict(duration=x) for x in [120,180,240]]
 raise ValueError(stage)
def parity():
 old=load(p.RAW/'native/usdjpy-morning/trades.json')
 clean=lambda rows:[{k:v for k,v in t.items() if k!='ea'} for t in rows]
 results={}
 for name,force in [('parity-off',False),('parity-extended',True)]:
  batch(name,[BASE],start='2025.09.27',end='2026.09.27',model=4,opt=False,force=force)
  new=load(ROOT/'native'/name/'trades.json');results[name]=clean(new)==clean(old)
 save(ROOT/'PARITY.json',results);assert all(results.values()),results
def search():
 gate=load(p.ROOT/'GATE.json');assert any(x['id']=='usdjpy-morning' and x['optimization_allowed'] for x in gate['decisions'])
 assert all(load(ROOT/'PARITY.json').values())
 leaders=[BASE];ledger=[]
 for stage in ['timeframe_entry','entry','stop','trailing','exit','session','direction','filters','management','range_duration']:
  cases=list(leaders)
  for b in leaders:
   for change in patches(stage):
    if 'duration' in change:change={'range_start':b['range_end']-change['duration']}
    c=b|change
    if 0<=c['range_start']<c['range_end']<c['flat']<1440:cases.append(c)
  rows=batch(stage,unique(cases));ledger.extend([dict(stage=stage,**r) for r in rows])
  good=sorted([r for r in rows if score(r)>0],key=score,reverse=True)
  if not good:save(ROOT/'SEARCH_RESULTS.json',ledger);save(ROOT/'STOP.json',dict(reason='No eligible development candidate',stage=stage));return
  leaders=[r['parameters'] for r in good[:3]]
  save(ROOT/'SEARCH_RESULTS.json',ledger);save(ROOT/'LEADERS.json',leaders)
 plateaus=[]
 for i,b in enumerate(leaders):
  key='rr' if b['exit'] in (1,5) else 'trail_distance'
  cases=[]
  for shift,flat,step in itertools.product([-30,0,30],[-30,0,30],[-1,0,1]):
   c=b|dict(range_start=b['range_start']+shift,range_end=b['range_end']+shift,flat=b['flat']+flat)
   c[key]=max(.25,b[key]+.25*step) if key=='rr' else b[key]*(1+.2*step)
   if 0<=c['range_start']<c['range_end']<c['flat']<1440:cases.append(c)
  rows=batch('neighborhood-'+str(i),unique(cases));ledger.extend([dict(stage='neighborhood-'+str(i),**r) for r in rows])
  profitable=sum(r['native'].get('Profit',0)>0 for r in rows)/len(rows)
  median_pf=sorted(r['native'].get('Profit Factor',0) for r in rows)[len(rows)//2]
  if profitable>=2/3 and median_pf>1:plateaus.append(b)
 save(ROOT/'SEARCH_RESULTS.json',ledger);save(ROOT/'PLATEAUS.json',plateaus)
 if not plateaus:save(ROOT/'STOP.json',dict(reason='No stable neighborhood'));return
 validations=[]
 for i,b in enumerate(plateaus):
  r=batch('validation-'+str(i),[b],start='2024.03.27',end='2025.09.27',model=4,opt=False)[0]
  validations.append(r|{'index':i})
 good=sorted([r for r in validations if score(r)>0],key=score,reverse=True)
 save(ROOT/'VALIDATION.json',validations)
 if not good:save(ROOT/'STOP.json',dict(reason='All finalists failed validation'));return
 selected=good[0];save(ROOT/'SELECTED.json',selected)
 hold=batch('holdout',[selected['parameters']],start='2020.09.27',end='2021.09.27',model=4,opt=False)[0]
 confirmed=hold['net']['net_usd']>0 and (hold['net']['profit_factor'] or 0)>=1 and hold['net']['trades']>=30
 save(ROOT/'HOLDOUT_GATE.json',dict(passed=confirmed,result=hold))
 if not confirmed:save(ROOT/'STOP.json',dict(reason='Historical holdout failed; no retuning'));return
 for tag,start,end in [('retrospective-1y','2025.09.27','2026.09.27'),('development-native','2021.09.27','2024.03.27')]:batch(tag,[selected['parameters']],start=start,end=end,model=4,opt=False)
 status('Parameter search complete; Monte Carlo and FTMO gates still required')
if __name__=='__main__':
 if sys.argv[1]=='parity':parity()
 elif sys.argv[1]=='search':search()
