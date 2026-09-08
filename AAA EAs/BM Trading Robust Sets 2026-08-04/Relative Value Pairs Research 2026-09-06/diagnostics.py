"""Relationship tests and parameter sensitivity; never used to reselect final settings."""
import json
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint,adfuller
from research import ROOT,PAIRS,PERIODS,load_pair,dump

def main():
    rows=[]
    for pair in PAIRS:
        d,_,_=load_pair(pair)
        daily=np.log(d[['close_a','close_b']].resample('1D').last().dropna())
        for stage,(start,end) in PERIODS.items():
            if stage=='full':continue
            s=daily[(daily.index>=start)&(daily.index<end)]
            stat,pval,critical=coint(s.iloc[:,0],s.iloc[:,1],trend='c',maxlag=4,autolag='bic')
            slope,intercept=np.polyfit(s.iloc[:,1],s.iloc[:,0],1)
            residual=s.iloc[:,0]-slope*s.iloc[:,1]-intercept
            ar=np.polyfit(residual.to_numpy()[:-1],np.diff(residual),1)[0]
            half=-np.log(2)/np.log(1+ar) if -1<ar<0 else None
            rows.append(dict(pair=pair,period=stage,daily_observations=len(s),daily_return_correlation=float(s.diff().corr().iloc[0,1]),
                log_price_correlation=float(s.corr().iloc[0,1]),engle_granger_p=float(pval),ols_beta=float(slope),
                residual_half_life_days=float(half) if half else None,
                level_adf_p=[float(adfuller(s.iloc[:,i],maxlag=4,autolag='BIC')[1]) for i in (0,1)],
                first_difference_adf_p=[float(adfuller(s.iloc[:,i].diff().dropna(),maxlag=4,autolag='BIC')[1]) for i in (0,1)]))
    dump(ROOT/'relationship-diagnostics.json',rows)
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
