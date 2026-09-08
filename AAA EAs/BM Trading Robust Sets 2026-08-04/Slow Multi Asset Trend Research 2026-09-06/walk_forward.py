"""Rolling one-year train / six-month test re-selection over the fixed candidate grid."""
from pathlib import Path
import json, math
import pandas as pd
from research import ROOT,SYMBOLS,Config,load,run,dump

FOLDS=[
 ('fold-1','2023-09-01','2024-09-01','2024-09-01','2025-03-01'),
 ('fold-2','2024-03-01','2025-03-01','2025-03-01','2025-09-01'),
 ('fold-3','2024-09-01','2025-09-01','2025-09-01','2026-03-01'),
 ('fold-4','2025-03-01','2026-03-01','2026-03-01','2026-09-01'),
]

def fold_score(m):
    if m['trades']<5 or m['return_pct']<=0:return -10000+m['trades']
    pf=max(.01,min(3,m['profit_factor']));rec=max(-3,min(8,m['recovery']))
    return 4*math.log1p(m['return_pct'])+4*math.log(pf)+2.5*rec+1.5*max(-3,min(3,m['sharpe']))-.3*m['max_dd_pct']

def main():
    table=pd.read_csv(ROOT/'all-screen-results.csv');output={}
    for symbol in SYMBOLS:
        configs=[];seen=set()
        for raw in table.loc[(table.symbol==symbol)&(table.stage=='development'),'config']:
            c=json.loads(raw);key=json.dumps(c,sort_keys=True)
            if key not in seen:seen.add(key);configs.append(Config(**c))
        frame,_,_=load(symbol);rows=[]
        for name,tr0,tr1,te0,te1 in FOLDS:
            tr=(pd.Timestamp(tr0,tz='UTC'),pd.Timestamp(tr1,tz='UTC'));te=(pd.Timestamp(te0,tz='UTC'),pd.Timestamp(te1,tz='UTC'))
            assessed=[]
            for c in configs:
                m=run(frame,c,*tr);assessed.append((fold_score(m),c,m))
            _,choice,train=max(assessed,key=lambda x:x[0]);test=run(frame,choice,*te)
            rows.append(dict(fold=name,train_start=tr0,train_end=tr1,test_start=te0,test_end=te1,config=choice.asdict(),train={k:v for k,v in train.items() if k!='trades_data'},test={k:v for k,v in test.items() if k!='trades_data'}))
            print(symbol,name,'TEST',round(test['return_pct'],2),round(test['profit_factor'],2),test['trades'],flush=True)
        compounded=(math.prod(1+r['test']['return_pct']/100 for r in rows)-1)*100
        output[symbol]=dict(folds=rows,compounded_test_return_pct=compounded,positive_folds=sum(r['test']['return_pct']>0 for r in rows),total_test_trades=sum(r['test']['trades'] for r in rows))
        dump(ROOT/'walk-forward.json',output)

if __name__=='__main__':main()
