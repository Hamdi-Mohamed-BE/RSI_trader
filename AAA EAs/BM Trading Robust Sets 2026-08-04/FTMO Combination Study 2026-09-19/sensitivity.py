"""Two-week dependence check on frozen news/high-win comparisons; never live."""
import math,random,hashlib
from simulate import ROOT,read,save,plans,window,shifted_data,replay,aggregate,WEEK

def main():
    data=read(ROOT/'prepared.json');configs=plans(read(ROOT/'audit.json'))
    selected={'Raw + XAU/XAG news, $10/order','High-win + news','Raw + USDJPY + news'}
    result=[]
    for cfg in configs:
        if cfg['name'] not in selected:continue
        for months in (2,4,6):
            start,end=window(months);rng=random.Random(20260921);rr=[]
            for _ in range(1000):
                sample=[rng.randrange(25) for _ in range(math.ceil((end-start)/(2*WEEK))+1)]
                rows,places=shifted_data(data,cfg['keys'],start,end,sample,block_weeks=2)
                rr.append(replay(rows,places,start,end,news_risk=cfg['news_risk'],stress=True))
            out=dict(plan=cfg['name'],months=months,stress_two_week=aggregate(rr))
            result.append(out);print(cfg['name'],months,out['stress_two_week']['payout_pct'],flush=True)
            save(ROOT/'sensitivity.json',dict(results=result,seed=20260921,block_weeks=2,paths=1000))

if __name__=='__main__':main()
