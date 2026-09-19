from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timedelta
import importlib.util
import json
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('calyx_shared_audit',ROOT.parent.parent/'Calyx Research Pipeline'/'calyx_pipeline.py')
calyx=importlib.util.module_from_spec(spec);sys.modules[spec.name]=calyx;spec.loader.exec_module(calyx)

def readrun(tag):return json.loads((ROOT/'Runs'/f'{tag}.json').read_text())
def trades(tag):return json.loads((ROOT/'Audit'/f'{tag}-trades.json').read_text())
def save(path,data):path.write_text(json.dumps(calyx.json_safe(data),indent=2),encoding='utf-8')

def cost_sensitivity(tag):
    ts=trades(tag);r=readrun(tag);adjusted=[]
    for t in ts:
        extra_spread=t['entry_spread_cost'];extra_commission=.5*max(0,-t['commission']);extra_swap=max(0,-t['swap'])
        adjusted.append({**t,'extra_spread':extra_spread,'extra_commission':extra_commission,'extra_swap':extra_swap,
                         'stressed_net':t['net_profit']-extra_spread-extra_commission-extra_swap})
    pnls=[t['stressed_net'] for t in adjusted]
    eq=peak=10000.;dd=0
    for p in pnls:eq+=p;peak=max(peak,eq);dd=max(dd,100*(peak-eq)/peak)
    return {'tag':tag,'trades':len(ts),'base_net':r['net_profit'],'net':sum(pnls),'return_pct':sum(pnls)/100,
            'pf':calyx.profit_factor(pnls),'win_rate':100*sum(p>0 for p in pnls)/len(pnls) if pnls else 0,
            'closed_dd_pct':dd,'extra_spread_total':sum(t['extra_spread'] for t in adjusted),
            'extra_commission_total':sum(t['extra_commission'] for t in adjusted),
            'extra_swap_total':sum(t['extra_swap'] for t in adjusted),
            'scope':'Fixed realized trades/lots; add one observed entry spread, 50% recorded commission and another negative recorded swap. Not a new native fill simulation.',
            'trades_detail':adjusted}

def month_year(ts):
    months=defaultdict(list);years=defaultdict(list)
    for t in ts:months[t['close_time'][:7]].append(t);years[t['close_time'][:4]].append(t)
    def summarize(k,v):
        p=[t['net_profit'] for t in v]
        return {'period':k,'trades':len(v),'net':sum(p),'commission':sum(t['commission'] for t in v),'swap':sum(t['swap'] for t in v),
                'win_rate':100*sum(x>0 for x in p)/len(p),'pf':calyx.profit_factor(p)}
    return {'months':[summarize(k,v) for k,v in sorted(months.items())],'years':[summarize(k,v) for k,v in sorted(years.items())]}

def full_window_bootstrap(tag,stressed=False):
    r=readrun(tag);ts=trades(tag)
    if stressed:ts=cost_sensitivity(tag)['trades_detail']
    grouped=defaultdict(float)
    for t in ts:grouped[datetime.fromisoformat(t['close_time']).date()]+=t['stressed_net' if stressed else 'net_profit']
    first=datetime.strptime(r['window'][0],'%Y.%m.%d').date();end=datetime.strptime(r['window'][1],'%Y.%m.%d').date()
    days=[];ret=[];equity=10000.
    cursor=first
    while cursor<end:
        # Include flat calendar days, so inactive initial/final weeks are retained.
        value=grouped.get(cursor,0.);ret.append(value/equity if equity>0 else -1);equity+=value;days.append(cursor);cursor+=timedelta(days=1)
    pnls=[t['stressed_net' if stressed else 'net_profit'] for t in ts]
    boot=calyx.bootstrap(pnls,ret,paths=10000,block=5,daily_loss_limit_pct=5,total_loss_limit_pct=10,seed=20260913)
    return {'tag':tag,'stressed':stressed,'calendar_days':len(days),'window':r['window'],
            'scope':'Conditional five-calendar-day circular blocks; PF uses separate five-trade blocks. Closed P&L only; not a live pass or profit probability.',**boot}

