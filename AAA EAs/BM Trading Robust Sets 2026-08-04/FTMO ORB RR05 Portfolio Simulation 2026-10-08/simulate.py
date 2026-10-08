"""Offline, paired shared-cash FTMO scenarios; not a calibrated pass forecast.

All source entries/exits are native, freshly aligned to FTMO strategy inputs.
No trading API, terminal control, deployment, credentials or network imports.
The equity check is an initial-stop reserve proxy, NOT measured floating equity.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import argparse, ast, hashlib, html, importlib.util, json, math, random, statistics, sys

ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent
PRIOR=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
sys.path.insert(0,str(BASE/'FTMO Fourteen EA Study 2026-09-27'))
import study as legacy
UTC=timezone.utc; DAY=86400; WEEK=7*DAY
START=datetime(2025,10,6,tzinfo=UTC).timestamp()
END=datetime(2026,10,6,tzinfo=UTC).timestamp()
SYN=datetime(2026,10,12,tzinfo=UTC).timestamp()
STRICT=['us100-h1-orb-13utc','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30']
BROAD=STRICT+['ema3','xau-weakness','xau-elliott-wave-1-2-3','3-way-gold']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dt(v):return datetime.fromisoformat(v).timestamp() if v else None
def iso(v):return datetime.fromtimestamp(v,UTC).isoformat() if v is not None else None
def date(v):return iso(v)[:10] if v is not None else None
def dist(xs):
    if not xs:return dict(n=0,mean=None,median=None,p10=None,p25=None,p75=None,p90=None)
    xs=sorted(xs)
    def q(p):
        k=(len(xs)-1)*p;i=int(k);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(k-i)
    return dict(n=len(xs),mean=statistics.mean(xs),median=statistics.median(xs),p10=q(.1),p25=q(.25),p75=q(.75),p90=q(.9))

def native_rows(q,key,symbol):
    """Initial filled-order stop, not cached configured-risk estimates."""
    symbol='USTEC' if symbol in ('US100','NAS100','USTEC') else symbol
    contract={'XAUUSD':100.,'USTEC':1.,'USDJPY':100000.}[symbol]
    rows=[]
    for t in q['trades']:
        assert t['sl']>0 and t['volume']>0,('Missing protected stop',key,t)
        distance=abs(t['open_price']-t['sl'])
        # MT5 converts the USDJPY quote-currency loss at the stop price.
        unit=distance*contract/(t['sl'] if symbol=='USDJPY' else 1.)
        assert unit>0
        assert (t['sl']<t['open_price'])==(t['side']=='Long'),('Stop geometry',key,t)
        rows.append(dict(key=key,symbol=symbol,news=False,op=t['open_epoch'],cl=max(t['close_epoch'],t['open_epoch']+.001),
                         unit_risk=unit,unit_gross=t['gross']/t['volume'],unit_comm=(t['commission']+t['fee'])/t['volume'],
                         unit_swap=t['swap']/t['volume'],open_price=t['open_price'],close_price=t['close_price'],side=t['side'],
                         lane=str(t.get('magic',0)) if key=='3-way-gold' else key,partial=t.get('partial',False),position_id=t['position_id'],
                         order_compatible=key!='xau-weakness',risk_weight=.5 if key=='xau-weakness' else 1.))
    return rows

def prepare():
    sources=read(ROOT/'NATIVE_SOURCES.json'); manifest=read(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    assert len(sources['entries'])==14 and sources['window']==['2025.10.06','2026.10.06']
    baseline={};fingerprints={};details=[]
    for e in manifest['entries']:
        s=sources['entries'][e['slug']];p=Path(s['path']);assert sha(p)==s['sha256'];fingerprints[str(p)]=sha(p)
        q=read(p);q=q['current'] if s['kind']=='comparison-current' else q
        baseline[e['slug']]=native_rows(q,e['slug'],e['symbol'])
        details.append(dict(slug=e['slug'],trades=q['metrics']['trades'],history_quality=q['native']['history_quality'],
                            source=str(p),partial_positions=q['metrics'].get('partial_positions',0)))
    candidates={};qual=[]
    for key in BROAD+['us100-selective-orb-v3']:
        p=ROOT/'FTMO_MARKET_3WAY_COMPARISON.json' if key=='3-way-gold' else PRIOR/'comparisons'/(key+'.json')
        q=read(p);fingerprints[str(p)]=sha(p)
        a=q['current']['metrics'];b=q['half']['metrics']
        qualifies=(b['pf'] is not None and b['pf']>=1.15 and b['win_rate']>a['win_rate'] and b['win_streak']>a['win_streak'])
        candidates[key]=native_rows(q['half'],key,q['symbol'])
        qual.append(dict(slug=key,label=q['label'],current=a,candidate=b,qualifies=qualifies,
                         order_compatible=key!='xau-weakness',already_ftmo=key in baseline,
                         note='FTMO market-entry reproduction' if key=='3-way-gold' else 'Five trades, zero losses: PF undefined, provisional only' if key=='us100-selective-orb-v3' else 'Pending orders rejected by current FTMO guard' if key=='xau-weakness' else ''))
    selected=[q['slug'] for q in qual if q['qualifies'] and q['order_compatible']]
    strict=[k for k in STRICT if k in selected]
    def config(name,label,replacements,provisional=False,small_additions=False):
        pool={k:[dict(r) for r in rr] for k,rr in baseline.items()}
        for k in replacements:pool[k]=[dict(r) for r in candidates[k]]
        if provisional:pool['us100-selective-orb-v3']=[dict(r) for r in candidates['us100-selective-orb-v3']]
        if small_additions:
            for k,rr in pool.items():
                if k not in baseline:
                    for r in rr:r['risk_weight']*=.5
        return dict(name=name,label=label,ea_count=len(pool),replacements=[k for k in replacements if k in baseline],
                    additions=[k for k in pool if k not in baseline],rows=[r for rr in pool.values() for r in rr],
                    small_additions=small_additions)
    configs=[config('baseline','Current FTMO 14',[]),config('orb_only','Only qualifying classical ORBs',strict),
             config('all_compatible','All qualifying, FTMO-compatible',selected),
             config('new_only','Add new qualifying EAs; keep current targets',[k for k in selected if k not in baseline]),
             config('small_additions','All compatible; new additions at $25',selected,small_additions=True),
             config('selective_sensitivity','All compatible + provisional Selective',selected,provisional=True)]
    audit=dict(window_from=date(START),window_through=date(END-DAY),end_exclusive=iso(END),
               package_version=manifest['version'],risk_usd=50,news_enabled=False,initial_stops_reconstructed=True,
               baseline_sources=details,qualified=qual,selected_compatible=selected,source_hashes=fingerprints,
               strategy_inputs_match_ftmo=True,standalone_percent_risk=1,portfolio_fixed_risk=50,
               guarded_native_portfolio=False)
    save(ROOT/'DATA_AUDIT.json',audit)
    save(ROOT/'FROZEN_ROWS.json',{c['name']:c['rows'] for c in configs})
    return configs,audit

def engine(risk=50.,reserve_multiple=1.25,cooldown=False):
    ns=legacy.engine(risk)
    text=(legacy.OLD/'simulate.py').read_text(encoding='utf-8-sig')
    fn=next(n for n in ast.parse((legacy.ROOT/'study.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='engine')
    repl=ast.literal_eval(next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='replacements' for t in n.targets)))
    for a,b in repl.items():assert text.count(a)==1;text=text.replace(a,b)
    # Source lanes allow 3-Way's distinct modules to coexist; same lane remains blocked.
    text=text.replace("if any(p['key']==key for p in active.values()):", "if any(p.get('lane',p['key'])==r.get('lane',key) for p in active.values()):")
    text=text.replace("lot=rounded(RISK/r['unit_risk'])", "budget=RISK*r.get('risk_weight',1.)\n                lot=rounded(budget/r['unit_risk'])")
    text=text.replace('assert risk<=RISK+1e-7','assert risk<=budget+1e-7')
    text=text.replace("env=risk*(1.25 if stress else 1.)",f"env=risk*({reserve_multiple!r}*(1.25 if stress else 1.))+5.")
    text=text.replace("p=dict(lot=lot,risk=risk,margin=marg,env=env,key=key,group=", "p=dict(lot=lot,risk=risk,margin=marg,env=env,key=key,lane=r.get('lane',key),group=")
    text=text.replace("r=rows[i];key=r['key'];g,c,s,x=r['_costs'];sym=r['symbol']", "r=rows[i];key=r['key'];g,c,s,x=r['_costs'];sym=r['symbol']\n            if not r.get('order_compatible',True):counts['unsupported_pending_order']+=1;continue")
    # No account-wide retry scheduling is reconstructed; rejected single-source
    # fills are not re-entered. Separate same-second sensitivity is reported.
    text=text.replace('events.sort()', "events.sort(key=lambda e:(e[0],-1 if e[1]==2 else e[1],e[2]))")
    if cooldown:
        text=text.replace("reason=gate(t)\n                if reason:", "reason=gate(t)\n                if t<entry_ready:reason='entry_reconciliation_cooldown'\n                if reason:")
        text=text.replace('today_count=0;max_daily_entries=0;', 'entry_ready=start;today_count=0;max_daily_entries=0;')
        text=text.replace("active[i]=p;today_count+=1;", "entry_ready=t+3;active[i]=p;today_count+=1;")
    ns['iso']=iso
    exec(compile(ast.Module(body=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='replay'],type_ignores=[]),'orb_ftmo_offline','exec'),ns)
    return ns

def continuous(r,start,end):
    log=r['log'];daily=defaultdict(float);curve=[[0,10000.]];months=defaultdict(lambda:dict(trades=0,net=0.))
    for x in log:
        daily[x['close'][:10]]+=x['net_profit'];curve.append([(dt(x['close'])-start)/DAY,x['balance']])
        v=months[x['close'][:7]];v['trades']+=1;v['net']+=x['net_profit']
    vals=[];d=datetime.fromtimestamp(start,UTC)
    while d.timestamp()<end:
        if d.weekday()<5:vals.append(daily[d.date().isoformat()]/10000)
        d+=timedelta(days=1)
    sd=statistics.stdev(vals) if len(vals)>1 else 0
    cash=sum(x['net_profit'] for x in log)+r['unclosed_entry_costs'];assert abs(cash-(r['balance']-10000))<1e-5
    return dict(trades=r['trades'],win_rate=r['win_rate'],pf=r['pf'],return_pct=(r['balance']/10000-1)*100,
                closed_balance_dd_pct=r['closed_dd_pct'],stop_reserve_proxy_dd_pct=r['model_dd_pct'],
                daily_closed_sharpe=statistics.mean(vals)/sd*math.sqrt(252) if sd else None,
                win_streak=r['max_win_streak'],loss_streak=r['max_loss_streak'],model_breach=r['breach'],
                months=dict(months),contributions=r['by_ea'],skips=r['counts'],balance_curve=curve,
                open_at_end=r['open_positions'],cash_reconciled=True)

def horizon_summary(results,start,horizon,fee=None):
    end=start+horizon*DAY;n=len(results)
    before=lambda v:v is not None and dt(v)<end
    p1=[r for r in results if r['passes'] and before(r['passes'][0]['time'])]
    both=[r for r in results if len(r['passes'])==2 and before(r['passes'][1]['time'])]
    funded=[r for r in results if before(r['funded_at'])]
    paid=[r for r in results if before(r['receipt_at'])]
    breached=[r for r in results if before(r['breach_at'])]
    eval_breach=[r for r in breached if not r['funded_at'] or dt(r['breach_at'])<dt(r['funded_at'])]
    paid_ids={id(r) for r in paid};both_ids={id(r) for r in both};breach_ids={id(r) for r in eval_breach}
    unresolved=[r for r in results if id(r) not in both_ids and id(r) not in breach_ids]
    def timing(rs,field):return dist([(dt(r[field])-start)/DAY for r in rs])
    rewards=[r['reward'] if id(r) in paid_ids else 0. for r in results]
    expectation=statistics.mean(rewards)
    ratio=len(paid)/n
    fees=[fee] if fee else [150.,200.]
    return dict(days=horizon,paths=n,phase1_pass_pct=len(p1)*100/n,both_pass_pct=len(both)*100/n,
                funded_pct=len(funded)*100/n,first_reward_received_pct=ratio*100,
                evaluation_proxy_breach_pct=len(eval_breach)*100/n,all_proxy_breach_pct=len(breached)*100/n,
                unfinished_evaluation_pct=len(unresolved)*100/n,
                days_to_pass_both=dist([(dt(r['passes'][1]['time'])-start)/DAY for r in both]),
                days_to_funded=timing(funded,'funded_at'),days_to_first_reward=timing(paid,'receipt_at'),
                expected_first_reward_usd=expectation,reward_if_received=dist([r['reward'] for r in paid]),
                expected_net_cash_and_fee_roi=[dict(fee_usd=f,assumed=fee is None,expected_net_cash=expectation+ratio*f-f,
                     expected_fee_roi_pct=100*(expectation+ratio*f-f)/f) for f in fees],
                pass_mc_only_interval=legacy.c.wilson(len(both),n),
                synthetic_funded_date_median=date(start+(timing(funded,'funded_at')['median'] or 0)*DAY) if funded else None)

def samples(configs,weeks,paths,seed,recent_only=False):
    """Joint blocks sampled once across all assets/EAs; never independent trades."""
    poolweeks=int((END-START)//WEEK)
    lo=poolweeks-13 if recent_only else 0
    available=list(range(lo,poolweeks-weeks+1));assert available
    rng=random.Random(seed)
    draws=[[rng.choice(available) for _ in range(math.ceil(365/(7*weeks)))] for _ in range(paths)]
    pools={c['name']:[[] for _ in range(poolweeks)] for c in configs}
    for c in configs:
        for r in c['rows']:
            j=int((r['op']-START)//WEEK)
            if 0<=j<poolweeks:pools[c['name']][j].append(r)
    ny=legacy.c.ZoneInfo('America/New_York')
    def shifted(name,draw):
        out=[]
        for i,j in enumerate(draw):
            src=START+j*WEEK;dest=SYN+i*weeks*WEEK
            off=dest-src+datetime.fromtimestamp(src+2*DAY,ny).utcoffset().total_seconds()-datetime.fromtimestamp(dest+2*DAY,ny).utcoffset().total_seconds()
            for bucket in pools[name][j:j+weeks]:
                for r in bucket:
                    if SYN<=r['op']+off<SYN+365*DAY:
                        out.append(dict(r,op=r['op']+off,cl=r['cl']+off))
        return out
    return draws,shifted

def tests():
    out=legacy.unit_tests();ns=engine();t=START
    base=dict(key='t',symbol='USTEC',news=False,op=t+100,cl=t+200,unit_risk=1000.,unit_gross=500.,unit_comm=-.7,unit_swap=0.,open_price=25000.,close_price=25500.,side='Long')
    r=ns['replay']([dict(base)],[],t,t+DAY,challenge=False,detail=True)
    assert r['trades']==1 and r['log'][0]['lots']==.05
    assert ns['replay']([dict(base,order_compatible=False)],[],t,t+DAY,challenge=False)['trades']==0
    r=ns['replay']([dict(base,lane='a'),dict(base,op=t+101,lane='b')],[],t,t+DAY,challenge=False)
    assert r['trades']==2
    r=ns['replay']([dict(base),dict(base,op=t+101)],[],t,t+DAY,challenge=False)
    assert r['trades']==1
    r=ns['replay']([dict(base,risk_weight=.5)],[],t,t+DAY,challenge=False,detail=True)
    assert r['log'][0]['lots']==.02 and r['log'][0]['initial_risk']==20
    return dict(legacy=out,new_checks=5)

def main():
    p=argparse.ArgumentParser();p.add_argument('--paths',type=int,default=1500);p.add_argument('--fee-usd',type=float);a=p.parse_args()
    checks=tests();configs,audit=prepare();ns=engine()
    result=dict(status='Research-only standalone-ledger overlay; stop-reserve proxy, not measured FTMO equity or a forecast',
                checks=checks,audit=audit,paths_per_case=a.paths,synthetic_from=iso(SYN),synthetic_end_exclusive=iso(SYN+365*DAY),
                seed=20261008,fee_usd=a.fee_usd,first_reward_only=True,historical=[],historical_starts=[],random_cases=[],
                methodology='Fixed $50 initial stop budget, floor to 0.01, skip below minimum; FTMO Swing simplified 1:15 indices/metals, 1:30 FX. 7 entries, 3 losses/day, 225 portfolio/150 symbol initial risk, 300 daily/9200 total reserve guards. 1.25 initial risk +5 per position reserve (extra stress 1.25). Prague midnight; distinct 4 entry-days per phase; target 10%/5%; 2/5 business-day administrative waits; first reward 80%, 14 days after first funded trade, flat and at least $25 profit, 4 business-day assumed processing. No arbitrary evaluation expiry.',
                limitations=['No native guarded multi-EA portfolio test or FTMO bid/ask floating-equity replay. Reserve breaches are proxies, not real breach probabilities or mathematical loss bounds.',
                    'Standalone source trades can change if shared guards reject an entry. Rejected setups are not re-entered or recomputed; partial closes are collapsed into final position cash and closing time.',
                    'The 3-second account-wide entry reconciliation cooldown and detailed retry/error/position-stop updates are not reconstructed; simultaneous-chart scheduling can change admissions.',
                    'Native tests use 76% real ticks with generated-tick fallback before 2026-01-01. Tester wall timestamps use the existing UTC convention.',
                    'Portfolio additions are selected on this same year. This is fitted-history experimentation, not untouched out-of-sample validation.',
                    'Joint block bootstrap preserves cross-EA source timing within blocks. Trades can extend beyond a source block; no coherent synthetic price history or new signals are generated. Cross-block dependencies are weakened.',
                    'Historical spread/gap fills remain in native cash. Explicit commission floors and stress carry are scenarios, not reconstructed FTMO execution.',
                    'The 1% standalone risk input is not the portfolio risk: all overlay positions are re-sized from their filled-order initial stops to $50 or labelled $25 additions.',
                    'News, hourly bots, fee exchange rates, scaling, tax and repeated payouts are excluded. Conditional days censor unfinished accounts; failed/unfinished paths contribute zero first reward.'])
    for c in configs:
        rr=[dict(r) for r in c['rows'] if START<=r['op']<r['cl']<END]
        hist=ns['replay'](rr,[],START,END,challenge=False,detail=True)
        hc=ns['replay']([dict(r) for r in rr],[],START,END,detail=True)
        result['historical'].append(dict(name=c['name'],label=c['label'],ea_count=c['ea_count'],replacements=c['replacements'],additions=c['additions'],
                                       portfolio=continuous(hist,START,END),challenge=hc))
        for horizon in (90,180):
            start=START
            while start+horizon*DAY<=END:
                rows=[dict(r) for r in rr if start<=r['op']<start+horizon*DAY]
                v=ns['replay'](rows,[],start,start+horizon*DAY)
                result['historical_starts'].append(dict(portfolio=c['name'],horizon_days=horizon,start=date(start),end_exclusive=date(start+horizon*DAY),
                    both_passed=len(v['passes'])==2,phase1_passed=bool(v['passes']),passes=v['passes'],funded_at=v['funded_at'],
                    reward_received=v['payout'],reward_at=v['receipt_at'],first_reward=v['reward'] if v['payout'] else 0.,
                    breach=v['breach'],ending_balance=v['balance'],trades=v['trades']))
                start+=WEEK
        print('HISTORY '+c['name']+' '+json.dumps({k:v for k,v in result['historical'][-1]['portfolio'].items() if k not in ('months','contributions','skips','balance_curve')}),flush=True)
    save(ROOT/'Results.json',result)
    protocols=[('Joint 4-week blocks',4,False,False,False,20261008),('Joint 8-week blocks',8,False,False,False,20261009),
               ('Execution/carry stress, 4-week blocks',4,True,False,False,20261008),('Recent 13-week pool, 2-week blocks',2,False,True,False,20261010),
               ('3-second entry cooldown, no retries',4,False,False,True,20261008)]
    for label,weeks,stress,recent,cooldown,seed in protocols:
        ns=engine(cooldown=cooldown)
        draws,shifted=samples(configs,weeks,a.paths,seed,recent)
        save(ROOT/('DRAWS-'+str(seed)+'-'+str(weeks)+'.json'),dict(seed=seed,block_weeks=weeks,recent_only=recent,draws=draws))
        full=[]
        for c in configs:
            rr=[]
            for i,draw in enumerate(draws):
                rr.append(ns['replay'](shifted(c['name'],draw),[],SYN,SYN+365*DAY,stress=stress))
                if (i+1)%500==0:print(label+' '+c['name']+' '+str(i+1)+'/'+str(a.paths),flush=True)
            sums=[horizon_summary(rr,SYN,h,a.fee_usd) for h in (90,180,365)]
            result['random_cases'].append(dict(protocol=label,block_weeks=weeks,stress=stress,recent_only=recent,cooldown=cooldown,seed=seed,portfolio=c['name'],ea_count=c['ea_count'],summary=sums))
            full.append(rr)
            save(ROOT/('PATHS-'+str(seed)+'-'+str(weeks)+'-'+c['name']+('-stress' if stress else '-cooldown' if cooldown else '')+'.json'),
                 [{k:r[k] for k in ('passes','funded_at','receipt_at','breach_at','reward','counts','trades','phase','model_dd_pct','closed_dd_pct')} for r in rr])
            print('SUMMARY '+label+' '+c['name']+' '+json.dumps(sums[-1]),flush=True)
            save(ROOT/'Results.json',result)
        # Paired changes: same sampled market blocks, not separate favourable draws.
        ref=full[0]
        for idx,c in enumerate(configs[1:],1):
            win=sum(len(r['passes'])==2 and len(b['passes'])!=2 for r,b in zip(full[idx],ref))
            lose=sum(len(r['passes'])!=2 and len(b['passes'])==2 for r,b in zip(full[idx],ref))
            case=next(x for x in result['random_cases'] if x['protocol']==label and x['portfolio']==c['name'])
            case['paired_vs_baseline_365d']=dict(new_passes=win,lost_passes=lose,net_pass_change_pct=(win-lose)*100/a.paths,
                                               expected_reward_change=statistics.mean((r['reward'] if r['payout'] else 0)-(b['reward'] if b['payout'] else 0) for r,b in zip(full[idx],ref)))
        save(ROOT/'Results.json',result)
    assert all(sha(p)==v for p,v in audit['source_hashes'].items())
    result['verification']=dict(source_hashes_unchanged=True,paths=a.paths*len(protocols)*len(configs),
                                paired_draws=True,no_live_changes=True,historical_cash_reconciled=True)
    save(ROOT/'Results.json',result)
    print('ALL PORTFOLIO SIMULATIONS COMPLETE',flush=True)

if __name__=='__main__':main()
