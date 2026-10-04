"""Independent daily recurrence + paired block resampling diagnostics, not forecasts."""
import json
import numpy as np
import pandas as pd
from sma200 import ROOT,save
out={}
for symbol in ['QQQ','TQQQ']:
 e=pd.read_csv(ROOT/'etf'/f'{symbol}-16y-baseline/equity.csv').equity.to_numpy();r=np.r_[e[0]/10000-1,e[1:]/e[:-1]-1];log=np.log1p(r);n=len(log);rng=np.random.default_rng(20261002);values=[]
 for batch in range(20):
  start=rng.integers(0,n,size=(1000,(n+19)//20));ix=(start[:,:,None]+np.arange(20)[None,None,:])%n;sample=log[ix.reshape(1000,-1)[:,:n]]
  values.extend(np.expm1(sample.sum(axis=1))*100)
 values=np.array(values);out[symbol]={'paths':20000,'block_length_trading_days':20,'diagnostic_scope':'Resamples observed strategy daily equity returns; does NOT rerun SMA on bootstrapped fund prices or forecast future performance. Same index seed across funds. Historical selection/regime bias remains.','sample_sessions':n,'probability_positive_resampled_total_pct':float((values>0).mean()*100),'resampled_total_return_p05_pct':float(np.quantile(values,.05)),'resampled_total_return_median_pct':float(np.median(values)),'resampled_total_return_p95_pct':float(np.quantile(values,.95))}
save(ROOT/'ETF BOOTSTRAP.json',out);print(json.dumps(out,indent=2))
