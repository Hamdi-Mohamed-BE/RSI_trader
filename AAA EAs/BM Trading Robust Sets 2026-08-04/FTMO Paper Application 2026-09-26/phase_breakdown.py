"""Phase-by-phase extension of the frozen offline comparison. No MT5 connection."""
from __future__ import annotations
import math
import random
import statistics
from collections import Counter
from datetime import datetime
import compare as c

HORIZONS = [30, 60, 90, 120, 180]
N = 1000
POOL_START = datetime(2026, 3, 2, tzinfo=c.UTC).timestamp()
CONFIGS = c.CONFIGS[-3:]

def epoch(s):
    return datetime.fromisoformat(s).timestamp() if s else None

def happened(t, cutoff):
    return t is not None and t < cutoff

def marks(r, ns):
    p = {x['phase']: epoch(x['time']) for x in r['passes']}
    return dict(p1=p.get(1), p2=p.get(2), p2_ready=ns['business'](p[1],2) if 1 in p else None,
                funded=epoch(r['funded_at']), paid=epoch(r['receipt_at']), breach=epoch(r['breach_at']))

def classify(m, cutoff):
    if happened(m['breach'], cutoff):
        return 'breached_funded' if happened(m['funded'], m['breach']) else 'breached_evaluation'
    if happened(m['paid'], cutoff):
        return 'first_reward_received'
    if happened(m['funded'], cutoff):
        return 'funded_waiting_first_reward'
    if happened(m['p2'], cutoff):
        return 'passed_both_awaiting_activation'
    if happened(m['p2_ready'], cutoff):
        return 'phase2_unfinished'
    if happened(m['p1'], cutoff):
        return 'phase1_passed_awaiting_phase2'
    return 'phase1_unfinished'

def distribution(vals):
    if not vals:
        return dict(n=0, mean=None, median=None, p10=None, p90=None)
    v=sorted(vals)
    def q(p):
        x=(len(v)-1)*p;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
    return dict(n=len(v),mean=statistics.mean(v),median=statistics.median(v),p10=q(.1),p90=q(.9))

def summarize(results, ns):
    mm=[marks(r,ns) for r in results]
    total=len(results)
    out=[]
    for d in HORIZONS:
        cutoff=c.START+d*c.DAY
        counts=Counter(classify(m,cutoff) for m in mm)
        count=lambda key:sum(happened(m[key],cutoff) for m in mm)
        p1=count('p1');p2=count('p2');entered=count('p2_ready');fund=count('funded');paid=count('paid')
        assert sum(counts.values())==total
        assert paid<=fund<=p2<=p1<=total
        assert p2<=entered
        out.append(dict(days=d,paths=total,phase1_passed=p1,phase2_started=entered,
                        both_phases_passed=p2,funded=fund,first_payout_received=paid,
                        phase1_pass_pct=100*p1/total,both_pass_pct=100*p2/total,
                        phase2_completion_pct_among_started=100*p2/entered if entered else None,
                        funded_pct=100*fund/total,payout_pct=100*paid/total,
                        evaluation_breach_pct=100*counts['breached_evaluation']/total,
                        breach_before_first_reward_pct=100*(counts['breached_evaluation']+counts['breached_funded'])/total,
                        unfinished_evaluation_pct=100*(counts['phase1_unfinished']+counts['phase2_unfinished']+
                                                      counts['phase1_passed_awaiting_phase2'])/total,
                        counts=dict(counts),funded_mc_interval=c.wilson(fund,total)))
    end=c.START+180*c.DAY
    p1=[(m['p1']-c.START)/c.DAY for m in mm if happened(m['p1'],end)]
    p2=[(m['p2']-m['p2_ready'])/c.DAY for m in mm if happened(m['p2'],end)]
    funded_cohort=[m for m in mm if happened(m['funded'],end)]
    timing=dict(phase1_days_among_phase1_passers=distribution(p1),
                phase2_days_from_availability_among_phase2_passers=distribution(p2),
                funded_days_from_purchase=distribution([(m['funded']-c.START)/c.DAY for m in funded_cohort]),
                payout_days_from_purchase=distribution([(m['paid']-c.START)/c.DAY for m in mm if happened(m['paid'],end)]),
                funded_cohort_phase1_days=distribution([(m['p1']-c.START)/c.DAY for m in funded_cohort]),
                funded_cohort_phase2_days=distribution([(m['p2']-m['p2_ready'])/c.DAY for m in funded_cohort]))
    # All durations are conditional on completion inside the 180-day horizon.
    for item in timing.values():
        if item['n']:
            assert 0<=item['p10']<=item['median']<=item['p90']<=180
    gate_count=sum(any('total_loss_buffer' in k and v>0 for k,v in r['counts'].items()) for r in results)
    return dict(horizons=out,timing=timing,
                paths_touching_internal_total_buffer=gate_count,
                max_modeled_daily_loss=max(r['worst_daily_usd'] for r in results),
                max_peak_to_trough_stop_reserve_dd=max(r['model_dd_pct'] for r in results))

