"""Three portfolio comparisons using frozen native trade streams. Offline only."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import argparse,ast,hashlib,importlib.util,json,math,statistics

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PURE=BASE/'FTMO Pure ORB Swing Portfolio 2026-10-08'
PREVIOUS=BASE/'FTMO ORB RR05 Portfolio Simulation 2026-10-08'
spec=importlib.util.spec_from_file_location('pure_three_source',PURE/'run.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
s=p.s;DAY=p.DAY;WEEK=p.WEEK;START=p.START;END=p.END;SYN=p.SYN
EXTRAS=['xau-rsi-vwap','gold-overnight-value-area','xau-trend-progression','3-way-gold','nasdaq-5m-candle-momentum']
POLICIES=[dict(name='original_50',label='Original $50 / $300 reserved daily budget',risk=50.,daily=300.,symbol=150.),
          dict(name='risk200_daily400',label='$200 / $400 reserved daily stop',risk=200.,daily=400.,symbol=200.),
          dict(name='risk200_daily450',label='$200 / $450 reserved daily stop',risk=200.,daily=450.,symbol=200.)]
PROTOCOLS=[('Joint 4-week blocks',4,False,False,False,20261008),('Joint 8-week blocks',8,False,False,False,20261009),
           ('Execution/carry stress',4,True,False,False,20261008),('Recent 13-week pool',2,False,True,False,20261010),
           ('3-second cooldown, no retries',4,False,False,True,20261008)]

def read(q):return json.loads(Path(q).read_text(encoding='utf-8-sig'))
def save(q,v):Path(q).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(q):return hashlib.sha256(Path(q).read_bytes()).hexdigest()

def engine(policy,cooldown=False):
    # Capture the verified engine's final replay source, never importing a
    # trading API or modifying an installed build.
    fn=next(x for x in ast.parse((s.ROOT/'simulate.py').read_text(encoding='utf-8-sig')).body if isinstance(x,ast.FunctionDef) and x.name=='engine')
    captures=0
    for i,x in enumerate(fn.body):
        if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='exec':
            fn.body[i]=ast.parse("ns['_source']=text").body[0];captures+=1
    assert captures==1
    env=dict(s.__dict__);exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'capture_three_portfolio_source','exec'),env)
    ns=env['engine'](policy['risk'],cooldown=cooldown);source=ns.pop('_source')
    if policy['name']!='original_50':
        changes={">150:return 'correlated_risk'":f">{policy['symbol']!r}+1e-7:return 'correlated_risk'",
                 ">300:return 'daily_budget'":f">{policy['daily']!r}+1e-7:return 'daily_budget'",
                 'today_count=0;max_daily_entries=0;':'day_locked=False;today_count=0;max_daily_entries=0;',
                 "if t<ready:return 'phase_wait'":"if t<ready:return 'phase_wait'\n        if day_locked:return 'daily_latched_stop'",
                 'if kind==-1:anchor=bal;today_count=today_losses=0':'if kind==-1:anchor=bal;today_count=today_losses=0;day_locked=False',
                 "maxmargin=max(maxmargin,sum(p['margin'] for p in held()));maxrisk=max(maxrisk,sum(p['risk'] for p in held()))":
                 f"maxmargin=max(maxmargin,sum(p['margin'] for p in held()));maxrisk=max(maxrisk,sum(p['risk'] for p in held()))\n        if anchor-eq>={policy['daily']!r}-1e-7:day_locked=True"}
        for before,after in changes.items():assert source.count(before)==1,before;source=source.replace(before,after)
    # Record entry-known budgets and exposure, enabling independent checks.
    before="fee=entry_charge(r,c,x)*p['lot'];bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)"
    after="fee=entry_charge(r,c,x)*p['lot'];p.update(balance_before_entry=bal,planned_budget=budget,day_anchor=anchor,prior_reserve=envelope(),prior_open_risk=sum(q['risk'] for q in held()));bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)"
    assert source.count(before)==1;source=source.replace(before,after)
    before="initial_risk=p['risk'],actual_fill_stop_risk="
    after="initial_risk=p['risk'],balance_before_entry=p['balance_before_entry'],planned_budget=p['planned_budget'],day_anchor=p['day_anchor'],prior_reserve=p['prior_reserve'],prior_open_risk=p['prior_open_risk'],entry_fee=p['entryfee'],admission_reserve=p['env'],actual_fill_stop_risk="
    assert source.count(before)==1;source=source.replace(before,after)
    replay=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='replay')
    exec(compile(ast.Module(body=[replay],type_ignores=[]),'three_portfolio_risk200','exec'),ns)
    return ns

def prepare():
    old=read(PURE/'FROZEN_ROWS.json');native=read(PREVIOUS/'FROZEN_ROWS.json')['baseline']
    manifest=read(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    keys=[x['slug'] for x in manifest['entries']];assert len(keys)==14
    assert set(keys)=={x['key'] for x in native}
    orbs=old['orb_qualified_4'];orb_keys={x['key'] for x in orbs};assert len(orb_keys)==4
    extra_rows=[dict(x) for x in native if x['key'] in EXTRAS];assert {x['key'] for x in extra_rows}==set(EXTRAS)
    portfolios=[dict(name='orbs4',label='Qualifying ORBs only',ea_count=4,keys=sorted(orb_keys),rows=orbs),
                dict(name='current14',label='Current FTMO launcher (14 EAs; legacy 13 name)',ea_count=14,keys=keys,rows=native),
                dict(name='hybrid9',label='Four ORBs + five requested EAs',ea_count=9,keys=sorted(orb_keys)+EXTRAS,rows=orbs+extra_rows)]
    for x in portfolios:
        assert len(set(x['keys']))==x['ea_count'] and {r['key'] for r in x['rows']}==set(x['keys'])
        assert all(not r['news'] and r.get('order_compatible',True) for r in x['rows'])
    paths=[PURE/'FROZEN_ROWS.json',PURE/'Results.json',PURE/'run.py',PREVIOUS/'FROZEN_ROWS.json',PREVIOUS/'NATIVE_SOURCES.json',
           BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json',s.ROOT/'simulate.py',s.legacy.ROOT/'study.py',s.legacy.OLD/'simulate.py',s.legacy.OLD/'prepare.py']
    hashes={str(q):sha(q) for q in paths};hashes.update(read(PURE/'Results.json')['sources'])
    nsources=read(PREVIOUS/'NATIVE_SOURCES.json')
    for z in nsources['entries'].values():assert sha(z['path'])==z['sha256'];hashes[z['path']]=z['sha256']
    save(ROOT/'FROZEN_ROWS.json',{x['name']:x['rows'] for x in portfolios})
    return portfolios,hashes,manifest

def tests():
    parent=s.tests();t=START
    row=dict(key='a',symbol='USTEC',news=False,op=t+3600,cl=t+3660,unit_risk=1000.,unit_gross=-1000.,
             unit_comm=-.7,unit_swap=0.,open_price=25000.,close_price=24000.,side='Long')
    for pol in POLICIES[1:]:
        ns=engine(pol);r=ns['replay']([dict(row)],[],t,t+DAY,challenge=False,detail=True)
        assert r['trades']==1 and r['log'][0]['lots']==.2 and r['max_open_risk']<=225+1e-7
        r=ns['replay']([dict(row),dict(row,key='b',op=t+3700,cl=t+3760)],[],t,t+DAY,challenge=False)
        # $200 loss plus 1.25x reserved future stop and costs exceeds either budget.
        assert r['trades']==1 and r['counts']['daily_budget_rejected']==1
        # A new Prague day releases the daily stop/admission budget.
        r=ns['replay']([dict(row),dict(row,key='b',op=t+DAY+3700,cl=t+DAY+3760)],[],t,t+2*DAY,challenge=False)
        assert r['trades']==2
        # No extra simultaneous full-risk trade is added by raising the symbol cap.
        r=ns['replay']([dict(row),dict(row,key='b',op=t+3601,cl=t+3661)],[],t,t+DAY,challenge=False)
        assert r['trades']==1 and r['counts']['open_risk_rejected']==1
        # Large gap beyond the reserve triggers a day latch, no fabricated liquidation.
        rr=[dict(row,unit_gross=-2400.),dict(row,key='b',op=t+3700,cl=t+3760)]
        r=ns['replay'](rr,[],t,t+DAY,challenge=False)
        assert r['trades']==1 and r['counts']['daily_latched_stop']==1
    return dict(parent=parent,new_policy_checks=10)

def stats(runs):
    out=[]
    for horizon in (90,180,365,730):
        z=s.horizon_summary(runs,SYN,horizon);cut=SYN+horizon*DAY
        rr=[r for r in runs if r['passes'] and p.before(r['passes'][0]['time'],cut)]
        z['days_to_phase1']=s.dist([(p.stamp(r['passes'][0]['time'])-SYN)/DAY for r in rr])
        out.append(z)
    return out

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--paths',type=int,default=1000);parser.add_argument('--history-only',action='store_true');a=parser.parse_args()
    checks=tests();portfolios,hashes,manifest=prepare();old=read(PURE/'Results.json')
    result=dict(window_from=old['window_from'],window_through=old['window_through'],synthetic_start=old['synthetic_start'],paths_per_case=a.paths,
        capital_usd=10000,profiles=[{k:v for k,v in x.items() if k!='rows'} for x in portfolios],policies=POLICIES,
        current_manifest_version=manifest['version'],legacy_13_profile_actual_ea_count=14,
        stop_policy='Stop NEW entries; do not force-liquidate existing trades. Use Prague-midnight balance and initial-stop reserve proxy, 1.25 x risk + $5 per open position (stress adds 1.25 factor), entry charges counted. Latch new entries off until next Prague day if observed proxy loss hits $400/$450. Reject new orders earlier if projected reserve loss would exceed budget.',
        unchanged_rules='Static $500 official daily/$1000 total loss proxy; $225 total open initial risk; 7 entries/3 closed losses per day; $9200 admission floor; broker step rounding down; unchanged signals/exits and no daily profit cap. $200 policies raise symbol cap from $150 to $200 solely to permit requested full-size trade. No actual guard build changed.',
        hard_stop_warning='No hard floating-equity or forced-close daily stop was measured. Open P/L not available in the matched ledgers. Reserve buffers may reject a second trade even when only one loss has closed. Gaps can exceed both the internal budget and official limits.',
        limitations=old['limitations']+[
          'This new policy is an admission-stop test, not a force-liquidation test; no equity mark path is fabricated.',
          'Using $200 initial risk on a $10000 account is 2% initial risk before fees, slippage and gaps.',
          'The $225 unchanged aggregate exposure cap generally admits only one full $200 trade at a time. Concurrency changes drive part of the comparison.',
          'The requested third profile includes four ORBs plus exactly five requested current-FTMO variants, with no duplicate strategy. ORB targets stay 0.5R except Selective at 2R.',
          '730-day scenarios repeat the same one-year source pool; no independent new-year validation.',
          'Only five native trades support the Selective US100 result; the Gold NY source has twelve.'],
        source_hashes=hashes,checks=checks,historical=[],random_cases=[],starts=[])
    existing={x['name']:x for x in old['historical']}
    for profile in portfolios:
        for pol in POLICIES:
            ns=engine(pol);rr=[dict(r) for r in profile['rows'] if START<=r['op']<r['cl']<END]
            hist=ns['replay'](rr,[],START,END,challenge=False,detail=True)
            continuous=s.continuous(hist,START,END)
            if pol['name']=='original_50' and profile['name']!='hybrid9':
                expected=existing['orb_qualified_4' if profile['name']=='orbs4' else 'current_ftmo_14']['portfolio']
                assert continuous==expected
            challenge=ns['replay']([dict(r) for r in rr],[],START,END,detail=True)
            result['historical'].append(dict(profile=profile['name'],policy=pol['name'],portfolio=continuous,challenge=challenge,log=hist['log'],
                trades_per_weekday=hist['trades']/261,worst_daily_reserve_usd=hist['worst_daily_usd'],max_open_risk=hist['max_open_risk']))
            print('HISTORY '+profile['name']+' '+pol['name']+' '+json.dumps({k:v for k,v in continuous.items() if k not in ('balance_curve','months','contributions')}),flush=True)
            for horizon in (90,180):
                begin=START
                while begin+horizon*DAY<=END:
                    cut=begin+horizon*DAY;r=ns['replay']([dict(q) for q in rr if begin<=q['op']<cut],[],begin,cut)
                    result['starts'].append(dict(profile=profile['name'],policy=pol['name'],horizon_days=horizon,start=s.date(begin),end_exclusive=s.date(cut),
                         passes=r['passes'],breach_at=r['breach_at'],funded_at=r['funded_at'],receipt_at=r['receipt_at'],trades=r['trades']))
                    begin+=WEEK
    if a.history_only:save(ROOT/'HistoryProbe.json',result);return
    save(ROOT/'Results.json',result)
    for label,weeks,stress,recent,cooldown,seed in PROTOCOLS:
        draws,shifted=p.joint_samples(portfolios,weeks,a.paths,seed,730,recent)
        assert draws==read(PURE/('DRAWS-'+str(seed)+'-'+str(weeks)+'.json'))['draws'][:a.paths]
        save(ROOT/('DRAWS-'+str(seed)+'-'+str(weeks)+'.json'),dict(seed=seed,block_weeks=weeks,draws=draws,recent_only=recent,horizon_days=730))
        reference={}
        for profile in portfolios:
            for pol in POLICIES:
                ns=engine(pol,cooldown);suffix='-stress' if stress else '-cooldown' if cooldown else ''
                if pol['name']=='original_50' and profile['name']!='hybrid9':
                    key='orb_qualified_4' if profile['name']=='orbs4' else 'current_ftmo_14'
                    runs=read(PURE/('PATHS-'+str(seed)+'-'+str(weeks)+'-'+key+suffix+'.json'))[:a.paths]
                else:
                    runs=[]
                    for i,draw in enumerate(draws):
                        runs.append(ns['replay'](shifted(profile['name'],draw),[],SYN,SYN+730*DAY,stress=stress))
                        if (i+1)%500==0:print(label+' '+profile['name']+' '+pol['name']+' '+str(i+1)+'/'+str(a.paths),flush=True)
                if pol['name']=='original_50':reference[profile['name']]=runs
                case=dict(protocol=label,profile=profile['name'],policy=pol['name'],block_weeks=weeks,seed=seed,stress=stress,cooldown=cooldown,recent_only=recent,summary=stats(runs))
                base=reference[profile['name']];paired=[]
                for horizon in (365,730):
                    cut=SYN+horizon*DAY
                    passed=lambda r:len(r['passes'])==2 and p.before(r['passes'][1]['time'],cut)
                    improved=sum(passed(r) and not passed(b) for r,b in zip(runs,base));worse=sum(passed(b) and not passed(r) for r,b in zip(runs,base))
                    paired.append(dict(days=horizon,new_passes=improved,lost_passes=worse,net_change_pct=(improved-worse)*100/a.paths))
                case['paired_vs_original']=paired;result['random_cases'].append(case)
                save(ROOT/('PATHS-'+str(seed)+'-'+str(weeks)+'-'+profile['name']+'-'+pol['name']+suffix+'.json'),[p.full_path(r) for r in runs])
                save(ROOT/'Results.json',result)
                print('SUMMARY '+label+' '+profile['name']+' '+pol['name']+' '+json.dumps([(z['days'],z['both_pass_pct'],z['days_to_pass_both']['median']) for z in case['summary']]),flush=True)
    assert all(sha(q)==h for q,h in hashes.items())
    result['verification']=dict(source_hashes_unchanged=True,paths=a.paths*len(PROTOCOLS)*len(portfolios)*len(POLICIES),no_live_changes=True,matched_joint_draws=True,historical_cash_reconciled=True)
    save(ROOT/'Results.json',result);print('THREE PORTFOLIOS COMPLETE',flush=True)
if __name__=='__main__':main()
