"""Paired risk-rule experiment. Uses saved MT5 outcomes; never connects to MT5."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, random, statistics
import engine

OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'FTMO Combination Study 2026-09-19'
RULES=('flat','loss_1_5x')
PLANS=[dict(name='Raw Gold',keys=[engine.RAW],news_risk=10.),
       dict(name='Raw Gold + XAU/XAG news',keys=[engine.RAW]+engine.NEWS,news_risk=10.)]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):engine.save(p,v)
def old_engine():
    spec=importlib.util.spec_from_file_location('frozen_ftmo_engine',SOURCE/'simulate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def parity(old,new):
    for k,v in old.items():
        if k=='log':continue
        assert new[k]==v,(k,new[k],v)
    for before,after in zip(old['log'],new['log']):
        assert all(after[k]==v for k,v in before.items())

def aggregate(rr,start):
    out=engine.aggregate(rr)
    quant=lambda v,p:sorted(v)[int(p*(len(v)-1))]
    paid=[r for r in rr if r['payout']]
    funded=[r for r in rr if r['funded']]
    epoch=lambda s:engine.datetime.fromisoformat(s).timestamp()
    out.update(phase1_pass_pct=100*sum(bool(r['passes']) for r in rr)/len(rr),
               median_days_to_funding=statistics.median((epoch(r['funded_at'])-start)/engine.DAY for r in funded) if funded else None,
               median_days_to_receipt=statistics.median((epoch(r['receipt_at'])-start)/engine.DAY for r in paid) if paid else None,
               max_admitted_single_risk=max(r['max_admitted_single_risk'] for r in rr),
               p95_admitted_single_risk=quant([r['max_admitted_single_risk'] for r in rr],.95),
               max_requested_risk=max(r['max_requested_risk'] for r in rr),
               p95_requested_risk=quant([r['max_requested_risk'] for r in rr],.95),
               mean_escalated_rejections=statistics.mean(r['counts'].get('escalated_rejections',0) for r in rr))
    return out

def compact(r):
    return {k:r[k] for k in ('funded','payout','eligible','breach','inactive','phase','funded_at','receipt_at','breach_at','reward','balance','trades','win_rate','model_dd_pct','worst_daily_usd','max_requested_risk','max_admitted_single_risk','max_admitted_multiplier','max_loss_streak','counts','final_loss_state')}

def run_case(data,cfg,months,stress,n,block=1):
    start,end=engine.window(months);old=old_engine()
    rows,places=engine.shifted_data(data,cfg['keys'],start,end)
    historical={r:engine.replay(rows,places,start,end,news_risk=cfg['news_risk'],stress=stress,risk_profile=r,detail=True) for r in RULES}
    parity(old.replay(rows,places,start,end,news_risk=cfg['news_risk'],stress=stress,detail=True),historical['flat'])
    rng=random.Random(20260920 if block==1 else 20260921)
    size=math.ceil((end-start)/(block*engine.WEEK))+1
    outcomes={r:[] for r in RULES}
    summaries={r:[] for r in RULES}
    for idx in range(n):
        sample=[rng.randrange(27-block) for _ in range(size)]
        rr,pp=engine.shifted_data(data,cfg['keys'],start,end,sample,block_weeks=block)
        for rule in RULES:
            result=engine.replay(rr,pp,start,end,news_risk=cfg['news_risk'],stress=stress,risk_profile=rule)
            if idx<3 and rule=='flat':parity(old.replay(rr,pp,start,end,news_risk=cfg['news_risk'],stress=stress),result)
            summaries[rule].append(result);outcomes[rule].append(compact(result))
    delta=[int(b['payout'])-int(a['payout']) for a,b in zip(outcomes['flat'],outcomes['loss_1_5x'])]
    mean=statistics.mean(delta);se=statistics.stdev(delta)/math.sqrt(n) if n>1 else 0
    stem=f"{'gold-news' if len(cfg['keys'])>1 else 'gold'}-{months}m-{'stress' if stress else 'reference'}-{block}w"
    save(OUT/(stem+'-paths.json'),dict(plan=cfg,months=months,block_weeks=block,outcomes=outcomes))
    result=dict(plan=cfg,months=months,start=engine.iso(start),end_exclusive=engine.iso(end),stress=stress,block_weeks=block,
                rules={rule:dict(historical=historical[rule],bootstrap=aggregate(summaries[rule],start)) for rule in RULES},
                paired_payout_change_percentage_points=100*mean,paired_monte_carlo_95pct_interval=[100*(mean-1.96*se),100*(mean+1.96*se)],path_file=stem+'-paths.json')
    print(stem,json.dumps({rule:result['rules'][rule]['bootstrap'] for rule in RULES}),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--paths',type=int,default=1000);parser.add_argument('--skip-sensitivity',action='store_true');args=parser.parse_args()
    data=engine.read(SOURCE/'prepared.json');results=[]
    for cfg in PLANS:
        for months in (2,4,6):
            for stress in (False,True):
                results.append(run_case(data,cfg,months,stress,args.paths))
                save(OUT/'results.json',dict(paths_per_rule=args.paths,results=results))
    if not args.skip_sensitivity:
        for months in (2,4,6):
            results.append(run_case(data,PLANS[1],months,True,args.paths,block=2))
            save(OUT/'results.json',dict(paths_per_rule=args.paths,results=results))
    paths=[SOURCE/'prepared.json',SOURCE/'simulate.py',SOURCE/'prepare.py',OUT/'PROTOCOL.md',OUT/'engine.py',Path(__file__),OUT/'test_engine.py']
    save(OUT/'SOURCE MANIFEST.json',{str(p):sha(p) for p in paths})

if __name__=='__main__':main()
