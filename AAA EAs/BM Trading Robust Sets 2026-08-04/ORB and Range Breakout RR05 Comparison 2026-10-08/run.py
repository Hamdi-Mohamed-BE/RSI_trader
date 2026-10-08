"""Current-catalogue TP-only tests; isolated tester, no deployment or live-account API."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, html, importlib.util, json, math, msvcrt, os, re, shutil, subprocess, sys, time
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(B.parent/'EA store'))
from app.catalog import get_website_catalog
from app.mt5_evidence_jobs import _metric, _number
spec=importlib.util.spec_from_file_location('rr05_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);T=h.TESTER
START='2025.10.06';END='2026.10.06';PORT=3010
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxRR05All20261008'
PRIOR=B/'US100 H1 ORB RR05 Comparison 2026-10-08/Agent3010'
SLUGS=['us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3',
 'orb-volume-profile','orb-volume-profile-volume-confirmed','xau-orb-new-york-m30',
 'xau-orb-london-ny-overlap-m30','asia-breakout','ema3','xau-weakness',
 'xau-squeeze-momentum-standard','gold-overnight-value-area','sell-nasdaq-15min',
 'xau-elliott-wave-1-2-3','3-way-gold']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def safe(v):
 if isinstance(v,np.generic):v=v.item()
 if isinstance(v,float) and not math.isfinite(v):return None
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [safe(x) for x in v]
 return v
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(safe(v),indent=2,allow_nan=False,default=str),encoding='utf-8')
def status(message,**values):
 save(R/'status.json',dict(message=message,utc=datetime.now(timezone.utc).isoformat(),**values));print(message,json.dumps(safe(values)),flush=True)
def settings(p):
 text=h.text(p);return {line.split('=',1)[0]:line.split('=',1)[1].split('||')[0] for line in text.splitlines() if '=' in line and not line.startswith(';')}
def local_includes(p):
 return [(p.parent/ref.replace('\\','/')).resolve() for ref in re.findall(r'^\s*#include\s+"([^"]+)"',h.text(p),re.M)]
def closure(p,seen=None):
 seen=set() if seen is None else seen
 if p in seen:return seen
 assert p.is_file(),str(p);seen.add(p)
 for child in local_includes(p):closure(child,seen)
 return seen
def absolute_includes(text,parent):
 return re.sub(r'(^\s*#include\s+)"([^"]+)"',lambda m:m[1]+'"'+str((parent/m[2].replace('\\','/')).resolve()).replace('\\','/')+'"',text,flags=re.M)
def available():
 check=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert str(T).lower() not in check.stdout.lower(),'Isolated tester occupied; no process stopped'
 ports=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
 assert not any(f':{PORT} ' in x and 'LISTENING' in x for x in ports.splitlines()),'Independent tester port occupied'

def inventory():
 products=get_website_catalog(); index={p.slug:p for p in products}; rows=[]
 for slug in SLUGS:
  p=index[slug]
  expert=p.dynamic_expert_source if p.recommended_dynamic_mode and p.dynamic_expert_source else p.expert_source
  preset=p.dynamic_set_source if p.recommended_dynamic_mode and p.dynamic_set_source else p.set_source
  binary=(B/expert).resolve(); source=binary.with_suffix('.mq5'); preset=(B/preset).resolve()
  row=dict(slug=slug,label=p.label,symbol=p.canonical,period=p.timeframe,expert=str(binary),source=str(source),preset=str(preset),
    management=p.exit_mode,input_settings=settings(preset),production_hashes={str(f):sha(f) for f in sorted(closure(source)|{binary,preset})})
  overrides={}
  if slug=='gold-overnight-value-area':
   overrides={'InpTargetR':.5};row['research_patch']='Relax only the production guard on InpTargetR in a tester-only copy; all other raw guards retained.'
  elif slug=='sell-nasdaq-15min':overrides={'InpTargetMode':1,'InpTargetRMultiple':.5}
  elif slug=='xau-squeeze-momentum-standard':overrides={'InpTargetR':.5}
  elif slug=='3-way-gold':
   overrides={'InpRR05ModuleTarget':.5};row['research_patch']='Expose TP-only override for momentum and Donchian modules; month-end target and all entry/stop/partial/trailing logic unchanged.'
  else:overrides={'InpRewardRisk':.5}
  row['candidate_overrides']=overrides
  row['interpretation']='Target distance = 0.5 times original entry-to-stop distance. Existing management retained.'
  if slug=='3-way-gold':row['interpretation']+=' Whole-EA result plus module breakdown; only MOM/BRK targets changed.'
  rows.append(row)
 exclusions=[dict(slug=p.slug,label=p.label,strategy=p.strategy,reason='Not an ORB or range/compression/structural breakout setup; unchanged and not tested in this comparison.') for p in products if p.slug not in SLUGS]
 value=dict(from_date=START,end_exclusive=END,risk_percent=1,deposit_usd=10000,execution_delay_ms=150,model=4,agent_port=PORT,
  catalogue_scope=True,archived_research_variations_not_included=True,variants=['Current','0.5R'],setups=rows,excluded=exclusions,
  only_target_changes=True,live_changes=False,policy='Diagnostic comparison, not optimization or untouched OOS.')
 p=R/'PLAN.json'
 if p.exists():assert read(p)==value,'Frozen catalogue/config changed'
 else:save(p,value)
 return value

def build(row):
 folder=R/'EA'/row['slug'];folder.mkdir(parents=True,exist_ok=True)
 cached=folder/'build.json';cached_binary=folder/'Audit.ex5'
 if cached.is_file() and cached_binary.is_file():
  info=read(cached)
  if (info['production_hashes']==row['production_hashes'] and
      all(sha(Path(p))==digest for p,digest in row['production_hashes'].items()) and
      info['audit_sha256']==sha(R/'ReadOnlyAudit.mqh') and
      info['source_sha256']==sha(folder/'Audit.mq5') and
      info['source_copy_sha256']==sha(folder/'SourceCopy.mq5') and
      info['binary_sha256']==sha(cached_binary)):
   return cached_binary,info
 origin=Path(row['source']);text=h.text(origin)
 includes=closure(origin);full='\n'.join(h.text(f) for f in includes)
 callbacks={name:bool(re.search(r'\b(?:void|int|double)\s+'+name+r'\s*\(',full)) for name in ['OnInit','OnDeinit','OnTick','OnTimer']}
 assert callbacks['OnInit'] and callbacks['OnTick']
 changes=[]
 if row['slug']=='gold-overnight-value-area':
  assert text.count(' || InpTargetR!=0')==1
  text=text.replace(' || InpTargetR!=0','',1);changes.append('Removed only InpTargetR!=0 from approved-raw parameter guard in tester copy.')
 if row['slug']=='3-way-gold':
  original='double F(int s,int k){return Cases[S[s].c][k];}'
  replacement='double F(int s,int k){if(k==6 && S[s].c<2 && InpRR05ModuleTarget>0)return InpRR05ModuleTarget;return Cases[S[s].c][k];}'
  assert text.count(original)==1;text=text.replace(original,replacement,1);changes.append('TP accessor override for MOM/BRK only; baseline override is zero.')
 source_copy=folder/'SourceCopy.mq5';source_copy.write_text(absolute_includes(text,origin.parent),encoding='utf-8')
 prefix='\n'.join('#define '+name+' RR05Base'+name for name in callbacks)+'\n'
 if row['slug']=='3-way-gold':prefix+='input double InpRR05ModuleTarget=0;\n'
 code=prefix+'#include "SourceCopy.mq5"\n'+'\n'.join('#undef '+name for name in callbacks)+'\n'
 code+='#include "'+str(R/'ReadOnlyAudit.mqh').replace('\\','/')+'"\n'
 code+='int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;int v=RR05BaseOnInit();if(v!=INIT_SUCCEEDED)return v;if(!RR05AuditInit())return INIT_FAILED;RR05Observe();return INIT_SUCCEEDED;}\n'
 code+='void OnTick(){RR05Observe();RR05BaseOnTick();RR05Observe();}\n'
 if callbacks['OnTimer']:code+='void OnTimer(){RR05Observe();RR05BaseOnTimer();RR05Observe();}\n'
 code+='void OnDeinit(const int reason){RR05Observe();'+('RR05BaseOnDeinit(reason);' if callbacks['OnDeinit'] else '')+'RR05Finish();}\n'
 source=folder/'Audit.mq5';source.write_text(code,encoding='utf-8')
 available();log=folder/'compile.log';began=time.time()
 subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 result=h.text(log);assert '0 errors, 0 warnings' in result,result[-6000:]
 binary=source.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
 value=dict(source_sha256=sha(source),source_copy_sha256=sha(source_copy),audit_sha256=sha(R/'ReadOnlyAudit.mqh'),binary_sha256=sha(binary),
  callbacks=callbacks,patches=changes,production_hashes=row['production_hashes'],compile='0 errors, 0 warnings',tester_only=True)
 save(folder/'build.json',value);return binary,value

def export_rows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def trades_from_deals(ds):
 groups={};seen=set();balance=10000;cash=[]
 for d in ds:
  ticket=int(d['deal']);assert ticket not in seen;seen.add(ticket)
  for k in ['volume','price','gross','commission','swap','fee','sl','tp']:d[k]=float(d[k])
  for k in ['entry','type','epoch','magic','position_id']:d[k]=int(d[k])
  assert d['entry'] in [0,1] and d['type'] in [0,1]
  flow=sum(d[k] for k in ['gross','commission','swap','fee']);balance+=flow
  cash.append(dict(epoch=d['epoch'],deal=ticket,balance=round(balance,2),net=round(flow,2)))
  groups.setdefault(d['position_id'],[]).append(d)
 out=[]
 for pid,parts in groups.items():
  opened=[d for d in parts if d['entry']==0];closed=[d for d in parts if d['entry']==1]
  assert len(opened)==1 and len(closed)>=1,('Missing/unsupported position',pid)
  a=opened[0];z=closed[-1];assert abs(a['volume']-sum(d['volume'] for d in closed))<1e-7
  assert all(d['type']!=a['type'] for d in closed)
  vals={k:round(sum(d[k] for d in parts),2) for k in ['gross','commission','swap','fee']}
  out.append(dict(position_id=pid,open_epoch=a['epoch'],close_epoch=z['epoch'],last_deal=int(z['deal']),side='Long' if a['type']==0 else 'Short',
    volume=a['volume'],open_price=a['price'],close_price=sum(d['price']*d['volume'] for d in closed)/a['volume'],
    net=round(sum(vals.values()),2),magic=a['magic'],sl=a['sl'],tp=a['tp'],entry_comment=a['comment'],
    exit_comments=[d['comment'] for d in closed],exit_legs=len(closed),partial=len(closed)>1,**vals))
 out.sort(key=lambda x:(x['close_epoch'],x['last_deal']))
 assert abs(sum(t['net'] for t in out)-(balance-10000))<.03
 return out,cash
def metrics(ts,trace,native):
 profits=[t['net'] for t in ts];wins=[x for x in profits if x>0];losses=[x for x in profits if x<0]
 w=l=mw=ml=0
 for x in profits:w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
 sharpe=None
 if trace:
  frame=pd.DataFrame(trace);frame['epoch']=frame.epoch.astype('int64');frame['equity']=frame.equity.astype(float)
  daily=pd.Series(frame.equity.to_numpy(),index=pd.to_datetime(frame.epoch,unit='s',utc=True)).resample('D').last().ffill()
  changes=daily[daily.index.weekday<5].pct_change().dropna()
  if len(changes)>2 and changes.std(ddof=1)>0:sharpe=float(np.sqrt(252)*changes.mean()/changes.std(ddof=1))
 return dict(trades=len(ts),return_pct=sum(profits)/100,net_profit=round(sum(profits),2),pf=sum(wins)/-sum(losses) if losses else None,
  wins=len(wins),losses=len(losses),flat=len(ts)-len(wins)-len(losses),win_rate=100*len(wins)/len(ts) if ts else None,
  equity_dd_pct=native['equity_dd_pct'],balance_dd_pct=native['balance_dd_pct'],sharpe_daily_equity=sharpe,
  win_streak=mw,loss_streak=ml,avg_win=sum(wins)/len(wins) if wins else None,avg_loss=sum(losses)/len(losses) if losses else None,
  partial_positions=sum(t['partial'] for t in ts),exit_legs=sum(t['exit_legs'] for t in ts),
  commission=sum(t['commission'] for t in ts),swap=sum(t['swap'] for t in ts),fee=sum(t['fee'] for t in ts))

def run_case(row,variant,binary,build_info):
 slug=row['slug'];tag='allrr05-'+slug+'-'+variant
 out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
 inputs=dict(row['input_settings']);inputs['InpRiskPercent']='1.0';inputs['InpRR05AuditTag']=tag
 if slug=='3-way-gold':inputs['InpRR05ModuleTarget']='0';inputs['InpRiskMode']='0';inputs['InpFixedRiskMoney']='0'
 if variant=='half':inputs.update({k:str(v) for k,v in row['candidate_overrides'].items()})
 manifest=dict(tag=tag,slug=slug,variant=variant,inputs=inputs,start=START,end_exclusive=END,model=4,delay=150,symbol=row['symbol'],period=row['period'],build=build_info)
 if (out/'manifest.json').exists():assert read(out/'manifest.json')==manifest,'Case changed'
 else:save(out/'manifest.json',manifest)
 if (out/'results.json').exists():return read(out/'results.json')
 assert all(sha(Path(p))==digest for p,digest in row['production_hashes'].items()),'Production changed during test'
 available();destination=T/'MQL5/Experts/AAA Research/RR05All20261008';destination.mkdir(parents=True,exist_ok=True)
 shutil.copy2(binary,destination/(slug+'.ex5'))
 preset=tag+'.set';body='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
 (out/'inputs.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/preset).write_text(body,encoding='utf-8')
 header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
 report=T/'reports/rr05-all-20261008'/(tag+'.htm');report.parent.mkdir(exist_ok=True)
 ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port={PORT}
Expert=AAA Research\\RR05All20261008\\{slug}
ExpertParameters={preset}
Symbol={row['symbol']}
Period={row['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
Report=reports\\rr05-all-20261008\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
 offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
 save(out/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe'),started=began))
 try:proc.wait(timeout=2400)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned tester timed out; other processes untouched')
 journal=''
 for p in h.logfiles():
  if p.stat().st_mtime<began-2:continue
  with p.open('rb') as stream:stream.seek(offsets.get(p,0));journal+=stream.read().decode('utf-16-le',errors='replace')+'\n'
 (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
 assert proc.returncode==0 and report.is_file() and report.stat().st_mtime>=began-2,('No fresh report',journal[-2000:])
 flags={key:len(re.findall(pattern,journal,re.I)) for key,pattern in {
   'init_failed':'initialization failed','runtime':'access violation|array out of range|zero divide','history':'testing start time changed|not enough history',
   'stopout':'stop out|margin call','invalid_stops':'invalid stops','invalid_volume':'invalid volume','export_failed':'RR05_EXPORT_FAILED'}.items()}
 assert not any(flags[key] for key in ['init_failed','runtime','history','stopout','export_failed']),flags
 assert 'RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal,'Missing independent-agent completion'
 actual=h._report_inputs(report)
 # Some older maintained SETs contain inactive archived parameters; record them,
 # but strictly verify all supplied parameters that exist in the running EA.
 unsupported=[k for k in inputs if k not in actual]
 mismatched=[k for k,v in inputs.items() if k in actual and not h._same_setting(v,actual[k])]
 assert not mismatched,mismatched
 required=['InpRiskPercent','InpRR05AuditTag',*row['candidate_overrides']]
 assert all(k in actual for k in required),('Required active input missing',required,unsupported)
 native=h._native_metrics(report);text=h._read_report(report)
 assert START in text and END in text and row['symbol'] in text
 native.update(equity_dd_pct=_number(_metric(text,'Equity Drawdown Relative')),balance_dd_pct=_number(_metric(text,'Balance Drawdown Relative')))
 shutil.copy2(report,out/'report.htm');(out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 for suffix in ['deals','equity']:
  file=COMMON/(tag+'-'+suffix+'.csv');assert file.is_file() and file.stat().st_mtime>=began-2
  shutil.copy2(file,out/(suffix+'.csv'))
 trades,ledger=trades_from_deals(export_rows(out/'deals.csv'))
 assert abs(sum(t['net'] for t in trades)-native['net_profit'])<.031,('Native cash mismatch',slug)
 assert all(pd.Timestamp(START.replace('.','-'),tz='UTC').timestamp()<=t['open_epoch']<=t['close_epoch']<pd.Timestamp(END.replace('.','-'),tz='UTC').timestamp() for t in trades)
 m=metrics(trades,export_rows(out/'equity.csv'),native)
 result=dict(tag=tag,slug=slug,variant=variant,window=[START,END],inputs=actual,unsupported_set_inputs=unsupported,
  native=native,metrics=m,flags=flags,trades=trades,ledger=ledger,seconds=time.time()-began,
  binary_sha256=sha(binary),report_sha256=sha(report),
  tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*',journal,re.I)))[:20],
  source_patch=build_info['patches'],no_live_changes=True)
 save(out/'results.json',result);status('DONE '+tag,metrics=m,history_quality=native['history_quality'],seconds=round(result['seconds'],1));return result

def prior_h1(row):
 data=read(PRIOR/'SUMMARY.json');assert data['production_files_unchanged'] and data['plan']['from']=='2025-10-06' and data['plan']['end_exclusive']=='2026-10-06'
 cases=[read(PRIOR/'native'/tag/'results.json') for tag in ['rrcomp20261008-current-1y','rrcomp20261008-half-1y']]
 for q in cases:q['metrics']['equity_dd_pct']=q['native']['equity_dd_pct']
 return dict(slug=row['slug'],label=row['label'],symbol=row['symbol'],current=cases[0],half=cases[1],completed=True,reused_verified_comparison=True)
def comparison(row,a,b):
 differences=[k for k,v in a['inputs'].items() if b['inputs'].get(k)!=v and k!='InpRR05AuditTag']
 allowed=list(row['candidate_overrides']);assert set(differences)<=set(allowed) and differences,('Unexpected strategy differences',differences,allowed)
 assert a['binary_sha256']==b['binary_sha256']
 identities=lambda q:sorted((t['open_epoch'],t['side']) for t in q['trades'])
 pair=dict(slug=row['slug'],label=row['label'],symbol=row['symbol'],current=a,half=b,completed=True,
  actual_input_differences=differences,identical_entry_times_and_directions=identities(a)==identities(b))
 if row['slug']=='3-way-gold':
  base=int(row['input_settings']['InpMagic']);pair['module_breakdown']={}
  for name,offset in [('Momentum',0),('Donchian breakout',1),('Month end (unchanged target)',2)]:
   pair['module_breakdown'][name]={kind:metrics([t for t in q['trades'] if t['magic']==base+offset],[],q['native']) for kind,q in [('current',a),('half',b)]}
 return pair
def compact(pair):
 return dict(label=pair['label'],slug=pair['slug'],current=pair['current']['metrics'],half=pair['half']['metrics'],
  history_quality=pair['half']['native']['history_quality'],completed=True)
def display(value,places=2):return 'N/A' if value is None else f'{value:,.{places}f}'
def render(plan,pairs):
 done={p['slug']:p for p in pairs};sections=[];summaries=[]
 metrics_list=[('Trades','trades',0),('Win rate %','win_rate',2),('PF after costs','pf',2),('Return %','return_pct',2),
  ('Maximum equity DD %','equity_dd_pct',2),('Annualized daily-equity Sharpe','sharpe_daily_equity',2),
  ('Longest winning streak','win_streak',0),('Longest losing streak','loss_streak',0),('Average win USD','avg_win',2),('Average loss USD','avg_loss',2)]
 for row in plan['setups']:
  slug=row['slug'];pair=done.get(slug)
  if not pair:summaries.append('<tr><td>'+html.escape(row['label'])+'</td><td colspan="7">Pending — no result yet</td></tr>');continue
  a=pair['current']['metrics'];b=pair['half']['metrics']
  fields=['win_rate','pf','return_pct','equity_dd_pct','sharpe_daily_equity']
  summaries.append('<tr><td><a href="#'+slug+'">'+html.escape(row['label'])+'</a></td><td>'+str(a['trades'])+' → '+str(b['trades'])+'</td>'+''.join('<td>'+display(a[k])+' → '+display(b[k])+'</td>' for k in fields)+'<td>'+str(a['win_streak'])+'/'+str(a['loss_streak'])+' → '+str(b['win_streak'])+'/'+str(b['loss_streak'])+'</td></tr>')
  rows=''.join('<tr><td>'+label+'</td><td>'+display(a[key],p)+'</td><td>'+display(b[key],p)+'</td></tr>' for label,key,p in metrics_list)
  paragraphs='<p>'+html.escape(row['management'])+' retained. '+html.escape(row['interpretation'])+'</p>'
  if slug=='xau-weakness':paragraphs+='<p>The existing EA divides its 1% idea-level risk setting between the limit and stop entries (0.5% each before lot rounding). This allocation is retained in both tests.</p>'
  if slug=='gold-overnight-value-area':paragraphs+='<p>The original target is an overnight price extreme, not a fixed R multiple. A 0.5R replacement can be farther away. Both runs generate the same 245 raw signals: current has 40 invalid-target-geometry skips and 2 rejected entries, while 0.5R admits all 245. Thus the changed target also changes entry eligibility; this is not a matched-trades-only comparison.</p>'
  paragraphs+='<p>Native history quality: '+html.escape(pair['half']['native']['history_quality'])+'. Real-tick start notes: '+html.escape('; '.join(pair['half']['tick_notes']))+'</p>'
  if row.get('research_patch'):paragraphs+='<p>Tester-only patch: '+html.escape(row['research_patch'])+'</p>'
  if pair.get('module_breakdown'):
   paragraphs+='<h3>Module-level net trade results</h3><table><tr><th>Module</th><th>Trades</th><th>Win rate</th><th>PF</th><th>Net USD</th></tr>'
   for name,values in pair['module_breakdown'].items():
    x,y=values['current'],values['half'];paragraphs+='<tr><td>'+name+'</td>'+''.join('<td>'+display(x[k])+' → '+display(y[k])+'</td>' for k in ['trades','win_rate','pf','net_profit'])+'</tr>'
   paragraphs+='</table><p>Module cash results come from the shared account, not separately compounded module backtests. Account-level drawdown and Sharpe are not attributed to individual modules.</p>'
  sections.append('<section id="'+slug+'"><h2>'+html.escape(row['label'])+'</h2>'+paragraphs+'<table><tr><th>Metric</th><th>Current</th><th>0.5R target</th></tr>'+rows+'</table></section>')
 report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ORB and range breakouts: current versus 0.5R</title>
<style>body{font:16px system-ui;background:#081713;color:#edf8f3;margin:30px auto;padding:0 20px;max-width:1600px}p{line-height:1.6;color:#b4ccc0}h1{font-size:28px}h2{font-size:22px}a{color:#75f5c7}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:12px;text-align:right;border-bottom:1px solid #345045}th:first-child,td:first-child{text-align:left}section{margin:50px 0}.wide{overflow-x:auto}.note{padding:16px;border:1px solid #8f7745;border-radius:10px}</style>
<h1>Current ORBs and range-breakout setups versus 0.5R</h1>
<p>Findings: 0.5R is not a universal improvement. Gold New York M30 improves the main metrics, but has only 12 trades. Gold London–New York overlap retains almost the same return with higher wins and better streaks. XAU Weakness has the strongest larger-sample win-rate/drawdown trade-off, sacrificing total return. US100 H1 improves drawdown and Sharpe but approximately halves the return. Asia, Squeeze and US100 New York turn unprofitable.</p>
<p>Native Exness tests: 6 October 2025–5 October 2026 inclusive. $10,000 initial balance, 1% EA risk setting with existing split-order/module allocations retained, native costs, 150 ms delay, real-tick model with generated-tick fallback where broker real ticks are missing. A 0.5R target means profit distance is half the initial stop distance.</p>
<p class="note">Research only. Stops, signal filters, clocks, DI gates, partials, trailing settings and sizing rules are unchanged. Target-relative Dynamic 50/20 or 60/20 trigger levels necessarily move when TP is reduced. Entries and trade counts can differ when exits free capacity earlier or target placement becomes valid on additional signals. No live EAs, BATs, website or active account settings are modified. This is retrospective diagnostics, not untouched OOS or proof of future profitability.</p>
<p>1% is the selected risk setting, not a guaranteed loss ceiling: these existing EAs round lot sizes up to the broker step/minimum, and costs, gaps or slippage can exceed the selected budget.</p>
<h2>Completed '''+str(len(pairs))+' / '+str(len(plan['setups']))+'''</h2><p>All values below are Current → 0.5R. Streaks are longest wins / longest losses. PF and win rate include whole-position costs. N/A PF for the 0.5R Selective ORB means no losses in its five trades, not an established perfect win rate. Sharpe uses daily mark-to-market equity, 252 weekdays, zero risk-free rate.</p>
<div class="wide"><table><tr><th>Setup</th><th>Trades</th><th>Win %</th><th>PF</th><th>Return %</th><th>Equity DD %</th><th>Sharpe</th><th>Streaks W/L</th></tr>'''+''.join(summaries)+'</table></div>'+''.join(sections)
 report+='<h2>Scope exclusions</h2><p>Current catalogue setups only; archived exploratory variations are not counted as active EAs. News straddles, liquidity reversals, timed hourly portfolios and pure directional/pullback strategies are not an ORB/range-breakout target conversion.</p><ul>'+''.join('<li>'+html.escape(x['label'])+' — '+html.escape(x['strategy'])+'</li>' for x in plan['excluded'])+'</ul></html>'
 (R/'Results.html').write_text(report,encoding='utf-8')
 save(R/'SUMMARY.json',dict(plan=plan,comparisons=pairs,completed=len(pairs),total=len(plan['setups']),no_live_changes=True))

def main():
 with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  plan=inventory();pairs=[]
  for row in plan['setups']:
   p=R/'comparisons'/(row['slug']+'.json')
   if p.exists():pairs.append(read(p));continue
   if row['slug']=='us100-h1-orb-13utc':pair=prior_h1(row)
   else:
    binary,info=build(row)
    a=run_case(row,'current',binary,info);b=run_case(row,'half',binary,info)
    pair=comparison(row,a,b)
   save(p,pair);pairs.append(pair);render(plan,pairs);status('COMPARISON FINISHED',**compact(pair),count=len(pairs),total=len(plan['setups']))
  assert all(all(sha(Path(p))==digest for p,digest in row['production_hashes'].items()) for row in plan['setups'])
  render(plan,pairs);save(R/'VERIFICATION.json',dict(completed=len(pairs),total=len(plan['setups']),all_production_hashes_unchanged=True,
   native_cash_reconciliation=True,only_target_changes=True,whole_position_trade_counts=True,no_live_changes=True))
  status('ALL COMPARISONS COMPLETE',count=len(pairs))
if __name__=='__main__':main()