def checks(ns):
    # State attribution at a deadline, independent of the EA data.
    m=dict(p1=10,p2_ready=12,p2=20,funded=25,paid=40,breach=None)
    assert classify(m,9)=='phase1_unfinished'
    assert classify(m,11)=='phase1_passed_awaiting_phase2'
    assert classify(m,15)=='phase2_unfinished'
    assert classify(m,21)=='passed_both_awaiting_activation'
    assert classify(m,30)=='funded_waiting_first_reward'
    assert classify(m,41)=='first_reward_received'
    assert classify(dict(m,breach=18),19)=='breached_evaluation'
    assert classify(dict(m,breach=30),35)=='breached_funded'
    assert distribution([1,2,3])['median']==2
    # Two business days of review are excluded from Phase 2's own duration.
    first=datetime(2026,9,25,tzinfo=c.UTC).timestamp()
    assert (ns['business'](first,2)-first)/c.DAY==4
    assert (ns['business'](first,5)-first)/c.DAY==7
    return 11

def report(out):
    def f(v,n=1):return '—' if v is None else f'{v:.{n}f}'
    lines=['# FTMO $10K Swing: phase-by-phase simulation', '',
           'Offline extension, 26 September 2026. No new EA optimization and no account or live settings changed.', '',
           '## Interpretation', '',
           '**Fitted-history simulation, not a calibrated forecast.** 1,000 matched paths per portfolio/cost case. Source pool: 26 joint weeks, 2 March–30 August 2026. These news presets were selected using this same history, containing only 20 gold and 17 silver news trades. No genuine out-of-sample claim is made.', '',
           'Account: $10,000 FTMO 2-Step Swing. Phase 1 +$1,000; Phase 2 +$500; four trading days per phase; $500 daily and $1,000 static total loss limits; Prague midnight reset. No evaluation time limit. Reporting stops at 180 days or first reward request, whichever occurs first, with subsequent first-payment receipt scheduled.', '',
           'Ordinary risk $71.43/entry, news $10/side, with lot rounding and both news sides reserved. Shared internal gates: $300 daily admission budget, $225 aggregate initial risk, $150 correlated-metal/per-symbol risk, $9,200 internal buffer, seven entries/day maximum, no new entries after three closed losses. Full assumptions and costs remain in PROTOCOL.md.', '',
           'Two business days assumed between Phase 1 and Phase 2, five between Phase 2 completion and funded activation, four for first-reward review/payment after eligibility. These are modeling assumptions, not guaranteed FTMO turnaround. Eligibility starts 14 calendar days after the first funded trade while flat.', '',
           '## Phase probabilities by deadline', '']
    for r in out['cases']:
        lines += ['### '+r['config']['name']+' — '+('stressed costs' if r['stress'] else 'reference costs'), '',
                  '| Calendar days | Phase 1 passed | Both phases passed | Funded/activated | First reward received | Evaluation breached | Still evaluating |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for h in r['summary']['horizons']:
            lines.append(f"| {h['days']} | {f(h['phase1_pass_pct'])}% | {f(h['both_pass_pct'])}% | {f(h['funded_pct'])}% | {f(h['payout_pct'])}% | {f(h['evaluation_breach_pct'])}% | {f(h['unfinished_evaluation_pct'])}% |")
        lines += ['', 'Timing is conditional on finishing the relevant milestone by day 180; unfinished accounts are censored, not assigned zero or labeled failed. Phase 2 time begins when its account becomes available, excluding the prior review wait. Separate medians do not add up to the median total.', '',
                  '| Milestone | Successful paths | Mean calendar days | Median | 10th–90th percentile |',
                  '|---|---:|---:|---:|---:|']
        labels={'phase1_days_among_phase1_passers':'Phase 1, from purchase',
                'phase2_days_from_availability_among_phase2_passers':'Phase 2, from its availability',
                'funded_days_from_purchase':'Funded, from purchase, including reviews',
                'payout_days_from_purchase':'First payment, from purchase'}
        for key,label in labels.items():
            d=r['summary']['timing'][key]
            lines.append(f"| {label} | {d['n']} | {f(d['mean'])} | {f(d['median'])} | {f(d['p10'])}–{f(d['p90'])} |")
        h=r['summary']['horizons'][-1]
        lines += ['', f"Phase 2 completion among paths that had become eligible to start it by day 180: {f(h['phase2_completion_pct_among_started'])}%. This is deadline-censored, not eventual conditional success.", '',
                  f"Internal $9,200 buffer gate encountered by {r['summary']['paths_touching_internal_total_buffer']} of 1,000 paths. This records a rejected admission, not necessarily permanent termination.", '']
    lines += ['## Breach-risk limitation', '',
              'The simulated breach rate concerns the evaluation and, separately, funded trading only until the first reward request (or day 180). It is not the probability of losing a funded account over its full lifetime or after withdrawals. The zero breach outcome, if observed, is conditional on admission gates and stop-reserve equity assumptions. Stops do not cap gaps, and we did not replay FTMO bid/ask equity tick by tick. Real-world breach probability is not established by this study.', '',
              'Do not equate 1 minus pass probability with blow-up probability: unfinished accounts and accounts waiting for administrative activation are distinct states. The state-count dictionaries in PHASE_RESULTS.json reconcile to 1,000 at every deadline.', '',
              '## News eligibility', '',
              'Swing permits news trading generally, but the exact pre-news two-sided stop strategy remains subject to FTMO forbidden gap-trading practices and contract review. No disqualification probability is modeled; written clarification is needed before deployment.', '',
              '## Evidence and validation', '',
              'All source hashes were verified. The prior nine engine tests, seven source-adapter assertions and eight historical parity fields pass again. Eleven new deadline/timing tests pass. All phase funnels reconcile, and the funded/first-payout percentages reproduce the previous results for every matching horizon.', '',
              '- [FTMO objectives](https://ftmo.com/en/trading-objectives/)',
              '- [FTMO comparison](https://ftmo.com/en/comparison-table/)',
              '- [Reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)',
              '- [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/)',
              '- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)', '']
    (c.ROOT/'PHASE_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
    c.verify_sources()
    data=c.read(c.SOURCE/'prepared.json')
    old=c.read(c.ROOT/'RESULTS.json')['results']
    ns=c.engine()
    validation=c.tests(data)
    validation['new_phase_tests']=checks(ns)
    weeks=c.pool(data,POOL_START,26)
    rng=random.Random(20260926)
    samples=[[rng.randrange(26) for _ in range(26)] for _ in range(N)]
    output=dict(paths=N,seed=20260926,synthetic_start=c.iso(c.START),end=c.iso(c.START+180*c.DAY),
                pool_start=c.iso(POOL_START),pool_end=c.iso(c.END),checks=validation,cases=[])
    for config in CONFIGS:
        for stress in (False,True):
            ns['RISK']=config['risk'];rr=[]
            for sample in samples:
                rows,places=c.sample_rows(data,config['keys'],POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
                r=ns['replay'](rows,places,c.START,c.START+180*c.DAY,news_risk=10.,stress=stress)
                rr.append(r)
            summary=summarize(rr,ns)
            prior=next(r for r in old if r['pool']=='recent26' and r['config']['name']==config['name'] and r['stress']==stress)
            for prev in prior['outcomes']:
                new=next(r for r in summary['horizons'] if r['days']==prev['horizon_days'])
                for field in ('funded_pct','payout_pct'):
                    assert abs(new[field]-prev[field])<1e-9,(config['name'],stress,field,new[field],prev[field])
            paths=[dict(id=i,passes=r['passes'],funded_at=r['funded_at'],request_at=r['request_at'],
                        receipt_at=r['receipt_at'],breach_at=r['breach_at'],phase=r['phase'],
                        reward=r['reward'],trades=r['trades'],counts=r['counts']) for i,r in enumerate(rr)]
            output['cases'].append(dict(config=config,stress=stress,summary=summary,paths=paths))
            c.save(c.ROOT/'PHASE_RESULTS.json',output)
            report(output)
            print(config['name'], 'stress' if stress else 'reference', json_summary(summary),flush=True)
    print('COMPLETE: phase funnels, timing distributions and 6,000 path records saved.',flush=True)

def json_summary(s):
    import json
    return json.dumps(dict(day180=s['horizons'][-1],timing=s['timing']))

if __name__=='__main__':main()
