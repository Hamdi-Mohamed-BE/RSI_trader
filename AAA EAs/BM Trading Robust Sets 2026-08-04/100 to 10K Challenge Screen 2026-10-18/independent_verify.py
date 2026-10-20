"""Independent frozen-ledger challenge verifier; never imports simulate.py.

Run only after the researcher announces outcomes: --verify-results. Core cash,
ownership, risk, chronological ordering and summary calculations are separately
implemented here. The receipt binds inputs, selected configurations and outcomes.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations
import argparse
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
D = 86400
CHECKS = 0


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(message)


def equivalent(expected, actual, path='root'):
    """Compare complete schemas; float tolerances are cash-subcent or tighter."""
    global CHECKS
    CHECKS += 1
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise AssertionError((path,'dict schema',set(expected),set(actual) if isinstance(actual,dict) else actual))
        for k in expected:
            equivalent(expected[k], actual[k], path+'.'+str(k))
    elif isinstance(expected, list):
        if not isinstance(actual,list) or len(expected)!=len(actual):
            raise AssertionError((path,'list length',len(expected),len(actual) if isinstance(actual,list) else actual))
        for i,(a,b) in enumerate(zip(expected,actual)):
            equivalent(a,b,f'{path}[{i}]')
    elif isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if not isinstance(actual,(int,float)) or not math.isclose(expected,actual,rel_tol=1e-11,abs_tol=1e-7):
            raise AssertionError((path,expected,actual))
    elif expected != actual:
        raise AssertionError((path,expected,actual))


def date_epoch(text):
    return datetime.strptime(text,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()


def starts(window):
    a,b=map(date_epoch,window)
    a += ((7-datetime.fromtimestamp(a,timezone.utc).weekday())%7)*D
    return list(range(int(a),int(b-365*D)+1,7*D))


def events_for(rows, members):
    output=[]
    for p in rows:
        if p['key'] in members:
            output.append((p['op'],1,p['id'],0,p,None))
            for cashflow in p['flows']:
                if cashflow['kind']!='entry':
                    output.append((cashflow['epoch'],0,p['id'],int(cashflow['deal_id']),p,cashflow))
    output.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    return output


def independent_attempt(events, contracts, percentage, start, end, detail=False, stressed=False):
    balance=100.
    peak=100.
    drawdown=0.
    positions={}
    tally=Counter()
    completed=[]
    curve=[]
    decisions=[]
    fail=None
    success=None
    anchor=100.
    day=int(start//D)
    halted=False
    last=start
    f=percentage/100.

    def account_observation(t):
        nonlocal peak,drawdown,fail,success,anchor,day,halted
        stamp=int(t//D)
        if stamp!=day:
            day=stamp
            anchor=balance
            halted=False
        peak=max(peak,balance)
        drawdown=max(drawdown,100*(peak-balance)/peak)
        if fail is None and balance<=20.+1e-9:
            fail=t
        if balance<=anchor*(1.-min(2*f,.30))+1e-9:
            halted=True
        if fail is None and not positions and balance>=10000.:
            success=t
        if detail:
            curve.append(dict(epoch=t,balance=balance,open_positions=len(positions)))

    account_observation(start)
    for stamp,phase,pid,deal,p,flow in events:
        if stamp<start:
            continue
        if stamp>=end or success is not None or (fail is not None and not positions):
            break
        if p['op']<start:
            continue
        last=stamp
        current_day=int(stamp//D)
        if current_day!=day:
            day=current_day
            anchor=balance
            halted=False
        if phase==1:
            tally['candidates']+=1
            c=contracts[p['symbol']]
            budget=max(0.,balance*f)
            maximum=min(c['volume_max'],budget/p['unit_risk'])
            lots=round(max(0.,math.floor(maximum/c['volume_step']+1e-9)*c['volume_step']),8)
            risk=lots*p['unit_risk']
            holding_risk=sum(x['initial_risk'] for x in positions.values())
            symbol_risk=sum(x['initial_risk'] for x in positions.values() if x['symbol']==p['symbol'])
            entry=round((p['entry_unit_cash']-(c['spread_cash_per_lot'] if stressed else 0.))*lots,2)
            required_margin=lots*p['margin_unit_proxy']*(2 if stressed else 1)
            protected=balance-holding_risk-risk+min(entry,0.)
            reason=None
            if fail is not None:
                reason='floor_latched'
            elif balance>=10000.:
                reason='target_waiting_flat'
            elif halted:
                reason='daily_pause'
            elif lots<c['volume_min']-1e-9:
                reason='minimum_lot'
            elif pid in positions:
                reason='duplicate_position'
            elif holding_risk+risk>balance*min(2*f,.60)+1e-7:
                reason='aggregate_risk'
            elif symbol_risk+risk>budget+1e-7:
                reason='same_symbol_risk'
            elif protected<=0. or sum(x['initial_margin'] for x in positions.values())+required_margin>.8*protected+1e-7:
                reason='margin_proxy'
            tally[reason or 'opened']+=1
            if reason is None:
                check(risk<=budget+1e-6,'Risk exceeded budget '+pid)
                positions[pid]=dict(symbol=p['symbol'],lots=lots,initial_risk=risk,
                    initial_margin=required_margin,left=1.,total_net=entry,op=stamp,key=p['key'])
                balance=round(balance+entry,2)
            if detail:
                decisions.append(dict(epoch=stamp,id=pid,key=p['key'],decision=reason or 'opened',
                    budget=budget,volume=lots,planned_stop_risk=risk,margin_proxy=required_margin))
        elif pid in positions:
            owned=positions[pid]
            penalty=0.
            if stressed:
                penalty=contracts[p['symbol']]['spread_cash_per_lot']*flow['closed_volume_fraction']
                penalty+=max(-flow.get('swap_unit',0.),0.)
            paid=round((flow['cash_unit']-penalty)*owned['lots'],2)
            balance=round(balance+paid,2)
            owned['total_net']=round(owned['total_net']+paid,2)
            owned['left']-=flow['closed_volume_fraction']
            if owned['left']<=1e-7:
                completed.append(dict(id=pid,key=owned['key'],op=owned['op'],cl=stamp,
                    lots=owned['lots'],net=owned['total_net'],risk=owned['initial_risk']))
                positions.pop(pid)
        account_observation(stamp)
    status='hit' if success is not None else 'floor' if fail is not None else 'timeout'
    tally['closed_positions']=len(completed)
    result=dict(start=start,end_exclusive=end,status=status,ending_closed_cash=balance,
        open_positions=len(positions),max_closed_dd_pct=drawdown,counts=dict(tally),
        hit_epoch=success,hit_days=(success-start)/D if success is not None else None,
        floor_epoch=fail,last_event=last,no_admitted_positions=tally['opened']==0)
    if detail:
        wins=[x['net'] for x in completed if x['net']>0]
        losses=[x['net'] for x in completed if x['net']<0]
        longest_win=longest_loss=current_win=current_loss=0
        for p in completed:
            current_win=current_win+1 if p['net']>0 else 0
            current_loss=current_loss+1 if p['net']<0 else 0
            longest_win=max(longest_win,current_win)
            longest_loss=max(longest_loss,current_loss)
        result.update(closed_positions=completed,decisions=decisions,curve=curve,
            trade_stats=dict(trades=len(completed),win_rate_pct=100*len(wins)/len(completed) if completed else None,
                profit_factor=sum(wins)/abs(sum(losses)) if losses else None,
                max_win_streak=longest_win,max_loss_streak=longest_loss))
    return result


def percentile(values, fraction):
    ordered=sorted(values)
    if not ordered:
        return None
    position=(len(ordered)-1)*fraction
    lower=math.floor(position)
    upper=math.ceil(position)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)


def summary_of(attempts):
    n=len(attempts)
    hits=[a for a in attempts if a['status']=='hit']
    times=sorted(a['hit_days'] for a in hits)
    fastest=min(hits,key=lambda x:x['hit_days']) if hits else None
    return dict(starts=n,hits=len(hits),hit_pct=100*len(hits)/n,
        floor_pct=100*sum(a['status']=='floor' for a in attempts)/n,
        timeout_pct=100*sum(a['status']=='timeout' for a in attempts)/n,
        no_trade_pct=100*sum(a['no_admitted_positions'] for a in attempts)/n,
        median_hit_days=statistics.median(times) if times else None,
        all_start_median_days=(times[(n-1)//2]+times[n//2])/2 if len(times)>n//2 else None,
        mean_capped_days=sum(a['hit_days'] if a['status']=='hit' else 365. for a in attempts)/n,
        ending_cash_p10=percentile([a['ending_closed_cash'] for a in attempts],.1),
        ending_cash_median=percentile([a['ending_closed_cash'] for a in attempts],.5),
        ending_cash_p90=percentile([a['ending_closed_cash'] for a in attempts],.9),
        median_closed_dd_pct=statistics.median(a['max_closed_dd_pct'] for a in attempts),
        worst_closed_dd_pct=max(a['max_closed_dd_pct'] for a in attempts),
        fastest=dict(start=fastest['start'],hit_epoch=fastest['hit_epoch'],days=fastest['hit_days']) if fastest else None,
        total_counts=dict(sum((Counter(a['counts']) for a in attempts),Counter())))


def selection_order(c):
    m=c['summary']
    if m['hit_pct']>=50:
        return (0,m['median_hit_days'],-m['hit_pct'],m['median_closed_dd_pct'],c['id'])
    return (1,-m['hit_pct'],m['mean_capped_days'],-m['ending_cash_median'],c['id'])


def configuration(keys,risk):
    ordered=sorted(keys)
    return dict(id='+'.join(ordered)+'@'+str(risk),keys=ordered,risk_pct=risk)


def verify():
    global CHECKS
    plan=read('PLAN.json')
    frozen=read('FROZEN.json')
    data=read('INPUTS.json')
    development=read('DEVELOPMENT.json')
    selected=read('SELECTION.json')
    results=read('RESULTS.json')
    for path,wanted in {**frozen['files'],**data['source_hashes']}.items():
        check(sha(path)==wanted,'Changed frozen/source evidence '+path)
    equivalent(sha(ROOT/'DEVELOPMENT.json'),selected['development_sha256'],'selection.development_sha256')
    equivalent(sha(ROOT/'FROZEN.json'),selected['frozen_sha256'],'selection.frozen_sha256')
    for field,file in [('plan_sha256','PLAN.json'),('inputs_sha256','INPUTS.json'),
                       ('frozen_sha256','FROZEN.json'),('selection_sha256','SELECTION.json')]:
        equivalent(sha(ROOT/file),results[field],'results.'+field)
    devstarts=starts(plan['development'])
    evalstarts=starts(plan['evaluation'])
    equivalent(devstarts,development['starts'],'development.starts')
    members=sorted({p['key'] for p in data['rows']})
    groups={p['key']:p.get('variant_group',p['key']) for p in data['rows']}
    expected_singles=[configuration([k],r) for k in members for r in plan['risk_percentages']]
    equivalent(expected_singles,[{k:c[k] for k in ('id','keys','risk_pct')} for c in development['singles']],
               'all_single_configuration_coverage')
    cache={}
    def get_events(keys):
        identity=tuple(keys)
        if identity not in cache:
            cache[identity]=events_for(data['rows'],set(keys))
        return cache[identity]
    def validate_development(c):
        # Independently audit every development path, not just winners.
        aa=[independent_attempt(get_events(c['keys']),data['symbols'],c['risk_pct'],t,t+365*D) for t in devstarts]
        equivalent(aa,c['attempts'],'development.'+c['id']+'.attempts')
        equivalent(summary_of(aa),c['summary'],'development.'+c['id']+'.summary')
    for c in development['singles']:
        validate_development(c)
    family_best={}
    for c in sorted(development['singles'],key=selection_order):
        family_best.setdefault(groups[c['keys'][0]],c)
    short=[c['keys'][0] for c in sorted(family_best.values(),key=selection_order)[:8]]
    equivalent(short,development['shortlist'],'development.shortlist')
    basket_set={tuple(sorted(k)) for size in (2,3) for k in combinations(short,size)}
    for value in data['metadata']['named_baskets'].values():
        if isinstance(value,dict):
            value=value.get('keys',value.get('members',[]))
        keys=sorted(set(value)&set(members))
        if len(keys)>1 and len({groups[k] for k in keys})==len(keys):
            basket_set.add(tuple(keys))
    expected_combos=[configuration(k,r) for k in sorted(basket_set) for r in plan['risk_percentages']]
    equivalent(expected_combos,[{k:c[k] for k in ('id','keys','risk_pct')} for c in development['combos']],
               'all_combo_configuration_coverage')
    equivalent(len(expected_singles)+len(expected_combos),development['configuration_count'],'configuration_count')
    for c in development['combos']:
        check(len({groups[k] for k in c['keys']})==len(c['keys']),'Exclusive variants in combo '+c['id'])
        validate_development(c)
    expected_locked=[]
    for kind,cc in [('single',development['singles']),('combo',development['combos'])]:
        primary=min(cc,key=selection_order)
        highest=min(cc,key=lambda c:(-c['summary']['hit_pct'],c['summary']['mean_capped_days'],
                                    -c['summary']['ending_cash_median'],c['id']))
        with_hits=[c for c in cc if c['summary']['fastest'] is not None]
        fastest=min(with_hits,key=lambda c:(c['summary']['fastest']['days'],-c['summary']['hit_pct'],c['id'])) if with_hits else primary
        for role,c in [('primary',primary),('highest_hit_rate',highest),('fastest_observed',fastest)]:
            expected_locked.append(dict(kind=kind,role=role,qualified=c['summary']['hit_pct']>=50,
                id=c['id'],keys=c['keys'],risk_pct=c['risk_pct'],development=c['summary']))
    equivalent(expected_locked,selected['locked'],'selection.locked')
    expected_eval={(c['id'],cost) for c in selected['locked'] for cost in ('recorded','stress')}
    equivalent(sorted(expected_eval),sorted((c['id'],c['cost']) for c in results['results']),'evaluation.coverage')
    check(len(results['results'])==len(expected_eval),'Duplicate evaluation records')
    attempts_verified=0
    detail_paths=0
    for c in results['results']:
        locked=next(x for x in selected['locked'] if x['id']==c['id'])
        equivalent(locked['keys'],c['keys'],'evaluation.keys')
        equivalent(locked['risk_pct'],c['risk_pct'],'evaluation.risk')
        events=get_events(c['keys'])
        aa=[independent_attempt(events,data['symbols'],c['risk_pct'],t,t+365*D,stressed=c['cost']=='stress') for t in evalstarts]
        equivalent(aa,c['attempts'],'evaluation.'+c['id']+'.'+c['cost']+'.attempts')
        ss=summary_of(aa)
        equivalent(ss,c['summary'],'evaluation.'+c['id']+'.'+c['cost']+'.summary')
        representative=sorted(aa,key=lambda a:a['ending_closed_cash'])[len(aa)//2]
        chosen={representative['start']}
        if ss['fastest']:
            chosen.add(ss['fastest']['start'])
        dd=[independent_attempt(events,data['symbols'],c['risk_pct'],t,t+365*D,True,c['cost']=='stress') for t in sorted(chosen)]
        equivalent(dd,c['details'],'evaluation.'+c['id']+'.'+c['cost']+'.details')
        attempts_verified+=len(aa)
        detail_paths+=len(dd)
    receipt=dict(status='PASS',checks=CHECKS,independent_core_imports_simulate=False,
        development_configurations_verified=development['configuration_count'],
        development_attempts_verified=development['configuration_count']*len(devstarts),
        evaluation_comparisons_verified=len(results['results']),evaluation_attempts_verified=attempts_verified,
        detailed_paths_verified=detail_paths,development_starts=len(devstarts),evaluation_starts=len(evalstarts),
        results_sha256=sha(ROOT/'RESULTS.json'),selection_sha256=sha(ROOT/'SELECTION.json'),
        frozen_sha256=sha(ROOT/'FROZEN.json'),inputs_sha256=sha(ROOT/'INPUTS.json'),
        plan_sha256=sha(ROOT/'PLAN.json'),development_sha256=sha(ROOT/'DEVELOPMENT.json'),
        verifier_sha256=sha(Path(__file__)),test_suite_sha256=sha(ROOT/'test_simulate.py'),
        scope='Separately implemented chronological cash/risk replay for every development and locked evaluation attempt; exhaustive candidate, selection, summary and detailed-path audit. Not a native/live-execution proof.')
    (ROOT/'VERIFICATION.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-results',action='store_true',required=True,
                        help='Run only after root announces that locked evaluation outcomes exist.')
    parser.parse_args()
    verify()
