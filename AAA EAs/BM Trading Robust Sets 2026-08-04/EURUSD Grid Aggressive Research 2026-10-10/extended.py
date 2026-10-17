"""Supplemental higher-exposure pass, frozen separately before its outcomes."""
from pathlib import Path
import contextlib, json, msvcrt, traceback
import run as r
n=r.n;ROOT=r.ROOT

def main():
    original=n.read(ROOT/'SUMMARY.json');assert original['completed']==24 and not original['failed']
    candidates=[];rows=[]
    for risk in [5,10]:
        for lot in [.5*risk/5,1.0*risk/5]:
            for reward in [.25,.5]:
                cid=f'fast-r{risk}-l{lot:g}-tp{reward:g}-g100'
                inputs=dict(InpSignalTF='5',InpEMAPeriod='5',InpMagicBase='261010000',InpBasketTargetUSD='10.0',
                    InpStartingLot=str(lot),InpLotIncrement='0',InpGridPoints='100',InpAlternateAfterBasket='false',
                    InpMaxOrders='5',InpBasketLossPercent=str(risk),InpBasketTargetR=str(reward),InpScaleLotsWithBalance='true',InpMaxAgeHours='72')
                candidates.append(dict(id=cid,family='guarded',inputs=inputs))
                rows.append(r.case(cid,'guarded','dev',inputs,'2020.10.10','2024.10.10'))
    plan=dict(reason='Initial capped studies often time-exited before target; increase equal lot exposure, without changing entries or source logic.',
        candidates=candidates,cases=rows,ranking='Same development-only gate/ranking as original plan; take top two, label failures.',
        selected_count=2,recent_results_not_selection_data=True,not_initial_preregistration=True,
        source_sha256=n.sha(ROOT/'EURUSD Grid Aggressive Research.mq5'))
    path=ROOT/'SUPPLEMENTAL_PLAN.json'
    if path.exists():assert n.read(path)==plan,'Supplemental plan changed'
    else:n.save(path,plan)
    r.c.verify=r.verify
    status=ROOT/'SUPPLEMENTAL_STATUS.json';state=n.read(status) if status.exists() else dict(complete={},failed={})
    def batch(cases):
        for row in cases:
            if row['slug'] in state['complete']:continue
            print('START supplemental '+row['slug'],flush=True)
            try:
                with (ROOT/(row['slug']+'-run.log')).open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):q=r.run_case(row)
                state['complete'][row['slug']]=str(ROOT/'native'/q['tag']/'results.json');state['failed'].pop(row['slug'],None)
                m=q['summary'];print('DONE '+row['slug']+' '+json.dumps({k:m[k] for k in ['return_pct','average_monthly_pct','equity_dd_pct','stopout_deals']}),flush=True)
            except Exception as e:state['failed'][row['slug']]=dict(error=str(e),trace=traceback.format_exc()[-5000:]);print('FAILED '+str(e),flush=True)
            n.save(status,state)
    batch(rows);assert all(x['slug'] in state['complete'] for x in rows),state['failed']
    dev=[n.read(Path(state['complete'][x['slug']])) for x in rows]
    key=lambda q:(r.passes(q['summary']),q['summary']['compounded_equivalent_monthly_pct'],q['summary']['baskets']['pf'] or 0,-q['summary']['equity_dd_pct'])
    choices=sorted(dev,key=key,reverse=True)[:2]
    selection=dict(selected=[dict(id=q['candidate'],passes_development_gate=r.passes(q['summary']),development_summary=q['summary']) for q in choices],
        development_only=True,selection_data=['2020.10.10','2024.10.10'],not_genuinely_untouched=True)
    sel=ROOT/'SUPPLEMENTAL_SELECTION.json'
    if sel.exists():assert n.read(sel)==n.safe(selection),'Supplemental selection changed'
    else:n.save(sel,selection)
    index={x['id']:x for x in candidates};validation=[]
    for q in choices:
        for stage,start in [('validation2y','2024.10.10'),('validation1y','2025.10.10')]:
            validation.append(r.case(q['candidate'],'guarded',stage,index[q['candidate']]['inputs'],start,'2026.10.10'))
    n.save(ROOT/'SUPPLEMENTAL_VALIDATION_PLAN.json',validation);batch(validation)
    assert not state['failed'] and len(state['complete'])==12,state['failed']
    additions=[n.read(Path(p)) for p in state['complete'].values()]
    bytag={q['tag']:q for q in [*original['results'],*additions]}
    original.update(results=list(bytag.values()),completed=len(bytag),supplemental_plan=plan,supplemental_selection=selection)
    assert original['completed']==36
    n.save(ROOT/'SUMMARY.json',original)
    v=n.read(ROOT/'VERIFICATION.json');v.update(completed=36,supplemental_candidates_frozen_before_outcomes=True,supplemental_development_only_selection=True)
    n.save(ROOT/'VERIFICATION.json',v);print('ALL 36 AGGRESSIVE RESEARCH CASES FINISHED',flush=True)

if __name__=='__main__':
    with (r.BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1);n.available();main()
