"""Frozen public-idea reconstruction, isolated native MT5 ONLY."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,msvcrt
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('gold4_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER
SOURCE=R/'EA/Calyx Gold Speed Q4 Turn Research.mq5';EXPERT=SOURCE.with_suffix('.ex5')
CFG=json.loads((R/'run-config.json').read_text())
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGoldSpeed20261005'
LABELS={'A_SPEED':'Adaptive H4 momentum','B_Q4':'Q4 H1 breakout','C_TURN':'Turn of month'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(msg):
 save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=msg));print(msg,flush=True)
def compile_ea():
 h.free();log=SOURCE.with_suffix('.compile.log');began=time.time()
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log) if log.exists() else 'No compiler output'
 assert '0 errors, 0 warnings' in body,body[-7000:]
 assert EXPERT.stat().st_mtime>=began-2
 save(R/'build.json',dict(source_sha256=sha(SOURCE),binary_sha256=sha(EXPERT),protocol_sha256=sha(R/'PROTOCOL.txt'),config_sha256=sha(R/'run-config.json'),compiler_tail=body[-700:]))
 status('COMPILED: zero errors/warnings')
def metrics(trades):
 p=[t['net_profit'] for t in trades];win=[x for x in p if x>0];loss=[x for x in p if x<0]
 w=l=mw=ml=0
 for t in sorted(trades,key=lambda t:(t['close_epoch'],t['last_exit_deal'])):
  if t['net_profit']>0:w+=1;l=0
  elif t['net_profit']<0:l+=1;w=0
  else:w=l=0
  mw=max(mw,w);ml=max(ml,l)
 return dict(trades=len(p),net_profit=round(sum(p),2),return_pct=sum(p)/100,net_pf=sum(win)/-sum(loss) if loss else None,
  win_rate_pct=100*len(win)/len(p) if p else None,wins=len(win),losses=len(loss),flat=sum(x==0 for x in p),
  max_win_streak=mw,max_loss_streak=ml,avg_win_usd=sum(win)/len(win) if win else None,
  avg_loss_usd=sum(loss)/len(loss) if loss else None,expectancy_usd=sum(p)/len(p) if p else None,
  mean_net_initial_R=sum(t['net_profit']/t['actual_risk'] for t in trades)/len(trades) if trades else None)
def reconstruct(deals,export):
 """Exact DEAL_POSITION_ID pairing; entry costs, partials, out-of-order hedged closures."""
 rows={};ledger=[];balance=10000.;ids=set()
 for d in deals:
  deal=int(d['deal']);assert deal not in ids;ids.add(deal)
  pos=int(d['position_id']);e=int(d['entry']);assert e in (0,1)
  flow=sum(float(d[k]) for k in ['gross','commission','swap','fee']);balance=round(balance+flow,2)
  ledger.append(dict(deal=deal,position_id=pos,epoch=int(d['epoch']),time=datetime.fromtimestamp(int(d['epoch']),timezone.utc).isoformat(),
   entry=e,cash_flow=round(flow,2),balance=balance))
  if e==0:
   assert pos not in rows
   rows[pos]=dict(position_id=pos,open_epoch=int(d['epoch']),entry_deal=deal,side='Long' if int(d['type'])==0 else 'Short',
    volume=float(d['volume']),open_price=float(d['price']),remaining=float(d['volume']),net_profit=flow,gross_profit=float(d['gross']),
    commission=float(d['commission']),swap=float(d['swap']),fee=float(d['fee']),exits=[])
  else:
   assert pos in rows and rows[pos]['remaining']>=float(d['volume'])-1e-8
   t=rows[pos];assert int(d['type'])==(1 if t['side']=='Long' else 0)
   t['remaining']-=float(d['volume']);t['net_profit']+=flow
   for k in ['gross','commission','swap','fee']:t['gross_profit' if k=='gross' else k]+=float(d[k])
   t['exits'].append(d);t['close_epoch']=int(d['epoch']);t['last_exit_deal']=deal
 result=[];exp={int(t['position_id']):t for t in export}
 assert set(rows)==set(exp)
 for pos,t in rows.items():
  assert abs(t.pop('remaining'))<1e-8
  exits=t.pop('exits');t['close_price']=sum(float(d['volume'])*float(d['price']) for d in exits)/t['volume']
  e=exp[pos]
  for k in ['open_epoch','close_epoch','volume','open_price','close_price','net_profit','gross_profit','commission','swap','fee']:
   actual=t[k];expected=float(e[k])
   assert abs(actual-expected)<(.021 if k in ['net_profit','gross_profit','commission','swap','fee'] else 1e-6),(k,pos,actual,expected)
  t.update(module=e['module'],module_name=LABELS[e['module']],initial_sl=float(e['initial_sl']),initial_tp=float(e['initial_tp']),
   requested_risk=float(e['requested_risk']),actual_risk=float(e['actual_risk']))
  for k in ['net_profit','gross_profit','commission','swap','fee']:t[k]=round(t[k],2)
  for k in ['open','close']:t[k+'_time']=datetime.fromtimestamp(t[k+'_epoch'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
  t['hold_hours']=(t['close_epoch']-t['open_epoch'])/3600
  t['result']='Win' if t['net_profit']>0 else 'Loss' if t['net_profit']<0 else 'Flat'
  result.append(t)
 result.sort(key=lambda t:(t['close_epoch'],t['last_exit_deal']))
 for i,t in enumerate(result):t['number']=i+1
 assert abs(sum(t['net_profit'] for t in result)-(balance-10000))<.015
 return result,ledger
def algebra_audit(journal,trades,signals,control):
 a={};b={};entry={}
 for line in journal.splitlines():
  hit=re.search(r'GS_ENTRY position=(\d+) module=(\w+) requested=([\d.]+) quote_stop_cash=([\d.]+) actual_stop_cash=([\d.]+)',line)
  if hit:entry[int(hit[1])]=dict(module=hit[2],budget=float(hit[3]),quote_risk=float(hit[4]),actual_risk=float(hit[5]))
  for prefix,out in [('GS_A',a),('GS_B',b)]:
   hit=re.search(prefix+r' bar=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}) (.+)',line)
   if hit:
    vals={k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',hit[2])}
    key=int(datetime.strptime(hit[1],'%Y.%m.%d %H:%M').replace(tzinfo=timezone.utc).timestamp())
    assert key not in out or vals==out[key];out[key]=vals
 sig={int(x['position_id']):x for x in signals};assert set(sig)==set(entry)=={t['position_id'] for t in trades}
 active=[];maxactive=0
 for t in sorted(trades,key=lambda t:t['entry_deal']):
  e=entry[t['position_id']];s=sig[t['position_id']];t['signal_audit']=s;t['risk_audit']=e
  assert e['module']==t['module'] and abs(e['budget']-t['requested_risk'])<1e-6
  assert e['quote_risk']<=e['budget']+.011 and e['actual_risk']>0
  assert abs(e['actual_risk']-t['actual_risk'])<1e-6
  assert int(s['actual_side'])==(1 if t['side']=='Long' else -1)
  side=int(s['raw_side']);bar=int(s['signal_time']);atr=float(s['atr'])
  assert atr>0
  dt=datetime.fromtimestamp(t['open_epoch'],timezone.utc)
  if not control:assert side==int(s['actual_side'])
  if t['module']=='A_SPEED':
   x=a[bar];lb=int(x['lookback'])
   assert lb==(6 if x['atr']>x['atr_mean'] else 24)
   assert 14400<=t['open_epoch']-bar<14700
   assert abs(float(s['stop_distance'])-2.5*atr)<1e-6
   if side>0:assert x['close']-x['old_close']>.5*x['atr'] and x['ema']>x['prev_ema'] and x['close']>x['high']
   else:assert x['close']-x['old_close']<-.5*x['atr'] and x['ema']<x['prev_ema'] and x['close']<x['low']
  elif t['module']=='B_Q4':
   x=b[bar];assert dt.month>=10 and 3600<=t['open_epoch']-bar<3900 and x['atr']>x['atr_mean']
   assert abs(float(s['stop_distance'])-2*atr)<1e-6
   pos=(x['close']-x['range_low'])/(x['range_high']-x['range_low'])
   if side>0:assert x['close']>x['break_high'] and pos>=.9-1e-9
   else:assert x['close']<x['break_low'] and pos<=.1+1e-9
  else:
   assert t['side']=='Long'
   day=datetime(dt.year,dt.month,dt.day)
   days=pd.date_range(day.replace(day=1),day,freq='D');td=sum(d.weekday()<5 for d in days)
   if control:assert td==10
   else:
    nxt=day+timedelta(days=1)
    while nxt.weekday()>=5:nxt+=timedelta(days=1)
    assert nxt.month!=day.month
  active=[x for x in active if x['last_exit_deal']>t['entry_deal']]
  assert not any(x['module']==t['module'] for x in active)
  active.append(t);maxactive=max(maxactive,len(active));assert len(active)<=3
 return dict(accepted_position_audits=len(trades),signal_algebra_passed=True,one_slot_per_module=True,max_concurrent_positions=maxactive,
  requested_quote_risk_cash_allowance_usd=.011,max_quote_risk_excess_usd=max((t['risk_audit']['quote_risk']-t['requested_risk'] for t in trades),default=0),
  max_actual_stop_risk_to_budget=max((t['actual_risk']/t['requested_risk'] for t in trades),default=0))
def run(case_id):
 c=next(x for x in CFG['cases'] if x['id']==case_id);start,end=CFG['windows'][c['window']]
 warm=(datetime.strptime(start,'%Y.%m.%d')-timedelta(days=CFG['warmup_days'])).strftime('%Y.%m.%d')
 if case_id!='SMOKE':assert (R/'native/SMOKE/results.json').exists()
 build=json.loads((R/'build.json').read_text())
 assert sha(SOURCE)==build['source_sha256'] and sha(EXPERT)==build['binary_sha256']
 assert sha(R/'PROTOCOL.txt')==build['protocol_sha256'] and sha(R/'run-config.json')==build['config_sha256']
 out=R/'native'/case_id;out.mkdir(parents=True,exist_ok=True)
 vals=dict(InpModules=c['modules'],InpBreakoutQ4Only='true',InpControl=str(c['control']).lower(),InpRiskPercent=1,
  InpSeed=CFG['seed'],InpTradeFrom=start+' 00:00:00',InpTag=case_id,InpMagic=1005040)
 receipt=dict(case=c,start=start,end_exclusive=end,warmup_from=warm,build=build,inputs=vals,deposit=10000,model=4,delay_ms=150,symbol=c['symbol'],period='M1')
 if (out/'manifest.json').exists():assert json.loads((out/'manifest.json').read_text())==receipt
 else:save(out/'manifest.json',receipt)
 if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 h.free()
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 dest=T/'MQL5/Experts/AAA Research/GoldSpeedPublic20261005';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(EXPERT,dest/'RAW.ex5')
 setname='gold4-'+case_id+'.set';body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n'
 (out/'inputs.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldSpeedPublic20261005\\RAW
ExpertParameters={setname}
Symbol={c['symbol']}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
ForwardMode=0
Report=reports\\gold-speed-public20261005\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 rp=T/'reports/gold-speed-public20261005'/(case_id+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free();status('START '+case_id)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=2700)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only owned research tester timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
 assert not re.search(r'initialization failed|testing start time changed|not enough history|access violation|array out of range|zero divide|GS_REQUIRES_HEDGING|GS_AUDIT_FAILED',journal,re.I)
 flags={k:len(re.findall(v,journal,re.I)) for k,v in {'entry_errors':'GS_ENTRY_FAIL','close_errors':'GS_CLOSE_FAIL','modify_errors':'GS_MODIFY_FAIL','invalid_stops':'invalid stops','invalid_volume':'invalid volume','stopout':'stop out|margin call'}.items()}
 assert not any(flags.values()),flags
 rb=h._read_report(rp);assert all(x in rb for x in [warm,end,c['symbol'],'M1'])
 actual=h._report_inputs(rp)
 expected=vals|dict(InpTradeFrom=int(datetime.strptime(start,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()))
 assert all(k in actual and h._same_setting(str(v),actual[k]) for k,v in expected.items())
 assert 'testing with execution delay 150 milliseconds' in journal
 frames={}
 for kind in ['trades','deals','signals','trace']:
  f=COMMON/(case_id+'-'+kind+'.csv');assert f.exists() and f.stat().st_mtime>=began-2,(kind,str(f))
  shutil.copy2(f,out/(kind+'.csv'));frames[kind]=pd.read_csv(f).to_dict('records')
 trades,ledger=reconstruct(frames['deals'],frames['trades'])
 audits=algebra_audit(journal,trades,frames['signals'],c['control'])
 native=h._native_metrics(rp)
 from app.mt5_evidence_jobs import _number,_metric
 native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 native['balance_dd_pct']=_number(_metric(rb,'Balance Drawdown Relative'))
 assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.021
 for t in trades:
  assert expected['InpTradeFrom']<=t['open_epoch']<=t['close_epoch']<int(datetime.strptime(end,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
 counters=re.findall(r'GS_SUMMARY A=(\d+) B=(\d+) C=(\d+) entryFails=(\d+) closeFails=(\d+) modifyFails=(\d+) skips=(\d+) minlot_skips=(\d+) stale=(\d+) trails=(\d+)',journal)
 assert counters
 counter=dict(zip(['A','B','C','entryFails','closeFails','modifyFails','skips','minlot_skips','stale','trails'],map(int,counters[-1])))
 assert all(counter[k]==sum(t['module']==m for t in trades) for k,m in zip('ABC',LABELS))
 result=dict(manifest=receipt,native=native,net_metrics=metrics(trades),module_metrics={k:metrics([t for t in trades if t['module']==k]) for k in LABELS},
  trades=trades,ledger=ledger,counters=counter,flags=flags,audit=audits,seconds=round(time.time()-began,1),report_sha256=sha(rp),
  trace_note='Five-minute sampled equity, not continuous tick-level equity',
  tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:20])
 save(out/'results.json',result);save(out/'ledger.json',ledger)
 (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 status('DONE '+case_id+' '+json.dumps(dict(**result['net_metrics'],equity_dd_pct=native['equity_dd_pct'],quality=native['history_quality'])))
 return result
if __name__=='__main__':
 with (R/'tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  if sys.argv[1]=='compile':compile_ea()
  else:
   cases=[x['id'] for x in CFG['cases']] if sys.argv[1]=='all' else sys.argv[1:]
   for c in cases:run(c)
   save(R/'RESULTS.json',[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))])