def main():
    final=json.loads((ROOT/'final-runs.json').read_text());freeze=json.loads((ROOT/'frozen-selection.json').read_text())
    folds=json.loads((ROOT/'walk-forward.json').read_text())['folds']
    assert len(folds)==3,'All three native walk-forward folds must finish before the final audit'
    assert len(final['neighbours'])==8,'All eight frozen neighbours must finish'
    allruns=[json.loads(p.read_text()) for p in (ROOT/'Runs').glob('*.json')]
    identities={(r['config_id'],r['delay_ms']) for r in allruns}
    trial_count=len(identities);out=ROOT/'Enhanced Audit';out.mkdir(exist_ok=True)
    enhanced={};stresses={};boots={}
    for key in ('1y','5y'):
        tag=final[key];ts=trades(tag)
        average_spread=statistics.fmean(t['entry_spread_cost'] for t in ts) if ts else 0
        payload=calyx.audit_report(ROOT/'Backtest Reports'/f'{tag}.htm',label=f'XAU D14 selected {key}',paths=10000,block=5,
              tested_configurations=trial_count,daily_loss_limit_pct=5,total_loss_limit_pct=10,extra_cost_per_trade=average_spread,seed=20260913)
        assert payload['metrics']['trades']==len(ts),'Independent report parser trade count mismatch'
        assert abs(payload['metrics']['net_profit']-sum(t['net_profit'] for t in ts))<.051,'Independent report parser net mismatch'
        save(out/f'{key}-common-audit.json',payload);(out/f'{key}-common-audit.md').write_text(calyx.markdown(payload),encoding='utf-8')
        enhanced[key]=payload;stresses[key]=cost_sensitivity(tag);save(out/f'{key}-trade-cost-stress.json',stresses[key])
        boots[key]=full_window_bootstrap(tag);boots[key+'-stressed']=full_window_bootstrap(tag,True)
        print(f'AUDITED {key}: common verdict={payload["verdict"]}; cost PF={stresses[key]["pf"]:.3f}',flush=True)
    wf=[];stitched_balance=10000.;stitched_peak=10000.;stitched_dd=0
    for f in folds:
        row=readrun(f['test_report']);fold_balance=10000.
        for t in trades(f['test_report']):
            ret=t['net_profit']/fold_balance;fold_balance+=t['net_profit'];stitched_balance*=1+ret
            stitched_peak=max(stitched_peak,stitched_balance);stitched_dd=max(stitched_dd,100*(stitched_peak-stitched_balance)/stitched_peak)
        wf.append({**f,'trades':row['trades'],'net':row['net_profit'],'return_pct':row['return_pct'],'pf':row['net_pf'],'win_rate':row['net_win_rate'],'dd_pct':row['dd_pct']})
    wf_summary={'folds':wf,'profitable_folds':sum(f['net']>0 for f in wf),'total_folds':len(wf),
                'normalized_compound_return_pct':(stitched_balance/10000-1)*100,'normalized_closed_dd_pct':stitched_dd,
                'scope':'Each native fold resets at $10K. Stitched curve compounds normalized realized trade returns; not an additional continuous native account run.'}
    ns=[readrun(t) for t in final['neighbours']];positive=sum(n['net_profit']>0 for n in ns)/len(ns)
    train=readrun(freeze['selected']['train']);valid=readrun(freeze['selected']['validation']);locked=readrun(final['1y'])
    gates={'eligible_train_validation':freeze['selected']['eligible'],'positive_train':train['net_profit']>0,'positive_validation':valid['net_profit']>0,
           'positive_final_year':locked['net_profit']>0,'final_year_pf_at_least_1_2':(locked['net_pf'] or 0)>=1.2,
           'final_year_minimum_30_trades':locked['trades']>=30,'final_year_equity_dd_at_most_15':locked['dd_pct']<=15,
           'positive_cost_stressed_final_year':stresses['1y']['net']>0,'at_least_60pct_positive_neighbours':positive>=.6,
           'walk_forward_positive':wf_summary['normalized_compound_return_pct']>0,'two_of_three_walk_forward_folds_positive':wf_summary['profitable_folds']>=2,
           'bootstrap_p05_return_positive':boots['1y'].get('return_p05_pct',-100)>0,
           'all_common_calyx_gates_clear':all(enhanced['1y']['gates'].values())}
    result={'native_run_count':len(allruns),'unique_parameter_configs':len({r['config_id'] for r in allruns}),
            'conservative_tested_configurations_including_delays':trial_count,'source_sha256':allruns[0]['source_sha256'],
            'frozen_selection':freeze,'final_runs':final,'cost_stress':{k:{a:b for a,b in v.items() if a!='trades_detail'} for k,v in stresses.items()},
            'bootstrap_full_calendar':boots,'common_audit_summaries':{k:{a:b for a,b in v.items() if a!='trades'} for k,v in enhanced.items()},
            'walk_forward':wf_summary,'positive_neighbours_pct':100*positive,
            'neighbours':[{'config':n['config'],'net':n['net_profit'],'pf':n['net_pf'],'trades':n['trades'],'dd_pct':n['dd_pct']} for n in ns],
            'calendar_breakdown_5y':month_year(trades(final['5y'])),'promotion_gates':gates,
            'verdict':'RESEARCH_FORWARD_CANDIDATE_ONLY' if all(gates.values()) else 'NOT_APPROVED_FOR_DEPLOYMENT',
            'limitations':['Earlier raw summaries already inspected; excluded year not truly unseen.','Actual real ticks begin 2026-01-01; older windows partly generated.',
                           'Native 1-minute OHLC used for preliminary search only.','Block bootstrap and multiple-comparison adjustment are conditional estimates, not probabilities of live profit.',
                           'Full-calendar bootstrap includes inactive days; common legacy audit begins at first trade and ends at last trade.',
                           'No live portfolio/BAT/website change.']}
    save(ROOT/'audit-results.json',result);print(json.dumps({'verdict':result['verdict'],'gates':gates,'runs':len(allruns),'trials':trial_count},indent=2),flush=True)
if __name__=='__main__':main()
