import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PACKAGE=ROOT.parent;TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
def text(p):
 raw=p.read_bytes();return raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
def run(name,delay=1,start='2025.09.19',end='2026.09.19'):
 out=ROOT/'native'/name;out.mkdir(parents=True,exist_ok=True)
 source=ROOT/(name+'.mq5');log=out/'compile.log'
 subprocess.run(f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=50)
 assert '0 errors, 0 warnings' in text(log),text(log)
 dest=TESTER/'MQL5'/'Experts'/'AAA Research'/'News Event Params 20260919';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),dest/(name+'.ex5'))
 original=PACKAGE/'Selected Portfolio Settings 2026-09-01'/'12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'
 config=dict(l.split('=',1) for l in text(original).splitlines() if '=' in l and not l.startswith(';'))
 config.update(InpTesterFromDateUTC=start.replace('.',''),InpTesterToDateUTC=end.replace('.',''),InpEnableBuySide='true',InpEnableSellSide='true',InpAdaptivePortfolioControls='false')
 setname='news-event-'+name+'.set';settext='\n'.join(k+'='+v for k,v in config.items())+'\n'
 (out/setname).write_text(settext);(TESTER/'MQL5'/'Profiles'/'Tester'/setname).write_text(settext)
 ini=out/'tester.ini';ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert=AAA Research\\News Event Params 20260919\\{name}
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
Report=reports\\news-event-{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 journal=TESTER/'Tester'/'logs'/'20260919.log';offset=journal.stat().st_size
 print('START '+name,flush=True);start=time.time()
 p=subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',creationflags=subprocess.CREATE_NO_WINDOW)
 try:p.wait(timeout=900)
 except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=15);raise
 with journal.open('rb') as f:f.seek(offset);journaltext=f.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt').write_text(journaltext,encoding='utf-8')
 report=TESTER/'reports'/('news-event-'+name+'.htm');assert report.exists(),'Missing native report'
 for r in report.parent.glob('news-event-'+name+'*'):shutil.copy2(r,out/r.name)
 if name=='NativeBaseline':
  files=list((TESTER/'Tester').glob('Agent-*/MQL5/Files/news-event-quotes-20260919.csv'));assert len(files)==1
  shutil.copy2(files[0],ROOT/'quotes.csv')
 print('DONE '+name+' '+str(round(time.time()-start))+' seconds',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='NativeBaseline');p.add_argument('--delay',type=int,default=1);p.add_argument('--start',default='2025.09.19');a=p.parse_args();run(a.name,a.delay,a.start)
