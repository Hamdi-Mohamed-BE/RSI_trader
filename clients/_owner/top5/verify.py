"""Final integrity audit. Safe: never starts or edits MT5."""
import json,re,gzip,subprocess,hashlib
from datetime import datetime
from build import ROOT,REPO,CLIENT,sha,read
from renew import logic_fingerprints

def main():
    m=json.loads((ROOT/'manifest.json').read_text());files=list(CLIENT.iterdir())
    assert len(files)==7 and all(p.is_file() for p in files)
    assert sorted(p.suffix.lower() for p in files)==['.bat']+['.ex5']*5+['.html']
    assert all(sha(CLIENT/r['expert'])==r['ex5_sha256'] for r in m['entries'])
    assert all(sha(REPO/p)==h for p,h in m['source_hashes'].items()),'Original source changed'
    assert sha(ROOT/'ClientGuard.mqh')==m['guard_sha256']
    for row in m['entries']:
        assert re.search(r'\b0 errors, 0 warnings\b',read(ROOT/'build'/row['expert'].replace('.ex5','.log')))
    runs=[json.loads(p.read_text()) for p in (ROOT/'tests-native').glob('nw-*/run.json')]
    assert len(runs)==20 and all(r['audited'] and r['ok'] for r in runs)
    assert all(not r['journal_flags']['critical'] and not r['journal_flags']['init_failed'] for r in runs)
    assert all(float(re.search(r'[\d.]+',str(r['metrics']['history_quality']))[0])==100 for r in runs)
    assert len(json.loads((ROOT/'EXPIRY_VERIFICATION.json').read_text()))==5
    assert json.loads((ROOT/'GUARD_VERIFICATION.json').read_text())['native_harness_pass']
    script=ROOT/'installer.generated.ps1'
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'test_installer.ps1')],check=True)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'test_symbol_mapping.ps1')],check=True)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'test_auto_setup.ps1')],check=True)
    assert re.search(r'\b0 errors, 0 warnings\b',read(ROOT/'DetectBrokerSymbols.log'))
    subprocess.run(['cmd.exe','/c',str(CLIENT/'Install Top 5.bat'),'--validate'],check=True)
    html=(CLIENT/'Performance and Setup.html').read_text(encoding='utf-8')
    assert '__DATA__' not in html and '<script src=' not in html and 'fetch(' not in html
    assert 'C:\\Users\\' not in html and 'Password=' not in html
    d=json.loads((ROOT/'report-data.json').read_text());assert d['licence']==m['licence']
    for mode in ('fixed','balance'):
        for period in ('3m','6m'):
            values=d['datasets'][mode][period];parts=[values[r['slug']] for r in m['entries']]
            assert values['all']['trades']==sum(p['trades'] for p in parts)
            assert abs(values['all']['net_profit']-sum(p['net_profit'] for p in parts))<.02
            assert values['all']['equity_dd_pct'] is None
    days=(datetime.fromisoformat(m['licence']['expires_utc'])-datetime.fromisoformat(m['licence']['issued_utc'])).total_seconds()/86400
    assert days==30
    current_evidence=all(r['ex5_sha256']==next(e['ex5_sha256'] for e in m['entries'] if e['slug'] in r['case']) for r in runs)
    if not current_evidence:assert d.get('riskPolicyRevision') and 'PREVIOUS' in d['licenceEditionNote']
    out={'current_build_native_evidence':current_evidence,'historical_tests_apply_to_current_build':current_evidence,'customer_file_count':7,'compiled_eas':5,'clean_compilation':True,'native_benchmarks':20,'forced_expiry_runs':5,
       'native_guard_harness':True,'risk_audits':sum(r['risk_audits'] for r in runs),'history_quality':'100%',
       'licence_days':days,'expires_utc':m['licence']['expires_utc'],'compiled_account_binding':bool(m['licence']['bound_login']),
       'original_sources_unchanged':True,'installer_fixture_and_validation':'passed under Windows PowerShell',
       'symbol_mapping_fixtures':'passed; recipient broker acceptance still required','detector_sha256':sha(ROOT/'DetectBrokerSymbols.ex5'),
       'automatic_setup_preflight_fixtures':'passed; native restart/attachment acceptance not run',
       'normal_mt5_deployed':False,'recipient_interactive_demo_acceptance':'still required',
       'logic_fingerprints':logic_fingerprints(m),'delivery_hashes':{p.name:sha(p) for p in files}}
    (ROOT/'VERIFICATION.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
