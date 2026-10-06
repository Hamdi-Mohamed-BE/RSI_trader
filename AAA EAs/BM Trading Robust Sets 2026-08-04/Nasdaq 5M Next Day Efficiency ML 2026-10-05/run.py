"""Past-only gate vs current BAT EA in isolated native MT5."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('er_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER
SOURCE=R/'EA/Nasdaq Efficiency Research.mq5'
ORIGINAL=B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5'
BASE=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxNasdaqER20261005'
WINDOWS={'3M':'2026.07.05','6M':'2026.04.05','2Y':'2024.10.05'}
END='2026.10.05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def freeze():
 v=dict(windows=WINDOWS,end_exclusive=END,production={str(p.relative_to(B)):sha(p) for p in [BASE,ORIGINAL,B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5',B/'_Auto Deploy/Install-BMTradingPortfolio.ps1']},
  research={p.name:sha(p) for p in sorted((R/'EA').glob('*.mq*'))},model=sha(R/'MODEL.json'),protocol=sha(R/'PROTOCOL.md'))
 path=R/'native-frozen.json'
 if path.exists():assert json.loads(path.read_text())==v
 else:save(path,v)
 return v
def compile_ea():
 h.free();log=R/'compile.log';began=time.time()
 subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 body=h.text(log);assert '0 errors, 0 warnings' in body,body[-9000:]
 assert SOURCE.with_suffix('.ex5').stat().st_mtime>=began-2
 save(R/'build.json',dict(binary=sha(SOURCE.with_suffix('.ex5')),compiler_tail=body[-600:],frozen=freeze()))
 print('COMPILED zero errors/warnings',flush=True)
def streaks(pnl):
 w=l=mw=ml=0
 for v in pnl:
  w=w+1 if v>0 else 0;l=l+1 if v<0 else 0;mw=max(w,mw);ml=max(l,ml)
 return mw,ml
def metrics(trades,trace):
 vals=[t['net_profit'] for t in trades];wins=[x for x in vals if x>0];losses=[x for x in vals if x<0];mw,ml=streaks(vals)
 daily_sharpe=None
 if trace:
  df=pd.DataFrame(trace);tm=pd.to_datetime(df.epoch.astype('int64'),unit='s',utc=True)
  eq=pd.Series(df.equity.astype(float).values,index=tm).resample('D').last().ffill()
  eq=eq[eq.index.weekday<5];ret=eq.pct_change().dropna()
  if len(ret)>2 and ret.std(ddof=1)>0:daily_sharpe=float(np.sqrt(252)*ret.mean()/ret.std(ddof=1))
 return dict(trades=len(vals),return_pct=sum(vals)/100,net_profit=sum(vals),net_pf=sum(wins)/-sum(losses) if losses else None,
  win_rate_pct=100*len(wins)/len(vals) if vals else None,max_win_streak=mw,max_loss_streak=ml,
  avg_win=np.mean(wins).item() if wins else None,avg_loss=np.mean(losses).item() if losses else None,expectancy=np.mean(vals).item() if vals else None,
  daily_equity_sharpe=daily_sharpe)
def csvrows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def native_deal_audit(rp,deals):
 from app.mt5_evidence_jobs import _clean,_number
 text=h._read_report(rp);marker=text.lower().find('<b>deals</b>');native={}
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text[marker:],re.I|re.S):
  c=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
  if len(c)<13 or c[3].lower() not in ['buy','sell']:continue
  native[int(c[1])]=dict(epoch=int(datetime.strptime(c[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()),
   entry=0 if c[4]=='in' else 1,type=0 if c[3]=='buy' else 1,volume=_number(c[5]),price=_number(c[6]),commission=_number(c[8]),swap=_number(c[9]),gross=_number(c[10]))
 assert set(native)=={int(d['deal']) for d in deals}
 for d in deals:
  for k,v in native[int(d['deal'])].items():assert abs(v-float(d[k]))<1e-7,(d['deal'],k,v,d[k])
  assert abs(float(d['fee']))<1e-9
 return len(deals)
def run(window,mode,original=False):
 tag=window+('_ORIGINAL' if original else ['_BASE','_ML','_LAG'][mode])
 out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 if (out/'results.json').exists():return json.loads((out/'results.json').read_text())
 build=json.loads((R/'build.json').read_text());assert freeze()==build['frozen'];assert sha(SOURCE.with_suffix('.ex5'))==build['binary']
 vals=dict(l.split('=',1) for l in BASE.read_text(encoding='utf-8-sig').splitlines() if '=' in l and not l.startswith(';'))
 vals['InpAdaptivePortfolioControls']='false'
 assert vals['InpRiskPercent']=='1.0' and vals['InpRequireDIAgreement']=='true'
 if not original:vals.update(InpERMode=str(mode),InpERTag=tag)
 dest=T/'MQL5/Experts/AAA Research/NasdaqER20261005';dest.mkdir(parents=True,exist_ok=True)
 name='Original' if original else 'Efficiency';binfile=ORIGINAL if original else SOURCE.with_suffix('.ex5')
 shutil.copy2(binfile,dest/(name+'.ex5'))
 setname='nasdaqer-'+tag+'.set';body='\n'.join(k+'='+v for k,v in vals.items())+'\n'
 (out/'inputs.set').write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 start=WINDOWS[window];rp=T/'reports/nasdaqer20261005'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\NasdaqER20261005\\{name}
ExpertParameters={setname}
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start}
ToDate={END}
ForwardMode=0
Report=reports\\nasdaqer20261005\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 save(out/'manifest.json',dict(window=window,start=start,end_exclusive=END,mode=mode,original=original,inputs=vals,binary=sha(binfile),frozen=build['frozen']))
 h.free();profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();print('START '+tag,flush=True)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,started=began,path=str(T/'terminal64.exe')))
 try:proc.wait(timeout=1800)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Only owned isolated tester timed out')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report'
 assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|N5EMA order rejected|ER_FORECAST_MISSING|ER_EXPORT_DEALS_FAILED',journal,re.I),journal[-6000:]
 rb=h._read_report(rp);assert all(s in rb for s in [start,END,'USTEC','M5'])
 actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in vals.items()),'SET mismatch'
 assert 'testing with execution delay 150 milliseconds' in journal
 native=h._native_metrics(rp)
 from app.mt5_evidence_jobs import _metric,_number
 native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 native['balance_dd_pct']=_number(_metric(rb,'Balance Drawdown Relative'))
 trades=h._native_trades(rp,tag);assert len(trades)==native['trades'];assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.021
 forecast=pd.read_csv(R/'forecasts.csv');forecast['date_key']=pd.to_datetime(forecast.date).dt.strftime('%Y%m%d').astype(int);forecasts=forecast.set_index('date_key')
 for t in trades:
  op=pd.Timestamp(t['open_time'],tz='UTC');cl=pd.Timestamp(t['close_time'],tz='UTC');ny=op.tz_convert('America/New_York')
  assert ny.strftime('%H:%M')=='09:35'
  t.update(open_ny=str(ny),hold_hours=(cl-op).total_seconds()/3600,boundary_exit='end of test' in t['exit_comment'].lower())
  key=int(ny.strftime('%Y%m%d'));f=forecasts.loc[key];assert f.available<op.timestamp()
  t.update(probability=float(f.probability),ml_allow=bool(f.ml_allow),lag_er_allow=bool(f.lag_er_allow),predicted_high=bool(f.ml_allow))
  if mode==1:assert t['ml_allow']
  if mode==2:assert t['lag_er_allow']
 trace=[];gates=[];deal_check=None;observed_dd=None
 if not original:
  for kind in ['gates','equity','deals']:
   path=COMMON/(tag+'-'+kind+'.csv');assert path.exists() and path.stat().st_mtime>=began-2;shutil.copy2(path,out/(kind+'.csv'))
  trace=csvrows(out/'equity.csv');gates=csvrows(out/'gates.csv');deals=csvrows(out/'deals.csv')
  deal_check=native_deal_audit(rp,deals)
  for g in gates:
   f=forecasts.loc[int(g['date_key'])]
   assert int(g['available'])<int(g['epoch']) and abs(float(g['probability'])-f.probability)<1e-10
   expected=1 if mode==0 else int(f.ml_allow if mode==1 else f.lag_er_allow)
   assert int(g['allow'])==expected
  m=re.findall(r'ER_SUMMARY candidates=(\d+) blocked=(\d+) missing=(\d+) observed_dd=([\d.]+)',journal);assert m
  candidates,blocked,missing,observed_dd=map(float,m[-1]);assert candidates==len(gates) and missing==0 and blocked==sum(int(g['allow'])==0 for g in gates)
 else:candidates=blocked=None
 metrics_out=metrics(trades,trace)
 for x in ['equity_dd_pct','balance_dd_pct','sharpe_ratio','history_quality']:metrics_out[x]=native[x]
 result=dict(tag=tag,start=start,end_exclusive=END,mode=mode,original=original,native=native,metrics=metrics_out,
  counters=dict(candidates=candidates,blocked=blocked,observed_dd=observed_dd,deal_rows_audited=deal_check,stop_modify_failures=journal.count('N5EMA stop modification failed')),
  end_liquidations=sum(t['boundary_exit'] for t in trades),commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),
  seconds=time.time()-began,tick_notes=sorted(set(x for x in journal.splitlines() if re.search('real ticks begin|real ticks absent|ticks discarded',x,re.I)))[:30],
  report_sha256=sha(rp),trades=trades)
 save(out/'trades.json',trades);pd.DataFrame(trades).to_csv(out/'trades.csv',index=False)
 shutil.copy2(rp,out/'report.htm');save(out/'results.json',result)
 print('DONE '+tag+' '+json.dumps(metrics_out),flush=True)
 return result
def parity():
 a=run('3M',0,True);b=run('3M',0)
 def cleaned(t):return {k:v for k,v in t.items() if k not in ['label','ea']}
 assert len(a['trades'])==len(b['trades'])
 assert [cleaned(t) for t in a['trades']]==[cleaned(t) for t in b['trades']], 'Off-switch changed trades'
 assert a['native']==b['native'], 'Off-switch changed native metrics'
 save(R/'PARITY.json',dict(exact=True,positions=len(a['trades']),native_metrics_exact=True))
 return a,b
if __name__=='__main__':
 action=sys.argv[1]
 if action=='compile':compile_ea()
 elif action=='parity':parity()
 elif action=='case':run(sys.argv[2],int(sys.argv[3]))
 elif action=='all':
  parity()
  for w in WINDOWS:
   for m in [0,1,2]:run(w,m)
  save(R/'RESULTS.json',[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))])
  print('ALL COMPLETE; no production changes',flush=True)
