"""Bounded weekly-cap study; uses the audited native harness in this directory."""
from pathlib import Path
import json,msvcrt
import engine as e
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'XAU Slow Trend Filter Review 2026-09-29'
ADX=dict(ResearchADXMinimum=20,ResearchDI=True,ResearchADXRising=True)
e.FILTER_DEFAULTS['ResearchWeeklyMode']=0
e.VARIANTS={'baseline':{},'adx20-di-rising':ADX,
    'calendar':dict(ResearchWeeklyMode=1),'rolling7':dict(ResearchWeeklyMode=2),
    'adx-calendar':ADX|dict(ResearchWeeklyMode=1),'adx-rolling7':ADX|dict(ResearchWeeklyMode=2)}
CANDIDATES=['calendar','rolling7','adx-calendar','adx-rolling7']
def core(ts):return [{k:v for k,v in t.items() if k not in ('ea','label','strategy','id')} for t in ts]
def main():
    with (e.TESTER/'research-serial.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        checks=[]
        for v in ['baseline','adx20-di-rising']:
            # The ADX control has a stored one-year real-tick result, not OHLC.
            model=1 if v=='baseline' else 4
            r=e.case(v,'1y',model)
            new=json.loads((ROOT/'native'/r['case']/'trades.json').read_text())
            old=json.loads((OLD/'native'/r['case']/'trades.json').read_text())
            ok=core(new)==core(old);assert ok,'Off-switch parity failed: '+v
            checks.append(dict(variant=v,model=model,trades=len(new),passed=ok))
        e.save(ROOT/'PARITY.json',dict(passed=True,checks=checks))
        e.status('PARITY PASS',checks=checks)
        dev={v:e.case(v,'dev',1) for v in CANDIDATES}
        val={v:e.case(v,'val',1) for v in CANDIDATES}
        eligible=[]
        for v in CANDIDATES:
            d=dev[v]['metrics'];m=val[v]['metrics']
            if d['trades']>=20 and d['return_pct']>0 and (d['profit_factor'] or 0)>=1.15 and m['trades']>=10 and m['return_pct']>0 and (m['profit_factor'] or 0)>=1.10:eligible.append(v)
        winner=max(eligible or CANDIDATES,key=lambda v:e.score(val[v]))
        selection=dict(chosen=winner,older_windows_pass=bool(eligible),eligible=eligible,criterion='older validation return / equity drawdown, before recent tests',exploratory=True)
        e.save(ROOT/'SELECTION.json',selection);e.status('SELECTION FROZEN',**selection)
        for v in CANDIDATES:e.case(v,'6m',4)
        e.case(winner,'1y',4)
        e.status('COMPLETE',selected=winner,older_windows_pass=bool(eligible))
if __name__=='__main__':main()
