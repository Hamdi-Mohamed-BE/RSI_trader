"""M1-resolution retrospective claim audit, strictly separate from entry rules."""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
START=int(pd.Timestamp('2025-10-03',tz='UTC').timestamp());END=int(pd.Timestamp('2026-10-03',tz='UTC').timestamp())
def pct(x):return float(np.mean(x)*100) if len(x) else None
def summarize(d):
 prior=d[d.prior_red];first=prior[prior.first_up];current_red=d[d.red];current_green=d[~d.red & ~d.doji]
 return dict(candles=len(d),prior_red_candles=len(prior),red_overall_pct=pct(d.red),next_red_after_red_pct=pct(prior.red),next_red_after_nonred_pct=pct(d.loc[~d.prior_red,'red']),high_first_half_pct=pct(d.high_fraction<.5),low_first_half_pct=pct(d.low_fraction<.5),high_first_half_last_tie_pct=pct(d.high_last_fraction<.5),low_first_half_last_tie_pct=pct(d.low_last_fraction<.5),prior_red_high_first_half_pct=pct(prior.high_fraction<.5),prior_red_low_first_half_pct=pct(prior.low_fraction<.5),final_red_high_first_half_pct=pct(current_red.high_fraction<.5),final_green_low_first_half_pct=pct(current_green.low_fraction<.5),high_in_middle_40_60_pct=pct((d.high_fraction>=.4)&(d.high_fraction<.6)),low_in_middle_40_60_pct=pct((d.low_fraction>=.4)&(d.low_fraction<.6)),median_high_fraction=float(d.high_fraction.median()),median_low_fraction=float(d.low_fraction.median()),prior_red_first_up_candles=len(first),next_red_after_red_first_up_pct=pct(first.red),first_up_second_half_bearish_m1_candles=int((first.second_bear_count>0).sum()),high_tie_candles=int((d.high_fraction!=d.high_last_fraction).sum()),low_tie_candles=int((d.low_fraction!=d.low_last_fraction).sum()))
def daily_bootstrap(d):
 # Five consecutive broker-days, not independent M1 observations.
 z=d.assign(day=pd.to_datetime(d.time,unit='s',utc=True).dt.strftime('%Y-%m-%d'))
 per=z.groupby('day').apply(lambda g:pd.Series(dict(n=len(g),prior=g.prior_red.sum(),prior_and_red=(g.prior_red&g.red).sum(),nonprior=(~g.prior_red).sum(),nonprior_and_red=((~g.prior_red)&g.red).sum(),high_first=(g.high_fraction<.5).sum(),low_first=(g.low_fraction<.5).sum())),include_groups=False)
 n=len(per);rng=np.random.default_rng(20261003);starts=rng.integers(0,n,size=(10000,(n+4)//5));idx=(starts[:,:,None]+np.arange(5))%n;idx=idx.reshape(10000,-1)[:,:n];tot=per.to_numpy()[idx].sum(axis=1);columns={k:tot[:,i] for i,k in enumerate(per.columns)}
 prior=columns['prior_and_red']/columns['prior'];nonprior=columns['nonprior_and_red']/columns['nonprior'];delta=(prior-nonprior)*100
 return dict(method='Circular five-broker-day blocks, 10000 paths, seed 20261003; descriptive conditional intervals, not an untouched or multiple-search-adjusted significance test.',next_red_given_previous_red_p025_pct=float(np.quantile(prior,.025)*100),next_red_given_previous_red_p975_pct=float(np.quantile(prior,.975)*100),red_probability_difference_p025_pp=float(np.quantile(delta,.025)),red_probability_difference_p975_pp=float(np.quantile(delta,.975)))
def main():
 m=pd.read_csv(R/'data/M1.csv.gz');assert m.time.is_monotonic_increasing and not m.time.duplicated().any()
 spec=pd.read_csv(R/'data/spec.csv.gz').iloc[0];tick=spec.tick_size;eps=max(spec.point*.1,1e-7)
 assert ((m.high+eps>=m[['open','close','low']].max(axis=1))&(m.low-eps<=m[['open','close','high']].min(axis=1))).all()
 times=m.time.to_numpy();o=m.open.to_numpy();hi=m.high.to_numpy();lo=m.low.to_numpy();cl=m.close.to_numpy()
 summaries={};allrows=[];mismatches=[]
 for tf,secs in [('H1',3600),('H4',14400),('D1',86400)]:
  p=pd.read_csv(R/'data'/f'{tf}.csv.gz');assert p.time.is_monotonic_increasing and not p.time.duplicated().any();rows=[];outside=0;nohalves=0;matched=0
  for i,b in enumerate(p.itertuples()):
   if i==0 or b.time<START or b.time+secs>END:outside+=1;continue
   left,right=np.searchsorted(times,[b.time,b.time+secs]);n=right-left
   if n==0:raise AssertionError(('Missing M1 parent',tf,b.time))
   agg=[o[left],hi[left:right].max(),lo[left:right].min(),cl[right-1]];native=[b.open,b.high,b.low,b.close]
   if max(abs(x-y) for x,y in zip(agg,native))>eps:mismatches.append(dict(tf=tf,time=b.time,m1=agg,native=native))
   else:matched+=1
   tm=times[left:right];half=tm<b.time+secs/2
   if not half.any() or half.all():nohalves+=1;continue
   high_indices=np.flatnonzero(np.abs(hi[left:right]-agg[1])<eps);low_indices=np.flatnonzero(np.abs(lo[left:right]-agg[2])<eps)
   first_high=hi[left:right][half].max();second=(~half)&(tm+60<b.time+secs)
   prior=p.iloc[i-1];row=dict(timeframe=tf,time=int(b.time),end_epoch=int(b.time+secs),open=b.open,high=b.high,low=b.low,close=b.close,prior_open=float(prior.open),prior_close=float(prior.close),prior_red=bool(prior.close<prior.open),red=bool(b.close<b.open),doji=bool(b.close==b.open),first_up=bool(first_high>=b.open+tick*.5-eps),first_high=float(first_high),half_close=float(cl[left:right][half][-1]),second_bear_count=int(((cl[left:right]<b.open)&second).sum()),m1_rows=n,first_half_rows=int(half.sum()),second_half_rows=int((~half).sum()),high_fraction=float((tm[high_indices[0]]-b.time)/secs),high_last_fraction=float((tm[high_indices[-1]]-b.time)/secs),low_fraction=float((tm[low_indices[0]]-b.time)/secs),low_last_fraction=float((tm[low_indices[-1]]-b.time)/secs))
   rows.append(row);allrows.append(row)
  d=pd.DataFrame(rows);summary=summarize(d);summary.update(outside_year_or_missing_prior=outside,parents_without_quotes_in_both_halves=nohalves,ohlc_matching_parents=matched,continuation_uncertainty=daily_bootstrap(d));summaries[tf]=summary
 assert not mismatches,('Native/M1 OHLC mismatches',mismatches[:8])
 pd.DataFrame(allrows).to_csv(R/'CANDLE_DIAGNOSTICS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 result=dict(window='2025-10-03 to 2026-10-03 exclusive',symbol='XAUUSD',clock='MT5 broker-server candle boundaries; not NY daily close',resolution='1 minute; first and last occurrence of tied extrema',retrospective_extrema_not_entry_conditions=True,m1_rows=len(m),m1_first=int(times[0]),m1_last=int(times[-1]),price_point=float(spec.point),tick_size=float(tick),data_sha256=hashlib.sha256((R/'data/M1.csv.gz').read_bytes()).hexdigest(),timeframes=summaries,ohlc_mismatches=mismatches)
 (R/'CLAIM_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
