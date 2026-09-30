import json,gzip,re,shutil,subprocess
from build import ROOT,TESTER,read,sha
import test_native as test
b=test.b

def main():
    assert not b.isolated_running() and not b.port_3000_busy()
    src=ROOT/'GuardHarness.mq5';log=ROOT/'GuardHarness.log'
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert re.search(r'\b0 errors, 0 warnings\b',read(log)),read(log)[-2000:]
    dest=TESTER/'MQL5/Experts/CalyxClientGuardTests';dest.mkdir(exist_ok=True);shutil.copy2(src.with_suffix('.ex5'),dest/'GuardHarness.ex5')
    b.ROOT=ROOT;b.OUT=ROOT/'tests-guard';b.OUT.mkdir(exist_ok=True);b.STATUS=b.OUT/'status.json'
    b.CONFIG.update(expert_dir=dest.name,expert_file='GuardHarness.ex5',period='M1',periods={'test':'2026.07.01'},end_date='2026.07.02',
      common_inputs={'InpMagic':'93095999'},variants={'guard':{'inputs':{}}})
    m=b.run_case('XAUUSD','guard','test')
    j=gzip.decompress((b.OUT/m['case']/'journal.txt.gz').read_bytes()).decode()
    assert 'HARNESS_PASS' in j and 'HARNESS_FAIL' not in j
    assert not m['journal_flags']['critical'] and not m['journal_flags']['init_failed']
    out={'native_harness_pass':True,'guard_sha256':sha(ROOT/'ClientGuard.mqh'),'tests':['expiry blocks entry','own pending cancelled','foreign pending untouched','foreign cancellation refused','SL modification after expiry','position close after expiry']}
    (ROOT/'GUARD_VERIFICATION.json').write_text(json.dumps(out,indent=2));print(out)
if __name__=='__main__':main()
