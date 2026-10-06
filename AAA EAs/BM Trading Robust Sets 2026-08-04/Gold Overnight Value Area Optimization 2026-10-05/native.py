"""Leased isolated MT5 tester; never connects to a live-account API."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,sys,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('gold_safe_helpers',B/'Trend Progression Optimization 2026-10-05/native.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.T
SOURCE=R/'EA/Gold VA Research.mq5'
BASE=B/'Selected Portfolio Settings 2026-09-01/24 Gold Overnight Value Area - RAW - 1PCT.set'
ORIGINAL=B/'Gold Overnight Value Area EA/EA/Gold Overnight Value Area EA.ex5'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGoldVAOptimize20261005'
WINDOWS={'1y':('2025.10.05','2026.10.05'),'6m':('2026.04.05','2026.10.05'),'3m':('2026.07.05','2026.10.05'),
 '3y':('2023.10.05','2026.10.05'),'5y':('2021.10.05','2026.10.05'),'train':('2021.10.05','2024.10.05'),'valid':('2024.10.05','2025.10.05')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def freeze():
 paths=[BASE,ORIGINAL,ORIGINAL.with_suffix('.mq5'),B/'_Auto Deploy/Install-BMTradingPortfolio.ps1']
 v=dict(production={str(p.relative_to(B)):sha(p) for p in paths},research={p.name:sha(p) for p in (R/'EA').glob('*.mq*')},
  protocol=sha(R/'PROTOCOL.md'),runner=sha(Path(__file__)),screen=sha(R/'screen.py'),selection=sha(R/'selection-frozen.json'))
 p=R/'frozen.json'
 if p.exists():assert json.loads(p.read_text())==v,'Frozen files changed'
 else:save(p,v)
 return v
def compile_ea():
 h.h.free();began=time.time();log=R/'compile.log'
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.h.text(log);assert '0 errors, 0 warnings' in body,body[-7000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'build.json',dict(frozen=freeze(),binary=sha(SOURCE.with_suffix('.ex5')),compiler_tail=body[-800:]))
 print('COMPILED: zero errors/warnings',flush=True)
def inputs(kind,tag):
 vals={}
 for line in BASE.read_text(encoding='utf-8-sig').splitlines():
  if '=' in line:k,v=line.split('=',1);vals[k]=v.split('||')[0]
 vals.update(InpWriteAudit='false',InpCase=tag)
 if kind=='candidate':
  c=json.loads((R/'selection-frozen.json').read_text())['selected']['config']
  for a,b in dict(InpStopMode='stop',InpMinimumR='min_r',InpEntryEndMinute='entry_end',InpExitMinute='exit',InpTargetR='target_r',InpBreakEvenR='be',InpTrailDistanceR='trail').items():vals[a]=str(c[b])
 return vals
def csvrows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def reconstruct(deals,events,start,end):
 eventmap={int(x['position_id']):x for x in events};assert len(eventmap)==len(events)
 groups={};cash=[];bal=10000.;seen=set()
 for d in deals:
  num=int(d['deal']);assert num not in seen;seen.add(num)
  for k in ['volume','price','gross','commission','swap','fee']:d[k]=float(d[k])
  p=int(d['position_id']);assert int(d['entry']) in [0,1]
  groups.setdefault(p,[]).append(d)
  flow=round(sum(d[k] for k in ['gross','commission','swap','fee']),2);bal=round(bal+flow,2)
  cash.append(dict(epoch=int(d['epoch']),deal=num,net=flow,balance=bal))
 assert set(groups)==set(eventmap),'Missing position event/deal'
 trades=[]
 for p,ds in groups.items():
  ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry'])==1]
  assert len(ins)==1 and len(outs)==1
  ent=ins[0];ex=outs[0];e=eventmap[p];side=int(e['side']);vol=ent['volume']
  assert abs(vol-ex['volume'])<1e-8 and abs(vol-float(e['volume']))<1e-8
  assert int(ent['type'])==(0 if side>0 else 1) and int(ex['type'])==(1 if side>0 else 0)
  risk=float(e['actual_risk']);requested=float(e['requested_risk']);sl=float(e['sl']);tp=float(e['tp'])
  assert risk>0 and requested>0 and side*(ent['price']-sl)>0 and side*(tp-ent['price'])>0
  # OrderCalcProfit rounds account-currency cash; analytic price*contract need not.
  assert abs(risk-abs(ent['price']-sl)*vol*100)<.011
  signal=int(e['signal_epoch']);opened=int(ent['epoch']);closed=int(ex['epoch'])
  assert 300<=opened-signal<600 and h.epoch(start)<=opened<=closed<=h.epoch(end)
  ny=datetime.fromtimestamp(opened,timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York'))
  assert ny.year*10000+ny.month*100+ny.day==int(e['ny_day'])
  assert ny.hour*60+ny.minute>=575
  costs={k:round(sum(d[k] for d in ds),2) for k in ['gross','commission','swap','fee']}
  t=dict(position_id=p,open_epoch=opened,close_epoch=closed,last_deal=int(ex['deal']),side='Long' if side>0 else 'Short',
   volume=vol,open_price=ent['price'],close_price=ex['price'],sl=sl,tp=tp,requested_risk=requested,actual_risk=risk,net=round(sum(costs.values()),2),
   request_spread=float(e['request_spread']),initial_rr=side*(tp-ent['price'])/abs(ent['price']-sl),exit_comment=ex['comment'],
   cutoff=int(e['cutoff']),late_seconds=max(0,closed-int(e['cutoff'])),hold_hours=(closed-opened)/3600,
   overnight=ny.date()!=datetime.fromtimestamp(closed,timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date(),**costs)
  trades.append(t)
 trades.sort(key=lambda t:(t['close_epoch'],t['last_deal']))
 assert abs(sum(t['net'] for t in trades)-(bal-10000))<.021
 return trades,cash
def parse_original(report):
 from app.mt5_evidence_jobs import _clean,_number
 body=h.h._read_report(report);ix=body.lower().find('<b>deals</b>');assert ix>=0
 rows=[]
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',body[ix:],re.I|re.S):
  c=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
  if len(c)<13 or c[3].lower() not in ['buy','sell']:continue
  rows.append(dict(epoch=int(datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()),
   deal=int(c[1]),type=c[3],entry=c[4],volume=_number(c[5]),price=_number(c[6]),commission=_number(c[8]),swap=_number(c[9]),gross=_number(c[10])))
 return rows
def free_wait():
 for i in range(15):
  try:h.h.free();return
  except AssertionError:
   if i==14:raise
   time.sleep(2)
def run(tag):
 kind,window=tag.split('-',1);assert kind in ['raw','original','candidate'];start,end=WINDOWS[window]
 out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 build=json.loads((R/'build.json').read_text());assert freeze()==build['frozen'] and sha(SOURCE.with_suffix('.ex5'))==build['binary']
 free_wait();dest=T/'MQL5/Experts/AAA Research/GoldVAOptimize20261005';dest.mkdir(parents=True,exist_ok=True)
 binary=ORIGINAL if kind=='original' else SOURCE.with_suffix('.ex5');name='Original' if kind=='original' else 'GoldVA'
 shutil.copy2(binary,dest/(name+'.ex5'));vals=inputs(kind,tag);setname='goldvaopt20261005-'+tag+'.set'
 setbody='\n'.join(k+'='+v for k,v in vals.items())+'\n'
 (out/'inputs.set').write_text(setbody,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
 save(out/'manifest.json',dict(tag=tag,start=start,end_exclusive=end,inputs=vals,model=4,delay_ms=150,deposit=10000,source_hashes=build))
 ini=out/'tester.ini';header=h.h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldVAOptimize20261005\\{name}
ExpertParameters={setname}
Symbol=XAUUSD
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\goldvaopt20261005\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 rp=T/'reports/goldvaopt20261005'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 offsets={p:p.stat().st_size for p in h.h.logfiles()};began=time.time();print('START '+tag,flush=True)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=3000)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timed out')
 journal=''
 for p in h.h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert rp.exists() and rp.stat().st_mtime>=began-2 and proc.returncode==0,('No fresh report',journal[-7000:])
 flags={k:len(re.findall(v,journal,re.I)) for k,v in dict(init='initialization failed',critical='access violation|array out of range|zero divide',
  audit='GVA_AUDIT_',stopout='stop out|margin call',invalid_stops='invalid stops',invalid_volume='invalid volume',market_closed='market closed',
  history='not enough history|testing start time changed').items()}
 assert not any(flags[k] for k in ['init','critical','audit','stopout','history']),flags
 rb=h.h._read_report(rp);actual=h.h._report_inputs(rp)
 assert all(k in actual and h.h._same_setting(v,actual[k]) for k,v in vals.items()),'Native inputs mismatch'
 assert start in rb and end in rb and 'XAUUSD' in rb and 'M5' in rb and 'testing with execution delay 150 milliseconds' in journal
 native=h.h._native_metrics(rp)
 from app.mt5_evidence_jobs import _metric,_number
 native.update(equity_dd_pct=_number(_metric(rb,'Equity Drawdown Relative')),balance_dd_pct=_number(_metric(rb,'Balance Drawdown Relative')))
 shutil.copy2(rp,out/'report.htm');(out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 native_rows=parse_original(rp);save(out/'native-deals.json',native_rows)
 summary=re.findall(r'ONVP_SUMMARY\|[^\r\n]*',journal);assert summary
 counters={k:float(v) for k,v in re.findall(r'([a-z_]+)=([\d.]+)',summary[-1])}
 trades=[];ledger=[];trace=[];match=None
 if kind!='original':
  for name in ['events','deals','equity']:
   f=COMMON/(tag+'-'+name+'.csv');assert f.exists() and f.stat().st_mtime>=began-2;shutil.copy2(f,out/(name+'.csv'))
  events=csvrows(out/'events.csv');deals=csvrows(out/'deals.csv');trace=csvrows(out/'equity.csv')
  match=h.native_deal_audit(rp,deals);trades,ledger=reconstruct(deals,events,start,end)
  assert len(trades)==counters['entries'] and abs(sum(t['net'] for t in trades)-native['net_profit'])<.021
  assert len([d for d in native_rows if d['entry']=='in'])==len(trades)
  stats=h.metrics(trades,trace)
  stats.update(mean_initial_rr=float(np.mean([t['initial_rr'] for t in trades])) if trades else None,
   max_initial_risk_pct=max((100*t['actual_risk']/ (100*t['requested_risk']) for t in trades),default=None),
   late_exits_over_60s=sum(t['late_seconds']>60 for t in trades),overnight_positions=sum(t['overnight'] for t in trades))
  execs=re.findall(r'GVA_EXECUTION\|modify_failed=(\d+)\|close_failed=(\d+)',journal);assert execs
  counters.update(modify_failed=int(execs[-1][0]),close_failed=int(execs[-1][1]))
  save(out/'trades.json',trades);save(out/'ledger.json',ledger)
 else:stats=dict(trades=int(counters['entries']),return_pct=native['return_pct'],pf=native['profit_factor'],win_rate=native['win_rate_pct'])
 days=(h.epoch(end)-h.epoch(start))/86400
 stats['trades_month']=stats['trades']/(days/30.4375);stats['trades_weekday']=stats['trades']/len(pd.bdate_range(start.replace('.','-'),(datetime.strptime(end,'%Y.%m.%d')-pd.Timedelta(days=1)).date()))
 result=dict(tag=tag,window=[start,end],inputs=actual,native=native,metrics=stats,counters=counters,flags=flags,trades=trades,ledger=ledger,
  deal_audit=match,report_sha256=sha(rp),binary_sha256=sha(binary),elapsed_seconds=time.time()-began,
  tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:15],
  operational_failure=any(counters.get(k,0)>0 for k in ['rejected','modify_failed','close_failed']))
 save(out/'results.json',result);print('DONE '+tag+' '+json.dumps(dict(**stats,dd=native['equity_dd_pct'],quality=native['history_quality'],operational_failure=result['operational_failure'])),flush=True)
 return result
def parity():
 a=json.loads((R/'native/original-3m/native-deals.json').read_text());b=json.loads((R/'native/raw-3m/native-deals.json').read_text())
 assert a==b,'Default clone/native production parity failed'
 save(R/'parity.json',dict(native_deal_rows=len(a),exact_trade_cash_parity=True,window=WINDOWS['3m']))
 print('DEFAULT PARITY PASSED',len(a),'deal rows',flush=True)
if __name__=='__main__':
 with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':compile_ea()
  elif sys.argv[1]=='parity':parity()
  elif sys.argv[1]=='all':
   for tag in ['original-3m','raw-3m']:run(tag)
   parity()
   for tag in ['raw-1y','raw-6m','candidate-train','candidate-valid','candidate-1y','candidate-6m','candidate-3m','raw-3y','candidate-3y','raw-5y','candidate-5y']:run(tag)
  else:
   for tag in sys.argv[1:]:run(tag)
