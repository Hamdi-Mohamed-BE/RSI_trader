"""Audit inputs, native cash and guards without accessing live trading API."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
import numpy as np
import study as s
import native_analysis as na
import test_research
ROOT=Path(__file__).resolve().parent
def main():
    inputs=json.loads((ROOT/'INPUTS.json').read_text())
    assert all(s.sha(s.SOURCE/n)==h for n,h in inputs['source_files'].items())
    assert s.sha(ROOT/'RULES.md')==inputs['protocol_sha256'] and s.sha(ROOT/'run-config.json')==inputs['config_sha256']
    build=json.loads((ROOT/'BUILD.json').read_text())
    assert all(s.sha(ROOT/n)==h for n,h in build['hashes'].items())
    source=(ROOT/'BruniProxy.mq5').read_text();assert '!MQLInfoInteger(MQL_TESTER)' in source
    assert 'entry+s*MathAbs(entry-stop)*InpRR' in source
    results=na.raw();parity=[]
    for sym in s.CFG['symbols']:
        for v in s.CFG['variants']:
            a=ROOT/'native'/f'{sym}-{v["name"]}-1y-m4/groups.csv.gz';b=ROOT/'native'/f'{sym}-{v["name"]}-6m-m4/groups.csv.gz'
            one=na.csvread(a);six=na.csvread(b)
            cols=['open_time','side','volume','fill','sl','target','net']
            # Ignore first week's possible carry-over from before the shorter test boundary.
            cutoff=s.stamp('2026-04-03')
            norm=lambda xs:[tuple(x[k] for k in cols) for x in xs if int(x['open_time'])>=cutoff]
            left,right=norm(one),norm(six)
            parity.append(dict(symbol=sym,variant=v['name'],one_year_trades=len(left),six_month_trades=len(right),exact=left==right))
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_research);r=unittest.TextTestRunner(verbosity=2).run(suite)
    assert r.wasSuccessful()
    assert all(x['exact'] for x in parity)
    assert all(x['stats']['history_quality']=='100% real ticks' for x in results if x['window']=='6m')
    proc=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath,@{Name='CreatedUtc';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}} | ConvertTo-Json"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert proc.returncode==0
    terminals=json.loads(proc.stdout);terminals=terminals if isinstance(terminals,list) else [terminals]
    live=[x for x in terminals if x['ExecutablePath']==r'C:\Program Files\MetaTrader 5\terminal64.exe']
    assert len(live)==1 and live[0]['ProcessId']==11196 and live[0]['CreatedUtc'].startswith('2026-09-27T20:58:13.301784')
    assert len(terminals)==1,'Research terminal should have exited before handoff'
    overlays=json.loads((ROOT/'OVERLAYS.json').read_text());features=json.loads((ROOT/'FEATURES-FTMO.json').read_text())
    # Frozen insufficient-evidence VAM is exactly the fixed-risk baseline.
    for firm in ['FTMO','Instant']:
        for stress in [False,True]:
            a=next(x for x in overlays if x['firm']==firm and x['stress']==stress and x['model']=='fixed')
            b=next(x for x in overlays if x['firm']==firm and x['stress']==stress and x['model']=='vam-evidence-gated')
            assert a['historical']==b['historical'] and a['rolling']==b['rolling']
    audit=dict(tests=r.testsRun,native_cases=len(results),native_trace_and_cash_checks=sum(x['checks'] for x in results),max_native_cash_error=max(x['stats']['cash_error'] for x in results),
      nested_window_parity=parity,live_terminal=live[0],source_hashes_unchanged=True,frozen_rules_unchanged=True,
      kelly_trained_opportunities=sum(x['kelly_trained'] for x in features),max_prior_streak7_observations=max(x['streak7_n'] for x in features),
      capital_exhausted_cases=[x['tag'] for x in results if x['stats']['capital_exhausted']],
      files={p.name:s.sha(p) for p in ROOT.iterdir() if p.suffix in ['.py','.mq5','.ex5','.json'] and p.name!='VERIFICATION.json'})
    s.save('VERIFICATION.json',audit)
    complete=json.loads((ROOT/'COMPLETE.json').read_text());complete['verified_code_sha256']={n:s.sha(ROOT/n) for n in ['study.py','prop_engine.py','native_analysis.py','verify.py','test_research.py','report.py']}
    complete['verdict']='No raw candidate or risk overlay qualified; no deployment.';s.save('COMPLETE.json',complete)
    print(json.dumps({k:v for k,v in audit.items() if k!='files'},indent=2),flush=True)
if __name__=='__main__':main()
