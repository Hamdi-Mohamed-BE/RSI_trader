"""Research-only native MT5 harness. Never attaches EAs to the normal terminal."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
PREVIOUS=PACKAGE/'News Pulse Event Parameters Research 2026-09-19'
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
sys.path.insert(0,str(PACKAGE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _native_trades, _read_report, _metric

START='2025.09.19'; END='2026.09.19'; HOLDOUT='2026.05.19'
ASSETS={
 'XAG':dict(symbol='XAGUSD',unit=.02,set='Selected Portfolio Settings 2026-09-01/12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set'),
 'BTC':dict(symbol='BTCUSD',unit=12.5,set='Selected Portfolio Settings 2026-09-01/12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set'),
 'EURUSD':dict(symbol='EURUSD',unit=.0001,set='active EAs with code and saves and charts/13 AAA Final News Pulse/Save File/12C News Pulse EURUSD Two Sided - HARD 1.5 TOTAL.set'),
}
def read(path):
 b=path.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def save(path,obj):path.write_text(json.dumps(obj,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def settings(asset):
 return dict(line.split('=',1) for line in read(PACKAGE/ASSETS[asset]['set']).splitlines() if '=' in line and not line.startswith(';'))

def prepare():
 ROOT.mkdir(exist_ok=True)
 for f in ('Base.mqh','Calendar.mqh','calendar.json'):
  shutil.copy2(PREVIOUS/f,ROOT/f)
 for a in ASSETS:
  dest=ROOT/a;dest.mkdir(exist_ok=True)
  s=settings(a);save(dest/'baseline-settings.json',s)
  code=(PREVIOUS/'NativeBaseline.mq5').read_text()
  # No quote export alongside synchronous trade operations: use a separate pass.
  head=code[:code.index('int export_file')]
  window=code[code.index('int EventWindow()'):code.index('int OnInit()')]
  wrapper='''int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){if(EventWindow()>=0)OriginalTick();}
void OnTimer(){if(EventWindow()>=0)OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}
'''
  (ROOT/f'{a}Baseline.mq5').write_text(head+window+wrapper)
  quote=(PREVIOUS/'NativeQuotesOnly.mq5').read_text().replace('news-clean-quotes-20260919.csv',f'multi-news-{a}-quotes.csv')
  quote=quote.replace('return INIT_SUCCEEDED;', '''PrintFormat("MULTI_SPEC|digits=%d|point=%.10f|ticksize=%.10f|contract=%.8f|lot_min=%.8f|lot_step=%.8f|lot_max=%.8f|stops=%d|freeze=%d|currency=%s|leverage=%d",
_Digits,_Point,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL),AccountInfoString(ACCOUNT_CURRENCY),(int)AccountInfoInteger(ACCOUNT_LEVERAGE));
return INIT_SUCCEEDED;''')
  (ROOT/f'{a}Quotes.mq5').write_text(quote)
 save(ROOT/'manifest.json',dict(start=START,end_exclusive=END,holdout_from=HOLDOUT,assets=ASSETS,calendar_sha256=sha(ROOT/'calendar.json'),source_sha256=sha(ROOT/'Base.mqh'),broker='Exness-MT5Trial16',deposit=10000,leverage=2000,risk_per_side_percent=.75,both_directions_retained=True,scope='Research only; EURUSD stays inactive; production and website unchanged',connection_note='Normal MT5 MCP initialize returned authorization failed; isolated existing Exness research tester used instead. Not a connected-account/FTMO simulation.'))

def run(asset,variant='Baseline',delay=1,start=START):
 name=asset+variant;out=ROOT/'native'/name;out.mkdir(parents=True,exist_ok=True)
 source=ROOT/(name+'.mq5')
 # Holdout/delay variants use identical source with a distinct tester/report identity.
 if not source.exists():
  base=variant.replace('Holdout','').replace('Delay250','')
  shutil.copy2(ROOT/(asset+base+'.mq5'),source)
 compilelog=out/'compile.log'
 subprocess.run(f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{compilelog}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
 assert '0 errors, 0 warnings' in read(compilelog),read(compilelog)
 folder=TESTER/'MQL5'/'Experts'/'AAA Research'/'News Multi Event 20260919';folder.mkdir(parents=True,exist_ok=True)
 shutil.copy2(source.with_suffix('.ex5'),folder/(name+'.ex5'))
 config=settings(asset)
 config.update(InpTesterFromDateUTC=start.replace('.',''),InpTesterToDateUTC=END.replace('.',''),InpEnableBuySide='true',InpEnableSellSide='true',InpAdaptivePortfolioControls='false',InpTesterServerClockMode='0')
 setname='multi-news-'+name+'.set';settext='\n'.join(k+'='+v for k,v in config.items())+'\n'
 (out/setname).write_text(settext);(TESTER/'MQL5'/'Profiles'/'Tester'/setname).write_text(settext)
 ini=out/'tester.ini';ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\News Multi Event 20260919\\{name}
ExpertParameters={setname}
Symbol={ASSETS[asset]['symbol']}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode={delay}
Optimization=0
FromDate={start}
ToDate={END}
Report=reports\\multi-news-{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 logdirs=[TESTER/'Tester'/'logs']+list((TESTER/'Tester').glob('Agent-*/logs'))
 offsets={p:p.stat().st_size for d in logdirs for p in d.glob('*.log')}
 t=time.time();print('START',name,flush=True)
 p=subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',creationflags=subprocess.CREATE_NO_WINDOW,cwd=TESTER)
 try:p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  p.terminate();p.wait(timeout=15);raise
 journal=''
 for d in [TESTER/'Tester'/'logs']+list((TESTER/'Tester').glob('Agent-*/logs')):
  for f in d.glob('*.log'):
   if f.stat().st_mtime<t:continue
   with f.open('rb') as h:h.seek(offsets.get(f,0));journal+=h.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt').write_text(journal,encoding='utf-8')
 report=TESTER/'reports'/f'multi-news-{name}.htm'
 assert report.exists() and report.stat().st_mtime>=t-2,'Missing fresh native report: '+name
 for r in report.parent.glob('multi-news-'+name+'*'):shutil.copy2(r,out/r.name)
 save(out/'run.json',dict(name=name,symbol=ASSETS[asset]['symbol'],start=start,end_exclusive=END,model=4,execution_delay_ms=delay,source_sha256=sha(source),binary_sha256=sha(source.with_suffix('.ex5')),settings=config,elapsed_seconds=round(time.time()-t,2)))
 if variant=='Quotes':
  files=[f for f in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/multi-news-{asset}-quotes.csv') if f.stat().st_mtime>=t-2]
  assert len(files)==1,files;shutil.copy2(files[0],ROOT/asset/'quotes.csv')
  match=re.search(r'MULTI_SPEC\|([^\r\n]+)',journal);assert match,'No symbol specification'
  spec=dict(x.split('=',1) for x in match[1].split('|'));save(ROOT/asset/'spec.json',spec)
 else:parse(asset,variant)
 print('DONE',name,round(time.time()-t),'seconds',flush=True)

def parse(asset,variant):
 name=asset+variant;out=ROOT/'native'/name;report=out/f'multi-news-{name}.htm'
 stats=_native_metrics(report);trades=_native_trades(report,'News Pulse '+asset)
 assert len(trades)==stats['trades']
 assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.10
 positive=sum(max(0,t['net_profit']) for t in trades);negative=sum(max(0,-t['net_profit']) for t in trades)
 stats['native_win_rate_pct']=stats['win_rate_pct'];stats['win_rate_pct']=100*sum(t['net_profit']>0 for t in trades)/len(trades) if trades else 0
 stats['profit_factor']=positive/negative if negative else None
 dd=re.match(r'([\d.]+)%',_metric(_read_report(report),'Equity Drawdown Relative'));assert dd
 stats['max_drawdown_pct']=float(dd[1]);stats['commission']=sum(t['commission'] for t in trades);stats['swap']=sum(t['swap'] for t in trades)
 journal=(out/'journal.txt').read_text()
 audit=re.search(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal)
 assert audit and audit[4]=='NO','Missing/invalid event audit'
 stats['calendar']=dict(expected=int(audit[1]),attempted=int(audit[2]),placed=int(audit[3]))
 for t in trades:
  m=re.match(r'NP\|(\d+)\|(NFP|CPI|FOMC)\|([BS])',t['entry_comment']);assert m,t
  t['event_epoch']=int(m[1]);t['event_kind']=m[2]
 save(out/'stats.json',stats);save(out/'trades.json',trades)
 print(name,json.dumps(stats),flush=True)
 return stats,trades

def candidates(asset):
 selected=json.loads((ROOT/asset/'selected.json').read_text())
 code=(PREVIOUS/'CandidateBase.mqh').read_text();(ROOT/'CandidateBase.mqh').write_text(code)
 base=(ROOT/(asset+'Baseline.mq5')).read_text().replace('"Base.mqh"','"CandidateBase.mqh"')
 boundary=base.index('int OnInit()');head=base[:boundary]
 for mode,label in [('full','Fitted'),('train','Train')]:
  function='void ApplySettings(const string kind) {\n'
  for k in ('NFP','CPI','FOMC'):
   p=selected[k][mode]['params_price']
   function+=f'if(kind=="{k}") {{InpPlacementLeadSeconds={int(p[0])};NPX_Anchor={int(p[1])};InpEntryOffsetPrice={p[2]:.10f};InpStopLossPrice={p[3]:.10f};NPX_TPR={p[4]};InpTrailStartR={p[5] if p[5] else 100000};InpTrailDistancePrice={p[6]:.10f};InpForceCloseSecondsAfterEvent={int(p[7])};}}\n'
  function+='}\n'
  wrapper='''int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTick();}
void OnTimer(){int index=EventWindow();if(index<0)return;ApplySettings(NP_GENERATED_EVENT_KINDS[index]);OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}
'''
  (ROOT/(asset+label+'.mq5')).write_text(head+function+wrapper)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','collect','run','candidates']);ap.add_argument('--assets',default=','.join(ASSETS));ap.add_argument('--variant',default='Baseline');ap.add_argument('--delay',type=int,default=1);ap.add_argument('--start',default=START);a=ap.parse_args()
 if a.phase=='prepare':prepare()
 else:
  for asset in a.assets.split(','):
   if a.phase=='collect':run(asset,'Quotes');run(asset,'Baseline')
   elif a.phase=='candidates':candidates(asset)
   else:run(asset,a.variant,a.delay,a.start)
