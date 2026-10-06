"""Isolated, leased USTEC H1 ORB research. Never connects to a live-account API."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,sys,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('asia_native_helpers',B/'Trend Progression Optimization 2026-10-05/native.py')
n=importlib.util.module_from_spec(sp);sp.loader.exec_module(n);h=n.h;T=n.T
sp=importlib.util.spec_from_file_location('asia_report_parser',B/'Gold Overnight Value Area Optimization 2026-10-05/native.py')
g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
SOURCE=R/'EA/ORB Research.mq5'
ORIGINAL=B/'ORB Volume Data EA/ORB Volume Data EA.ex5'
BASE=B/'ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxORBOptimize20261006'
WINDOWS={'1y':('2025.10.06','2026.10.06'),'6m':('2026.04.06','2026.10.06'),'3m':('2026.07.06','2026.10.06'),
 '3y':('2023.10.06','2026.10.06'),'5y':('2021.10.06','2026.10.06'),'train':('2021.10.06','2024.10.06'),'valid':('2024.10.06','2025.10.06')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def freeze():
 paths=[BASE,ORIGINAL,*ORIGINAL.parent.glob('*.mq*'),B/'_Shared/CalyxAdaptivePortfolio.mqh',B/'_Shared/CalyxORBComments.mqh',B/'_Auto Deploy/Install-BMTradingPortfolio.ps1']
 v=dict(production={str(p.relative_to(B)):sha(p) for p in paths},research={p.name:sha(p) for p in sorted((R/'EA').glob('*.mq*'))},
  protocol=sha(R/'PROTOCOL.md'),runner=sha(Path(__file__)),plan=sha(R/'plan.py'))
 if (R/'frozen.json').exists():assert read(R/'frozen.json')==v,'Frozen files changed'
 else:save(R/'frozen.json',v)
 return v
def compile_ea():
 h.free();began=time.time();log=R/'compile.log'
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log);assert '0 errors, 0 warnings' in body,body[-7000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'build.json',dict(binary=sha(SOURCE.with_suffix('.ex5')),frozen=freeze(),compiler_tail=body[-800:]))
 print('COMPILED zero errors/warnings',flush=True)
def inputs(overrides,tag,original=False):
 vals={}
 for line in BASE.read_text(encoding='utf-8-sig').splitlines():
  if '=' in line:k,v=line.split('=',1);vals[k]=v.split('||')[0]
 if not original:vals['InpAuditTag']=tag
 vals.update({k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in overrides.items()})
 return vals
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def reconstruct(deals,events,start,end,vals):
 eventmap={int(e['position_id']):e for e in events};assert len(eventmap)==len(events)
 seen=set();groups={};balance=10000.;ledger=[]
 for d in deals:
  num=int(d['deal']);assert num not in seen;seen.add(num)
  for k in ['price','volume','gross','commission','swap','fee']:d[k]=float(d[k])
  assert int(d['entry']) in [0,1] and int(d['type']) in [0,1]
  groups.setdefault(int(d['position_id']),[]).append(d)
  flow=round(sum(d[k] for k in ['gross','commission','swap','fee']),2);balance=round(balance+flow,2)
  ledger.append(dict(epoch=int(d['epoch']),deal=num,net=flow,balance=balance))
 assert set(groups)==set(eventmap),'Missing whole-position entry audit'
 trades=[];tf=int(vals['InpSignalTimeframe']);seconds={1:60,5:300,15:900,30:1800,16385:3600}[tf]
 for p,ds in groups.items():
  ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry'])==1];assert len(ins)==len(outs)==1
  ent,ex=ins[0],outs[0];e=eventmap[p];side=int(e['side']);vol=ent['volume']
  assert abs(vol-ex['volume'])<1e-8 and abs(vol-float(e['volume']))<1e-8
  assert int(ent['type'])==(0 if side>0 else 1) and int(ex['type'])==(1 if side>0 else 0)
  sl,tp,requested,actual=[float(e[k]) for k in ['sl','tp','requested_risk','actual_risk']]
  unit=float(e['cash_per_point_lot']);assert unit>0
  assert actual>0 and requested>0 and side*(ent['price']-sl)>0 and (tp==0 or side*(tp-ent['price'])>0)
  assert abs(actual-abs(ent['price']-sl)*vol*unit)<.011
  assert abs(side*(ex['price']-ent['price'])*vol*unit-ex['gross'])<.011
  opened,closed,signal=int(ent['epoch']),int(ex['epoch']),int(e['signal_epoch'])
  assert n.epoch(start)<=opened<=closed<n.epoch(end)
  assert seconds<=opened-signal<seconds+300,('Signal completion',opened,signal,seconds)
  costs={k:round(sum(d[k] for d in ds),2) for k in ['gross','commission','swap','fee']}
  trades.append(dict(position_id=p,open_epoch=opened,close_epoch=closed,last_deal=int(ex['deal']),side='Long' if side>0 else 'Short',volume=vol,
   open_price=ent['price'],close_price=ex['price'],sl=sl,tp=tp,requested_risk=requested,actual_risk=actual,request_spread=float(e['request_spread']),
   net=round(sum(costs.values()),2),initial_rr=side*(tp-ent['price'])/abs(ent['price']-sl) if tp else 0,hold_hours=(closed-opened)/3600,exit_comment=ex['comment'],
   cash_per_point_lot=unit,range_width=float(e['range_width']),atr=float(e['atr']),open_relvol=float(e['open_relvol']),request_price=float(e['request_price']),**costs))
 trades.sort(key=lambda t:(t['close_epoch'],t['last_deal']))
 assert abs(sum(t['net'] for t in trades)-(balance-10000))<.021
 return trades,ledger
def run(tag,window='train',overrides=None,model=4,original=False):
 overrides=overrides or {};start,end=WINDOWS[window];out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 build=read(R/'build.json');assert freeze()==build['frozen'] and sha(SOURCE.with_suffix('.ex5'))==build['binary']
 vals=inputs(overrides,tag,original);manifest=dict(tag=tag,window=window,start=start,end_exclusive=end,inputs=vals,model=model,delay_ms=150,original=original,build=build)
 if (out/'manifest.json').exists():assert read(out/'manifest.json')==manifest,'Case changed'
 else:save(out/'manifest.json',manifest)
 if (out/'results.json').exists():return read(out/'results.json')
 g.free_wait();dest=T/'MQL5/Experts/AAA Research/ORBOptimize20261006';dest.mkdir(parents=True,exist_ok=True)
 binary=ORIGINAL if original else SOURCE.with_suffix('.ex5');name='Original' if original else 'ORB';shutil.copy2(binary,dest/(name+'.ex5'))
 setname='orbopt20261006-'+tag+'.set';body='\n'.join(k+'='+v for k,v in vals.items())+'\n'
 (out/'inputs.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0];ini=out/'tester.ini'
 ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ORBOptimize20261006\\{name}
ExpertParameters={setname}
Symbol=USTEC
Period=M15
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\orbopt20261006\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 rp=T/'reports/orbopt20261006'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();print('START '+tag,flush=True)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=3000)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,('No fresh report',journal[-7000:])
 flags={k:len(re.findall(v,journal,re.I)) for k,v in dict(init='initialization failed',critical='access violation|array out of range|zero divide',audit='ORB_AUDIT_',
  stopout='stop out|margin call',invalid_stops='invalid stops',invalid_volume='invalid volume',history='not enough history|testing start time changed').items()}
 assert not any(flags[k] for k in ['init','critical','audit','stopout','history']),flags
 rb=h._read_report(rp);actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in vals.items()),'Native inputs mismatch'
 assert start in rb and end in rb and 'USTEC' in rb and 'M15' in rb and 'testing with execution delay 150 milliseconds' in journal
 native=h._native_metrics(rp)
 from app.mt5_evidence_jobs import _metric,_number
 native.update(equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')))
 shutil.copy2(rp,out/'report.htm');(out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 save(out/'native-deals.json',g.parse_original(rp));trades=[];ledger=[];counters={};match=None
 if not original:
  for kind in ['events','deals','equity']:
   f=COMMON/(tag+'-'+kind+'.csv');assert f.exists() and f.stat().st_mtime>=began-2;shutil.copy2(f,out/(kind+'.csv'))
  events=rows(out/'events.csv');deals=rows(out/'deals.csv');trace=rows(out/'equity.csv')
  match=n.native_deal_audit(rp,deals);trades,ledger=reconstruct(deals,events,start,end,vals)
  assert len(trades)==native['trades'] and abs(sum(t['net'] for t in trades)-native['net_profit'])<.021
  m=n.metrics(trades,trace);m['mean_initial_rr']=float(np.mean([t['initial_rr'] for t in trades])) if trades else None
  assert 'ORB_SUMMARY audit_complete' in journal
  # Parent and agent journals repeat messages; retain the unique dated failures.
  counters={k:len(set(re.findall(r'[^\r\n]*'+v+r'[^\r\n]*',journal,re.I))) for k,v in dict(order_failed='ORB entry failed',modify_failed='ORB stop update failed|Dynamic trailing SL modification failed',close_failed='ORB time exit failed').items()}
  save(out/'trades.json',trades);save(out/'ledger.json',ledger)
 else:m=dict(trades=native['trades'],return_pct=native['return_pct'],pf=native['profit_factor'],win_rate=native['win_rate_pct'])
 days=(n.epoch(end)-n.epoch(start))/86400;m['trades_month']=m['trades']/(days/30.4375);m['trades_weekday']=m['trades']/len(pd.bdate_range(start.replace('.','-'),(datetime.strptime(end,'%Y.%m.%d')-pd.Timedelta(days=1)).date()))
 result=dict(tag=tag,window=[start,end],model=model,inputs=actual,native=native,metrics=m,counters=counters,flags=flags,trades=trades,ledger=ledger,deal_audit=match,
  report_sha256=sha(rp),binary_sha256=sha(binary),seconds=time.time()-began,
  operational_failure=any(counters.values()),
  tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:15])
 save(out/'results.json',result);print('DONE '+tag+' '+json.dumps(dict(**m,dd=native['equity_dd_pct'],seconds=round(result['seconds'],1),failure=result['operational_failure'])),flush=True)
 return result
def parity():
 a=read(R/'native/original-3m/native-deals.json');b=read(R/'native/raw-3m/native-deals.json');assert a==b,'Default production parity failed'
 save(R/'parity.json',dict(deal_rows=len(a),exact_entry_exit_volume_cost_parity=True,window=WINDOWS['3m']));print('DEFAULT PARITY PASSED',len(a),flush=True)
if __name__=='__main__':
 with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':compile_ea()
  elif sys.argv[1]=='baseline':
   run('original-3m','3m',original=True);run('raw-3m','3m');parity()
   for window in ['1y','6m','3y','5y']:run('raw-'+window,window)
