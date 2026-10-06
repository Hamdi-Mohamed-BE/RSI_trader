"""Current news replay only, shared isolated-tester lease; no production writes."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import csv,gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,sys,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('news_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER;DEST=T/'MQL5/Experts/AAA Research/NewsAudit20261005'
S=B/'AAA Final EAs/AAA Final News Pulse XAU Event Specific EA/AAA Final News Pulse XAU Event Specific EA.mq5'
SET=B/'Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'
HELP=B/'AAA Final EAs/AAA Final News Pulse EA'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxNewsAudit20261005'
CASES=[('PARITY-ORIGINAL','2026.08.01','2026.09.01',150,True),('PARITY-AUDIT','2026.08.01','2026.09.01',150,False),
 ('INCIDENT','2026.10.02','2026.10.03',150,False),('1Y-150','2025.10.05','2026.10.05',150,False),
 ('1Y-1000','2025.10.05','2026.10.05',1000,False),('1Y-3000','2025.10.05','2026.10.05',3000,False),
 ('6M-150','2026.04.05','2026.10.05',150,False),('3M-150','2026.07.05','2026.10.05',150,False),
 ('3Y-150','2023.10.05','2026.10.05',150,False),('5Y-150','2021.10.05','2026.10.05',150,False)]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def status(message):print(message,flush=True);save(R/'status.json',dict(message=message,utc=datetime.now(timezone.utc).isoformat()))
def free():
 deadline=time.monotonic()+50
 while True:
  try:h.free();return
  except AssertionError:
   if time.monotonic()>deadline:raise
   time.sleep(2)
def fingerprint():
 files=[S,S.with_suffix('.ex5'),SET,S.parent/'NewsPulsePlacement.mqh',B/'_Shared/CalyxAdaptivePortfolio.mqh']+list(HELP.glob('*.mqh'))
 return dict(production={str(p.relative_to(B)):sha(p) for p in files},protocol=sha(R/'PROTOCOL.md'),runner=sha(Path(__file__)),audit=sha(R/'audit.mqh'),receipts=sha(R/'fresh-calendar-receipts.json'),cases=CASES)

def verify_frozen():
 actual=json.loads(json.dumps(fingerprint()));frozen=read(R/'FROZEN.json')
 if actual!=frozen:
  amendment=read(R/'PARSER AMENDMENT.json')
  assert frozen['runner']==amendment['original_runner_sha'] and actual['runner']==amendment['corrected_runner_sha']
  actual['runner']=frozen['runner']
 assert actual==frozen,'Frozen trading rules, protocol, inputs or calendar changed'
def prepare():
 free();snap=R/'snapshot';snap.mkdir(exist_ok=True)
 archive=B/'News Pulse Event Parameters Research 2026-09-19/Deployment/OFFICIAL CALENDAR.json'
 old=read(archive);rows={(x['kind'],int(x['epoch'])):x for x in old['events']}
 assert old['from_date']<='2021-10-05' and old['to_exclusive']=='2026-09-05'
 fresh=read(R/'fresh-calendar-receipts.json')
 for indicator,kind in [('non_farm_payrolls','NFP'),('inflation','CPI'),('policy_rate','FOMC')]:
  q=fresh['series'][indicator];assert q['data_quality']['is_official'] and not q['data_quality']['has_assumed_release_times']
  for x in q['data']:
   assert x['release_date_confirmed'] and x['time_announced']
   ep=int(x['announcement_datetime']);assert datetime.fromisoformat(x['announcement_datetime_utc']).timestamp()==ep
   if ep<int(datetime(2026,9,5,tzinfo=timezone.utc).timestamp()):assert (kind,ep) in rows,'Archived/API overlap conflict'
   rows[(kind,ep)]={**x,'epoch':ep,'kind':kind}
 lo=int(datetime(2021,10,5,tzinfo=timezone.utc).timestamp());hi=int(datetime(2026,10,5,tzinfo=timezone.utc).timestamp())
 events=sorted((x for x in rows.values() if lo<=int(x['epoch'])<hi),key=lambda x:x['epoch'])
 assert events[-1]['epoch']==1790944200
 save(R/'calendar.json',dict(from_date='2021-10-05',to_exclusive='2026-10-05',events=events,counts=dict(Counter(x['kind'] for x in events)),archive_sha=sha(archive),fresh_sha=sha(R/'fresh-calendar-receipts.json'),macro_values_used=False,live_historical_schedule_availability_proven=False))
 epochs=','.join(str(x['epoch']) for x in events);kinds=','.join('"'+x['kind']+'"' for x in events)
 calendar=f'''#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20211005
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261005
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS {len(events)}
long NP_GENERATED_EVENT_UTC_EPOCHS[]={{{epochs}}};
string NP_GENERATED_EVENT_KINDS[]={{{kinds}}};
string NP_GeneratedCalendarProvider(){{return "Archived BLS/Fed plus fresh FXMacroData USD calendar";}}
string NP_GeneratedCalendarHash(){{return "{sha(R/'calendar.json')}";}}
int NP_GeneratedCalendarEventCount(){{return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}}
'''
 (snap/'NewsPulseTesterCalendar.mqh').write_text(calendar,encoding='utf-8')
 for name in ['AAA_Final_Common.mqh','SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:shutil.copy2(HELP/name,snap/name)
 shutil.copy2(B/'_Shared/CalyxAdaptivePortfolio.mqh',snap/'CalyxAdaptivePortfolio.mqh')
 shutil.copy2(S.parent/'NewsPulsePlacement.mqh',snap/'NewsPulsePlacement.mqh');shutil.copy2(R/'audit.mqh',snap/'audit.mqh')
 body=h.text(S).replace('\r\n','\n');body=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',body)
 body=body.replace('void NP_RecordBrokerQuote()','#include "audit.mqh"\n\nvoid NP_RecordBrokerQuote()',1)
 body=body.replace('int OnInit()\n{','int OnInit()\n{\n   if(!NR_Init())return INIT_FAILED;',1)
 body=body.replace('   const uint rc=AAA_Trade.ResultRetcode();','   const uint rc=AAA_Trade.ResultRetcode();\n      NR_Intent(comment,buy,entry,sl,tp,lots,side_risk,tick.bid,tick.ask,rc,market);',1)
 body=body.replace('void OnDeinit(const int reason)\n{','void OnDeinit(const int reason)\n{\n   NR_Close();',1)
 body=body.replace('double OnTester()','double NP_OriginalOnTester()',1)
 body=body.replace('   NP_Run();\n}','   NP_Run();\n   NR_Trace();\n}')
 body+='\ndouble OnTester(){NR_Export();return NP_OriginalOnTester();}\n'
 assert body.count('NR_Trace();')==2 and body.count('NR_Intent(comment,')==1
 source=snap/'NewsAudit.mq5';source.write_text(body,encoding='utf-8')
 frozen=fingerprint();fp=R/'FROZEN.json'
 if fp.exists():verify_frozen()
 else:save(fp,frozen)
 if (R/'BUILD.json').exists():
  build=read(R/'BUILD.json');assert build['source']==sha(source) and build['binary']==sha(source.with_suffix('.ex5'))
  assert sha(DEST/'NewsAudit.ex5')==build['binary'] and sha(DEST/'Original.ex5')==sha(S.with_suffix('.ex5'))
  status('REUSED verified frozen binaries; parser-only recovery, no new strategy build');return
 log=R/'compile.log';began=time.time()
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-5000:]
 assert source.with_suffix('.ex5').stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),DEST/'NewsAudit.ex5');shutil.copy2(S.with_suffix('.ex5'),DEST/'Original.ex5')
 save(R/'BUILD.json',dict(source=sha(source),binary=sha(source.with_suffix('.ex5')),frozen=frozen))
 status('COMPILED: zero errors/warnings; no production changes')
def csvrows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def metrics(trades,start,end,trace=None):
 vals=[x['net'] for x in trades];gain=sum(v for v in vals if v>0);loss=-sum(v for v in vals if v<0)
 w=l=mw=ml=0
 for v in vals:w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(mw,w);ml=max(ml,l)
 sharpe=None
 if trace:
  df=pd.DataFrame(trace);ser=pd.Series(df.equity.astype(float).to_numpy(),index=pd.to_datetime(df.epoch,format='%Y.%m.%d %H:%M:%S',utc=True))
  daily=ser.resample('D').last().ffill();ret=daily[daily.index.weekday<5].pct_change().dropna()
  if len(ret)>2 and ret.std(ddof=1)>0:sharpe=float(np.sqrt(252)*ret.mean()/ret.std(ddof=1))
 days=(datetime.strptime(end,'%Y.%m.%d')-datetime.strptime(start,'%Y.%m.%d')).days
 return dict(trades=len(vals),net_profit=round(sum(vals),2),return_pct=sum(vals)/100,pf=gain/loss if loss else None,win_rate=100*sum(v>0 for v in vals)/len(vals) if vals else None,win_streak=mw,loss_streak=ml,daily_equity_sharpe=sharpe,trades_month=len(vals)/(days/30.4375),trades_weekday=len(vals)/len(pd.bdate_range(start.replace('.','-'),(datetime.strptime(end,'%Y.%m.%d')-pd.Timedelta(days=1)).date())))
def run(case):
 tag,start,end,delay,original=case;out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 verify_frozen()
 if (out/'results.json').exists():return read(out/'results.json')
 free();settings={}
 for line in h.text(SET).splitlines():
  if '=' in line and not line.startswith(';'):k,v=line.split('=',1);settings[k]=v.split('||')[0]
 settings.update(InpTesterFromDateUTC=start.replace('.',''),InpTesterToDateUTC=end.replace('.',''),InpAdaptivePortfolioControls='false')
 if not original:settings['InpAuditTag']=tag
 body='\n'.join(k+'='+v for k,v in settings.items())+'\n';setname='npaudit20261005-'+tag+'.set'
 (out/'inputs.set').write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 name='Original' if original else 'NewsAudit';report=T/'reports/newsaudit20261005'/(tag+'.htm');report.parent.mkdir(parents=True,exist_ok=True)
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\NewsAudit20261005\\{name}
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode={delay}
Optimization=0
FromDate={start}
ToDate={end}
Report=reports\\newsaudit20261005\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 recovery=out/'PARSER RECOVERY.json'
 if recovery.exists():
  receipt=read(recovery);assert sha(out/'report.htm')==receipt['report_sha'] and sha(out/'journal.txt.gz')==receipt['journal_sha']
  assert sha(DEST/(name+'.ex5'))==receipt['binary_sha'];began=read(out/'owned-process.json')['started']
  report=out/'report.htm';journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
  status('REUSE completed native replay '+tag+'; report calculation only')
 else:
  offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+tag)
  proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
  save(out/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started=began))
  try:proc.wait(timeout=2700)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated replay timed out')
  journal=''
  for p in h.logfiles():
   if p.stat().st_mtime<began-2:continue
   with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
  (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
  assert proc.returncode==0 and report.exists() and report.stat().st_mtime>=began-2,'No successful fresh native report'
 assert not re.search('initialization failed|access violation|array out of range|zero divide|NR_AUDIT_FAILED|boundary violation=YES',journal,re.I),journal[-4000:]
 assert f'testing with execution delay {delay} milliseconds' in journal
 actual=h._report_inputs(report);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in settings.items()),'Settings mismatch'
 native=h._native_metrics(report)
 from app.mt5_evidence_jobs import _number,_metric
 native['equity_dd_pct']=_number(_metric(h._read_report(report),'Equity Drawdown Relative'))
 simple=h._native_trades(report,tag);save(out/'native-trade-legs.json',simple)
 if report.resolve()!=(out/'report.htm').resolve():shutil.copy2(report,out/'report.htm')
 (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 trace=[];trades=[];baskets=defaultdict(float);failures=[];ratios=[];lag=[];duplicate=Counter()
 if original:
  trades=[dict(net=x['net_profit']) for x in simple]
 else:
  for suffix in ['deals','intents','equity']:
   p=COMMON/(tag+'-'+suffix+'.csv');assert p.exists() and p.stat().st_mtime>=began-2;shutil.copy2(p,out/(suffix+'.csv'))
  deals=csvrows(out/'deals.csv');intents=csvrows(out/'intents.csv');trace=csvrows(out/'equity.csv')
  groups=defaultdict(list)
  for d in deals:
   for key in ['volume','price','gross','commission','swap','fee']:d[key]=float(d[key])
   groups[int(d['position_id'])].append(d)
  for pid,ds in groups.items():
   ins=[d for d in ds if int(d['entry'])==0];outs=[d for d in ds if int(d['entry'])==1]
   assert len(ins)==1 and outs and abs(ins[0]['volume']-sum(d['volume'] for d in outs))<1e-8
   entry=ins[0];parts=entry['comment'].split('|');assert len(parts)==4 and parts[0]=='NP'
   event=int(parts[1]);duplicate[(event,parts[3])]+=1
   accepted=[x for x in intents if x['comment']==entry['comment'] and int(x['retcode']) in (10008,10009,10010)]
   assert len(accepted)==1,'Entry lacks a unique accepted request'
   intent=accepted[0];actualrisk=abs(entry['price']-float(intent['sl']))*entry['volume']*100
   budget=float(intent['budget']);ratios.append(actualrisk/budget)
   net=sum(sum(d[k] for k in ['gross','commission','swap','fee']) for d in ds)
   closed=max(int(d['epoch']) for d in outs);late=closed-event-30;lag.append(late)
   if late>2*delay/1000+2:failures.append(f'{entry["comment"]}: exit late {late}s')
   trade=dict(position_id=pid,event=event,kind=parts[2],side=parts[3],open_epoch=int(entry['epoch']),close_epoch=closed,open_price=entry['price'],volume=entry['volume'],initial_sl=float(intent['sl']),net=round(net,2),actual_risk=actualrisk,budget=budget,exit_delay_after_deadline=late)
   trades.append(trade);baskets[event]+=net
  trades.sort(key=lambda x:(x['close_epoch'],x['position_id']))
  assert abs(sum(x['net'] for x in trades)-native['net_profit'])<.021
  assert len(trades)==native['trades']==len(simple)
  # Independent native HTML versus complete exported deal-row audit.
  spec=importlib.util.spec_from_file_location('deal_reconciliation',B/'Trend Progression Optimization 2026-10-05/native.py')
  dm=importlib.util.module_from_spec(spec);spec.loader.exec_module(dm);assert dm.native_deal_audit(report,deals)['all_exported_deals_match_native_report']
  assert max(duplicate.values(),default=0)<=1,'Repeated side/event'
  exposure=re.findall(r'NR_EXPOSURE pending=(\d+) positions=(\d+)',journal);assert exposure and exposure[-1]==('0','0')
 audit=re.findall(r'calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(\w+)',journal);assert audit
 expected,attempted,complete=map(int,audit[-1][:3]);assert audit[-1][3]=='NO'
 if expected!=attempted or expected!=complete:failures.append(f'Incomplete event setup coverage {complete}/{expected}, attempted {attempted}')
 if re.search('stop out|margin call',journal,re.I):failures.append('Margin/stopout observed')
 errors=dict(rejected=journal.count('NP_SIDE_REJECTED|'),uncertain=journal.count('NP_SIDE_UNCERTAIN|'),incomplete_attempts=journal.count('NP_SETUP_INCOMPLETE|'),modify_failed=journal.count('trailing-stop update failed'),close_failed=journal.count('could not close position'),delete_failed=journal.count('could not delete pending order'),fallbacks=journal.count('NP_MARKET_FALLBACK|'))
 if any(errors[k] for k in ['uncertain','modify_failed','close_failed','delete_failed']):failures.append('Execution errors: '+json.dumps(errors))
 m=metrics(trades,start,end,trace);assert abs(m['net_profit']-native['net_profit'])<.021
 result=dict(case=tag,window=[start,end],delay_ms=delay,original=original,native=native,metrics=m,errors=errors,event_audit=dict(expected=expected,attempted=attempted,complete=complete),event_basket_metrics=metrics([dict(net=baskets[e]) for e in sorted(baskets)],start,end) if baskets else None,both_sides_filled_events=sum(sum(k[0]==e for k in duplicate)==2 for e in baskets),max_actual_risk_budget_ratio=max(ratios,default=None),latest_exit_seconds_after_deadline=max(lag,default=None),qualification_failures=failures,report_sha=sha(report),binary_sha=sha(DEST/(name+'.ex5')),tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:20])
 save(out/'trades.json',trades);save(out/'results.json',result);status('DONE '+tag+' '+json.dumps(dict(**m,dd=native['equity_dd_pct'],quality=native['history_quality'],failures=failures)))
 return result
def main():
 prepare();results=[]
 for case in CASES:
  results.append(run(case));save(R/'RESULTS.json',results)
  if case[0]=='PARITY-AUDIT':
   aa=read(R/'native/PARITY-ORIGINAL/native-trade-legs.json');bb=read(R/'native/PARITY-AUDIT/native-trade-legs.json')
   for records in [aa,bb]:
    for x in records:x.pop('id',None);x.pop('ea',None)
   assert aa==bb,'Shipped binary/audit clone parity failed'
   save(R/'PARITY.json',dict(passed=True,positions=len(aa),entry_exit_prices_times_lots_costs_equal=True))
 verify_frozen()
 status('COMPLETE exact-current news audit; no optimisation or production changes')
if __name__=='__main__':
 with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);main()
