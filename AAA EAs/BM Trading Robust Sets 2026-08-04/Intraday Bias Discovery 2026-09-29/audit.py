"""Independent replay/formula and data-provenance checks; no rule selection."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
import numpy as np
import pandas as pd
import study
ROOT=Path(__file__).resolve().parent
def main():
 out={};collection=json.loads((ROOT/'COLLECTION.json').read_text())
 for f in collection['files']:
  raw=gzip.decompress((ROOT/'data'/f['file']).read_bytes())
  assert hashlib.sha256(raw).hexdigest()==f['sha256']
 out['source_file_hashes_verified']=len(collection['files'])
 fx=[]
 for sym in study.SYMS[6:]:
  earlier=ROOT.parent/'FX Fixing Reversal Research 2026-09-09/Data'/f'{sym}-M5.npz'
  old=pd.DataFrame(np.load(earlier)['rates'])[['time','open','high','low','close']]
  new=pd.read_csv(ROOT/'data'/f'{sym}_M5.csv.gz')
  joined=new.merge(old,on='time',suffixes=('_new','_old'));cols=['open','high','low','close']
  same=np.ones(len(joined),bool)
  for c in cols:same &= np.isclose(joined[c+'_new'],joined[c+'_old'],rtol=0,atol=1e-8)
  fx.append(dict(symbol=sym,common_bars=len(joined),identical_ohlc_pct=float(100*np.mean(same))))
  assert same.mean()>.995,'Unexpected historical revision/time alignment '+sym
 out['same_feed_prior_archive_comparison']=fx
 tests=subprocess.run([sys.executable,'-m','unittest','-v','test_study'],cwd=ROOT,capture_output=True,text=True)
 (ROOT/'TEST_RESULTS.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8');assert tests.returncode==0
 out['unit_tests']=14
 if (ROOT/'RESULTS.json').exists():
  results=json.loads((ROOT/'RESULTS.json').read_text())['results'];ledgers=pd.read_csv(ROOT/'selected-trades.csv.gz');checks=[]
  for row in results:
   c=row['candidate'];m=study.Market(c['symbol']);d=m.data.set_index('time');hold=ledgers.loc[(ledgers.symbol==c['symbol'])&(ledgers.phase=='holdout')]
   independent=[]
   for tr in hold.itertuples():
    a=d.loc[tr.time];b=d.loc[tr.exit_time]
    end=pd.Timestamp(tr.exit_time,unit='s',tz='UTC');start=pd.Timestamp(tr.time,unit='s',tz='UTC');local=start.tz_convert(c['clock'])
    assert local.hour*2+local.minute//30==c['slot']
    assert (end-start).total_seconds()==c['hold_minutes']*60
    assert start>=pd.Timestamp(study.DATES[2],tz='UTC') and end<pd.Timestamp(study.DATES[3],tz='UTC')
    pay_time=tr.time if c['direction']==1 else tr.exit_time
    quote=d.loc[pay_time];ny=pd.Timestamp(pay_time,unit='s',tz='UTC').tz_convert('America/New_York')
    spread=max(quote.spread,m.floors[ny.hour*2+ny.minute//30])*m.point
    cash=c['direction']*(b.open-a.open)-spread
    ret=cash/a.open*10000;independent.append(ret)
    assert abs(ret-tr.net_bps)<1e-7
   x=np.asarray(independent);h=row['phases']['holdout'];pf=x[x>0].sum()/-x[x<0].sum()
   assert len(x)==h['n'] and abs(pf-h['pf'])<1e-9 and abs(x.sum()/100-h['return_pct'])<1e-8
   checks.append(dict(symbol=c['symbol'],independently_recomputed_holdout_trades=len(x),pf=float(pf)))
  out['independent_holdout_replay']=checks
  p=np.array([r['raw_p'] for r in results]);idx=np.argsort(p);adj=np.maximum.accumulate(p[idx]*(len(p)-np.arange(len(p)))).clip(max=1)
  for i,v in zip(idx,adj):assert abs(v-results[i]['holm_p'])<1e-12
  out['holm_independently_verified']=True
 processes=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name = 'terminal64.exe'\" | Select-Object ProcessId,ExecutablePath,CreationDate | ConvertTo-Json -Compress"],capture_output=True,text=True)
 out['terminal_processes']=json.loads(processes.stdout)
 arr=out['terminal_processes'];arr=arr if isinstance(arr,list) else [arr]
 live=[x for x in arr if x['ExecutablePath'].lower()=='c:\\program files\\metatrader 5\\terminal64.exe'];assert len(live)==1 and live[0]['ProcessId']==11196
 assert not any('MT5-DMC-20260811'.lower() in x['ExecutablePath'].lower() for x in arr)
 out['live_original_pid_unchanged']=True
 diff=subprocess.run(['git','diff','--stat'],cwd=ROOT.parents[2],capture_output=True,text=True);assert diff.returncode==0 and not diff.stdout.strip();out['tracked_diff_empty']=True
 study.save('VERIFICATION.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
