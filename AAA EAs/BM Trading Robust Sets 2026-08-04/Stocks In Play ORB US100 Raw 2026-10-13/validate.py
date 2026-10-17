"""Read-only independent result checks plus a saved validation receipt."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
r=json.loads((root/'RESULTS.json').read_text(encoding='utf-8'))
assert r['engine_sha256']==hashlib.sha256((root/'run.py').read_bytes()).hexdigest()
assert r['protocol_sha256']==hashlib.sha256((root/'PROTOCOL.json').read_bytes()).hexdigest()
g=r['opening_gate_audit']
assert g['summary']['scheduled_sessions']==756
assert sum(v['assessable'] for v in g['yearly'].values())==g['summary']['assessable']==704
assert sum(v['not_assessable'] for v in g['yearly'].values())==g['summary']['not_assessable']==52
assert len({x['date'] for x in g['records']})==756
assert sum(x['passes_2x'] for x in g['records'])==0
assert len(g['mt5_spot_checks'])==2 and all(x['price_and_tick_volume_match'] for x in g['mt5_spot_checks'])
for row in g['records']:
    if row['relative_volume'] is not None:
        assert abs(row['opening_volume']/row['previous_14_mean']-row['relative_volume'])<1e-12
assert all(r[k]['summary']['trades']==0 for k in ['primary','alternative_ordering','extra_cost'])
report=(root/'Results.html').read_text(encoding='utf-8')
assert report.count('<td>Below 2×</td>')==704
assert report.count('<td>Unassessable</td>')==52
assert 'not a complete three-year execution result' in report
assert 'RVOL ≥1.0' in report and 'RVOL ≥2.0' in report
tests=subprocess.run([sys.executable,'test_engine.py'],cwd=root,capture_output=True,text=True)
assert tests.returncode==0,tests.stdout+tests.stderr
receipt={'unit_tests':13,'result_reconciliations':'passed','all_756_opening_decisions_in_report':True,
         'two_read_only_mt5_spot_checks':'passed','no_optimisation_or_live_deployment':True,
         'result_sha256':hashlib.sha256((root/'RESULTS.json').read_bytes()).hexdigest(),
         'report_sha256':hashlib.sha256((root/'Results.html').read_bytes()).hexdigest()}
(root/'VALIDATION.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
