"""Offline ORB risk sensitivity. No live account, deployment or trading API."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ast, hashlib, importlib.util, json, math, statistics

ROOT=Path(__file__).resolve().parent
PURE=ROOT.parent/'FTMO Pure ORB Swing Portfolio 2026-10-08'
spec=importlib.util.spec_from_file_location('pure_orb_risk_parent',PURE/'run.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
s=p.s;DAY=p.DAY;START=p.START;END=p.END;SYN=p.SYN
MODES=[('fixed_50','Existing fixed $50'),('fixed_150','Fixed $150 (1.5% of starting capital)'),
       ('balance_1p5','Dynamic 1.5% of current closed balance')]
PROTOCOLS=[('Joint 4-week blocks',4,False,False,False,20261008),
           ('Joint 8-week blocks',8,False,False,False,20261009),
           ('Execution/carry stress',4,True,False,False,20261008),
           ('Recent 13-week pool',2,False,True,False,20261010),
           ('3-second cooldown, no retries',4,False,False,True,20261008)]

def read(q):return json.loads(Path(q).read_text(encoding='utf-8-sig'))
def save(q,v):Path(q).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(q):return hashlib.sha256(Path(q).read_bytes()).hexdigest()

def engine(mode,cooldown=False):
    # Capture the already-verified generator's exact final replay source. The
    # only simulation change is the per-entry planned-risk budget expression.
    tree=ast.parse((s.ROOT/'simulate.py').read_text(encoding='utf-8-sig'))
    fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='engine')
    captures=0
    for i,x in enumerate(fn.body):
        if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='exec':
            fn.body[i]=ast.parse("ns['_captured_replay_source']=text").body[0];captures+=1
    assert captures==1
    env=dict(s.__dict__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'captured_existing_generator','exec'),env)
    ns=env['engine'](50. if mode=='fixed_50' else 150.,cooldown=cooldown)
    source=ns.pop('_captured_replay_source')
    before="budget=RISK*r.get('risk_weight',1.)"
    assert source.count(before)==1
    if mode=='balance_1p5':
        source=source.replace(before,"budget=.015*bal*r.get('risk_weight',1.)")
    # Record the actual information available at entry so the new dynamic
    # budget can be independently checked without assuming trade ordering.
    capture="fee=entry_charge(r,c,x)*p['lot'];bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)"
    assert source.count(capture)==1
    source=source.replace(capture,"fee=entry_charge(r,c,x)*p['lot'];p.update(balance_before_entry=bal,planned_risk_budget=budget);bal+=fee;p.update(phase=phase,opened=t,entryfee=fee)")
    capture="initial_risk=p['risk'],actual_fill_stop_risk="
    assert source.count(capture)==1
    source=source.replace(capture,"initial_risk=p['risk'],balance_before_entry=p['balance_before_entry'],planned_risk_budget=p['planned_risk_budget'],actual_fill_stop_risk=")
    assert mode in {m[0] for m in MODES}
    tree=ast.parse(source)
    replay=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='replay')
    exec(compile(ast.Module(body=[replay],type_ignores=[]),'orb_risk_sensitivity','exec'),ns)
    return ns

def tests():
    checks=s.tests();t=START
    def row(i=0,**kw):
        out=dict(key='a'+str(i),symbol='USTEC',news=False,op=t+3600+i*DAY,cl=t+3660+i*DAY,
                 unit_risk=1000.,unit_gross=500.,unit_comm=-.7,unit_swap=0.,
                 open_price=25000.,close_price=25500.,side='Long');out.update(kw);return out
    for mode,expected in [('fixed_50',.05),('fixed_150',.15),('balance_1p5',.15)]:
        r=engine(mode)['replay']([row()],[],t,t+DAY,challenge=False,detail=True)
        assert r['log'][0]['lots']==expected and r['max_open_risk']<=150+1e-7
    # Prove current balance, not initial balance, is used after a loss.
    r=engine('balance_1p5')['replay']([row(unit_gross=-1000.),row(1)],[],t,t+3*DAY,challenge=False,detail=True)
    assert r['log'][0]['lots']==.15 and r['log'][1]['lots']==.14
    # Profit can push a tiny risk step above the UNCHANGED $150 symbol cap.
    tiny=row(unit_risk=100.,unit_gross=50.)
    r=engine('balance_1p5')['replay']([tiny,dict(tiny,key='b',op=t+DAY+3600,cl=t+DAY+3660)],[],t,t+3*DAY,challenge=False)
    assert r['trades']==1 and r['counts']['correlated_risk_rejected']==1
    # Two full-size simultaneous orders exceed the unchanged $225 aggregate cap.
    r=engine('fixed_150')['replay']([row(),row(1,op=t+3601,cl=t+3661)],[],t,t+DAY,challenge=False)
    assert r['trades']==1 and r['counts']['open_risk_rejected']==1
    r=engine('balance_1p5')['replay']([row(unit_risk=16000.)],[],t,t+DAY,challenge=False)
    assert r['trades']==0 and r['counts']['min_lot_over_budget']==1
    return dict(parent_checks=checks,new_risk_checks=8)

def summaries(runs):
    out=[]
    for h in (90,180,365,730):
        z=s.horizon_summary(runs,SYN,h);cut=SYN+h*DAY
        p1=[r for r in runs if r['passes'] and p.before(r['passes'][0]['time'],cut)]
        z['days_to_phase1']=s.dist([(p.stamp(r['passes'][0]['time'])-SYN)/DAY for r in p1])
        out.append(z)
    return out

def main():
    args=argparse.ArgumentParser();args.add_argument('--paths',type=int,default=1000);args.add_argument('--history-only',action='store_true');a=args.parse_args()
    checks=tests();old=read(PURE/'Results.json');frozen=read(PURE/'FROZEN_ROWS.json')
    rows=frozen['orb_qualified_4'];config=[dict(name='orb_qualified_4',rows=rows)]
    source_files=[PURE/'Results.json',PURE/'PORTFOLIO.json',PURE/'FROZEN_ROWS.json',PURE/'run.py',s.ROOT/'simulate.py']
    hashes={str(q):sha(q) for q in source_files};hashes.update(old['sources'])
    d=dict(window_from=old['window_from'],window_through=old['window_through'],synthetic_start=old['synthetic_start'],
           risk_cases=[dict(name=x,label=y) for x,y in MODES],paths_per_case=a.paths,checks=checks,
           account_capital=10000,shared_guard=old['profile']['shared_guard'],official_limits_unchanged=True,
           primary_interpretation='1.5% of current closed balance at each entry, before its fees; phase balance resets to $10,000. Fixed $150 is shown separately.',
           guard_warning='The existing symbol cap is $150. Dynamic requested risk above that cap is rejected, not clamped. Aggregate cap $225 and daily reserve $300 are not increased.',
           live_guard_warning='The actual compiled FTMO guard still caps each order at $50. This is a hypothetical change to its per-order sizing budget only; no live code or package changed.',
           original_profile=old['profile']['entries'],sources=hashes,historical=[],random_cases=[],
           limitations=old['limitations']+old['new_limitations']+[
                'Dynamic 1.5% can become incompatible with the unchanged fixed-dollar symbol cap as balance grows. This can stall evaluation without breaching any limit.',
                'The 730-day comparison repeats/resamples the same one-year source pool; not fresh historical validation.',
                'Loss guards reject new entries; they do not guarantee a loss cap on positions already open. Floating equity remains a stop-reserve proxy.'])
    for mode,label in MODES:
        ns=engine(mode);rr=[dict(r) for r in rows if START<=r['op']<r['cl']<END]
        hist=ns['replay'](rr,[],START,END,challenge=False,detail=True)
        if mode=='fixed_50':
            ref=next(x for x in old['historical'] if x['name']=='orb_qualified_4')
            assert s.continuous(hist,START,END)==ref['portfolio']
        challenge=ns['replay']([dict(r) for r in rr],[],START,END,detail=True)
        item=dict(mode=mode,label=label,portfolio=s.continuous(hist,START,END),challenge=challenge,
                  trades_per_weekday=hist['trades']/261,log=hist['log'],max_open_risk=hist['max_open_risk'],worst_daily_reserve_usd=hist['worst_daily_usd'])
        d['historical'].append(item)
        print('HISTORY '+mode+' '+json.dumps({k:v for k,v in item['portfolio'].items() if k not in ('balance_curve','months','contributions')}),flush=True)
    if a.history_only:
        save(ROOT/'HistoryProbe.json',d);return
    save(ROOT/'Results.json',d)
    for label,weeks,stress,recent,cooldown,seed in PROTOCOLS:
        draws,shifted=p.joint_samples(config,weeks,a.paths,seed,730,recent)
        reference=read(PURE/('DRAWS-'+str(seed)+'-'+str(weeks)+'.json'))
        assert draws==reference['draws'][:a.paths]
        for mode,_ in MODES:
            suffix='-stress' if stress else '-cooldown' if cooldown else ''
            if mode=='fixed_50':
                runs=read(PURE/('PATHS-'+str(seed)+'-'+str(weeks)+'-orb_qualified_4'+suffix+'.json'))[:a.paths]
            else:
                ns=engine(mode,cooldown);runs=[]
                for i,draw in enumerate(draws):
                    runs.append(ns['replay'](shifted('orb_qualified_4',draw),[],SYN,SYN+730*DAY,stress=stress))
                    if (i+1)%500==0:print(label+' '+mode+' '+str(i+1)+'/'+str(a.paths),flush=True)
            z=summaries(runs)
            case=dict(protocol=label,mode=mode,block_weeks=weeks,seed=seed,stress=stress,recent_only=recent,cooldown=cooldown,summary=z)
            d['random_cases'].append(case)
            fields=('passes','funded_at','receipt_at','request_at','breach_at','reward','counts','trades','phase','model_dd_pct','closed_dd_pct')
            save(ROOT/('PATHS-'+str(seed)+'-'+str(weeks)+'-'+mode+suffix+'.json'),[{k:r[k] for k in fields} for r in runs])
            save(ROOT/'Results.json',d)
            print('SUMMARY '+label+' '+mode+' '+json.dumps([(x['days'],x['both_pass_pct'],x['days_to_pass_both']['median']) for x in z]),flush=True)
    assert all(sha(q)==v for q,v in hashes.items())
    d['verification']=dict(sources_unchanged=True,no_live_changes=True,matched_draws=True,paths=a.paths*len(MODES)*len(PROTOCOLS))
    save(ROOT/'Results.json',d);print('ORB RISK COMPARISON COMPLETE',flush=True)

if __name__=='__main__':main()
