"""Native MT5 complete optimiser over a finite, frozen exit menu.
Local tester workers are used, not live MT5/API or delegated agents.
"""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone,date,timedelta
import csv,gzip,hashlib,json,os,re,shutil,statistics,subprocess,sys,time
import xml.etree.ElementTree as ET

R=Path(__file__).resolve().parent;B=R.parent;OLD=B/'News XAU Placement Fix 2026-10-03'
T=B/'_Backtests/MT5-DMC-20260811';DEST=T/'MQL5/Experts/AAA Research/NewsExits20261003'
SOURCE=B/'AAA Final EAs/AAA Final News Pulse XAU Event Specific EA/AAA Final News Pulse XAU Event Specific EA.mq5'
SET=B/'Selected Portfolio Settings 2026-09-01/12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'
NAME='NewsExitResearch'
MENU=[
 ('Current event-specific exits',None,None,None),
 ('No TP / no trail',0,0,0),
 ('Trail from 0.25R / $1.5 gap',0,.25,1.5),
 ('Trail from 0.5R / $2 gap',0,.5,2),
 ('Trail from 0.5R / $4 gap',0,.5,4),
 ('Trail from 1R / $2 gap',0,1,2),
 ('Trail from 1R / $4 gap',0,1,4),
 ('Trail from 1.5R / $4 gap',0,1.5,4),
 ('TP 1R / no trail',1,0,0),
 ('TP 2R / no trail',2,0,0),
 ('TP 3R / no trail',3,0,0),
 ('TP 3R / trail 0.5R / $4 gap',3,.5,4),
]
WINDOWS={'development':('2025.10.03','2026.07.03'),'validation':('2026.07.03','2026.10.03'),
 'year':('2025.10.03','2026.10.03'),'incident':('2026.10.02','2026.10.03')}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 d=p.read_bytes();return d.decode('utf-16') if d[:2] in (b'\xff\xfe',b'\xfe\xff') else d.decode('utf-8-sig',errors='replace')
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(message):
 print(message,flush=True);save(R/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=message))
def hidden():
 s=subprocess.STARTUPINFO();s.dwFlags|=subprocess.STARTF_USESHOWWINDOW;s.wShowWindow=0;return s
def free():
 a=subprocess.run(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Process -Filter "Name=\'terminal64.exe\'" | Select-Object -ExpandProperty ExecutablePath'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert a.returncode==0 and str(T).lower() not in a.stdout.lower(),'Isolated terminal busy; do not stop other work'
 assert not list((T/'MQL5/Profiles/Charts/Calyx Research Empty').glob('*.chr'))
def fingerprint():
 return dict(source=sha(SOURCE),settings=sha(SET),helper=sha(SOURCE.parent/'NewsPulsePlacement.mqh'),
  protocol=sha(R/'PROTOCOL.txt'),audit=sha(R/'ResearchAudit.mqh'),menu=MENU)

def prepare():
 free();folder=R/'snapshot';folder.mkdir(exist_ok=True)
 base=read(OLD/'snapshot/New-fixed-test.mq5').replace('\r\n','\n')
 current=read(SOURCE).replace('\r\n','\n');current=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',current)
 current=current.replace('int OnInit()\n{','int OnInit()\n{\n   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;')
 assert current==base,'Previous frozen baseline no longer matches production'
 for p in (OLD/'snapshot').glob('*.mqh'):shutil.copy2(p,folder/p.name)
 shutil.copy2(R/'ResearchAudit.mqh',folder/'ResearchAudit.mqh')
 # Declarations must appear after globals used by the audit exporter.
 base=base.replace('void NP_ApplyEventParameters(const string kind)','void NP_BaseEventParameters(const string kind)',1)
 anchor='string NP_KindFromComment(const string comment)'
 body='void NP_ApplyEventParameters(const string kind)\n{\n NP_BaseEventParameters(kind);\n'
 for case,(_,tp,start,gap) in enumerate(MENU):
  if case:body+=f' if(InpExitCase=={case}){{g_np_tp={tp};g_np_trail_start={start};g_np_trail_distance={gap};}}\n'
 body+='}\n'
 assert anchor in base;base=base.replace(anchor,body+anchor,1)
 # Inputs need to be known at compile time, before functions that use them.
 audit=read(R/'ResearchAudit.mqh')
 inputs='input int InpExitCase=0;\ninput long InpResearchRun=0;\n'
 audit=audit.replace('input int InpExitCase=0;','').replace('input long InpResearchRun=0;','')
 base=base.replace('input group "Trading"',inputs+'\ninput group "Trading"',1)
 i=base.index('double OnTester()');brace=base.index('{',i);depth=1;j=brace+1
 while depth:depth+=(base[j]=='{')-(base[j]=='}');j+=1
 base=base[:i]+audit+'\ndouble OnTester(){return NR_WriteAudit();}\n'+base[j:]
 (folder/(NAME+'.mq5')).write_text(base)
 f=fingerprint();manifest=R/'FROZEN.json'
 if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(f)),'Research protocol changed'
 else:save(manifest,f)
 log=R/'compile.log';began=time.time()
 subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{folder/(NAME+".mq5")}" /log:"{log}"',
  startupinfo=hidden(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 assert '0 errors, 0 warnings' in read(log),read(log)[-5000:]
 assert (folder/(NAME+'.ex5')).stat().st_mtime>=began-2
 DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/(NAME+'.ex5'),DEST/(NAME+'.ex5'))
 save(R/'BUILD.json',dict(source=sha(folder/(NAME+'.mq5')),binary=sha(DEST/(NAME+'.ex5'))))
 status('COMPILED 12-exit tester-only build, zero errors/warnings')

