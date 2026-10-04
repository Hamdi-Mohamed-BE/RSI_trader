"""Separate recomputation and source-signal/actual-fill audit; no runner imports."""
from pathlib import Path
import collections,gzip,hashlib,json,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
def main():
 build=json.loads((ROOT/'BUILD.json').read_text())
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert build['source_sha256']==sha(ROOT/'EA/VideoMatch.mq5') and build['binary_sha256']==sha(ROOT/'EA/VideoMatch.ex5')
 assert build['original_binary_sha256']==sha(ROOT.parent/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5')
 assert build['set_sha256']==sha(ROOT.parent/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set')
 assert build['helpers']=={p.name:sha(p) for p in (ROOT/'EA').glob('*.mqh')}
 complete=(ROOT/'SUMMARY.json').exists()
 rows=json.loads((ROOT/('SUMMARY.json' if complete else 'PROGRESS.json')).read_text());checks=[]
 for r in rows:
  meta=r['manifest'];folder=ROOT/'native'/meta['key'];d=pd.DataFrame(json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes())));sig=pd.read_csv(folder/'signals.csv.gz');v=d.net_profit.to_numpy()
  assert meta['source_sha256']==build['source_sha256'] and meta['binary_sha256']==build['binary_sha256']
  assert len(d)==r['native']['trades']==len(sig)
  assert abs(v.sum()-r['native']['net_profit'])<.12 and abs(v.sum()-r['stats']['net'])<1e-7
  win=(v>0).mean()*100;pf=v[v>0].sum()/-v[v<0].sum();assert abs(win-r['stats']['win_pct'])<1e-8 and abs(pf-r['stats']['pf'])<1e-8
  assert np.max(abs(d.gross_profit+d.commission+d.swap-d.net_profit))<.011
  op=pd.to_datetime(d.open_time,utc=True);cl=pd.to_datetime(d.close_time,utc=True);ny=op.dt.tz_convert('America/New_York');ss=pd.to_datetime(sig.signal_epoch,unit='s',utc=True).dt.tz_convert('America/New_York');ff=pd.to_datetime(sig.fill_epoch,unit='s',utc=True)
  assert ((ss.dt.hour==9)&(ss.dt.minute==30)&(ss.dt.dayofweek<5)).all()
  # Entry is processed when a new available M5 bar follows the completed
  # 09:30 signal. The existing EA has no stale-signal timeout. Quote gaps can
  # therefore delay that fill; record exceptions rather than silently changing
  # the baseline or pretending all executions occurred at 09:35.
  assert (ny.dt.date==ss.dt.date).all() and (ny.dt.dayofweek<5).all()
  normal=(ny.dt.hour==9)&(ny.dt.minute==35)
  delayed=[dict(signal=str(ss.iloc[i]),fill=str(ny.iloc[i]),delay_after_nominal_close_seconds=int(sig.fill_epoch.iloc[i]-sig.signal_epoch.iloc[i]-300)) for i in np.flatnonzero(~normal)]
  assert not ny.dt.date.duplicated().any();assert ((op-ff).dt.total_seconds().abs()<=2).all()
  assert (op>=pd.Timestamp(meta['start'].replace('.','-'),tz='UTC')).all() and (cl<=pd.Timestamp(meta['end'].replace('.','-'),tz='UTC')).all()
  assert all(a>=b for a,b in zip(op.iloc[1:],cl.iloc[:-1])),'Overlapping own positions'
  assert (sig.retcode==10009).all() and (sig.fill_epoch-sig.signal_epoch>=300).all()
  long=sig.direction>0;short=sig.direction<0
  assert (d.side=='Long').tolist()==long.tolist()
  assert (sig.loc[long,'signal_close']>sig.loc[long,'ema12']).all() and (sig.loc[short,'signal_close']<sig.loc[short,'ema12']).all()
  assert np.max(abs(d.open_price-sig.fill_price))<.011 and np.max(abs(d.volume-sig.volume))<1e-8
  par=meta['parameters']
  if par['body']>=1:assert (sig.loc[long,'signal_close']>sig.loc[long,'signal_open']).all()
  if par['body']==2:assert (sig.loc[short,'signal_close']<sig.loc[short,'signal_open']).all()
  if par['di']:assert (sig.loc[long,'plus_di']>sig.loc[long,'minus_di']).all() and (sig.loc[short,'minus_di']>sig.loc[short,'plus_di']).all()
  balance=np.r_[10000,10000+np.cumsum(v)];peak=np.maximum.accumulate(balance);assert abs(((peak-balance)/peak).max()*100-r['stats']['closed_dd_pct'])<1e-8
  w=l=mw=ml=0
  for z in v:w=w+1 if z>0 else 0;l=l+1 if z<0 else 0;mw=max(mw,w);ml=max(ml,l)
  assert mw==r['stats']['max_win_streak'] and ml==r['stats']['max_loss_streak']
  assert abs(d.commission.sum()-r['stats']['commission'])<1e-8 and abs(d.swap.sum()-r['stats']['swap'])<1e-8
  log=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode().splitlines()
  reasons=collections.Counter(re.split('stop modification failed[: ]*',line,flags=re.I)[-1] for line in log if 'stop modification failed' in line.lower())
  assert sum(reasons.values())==r['known_stop_modify_rejections']
  checks.append(dict(key=meta['key'],verified_trades=len(d),verified_signal_clock_body_ema_di_volume_costs=True,delayed_entries=delayed,stop_modification_rejection_reasons=dict(reasons)))
 assert len({r['manifest']['key'] for r in rows})==len(rows)
 if complete:assert len(rows)==24
 parity=json.loads((ROOT/'PARITY.json').read_text());assert parity['identical_entry_exit_volume_costs']
 result=dict(complete=complete,comparison_runs=len(checks),total_overlapping_window_trades=sum(x['verified_trades'] for x in checks),parity=parity,source_sha256=hashlib.sha256((ROOT/'EA/VideoMatch.mq5').read_bytes()).hexdigest(),checks=checks)
 if complete:(ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
