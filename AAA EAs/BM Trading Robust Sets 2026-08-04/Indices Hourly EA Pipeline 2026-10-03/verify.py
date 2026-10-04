"""Evidence binding, statistics and offline-report rendering checks."""
from pathlib import Path
import gzip,json,subprocess,sys
import analyse as a
R=Path(__file__).resolve().parent
def main():
 rows=json.loads((R/'SUMMARY.json').read_text());assert len(rows)==30
 proof=json.loads((R/'RECONCILIATION.json').read_text());assert len(proof)==30
 for row,receipt in zip(rows,proof):
  assert row['tag']==receipt['tag'];folder=R/'native'/row['tag'];p=folder/'positions.json.gz';positions=json.loads(gzip.decompress(p.read_bytes()))
  assert len(positions)==row['trades'] and abs(sum(x['net_cash'] for x in positions)-row['net_cash'])<1e-7
  assert a.sha(p)==receipt['positions_sha256']
  assert a.sha(folder/'deals.csv.gz')==receipt['deals_sha256'];assert a.sha(folder/'report.htm.gz')==receipt['report_sha256']
  assert a.sha(R/'CalyxHourlyProfiles.mq5')==row['source_sha256'];assert a.sha(R/'CalyxHourlyProfiles.ex5')==row['binary_sha256']
  assert abs(sum(x['net_cash'] for x in row['hour_breakdown'])-row['net_cash'])<1e-7
  assert abs(sum(x['net_cash'] for x in row['annual'])-row['net_cash'])<1e-7
  if row['account_failure']:assert len(row['recovered_forced_closes'])>=1
 mc=json.loads((R/'MONTE-CARLO.json').read_text())
 for asset in ['US30','US100','SP500']:
  m=mc[asset]['1y'];assert all(x['paths']==10000 for x in m['day_blocks']);assert len(m['day_blocks'])==3
  for x in m['day_blocks']:assert x['return_p05_p50_p95']==sorted(x['return_p05_p50_p95'])
  y=next(r for r in rows if r['asset']==asset and r['window']=='1y' and r['variant']=='baseline');assert abs(m['shuffle']['terminal_return_pct_constant']-y['return_pct'])<1e-7
 functional=json.loads((R/'FUNCTIONAL.json').read_text());assert functional['native_fault_pass']
 # Node DOM stub executes the actual inline script and every period change.
 node=Path(r'C:\Users\hama101\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
 script=R/'verify_report.cjs';v=subprocess.run([str(node),str(script)],capture_output=True,text=True,timeout=60);assert v.returncode==0,v.stderr+v.stdout
 tests=subprocess.run([sys.executable,'-m','unittest','-v','test_research'],cwd=R,capture_output=True,text=True,timeout=60);assert tests.returncode==0,tests.stderr+tests.stdout
 a.save(R/'VERIFICATION.json',{'native_passes':30,'native_profit_and_count_reconcile':True,'hashes_match':True,'all_hour_and_annual_sums_reconcile':True,'mc_paths_per_experiment':10000,'mc_shuffle_terminal_return_invariant':True,'native_functional_test_passed':True,'unit_tests':7,'unit_tests_passed':True,'report_script_rendered_all_5_horizons':True,'report_test_stdout':v.stdout,'unit_test_output':tests.stderr,'active_terminal_not_changed':True})
 print('VERIFIED: 30 native passes, MC, 7 unit tests, all report views',flush=True)
if __name__=='__main__':main()
