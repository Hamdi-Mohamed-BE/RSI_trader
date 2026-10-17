"""Prepare fixed historical inputs and protocol; computes no portfolio outcomes."""
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from bisect import bisect_left
from collections import defaultdict
import csv, hashlib, json, math
R=Path(__file__).resolve().parent;B=R.parent;Z=ZoneInfo('Europe/Prague')
LONG=B/'Portfolio Long History All ORB05 2026-10-14'
OLD=B/'FTMO Core3 vs Core4 Phase Timing 2026-10-16'
CORE=['nasdaq-5m-candle-momentum','usdjpy-london-open-momentum','us100-month-end-flow','xau-rsi-vwap']
GOLDVA='gold-overnight-value-area';EMA3='ema3';TREND='xau-trend-progression';H1='us100-h1-orb-13utc'
ORBS=[H1,'us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30']
SLUGS=CORE+[GOLDVA,EMA3,TREND]+ORBS
BASKETS={
 'CORE4':CORE,'CORE3':CORE[:3],
 'CORE4_MINUS_NASDAQ':[x for x in CORE if x!=CORE[0]],
 'CORE4_MINUS_USDJPY':[x for x in CORE if x!=CORE[1]],
 'CORE4_MINUS_MONTH_END':[x for x in CORE if x!=CORE[2]],
 'CORE4_PLUS_GOLD_VA':CORE+[GOLDVA],
 'CORE4_PLUS_EMA3':CORE+[EMA3],
 'CORE4_PLUS_TREND_06R':CORE+[TREND],
 'CORE4_PLUS_H1_ORB_05R':CORE+[H1],
 'CORE4_PLUS_FIVE_ORBS_05R':CORE+ORBS,
 'CORE4_PLUS_GOLD_VA_H1_ORB':CORE+[GOLDVA,H1],
 'CORE4_MINUS_NASDAQ_PLUS_GOLD_VA':[x for x in CORE if x!=CORE[0]]+[GOLDVA],
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def midnight(d):return datetime.combine(d,datetime.min.time(),tzinfo=Z).timestamp()
def prepare():
    assert not (R/'OUTCOMES.json').exists(),'Never prepare after portfolio outcomes'
    start_day,end_day=date(2025,10,6),date(2026,10,6);begin,end=midnight(start_day),midnight(end_day)
    p=read(LONG/'PLAN.json');state=read(LONG/'RUN_STATUS.json');package=B/'_00 Live profiles/Packages/FTMO/PACKAGE.json'
    current=read(package);native_guard=B/'_00 Live profiles/Packages/FTMO/package/CalyxFTMOGuard.mqh'
    sources={str(x):sha(x) for x in (LONG/'PLAN.json',LONG/'RUN_STATUS.json',LONG/'RISK_ROWS.json',package,native_guard)}
    reference=read(LONG/'RISK_ROWS.json')['ftmo'];lookup={(x['key'],x['position_id']):x for x in reference}
    for file in (OLD/'PLAN.json',OLD/'INPUTS.json',OLD/'SOURCE-COVERAGE.json',OLD/'FROZEN.json',OLD/'run.py',OLD/'SUMMARY.json',OLD/'OUTCOMES.json'):
        sources[str(file)]=sha(file)
    assert sha(R/'core_engine.py')==sha(OLD/'run.py'),'Core mathematics must stay byte-identical'
    coverage=[];prepared=[]
    for slug in SLUGS:
        cid=p['mappings']['ftmo'][slug];row=next(x for x in p['cases'] if x['case_id']==cid);receipt=state['complete'][cid]
        for file,digest in row['production_hashes'].items():
            assert sha(file)==digest,('Production source changed',file)
            sources[file]=digest
        path=Path(receipt['path']);assert sha(path)==receipt['sha256'];case=read(path)
        folder=path.parent;ds=list(csv.DictReader((folder/'deals.csv').open(encoding='utf-8-sig')))
        for file in (path,folder/'deals.csv',folder/'equity.csv',folder/'manifest.json'):
            sources[str(file)]=sha(file)
        source_trades=sorted(case['trades'],key=lambda t:(t['open_epoch'],t['position_id']))
        assert all(not t['partial'] for t in source_trades),'Partial timing requires a separate model'
        assert all(a['close_epoch']<=b['open_epoch'] for a,b in zip(source_trades,source_trades[1:])),'Floating ownership must be unique'
        opens=[t['open_epoch'] for t in source_trades];by_pid=defaultdict(list)
        for d in ds:by_pid[int(d['position_id'])].append(d)
        owner_marks=defaultdict(list);boundaries={int(t[k]) for t in source_trades for k in ('open_epoch','close_epoch')}
        previous_epoch=None;dropped_duplicate=boundary_marks=flat_marks=0;first_mark=last_mark=None;global_first=global_last=None
        with (folder/'equity.csv').open(encoding='utf-8-sig') as stream:
            for mark in csv.DictReader(stream):
                epoch=int(mark['epoch'])
                global_first=epoch if global_first is None else global_first;global_last=epoch
                if epoch<begin-900 or epoch>=end:continue
                assert previous_epoch is None or epoch>=previous_epoch,'Unordered native equity'
                if epoch==previous_epoch:dropped_duplicate+=1;continue # preserve first observation; never post-finalization overwrite
                previous_epoch=epoch;first_mark=epoch if first_mark is None else first_mark;last_mark=epoch
                balance,equity=float(mark['balance']),float(mark['equity']);assert math.isfinite(balance) and math.isfinite(equity)
                if epoch in boundaries:boundary_marks+=1;continue # original Observe precedes source OnTick
                i=bisect_left(opens,epoch)-1
                if i>=0 and source_trades[i]['open_epoch']<epoch<source_trades[i]['close_epoch']:
                    t=source_trades[i];volume=float(t['volume']);assert volume>0
                    owner_marks[t['position_id']].append([epoch,(equity-balance)/volume,volume,balance,equity])
                else:
                    assert abs(equity-balance)<.021,('Unowned nonzero floating mark',slug,epoch,equity-balance)
                    flat_marks+=1
        assert first_mark is not None and global_first<=begin and global_last>=end,('Incomplete native curve coverage',slug,global_first,global_last)
        candidates=[];lags=[];without_marks=0;restored=0
        contract={'USTEC':1.,'XAUUSD':100.,'USDJPY':100000.}[row['symbol']]
        for t in source_trades:
            if not begin<=t['open_epoch']<end:continue
            boundary=any('end of test' in x.lower() for x in t['exit_comments']);old=lookup.get((slug,t['position_id']))
            if old is None:assert boundary,('Unmapped ordinary trade',slug,t['position_id']);restored+=1
            unit_risk=old['unit_risk'] if old else abs(t['open_price']-t['sl'])*contract/(t['sl'] if row['symbol']=='USDJPY' else 1.)
            parts=by_pid[t['position_id']];opened=[d for d in parts if int(d['entry'])==0];assert len(opened)==1
            entry_unit=sum(float(opened[0][k]) for k in ('gross','commission','swap','fee'))/t['volume']
            owned=owner_marks[t['position_id']]
            if owned:lags.append(owned[0][0]-t['open_epoch'])
            else:without_marks+=1
            candidates.append(dict(id=slug+'|'+str(t['position_id']),ea=slug,symbol=row['symbol'],position_id=t['position_id'],op=t['open_epoch'],cl=None if boundary else t['close_epoch'],source_forced_close_epoch=t['close_epoch'] if boundary else None,end_censored=boundary,side=t['side'],open_price=t['open_price'],close_price=t['close_price'],sl=t['sl'],tp=t['tp'],unit_risk=unit_risk,source_volume=t['volume'],entry_unit_cost=entry_unit,unit_gross=t['gross']/t['volume'],unit_commission=(t['commission']+t['fee'])/t['volume'],unit_swap=t['swap']/t['volume'],marks=owned))
        prepared.extend(candidates)
        coverage.append(dict(ea=slug,case_id=cid,source_result=str(path),history_quality=case['native']['history_quality'],tick_notes=case['tick_notes'],candidates=len(candidates),restored_end_censored_positions=restored,first_mark=first_mark,last_mark=last_mark,global_first_mark=global_first,global_last_mark=global_last,owned_marks=sum(len(t['marks']) for t in candidates),discarded_boundary_marks=boundary_marks,discarded_duplicate_marks=dropped_duplicate,flat_marks=flat_marks,entry_initial_zero_segments=len(candidates),positions_without_owned_interior_mark=without_marks,max_initial_mark_lag_seconds=max(lags) if lags else None,source_parameters=row['input_settings']))
    starts=[];excluded=[];d=start_day
    while d<end_day:
        if d.weekday()<5:
            item=dict(date=d.isoformat(),epoch=midnight(d),horizon_date=(d+timedelta(days=180)).isoformat(),horizon_epoch=midnight(d+timedelta(days=180)))
            (starts if d+timedelta(days=180)<=end_day else excluded).append(item)
        d+=timedelta(days=1)
    assert len(starts)==134 and len(excluded)==127
    plan=dict(status='PROPOSED: no portfolio outcomes computed',created_utc=datetime.now(timezone.utc).isoformat(),baskets=BASKETS,history=dict(start_prague=str(start_day),end_exclusive_prague=str(end_day),start_utc=datetime.fromtimestamp(begin,timezone.utc).isoformat(),end_exclusive_utc=datetime.fromtimestamp(end,timezone.utc).isoformat(),all_eligible_weekday_starts=134,excluded_incomplete_followup_starts=127,first_start=starts[0]['date'],last_start=starts[-1]['date'],total_horizon_prague_civil_days=180,holidays_not_removed=True),scenarios=[dict(cost=c,handover=w) for c in ('recorded_exness','fixed_cost_stress') for w in ('next_prague_midnight','two_business_day_wait')],risk=dict(initial_balance=10000,currency='USD',fixed_guard_allocation=50,source_requested_risk_percent=.5,lot_sizing='Source request=ceil(0.5% sampled equity/unit-risk) to broker step with original min/max; guard floors min(source-request volume,50/unit-risk,volumeMax); reject below broker min.',specs={'USTEC':dict(contract=1,leverage=15,minimum=.05,step=.01,maximum=500),'USDJPY':dict(contract=100000,leverage=30,minimum=.01,step=.01,maximum=200),'XAUUSD':dict(contract=100,leverage=15,minimum=.01,step=.01,maximum=200)}),guard=dict(daily_prague_anchor='day-start cash balance',persistent_daily_entry_stop_loss=300,permanent_static_equity_floor=9000,permanent_daily_equity_loss=500,admission_equity_buffer=9200,aggregate_initial_risk_cap=225,same_symbol_initial_risk_cap=150,daily_entry_cap=7,daily_completed_losses_cap=3,entry_cooldown_seconds=3,reserve='1.25*retained filled initial risk +5 per open position; extra negative open-swap reserve unavailable and omitted (held swap already present in sampled floating).',projected='min(sampled equity,balance-existingReserve)-1.25*candidateRisk-5',margin='Gross per-symbol entry notional/leverage proxy; existing+proposed margin<=0.8*projected and proposed<=sampled free margin proxy. No hedging discount.',failure='Hard observed sampled equity breach stops phase permanently; no liquidation. Existing positions retain source exits after guard soft-stop. Soft daily/buffer admission rejection is NOT failure.',target='Phase1 balance>=11000;Phase2>=10500;>=4 distinct Prague entry-fill days per phase; no active positions; never native end-of-test liquidation.'),float_model=dict(source='Single-EA native5-minute equity-minus-balance divided by uniquely owned native open volume.',ownership='Strict source.open_epoch < mark_epoch < source.close_epoch; discard all source opening/closing epoch marks, duplicates and finalization marks; fail on nonzero unowned interior marks or nonfinite fields.',event_mark='Latest mark at or before replay event belonging to SAME source position only. Initial floating=0 until first eligible mark; no future interpolation or backfill. Mark remains until later owned mark or source exit; stale age and zero-initial durations logged.',swap='Native owned floating contains accrued source swap. Final swap booked at strategy close then position floating removed; no future final swap used for entry reserve.',unknowns='No complete tick path, true broker margin, currentSL/request-cooldown execution, counterfactual entries after skipped source trades, or quote-level pre-request geometry.'),costs=dict(base='Actual raw entry costs at entry; recorded remaining commission/fee, gross and swap at original strategy close, scaled by replay lots. No future exit fee is split into entry.',stress='Additional per-side execution cost:USTEC1price point,USDJPY0.01JPY,XAUUSD0.10USD, converted at side entry/exit quote; double negative recorded swap at exit, positive swap unchanged. Source exits unchanged; extra swap accrual between snapshots is not reconstructed.'),ordering='At same timestamp: Prague midnight reset, source closes, mark updates, phase-target evaluation, scheduled phase2 activation, candidates in N5→USDJPY→MonthEnd→RSI order;3s entry cooldown applies. No use of a later mark.',phases=dict(primary_handover='Next Prague civil-date midnight after Phase1 pass.',two_business_day_wait='Advance two weekdays after Phase1 local pass date; activate at midnight of that date; rerun subsequent path, not add waiting to prior result.',phase2='Fresh10000 balance and all phase/day/account state, no position carry-over; same overall180-day deadline.',phase2_started='Account activation before exclusive horizon, even with no trades; first fill separate.',qualification='Both trading phases naturally flat-pass within horizon; optional access date=Phase2pass+5weekdays is arithmetic only, excluded from qualification.',statistics='Phase1 median among Phase1passes; Phase2 median among Phase2passes after actual activation; total median among both-phase completions. No overall50% time if fewer than half all starts complete. No independent binomial CI: overlapping cohorts are dependent.',elapsed='Inclusive Prague civil dates plus fractional elapsed24h and distinct entry days separately.',outcomes='failed_phase1,failed_phase2,pending_phase1,pending_phase2,phase2_not_started_wait,horizon_completed_both; soft-buffer-blocked tagged separately, not hard-failed.'),sensitivity='Additionally show Jan1,2026-and-later eligible-start subgroup from SAME paired trials; not a newly selected winner.',live_changes=False,optimization=False,native_simultaneous=False,probability_label='Historical estimated replay completion fractions, NOT calibrated future FTMO pass probabilities.',source_hashes=sources)
    plan['ordering']='Prague midnight reset; source exits before unrelated entries; owned mark updates; natural-flat target checks; scheduled phase2 activation; candidate ties use current FTMO manifest relative order (RSI,USDJPY,MonthEnd,Nasdaq). An own same-second opening precedes its exit. Three-second entry wait is a market-time proxy for live wall-clock reconciliation.'
    plan['candidate_priority']=[e['slug'] for e in current['entries'] if e['slug'] in SLUGS]
    plan['float_model']['staleness']='Latest-owned-past-mark carried without time limit, including closed-market weekends; all mark ages and counts over900seconds reported. No future backfill or cross-position mark reuse; zero before first owned mark explicitly flagged.'
    previous=read(OLD/'INPUTS.json');oldplan=read(OLD/'PLAN.json')
    assert starts==previous['starts'] and excluded==previous['excluded_starts']
    for slug in CORE:
        assert [x for x in prepared if x['ea']==slug]==[x for x in previous['candidates'] if x['ea']==slug],('Baseline source changed',slug)
    for key in ('history','scenarios','risk','guard','float_model','costs','phases'):
        assert plan[key]==oldplan[key],('Protocol change',key)
    plan['status']='PREDECLARED research-only12basket screen; no replay outcomes computed.'
    plan['baseline_baskets']=['CORE4','CORE3']
    plan['event_sources']='For each basket use baselineCore4 plus added member sources; removed baseline members retain only the original observation clock. Inactive source opens call unchanged observer but cannot open positions. This exactly preserves priorCore3/Core4 controls; no financial-state interpolation.'
    plan['selection']=dict(
        historical_only=True,retrospective_selection=True,no_forward_probability_claim=True,
        total_unique_baskets=12,no_post_result_expansion=True,
        eligibility='In EVERY four predefined cost/handover scenarios require both completed>=101/134 AND Jan2026-plus completed>=54/71.',
        main_minimum_completed=101,main_starts=134,jan_minimum_completed=54,jan_starts=71,
        rank_order=['worst_across_four_all_start_time_to_50pct_ascending','worst_across_four_conditional_total_median_ascending','fewer_eas','stable_basket_id_ascending'],
        no_eligible_result='Report no configuration meets all frozen criteria; do not relax thresholds or add combinations.',
        tied_ablation='CORE3 is also Core4 minusRSI; this duplicate is not rerun as a separate candidate.',
        excluded_optional_reference='CurrentFTMO16 reference prospectively omitted byroot; full17 unsupported due3WayGold partial/overlapping lifecycles. No performance-based exclusion.',
        roster_authority='Root approved exact12basket menu before outcomes; risk,DI,exits,guard,horizon not optimized.')
    plan['sizing_model']='All12sourceEAs verified full equity-percent request with upward lot normalization. GoldVA riskmode0; Selective fixedmoney0; EMA3 grid input inactive. Guard still floors cap50; archived filled-stop-risk geometry proxy retained.'
    plan['comparison']=dict(previous_study=str(OLD),previous_summary_sha256=sha(OLD/'SUMMARY.json'),previous_outcomes_sha256=sha(OLD/'OUTCOMES.json'),baseline_parity_required=True,math_engine_sha256=sha(R/'core_engine.py'))
    save(R/'SOURCE-COVERAGE.json',dict(coverage=coverage,source_hashes=sources))
    save(R/'INPUTS.json',dict(candidates=prepared,starts=starts,excluded_starts=excluded,year_begin_epoch=begin,year_end_exclusive_epoch=end))
    save(R/'PLAN.json',plan)
    print(json.dumps(dict(coverage=[{k:v for k,v in x.items() if k not in ('source_parameters','tick_notes')} for x in coverage],starts=len(starts),excluded=len(excluded),plan_sha256=sha(R/'PLAN.json'),inputs_sha256=sha(R/'INPUTS.json')),indent=2))
if __name__=='__main__':prepare()
