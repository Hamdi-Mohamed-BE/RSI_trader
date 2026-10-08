"""Genuinely ORB-only research profile, shared cash, unchanged FTMO Swing guards.

No live account access, terminal startup, installer, deployment or MT5 imports.
Reuses fingerprinted native ledgers and the checked prior offline proxy engine.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
import argparse, hashlib, importlib.util, json, math, random, statistics

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
PRIOR=BASE/'FTMO ORB RR05 Portfolio Simulation 2026-10-08'
NATIVE=BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08'
spec=importlib.util.spec_from_file_location('prior_orb_replay',PRIOR/'simulate.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
DAY=s.DAY;WEEK=s.WEEK;UTC=timezone.utc;START=s.START;END=s.END;SYN=s.SYN
SCOPE=['us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3',
       'orb-volume-profile','orb-volume-profile-volume-confirmed','xau-orb-new-york-m30',
       'xau-orb-london-ny-overlap-m30','asia-breakout']
CORE=['us100-h1-orb-13utc','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30']
SELECTIVE='us100-selective-orb-v3'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def before(v,t):return v is not None and datetime.fromisoformat(v).timestamp()<t
def stamp(v):return datetime.fromisoformat(v).timestamp() if v else None

def prepare():
    plan={x['slug']:x for x in read(NATIVE/'PLAN.json')['setups']}
    selected=[];individual=[];audit=[];fingerprints={};rows={}
    ns=s.engine()
    for key in SCOPE:
        p=NATIVE/'comparisons'/(key+'.json');q=read(p);fingerprints[str(p)]=sha(p)
        eligible=[]
        for v in ('half','current'):
            m=q[v]['metrics']
            ok=m['win_rate']>=60. and m['pf'] is not None and m['pf']>=1.15
            audit.append(dict(slug=key,label=q['label'],variant=v,native_trades=m['trades'],
                              native_win_rate=m['win_rate'],native_pf=m['pf'],qualifies=ok,
                              reason='PF undefined: no losses; not treated as proven infinite PF' if m['pf'] is None else 'PF below 1.15 or win rate below 60%' if not ok else 'Passed numerical gate'))
            if ok:eligible.append(v)
        if not eligible:continue
        # Prefer the previously tested 0.5R version; no ranking/optimisation here.
        variant=eligible[0];rr=s.native_rows(q[variant],key,q['symbol'])
        native=q[variant]['metrics'];r=ns['replay']([dict(x) for x in rr],[],START,END,challenge=False,detail=True)
        m=s.continuous(r,START,END)
        assert m['win_rate']>=60 and m['pf']>=1.15,(key,m)
        rows[key]=rr;selected.append(key)
        individual.append(dict(slug=key,label=q['label'],variant=variant,rr=float(q[variant]['inputs']['InpRewardRisk']),
                               native=native,ftmo_proxy=m,source_path=str(p),source_sha256=sha(p),
                               small_sample_warning='Only 5 native trades; exploratory, not sufficient validation' if key==SELECTIVE else 'Only 12 native trades' if key=='xau-orb-new-york-m30' else None))
    assert set(selected)==set(CORE+[SELECTIVE])
    references=read(PRIOR/'FROZEN_ROWS.json');base=references['baseline']
    configs=[dict(name='orb_core_3',label='Pure ORB: three 0.5R EAs',ea_count=3,rows=[r for k in CORE for r in rows[k]]),
             dict(name='orb_qualified_4',label='Pure ORB: all four qualifying EAs',ea_count=4,rows=[r for k in selected for r in rows[k]]),
             dict(name='current_ftmo_14',label='Current FTMO 14 benchmark',ea_count=14,rows=base)]
    fingerprint_paths=[PRIOR/'FROZEN_ROWS.json',PRIOR/'simulate.py',s.legacy.ROOT/'study.py',s.legacy.OLD/'simulate.py',
        s.legacy.OLD/'prepare.py',BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json',
        BASE/'FTMO Thirteen EA Deployment 2026-09-27/CalyxFTMOGuard.mqh']
    fingerprints.update({str(p):sha(p) for p in fingerprint_paths})
    profile=dict(name='FTMO Pure ORB Swing',status='Research profile only; not an installed or validated guarded EA package',
                 account='FTMO 2-Step Swing',capital_usd=10000,risk_mode='fixed USD',risk_per_trade_usd=50,news=False,
                 selection='Native net win rate >=60% and finite PF >=1.15; rechecked under the FTMO $50 single-EA overlay',
                 only_opening_range_strategies=True,no_non_orb_eas=True,
                 phase_targets_pct=[10,5],official_daily_equity_loss_usd=500,official_total_equity_loss_usd=1000,
                 minimum_trading_days_per_phase=4,unlimited_evaluation_time=True,
                 shared_guard=dict(entries_per_prague_day=7,closed_losses_per_day=3,aggregate_initial_risk_usd=225,
                    same_symbol_initial_risk_usd=150,daily_admission_reserve_usd=300,equity_admission_buffer_usd=9200,
                    initial_stop_reserve_multiple=1.25,additional_reserve_usd_per_position=5,
                    margin_fraction=.8,lot_step=.01,minimum_lot=.01,rounding='down, skip below minimum',
                    guard_source_sha256=sha(fingerprint_paths[-1])),
                 entries=[dict(slug=x['slug'],label=x['label'],symbol=plan[x['slug']]['symbol'],timeframe=plan[x['slug']]['period'],
                    reward_risk=x['rr'],variant=x['variant'],expert_source=plan[x['slug']]['expert'],
                    preset_source=plan[x['slug']]['preset'],warning=x['small_sample_warning']) for x in individual],
                 protective_stops_required=True,market_entries_only=True,live_installation=False,
                 caveat='A source SET or EX5 is not automatically a guarded FTMO build. No installer is created and no source input is deployed.')
    save(ROOT/'PORTFOLIO.json',profile);save(ROOT/'SELECTION_AUDIT.json',audit)
    save(ROOT/'SOURCE_HASHES.json',fingerprints);save(ROOT/'FROZEN_ROWS.json',{c['name']:c['rows'] for c in configs})
    return configs,individual,profile,fingerprints

def joint_samples(configs,weeks,paths,seed,horizon,recent=False):
    poolweeks=int((END-START)//WEEK);lo=poolweeks-13 if recent else 0
    starts=list(range(lo,poolweeks-weeks+1));rng=random.Random(seed)
    draws=[[rng.choice(starts) for _ in range(math.ceil(horizon/(7*weeks)))] for _ in range(paths)]
    buckets={c['name']:[[] for _ in range(poolweeks)] for c in configs}
    for c in configs:
        for r in c['rows']:
            j=int((r['op']-START)//WEEK)
            if 0<=j<poolweeks:buckets[c['name']][j].append(r)
    ny=ZoneInfo('America/New_York')
    def shifted(name,draw):
        out=[]
        for i,j in enumerate(draw):
            src=START+j*WEEK;dest=SYN+i*weeks*WEEK
            offset=dest-src+datetime.fromtimestamp(src+2*DAY,ny).utcoffset().total_seconds()-datetime.fromtimestamp(dest+2*DAY,ny).utcoffset().total_seconds()
            for bucket in buckets[name][j:j+weeks]:
                for r in bucket:
                    if SYN<=r['op']+offset<SYN+horizon*DAY:
                        out.append(dict(r,op=r['op']+offset,cl=r['cl']+offset))
        return out
    return draws,shifted

def full_path(r):
    return {k:r[k] for k in ('passes','funded_at','receipt_at','request_at','breach_at','reward','counts','trades','phase','model_dd_pct','closed_dd_pct')}

def main():
    p=argparse.ArgumentParser();p.add_argument('--paths',type=int,default=1000);a=p.parse_args()
    configs,individual,profile,fingerprints=prepare();ns=s.engine()
    old=read(PRIOR/'Results.json')
    result=dict(status='Research-only ORB profile and stop-reserve proxy, not a calibrated FTMO forecast',
                window_from=s.date(START),window_through=s.date(END-DAY),synthetic_start=s.iso(SYN),
                paths_per_case=a.paths,profile=profile,individual=individual,historical=[],starts=[],random_cases=[],
                selection_audit=read(ROOT/'SELECTION_AUDIT.json'),methodology=old['methodology'],limitations=old['limitations'],
                new_limitations=['The Selective 2R variant is included because its finite PF and 80% win rate pass the literal filter, but there are only five trades. Its zero-loss 0.5R version is not accepted as a finite-PF result.',
                                 '730-day scenarios repeat/resample the same single year of evidence; they are not two years of new historical tests. These sparse ORBs can remain unfinished for a long time at unchanged $50 risk.'],
                sources=fingerprints)
    for c in configs:
        rr=[dict(r) for r in c['rows'] if START<=r['op']<r['cl']<END]
        hist=ns['replay'](rr,[],START,END,challenge=False,detail=True)
        h=s.continuous(hist,START,END);challenge=ns['replay']([dict(r) for r in rr],[],START,END,detail=True)
        result['historical'].append(dict(name=c['name'],label=c['label'],ea_count=c['ea_count'],portfolio=h,challenge=challenge))
        for horizon in (90,180):
            begin=START
            while begin+horizon*DAY<=END:
                cut=begin+horizon*DAY;rows=[dict(r) for r in rr if begin<=r['op']<cut]
                r=ns['replay'](rows,[],begin,cut)
                result['starts'].append(dict(portfolio=c['name'],horizon_days=horizon,start=s.date(begin),end_exclusive=s.date(cut),
                    both_passed=len(r['passes'])==2,phase1_passed=bool(r['passes']),passes=r['passes'],funded_at=r['funded_at'],
                    reward_received=r['payout'],reward_at=r['receipt_at'],reward=r['reward'] if r['payout'] else 0.,
                    breach=r['breach'],trades=r['trades'],phase=r['phase']))
                begin+=WEEK
        print('HISTORY '+c['name']+' '+json.dumps({k:v for k,v in h.items() if k not in ('months','contributions','balance_curve','skips')}),flush=True)
    save(ROOT/'Results.json',result)
    protocols=[('Joint 4-week blocks',4,False,False,False,20261008),('Joint 8-week blocks',8,False,False,False,20261009),
               ('Execution/carry stress',4,True,False,False,20261008),('Recent 13-week pool',2,False,True,False,20261010),
               ('3-second cooldown, no retries',4,False,False,True,20261008)]
    for label,weeks,stress,recent,cooldown,seed in protocols:
        horizon=730;draws,shifted=joint_samples(configs,weeks,a.paths,seed,horizon,recent)
        save(ROOT/('DRAWS-'+str(seed)+'-'+str(weeks)+'.json'),dict(seed=seed,block_weeks=weeks,horizon_days=horizon,draws=draws))
        ns=s.engine(cooldown=cooldown)
        for c in configs:
            runs=[]
            for i,draw in enumerate(draws):
                runs.append(ns['replay'](shifted(c['name'],draw),[],SYN,SYN+horizon*DAY,stress=stress))
                if (i+1)%500==0:print(label+' '+c['name']+' '+str(i+1)+'/'+str(a.paths),flush=True)
            summaries=[s.horizon_summary(runs,SYN,h) for h in (90,180,365,730)]
            # Add phase-specific successful-only durations; do not invent a pass for unfinished paths.
            for h in summaries:
                cut=SYN+h['days']*DAY
                p1=[r for r in runs if r['passes'] and before(r['passes'][0]['time'],cut)]
                h['days_to_phase1']=s.dist([(stamp(r['passes'][0]['time'])-SYN)/DAY for r in p1])
            result['random_cases'].append(dict(protocol=label,block_weeks=weeks,stress=stress,recent_only=recent,cooldown=cooldown,
                seed=seed,portfolio=c['name'],ea_count=c['ea_count'],summary=summaries))
            tag=str(seed)+'-'+str(weeks)+'-'+c['name']+('-stress' if stress else '-cooldown' if cooldown else '')
            save(ROOT/('PATHS-'+tag+'.json'),[full_path(r) for r in runs]);save(ROOT/'Results.json',result)
            print('SUMMARY '+label+' '+c['name']+' '+json.dumps([dict(days=h['days'],p1=h['phase1_pass_pct'],both=h['both_pass_pct'],
                    payout=h['first_reward_received_pct'],mean_pass_days=h['days_to_pass_both']['mean'],expected_reward=h['expected_first_reward_usd']) for h in summaries]),flush=True)
    assert all(sha(p)==v for p,v in fingerprints.items())
    result['verification']=dict(source_hashes_unchanged=True,paths=a.paths*len(configs)*len(protocols),no_live_changes=True,
                                 historical_cash_reconciled=True,only_orb_entries_in_research_profile=True)
    save(ROOT/'Results.json',result);print('PURE ORB PORTFOLIO COMPLETE',flush=True)

if __name__=='__main__':main()
