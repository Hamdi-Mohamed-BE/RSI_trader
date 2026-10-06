"""Confirm finalists, freeze on validation, then test reserved and viewed windows."""
from datetime import datetime,timezone
import json
import runner as n,search
R=n.R
def main():
    allrows=json.loads((R/'SEARCH RESULTS.json').read_text());finalists=json.loads((R/'FINALISTS.json').read_text())
    candidates=[f['inputs'] for f in finalists[:2]]
    trio=max([r for r in allrows if all(r['inputs'][k]=='true' for k in ['InpEnableDrop','InpEnableMonday','InpEnableTrend'])],key=search.score)['inputs']
    if n.key(trio) not in [n.key(v) for v in candidates]:candidates.append(trio)
    plan=dict(candidates=candidates,selection='Native development and validation only; score as registered, tie prefers lower R. The third candidate retains all three modules for an honest trio comparison.',holdout=n.PERIODS['HOLD'],recent_not_holdout=True,monte_carlo_paths=10000,block_length=5,control_seeds=[20261004,20261005,20261006],control='signal-free native entries with preregistered per-bar probabilities 0.02/0.04/0.06, Monday only for its module; approximate frequency, not exactly matched. Same chosen stops/exits/session/risk/position/loss-pause limits.',risk_comparison=[.25,.5,.75,1,1.25],after_raw_failure='exploratory')
    plan=json.loads(json.dumps(plan))
    pp=R/'VALIDATION PLAN.json'
    if pp.exists():assert json.loads(pp.read_text())==plan
    else:n.save(pp,plan)
    checks=[]
    for i,inputs in enumerate(candidates):
        print('CONFIRM finalist '+str(i+1)+' development and validation',flush=True)
        dev=n.run(inputs,'DEV',4);val=n.run(inputs,'VAL',4)
        checks.append(dict(id=n.key(inputs),inputs=inputs,development=dev,validation=val))
        n.save(R/'VALIDATION RESULTS.json',checks)
        print('VAL '+json.dumps(dict(id=n.key(inputs),**val['net_metrics'],equity_dd_pct=val['native']['equity_dd_pct'])),flush=True)
    best=max(checks,key=lambda r:(search.score(dict(net_metrics=r['validation']['net_metrics'],export_stats=r['validation']['export_stats'])),-float(r['inputs']['InpTrendTargetR'])))
    frozen=dict(id=best['id'],inputs=best['inputs'],selection_source='validation only, no reserved/recent results',source_sha256=n.sha(n.SOURCE),binary_sha256=n.sha(n.EXPERT),development=best['development']['net_metrics'],validation=best['validation']['net_metrics'])
    ff=R/'FROZEN FINAL.json'
    if ff.exists():assert json.loads(ff.read_text())==frozen
    else:n.save(ff,frozen)
    (R/'FINAL RESEARCH ONLY.set').write_text('\n'.join(k+'='+v for k,v in frozen['inputs'].items())+'\n',encoding='utf-8')
    results={}
    for phase in ['HOLD','1Y','3M','6M','3Y','5Y']:
        print('FINAL native '+phase,flush=True);r=n.run(best['inputs'],phase,4);results[phase]=r;n.save(R/'FINAL RESULTS.json',results)
        print('FINAL '+phase+' '+json.dumps(dict(**r['net_metrics'],equity_dd_pct=r['native']['equity_dd_pct'],history_quality=r['native']['history_quality'])),flush=True)
    results['XAG1Y']=n.run(best['inputs'],'1Y',4,'XAGUSD');n.save(R/'FINAL RESULTS.json',results)
    # A trio-only alternative is a diagnostic, never used to change the frozen choice.
    trios=[r for r in checks if all(r['inputs'][k]=='true' for k in ['InpEnableDrop','InpEnableMonday','InpEnableTrend'])]
    if trios:
        t=trios[0];comparison={p:n.run(t['inputs'],p,4) for p in ['1Y','3M','6M','3Y','5Y']}
        n.save(R/'OPTIMISED TRIO DIAGNOSTIC.json',comparison)
    controls=[]
    for seed in plan['control_seeds']:
        r=n.run({**best['inputs'],'InpControl':True,'InpControlSeed':seed},'VAL',4);controls.append(r)
    n.save(R/'CONTROLS.json',controls)
    risk=[]
    for amount in plan['risk_comparison']:
        risk.append(n.run({**best['inputs'],'InpRiskPercent':amount},'1Y',4))
    n.save(R/'RISK COMPARISON.json',risk)
    print('Native confirmations, frozen earlier reserve, recent diagnostics, silver, controls and risk comparisons finished. No deployment.',flush=True)
if __name__=='__main__':main()
