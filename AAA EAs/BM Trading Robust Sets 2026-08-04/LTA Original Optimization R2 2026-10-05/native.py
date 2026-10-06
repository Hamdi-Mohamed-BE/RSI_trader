"""Native, isolated MT5 last-year comparison. No trading API or deployment."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,msvcrt
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('lta_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER
SOURCE=R/'EA/LTA Flow Research.mq5';BASE=B/'Selected Portfolio Settings 2026-09-01/01 LTA Volume Profile - CURRENT - ALL DAY.set'
ORIGINAL=B/'LTA volume profile/EA/LTA_Concepts_EA.ex5'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxLTAOptimizeR220261005'
START='2025.10.05';END='2026.10.05'
CASES={
 'ORIGINAL':dict(label='Current LTA M15 (shipped binary)',mode=0,tf=15,safe=False,original=True),
 'CURRENT_M15':dict(label='Current LTA M15',mode=0,tf=15,safe=False),
 'CURRENT_M5':dict(label='Current entry rules on M5',mode=0,tf=5,safe=False),
 'FLOW_M5':dict(label='New VWAP / developing POC M5',mode=1,tf=5,safe=False),
 'AND_M5':dict(label='LTA M5 signal AND new flow',mode=2,tf=5,safe=False),
 'SAFE_M15':dict(label='Current LTA M15 — BAT Safe default',mode=0,tf=15,safe=True),
 'FLOW_SAFE_M5':dict(label='New flow M5 — same Safe gate',mode=1,tf=5,safe=True),
 'SMOKE':dict(label='Flow smoke test',mode=1,tf=5,safe=False,start='2026.09.01',end='2026.09.08')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def freeze():
 v=dict(production={str(p.relative_to(B)):sha(p) for p in [BASE,ORIGINAL,B/'LTA volume profile/EA/LTA_Concepts_EA.mq5']},
  research={p.name:sha(p) for p in sorted((R/'EA').glob('*.mq*'))},protocol=sha(R/'PROTOCOL.md'),
  plan=sha(R/'plan.py'),native_runner=sha(Path(__file__)))
 p=R/'frozen.json'
 if p.exists():assert json.loads(p.read_text())==v,'Frozen source/config changed'
 else:save(p,v)
 return v
def compile_ea():
 h.free();log=R/'compile.log';began=time.time()
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log) if log.exists() else 'No compiler output'
 assert '0 errors, 0 warnings' in body,body[-6000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'build.json',dict(binary=sha(SOURCE.with_suffix('.ex5')),compiler_tail=body[-600:],frozen=freeze()))
 print('COMPILED: zero errors/warnings',flush=True)
def csvrows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def epoch(s):return int(datetime.strptime(s,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
def stamp(n):return datetime.fromtimestamp(int(n),timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def reconstruct(deals,events,mode):
 entries={int(x['position_id']):x for x in events if x['event']=='entry'};groups={};ledger=[];balance=10000.;seen=set()
 for d in deals:
  num=int(d['deal']);assert num not in seen;seen.add(num)
  p=int(d['position_id']);e=int(d['entry']);assert e in (0,1)
  for k in ['volume','price','gross','commission','swap','fee']:d[k]=float(d[k])
  flow=sum(d[k] for k in ['gross','commission','swap','fee']);balance=round(balance+flow,2)
  ledger.append(dict(deal=num,epoch=int(d['epoch']),cash_flow=flow,balance=balance))
  groups.setdefault(p,[]).append(d)
 assert set(entries)==set(groups),'Unpaired audit position'
 trades=[]
 for p,ds in groups.items():
  ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry'])==1]
  assert len(ins)==1 and outs
  vi=sum(d['volume'] for d in ins);vo=sum(d['volume'] for d in outs);assert abs(vi-vo)<1e-8
  ent=ins[0];event=entries[p];side=int(event['dir']);assert int(ent['type'])==(0 if side>0 else 1)
  assert all(int(x['type'])==(1 if side>0 else 0) for x in outs)
  cost={k:round(sum(d[k] for d in ds),2) for k in ['gross','commission','swap','fee']}
  relevant=[x for x in events if int(x['position_id'])==p];parts=[x for x in relevant if x['event']=='partial'];bes=[x for x in relevant if x['event']=='breakeven']
  assert len(parts)<=1 and len(bes)<=1
  t=dict(position_id=p,open_epoch=int(ent['epoch']),close_epoch=int(outs[-1]['epoch']),last_deal=int(outs[-1]['deal']),
   side='Long' if side>0 else 'Short',volume=vi,open_price=ent['price'],close_price=sum(x['price']*x['volume'] for x in outs)/vi,
   sl=float(event['sl']),tp=float(event['tp']),requested_risk=float(event['requested_risk']),actual_risk=float(event['actual_risk']),
   net=round(sum(cost.values()),2),**cost,partial=bool(parts),breakeven=bool(bes),exit_comments=[d['comment'] for d in outs],audit=event)
  assert side*(t['open_price']-t['sl'])>0 and side*(t['tp']-t['open_price'])>0
  assert t['actual_risk']>0
  if mode:
   a=event;sig=int(a['signal_epoch']);assert int(a['pd_from'])<int(a['pd_to'])<=sig<t['open_epoch']
   assert 300<=t['open_epoch']-sig<600
   assert float(a['val'])<=t['open_price']<=float(a['vah'])
   assert abs(t['tp']-float(a['vah' if side>0 else 'val']))<.002
   assert float(a['body_fraction'])>=.6-1e-8
   assert float(a['close_location'])>=.75-1e-8 if side>0 else float(a['close_location'])<=.25+1e-8
   for x in parts+bes:
    assert int(x['epoch'])>t['open_epoch'];note=x['note'];close=float(note.split('close=')[1].split('|')[0]);bar=int(note.split('bar=')[1])
    assert bar>=t['open_epoch'] and side*(close-float(a['poc']))>0
    if x['event']=='partial':
     half=float(x['requested_risk']);assert 0<half<=vi*.5+1e-8
     assert any(abs(d['volume']-half)<1e-8 and 0<=int(d['epoch'])-int(x['epoch'])<=5 for d in outs)
    else:assert abs(float(x['sl'])-t['open_price'])<.002
  t['open_time']=stamp(t['open_epoch']);t['close_time']=stamp(t['close_epoch']);t['hold_hours']=(t['close_epoch']-t['open_epoch'])/3600
  trades.append(t)
 trades.sort(key=lambda x:(x['close_epoch'],x['last_deal']))
 assert abs(sum(t['net'] for t in trades)-(balance-10000))<.021
 return trades,ledger
def metrics(trades,trace=None):
 vals=[t['net'] for t in trades];wins=[v for v in vals if v>0];losses=[v for v in vals if v<0]
 w=l=mw=ml=0
 for v in vals:
  w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(mw,w);ml=max(ml,l)
 sharpe=None
 if trace:
  df=pd.DataFrame(trace);df['time']=pd.to_datetime(df.epoch.astype('int64'),unit='s',utc=True)
  daily=pd.Series(df.equity.astype(float).values,index=df.time).resample('D').last().ffill()
  daily=daily[daily.index.weekday<5];returns=daily.pct_change().dropna()
  if len(returns)>2 and returns.std(ddof=1)>0:sharpe=float(np.sqrt(252)*returns.mean()/returns.std(ddof=1))
 return dict(trades=len(vals),return_pct=sum(vals)/100,net_profit=round(sum(vals),2),pf=sum(wins)/-sum(losses) if losses else None,
  win_rate=100*len(wins)/len(vals) if vals else None,wins=len(wins),losses=len(losses),flat=len(vals)-len(wins)-len(losses),
  win_streak=mw,loss_streak=ml,avg_win=sum(wins)/len(wins) if wins else None,avg_loss=sum(losses)/len(losses) if losses else None,
  sharpe_daily_equity=sharpe,partials=sum(t.get('partial',False) for t in trades),breakevens=sum(t.get('breakeven',False) for t in trades),
  trades_month=len(vals)/12,trades_weekday=len(vals)/len(pd.bdate_range('2025-10-05','2026-10-04')),
  commission=sum(t.get('commission',0) for t in trades),swap=sum(t.get('swap',0) for t in trades),fee=sum(t.get('fee',0) for t in trades),
  max_actual_risk_budget_ratio=max((t['actual_risk']/t['requested_risk'] for t in trades if t.get('requested_risk',0)>0),default=None))
def inputs(c,tag):
 vals={}
 for line in BASE.read_text(encoding='utf-8-sig').splitlines():
  if '=' in line:
   k,v=line.split('=',1);vals[k]=v.split('||')[0]
 vals.update(InpUseMarkovRegimeFilter=str(c['safe']).lower(),InpMarkovReturnWindow='40',InpMarkovThreshold='0.05',InpMarkovSignalGate='0.05',
  InpMarkovMinLabels='252',InpMarkovHistoryBars='2600',InpAdaptivePortfolioControls='false',InpExecutionTF=str(c['tf']))
 if not c.get('original'):vals.update(InpFlowMode=str(c['mode']),InpAuditTag=tag)
 vals.update({k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in c.get('overrides',{}).items()})
 return vals
def native_deal_audit(report,deals):
 from app.mt5_evidence_jobs import _clean,_number
 text=h._read_report(report);marker=text.lower().find('<b>deals</b>');assert marker>=0
 native={}
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text[marker:],re.I|re.S):
  c=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
  if len(c)<13 or c[3].lower() not in ['buy','sell']:continue
  native[int(c[1])]=dict(epoch=int(datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()),
   entry=0 if c[4]=='in' else 1,type=0 if c[3]=='buy' else 1,volume=_number(c[5]),price=_number(c[6]),commission=_number(c[8]),swap=_number(c[9]),gross=_number(c[10]))
 assert set(native)=={int(d['deal']) for d in deals}
 for d in deals:
  row=native[int(d['deal'])]
  for k,v in row.items():assert abs(v-float(d[k]))<1e-7,(d['deal'],k,v,d[k])
  assert abs(float(d['fee']))<1e-9,'HTML omits non-zero fee'
 return dict(native_deal_rows=len(native),all_exported_deals_match_native_report=True)
def run(tag,reanalyze=False):
 c=CASES[tag];out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True);build=json.loads((R/'build.json').read_text());assert freeze()==build['frozen']
 assert sha(SOURCE.with_suffix('.ex5'))==build['binary']
 if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 h.free();dest=T/'MQL5/Experts/AAA Research/LTAFlow20261005';dest.mkdir(parents=True,exist_ok=True)
 binfile=ORIGINAL if c.get('original') else SOURCE.with_suffix('.ex5');name='Original' if c.get('original') else 'Flow'
 shutil.copy2(binfile,dest/(name+'.ex5'))
 vals=inputs(c,tag);setname='ltaflow20261005-'+tag+'.set';setbody='\n'.join(k+'='+v for k,v in vals.items())+'\n'
 (out/'inputs.set').write_text(setbody,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
 start=c.get('start',START);end=c.get('end',END);model=c.get('model',4)
 period={5:'M5',15:'M15',30:'M30',60:'H1'}[c['tf']]
 save(out/'manifest.json',dict(case=c,start=start,end_exclusive=end,inputs=vals,source_hashes=build,model=model,delay_ms=150,deposit=10000))
 ini=out/'tester.ini';header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\LTAFlow20261005\\{name}
ExpertParameters={setname}
Symbol=XAUUSD
Period={period}
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\ltaopt20261005\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 rp=T/'reports/ltaopt20261005'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 if reanalyze:
  began=json.loads((out/'owned-process.json').read_text())['started'];rp=out/'report.htm'
  journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
  assert rp.exists() and rp.stat().st_mtime>=began-2
  print('REANALYZE ARCHIVED '+tag,flush=True)
 else:
  offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();print('START '+tag,flush=True)
  proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
  save(out/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
  try:proc.wait(timeout=2700)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only owned isolated tester timed out')
  journal=''
  for p in h.logfiles():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
  (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert rp.exists() and rp.stat().st_mtime>=began-2 and proc.returncode==0,'No fresh successful report'
 flags={k:len(re.findall(v,journal,re.I)) for k,v in dict(initialization='initialization failed',critical='access violation|array out of range|zero divide',
  no_history='not enough history|testing start time changed',invalid_stops='invalid stops',invalid_volume='invalid volume',audit='FLOW_AUDIT_',stopout='stop out|margin call').items()}
 assert not any(v for k,v in flags.items() if k!='invalid_stops'),flags
 assert all('modify' in line.lower() for line in journal.splitlines() if 'invalid stops' in line.lower()),'Entry stop rejection'
 rb=h._read_report(rp);actual=h._report_inputs(rp)
 assert all(k in actual and h._same_setting(v,actual[k]) for k,v in vals.items()),'Input mismatch'
 assert start in rb and end in rb and 'XAUUSD' in rb and period in rb
 assert 'testing with execution delay 150 milliseconds' in journal
 native=h._native_metrics(rp)
 from app.mt5_evidence_jobs import _metric,_number
 native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 native['balance_dd_pct']=_number(_metric(rb,'Balance Drawdown Relative'))
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 if rp!=out/'report.htm':shutil.copy2(rp,out/'report.htm')
 simple=h._native_trades(rp,tag);save(out/'native-trade-legs.json',simple)
 trades=[];ledger=[];trace=[];events=[];counters={}
 if not c.get('original'):
  for kind in ['events','deals','equity']:
   f=COMMON/(tag+'-'+kind+'.csv');assert f.exists() and f.stat().st_mtime>=began-2;shutil.copy2(f,out/(kind+'.csv'))
  events=csvrows(out/'events.csv');deals=csvrows(out/'deals.csv');trace=csvrows(out/'equity.csv')
  trades,ledger=reconstruct(deals,events,c['mode']);assert abs(sum(t['net'] for t in trades)-native['net_profit'])<.021
  assert len(trades)==sum(int(d['entry'])==0 for d in deals)
  assert len(simple)==sum(int(d['entry'])==1 for d in deals)
  leg_rounding=sum(x['net_profit'] for x in simple)-native['net_profit']
  assert abs(leg_rounding)<=.0051*len(simple)+.01
  deal_audit=native_deal_audit(rp,deals)
  summaries=re.findall(r'FLOW_SUMMARY entries=(\d+) partials=(\d+) be=(\d+) minpartial=(\d+) orders_failed=(\d+) close_failed=(\d+) modify_failed=(\d+) maxdd=([\d.]+) cashdd=([\d.]+)',journal)
  assert summaries
  counters=dict(zip(['entries','partials','be','minpartial','order_failed','close_failed','modify_failed','observed_dd','observed_cash_dd'],map(float,summaries[-1])))
  assert counters['entries']==len(trades) and counters['partials']==sum(t['partial'] for t in trades)
  assert not any(counters[k] for k in ['order_failed','close_failed','modify_failed']),counters
  failed=[x for x in events if x['event']=='breakeven_failed']
  assert len(failed)==counters['modify_failed']
  assert all(any(y['event']=='breakeven' and y['position_id']==x['position_id'] and int(y['epoch'])>int(x['epoch']) for y in events) for x in failed),'Unrecovered BE rejection'
  assert flags['invalid_stops']==4*len(failed),(flags,len(failed))
  assert all(epoch(start)<=t['open_epoch']<=t['close_epoch']<epoch(end) for t in trades)
  save(out/'trades.json',trades);save(out/'ledger.json',ledger)
  m=metrics(trades,trace)
 else:
  assert abs(sum(x['net_profit'] for x in simple)-native['net_profit'])<.021
  m=dict(trades=len(simple),return_pct=native['return_pct'],pf=native['profit_factor'],win_rate=native['win_rate_pct'])
 days=(datetime.strptime(end,'%Y.%m.%d')-datetime.strptime(start,'%Y.%m.%d')).days
 m['trades_month']=len(trades)/(days/30.4375)
 m['trades_weekday']=len(trades)/len(pd.bdate_range(start.replace('.','-'),(datetime.strptime(end,'%Y.%m.%d')-pd.Timedelta(days=1)).date()))
 result=dict(case=tag,label=c['label'],window=[start,end],model=model,inputs=actual,native=native,metrics=m,trades=trades,ledger=ledger,counters=counters,flags=flags,
  deal_audit=deal_audit if not c.get('original') else None,
  report_sha256=sha(rp),binary_sha256=sha(binfile),seconds=round(rp.stat().st_mtime-began,1),
  tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:12])
 save(out/'results.json',result);print('DONE '+tag+' '+json.dumps(dict(**m,dd=native['equity_dd_pct'],quality=native['history_quality'])),flush=True)
 if tag=='CURRENT_M15' and (R/'native/ORIGINAL/results.json').exists():
  original=json.loads((R/'native/ORIGINAL/native-trade-legs.json').read_text());clone=simple
  for data in [original,clone]:
   for t in data:t.pop('ea',None)
  assert original==clone,'Off-switch parity differs from shipped binary'
  save(R/'PARITY.json',dict(passed=True,trades=len(clone),original_hash=sha(ORIGINAL),research_hash=sha(SOURCE.with_suffix('.ex5')),same_trade_times_prices_volume_costs=True))
 return result
if __name__=='__main__':
 with (R/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':compile_ea()
  else:
   reanalyze=sys.argv[1]=='--analyze'
   for tag in sys.argv[2:] if reanalyze else sys.argv[1:]:run(tag,reanalyze)
