"""Offline event-level, correlated-block prop risk research. No MT5 imports."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import argparse, hashlib, json, math, os, sys, time
import numpy as np
from numba import njit

ROOT=Path(__file__).resolve().parent
STORE=ROOT.parents[1]/'EA store'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(STORE))
from app.portfolio_analytics import performance

FIRMS=[dict(id='ftmo',label='FTMO 2-Step Swing',targets=[.10,.05],days=4,zone='Europe/Prague',
            sources=['https://ftmo.com/en/trading-objectives/','https://ftmo.com/en/2-step-challenge/'],
            status='EA use generally permitted; Swing needed for unchanged multi-day positions.'),
       dict(id='fundednext',label='FundedNext Stellar 2-Step (MT5 + EA add-on)',targets=[.08,.05],days=5,zone='Europe/Helsinki',
            sources=['https://help.fundednext.com/en/articles/17255124-stellar-2-step-challenge',
                     'https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit',
                     'https://help.fundednext.com/en/articles/14702245-what-are-the-risk-limits-on-a-fundednext-account',
                     'https://help.fundednext.com/en/articles/14702484-understanding-the-quick-strike-parameter-on-fundednext'],
            status='EA eligibility only below $50k and with EA access. Server DST date approximation uses Helsinki.'),
       dict(id='fundingpips',label='FundingPips 2-Step Standard + Swing add-on',targets=[.08,.05],days=3,zone='Etc/GMT-3',
            sources=['https://help.fundingpips.com/hc/en-us/articles/34501809112081-2-Step-Standard',
                     'https://help.fundingpips.com/hc/en-us/articles/34505029138449-Trading-Conduct-and-Security-Standards'],
            status='Conditional on approval of personally developed entry EAs; no intentional news trading. Swing add-on assumed. Opposite-side positions need conduct review.')]
POLICIES=['current_defaults','literal_buffer_7','guarded_buffer_7']
LABELS={'ftmo':'FTMO guarded roster (17)', 'current14-orb05':'Combined current + five ORBs (17)',
        'orbs-only':'Five ORBs at 0.5R (5)', 'full-eas':'Full roster (36/37 covered)'}
START='2025-10-06';END='2026-10-06';CAPITAL=25000.
FIELDS=['funded','phase1','pass_days','cause','failure_days','final_balance','closed_return_pct',
        'trades','wins','gross_wins','gross_losses','max_closed_dd_pct','max_daily_closed_dd_pct_initial',
        'max_win_streak','max_loss_streak','max_open_risk_pct_initial','min_risk_cash','max_risk_cash',
        'skipped_entries','risk_ceiling_flags','hedge_flags','open_positions','no_stop_closed_trades','phase2_days']

def epoch(s):return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def load_inputs():
    p=STORE/'data/portfolios.json';r=STORE/'data/portfolio-risk-ledgers.json'
    publication=json.loads(p.read_text());ledgers=json.loads(r.read_text())
    assert publication['risk_ledger_sha256']==sha(r),'Mixed-version portfolio evidence'
    meta={p['slug']:p for p in publication['portfolios']}
    assert set(meta)==set(LABELS)
    for key,p in meta.items():
        h=next(h for h in p['history'] if h['id']=='1y')
        assert h['available'] and h['start']==START and h['end_exclusive']==END
        if key=='orbs-only':assert all(m['target_rr']==.5 for m in p['members'])
    return publication,ledgers,meta

def freeze():
    _,ledgers,meta=load_inputs()
    plan=dict(version='2026-10-13',capital=CAPITAL,source_start=START,source_end_exclusive=END,
        ledger_sha256=sha(STORE/'data/portfolio-risk-ledgers.json'),publication_sha256=sha(STORE/'data/portfolios.json'),
        firms=FIRMS,policies=POLICIES,policy_details={
            'current_defaults':'Normalized 0.5% initial fixed risk for guarded FTMO; 0.5% balance combined/ORB; full 0.25% balance, news 0.10%, original adaptive tapers and Nasdaq x0.25.',
            'literal_buffer_7':'At each entry, max(0, current closed balance minus static 90% floor)/7. Does not subtract existing open risk or daily allowance. Original allocation weights/tapers and FTMO hard ceiling still apply. News also receives the formula in this literal stress test.',
            'guarded_buffer_7':'Min of (remaining total allowance minus open stop reserve)/7, (remaining firm daily allowance minus reserve)/7 and 0.5% initial capital. News capped at 0.10%. New-entry admission requires <=2% open risk, <=1% per symbol, and <=2% daily reserve; original FTMO guards additionally apply.'},
        ftmo_guard_note='Roster, entry limits and cash ceilings normalized to $25k for comparison, NOT the account-bound $10k executable guard. Margin, pending orders, 3-second lock and all live guard behavior are not reconstructed.',
        horizons=dict(challenge_calendar_days=180,fresh_funded_calendar_days=90),
        monte_carlo=dict(paths=2000,block_days=28,seed=20261013,weekday_aligned=True),
        fundingpips_reward_assumption='Standard bi-weekly programme, not Monthly 100% or On-Demand; no payout simulation. Monthly-specific 1% trade-idea striking rules are outside this run.',
        float_modes=['closed_only','full_stop_reserve_stress'],cost_stress='Winning gross P/L x0.90, losing gross x1.10, extra 0.05R cost; reserve x1.25. Not measured prop execution.',
        scope='Simulation only; no live EAs, BATs, website settings or firm registries changed.',
        limitations=[
            'All signals and exits are frozen; actual target ratios are retained, NOT changed to the video\'s 2R.',
            'Standalone broker-ledger overlay, not a simultaneous MT5 account test. No intraday equity data: neither closed-only nor full-stop reserve is an actual floating equity path or guaranteed bound.',
            'Simultaneous events use deterministic EA-slug ordering, with resets before exits before entries. Live broker sequencing and strategy signals after a skipped entry are not regenerated.',
            'Closed balance is the entry equity proxy; commission/swap aggregate booked at final exit. Intratrade partial timing, pending-order risk, firm-specific spread, contract size, slippage, margin and leverage are not reconstructed.',
            'Assume 0.01 minimum/step and round down. Too-small sizes skip, so asymptotic shrinkage can leave an unresolved or nearly inactive account.',
            'Whole 28-day Monday-start blocks keep simultaneous signals correlated. Durations carry across block boundaries; correlations across seams are imperfect. No IID trade shuffle. Long holdings can leave unvalued positions at horizon.',
            'Rolling-origin trials use their actual start dates for firm daily resets. Bootstrap dates are synthetic, beginning on October 6, 2025; their passing days are durations, not predicted future dates.',
            'Challenge passes require target, minimum entry days and flat account; target freezes new entries. Phase-1 handover assumed two calendar days. Results measure both targets reached, not actual KYC issuance time.',
            'Fresh-funded survival is measured for 90 calendar days with profits retained, no withdrawals. It is NOT payout or fee ROI; withdrawals reduce the loss buffer and need a separate run.',
            'FundingPips daily reset is UTC+3 and uses opening balance as proxy for max(balance,equity); opening floating gains are unknown. 30-day completed-trade inactivity enforced.',
            'FundedNext 30-second winning-profit share holds challenge advancement at >=30%, and is checked at 21-/14-day funded cycle ends. Its 3% funded exposure flags are shown, but full warning/deduction/reclassification mechanics are NOT simulated.',
            'FundedNext known news-EA positive cash credited at 40% on funded accounts; losses retained. Complete official speech/news-calendar tagging for other strategies unavailable. FundingPips full news roster is ineligible unchanged.',
            'FundingPips source ownership approval, conduct/hedging acceptance and news restrictions cannot be inferred from a mathematical pass. 50k+ funded strike variants are outside this $25k comparison.',
            'Full portfolio missing gold-news-v9-direction, 36/37 members; no zero-return substitute. Hourly EAs have no stop: their historical-loss reserve is NOT a maximum loss.',
            'Current ORB targets selected using the same recent data. Latest common coverage ends October 6, not today; no untouched-OOS claim and no credible under-1%-future-ruin certification.'
        ],members={k:[m['slug'] for m in p['members']] for k,p in meta.items()},
        missing={k:next(h for h in p['history'] if h['id']=='1y')['missing_members'] for k,p in meta.items()})
    (ROOT/'PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan

def source_array(rows,start,end,stress=False):
    begin,finish=epoch(start),epoch(end)
    eligible=sorted((r for r in rows if begin<=r['op']<r['cl']<finish and r['unit_risk']>0),key=lambda r:(r['op'],r['key'],r.get('position_id',0)))
    keys=sorted(set(r['key'] for r in eligible));symbols=sorted(set(r['symbol'] for r in eligible))
    lanes=sorted(set(r.get('lane',r['key']) for r in eligible))
    a=[]
    for r in eligible:
        risk=r['unit_risk'];g=r['unit_gross'];c=r['unit_comm'];sw=r['unit_swap']
        if stress:g*=.9 if g>0 else 1.1;c-=.05*risk
        a.append([(r['op']-begin)/86400,(r['cl']-r['op'])/86400,risk,(g+c+sw)/risk,
                  r.get('news',False),symbols.index(r['symbol']),lanes.index(r.get('lane',r['key'])),
                  r.get('risk_weight',1.),r['key']=='nasdaq-5m-candle-momentum',
                  'NO STOP' in str(r.get('risk_reference') or ''),r['cl']-r['op']<30,keys.index(r['key']),r.get('side')=='Long'])
    assert len(lanes)<100 and len(symbols)<100
    return np.asarray(a,float).reshape(-1,13),keys,symbols,dict(source_positions=len(eligible),covered_members=len(keys),
            maximum_holding_days=max(((r['cl']-r['op'])/86400 for r in eligible),default=0),
            no_stop_positions=sum('NO STOP' in str(r.get('risk_reference') or '') for r in eligible),
            native_costs_retained=True)

def resets(start,horizon,zone):
    first=datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    z=ZoneInfo(zone);local=first.astimezone(z).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    out=[]
    while local.timestamp()<first.timestamp()+horizon*86400:
        out.append((local.timestamp()-first.timestamp())/86400);local+=timedelta(days=1)
    return np.array(out,float)

@njit(cache=True)
def one_path(source,starts,block,horizon,resets_arr,firm,portfolio,policy,float_mode,initial_stage,capital,stress,detail):
    capacity=max(1,len(source)*len(starts))
    trades=np.empty((capacity,13));op=np.empty(capacity);cl=np.empty(capacity);n=0
    for b in range(len(starts)):
        left=starts[b];right=left+min(block,horizon-b*block)
        ia=np.searchsorted(source[:,0],left);ib=np.searchsorted(source[:,0],right)
        for j in range(ia,ib):
            trades[n]=source[j];op[n]=b*block+source[j,0]-left;cl[n]=op[n]+source[j,1];n+=1
    keys=np.empty(2*n+len(resets_arr));kind=np.empty(len(keys),np.int64);ids=np.empty(len(keys),np.int64);ne=0
    for i in range(n):
        keys[ne]=op[i]*4+2/86400;kind[ne]=2;ids[ne]=i;ne+=1
        if cl[i]<horizon:keys[ne]=cl[i]*4+1/86400;kind[ne]=1;ids[ne]=i;ne+=1
    for i,t in enumerate(resets_arr):keys[ne]=t*4;kind[ne]=0;ids[ne]=i;ne+=1
    order=np.argsort(keys[:ne],kind='mergesort');lot=np.zeros(n);risk=np.zeros(n)
    lane_losses=np.zeros(100,np.int64);group=np.zeros(100);longrisk=np.zeros(100);shortrisk=np.zeros(100)
    logs=np.empty((n if detail else 0,4));nlog=0
    bal=capital;peak=capital;anchor=capital;day_peak=capital;floor=.9*capital;daily_floor=anchor-.05*capital
    stage=initial_stage;ready=0.;phase1=-1.;pass_days=-1.;phase2=-1.;cause=0;fail=-1.;numactive=0
    reserve=0.;openrisk=0.;daily_count=0;daily_losses=0;entry_days=0;last_entry_day=-1;day_id=0
    last_close=0.;first_funded_entry=-1.;cycle_end=21.;posprofit=0.;quickprofit=0.;risk_flags=0.;hedge_flags=0.
    p1=.10 if firm==0 else .08;minimum=4 if firm==0 else 5 if firm==1 else 3
    total=0;wins=0;win_sum=0.;loss_sum=0.;ws=0;ls=0;maxw=0;maxl=0;dd=0.;daily_dd=0.
    maxrisk=0.;minbudget=1e100;maxbudget=0.;skips=0;no_stop=0
    for ei in order:
        what=kind[ei];i=ids[ei];t=keys[ei]/4-(2/86400 if what==2 else 1/86400 if what==1 else 0.)/4
        if initial_stage!=-1 and firm==2 and t-last_close>=30:
            cause=3;fail=last_close+30;break
        if firm==1 and stage==2 and first_funded_entry>=0 and t-first_funded_entry>=cycle_end:
            if posprofit>0 and quickprofit/posprofit>=.30:
                cause=4;fail=first_funded_entry+cycle_end;break
            cycle_end+=14;posprofit=0.;quickprofit=0.
        if what==0:
            day_id+=1;anchor=bal;day_peak=bal;daily_count=0;daily_losses=0
            daily_floor=anchor*(1-.05) if firm==2 else anchor-.05*capital
        elif what==2:
            r=trades[i];sym=int(r[5]);lane=int(r[6]);is_news=r[4]>0
            target=p1 if stage==0 else .05
            if t<ready or (0<=stage<2 and bal>=capital*(1+target) and entry_days>=minimum and (firm!=1 or posprofit==0 or quickprofit/posprofit<.30)):
                skips+=1;continue
            if portfolio==0 and (daily_count>=7 or daily_losses>=3):skips+=1;continue
            if portfolio==3 and not is_news and bal-anchor<=-.05*capital:skips+=1;continue
            if policy==0:
                budget=capital*.005 if portfolio==0 else bal*(.0025 if portfolio==3 else .005)
                if portfolio==3 and is_news:budget=bal*.001
            elif policy==1:budget=max(0.,bal-floor)/7
            else:
                budget=max(0.,min((bal-floor-reserve)/7,(bal-daily_floor-reserve)/7,.005*capital))
                if is_news:budget=min(budget,.001*capital)
            budget*=r[7]
            if portfolio==3 and not is_news:
                d=(peak-bal)/peak
                budget*=.25 if d>=.07 else .5 if d>=.04 else 1.
                budget*=.25 if lane_losses[lane]>=5 else .5 if lane_losses[lane]>=3 else 1.
                if r[8]>0:budget*=.25
            if portfolio==0:budget=min(budget,.005*capital)
            volume=math.floor(budget/r[2]*100+1e-10)/100
            if volume<.01:skips+=1;continue
            budget=volume*r[2];env=budget*(1.25 if stress else 1.)
            if portfolio==0:
                env=budget*1.25+5*capital/10000
                if openrisk+budget>.0225*capital or group[sym]+budget>.015*capital or bal-reserve-env<anchor-.03*capital or bal-reserve-env<.92*capital:
                    skips+=1;continue
            if policy==2 and (openrisk+budget>.02*capital or group[sym]+budget>.01*capital or bal-reserve-env<anchor-.02*capital):
                skips+=1;continue
            lot[i]=volume;risk[i]=env;reserve+=env;openrisk+=budget;group[sym]+=budget;numactive+=1;daily_count+=1
            if r[12]>0:
                if shortrisk[sym]>1e-8:hedge_flags+=1
                longrisk[sym]+=budget
            else:
                if longrisk[sym]>1e-8:hedge_flags+=1
                shortrisk[sym]+=budget
            if firm==1 and stage==2 and openrisk>.03*capital:risk_flags+=1
            if first_funded_entry<0 and stage==2:first_funded_entry=t
            if day_id!=last_entry_day:entry_days+=1;last_entry_day=day_id
            maxrisk=max(maxrisk,openrisk/capital*100);minbudget=min(minbudget,budget);maxbudget=max(maxbudget,budget)
        elif lot[i]>0:
            r=trades[i];sym=int(r[5]);lane=int(r[6]);budget=lot[i]*r[2];net=budget*r[3]
            if firm==1 and stage==2 and r[4]>0 and net>0:net*=.4
            bal+=net;reserve-=risk[i];openrisk-=budget;group[sym]-=budget;numactive-=1;lot[i]=0
            if r[12]>0:longrisk[sym]-=budget
            else:shortrisk[sym]-=budget
            reserve=max(0.,reserve);openrisk=max(0.,openrisk);group[sym]=max(0.,group[sym]);longrisk[sym]=max(0.,longrisk[sym]);shortrisk[sym]=max(0.,shortrisk[sym])
            last_close=t;total+=1;peak=max(peak,bal);day_peak=max(day_peak,bal)
            dd=max(dd,(peak-bal)/peak*100);daily_dd=max(daily_dd,(day_peak-bal)/capital*100)
            if net>.005:
                wins+=1;win_sum+=net;ws+=1;ls=0;posprofit+=net
                if r[10]>0:quickprofit+=net
                lane_losses[lane]=0
            elif net<-.005:
                loss_sum-=net;ls+=1;ws=0;daily_losses+=1;lane_losses[lane]+=1
            else:ws=0;ls=0;lane_losses[lane]=0
            maxw=max(maxw,ws);maxl=max(maxl,ls);no_stop+=int(r[9]>0)
            if detail:logs[nlog,0]=t;logs[nlog,1]=net;logs[nlog,2]=r[11];logs[nlog,3]=budget;nlog+=1
        equity=bal-(reserve if float_mode==1 else 0.)
        if initial_stage!=-1:
            if equity<=daily_floor+1e-8:cause=1;fail=t;break
            if equity<=floor+1e-8:cause=2;fail=t;break
        if stage>=0 and stage<2:
            target=p1 if stage==0 else .05
            if bal>=capital*(1+target) and entry_days>=minimum and numactive==0 and (firm!=1 or posprofit==0 or quickprofit/posprofit<.30):
                if stage==0:phase1=t;stage=1;ready=t+2;bal=capital;peak=capital;anchor=capital;day_peak=capital;daily_floor=capital*.95
                else:pass_days=t;phase2=t-phase1;stage=2;break
                entry_days=0;last_entry_day=-1;posprofit=0.;quickprofit=0.;daily_count=0;daily_losses=0;last_close=ready
    out=np.array([int(stage==2),int(phase1>=0),pass_days,cause,fail,bal,(bal/capital-1)*100,total,wins,win_sum,loss_sum,dd,daily_dd,maxw,maxl,maxrisk,minbudget if minbudget<1e99 else 0.,maxbudget,skips,risk_flags,hedge_flags,numactive,no_stop,phase2])
    return out,logs[:nlog]

@njit(cache=True)
def many_paths(source,starts,block,horizon,reset_array,firm,portfolio,policy,float_mode,stage,capital,stress):
    result=np.empty((len(starts),24))
    for i in range(len(starts)):
        out,_=one_path(source,starts[i],block,horizon,reset_array,firm,portfolio,policy,float_mode,stage,capital,stress,False)
        result[i]=out
    return result

def wilson(k,n):
    p=k/n;z=1.95996398454;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,c-h)*100,min(1.,c+h)*100]
def quant(a):
    return None if len(a)==0 else dict(zip(['p10','median','p90'],map(float,np.percentile(a,[10,50,90]))))
def summary(a,challenge):
    n=len(a);passed=a[:,0]>0 if challenge else a[:,3]==0;fail=a[:,3]>0
    return dict(paths=n,pass_rate_pct=float(passed.mean()*100) if challenge else None,
        failure_rate_pct=float(fail.mean()*100),failure_rate_mc95_pct=wilson(int(fail.sum()),n),
        pass_rate_mc95_pct=wilson(int(passed.sum()),n) if challenge else None,
        unresolved_rate_pct=float(((a[:,0]==0)&(a[:,3]==0)).mean()*100) if challenge else None,
        median_calendar_days_to_pass=quant(a[passed,2]) if challenge else None,
        phase1_rate_pct=float(a[:,1].mean()*100) if challenge else None,
        phase2_elapsed_calendar_days=quant(a[passed,23]) if challenge else None,
        failure_causes={name:float((a[:,3]==code).mean()*100) for code,name in [(1,'daily_loss'),(2,'total_loss'),(3,'inactivity'),(4,'quick_strike')]},
        closed_return_pct=quant(a[:,6]) if not challenge else None,
        pooled_win_rate_pct=float(a[:,8].sum()/a[:,7].sum()*100) if a[:,7].sum()>0 else None,
        pooled_profit_factor=float(a[:,9].sum()/a[:,10].sum()) if a[:,10].sum()>0 else None,
        max_win_streak=quant(a[:,13]),max_loss_streak=quant(a[:,14]),max_closed_dd_pct=quant(a[:,11]),
        min_trade_risk_cash=quant(a[:,16]),max_trade_risk_cash=quant(a[:,17]),
        median_trades=float(np.median(a[:,7])),risk_ceiling_flags_path_pct=float((a[:,19]>0).mean()*100),
        hedge_overlap_path_pct=float((a[:,20]>0).mean()*100),positions_left_open_path_pct=float((a[:,21]>0).mean()*100),
        max_open_stop_reference_pct=quant(a[:,15]),skipped_entries=quant(a[:,18]))

def start_paths(days,horizon,method,paths,seed):
    if method=='rolling':
        s=np.arange(0,days-horizon+1,7,dtype=np.int64)
        return s[:,None],horizon
    block=28;n=math.ceil(horizon/block);possible=np.arange(0,days-block+1,7,dtype=np.int64)
    return np.random.default_rng(seed).choice(possible,size=(paths,n)),block

def rolling_paths(source,sp,block,horizon,firm,fi,pi,policy,mode,challenge):
    values=[];dates=[]
    for starts in sp:
        start=(datetime.fromisoformat(START)+timedelta(days=int(starts[0]))).date().isoformat()
        out,_=one_path(source,starts,block,horizon,resets(start,horizon,firm['zone']),fi,pi,policy,mode,
                       0 if challenge else 2,CAPITAL,False,False)
        values.append(out)
        date_of=lambda t:None if t<0 else datetime.fromtimestamp(epoch(start)+t*86400,timezone.utc).isoformat()
        dates.append(dict(start=start,end_exclusive=(datetime.fromisoformat(start)+timedelta(days=horizon)).date().isoformat(),
                          phase1_pass=date_of(out[2]-out[23]) if out[0] else None,both_phases_pass=date_of(out[2]),
                          failure=date_of(out[4]),failure_cause=int(out[3]),closed_return_pct=float(out[6]),
                          trades=int(out[7]),positions_left_open=int(out[21])))
    return np.asarray(values),dates

def run(paths=2000,quick=False):
    plan=json.loads((ROOT/'PLAN.json').read_text());pub,ledgers,meta=load_inputs()
    assert plan['ledger_sha256']==sha(STORE/'data/portfolio-risk-ledgers.json')
    assert plan['publication_sha256']==sha(STORE/'data/portfolios.json')
    started=time.time();results=[];histories=[]
    keys=list(LABELS)
    for pi,key in enumerate(keys):
        row_sources={}
        for stress in (False,True):row_sources[stress]=source_array(ledgers[key],START,END,stress)
        a,keynames,_,coverage=row_sources[False]
        print(key,coverage,flush=True)
        for fi,firm in enumerate(FIRMS):
            for policy in range(3):
                for window,start in [('1y',START),('6m','2026-04-06'),('3m','2026-07-06')]:
                    arr,kn,_,cv=source_array(ledgers[key],start,END)
                    days=int((epoch(END)-epoch(start))/86400)
                    out,log=one_path(arr,np.array([0],np.int64),days,days,resets(start,days,firm['zone']),fi,pi,policy,0,-1,CAPITAL,False,True)
                    trades=[dict(slug=kn[int(k)],position_id=i,close_time=datetime.fromtimestamp(epoch(start)+t*86400,timezone.utc).isoformat(),net_profit=float(p)) for i,(t,p,k,b) in enumerate(log)]
                    stats,curve,months=performance(trades,start,END,CAPITAL)
                    histories.append(dict(portfolio=key,firm=firm['id'],policy=POLICIES[policy],period=window,start=start,end_exclusive=END,stats=stats,
                                          curve=curve[::max(1,len(curve)//250)]+curve[-1:],months=months,coverage=cv,engine=dict(zip(FIELDS,out.tolist()))))
                for method in ('bootstrap','rolling'):
                    for mode in (0,1):
                        for challenge,horizon in [(True,180),(False,90)]:
                            sp,block=start_paths(365,horizon,method,paths,20261013+(0 if challenge else 1))
                            dates=[]
                            if method=='rolling':out,dates=rolling_paths(a,sp,block,horizon,firm,fi,pi,policy,mode,challenge)
                            else:out=many_paths(a,sp,block,horizon,resets(START,horizon,firm['zone']),fi,pi,policy,mode,0 if challenge else 2,CAPITAL,False)
                            results.append(dict(portfolio=key,firm=firm['id'],policy=POLICIES[policy],method=method,float_mode=['closed_only','full_stop_reserve_stress'][mode],
                                task='challenge_180d' if challenge else 'fresh_funded_90d',cost_stress=False,summary=summary(out,challenge),rolling_dates=dates))
                if not quick:
                    arr=row_sources[True][0]
                    for challenge,horizon in [(True,180),(False,90)]:
                        sp,block=start_paths(365,horizon,'bootstrap',paths,20261013+(0 if challenge else 1))
                        out=many_paths(arr,sp,block,horizon,resets(START,horizon,firm['zone']),fi,pi,policy,1,0 if challenge else 2,CAPITAL,True)
                        results.append(dict(portfolio=key,firm=firm['id'],policy=POLICIES[policy],method='bootstrap',float_mode='full_stop_reserve_stress',
                            task='challenge_180d' if challenge else 'fresh_funded_90d',cost_stress=True,summary=summary(out,challenge)))
                print(f"  {firm['id']} {POLICIES[policy]} complete ({time.time()-started:.1f}s)",flush=True)
                (ROOT/'status.json').write_text(json.dumps(dict(portfolio=key,firm=firm['id'],policy=POLICIES[policy],completed=len(results),elapsed_seconds=time.time()-started)))
    payload=dict(plan=plan,results=results,histories=histories,elapsed_seconds=time.time()-started,
                 code_sha256=sha(Path(__file__)),generated_utc=datetime.now(timezone.utc).isoformat(),
                 native_mt5_execution=False,live_changes=False,actual_equity_validation=False)
    (ROOT/'RESULTS.json').write_text(json.dumps(payload,indent=2,allow_nan=False))
    print('DONE',len(results),'scenario summaries',len(histories),'historical replays',round(time.time()-started,1),'seconds',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run']);parser.add_argument('--paths',type=int,default=2000);parser.add_argument('--quick',action='store_true');args=parser.parse_args()
    if args.stage=='freeze':freeze();print('Frozen research plan')
    else:run(args.paths,args.quick)
