"""Native parity and independent website windows for the approved production XAU EA."""
import hashlib,importlib.util,json,shutil,subprocess
from pathlib import Path
from run_native import ROOT,PACKAGE,TESTER,run,text
from parse_native import parse
DEPLOY=ROOT/'Deployment';DEPLOY.mkdir(exist_ok=True)
SOURCE=PACKAGE/'AAA Final EAs'/'AAA Final News Pulse XAU Event Specific EA'/'AAA Final News Pulse XAU Event Specific EA.mq5'
SHARED=PACKAGE/'AAA Final EAs'/'AAA Final News Pulse EA'
OLD=PACKAGE/'News Pulse Full Coverage 2026-09-12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make_source(name,calendar):
 code=SOURCE.read_text().replace('../AAA Final News Pulse EA/',SHARED.as_posix()+'/').replace('..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh',(PACKAGE/'_Shared'/'CalyxAdaptivePortfolio.mqh').as_posix())
 code=code.replace((SHARED/'NewsPulseTesterCalendar.mqh').as_posix(),calendar.as_posix())
 (ROOT/(name+'Base.mqh')).write_text(code)
 original=(ROOT/'NativeBaseline.mq5').read_text()
 head=original[:original.index('int export_file')].replace('Base.mqh',name+'Base.mqh')
 window=original[original.index('int EventWindow()'):original.index('int OnInit()')]
 wrapper='''int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){if(EventWindow()>=0)OriginalTick();}
void OnTimer(){if(EventWindow()>=0)OriginalTimer();}
void OnDeinit(const int reason){OriginalDeinit(reason);}
'''
 (ROOT/(name+'.mq5')).write_text(head+window+wrapper)

log=DEPLOY/'production-compile.log'
subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
assert '0 errors, 0 warnings' in text(log),text(log)
make_source('NativeProductionParity',ROOT/'Calendar.mqh')
run('NativeProductionParity');stats,trades=parse('NativeProductionParity')
expected=json.loads((ROOT/'native'/'NativeFullBestV2'/'stats.json').read_text())
for k in ['final_balance','trades','win_rate_pct','max_drawdown_pct']:
 assert abs(stats[k]-expected[k])<.02,(k,stats[k],expected[k])
(DEPLOY/'PARITY.json').write_text(json.dumps({'passed':True,'stats':stats,'source_sha256':sha(SOURCE)},indent=2))
shutil.copy2(OLD/'OFFICIAL CALENDAR.json',DEPLOY/'OFFICIAL CALENDAR.json')
shutil.copy2(OLD/'NewsPulseTesterCalendar.mqh',DEPLOY/'NewsPulseTesterCalendar.mqh')
identity={'source_sha256':sha(SOURCE),'compiled_sha256':sha(SOURCE.with_suffix('.ex5')),'indexed_lookup':False,'event_window_guard':True,'changes':'Verified parity guard outside event windows; calendar include relocation only. Production event settings are unchanged.','dependencies':{str(p.relative_to(PACKAGE)).replace('\\','/'):sha(p) for p in [SHARED/'AAA_Final_Common.mqh',SHARED/'SafeRegimeFilter.mqh',SHARED/'DynamicTrailingSessionFilter.mqh',PACKAGE/'_Shared'/'CalyxAdaptivePortfolio.mqh']},'calendar_sha256':sha(DEPLOY/'NewsPulseTesterCalendar.mqh')}
(DEPLOY/'BUILD MANIFEST.json').write_text(json.dumps(identity,indent=2))
spec=importlib.util.spec_from_file_location('old_coverage',OLD/'run_coverage.py');coverage=importlib.util.module_from_spec(spec);spec.loader.exec_module(coverage);coverage.ROOT=DEPLOY
for period,start in coverage.WINDOWS.items():
 name='NativeXauEvent'+period
 make_source(name,DEPLOY/'NewsPulseTesterCalendar.mqh')
 run(name,start=start.replace('-','.'),end=coverage.END.replace('-','.'))
 folder=ROOT/'native'/name;report=folder/('news-event-'+name+'.htm')
 dest=DEPLOY/'Backtest Reports';dest.mkdir(exist_ok=True)
 for p in folder.glob('*.htm'):shutil.copy2(p,dest/p.name)
 for p in folder.glob('*.png'):shutil.copy2(p,dest/p.name)
 journal=(folder/'journal.txt').read_text()
 result=coverage.parse_result('news-pulse-xau',period,4,dest/report.name,journal)
 result['strategy_profile']='xau-event-specific-2026-09-19'
 result['optimization_in_sample']=True
 (DEPLOY/f'news-pulse-xau-{period}-model4.json').write_text(json.dumps(result,indent=2))
 print('WEBSITE',period,result['stats'],flush=True)