def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def parse_case(folder,case,start,end):
 summary={x['key']:float(x['value']) for x in rows(folder/f'case{case}-summary.csv')}
 ds=rows(folder/f'case{case}-deals.csv');groups=defaultdict(list)
 for d in ds:
  if d['symbol']!='XAUUSD' or int(d['type']) not in (0,1):continue
  assert int(d['magic'])==861301
  for k in ['volume','price','profit','commission','swap','fee']:d[k]=float(d[k])
  groups[d['position_id']].append(d)
 trades=[];unique=Counter()
 for pid,g in groups.items():
  ins=[d for d in g if int(d['entry'])==0];outs=[d for d in g if int(d['entry']) in (1,3)]
  assert ins and outs and abs(sum(d['volume'] for d in ins)-sum(d['volume'] for d in outs))<1e-7
  parts=ins[0]['comment'].split('|');assert len(parts)==4 and parts[0]=='NP'
  unique[(parts[1],parts[3])]+=1
  exit_time=datetime.strptime(outs[-1]['time'],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
  assert exit_time<=int(parts[1])+33,'Late exit beyond 30s plus execution tolerance'
  net=sum(d['profit']+d['commission']+d['swap']+d['fee'] for d in g)
  trades.append(dict(position_id=pid,kind=parts[2],side=parts[3],open=ins[0]['time'],close=outs[-1]['time'],net=net,
   commission=sum(d['commission'] for d in g),swap=sum(d['swap'] for d in g),fee=sum(d['fee'] for d in g)))
 trades.sort(key=lambda x:(x['close'],int(x['position_id'])))
 assert not any(n>1 for n in unique.values())
 assert len(trades)==int(summary['trades'])
 net=sum(t['net'] for t in trades);assert abs(net-summary['profit'])<.06
 assert abs(summary['final_balance']-10000-net)<.06
 assert summary['boundary_violation']==0 and summary['open_positions']==0 and summary['pending_orders']==0
 assert summary['complete_straddles']==summary['attempted_events']
 gains=sum(t['net'] for t in trades if t['net']>0);losses=-sum(t['net'] for t in trades if t['net']<0)
 win=loss=bestwin=bestloss=0
 for t in trades:
  win=win+1 if t['net']>0 else 0;loss=loss+1 if t['net']<0 else 0;bestwin=max(bestwin,win);bestloss=max(bestloss,loss)
 byday=defaultdict(float)
 for t in trades:byday[t['close'][:10]]+=t['net']
 balance=10000;daily=[];day=date.fromisoformat(start.replace('.','-'));enddate=date.fromisoformat(end.replace('.','-'))
 while day<enddate:
  amount=byday[day.strftime('%Y.%m.%d')]
  if day.weekday()<5:daily.append(amount/balance)
  balance+=amount;day+=timedelta(days=1)
 sharpe=statistics.mean(daily)/statistics.stdev(daily)*252**.5 if len(daily)>1 and statistics.stdev(daily)>0 else None
 result=dict(case=case,label=MENU[case][0],from_date=start,to_exclusive=end,net_profit=net,return_pct=net/100,
  net_pf=gains/losses if losses else None,win_rate=100*sum(t['net']>0 for t in trades)/len(trades) if trades else 0,
  trades=len(trades),equity_dd=summary['equity_dd_pct'],win_streak=bestwin,loss_streak=bestloss,daily_closed_sharpe=sharpe,
  average_win=gains/sum(t['net']>0 for t in trades) if gains else 0,
  average_loss=losses/sum(t['net']<0 for t in trades) if losses else 0,
  native=summary,max_same_side_per_event=max(unique.values(),default=0))
 save(folder/f'case{case}-trades.json',trades);return result

def batch(phase,cases,delay=150):
 start,end=WINDOWS[phase];tag=phase+'-'+','.join(map(str,cases))+'-'+str(delay)
 folder=R/'native'/tag;folder.mkdir(parents=True,exist_ok=True)
 if (folder/'results.json').exists():return json.loads((folder/'results.json').read_text())
 free();runid=int(time.time());settings={}
 for line in read(SET).splitlines():
  if '=' in line and not line.startswith(';'):k,v=line.split('=',1);settings[k]=v.split('||')[0]
 if len(cases)>1:
  step=cases[1]-cases[0];assert cases==list(range(cases[0],cases[-1]+1,step))
  selector=f'{cases[0]}||{cases[0]}||{step}||{cases[-1]}||Y'
 else:selector=str(cases[0])
 settings.update(InpExitCase=selector,InpResearchRun=str(runid),InpTesterFromDateUTC=start.replace('.',''),
  InpTesterToDateUTC=end.replace('.',''),InpAdaptivePortfolioControls='false')
 setname='npexit-'+tag+'.set';body='\n'.join(f'{k}={v}' for k,v in settings.items())+'\n'
 (folder/'inputs.set').write_text(body);(T/'MQL5/Profiles/Tester'/setname).write_text(body)
 header=read(OLD/'native/Current-test-150-2025.10.03/tester.ini').split('[Experts]')[0]
 ext='xml' if len(cases)>1 else 'htm';report=T/'reports/npexits20261003'/(tag+'.'+ext);report.parent.mkdir(parents=True,exist_ok=True)
 ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\NewsExits20261003\\{NAME}
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode={delay}
Optimization={1 if len(cases)>1 else 0}
OptimizationCriterion=6
ForwardMode=0
FromDate={start}
ToDate={end}
Report=reports\\npexits20261003\\{tag}.{ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 begun=time.time();status('START '+tag)
 proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,startupinfo=hidden(),creationflags=subprocess.CREATE_NO_WINDOW)
 save(R/'owned-process.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),case=tag))
 last=-1
 while proc.poll() is None:
  complete=list((T/'Tester').glob(f'Agent-*/MQL5/Files/NP-EXIT-{runid}-*-summary.csv'))
  if len(complete)!=last:last=len(complete);status(f'RUNNING {tag}: {last}/{len(cases)} native passes exported')
  if time.time()-begun>3600:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned research batch timed out')
  time.sleep(1)
 assert report.exists() and report.stat().st_mtime>=begun-2,'No fresh native report'
 (folder/('report.'+ext+'.gz')).write_bytes(gzip.compress(report.read_bytes(),mtime=0))
 result=[]
 for case in cases:
  matches=list((T/'Tester').glob(f'Agent-*/MQL5/Files/NP-EXIT-{runid}-{case}-summary.csv'))
  assert len(matches)==1,(case,'missing/multiple native summaries',matches)
  p=matches[0]
  for suffix in ['summary','deals']:shutil.copy2(p.with_name(f'NP-EXIT-{runid}-{case}-{suffix}.csv'),folder/f'case{case}-{suffix}.csv')
  result.append(parse_case(folder,case,start,end))
 save(folder/'results.json',result);status('DONE '+tag+' '+json.dumps([{k:x[k] for k in ['case','return_pct','win_rate','net_pf','trades']} for x in result]))
 return result

def main():
 prepare()
 control=batch('incident',[0])[0]
 assert abs(control['net_profit']-127.64)<.06 and control['trades']==1,'Research wrapper changed baseline'
 dev=batch('development',list(range(len(MENU))))
 baseline=next(x for x in dev if x['case']==0)
 eligible=[x for x in dev if x['case']!=0 and x['win_rate']>=baseline['win_rate']-1e-8 and
  (x['net_pf'] is None or x['net_pf']>=1.2) and x['return_pct']>baseline['return_pct'] and
  x['equity_dd']<=max(1.5,baseline['equity_dd']*1.5)]
 winner=max(eligible,key=lambda x:(x['return_pct'],x['net_pf'] or 100000)) if eligible else baseline
 selection=dict(case=winner['case'],label=winner['label'],development=winner,eligible=[x['case'] for x in eligible],
  protocol=fingerprint(),frozen_before_validation=True)
 save(R/'SELECTION.json',selection);status('FROZEN development choice: '+str(winner['case'])+' '+winner['label'])
 val=batch('validation',[0,winner['case']] if winner['case'] else [0])
 annual=batch('year',[winner['case']])
 stress=batch('year',[winner['case']],1000)
 base_year=json.loads((OLD/'native/New-fixed-test-150-2025.10.03/result.json').read_text())
 base_stress=json.loads((OLD/'native/New-fixed-test-1000-2025.10.03/result.json').read_text())
 save(R/'RESULTS.json',dict(development=dev,selection=selection,validation=val,annual=annual,stress=stress,
  baseline_year=base_year,baseline_stress=base_stress,production_changed=False,
  validation_seen_before=True,real_ticks_full_year_pct=75,risk_percent_per_side=.75))
 assert fingerprint()==json.loads((R/'FROZEN.json').read_text()) or json.loads(json.dumps(fingerprint()))==json.loads((R/'FROZEN.json').read_text())
 status('COMPLETE native exit research; production and running MT5 unchanged')

if __name__=='__main__':main()
