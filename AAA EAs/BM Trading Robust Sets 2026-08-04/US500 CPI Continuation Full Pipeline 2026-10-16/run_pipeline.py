"""Raw parity -> small development search -> validation -> freeze -> evaluation."""
from datetime import datetime,timezone
from pathlib import Path
import itertools,json,statistics
import prepare,runner as r
from search_plan import BASE,PLAN,STAGES,key,rank,score,neighbours,complexity
R=r.R;C=r.CONFIG

def trials_add(rows):
    old=r.load(R/'trials.json') if (R/'trials.json').exists() else []
    seen={(x['stage'],x['index']) for x in old}
    old.extend(x for x in rows if (x['stage'],x['index']) not in seen)
    r.save(R/'trials.json',old)

def main():
    prepare.main();lock=r.lease()
    try:
        # Reproduction only, never a candidate-selection stage. The baseline's
        # raw full-history result was already inspected before this request.
        p=r.native('parity',[BASE],C['start'],C['end_exclusive'])[0]
        original=r.load(R.parent/'US500 CPI Continuation vs Reversion Raw 2026-10-16/RESULTS.json')[3]
        fields=['open_epoch','close_epoch','side','volume','open_price','close_price','net_profit','initial_sl','initial_tp']
        assert [[t[k] for k in fields] for t in p['trades']]==[[t[k] for k in fields] for t in original['trades']],'Baseline parity failure; search prohibited'
        r.save(R/'PARITY.json',dict(passed=True,trades=len(p['trades']),net=p['metrics']['net'],fields=fields,source_sha256=r.sha(R.parent/'US500 CPI Continuation vs Reversion Raw 2026-10-16/RESULTS.json')))
        raw=r.native('raw-3y',[BASE],C['raw_gate']['three_year_start'],C['raw_gate']['end_exclusive'])[0]
        checks=dict(minimum_30_trades=raw['metrics']['trades']>=30,pf_at_least_1_15=(raw['metrics']['pf'] or 0)>=1.15,positive_net=raw['metrics']['net']>0)
        r.save(R/'RAW-GATES.json',dict(three_year_checks=checks,three_year_metrics=raw['metrics'],three_year_dates=[raw['start'],raw['end']],
                   five_year_unavailable=True,five_year_required_dates=['2018-10-16','2023-10-16'],
                   five_year_reason=C['raw_gate']['five_year_status'],passed=False,exploratory_authorized=True))
        dev_cache={}
        for row in r.load(R/'trials.json') if (R/'trials.json').exists() else []:
            if row['start']==C['start'] and row['end']==C['development_end_exclusive']:
                dev_cache[key(row['parameters'])]=row
        def dev(label,cases):
            unique=list({key(x):x for x in cases}.values())
            missing=[x for x in unique if key(x) not in dev_cache]
            if missing:
                rows=r.native(label,missing,C['start'],C['development_end_exclusive']);trials_add(rows)
                dev_cache.update({key(x['parameters']):x for x in rows})
            return [dev_cache[key(x)] for x in unique]
        baseline=dev('dev-baseline',[BASE])[0];centre=BASE;stage_log=[]
        for label,name,values in STAGES:
            cases=[dict(centre,**{name:value}) for value in values]
            rows=dev('dev-'+label,cases);winner=rank(rows)[0]
            centre=winner['parameters'];stage_log.append(dict(stage=label,selected=centre,ranked=[dict(parameters=x['parameters'],score=score(x),metrics=x['metrics']) for x in rank(rows)]))
            r.save(R/'DEVELOPMENT-STAGES.json',stage_log)
        centres=list({key(x):x for x in [BASE,centre]}.values())
        plateau=[]
        for i,case in enumerate(centres):
            family=dev(f'dev-neighbours-{i}',neighbours(case))
            values=[score(x) for x in family]
            plateau.append(dict(parameters=case,median_score=statistics.median(values),positive_neighbours=sum(x['metrics']['net']>0 for x in family),
                        total_neighbours=len(family),centre_metrics=dev_cache[key(case)]['metrics'],
                        family=[dict(parameters=x['parameters'],metrics=x['metrics'],score=score(x)) for x in family]))
        assert len(dev_cache)<=PLAN['max_main_unique_configurations']
        r.save(R/'DEVELOPMENT-PLATEAU.json',plateau)
        # Independent predetermined compact walk-forward grid. Do not use
        # these test outcomes to tune the final development candidate.
        wf=[];grid=[dict(BASE,target_r=tp,hold_minutes=hold) for tp in PLAN['walk_forward']['grid_target_r'] for hold in PLAN['walk_forward']['grid_hold_minutes']]
        for i,fold in enumerate(PLAN['walk_forward']['folds']):
            training=r.native(f'wf-train-{i}',grid,fold['train_start'],fold['train_end']);trials_add(training)
            chosen=rank(training)[0]['parameters']
            tested=r.native(f'wf-test-{i}',[BASE,chosen],fold['test_start'],fold['test_end'])
            wf.append(dict(**fold,selected=chosen,baseline_metrics=tested[0]['metrics'],selected_metrics=tested[1]['metrics'],train_unique_config_count=len(grid),
                           baseline_stage=tested[0]['stage'],selected_stage=tested[1]['stage']))
            r.save(R/'WALK-FORWARD.json',dict(folds=wf,selection_used_for_final=False,scope='Retrospective anchored selection; each fold chooses only from its earlier training data'))
        r.save(R/'DEVELOPMENT-FINALISTS.json',dict(centres=plateau,finalists=centres,selected_without_oos=True))
        validation=r.native('validation',centres,C['development_end_exclusive'],C['validation_end_exclusive'])
        ranked=[]
        for row in validation:
            item=next(p for p in plateau if p['parameters']==row['parameters'])
            okay=row['metrics']['trades']>=6 and row['metrics']['net']>0 and (row['metrics']['pf'] or 0)>1 and item['positive_neighbours']>item['total_neighbours']/2 and item['centre_metrics']['net']>0
            ranked.append(dict(parameters=row['parameters'],validation_metrics=row['metrics'],development_plateau=item,
                               research_selection_checks_passed=okay,selection_score=(item['median_score']+score(row,10))/2))
        eligible=[x for x in ranked if x['research_selection_checks_passed']]
        if eligible:
            selected=sorted(eligible,key=lambda x:(-x['selection_score'],complexity(x['parameters']),key(x['parameters'])))[0]['parameters']
            reason='Predeclared development plateau + validation score among the at-most-two research finalists; not promotion approval'
        else:
            selected=sorted(plateau,key=lambda x:(-x['median_score'],complexity(x['parameters']),key(x['parameters'])))[0]['parameters']
            reason='No finalist passed research validation. Best development plateau frozen ONLY to demonstrate failed-validation exploratory performance; no OOS reselection'
        selection=dict(selected=selected,baseline=BASE,centres=plateau,validation_ranked=ranked,selected_reason=reason,
                       validation_research_gate_passed=bool(eligible),research_only=True,live_changes=False)
        r.save(R/'SELECTION.json',selection)
        hashed={name:r.sha(R/name) for name in ['engine.mq5','build_engine.py','config.json','calendar.json','DATA-SPLIT.json','SEARCH-PLAN.json','SELECTION.json','trials.json']}
        frozen=dict(locked=dict(files=hashed,selected=selected,baseline=BASE),frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                    retrospective_oos=True,research_only=True,live_changes=False)
        fp=R/'FROZEN.json'
        if fp.exists(): assert r.load(fp)['locked']==frozen['locked']
        else:r.save(fp,frozen)
        # NO selection, scoring or new parameters below this persisted lock.
        r.native('holdout',[BASE,selected],C['oos_start'],C['end_exclusive'])
        r.native('full',[BASE,selected],C['start'],C['end_exclusive'])
        for delay in [500,1000]:r.native('delay-'+str(delay),[selected],C['oos_start'],C['end_exclusive'],delay=delay)
        r.native('generated-diagnostic',[selected],C['oos_start'],C['end_exclusive'],model=0)
        r.status('NATIVE PIPELINE COMPLETE — audit/report next',research_only=True,live_changes=False)
    finally: lock.close()

if __name__=='__main__':main()
