"""Thirty frozen filter variants plus five original/copy parity controls. No live API."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,io,json,os,re,shutil,subprocess,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sp=importlib.util.spec_from_file_location('native_helper',B/'FTMO Exit Management Research 2026-09-27/run.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
T=h.TESTER;DEST=T/'MQL5/Experts/AAA Research/ADXDI20261003';OUT=R/'native'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
START='2025.10.02';END='2026.10.02'
VARIANTS={'BASE':(0,False),'DI_ONLY':(0,True),'ADX20':(20,False),'ADX25':(25,False),'ADX20_DI':(20,True),'ADX25_DI':(25,True)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def status(s):save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=s));print(s,flush=True)
def compile_all(bots):
 h.free();build={}
 for key,b in bots.items():
  folder=R/'EA'/key;src=folder/'Research.mq5';log=folder/'compile.log';began=time.time()
  subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
  assert '0 errors, 0 warnings' in h.text(log),h.text(log)[-2500:]
  assert src.with_suffix('.ex5').stat().st_mtime>=began-2
  target=DEST/key;target.mkdir(parents=True,exist_ok=True)
  shutil.copy2(src.with_suffix('.ex5'),target/'Research.ex5');shutil.copy2(b['original'],target/'Original.ex5')
  build[key]=dict(source_sha=sha(src),binary_sha=sha(src.with_suffix('.ex5')),original_sha=sha(Path(b['original'])),helpers={p.name:sha(p) for p in folder.glob('*.mqh')},compile_tail=h.text(log)[-350:])
  assert build[key]['original_sha']==b['original_sha']
  status('COMPILED '+key+': 0 errors, 0 warnings')
 save(R/'BUILD.json',build)
def streaks(v):
 groups=[];sign=None;n=0
 for x in v:
  sg=int(np.sign(x))
  if sg==sign:n+=1
  else:
   if sign is not None:groups.append((sign,n))
   sign=sg;n=1
 if sign is not None:groups.append((sign,n))
 return dict(max_win_streak=max((n for s,n in groups if s>0),default=0),max_loss_streak=max((n for s,n in groups if s<0),default=0))
def stats(trades,native):
 v=np.array([x['net_profit'] for x in trades]);gp=v[v>0].sum();gl=-v[v<0].sum()
 daily=pd.Series([x['net_profit'] for x in trades],index=[x['close_time'][:10] for x in trades],dtype=float).groupby(level=0).sum()
 cal=pd.date_range(START.replace('.','-'),pd.Timestamp(END.replace('.','-'))-pd.Timedelta(days=1));daily=daily.reindex(cal.strftime('%Y-%m-%d'),fill_value=0).to_numpy()
 balance=10000+np.cumsum(daily);opening=np.r_[10000,balance[:-1]];returns=np.divide(daily,opening,out=np.zeros_like(daily),where=opening>0);sd=returns.std(ddof=1)
 bal=np.r_[10000,10000+np.cumsum(v)];peak=np.maximum.accumulate(bal)
 return dict(return_pct=float(v.sum()/100),net=float(v.sum()),pf=float(gp/gl) if gl else None,win_pct=float((v>0).mean()*100) if len(v) else 0,equity_dd_pct=native['equity_dd_pct'],closed_dd_pct=float(np.max((peak-bal)/peak)*100),trades=len(v),trades_month=len(v)/(len(cal)/365.2425*12),trades_weekday=len(v)/sum(cal.dayofweek<5),sharpe=float(returns.mean()/sd*np.sqrt(365.2425)) if sd else None,commission=float(sum(x['commission'] for x in trades)),swap=float(sum(x['swap'] for x in trades)),history_quality=native['history_quality'],**streaks(v))
def case(key,b,variant,original=False):
 tag=key+'-'+('ORIGINAL' if original else variant);folder=OUT/tag;folder.mkdir(parents=True,exist_ok=True)
 level,di=VARIANTS[variant];inputs=dict(b['inputs'])
 if not original:inputs.update(InpStudyADXGate=str(b['gate'] if level else 0),InpStudyADXLevel=str(level or 20),InpStudyDI=str(di).lower(),InpStudyTF=str(b['tf']),InpStudyTag=tag)
 expert='Original' if original else 'Research'
 frozen=dict(tag=tag,inputs=inputs,symbol=b['symbol'],period=b['period'],start=START,end=END,deposit=10000,model=4,delay_ms=150,original=original,protocol_sha=sha(R/'PROTOCOL.txt'),build=load(R/'BUILD.json')[key])
 if (folder/'manifest.json').exists():assert load(folder/'manifest.json')==frozen,'Frozen config changed'
 else:save(folder/'manifest.json',frozen)
 if (folder/'result.json').exists():return load(folder/'result.json')
 h.free();setname='adxdistudy-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in inputs.items())+'\n'
 (folder/setname).write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 rp=T/'reports/adxdi20261003'/f'{tag}.htm';rp.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ADXDI20261003\\{key}\\{expert}
ExpertParameters={setname}
Symbol={b['symbol']}
Period={b['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
Report=reports\\adxdi20261003\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+tag)
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
 save(R/'owned-process.json',dict(pid=proc.pid,key=tag,executable=str(T/'terminal64.exe')))
 try:proc.wait(timeout=3600)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated case timed out: '+tag)
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')
 (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'No fresh report '+tag
 lines=journal.splitlines();fatal_re=re.compile(r'initialization failed|start time changed|invalid volume|stop out|margin call|access violation|array out of range|zero divide|order rejected',re.I)
 fatal=[l for l in lines if fatal_re.search(l)];assert not fatal,'Invalid run; inspect journal '+tag
 rb=h._read_report(rp);assert all(x in rb for x in (b['symbol'],b['period'],START,END))
 actual=h._report_inputs(rp);mismatch=[k for k,v in inputs.items() if k not in actual or not h._same_setting(v,actual[k])];assert not mismatch,(tag,mismatch)
 from app.mt5_evidence_jobs import _metric,_number
 native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
 trades=h._native_trades(rp,tag);assert len(trades)==native['trades'];assert abs(sum(x['net_profit'] for x in trades)-native['net_profit'])<.2
 audit_stats={}
 if not original:
  p=COMMON/f'ADXDI20261003-{tag}.csv';assert p.exists() and p.stat().st_mtime>=began-2
  raw=p.read_bytes();audit=pd.read_csv(io.BytesIO(raw));g=audit[audit.event=='gate'];e=audit[audit.event=='entry']
  assert (e.retcode==10009).all(),('Entry failures',tag,e[e.retcode!=10009].to_dict('records'))
  assert len(e)==len(trades),(tag,len(e),len(trades))
  assert len(e)==int(g.allowed.sum()),('Admission/order mismatch',tag)
  valid=g[g.valid==1];assert (valid.epoch>=valid.bar_epoch+valid.tf_seconds).all()
  if variant!='BASE':
   permitted=g[g.allowed==1];assert (permitted.valid==1).all()
   if level:assert ((permitted.adx>=level) if b['gate']==1 else (permitted.adx<=level)).all()
   if di:assert (((permitted.direction>0)&(permitted.plus_di>permitted.minus_di))|((permitted.direction<0)&(permitted.minus_di>permitted.plus_di))).all()
  audit_stats=dict(candidates=len(g),admitted=int(g.allowed.sum()),rejected=int((g.allowed==0).sum()),missing_indicator=int((g.valid==0).sum()))
  (folder/'audit.csv.gz').write_bytes(gzip.compress(raw,mtime=0))
 (folder/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0));(folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
 tick_re=re.compile(r'real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded',re.I)
 result=dict(tag=tag,ea=key,label=b['label'],variant=variant,original=original,stats=stats(trades,native),native=native,audit=audit_stats,seconds=time.time()-began,tick_notes=sorted(set(l for l in lines if tick_re.search(l)))[:20],known_stop_modify_rejections=journal.count('stop modification failed'),report_sha=sha(rp))
 save(folder/'result.json',result);status('DONE '+tag+' '+json.dumps(result['stats']));return result
def parity(a,b):
 def ledger(tag):return json.loads(gzip.decompress((OUT/tag/'trades.json.gz').read_bytes()))
 x=ledger(a['tag']);y=ledger(b['tag']);fields=['open_time','close_time','side','volume','open_price','close_price','commission','swap','net_profit']
 assert len(x)==len(y) and all(all(i[k]==j[k] for k in fields) for i,j in zip(x,y)),('Parity failed',a['tag'])
 return dict(trades=len(x),identical_entry_exit_volume_costs=True,fields=fields)
def main():
 bots=load(R/'bots.json');frozen=dict(bots=bots,variants=VARIANTS,start=START,end=END,protocol_sha=sha(R/'PROTOCOL.txt'),filter_sha=sha(R/'EA/StudyFilter.mqh'))
 frozen=json.loads(json.dumps(frozen))
 if (R/'run-config.json').exists():assert load(R/'run-config.json')==frozen
 else:save(R/'run-config.json',frozen)
 if not (R/'BUILD.json').exists():compile_all(bots)
 else:
  build=load(R/'BUILD.json')
  for key,b in bots.items():
   assert sha(R/'EA'/key/'Research.mq5')==build[key]['source_sha'] and sha(Path(b['original']))==b['original_sha']
   assert {p.name:sha(p) for p in (R/'EA'/key).glob('*.mqh')}==build[key]['helpers']
 results=[];parities={}
 for key,b in bots.items():
  original=case(key,b,'BASE',True);base=case(key,b,'BASE');parities[key]=parity(original,base);save(R/'PARITY.json',parities);status('PARITY '+key+': '+str(base['stats']['trades'])+' identical trades')
  results.append(base)
  for v in VARIANTS:
   if v!='BASE':results.append(case(key,b,v))
   save(R/'PROGRESS.json',results)
 save(R/'SUMMARY.json',results);status('COMPLETE 30 comparisons + 5 parity controls; no deployment')
if __name__=='__main__':main()
