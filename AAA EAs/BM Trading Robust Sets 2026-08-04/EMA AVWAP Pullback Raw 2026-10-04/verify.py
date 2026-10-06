"""Independent causal anchor / VWAP reconstruction and position-ledger checks."""
import gzip,io,math
import numpy as np
import pandas as pd
import native
R=native.ROOT
def csv(row,name):return pd.read_csv(io.BytesIO(gzip.decompress((native.OUT/row['stage']/('0-'+name+'.csv.gz')).read_bytes())))
def verify(row):
 d=csv(row,'d1');h=csv(row,'h1');a=csv(row,'signals');b=csv(row,'bars');t=native.ledger(row)
 d=d.sort_values('epoch').reset_index(drop=True);h=h.sort_values('epoch').reset_index(drop=True)
 assert d.epoch.is_unique and h.epoch.is_unique
 for p in [9,21,50]:d['ema'+str(p)]=d.close.ewm(span=p,adjust=False).mean()
 d['tr']=np.maximum(d.high-d.low,np.maximum(abs(d.high-d.close.shift()),abs(d.low-d.close.shift())))
 # MT5 iATR uses arithmetic mean of true ranges, not a Wilder recursive ATR.
 d['atr']=d.tr.rolling(14).mean()
 max_vwap_error=0.;max_ema_error=0.;max_atr_error=0.
 for _,s in b.iterrows():
  # Features are sampled at signal completion, not at the candle's opening timestamp.
  seconds=int((s.expiry-s.epoch)/2)
  assert seconds in (60,300)
  decision=s.epoch+seconds
  ix=int(np.searchsorted(d.epoch.to_numpy(),decision,side='right')-1);assert ix>=65
  current=d.iloc[ix];prior=d.iloc[ix-1]
  side=int(s.side);assert s.anchor<current.epoch
  expected=None
  for lag in range(3,61):
   j=ix-lag;v=d.iloc[j].low if side>0 else d.iloc[j].high
   vals=[d.iloc[j+k].low if side>0 else d.iloc[j+k].high for k in [-2,-1,1,2]]
   if all(v<x for x in vals) if side>0 else all(v>x for x in vals):expected=int(d.iloc[j].epoch);break
  assert expected==int(s.anchor),(row['stage'],'anchor',expected,s.anchor)
  eligible=h[(h.epoch>=s.anchor)&(h.epoch+3600<=decision)]
  price=(eligible.high+eligible.low+eligible.close)/3
  vwap=float(np.average(price,weights=eligible.tick_volume))
  err=abs(vwap-s.avwap);max_vwap_error=max(max_vwap_error,err);assert err<.011,(row['stage'],'VWAP',err)
  for period in [9,21]:
   err=abs(prior['ema'+str(period)]-s['ema'+str(period)]);max_ema_error=max(max_ema_error,err);assert err<.011,(row['stage'],'EMA',period,err)
  err=abs(prior.atr-s.atr);max_atr_error=max(max_atr_error,err);assert err<.011,(row['stage'],'ATR',err,prior.atr,s.atr)
  assert side*(prior.ema9-prior.ema21)>0 and side*(prior.ema9-d.iloc[ix-2].ema9)>0 and side*(prior.close-prior.ema50)>0
  level=s.ema9 if abs(s.avwap-s.ema9)<=abs(s.avwap-s.ema21) else s.ema21
  assert abs(s.avwap-level)<=s.atr*.5+.02
  low,high=min(s.avwap,level),max(s.avwap,level)
  assert (s.signal_low<=high+.15*s.atr+.02 and s.signal_low>=low-.5*s.atr-.02 and s.signal_close>high-.02) if side>0 else (s.signal_high>=low-.15*s.atr-.02 and s.signal_high<=high+.5*s.atr+.02 and s.signal_close<low+.02)
  assert s.expiry==decision+seconds
 for _,s in a.iterrows():
  seconds=(s.signal_expiry-s.signal_bar)/2
  assert s.epoch>=s.signal_bar+seconds and s.epoch<s.signal_expiry
  assert s.side*(s.entry_quote-(s.signal_high if s.side>0 else s.signal_low))>0
  assert 0<s.side*(s.entry_quote-s.initial_sl)/s.entry_quote<=.025+.00001
  assert s.quoted_risk<=s.requested_risk+.02
  assert s.retcode in [10009,10016,10018,10019],(row['stage'],'execution',s.retcode)
 assert len(t)==int((a.retcode==10009).sum())
 assert len(t)==row['stats']['trades'] and abs(t.net_profit.sum()-row['stats']['net'])<.02
 assert np.allclose(t.gross_profit+t.commission+t.swap+t.fee,t.net_profit,atol=.011)
 assert (t.volume-t.closed_volume).abs().max()<1e-7 if len(t) else True
 maxrisk=float((t.actual_risk/t.requested_risk).max()) if len(t) else None
 return dict(stage=row['stage'],signals_verified=len(b),positions_verified=len(t),ema_max_abs_error=max_ema_error,atr_max_abs_error=max_atr_error,vwap_max_abs_error=max_vwap_error,max_filled_risk_to_budget=maxrisk,entry_failures=row['net']['entry_fail'],close_failures=row['net']['close_fail'],passed=True)
def main():
 result=[]
 for row in native.load(R/'SUMMARY.json'):
  result.append(verify(row));print(result[-1],flush=True)
 native.save(R/'VERIFICATION.json',result)
if __name__=='__main__':main()
