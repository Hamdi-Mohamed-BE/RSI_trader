"""Isolated native tests and audited raw-compatible ledgers."""
import argparse,importlib.util,json,hashlib,subprocess,shutil,time
from datetime import datetime,timezone
from data import ROOT,RAW,PACKAGE,NORMAL,save,sha
import MetaTrader5 as mt
from build import SOURCE,TESTER
spec=importlib.util.spec_from_file_location('onvp_native_parser',RAW/'run_raw.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
DEFAULT=dict(bins=64,va=70,stop=0,min_r=0.,entry_end=960,exit=960,target_r=0.,be=0.,trail=0.)
WINDOWS={'train':('2021.09.19','2024.09.19'),'validation':('2024.09.19','2025.09.19'),'5y':('2021.09.19','2026.09.19'),'3y':('2023.09.19','2026.09.19'),'1y':('2025.09.19','2026.09.19'),'6m':('2026.03.19','2026.09.19')}
def ident(c):return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()[:10]
def run(c,period,label='candidate',delay=150,risk=1,model=4):
 meta=json.loads((ROOT/'manifest.json').read_text());build=json.loads((ROOT/'build.json').read_text())
 assert sha(SOURCE)==build['source_sha256'] and sha(SOURCE.with_suffix('.ex5'))==build['binary_sha256']
 assert mt.initialize(NORMAL);a=mt.account_info();assert a.login==meta['account']['login'] and a.server==meta['account']['server'];mt.shutdown()
 start,end=WINDOWS[period];case=f'gva-{label}-{ident(c)}-{period}-d{delay}-r{risk}-m{model}'
 out=ROOT/'native'/case;out.mkdir(parents=True,exist_ok=True)
 params=dict(InpDirectionMode=0,InpBins=c['bins'],InpValueAreaPercent=c['va'],InpMinimumProfileBars=120,InpRiskPercent=risk,InpServerUTCOffsetHours=0,InpExpectedLogin=a.login,InpExpectedServer=a.server,InpMagic=89191901,InpCase=case,
 InpEntryEndMinute=c['entry_end'],InpExitMinute=c['exit'],InpStopMode=c['stop'],InpMinimumR=c['min_r'],InpTargetR=c['target_r'],InpBreakEvenR=c['be'],InpTrailDistanceR=c['trail'])
 fingerprint=hashlib.sha256(json.dumps([build,params,start,end,delay,model,meta['contract'],a.leverage],sort_keys=True).encode()).hexdigest()
 if (out/'summary.json').exists():
  r=json.loads((out/'summary.json').read_text());assert r['fingerprint']==fingerprint;return r
 text='\n'.join(f'{k}={v}' for k,v in params.items())+'\n';(out/(case+'.set')).write_text(text);(TESTER/'MQL5/Profiles/Tester'/(case+'.set')).write_text(text)
 ini=out/'tester.ini';ini.write_text(f'''[Common]
Login={a.login}
Server={a.server}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Gold VA Pipeline 20260919\\Gold Overnight Value Area Research
ExpertParameters={case}.set
Symbol={meta['symbol']}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:{a.leverage}
Model={model}
ExecutionMode={delay}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
 logs=lambda:list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
 offsets={p:p.stat().st_size for p in logs()};began=time.time()
 save(ROOT/'progress.json',dict(state='native-running',case=case,started_utc=datetime.now(timezone.utc).isoformat()))
 print('START',case,flush=True)
 p=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
 try:p.wait(timeout=1800)
 except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=15);raise
 journal=''
 for f in logs():
  if f.stat().st_mtime<began:continue
  with f.open('rb') as h:h.seek(offsets.get(f,0));journal+=h.read().decode('utf-16-le',errors='replace')
 (out/'journal.txt').write_text(journal,encoding='utf-8')
 report=TESTER/'reports'/(case+'.htm');assert report.exists() and report.stat().st_mtime>=began-2,case
 for f in report.parent.glob(case+'*'):
  if f.is_file() and f.stat().st_mtime>=began-2:shutil.copy2(f,out/f.name)
 audits=[f for f in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{case}-audit.csv') if f.stat().st_mtime>=began-2];assert len(audits)==1
 shutil.copy2(audits[0],out/'audit.csv')
 runmeta=dict(**meta,params=params,asset='XAU',mode='VA',symbols={'XAU':meta['symbol']},contracts={'XAU':meta['contract']},start=start,end_exclusive=end,fingerprint=fingerprint,build=build,config=c,period=period,label=label,delay=delay,risk=risk,model=model,elapsed_seconds=time.time()-began)
 save(out/'run.json',runmeta)
 r=legacy.parse_case(out);r.update(period=period,label=label,config=c,delay=delay,risk_percent=risk,model=model,directory=str(out),case=case)
 save(out/'summary.json',r)
 print('DONE',case,{k:r[k] for k in ('return_pct','trades','win_rate_pct','profit_factor','max_drawdown_pct')},flush=True)
 return r
def baseline():
 rows={}
 for period in ('1y','train','validation','5y','3y','6m'):
  r=run(DEFAULT,period,'raw');rows[period]=r;save(ROOT/'raw-results.json',rows)
  if period=='1y':
   old=json.loads((RAW/'native/onvp-xau-VA-20260919/trades.json').read_text());new=json.loads((__import__('pathlib').Path(r['directory'])/'trades.json').read_text())
   keys=['open_time','close_time','side','volume','open_price','close_price','net_profit','commission','swap','stop','target']
   assert [{k:t[k] for k in keys} for t in old]==[{k:t[k] for k in keys} for t in new],'Raw default ledger parity failed'
   save(ROOT/'raw-parity.json',dict(passed=True,trades=len(new),keys=keys))
 return rows
if __name__=='__main__':baseline()
