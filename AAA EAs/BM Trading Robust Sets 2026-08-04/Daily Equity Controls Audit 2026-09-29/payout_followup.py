"""Offline lifecycle scenarios. Uses saved source history only; no terminal APIs."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import hashlib, json, time
import numpy as np
from simulate import ROOT, read, save, run, specs, clock, configs, FIELDS

DAY=1440
PRAGUE=ZoneInfo('Europe/Prague')
CASES=[dict(name='Reference',stress=False,haircut=0.,delay=1),
       dict(name='Higher costs',stress=True,haircut=0.,delay=1),
       dict(name='Costs + weaker edge',stress=True,haircut=.10,delay=1),
       dict(name='5-minute liquidation',stress=False,haircut=0.,delay=5)]

def business_ready(t,n):
    dt=datetime.fromtimestamp(t*60,timezone.utc).astimezone(PRAGUE)
    while n:
        dt+=timedelta(days=1)
        if dt.weekday()<5:n-=1
    return int(dt.timestamp()//60)

def stage(data,sp,all_days,origin,start,end,cfg,case,profit,min_days,min_age):
    lo=start-origin;hi=end-origin+1
    v,logs,_,_=run(data['trades'],data['prices'][:,lo:hi],data['opens'][:,lo:hi],
        data['fresh'][:,lo:hi],sp,start,end,all_days[lo:hi],True,cfg['loss'],cfg['target'],cfg['cap'],
        case['stress'],False,False,case['delay'],profit,min_days,min_age,case['haircut'])
    m=dict(zip(FIELDS,map(float,v)))
    ok=m['stop_minute']>=0 and m['first_ftmo_breach_minute']<0 and m['open_at_end']==0
    # Basic accounting is asserted for every stage, including incomplete ones.
    closed_net=float(logs[:,4].sum()) if len(logs) else 0.
    if m['open_at_end']==0:assert abs(m['balance']-10000.-closed_net)<1e-6
    assert np.isfinite(v).all()
    return dict(start=start,end=int(m['stop_minute']) if m['stop_minute']>=0 else end,success=bool(ok),
        first_entry=int(logs[:,1].min()) if len(logs) else None,profit=m['balance']-10000.,metrics=m)

def lifecycle(data,sp,days,origin,start,end,cfg,case):
    stages=[];rewards=[];now=start;phase1=None;phase2=None;funded=None;breach=None;envelope=None
    for phase,profit in [(1,1000.),(2,500.)]:
        if now>end:break
        s=stage(data,sp,days,origin,now,end,cfg,case,profit,4,0);s['phase']=phase;stages.append(s)
        b=s['metrics']['first_ftmo_breach_minute'];e=s['metrics']['adverse_ftmo_flag_minute']
        if e>=0 and envelope is None:envelope=int(e)
        if b>=0:breach=int(b);break
        if not s['success']:break
        if phase==1:phase1=s['end'];now=business_ready(phase1,2)
        else:phase2=s['end'];now=business_ready(phase2,5);funded=now if now<=end else None
    if funded is not None and breach is None:
        while now<=end:
            s=stage(data,sp,days,origin,now,end,cfg,case,50.,0,14);s['phase']=3;stages.append(s)
            b=s['metrics']['first_ftmo_breach_minute'];e=s['metrics']['adverse_ftmo_flag_minute']
            if e>=0 and envelope is None:envelope=int(e)
            if b>=0:breach=int(b);break
            if not s['success']:break
            assert s['first_entry'] is not None and s['end']-s['first_entry']>=14*DAY
            assert s['profit']>=50.-1e-8
            rewards.append(dict(request=s['end'],gross=s['profit'],trader_share=.8*s['profit']))
            now=business_ready(s['end'],2)
    return dict(start=start,end=end,phase1=phase1,phase2=phase2,funded=funded,breach=breach,
        envelope_flag=envelope,rewards=rewards,stages=stages)

def distribution(values):
    a=np.asarray(values,float)
    if not len(a):return None
    return dict(n=len(a),min=float(a.min()),p10=float(np.quantile(a,.1)),median=float(np.median(a)),
                mean=float(a.mean()),p90=float(np.quantile(a,.9)),max=float(a.max()))

def summarize(paths,h):
    pp=[p for p in paths if p['end']-p['start']>=h*DAY]
    n=len(pp);counts={k:0 for k in ['phase1','phase2','funded','reward','breach','breach_before_reward','envelope_flag','unresolved']}
    times={k:[] for k in ['phase1','phase2','funded','first_reward','phase2_duration','funded_to_reward']}
    first=[];total=[];numbers=[]
    for p in pp:
        st=p['start'];end=st+h*DAY
        for k in ['phase1','phase2','funded','breach','envelope_flag']:
            if p[k] is not None and p[k]<=end:
                counts[k]+=1
                if k in times:times[k].append((p[k]-st)/DAY)
        rw=[r for r in p['rewards'] if r['request']<=end]
        failed=p['breach'] is not None and p['breach']<=end
        if rw:
            counts['reward']+=1;first.append(rw[0]['trader_share'])
            times['first_reward'].append((rw[0]['request']-st)/DAY)
            times['funded_to_reward'].append((rw[0]['request']-p['funded'])/DAY)
        elif failed:counts['breach_before_reward']+=1
        else:counts['unresolved']+=1
        total.append(sum(r['trader_share'] for r in rw));numbers.append(len(rw))
        if p['phase2'] is not None and p['phase2']<=end:
            times['phase2_duration'].append((p['phase2']-business_ready(p['phase1'],2))/DAY)
    return dict(horizon_days=h,starts=n,counts=counts,
        frequencies_pct={k:100*v/n for k,v in counts.items()},timing_days={k:distribution(v) for k,v in times.items()},
        first_reward_usd=distribution(first),total_trader_share_all_starts_usd=distribution(total),
        number_rewards_all_starts=distribution(numbers))

def main():
    a=read(ROOT/'recent-AUDIT.json');z=np.load(ROOT/'recent-prepared.npz')
    data={k:z[k] for k in z.files};sp=specs();origin=a['start'];end=a['end'];days=clock(origin,end)
    first=int(datetime(2025,9,29,tzinfo=timezone.utc).timestamp()//60)
    starts=list(range(first,end-30*DAY+1,7*DAY))
    result=dict(source_sha256=hashlib.sha256((ROOT/'recent-prepared.npz').read_bytes()).hexdigest(),
        protocol='PAYOUT_PROTOCOL.md',as_of='2026-09-29',scenarios=[],starts=starts)
    tic=time.time()
    for cfg in configs():
        for case in CASES:
            paths=[lifecycle(data,sp,days,origin,s,min(end,s+180*DAY),cfg,case) for s in starts]
            summ=[summarize(paths,h) for h in [30,60,90,120,180]]
            result['scenarios'].append(dict(config=cfg,case=case,summary=summ,paths=paths))
            save(ROOT/'PAYOUT_RESULTS.json',result)
            print(json.dumps(dict(policy=cfg['name'],case=case['name'],seconds=round(time.time()-tic,1),
                summary=[dict(days=x['horizon_days'],n=x['starts'],passed=x['counts']['phase2'],
                    rewards=x['counts']['reward'],breaches=x['counts']['breach']) for x in summ])),flush=True)

if __name__=='__main__':main()
