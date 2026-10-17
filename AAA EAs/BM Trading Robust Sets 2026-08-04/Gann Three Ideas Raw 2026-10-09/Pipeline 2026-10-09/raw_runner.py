"""Standardised raw gates; original frozen EA, isolated tester, never live API."""
from pathlib import Path
import gzip, importlib.util, inspect, json, msvcrt, os, re, shutil, sys, traceback
R=Path(__file__).resolve().parent;RAW=R.parent;B=RAW.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('gann_raw_native',RAW/'run.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
n=g.n;n.R=R
CFG=dict(end_exclusive='2026-10-09',development=['2021-10-09','2023-10-09'],
 validation=['2023-10-09','2024-10-09'],oos=['2024-10-09','2026-10-09'],
 oos_label='Retrospective validation: already inspected in raw research, not untouched',
 risk_percent=1,deposit=10000,rounding='floor broker volume step; skip undersized/margin failures',
 native_model=4,delay_ms=150,screening_model=1,live_changes=False,push=False,
 scope='Research stages 1-6 only. Raw gate failures remain failures; no production promotion.',
 raw_gate='Positive net, PF >=1.15, >=30 whole positions in 3Y and 5Y; PF and mean net R better than signal control.')

def prepare():
 R.mkdir(parents=True,exist_ok=True)
 shutil.copy2(g.PRIOR/'ReadOnlyAudit.mqh',R/'ReadOnlyAudit.mqh')
 source=inspect.getsource(n.run_case)
 old="inputs['InpRiskPercent']='1.0'";assert source.count(old)==1
 source=source.replace(old,"inputs['InpRiskPercent']=row['input_settings']['InpRiskPercent']")
 exec(compile(source,str(R/'raw_runner.py')+'::native','exec'),n.__dict__)
 for file,value in [('run-config.json',CFG)]:
  p=R/file
  if p.exists():assert n.read(p)==value
  else:n.save(p,value)

def cases():
 original=g.plan()['cases'];rows=[]
 codes=[('XAUUSD','eighth-rejection'),('XAUUSD','quartile-control'),('USTEC','time-cycle'),
        ('USTEC','ema-baseline'),('USTEC','random-cycle'),('BTCUSD','quartile-control'),('BTCUSD','eighth-rejection')]
 for symbol,code in codes:
  base=next(x for x in original if x['symbol']==symbol and x['idea']==code and x['window']=='3y')
  for window,start in [('5y','2021.10.09'),('3y','2023.10.09')]:
   slug=f'gp-{symbol.lower()}-{code}-{window}'
   row=base|dict(slug=slug,window=window,start=start)
   row['input_settings']=base['input_settings']|dict(InpRiskPercent='1',InpSignalAuditTag=slug)
   rows.append(row)
 for symbol,code in [('XAUUSD','eighth-rejection'),('USTEC','time-cycle'),('BTCUSD','quartile-control')]:
  base=next(x for x in original if x['symbol']==symbol and x['idea']==code and x['window']=='3y')
  for window,start in [('1y','2025.10.09'),('6m','2026.04.09')]:
   slug=f'gp-{symbol.lower()}-{code}-{window}'
   row=base|dict(slug=slug,window=window,start=start)
   row['input_settings']=base['input_settings']|dict(InpRiskPercent='1',InpSignalAuditTag=slug)
   rows.append(row)
 return rows

def audit(q,folder):
 signals=n.export_rows(folder/'signals.csv');trades=sorted(q['trades'],key=lambda t:t['open_epoch'])
 assert len(signals)==len(trades)
 balance=10000
 for s,t in zip(signals,trades):
  assert int(s['signal_start_epoch'])<int(s['signal_close_epoch'])<=t['open_epoch']
  assert int(s['feature_known_epoch'])<=int(s['signal_close_epoch'])
  assert not int(s['anchor_epoch']) or int(s['anchor_epoch'])<int(s['feature_known_epoch'])
  assert abs(float(s['requested_risk_usd'])-balance*.01)<.011
  assert abs(float(s['stop'])-t['sl'])<1e-7 and abs(float(s['target'])-t['tp'])<1e-7
  assert float(s['lots'])==t['volume'];balance+=t['net']
 q['signal_audit_verified']=True
 q['signals']=signals

def main():
 prepare();rows=cases();n.save(R/'RAW PLAN.json',rows)
 state_path=R/'RAW STATUS.json';state=n.read(state_path) if state_path.exists() else dict(total=len(rows),complete={},failed={})
 for row in rows:
  if row['slug'] in state['complete']:continue
  try:
   n.START=row['start'];n.END=CFG['end_exclusive'].replace('-','.')
   binary,info=n.build(row);q=n.run_case(row,'raw',binary,info);folder=R/'native'/q['tag']
   signal=g.SIGNALS/(row['slug']+'.csv');owned=n.read(folder/'owned-process.json')
   assert signal.stat().st_mtime>=owned['started']-2
   shutil.copy2(signal,folder/'signals.csv');audit(q,folder)
   journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
   q['diagnostics']=sorted(set(re.findall(r'GANN_STATS[^\r\n]*',journal)))
   assert len(q['diagnostics'])==1
   q['execution_rejections']=int(re.search(r' rejected=(\d+)',q['diagnostics'][0]).group(1))
   assert not any(q['flags'][k] for k in ['init_failed','runtime','history','stopout','invalid_volume','export_failed'])
   q['tester_end_liquidations']=sum(any('end of test' in c.lower() for c in t['exit_comments']) for t in q['trades'])
   n.save(folder/'results.json',q);state['complete'][row['slug']]=str(folder/'results.json');state['failed'].pop(row['slug'],None)
  except Exception as e:
   state['failed'][row['slug']]=dict(error=str(e),trace=traceback.format_exc()[-5000:]);print('FAILED '+row['slug']+' '+str(e),flush=True)
  n.save(state_path,state);print('RAW PROGRESS',len(state['complete']),len(rows),'failed',len(state['failed']),flush=True)

if __name__=='__main__':
 with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);n.available();main()
