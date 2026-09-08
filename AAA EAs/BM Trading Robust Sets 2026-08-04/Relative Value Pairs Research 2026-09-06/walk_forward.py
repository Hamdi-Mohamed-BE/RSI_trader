"""Supplemental rolling diagnostic; not a second untouched final test.

Use the predefined 900-cell broad grid, fit preceding 12 months, test next
three months. Hold cash unless training return is positive, PF >= 1.10,
at least 30 baskets, and M5-marked DD <= 15%. Thresholds are not optimized.
"""
import numpy as np
import pandas as pd
from research import ROOT,PAIRS,load_pair,features,simulate,params,broad_configs,METRICS,score,dump

def main():
    out=[]
    for pair in PAIRS:
        d,m,spec=load_pair(pair);cache={}
        for tf in (5,15,30,60,240):cache[tf]=features(d,tf,64,0)
        equity=10000.
        for start in pd.date_range('2024-09-01','2026-06-01',freq='3MS',tz='UTC'):
            train=start-pd.DateOffset(years=1);end=start+pd.DateOffset(months=3)
            rows=[]
            for c in broad_configs():
                mt,_,_=simulate(m,cache[c['tf']],spec,train.timestamp(),start.timestamp(),params(c),0.)
                r=dict(zip(METRICS,map(float,mt)));r['config']=c
                if r['return_pct']>0 and r['profit_factor']>=1.10 and r['trades']>=30 and r['dd_pct']<=15:rows.append(r)
            row=dict(pair=pair,train_start=str(train.date()),test_start=str(start.date()),test_end=str(end.date()),eligible_configs=len(rows))
            if rows:
                best=max(rows,key=score);c=best['config'];mt,t,eq=simulate(m,cache[c['tf']],spec,start.timestamp(),end.timestamp(),params(c),0.)
                row.update(config=c,training=best,test=dict(zip(METRICS,map(float,mt))))
                equity*=1+mt[0]/100
            else:row.update(config=None,test=dict(zip(METRICS,[0.]*len(METRICS))),decision='hold_cash_no_eligible_training_config')
            # Each fold's native-lot simulation restarts at 10k; this compound
            # illustration is not a continuous lot-exact portfolio simulation.
            row['normalized_compound_balance']=equity;out.append(row)
            print('WF',pair,row['test_start'],'eligible',len(rows),'return',row['test']['return_pct'],flush=True)
    dump(ROOT/'walk-forward.json',out)

if __name__=='__main__':main()
