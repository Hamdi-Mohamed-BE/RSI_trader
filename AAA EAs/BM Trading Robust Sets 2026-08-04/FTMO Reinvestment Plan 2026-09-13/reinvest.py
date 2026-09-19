"""Counterfactual prop-fee reinvestment on a common historical market path.

Only real received rewards/refunds can buy new challenges; accounts never
become funded automatically. Same signals/dates across accounts, no independent
reshuffling and no compounding by multiplying a $100k summary down to $10k.
"""
import heapq
import itertools
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import engine as e

OUT=Path(__file__).resolve().parent
FEES_EUR={10000:99,25000:279,50000:379,100000:599,200000:1080}
FX=1.1592  # ECB 2026-09-11; fixed conversion assumption, not historical FX.
FX_MARKUP=.02  # explicit, non-refundable FX/card friction sensitivity assumption
CAP=400000
BASE={s:v for s,v in e.EAS.items() if s!='news-pulse-xau'}
e.EAS={**BASE,'dmc-fresh-reaction-us100':('DMC Fresh Reaction US100','standard')}
e.NEWS={'news-pulse-xag'}
ROWS,AUDIT,COMMON_START,COMMON_END=e.load()


def fee(size,markup=FX_MARKUP):
    principal=round(FEES_EUR[size]*FX,2)
    friction=round(principal*markup,2)
    return principal,friction,round(principal+friction,2)


