"""Reproducible native transfer of active ORB/US100 presets; no live deployment."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import MetaTrader5 as mt5
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent; PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
NORMAL=Path('C:/Program Files/MetaTrader 5/terminal64.exe')
SELECTED=PACKAGE/'Selected Portfolio Settings 2026-09-01'
START='2025.09.19'; END='2026.09.19'; EXPERT_DIR='SP500 Transfer 20260919'
sys.path.insert(0,str(PACKAGE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_read_report,_metric,_report_inputs,_same_setting

ORB=PACKAGE/'ORB Volume Data EA'/'ORB Volume Data EA.mq5'
CASES=[
 ('vp','ORB Volume Profile (XAU preset)',5,ORB,SELECTED/'05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set'),
 ('vpc','ORB Volume Confirmed (XAU preset)',5,ORB,SELECTED/'05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set'),
 ('xny','XAU ORB New York M30',30,ORB,SELECTED/'14 XAU ORB New York M30 - LOCKED STANDALONE.set'),
 ('xov','XAU ORB London NY Overlap M30',30,ORB,SELECTED/'15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set'),
 ('uny','US100 ORB New York M30',30,ORB,SELECTED/'16 US100 ORB New York M30 - LOCKED STANDALONE.set'),
 ('uh1','US100 H1 ORB 13UTC',15,ORB,PACKAGE/'ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set'),
 ('usel','US100 Selective ORB V3',5,PACKAGE/'US100 Selective ORB Research 2026-08-21/EA/US100 Selective ORB Retest EA.mq5',PACKAGE/'US100 Selective ORB Research 2026-08-21/Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set'),
 ('dmc','DMC Fresh Reaction US100',60,PACKAGE/'AAA Final EAs/Calyx DMC Fresh Reaction EA/Calyx DMC Fresh Reaction EA.mq5',SELECTED/'22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set'),
 ('overnight','Nasdaq Overnight',1,PACKAGE/'Nasdaq Overnight Negative Day EA/Nasdaq Overnight Negative Day EA.mq5',SELECTED/'10 Nasdaq Overnight - CURRENT - ALL DAY.set'),
 ('momentum','Nasdaq 5M Candle Momentum',5,PACKAGE/'Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/EA/Nasdaq 5M Candle Momentum Audit EA.mq5',SELECTED/'11 Nasdaq 5M Candle Momentum - OPTIMIZED 2P5R - HARD 1PCT.set'),
 ('sell','Sell Nasdaq 15min (recommended dynamic)',15,PACKAGE/'Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/EA/Sell Nasdaq 15min Dynamic Exit Research EA.mq5',PACKAGE/'Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/Sets/Sell Nasdaq 15min - london-safe dynamic exit candidate - 1pct.set'),
 ('monthend','US100 Month End Flow',30,PACKAGE/'Month End Institutional Flow Research 2026-09-06/EA/Calyx Month End Flow EA.mq5',SELECTED/'19 US100 Month End Flow M30 - FIRST3 NY - LOCKED 2P5R - HARD 1PCT.set'),
]

def save(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def settings(p):
 return {k.strip():v.split('||')[0].strip() for k,v in (x.split('=',1) for x in read(p).splitlines() if '=' in x and not x.lstrip().startswith(';'))}
def connect():
 assert mt5.initialize(str(NORMAL)),mt5.last_error()
 a=mt5.account_info();t=mt5.terminal_info();assert a and t and t.connected
 return a,t
def dependencies(p,seen=None):
 seen={} if seen is None else seen
 p=p.resolve()
 if str(p) in seen:return seen
 seen[str(p)]=sha(p)
 for bracket,name in re.findall(r'^\s*#include\s*(["<])([^">]+)[">]',read(p),re.M):
  child=(p.parent/name.replace('\\','/')) if bracket=='"' else (TESTER/'MQL5/Include'/name.replace('\\','/'))
  assert child.exists(),str(child)
  dependencies(child,seen)
 return seen
def prepare():
 a,t=connect(); assert a.server.startswith('Exness-'),'Different broker requires clock review'
 candidates=[s for s in mt5.symbols_get() if s.name.upper() in ('US500','SP500','SPX500') and s.trade_mode==4]
 assert len(candidates)==1,[s.name for s in candidates]
 s=candidates[0];assert s.name=='US500','Update tester-only symbol guard after reviewing discovered contract'
 fields=['name','description','path','trade_contract_size','trade_tick_size','trade_tick_value','volume_min','volume_step','volume_max','trade_stops_level','swap_mode','swap_long','swap_short','currency_profit']
 meta=dict(captured_utc=datetime.now(timezone.utc).isoformat(),account={k:getattr(a,k) for k in ('login','server','company','currency','leverage','trade_mode','balance','equity')},symbol=s.name,contract={k:getattr(s,k) for k in fields},normal_terminal=str(NORMAL),normal_data=t.data_path,start=START,end_exclusive=END,deposit=10000,model=4,execution_delay_ms=150,rules_sha256=sha(ROOT/'RULES.md'),cases={})
 mt5.shutdown()
 assert meta['contract']['currency_profit']=='USD'
 dest=TESTER/'MQL5/Experts/AAA Research'/EXPERT_DIR;dest.mkdir(parents=True,exist_ok=True)
 for slug,label,period,source,preset in CASES:
  deps=dependencies(source); deps.update(dependencies(ROOT/'StudyAudit.mqh'))
  alltext='\n'.join(read(Path(p)) for p in deps if not str(TESTER/'MQL5/Include') in p)
  events=[e for e in ('OnInit','OnTick','OnTimer','OnDeinit') if re.search(r'\b(?:int|void)\s+'+e+r'\s*\(',alltext)]
  assert 'OnInit' in events and 'OnTick' in events
  wrapper=ROOT/(slug+'.mq5');rel='..\\'+str(source.relative_to(PACKAGE)).replace('/','\\')
  code='\n'.join('#define '+e+' StudyBase'+e for e in events)+'\n#include "'+rel+'"\n'
  code+='\n'.join('#undef '+e for e in events)+'\n#include "StudyAudit.mqh"\n'
  code+='int OnInit(){if(!StudyGuard())return INIT_FAILED;int code=StudyBaseOnInit();if(code!=INIT_SUCCEEDED)return code;return StudyInit();}\n'
  code+='void OnTick(){StudyObserve();StudyBaseOnTick();StudyObserve();}\n'
  if 'OnTimer' in events:code+='void OnTimer(){StudyObserve();StudyBaseOnTimer();StudyObserve();}\n'
  code+='void OnDeinit(const int reason){StudyFinish();'+('StudyBaseOnDeinit(reason);' if 'OnDeinit' in events else '')+'}\n'
  # Generated wrappers are deterministic research artifacts, not edited production sources.
  wrapper.write_text(code,encoding='utf-8')
  log=wrapper.with_suffix('.compile.log');began=time.time()
  subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{wrapper}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
  assert log.exists() and log.stat().st_mtime>=began-1 and '0 errors, 0 warnings' in read(log),read(log)
  binary=wrapper.with_suffix('.ex5');shutil.copy2(binary,dest/binary.name)
  original=settings(preset);assert float(original['InpRiskPercent'])==1.0
  assert original.get('InpAdaptivePortfolioControls','false')=='false'
  overrides={'InpTesterServerClockMode':'0','InpResearchBrokerUtcOffsetMinutes':'0'} if slug=='dmc' else {}
  params=dict(original,**overrides,InpStudyCase='sp500-'+slug+'-20260919',InpStudyLogin=str(a.login),InpStudyServer=a.server)
  meta['cases'][slug]=dict(label=label,period=period,source=str(source),preset=str(preset),preset_sha256=sha(preset),dependencies=deps,wrapper_sha256=sha(wrapper),binary_sha256=sha(binary),original_params=original,clock_overrides=overrides,params=params)
  print('COMPILED',slug,len(deps),'dependencies',flush=True)
 save(ROOT/'manifest.json',meta);return meta
def logs():return list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def run(meta,slug):
 item=meta['cases'][slug]; params=item['params'];case=params['InpStudyCase'];out=ROOT/'native'/case;out.mkdir(parents=True,exist_ok=True)
 for p,h in item['dependencies'].items():assert sha(Path(p))==h,'Source changed since compilation: '+p
 assert sha(Path(item['preset']))==item['preset_sha256']
 a,_=connect();assert a.login==meta['account']['login'] and a.server==meta['account']['server'];mt5.shutdown()
 fp=hashlib.sha256(json.dumps([item,meta['contract'],START,END,150,meta['account']['leverage']],sort_keys=True).encode()).hexdigest()
 if (out/'summary.json').exists():
  saved=json.loads((out/'summary.json').read_text())
  if saved.get('fingerprint')==fp:print('REUSE',slug,flush=True);return saved
 settext='\n'.join(k+'='+v for k,v in params.items())+'\n'
 (out/(case+'.set')).write_text(settext);(TESTER/'MQL5/Profiles/Tester'/(case+'.set')).write_text(settext)
 period='H1' if item['period']==60 else 'M'+str(item['period'])
 ini=out/'tester.ini';ini.write_text(f'''[Common]
Login={a.login}
Server={a.server}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\{EXPERT_DIR}\\{slug}
ExpertParameters={case}.set
Symbol={meta['symbol']}
Period={period}
Deposit=10000
Currency=USD
Leverage=1:{a.leverage}
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
ForwardMode=0
Report=reports\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 offsets={p:p.stat().st_size for p in logs()};began=time.time()
 save(ROOT/'progress.json',dict(state='running',slug=slug,label=item['label'],started_utc=datetime.now(timezone.utc).isoformat()))
 print('START',slug,item['label'],flush=True)
 p=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:p.wait(timeout=1800)
 except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=15);raise
 journal=''
 for f in logs():
  if f.stat().st_mtime<began:continue
  with f.open('rb') as h:h.seek(offsets.get(f,0));journal+=h.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt').write_text(journal,encoding='utf-8')
 report=TESTER/'reports'/(case+'.htm');assert report.exists() and report.stat().st_mtime>=began-2,'No fresh report: '+slug
 for f in report.parent.glob(case+'*'):
  if f.is_file() and f.stat().st_mtime>=began-2:shutil.copy2(f,out/f.name)
 audits=[f for f in (TESTER/'Tester').glob('Agent-*/MQL5/Files/'+case+'-equity.csv') if f.stat().st_mtime>=began-2]
 assert len(audits)==1,audits
 shutil.copy2(audits[0],out/'equity.csv')
 save(out/'run.json',dict(slug=slug,fingerprint=fp,elapsed_seconds=time.time()-began,**meta))
 row=parse(out);save(out/'summary.json',row);print('DONE',slug,row['return_pct'],row['trades'],flush=True);return row

def parse(out):
 run=json.loads((out/'run.json').read_text());slug=run['slug'];item=run['cases'][slug];case=item['params']['InpStudyCase'];report=out/(case+'.htm')
 inputs=_report_inputs(report)
 for k,v in item['params'].items():assert k in inputs and _same_setting(v,inputs[k]),(slug,k,v,inputs.get(k))
 stats=_native_metrics(report);trades=_native_trades(report,item['label']);text=_read_report(report);journal=(out/'journal.txt').read_text(encoding='utf-8')
 assert stats['initial_balance']==10000
 assert len(trades)==stats['trades'],(slug,len(trades),stats['trades'])
 assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.08
 match=re.search('SP500_AUDIT\\|'+re.escape(case)+r'\|([^\r\n]+)',journal);assert match,'Missing audit'
 audit={k:float(v) for k,v in (p.split('=',1) for p in match[1].split('|'))}
 assert abs(audit['final']-stats['final_balance'])<.03
 # Recover original order SL/TP and exact entry balance from native tables.
 orders={};entries={};section=''
 for row in BeautifulSoup(text,'html.parser').find_all('tr'):
  title=row.get_text(' ',strip=True)
  if title in ('Orders','Deals'):section=title;continue
  cells=[' '.join(c.get_text(' ',strip=True).split()) for c in row.find_all('td')]
  if not cells or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]):continue
  num=lambda s:float(s.replace(' ','').replace('\xa0','')) if s else 0.0
  if section=='Orders' and len(cells)==11:orders[cells[1]]={'stop':num(cells[6]),'target':num(cells[7])}
  elif section=='Deals' and len(cells)==13 and cells[4]=='in':
   key=(cells[0].replace('.','-',2).replace(' ','T',1),cells[3],num(cells[6]))
   assert key not in entries,'Ambiguous entry pairing'
   entries[key]=dict(**orders[cells[7]],balance_before=num(cells[11])-sum(num(cells[i]) for i in (8,9,10)))
 months=defaultdict(list);balance=10000
 for t in trades:
  assert t['symbol']==run['symbol']
  sign=1 if t['side']=='Long' else -1;contract=run['contract']['trade_contract_size']
  assert abs((t['close_price']-t['open_price'])*sign*t['volume']*contract-t['gross_profit'])<.12
  e=entries[(t['open_time'],'buy' if sign==1 else 'sell',t['open_price'])];t.update(e)
  risk=abs(t['open_price']-e['stop'])*t['volume']*contract if e['stop'] else None
  t['initial_risk_usd']=risk;t['initial_risk_pct']=100*risk/e['balance_before'] if risk else None
  t['initial_rr']=abs(t['target']-t['open_price'])/abs(t['open_price']-t['stop']) if risk and t['target'] else None
  t['net_r']=t['net_profit']/risk if risk else None
  balance+=t['net_profit'];t['balance_after']=round(balance,2)
  months[t['close_time'][:7]].append(t)
  t['open_time']+='+00:00';t['close_time']+='+00:00'
 def relative(label):
  m=re.match(r'([\d.]+)%',_metric(text,label));assert m,(slug,label);return float(m[1])
 grosswin=sum(max(t['net_profit'],0) for t in trades);grossloss=sum(max(-t['net_profit'],0) for t in trades)
 native_dd=relative('Equity Drawdown Relative')
 stats.update(slug=slug,label=item['label'],chart_period_minutes=item['period'],symbol=run['symbol'],fingerprint=run['fingerprint'],profit_factor=grosswin/grossloss if grossloss else None,
  win_rate_pct=100*sum(t['net_profit']>0 for t in trades)/len(trades) if trades else 0,
  native_equity_dd_pct=native_dd,tick_observed_equity_dd_pct=audit['equity_dd'],max_drawdown_pct=max(native_dd,audit['equity_dd']),balance_dd_pct=relative('Balance Drawdown Relative'),
  min_equity=audit['min_equity'],max_margin=audit['max_margin'],commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),
  max_initial_risk_pct=max((t['initial_risk_pct'] for t in trades if t['initial_risk_pct'] is not None),default=0),
  average_trade_usd=stats['net_profit']/len(trades) if trades else 0,report_sha256=sha(report),
  real_tick_start_lines=sorted(set(x.split('Ticks',1)[-1].strip() for x in journal.splitlines() if 'real ticks begin from' in x)),
  warnings=sorted(set(x.strip() for x in journal.splitlines() if any(s in x.lower() for s in ('real ticks absent','no real ticks','ticks discarded','mismatch','not enough money','no history data')))))
 ny=ZoneInfo('America/New_York')
 stats['overnight_trades']=sum(datetime.fromisoformat(t['open_time']).astimezone(ny).date()!=datetime.fromisoformat(t['close_time']).astimezone(ny).date() for t in trades)
 stats['market_closed_messages_present']='market closed' in journal.lower()
 stats['late_session_exits']=0
 if slug in ('vp','vpc','xny','xov','uny','uh1','usel','momentum','sell'):
  zone=timezone.utc if inputs.get('InpSessionZone')=='1' else ny
  hour=float(inputs.get('InpHardExitNyHour',inputs.get('InpFlatHour',inputs.get('InpCloseHourNY','15'))))
  minute=0 if 'InpHardExitNyHour' in inputs else int(inputs.get('InpFlatMinute',inputs.get('InpCloseMinuteNY','55')))
  for t in trades:
   opened=datetime.fromisoformat(t['open_time']).astimezone(zone);closed=datetime.fromisoformat(t['close_time']).astimezone(zone)
   cutoff=opened.replace(hour=int(hour),minute=minute+round((hour-int(hour))*60),second=0,microsecond=0)
   t['late_session_exit_minutes']=max(0,(closed-cutoff).total_seconds()/60)
  stats['late_session_exits']=sum(t['late_session_exit_minutes']>1 for t in trades)
 for name,sign in [('win',1),('loss',-1)]:
  current=maximum=0
  for t in trades:current=current+1 if sign*t['net_profit']>0 else 0;maximum=max(current,maximum)
  stats['max_'+name+'_streak']=maximum
 stats['months']=[dict(month=m,trades=len(ts),wins=sum(t['net_profit']>0 for t in ts),net_profit=round(sum(t['net_profit'] for t in ts),2),commission=round(sum(t['commission'] for t in ts),2),swap=round(sum(t['swap'] for t in ts),2)) for m,ts in sorted(months.items())]
 stats['entry_date_segments']=[]
 for name,start,end in [('Before real-tick availability','2025-09-19','2026-01-01'),('Real-tick-available dates','2026-01-01','2026-09-19')]:
  subset=[t for t in trades if start<=t['open_time']<end]
  losses=sum(max(-t['net_profit'],0) for t in subset);wins=sum(max(t['net_profit'],0) for t in subset)
  stats['entry_date_segments'].append(dict(segment=name,trades=len(subset),net_profit=round(sum(t['net_profit'] for t in subset),2),profit_factor=wins/losses if losses else None,win_rate_pct=100*sum(t['net_profit']>0 for t in subset)/len(subset) if subset else 0))
 stats['tested_inputs']=inputs;save(out/'trades.json',trades);return stats
def report(rows):
 save(ROOT/'results.json',rows)
 lines=['# US500 transfer — unchanged active presets','',f'{START} inclusive to {END} exclusive. Each independent USD 10,000 test uses the saved 1% base risk. Native MT5 / 150 ms modeled delay. No optimization or adaptive portfolio overlay.','',
 '| Original preset transferred to US500 | Return | Net USD | Trades | Net win rate | Net PF | Equity DD | Commission | Swap | History quality |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
 for r in rows:
  pf=f"{r['profit_factor']:.2f}" if r['profit_factor'] is not None else 'N/A'
  wr=f"{r['win_rate_pct']:.2f}%" if r['trades'] else 'N/A'
  lines.append(f"| {r['label']} | {r['return_pct']:+.2f}% | {r['net_profit']:+.2f} | {r['trades']} | {wr} | {pf} | {r['max_drawdown_pct']:.2f}% | {r['commission']:.2f} | {r['swap']:.2f} | {r['history_quality']} |")
 lines+=['','## Limits','', '- This is a transfer screen of 12 active presets, not the hundreds of archived research variants and not a simultaneous portfolio.', '- Native spread and recorded commissions/swaps included. Delay models execution effects; live news fills are not demonstrated.', '- Real/generated tick coverage and warnings are retained in each summary. A year with generated ticks is not a full real-tick validation.', '- DMC historical clock only mapped from EET/UTC+3 to Exness UTC. No trading parameters retuned. Minimum lots/upward rounding can exceed 1%.', '- Sell Nasdaq uses the currently recommended dynamic-exit source/SET, not its archived fixed-pip baseline.', '- Equity DD uses the larger native relative value and tick-observed value. SL/TP are from original native order records; they are not the final trailing stop.', '- No system deployment or website/BAT changes. Gold Value Area full pipeline remains separate.']
 lines+=['','## Streaks and risk','', '| Preset | Max win streak | Max loss streak | Max initial risk | Native equity DD | Tick-observed DD |','|---|---:|---:|---:|---:|---:|']
 for r in rows:lines.append(f"| {r['label']} | {r['max_win_streak']} | {r['max_loss_streak']} | {r['max_initial_risk_pct']:.3f}% | {r['native_equity_dd_pct']:.2f}% | {r['tick_observed_equity_dd_pct']:.2f}% |")
 lines+=['','## Original settings retained','', '| Preset | Signal chart | Opening range | Target | Break-even trigger | Dynamic 50/20 | Other stop inputs |','|---|---|---|---|---|---|---|']
 for r in rows:
  p=r['tested_inputs'];tf=p.get('InpSignalTimeframe',p.get('InpDmCSignalTimeframe',str(r['chart_period_minutes'])))
  tf='H1' if tf=='16385' else 'M'+tf
  target=p.get('InpRewardRisk',p.get('InpTargetRMultiple','N/A'))
  if r['slug']=='overnight':target='Time exit; no fixed TP'
  else:target+='R'
  stop=', '.join(k.replace('Inp','')+'='+p[k] for k in ('InpStopMode','InpStopBufferATR','InpInitialStopATR','InpDmCStopATR','InpStopAtrMultiple','InpStopValue','InpEmergencyStopPercent') if k in p)
  lines.append(f"| {r['label']} | {tf} | {p.get('InpOpeningRangeMinutes','N/A')} min | {target} | {p.get('InpBreakEvenAtR','disabled')} | {p.get('InpUseDynamicTrailingSL',p.get('InpUseDynamic5020','false'))} | {stop} |")
 lines+=['','## Session-exit caveat','', 'Some native tests reject scheduled closes because the broker reports Market closed. Intraday strategies can therefore hold beyond their intended exit. Their actual ledger, including resulting swap, is retained rather than inventing a timely exit. A broker-session-aware exit audit is required before any US500 promotion. Overnight and multi-hour DMC/Month-End positions are not inherently violations.','', '| Preset | Overnight trades (NY dates) | Intraday exits >1 minute late | Market-closed messages |','|---|---:|---:|---|']
 for r in rows:lines.append(f"| {r['label']} | {r['overnight_trades']} | {r['late_session_exits'] if r['slug'] not in ('dmc','overnight','monthend') else 'N/A'} | {r['market_closed_messages_present']} |")
 lines+=['','## Tick-history date segments','', 'These partition the original full-year ledger by entry date; they are not independently restarted accounts. January onward is where broker real ticks become available, not a promise that every tick is real. Entries before January can close later.','', '| Preset | Entry-date segment | Trades | Net USD | Net PF |','|---|---|---:|---:|---:|']
 for r in rows:
  for s in r.get('entry_date_segments',[]):
   pf=f"{s['profit_factor']:.2f}" if s['profit_factor'] is not None else 'N/A'
   lines.append(f"| {r['label']} | {s['segment']} | {s['trades']} | {s['net_profit']:+.2f} | {pf} |")
 lines+=['','## Monthly net USD / trade count','']
 for r in rows:
  lines+=['### '+r['label'],'','| Month | Trades | Wins | Net USD | Commission | Swap |','|---|---:|---:|---:|---:|---:|']
  for m in r['months']:lines.append(f"| {m['month']} | {m['trades']} | {m['wins']} | {m['net_profit']:+.2f} | {m['commission']:.2f} | {m['swap']:.2f} |")
  lines+=['']
 (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--resume',action='store_true');ap.add_argument('--cases');ap.add_argument('--report-only',action='store_true');args=ap.parse_args()
 if args.report_only:
  rows=[]
  for p in sorted((ROOT/'native').glob('*/run.json')):
   r=parse(p.parent);save(p.parent/'summary.json',r);rows.append(r)
  report(rows);return
 meta=json.loads((ROOT/'manifest.json').read_text()) if args.resume else prepare()
 if args.prepare_only:return
 wanted=args.cases.split(',') if args.cases else list(meta['cases'])
 for slug in wanted:
  run(meta,slug);report([json.loads(p.read_text()) for p in sorted((ROOT/'native').glob('*/summary.json'))])
 save(ROOT/'progress.json',dict(state='completed',cases=wanted))
if __name__=='__main__':main()
