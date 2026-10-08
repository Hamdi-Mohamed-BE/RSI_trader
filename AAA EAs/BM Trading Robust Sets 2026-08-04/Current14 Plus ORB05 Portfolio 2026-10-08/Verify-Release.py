"""Read-only integrity/preservation audit and final local verification record."""
from pathlib import Path
import base64,hashlib,io,json,zipfile
R=Path(__file__).resolve().parent;B=R.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()
p=read(R/'Package.json');build=read(R/'BUILD.json');checksums=read(R/'Checksums.json')
old=read(B/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
assert {e['key'] for e in p['entries']}=={e['slug'] for e in old['entries']}|{'xau-orb-new-york-m30'}
assert len(p['entries'])==15 and len(set(e['magic'] for e in p['entries']))==15
assert len(p['orb_keys'])==3
assert all(float(e['inputs']['InpRewardRisk'])==.5 for e in p['entries'] if e['key'] in p['orb_keys'])
changed={'InpRiskPercent','InpRiskMode','InpAdaptivePortfolioControls','InpTesterOnly'}
for e in old['entries']:
    new=next(n for n in p['entries'] if n['key']==e['slug'])
    for k,v in e['inputs'].items():
        if k.startswith('FTMO') or k in changed or (k=='InpRewardRisk' and e['slug'] in p['orb_keys']):continue
        assert str(v)==new['inputs'][k],('Unrequested signal/exit change',e['slug'],k,v,new['inputs'][k])
for path,digest in p['original_hashes'].items():assert sha(Path(path).read_bytes())==digest,path
for path,digest in old['files'].items():assert sha((B/'FTMO Thirteen EA Deployment 2026-09-27/package'/path).read_bytes())==digest,path
for path,digest in checksums.items():assert sha((R/path).read_bytes())==digest,path
bat=Path(build['single_bat']);raw=bat.read_text(encoding='ascii')
assert max(map(len,raw.split('exit /b %CALYX_EXIT%')[0].splitlines()))<8191
data=base64.b64decode(raw.rsplit(':CALYX_PAYLOAD_V1',1)[1].strip(),validate=True)
assert sha(data)==build['payload_sha256'] and len(data)==build['payload_bytes']
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert set(z.namelist())==set(checksums)|{'Checksums.json'}
    for path,digest in checksums.items():assert sha(z.read(path))==digest,path
for e in p['entries']:
    log=R/e['source'].replace('.mq5','.compile.log');body=log.read_bytes().decode('utf-16')
    assert '0 errors, 0 warnings' in body
    assert sha((R/e['expert']).read_bytes())==sha((R/e['source']).with_suffix('.ex5').read_bytes())
tests=read(R/'TESTS.json');transaction=read(R/'TRANSACTION-TESTS.json');native=read(R/'VALIDATION.json')
assert tests['passed'] and transaction['passed'] and native['all_passed'] and native['cases']==17
assert all(x['binary_sha256']==sha((R/next(e['expert'] for e in p['entries'] if x['case'].startswith(e['key']+'-'))).read_bytes()) for x in native['results'])
record=dict(verified=True,unique_eas=15,orbs_05r=3,compiled_eas=15,compiler_errors=0,compiler_warnings=0,
    offline_checks=tests['checks'],transaction_checks=transaction['checks'],native_execution_cases=17,
    native_risk_readings=sum(x['risk_budget_readings'] for x in native['results']),
    original_sources_unchanged=len(p['original_hashes']),original_ftmo_package_files_unchanged=len(old['files']),
    bat_sha256=sha(bat.read_bytes()),payload_sha256=sha(data),single_bat_bytes=bat.stat().st_size,
    no_live_account_access=True,not_installed=True,not_pushed=True,not_a_performance_validation=True)
(R/'VERIFICATION.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,indent=2))
