"""Fixed12-roster historical diagnostic screen. No native or trading/API actions."""
from pathlib import Path
from bisect import bisect_left
from datetime import datetime,timezone
import hashlib,importlib.util,json,time
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_core_phase_math',R/'core_engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):e.save(p,v)
def select(summary,plan):
    rows=[]
    for basket,members in plan['baskets'].items():
        found=[x for x in summary if x['portfolio']==basket]
        assert len(found)==4
        eligible=all(x['all_starts']['both_completed']>=101 and x['jan2026_plus']['both_completed']>=54 for x in found)
        rows.append(dict(portfolio=basket,ea_count=len(members),eligible=eligible,
            main_min_completions=min(x['all_starts']['both_completed'] for x in found),
            jan_min_completions=min(x['jan2026_plus']['both_completed'] for x in found),
            worst_all_start_t50=max(x['all_starts']['overall_time_to50pct_prague_days'] or 10**9 for x in found),
            worst_conditional_total_median=max(x['all_starts']['total_median_prague_days_among_completed'] or 10**9 for x in found)))
    rows.sort(key=lambda x:(not x['eligible'],x['worst_all_start_t50'],x['worst_conditional_total_median'],x['ea_count'],x['portfolio']))
    return dict(criterion=plan['selection'],rows=rows,best_eligible=next((x['portfolio'] for x in rows if x['eligible']),None))
def main():
    e.verify_freeze();plan=read(R/'PLAN.json');data=read(R/'INPUTS.json');began=time.time()
    old=Path(plan['comparison']['previous_study']);assert sha(R/'core_engine.py')==sha(old/'run.py')
    prior={ (t['portfolio'],t['start_date'],t['cost'],t['handover']):t for t in read(old/'OUTCOMES.json')['trials']}
    core=set(plan['baskets']['CORE4']);streams={}
    for basket,members in plan['baskets'].items():
        universe=core|set(members)
        events=e.master_events(plan,dict(data,candidates=[x for x in data['candidates'] if x['ea'] in universe]))
        streams[basket]=(events,[x[0] for x in events])
    trials=[];parity_checks=0
    for index,start in enumerate(data['starts']):
        for basket in plan['baskets']:
            events,epochs=streams[basket]
            window=events[bisect_left(epochs,start['epoch']):bisect_left(epochs,start['horizon_epoch'])]
            for scenario in plan['scenarios']:
                row=e.replay(plan,basket,start,scenario['cost'],scenario['handover'],window)
                if basket in ('CORE3','CORE4'):
                    before=prior[(basket,start['date'],scenario['cost'],scenario['handover'])]
                    assert row==before,('Baseline replay differs',basket,start['date'],scenario)
                    parity_checks+=1
                trials.append(row)
        if index%10==0:print('Paired start',index+1,'of',len(data['starts']),flush=True)
    summary=[]
    for basket in plan['baskets']:
        for scenario in plan['scenarios']:
            subset=[x for x in trials if x['portfolio']==basket and x['cost']==scenario['cost'] and x['handover']==scenario['handover']]
            summary.append(dict(portfolio=basket,**scenario,all_starts=e.aggregate(subset),jan2026_plus=e.aggregate([x for x in subset if x['start_date']>='2026-01-01'])))
    selected=select(summary,plan)
    save(R/'OUTCOMES.json',dict(trials=trials,summary=summary,elapsed_seconds=time.time()-began,model='Exploratory historical sampled-equity immutable-signal screen; not native simultaneous FTMO execution or forward probabilities.',plan_sha256=sha(R/'PLAN.json'),inputs_sha256=sha(R/'INPUTS.json'),engine_sha256=sha(R/'core_engine.py'),orchestrator_sha256=sha(Path(__file__)),frozen_sha256=sha(R/'FROZEN.json')))
    save(R/'BASELINE-PARITY.json',dict(status='PASS',full_trial_records_identical=parity_checks,expected=1072,previous_outcomes_sha256=sha(old/'OUTCOMES.json'),math_engine_byte_identical=True))
    save(R/'SUMMARY.json',dict(meta=dict(title='FTMO faster portfolio: fixed12-basket historical screen',history=plan['history'],risk=plan['risk'],model='Estimated sampled-equity immutable-signal replay; exploratory retrospective selection, not genuineFTMO execution or calibrated forward odds.',live_changes=False,optimization='Fixed12-roster menu only; no parameter search or post-result roster expansion.',jan2026_plus_eligible_starts=71),selection=selected,results=summary,scenarios=plan['scenarios'],baskets=plan['baskets'],rules=plan['guard'],phases=plan['phases'],float_model=plan['float_model'],costs=plan['costs'],source_coverage=read(R/'SOURCE-COVERAGE.json')['coverage'],outcomes_path=str(R/'OUTCOMES.json'),outcomes_sha256=sha(R/'OUTCOMES.json'),plan_sha256=sha(R/'PLAN.json'),engine_sha256=sha(R/'core_engine.py'),orchestrator_sha256=sha(Path(__file__)),frozen_sha256=sha(R/'FROZEN.json'),limitations=['Retrospectively selected fixed screen; >=75%historical threshold is not a75%future pass probability.','Starts overlap and are dependent; all180-day incomplete-followup starts excluded.','Source15%real ticks globally, part of matchingyeargenerated; Jan71sensitivity required separately.','Owned5-minute floating marks only, zero until first mark and unlimited past-mark carry with staleness receipts; no full tick equity.','Historical source fills/exits immutable; skipped original signals and currentSL/cooldown/extra negativeopen-swap reserve not completely reconstructed.','ArchivedExnessspecs/quotes/fees are proxies, not actualFTMOexecution or certified currentminlots.','No3WayGold/full17 reference: partial/overlap ownership unsupported; optional16reference omitted before outcomes.','No production/live account changes.']))
    print(json.dumps(dict(status='COMPLETE',trials=len(trials),baseline_parity=parity_checks,seconds=time.time()-began,selection=selected,summary_sha256=sha(R/'SUMMARY.json')),indent=2),flush=True)
if __name__=='__main__':main()

