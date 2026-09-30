from pathlib import Path
import json,hashlib,subprocess,re
import numpy as np
import study as s
import native_analysis as na
ROOT=Path(__file__).resolve().parent
def main():
 cfg=json.loads((ROOT/'run-config.json').read_text());build=json.loads((ROOT/'BUILD.json').read_text())
 for p,h in build['hashes'].items():assert s.sha(ROOT/p)==h
 expected=[(v['name'],w,4 if w in ('smoke','6m','1y') else 1) for v in cfg['variants'] for w in ('smoke','6m','1y','3y','5y')]
 missing=[(n,w,m) for n,w,m in expected if not (ROOT/'native'/f'USTEC-{n}-{w}-m{m}/run.json').exists()]
 assert not missing,missing
 raw=na.raw();checks=0;coverage=[]
 for r in raw:
  assert not any(v for k,v in r['flags'].items() if k!='margin_call'),(r['tag'],r['flags'])
  if r['flags']['margin_call']:assert r['stats']['capital_exhausted']
  sm=r['signal_audit']['summary']
  sync_rejections=int(re.search(r'syncMissing=(\d+)',sm)[1])
  missing_refs=int(re.search(r'referenceMissing=(\d+)',sm)[1]);decisions=int(re.search(r'decisions=(\d+)',sm)[1])
  coverage.append(dict(case=r['tag'],reference_rejections=missing_refs,synchronization_rejections=sync_rejections,entry_window_checks=decisions))
  checks+=r['checks']+r['signal_audit']['checks']
 parity=[]
 for v in cfg['variants']:
  a=na.csvread(ROOT/'native'/f"USTEC-{v['name']}-6m-m4/groups.csv.gz")
  b=na.csvread(ROOT/'native'/f"USTEC-{v['name']}-1y-m4/groups.csv.gz")
  b=[x for x in b if float(x['open_time'])>=s.stamp('2026-03-27')]
  assert len(a)==len(b),(v['name'],len(a),len(b))
  for x,y in zip(a,b):
   for k in ('open_time','close_msc','side','fill','sl','target','volume','risk','net'):
    assert abs(float(x[k])-float(y[k]))<1e-7,(v['name'],k,x[k],y[k])
  parity.append(dict(variant=v['name'],matched=len(a)))
 ps=subprocess.run(['powershell','-NoProfile','-Command',"""Get-CimInstance Win32_Process -Filter "name='terminal64.exe'" | Select-Object ProcessId,ExecutablePath,@{Name='CreatedUtc';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Compress"""],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 assert ps.returncode==0;procs=json.loads(ps.stdout);procs=[procs] if isinstance(procs,dict) else procs
 live=[p for p in procs if p['ExecutablePath']==r'C:\Program Files\MetaTrader 5\terminal64.exe']
 assert len(live)==1 and live[0]['ProcessId']==11196 and live[0]['CreatedUtc'].startswith('2026-09-27T20:58:13.301784')
 assert not any('_Backtests' in p['ExecutablePath'] for p in procs)
 proc=subprocess.run(['git','diff','--stat'],cwd=ROOT.parents[2],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert proc.returncode==0 and not proc.stdout.strip()
 tests=subprocess.run([__import__('sys').executable,'-m','unittest','test_research','-v'],cwd=ROOT,capture_output=True,text=True)
 assert tests.returncode==0,tests.stderr
 (ROOT/'TEST_RESULTS.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
 hist=json.loads((ROOT/'HISTORY_AUDIT.json').read_text());assert hist['mismatching_decisions']==0
 output=dict(passed=True,scope='Execution/accounting/timing checks; NOT strategy promotion or complete data coverage',complete_reference_history=not any(x['reference_rejections'] or x['synchronization_rejections'] for x in coverage),valid_native_cases=len(raw),unit_tests=18,assertions_at_least=checks,nested_window_parity=parity,reference_coverage=coverage,independent_history=hist,live_process=live[0],tracked_git_diff_empty=True,
  hashes={p.name:s.sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.mq5','.ex5')},infrastructure_retry_reports=len(list((ROOT/'native').glob('*/infrastructure-failure-*.report.htm.gz'))))
 s.save('VERIFICATION.json',output);print(json.dumps({k:v for k,v in output.items() if k not in ('hashes','independent_history')},indent=2))
if __name__=='__main__':main()