def batch(budget,headroom,markup=FX_MARKUP):
    """Max combined face value <= budget, with >= one $100k challenge.
    Equal allocations prefer fewer accounts, then lower actual price.
    """
    best=None
    for n100 in range(1,min(headroom//100000,int(budget/fee(100000,markup)[2]))+1):
      for n50 in range(0,min(headroom//50000,int(budget/fee(50000,markup)[2]))+1):
       for n25 in range(0,min(headroom//25000,int(budget/fee(25000,markup)[2]))+1):
        for n10 in range(0,min(headroom//10000,int(budget/fee(10000,markup)[2]))+1):
            sizes=[100000]*n100+[50000]*n50+[25000]*n25+[10000]*n10
            notional=sum(sizes); cost=round(sum(fee(s,markup)[2] for s in sizes),2)
            if notional>headroom or cost>budget+.00001:
                continue
            score=(notional,-len(sizes),-cost)
            if best is None or score>best[0]:
                best=(score,sizes)
    return [] if best is None else best[1]


def simulate(*,stress=True,envelope=True,initial_funded=False,markup=FX_MARKUP):
    serial=itertools.count()
    queue=[]
    accounts=[]
    monthly={}
    activity=[]
    external=fee(10000,markup)[2]
    wallet=external
    rewards=refunds=fees=friction=failed_fees=0.0
    stage_two=False
    first_batch_pending=False
    batch_bucket=0.0

    def month(at):
        return at.astimezone(e.PRAGUE).strftime('%Y-%m')

    def bucket(at):
        key=month(at)
        if key not in monthly:
            monthly[key]={'month':key,'rewards':0.0,'refunds':0.0,'fees_paid':0.0,
                          'fx_card_cost':0.0,'failed_unrecovered_fees':0.0,'net_cash':0.0,
                          'purchased':0,'funded_new':0,'failures':0,'cash_end':wallet,
                          'active_funded_capital':0,'reserved_capital':0,
                          'closed_trades':0,'simulated_trading_net':0.0,
                          'gross_losing_trades':0.0,'gross_winning_trades':0.0}
        return monthly[key]

    def allocation():
        return sum(a['size'] for a in accounts if a['status']!='failed')

    def log(at,kind,**values):
        activity.append({'at':at.isoformat(),'kind':kind,**values,'wallet_after':round(wallet,2)})

    def purchase(size,at,why,seed=False):
        nonlocal wallet,fees,friction
        principal,fxcost,cost=fee(size,markup)
        assert wallet+.0001>=cost
        assert allocation()+size<=CAP
        wallet=round(wallet-cost,2);fees+=cost;friction+=fxcost
        aid=len(accounts)+1
        activation=e.START if seed else e.business_pause(at,1)
        result=e.replay(ROWS,activation,e.END,account=size,risk=.35,stress=stress,
                        challenge=not(initial_funded and seed),enforce_envelope=envelope,
                        fixed_news=False,payout_pause_days=4)
        a={'id':aid,'size':size,'fee_principal':principal,'fx_card_cost':fxcost,'fee_total':cost,
           'bought_at':at.isoformat(),'start_at':activation.isoformat(),'status':'evaluation',
           'refund_received':False,'reason':why,'result':result}
        accounts.append(a)
        m=bucket(at);m['fees_paid']+=cost;m['fx_card_cost']+=fxcost;m['purchased']+=1
        log(at,'purchase',account=aid,size=size,fee=cost,reason=why)
        for p in result['phases']:
            heapq.heappush(queue,(e.dt(p['passed_at']),1,next(serial),'phase',aid,p))
        if result['funded_at']:
            heapq.heappush(queue,(e.dt(result['funded_at']),2,next(serial),'funded',aid,None))
        if result['breach']:
            heapq.heappush(queue,(e.dt(result['breach']['at']),0,next(serial),'failed',aid,result['breach']))
        for n,w in enumerate(result['withdrawals']):
            settlement=e.business_pause(e.dt(w['at']),4)
            pay=round(w['payout'],2)
            refund=principal if n==0 else 0.0
            heapq.heappush(queue,(settlement,3,next(serial),'receipt',aid,
                                  {'reward':pay,'refund':refund,'requested_at':w['at']}))
        for t in result['trades']:
            mt=bucket(e.dt(t['closed']))
            mt['closed_trades']+=1
            mt['gross_losing_trades']+=max(0,-t['net'])
            mt['gross_winning_trades']+=max(0,t['net'])
        for mm in result['monthly']:
            # Do not use precomputed future account results for purchase choices.
            # These fields are only retrospective report accounting.
            date=e.dt(mm['month']+'-15T00:00:00')
            bucket(date)['simulated_trading_net']+=mm['net']

    def spend(at):
        nonlocal first_batch_pending,batch_bucket
        if not stage_two:
            eligible=[s for s in FEES_EUR if fee(s,markup)[2]<=wallet+.0001 and s<=CAP-allocation()]
            if eligible:
                purchase(max(eligible),at,'early: largest affordable single challenge')
            return
        while first_batch_pending or batch_bucket>=2500:
            sizes=batch(min(1100,wallet),CAP-allocation(),markup)
            if not sizes:
                break
            for size in sizes:
                purchase(size,at,'growth: up to $1100 batch, at least one $100k')
            if first_batch_pending:
                first_batch_pending=False
            else:
                batch_bucket-=2500

    # Snapshot events do not change cash, account state or sizing.
    d=e.START.astimezone(e.PRAGUE).date().replace(day=1)
    while True:
        following=(d.replace(day=28)+timedelta(days=4)).replace(day=1)
        at=datetime.combine(following,datetime.min.time(),e.PRAGUE).astimezone(e.UTC)-timedelta(microseconds=1)
        if at>=e.END:
            break
        heapq.heappush(queue,(at,9,next(serial),'snapshot',0,None))
        d=following
    purchase(10000,e.START,'initial $10k account',seed=True)
    while queue:
        at,_,_,kind,aid,payload=heapq.heappop(queue)
        if at>=e.END:
            break
        m=bucket(at)
        a=accounts[aid-1] if aid else None
        if kind=='phase':
            log(at,'phase_pass',account=aid,phase=payload['phase'],balance=round(payload['balance'],2))
        elif kind=='funded':
            a['status']='funded';m['funded_new']+=1
            log(at,'funded',account=aid,size=a['size'])
        elif kind=='failed':
            a['status']='failed';m['failures']+=1
            unrecovered=a['fee_principal'] if not a['refund_received'] else 0
            m['failed_unrecovered_fees']+=unrecovered;failed_fees+=unrecovered
            log(at,'failed',account=aid,size=a['size'],reason=payload['reason'],unrecovered_fee=unrecovered)
        elif kind=='receipt':
            # Trading paused for the four business days; cash cannot be used early.
            before=rewards
            wallet=round(wallet+payload['reward']+payload['refund'],2)
            rewards+=payload['reward'];refunds+=payload['refund']
            m['rewards']+=payload['reward'];m['refunds']+=payload['refund']
            if payload['refund']:
                a['refund_received']=True
            log(at,'receipt',account=aid,**payload)
            if not stage_two and rewards>=2000:
                stage_two=True;first_batch_pending=True;batch_bucket=max(0,rewards-2000)
            elif stage_two:
                batch_bucket+=payload['reward']
            spend(at)
        elif kind=='snapshot':
            m['cash_end']=wallet
            m['active_funded_capital']=sum(a['size'] for a in accounts if a['status']=='funded')
            m['reserved_capital']=allocation()
            assert allocation()<=CAP
        assert wallet>=-.000001

    months=[]
    for key in sorted(monthly):
        m=monthly[key]
        if key<month(e.START) or key>month(e.END-timedelta(seconds=1)):
            continue
        m['net_cash']=round(m['rewards']+m['refunds']-m['fees_paid'],2)
        months.append(m)
    assert len(months)==36
    assert abs(external+sum(m['net_cash'] for m in months)-wallet)<.01
    assert abs(sum(m['rewards'] for m in months)-rewards)<.01
    assert abs(sum(m['fees_paid'] for m in months)-fees)<.01
    assert all(a['start_at']>=a['bought_at'] for a in accounts)
    by_year={}
    for m in months:
        y=m['month'][:4]
        if y not in by_year:
            by_year[y]={k:0 for k in ['rewards','refunds','fees_paid','fx_card_cost','failed_unrecovered_fees','net_cash','purchased','funded_new','failures','closed_trades','simulated_trading_net','gross_losing_trades']}
        for k in by_year[y]:
            by_year[y][k]+=m[k]
        by_year[y]['cash_end']=m['cash_end']
        by_year[y]['active_funded_capital']=m['active_funded_capital']
    pending_rewards=sum(w['payout'] for a in accounts for w in a['result']['withdrawals']
                        if e.business_pause(e.dt(w['at']),4)>=e.END)
    return {'stress':stress,'envelope_enforced':envelope,'initial_funded':initial_funded,
            'initial_external_cash':external,'cash_final':wallet,'rewards_received':rewards,
            'fee_refunds_received':refunds,'fees_paid':fees,'fx_card_cost':friction,
            'failed_unrecovered_fees':failed_fees,'unrecovered_costs':fees-refunds,
            'net_real_cash_profit':rewards+refunds-fees,'pending_rewards':pending_rewards,
            'accounts_purchased':len(accounts),'accounts_failed':sum(a['status']=='failed' for a in accounts),
            'accounts_funded_now':sum(a['status']=='funded' for a in accounts),
            'funded_capital_now':sum(a['size'] for a in accounts if a['status']=='funded'),
            'allocation_reserved_now':allocation(),'activity':activity,'monthly':months,'yearly':by_year,
            'accounts':accounts}


def compact(r):
    return {k:v for k,v in r.items() if k not in ['accounts','activity','monthly','yearly']}


def main():
    results={}
    for key,stress,envelope in [('stressed-stop-check',True,True),('stressed-closed-only',True,False),('recorded-fill-reference',False,False)]:
        r=simulate(stress=stress,envelope=envelope)
        results[key]=r
        print(key,json.dumps(compact(r)),flush=True)
        print('ACTIVITY saved:',len(r['activity']),'events',flush=True)
    check10=e.replay(ROWS,e.START,e.END,account=10000,risk=.35,stress=True,challenge=False,fixed_news=False)
    ea_stats=[]
    for s,(name,_) in e.EAS.items():
        trades=[t for t in check10['trades'] if t['slug']==s]
        pos=sum(max(0,t['net']) for t in trades);neg=sum(max(0,-t['net']) for t in trades)
        ea_stats.append({'slug':s,'name':name,'closed':len(trades),'net':sum(t['net'] for t in trades),
                         'win_rate':100*sum(t['net']>0 for t in trades)/max(1,len(trades)),
                         'pf':pos/neg if neg else None})
    payload={'from':e.START.isoformat(),'to_exclusive':e.END.isoformat(),'fx_rate':FX,'fx_markup':FX_MARKUP,
             'fees':{s:{'eur':eur,'usd_base':fee(s)[0],'usd_fx_cost':fee(s)[1],'usd_paid':fee(s)[2]} for s,eur in FEES_EUR.items()},
             'allocation_limit':CAP,'batch_at_full_budget':batch(1100,CAP),
             'source_audit':AUDIT,'ten_k_same_account_ea_contributions':ea_stats,'runs':results}
    (OUT/'results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print('FEE SCHEDULE',payload['fees'])
    print('BATCH',payload['batch_at_full_budget'])
    print('10K EA SCREEN',json.dumps(ea_stats))


if __name__=='__main__':main()
