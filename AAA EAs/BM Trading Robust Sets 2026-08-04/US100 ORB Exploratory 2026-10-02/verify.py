"""Independent checks of emitted ledgers/signals using Python NY timezone and risk math."""
import gzip,io,math
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from native import ROOT,OUT,save,load,ledger,digest,sha
NY=ZoneInfo('America/New_York')
def main():
 summary=load(ROOT/'SUMMARY.json');frozen=load(ROOT/'FROZEN PRIMARY.json')
 assert frozen['source_main_sha']==sha(ROOT/'EA/Main.mqh')
 assert frozen['parameters_sha']==digest(frozen['parameters'])
 rows=[r for p in OUT.glob('*/results.json') for r in load(p)]
 count=0;signal_count=0;max_overfill=0;checked=[]
 for row in rows:
  d=ledger(row).sort_values(['close_epoch','position_id']);count+=len(d);s=row['stats'];c=row['parameters']
  gp=float(d.loc[d.net_profit>0,'net_profit'].sum());gl=-float(d.loc[d.net_profit<0,'net_profit'].sum())
  assert abs(s['net']-d.net_profit.sum())<.011
  if gl>0:assert abs(s['pf']-gp/gl)<=.00051
  assert np.allclose(d.net_profit,d.gross_profit+d.commission+d.swap+d.fee,atol=1e-7)
  assert (d.open_epoch>=pd.Timestamp(row['start'].replace('.','-'),tz='UTC').timestamp()).all()
  assert np.allclose(d.volume,d.closed_volume)
  signals=pd.read_csv(io.BytesIO(gzip.decompress((OUT/row['stage']/f"{row['index']}-signals.csv.gz").read_bytes())))
  signals=signals[signals.retcode==10009];signal_count+=len(signals);assert len(signals)==len(d)
  seen=set()
  for _,x in signals.iterrows():
   t=datetime.fromtimestamp(x.epoch,timezone.utc).astimezone(NY);b=datetime.fromtimestamp(x.signal_bar,timezone.utc).astimezone(NY)
   assert t.weekday()<5 and b.date()==t.date() and t.date() not in seen;seen.add(t.date())
   assert b.hour*60+b.minute>=570+c['opening_minutes'] and t.hour*60+t.minute<c['entry_cutoff']
   assert x.epoch-x.signal_bar>=300
   assert x.quoted_risk<=x.requested_risk+.02
   assert abs(x.initial_sl-(x.range_low if x.side>0 else x.range_high))<.011
   assert (x.signal_close>x.range_high) if x.side>0 else (x.signal_close<x.range_low)
   if c['direction']:assert x.side==c['direction']
   if c['ema']:assert x.h1_close>x.ema if x.side>0 else x.h1_close<x.ema
  if len(d):max_overfill=max(max_overfill,float((d.actual_risk/d.requested_risk).max()))
  checked.append(dict(stage=row['stage'],index=row['index'],closed_positions=len(d),clean=row['clean']))
 for name,row in summary['results'].items():
  if name.startswith('safe-raw'):continue
  assert row['parameters_sha']==frozen['parameters_sha'],'Post-lock parameter changed'
 payload=dict(passed=True,closed_positions_checked=count,filled_signals_checked=signal_count,maximum_actual_initial_risk_over_budget_ratio=max_overfill,checks=checked,
  limitations=['Initial-risk budget excludes commission and gap/slippage; fill risk can exceed quote risk.','Signals independently checked against their exported range/EMA values, not reconstructed from a second full OHLC dataset.','Trace equity is sampled once/minute; maximum drawdown is separately measured by native MT5 tick path.','Historical holiday calendars are unavailable; carryovers are counted.'])
 save(ROOT/'VERIFICATION.json',payload);print('Verified '+str(count)+' positions / '+str(signal_count)+' filled signals',flush=True)
if __name__=='__main__':main()
