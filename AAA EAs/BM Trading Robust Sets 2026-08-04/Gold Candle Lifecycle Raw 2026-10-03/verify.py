"""Independent causal reconstruction of every native entry attempt from exported bars."""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def streaks(v):
 wins=loss=bestw=bestl=0
 for x in v:
  if x>0:wins+=1;loss=0
  elif x<0:loss+=1;wins=0
  else:wins=loss=0
  bestw=max(bestw,wins);bestl=max(bestl,loss)
 return bestw,bestl
def main():
 m=pd.read_csv(R/'data/M1.csv.gz');times=m.time.to_numpy();spec=pd.read_csv(R/'data/spec.csv.gz').iloc[0];eps=spec.point*.11
 parents={tf:pd.read_csv(R/'data'/f'{tf}.csv.gz') for tf in ('H1','H4','D1')}
 cases=[];allattempts=allfills=0
 for file in sorted((R/'native').glob('*/result.json')):
  z=load(file)
  if z.get('export'):continue
  folder=file.parent;d=pd.read_csv(folder/'audit.csv.gz');e=d[d.event=='entry'];filled=e[e.retcode==10009];trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()));s=z['stats'];tf=z['timeframe'];pt=parents[tf].time.to_numpy();p=parents[tf];secs={'H1':3600,'H4':14400,'D1':86400}[tf]
  assert len(trades)==len(filled)==s['trades'] and not e.parent_epoch.duplicated().any()
  allattempts+=len(e);allfills+=len(filled)
  for row in e.itertuples():
   j=np.searchsorted(pt,row.parent_epoch);assert j>0 and pt[j]==row.parent_epoch
   b=p.iloc[j];prior=p.iloc[j-1]
   assert abs(b.open-row.parent_open)<eps and abs(prior.open-row.prior_open)<eps and abs(prior.close-row.prior_close)<eps
   assert prior.close<prior.open
   assert row.end_epoch==row.parent_epoch+secs and row.midpoint==row.parent_epoch+secs/2
   assert row.signal_epoch>=row.midpoint and row.signal_epoch+60<=row.epoch<row.end_epoch
   left,right=np.searchsorted(times,[row.parent_epoch,row.signal_epoch+60]);obs=m.iloc[left:right]
   assert len(obs)==row.observed_count and obs.iloc[-1].time==row.observed_until==row.signal_epoch
   assert abs(obs.high.max()-row.known_high)<eps
   first=obs[obs.time<row.midpoint];assert len(first)>0 and abs(first.high.max()-row.first_high)<eps
   assert abs(obs.iloc[-1].close-row.signal_close)<eps
   if not z['control']:
    assert row.first_high>=row.parent_open+spec.tick_size*.5-eps and row.signal_close<row.parent_open and row.decision_bid<row.parent_open
   proposed=row.known_high+(row.decision_ask-row.decision_bid)+2*spec.tick_size
   proposed=max(proposed,row.decision_ask+(spec.stops_level+2)*spec.point)
   stop=np.ceil((proposed-1e-10)/spec.tick_size)*spec.tick_size
   assert abs(stop-row.stop)<eps,('Causal stop mismatch',z['tag'],stop,row.stop)
   loss_per_lot=(row.stop-row.decision_bid)*spec.contract_size
   assert abs(row.actual_risk-loss_per_lot*row.volume)<.021
  net=np.array([t['net_profit'] for t in trades]);gp=net[net>0].sum();gl=-net[net<0].sum()
  assert abs(net.sum()-s['net'])<1e-6 and len(net)==s['trades']
  assert (s['pf'] is None and gl==0) or abs(gp/gl-s['pf'])<1e-9
  assert streaks(net)==(s['max_win_streak'],s['max_loss_streak'])
  for row,t in zip(filled.itertuples(),trades):
   open_epoch=int(pd.Timestamp(t['open_time'],tz='UTC').timestamp());assert row.epoch<=open_epoch<=row.epoch+2
   assert t['side']=='Short' and abs(row.volume-t['volume'])<1e-8
   assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
  cases.append(dict(tag=z['tag'],filled=len(filled),attempts=len(e),entries_rejected=len(e)-len(filled),causal_parent_and_prior=True,causal_first_half_and_signal=True,causal_stop=True,net_pnl_and_streaks=True))
 build=load(R/'BUILD.json')
 for name in ('Lifecycle','Export'):
  assert hashlib.sha256((R/'EA'/f'{name}.mq5').read_bytes()).hexdigest()==build[name]['source']
  assert hashlib.sha256((R/'EA'/f'{name}.ex5').read_bytes()).hexdigest()==build[name]['binary']
 result=dict(cases=cases,attempts_checked=allattempts,fills_checked=allfills,source_and_binary_unchanged=True,final_extrema_never_used_for_entry=True)
 (R/'VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
