"""Cache verified equivalent-input runs for an already-running legacy batch.

No invented native result: retain the original report/tag/hash and explicitly
state that the result is reused. Only operational/inactive differences may alias.
"""
from pathlib import Path
import importlib.util, json

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('long_history_frozen',ROOT/'run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
plan=m.read(ROOT/'PLAN.json');state=m.read(ROOT/'RUN_STATUS.json')
for row in plan['cases']:
    if row['case_id'] in state['complete']:continue
    receipt=m.verified_reuse(row,plan,state)
    if not receipt:continue
    target=ROOT/'native'/('allrr05-'+row['slug']+'-long-'+row['case_id'].split('-')[-1])/'results.json'
    if target.exists():continue
    result=m.read(receipt['path'])
    result['verified_same_active_inputs']=True
    result['reused_native_case']=receipt['reused_case']
    result['requested_case']=row['case_id']
    result['fresh_native_test']=False
    result['original_native_results_path']=receipt['path']
    result['original_native_results_sha256']=receipt['sha256']
    m.n.save(target,result)
    print('VERIFIED CACHE '+row['case_id']+' <- '+receipt['reused_case'],flush=True)
