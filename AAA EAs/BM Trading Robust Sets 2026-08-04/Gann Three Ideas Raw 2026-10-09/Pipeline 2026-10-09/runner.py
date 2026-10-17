"""Batched exhaustive case-index screening; exact native ledgers and frozen manifests."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,math,msvcrt,os,re,shutil,subprocess,time,xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import raw_runner as rr
import search_plan as sp
import build_engine
R=rr.R;RAW=rr.RAW;B=rr.B;n=rr.n;T=n.T;h=n.h;CFG=rr.CFG
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGannPipeline20261009'
def load(p):return n.read(p)
def save(p,v):return n.save(p,v)
def safe(v):return n.safe(v)
def sha(p):return n.sha(p)
def status(message,**kw):n.status(message,**kw)
def lease():
 f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);n.available();return f
def digest(x):return sp.digest(x)
def dedupe(x):return sp.dedupe(x)

def native_xml(p,count):
 ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};head=None;results={}
 for row in ET.parse(p).getroot().findall('.//s:Row',ns):
  vals=[]
  for cell in row.findall('s:Cell',ns):
   index=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
   if index:
    while len(vals)<int(index)-1:vals.append('')
   d=cell.find('s:Data',ns);vals.append(''.join(d.itertext()) if d is not None else '')
  if 'Pass' in vals and 'InpCase' in vals:head=vals;continue
  if head and len(vals)==len(head):
   d=dict(zip(head,vals))
   if d.get('InpCase','').isdigit():results[int(d['InpCase'])]=float(d['Profit'].replace(' ',''))
 assert sorted(results)==list(range(count)),('Incomplete optimization export',count,len(results))
 return results

def wrapper(cases,bot):
 table='double C[][23]={\n'+',\n'.join('{'+','.join(repr(float(c[f])) for f in sp.FIELDS)+'}' for c in cases)+'\n};\n'
 prefix='input int InpCase=0;input int InpBot='+str(sp.IDEA[bot])+';input string InpTag="";input double InpRiskPct=1;\n'
 code=table+prefix+'#define OnInit BaseInit\n#define OnTick BaseTick\n#define OnDeinit BaseDeinit\n#include "Logic.mqh"\n#undef OnInit\n#undef OnTick\n#undef OnDeinit\n'
 audit=(R/'ReadOnlyAudit.mqh').read_text().replace('input string InpRR05AuditTag','string InpRR05AuditTag').replace('CalyxRR05All20261008','CalyxGannPipeline20261009')
 audit=audit.replace('now/300==rr05_last_trace/300','now/(MQLInfoInteger(MQL_OPTIMIZATION)?86400:300)==rr05_last_trace/(MQLInfoInteger(MQL_OPTIMIZATION)?86400:300)')
 code+=audit
 code+='''
int quotes_file=INVALID_HANDLE;
int OnInit(){if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(C,0))return INIT_FAILED;LoadCase();int v=BaseInit();if(v!=INIT_SUCCEEDED)return v;InpRR05AuditTag=InpSignalAuditTag;if(!RR05AuditInit())return INIT_FAILED;
 quotes_file=FileOpen(RR05Path("quotes"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(quotes_file==INVALID_HANDLE)return INIT_FAILED;FileWrite(quotes_file,"deal","position_id","epoch","bid","ask","volume","price");RR05Observe();return INIT_SUCCEEDED;}
void OnTick(){RR05Observe();BaseTick();RR05Observe();}
void OnTradeTransaction(const MqlTradeTransaction &t,const MqlTradeRequest &request,const MqlTradeResult &result){if(t.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(t.deal))return;long type=HistoryDealGetInteger(t.deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)return;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;FileWrite(quotes_file,t.deal,HistoryDealGetInteger(t.deal,DEAL_POSITION_ID),HistoryDealGetInteger(t.deal,DEAL_TIME),DoubleToString(q.bid,8),DoubleToString(q.ask,8),DoubleToString(HistoryDealGetDouble(t.deal,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(t.deal,DEAL_PRICE),8));}
double OnTester(){int f=FileOpen(RR05Path("stats"),FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)return -1e10;
 FileWrite(f,"net","balance","equity_dd_pct","balance_dd_pct","open_positions","rejected","invalid_geometry","undersize","placed");
 FileWrite(f,DoubleToString(TesterStatistics(STAT_PROFIT),2),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(TesterStatistics(STAT_EQUITY_DDREL_PERCENT),8),DoubleToString(TesterStatistics(STAT_BALANCE_DDREL_PERCENT),8),PositionsTotal(),rejected,invalid_geometry,undersize,placed);FileClose(f);return TesterStatistics(STAT_PROFIT);}
void OnDeinit(const int reason){RR05Observe();BaseDeinit(reason);RR05Finish();if(quotes_file!=INVALID_HANDLE)FileClose(quotes_file);}
'''
 return code

def validate_signals(result,folder,stem,parameters):
 signals=n.export_rows(folder/(stem+'-signals.csv'));trades=sorted(result['trades'],key=lambda t:t['open_epoch'])
 assert len(signals)==len(trades),(len(signals),len(trades))
 balance=10000
 for s,t in zip(signals,trades):
  assert int(s['signal_start_epoch'])<int(s['signal_close_epoch'])<=t['open_epoch']
  assert int(s['feature_known_epoch'])<=int(s['signal_close_epoch'])
  assert not int(s['anchor_epoch']) or int(s['anchor_epoch'])<int(s['feature_known_epoch'])
  assert abs(float(s['requested_risk_usd'])-balance*result['risk']/100)<.011
  assert float(s['lots'])==t['volume']
  assert abs(float(s['stop'])-t['sl'])<1e-7 and abs(float(s['target'])-t['tp'])<1e-7
  balance+=t['net']
 result['signal_audit_verified']=True;result['signals']=signals

def batch(name,cases,bot,start,end,model=1,optimize=True,risk=1,idea=None,delay=150):
 n.available();out=R/'native'/name;out.mkdir(parents=True,exist_ok=True)
 logic=build_engine.build();code=wrapper(cases,bot)
 manifest=dict(name=name,cases=cases,bot=bot,start=start,end_exclusive=end,model=model,optimize=optimize,risk=risk,delay_ms=delay,
  idea=sp.IDEA[bot] if idea is None else idea,engine_sha=hashlib.sha256(logic.encode()).hexdigest(),wrapper_sha=hashlib.sha256(code.encode()).hexdigest(),plan_sha=sha(R/'SEARCH PLAN.json'))
 p=out/'manifest.json'
 if p.exists():
  assert load(p)==manifest,'Frozen batch changed '+name
  if (out/'results.json').exists():return load(out/'results.json')
 else:save(p,manifest)
 assert optimize or len(cases)==1
 source=out/'GannSearch.mq5';source.write_text(code,encoding='utf-8');(out/'Logic.mqh').write_text(logic,encoding='utf-8')
 began=time.time();log=out/'compile.log';subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 txt=h.text(log);assert '0 errors, 0 warnings' in txt,txt[-6000:]
 binary=source.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
 dest=T/'MQL5/Experts/AAA Research/GannPipeline20261009';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(binary,dest/'GannSearch.ex5')
 tag='gp-'+name+'-'+digest(manifest)[:8];setname=tag+'.set'
 vals=dict(InpCase=f'0||0||1||{len(cases)-1}||Y' if optimize else '0',InpBot=str(manifest['idea']),InpTag=tag,InpRiskPct=str(risk))
 body='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n';(out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
 ext='.xml' if optimize else '.htm';rp=T/'reports/gann-pipeline-20261009'/(tag+ext);rp.parent.mkdir(parents=True,exist_ok=True)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 a=start.replace('-','.');b=end.replace('-','.')
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port=3010
Expert=AAA Research\\GannPipeline20261009\\GannSearch
ExpertParameters={setname}
Symbol={sp.SYMBOL[bot]}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={delay}
Optimization={1 if optimize else 0}
OptimizationCriterion=6
FromDate={a}
ToDate={b}
ForwardMode=0
Report=reports\\gann-pipeline-20261009\\{tag+ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();n.available();status('START '+name,cases=len(cases),model=model)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,started=began,terminal=str(T)))
 try:proc.wait(timeout=14400)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated tester timeout; unrelated processes untouched')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.is_file() and rp.stat().st_mtime>=began-2,'No fresh native report'
 assert not re.search(r'initialization failed|start time changed|not enough history|access violation|array out of range|zero divide|some error after pass finished|stop out',journal,re.I),'Native fatal/history failure'
 profits=native_xml(rp,len(cases)) if optimize else {0:h._native_metrics(rp)['net_profit']}
 (out/('report'+ext+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
 if not optimize:
  actual=h._report_inputs(rp);assert all(h._same_setting(str(v),actual.get(k,'')) for k,v in vals.items())
  txt=h._read_report(rp);assert a in txt and b in txt and sp.SYMBOL[bot] in txt
 records=[]
 for index,parameters in enumerate(cases):
  stem=tag+'-'+str(index)
  for suffix in ['deals','equity','quotes','stats']:
   p=COMMON/(stem+'-'+suffix+'.csv');assert p.exists() and p.stat().st_mtime>=began-2,('Missing pass export',suffix,index)
   shutil.copy2(p,out/(str(index)+'-'+suffix+'.csv'))
  p=COMMON/(stem+'.csv');assert p.is_file() and p.stat().st_mtime>=began-2;shutil.copy2(p,out/(str(index)+'-signals.csv'))
  deals=n.export_rows(out/(str(index)+'-deals.csv'));trades,cash=n.trades_from_deals(deals)
  native=pd.read_csv(out/(str(index)+'-stats.csv')).iloc[0].to_dict()
  assert abs(sum(t['net'] for t in trades)-profits[index])<.031
  assert abs(native['net']-profits[index])<.031
  assert all(pd.Timestamp(start,tz='UTC').timestamp()<=t['open_epoch']<=t['close_epoch']<pd.Timestamp(end,tz='UTC').timestamp() for t in trades)
  native['history_quality']='Screening Model1; M1OHLC' if optimize else h._native_metrics(rp)['history_quality']
  m=n.metrics(trades,n.export_rows(out/(str(index)+'-equity.csv')),native)
  eq=pd.read_csv(out/(str(index)+'-equity.csv'))
  daily=pd.Series(eq.equity.to_numpy(),index=pd.to_datetime(eq.epoch,unit='s',utc=True)).resample('D').last()
  days_index=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1),tz='UTC')
  daily=daily.reindex(days_index).ffill().fillna(10000)
  if bot!='btc':daily=daily[daily.index.weekday<5]
  returns=daily.pct_change();returns.iloc[0]=daily.iloc[0]/10000-1
  m['sharpe_daily_equity']=float(returns.mean()/returns.std(ddof=1)*np.sqrt(365 if bot=='btc' else 252)) if returns.std(ddof=1)>0 else None
  if optimize:m['sharpe_daily_equity']=None # daily-first-tick screening trace is not closing equity
  days=(pd.Timestamp(end)-pd.Timestamp(start)).days
  m['trades_per_month']=len(trades)/(days/30.436875)
  m['trades_per_market_day']=len(trades)/(days if bot=='btc' else len(pd.bdate_range(start,pd.Timestamp(end)-pd.Timedelta(days=1))))
  q=dict(index=index,parameters=parameters,bot=bot,start=start,end=end,model=model,risk=risk,metrics=m,native=native,
   trades=trades,ledger=cash,stage=name,tag=tag,report_sha=sha(rp),binary_sha=sha(binary),clean=native['open_positions']==0,
   end_liquidations=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in trades),
   tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:20])
  validate_signals(q,out,str(index),parameters)
  q['clean']=q['clean'] and q['end_liquidations']==0
  records.append(q)
 save(out/'results.json',records);status('DONE '+name,cases=len(cases),seconds=round(time.time()-began,1));return records

def score(q,minimum=30):
 m=q['metrics'];pf=m['pf'] or 0
 if not q['clean']:return -1e6
 if m['trades']<minimum:return -1000+m['trades']/100
 if m['net_profit']<=0:return -1-abs(m['net_profit'])/10000-m['equity_dd_pct']/100
 return (pf-1)*math.sqrt(m['trades'])/(1+m['equity_dd_pct']/10)
def slim(q):return {k:v for k,v in q.items() if k not in ['trades','signals','ledger']}
