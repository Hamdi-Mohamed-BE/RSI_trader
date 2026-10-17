"""One prospectively fixed DI-off source run in the isolated native tester only."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,inspect,json,msvcrt,os,subprocess,sys
R=Path(__file__).resolve().parent;B=R.parent;OLD=B/'FTMO Core3 vs Core4 Phase Timing 2026-10-16'
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('di_off_native_helpers',B/'ORB and Range Breakout RR05 Comparison 2026-10-08/run.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.R=R;n.START='2021.10.06';n.END='2026.10.06'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def cache_receipt(name):
    rows=[]
    for prefix in ('Bases','Tester/bases'):
        for kind in ('history','ticks'):
            folder=n.T/prefix/'Exness-MT5Trial16'/kind/'USTEC'
            for path in sorted(folder.rglob('*')):
                if path.is_file():rows.append(dict(path=str(path),bytes=path.stat().st_size,mtime_ns=path.stat().st_mtime_ns,sha256=sha(path)))
    assert rows
    save(R/name,dict(captured_utc=datetime.now(timezone.utc).isoformat(),files=rows,limitation='Current cache snapshots only; old DI-on run did not retain cache byte hashes, so archived versus fresh historical-data identity cannot be proven.'))
def processes():
    p=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    assert p.returncode==0,p.stderr
    q=json.loads(p.stdout) if p.stdout.strip() else []
    return q if isinstance(q,list) else [q]
def prepare():
    assert not (R/'NATIVE-RUN.json').exists()
    p=read(B/'Portfolio Long History All ORB05 2026-10-14/PLAN.json')
    cid=p['mappings']['ftmo']['nasdaq-5m-candle-momentum']
    row=copy.deepcopy(next(x for x in p['cases'] if x['case_id']==cid))
    assert row['input_settings']['InpRequireDIAgreement']=='true'
    before=copy.deepcopy(row['input_settings']);row['input_settings']['InpRequireDIAgreement']='false'
    differences=[k for k in before if before[k]!=row['input_settings'][k]]
    assert differences==['InpRequireDIAgreement']
    assert all(sha(f)==v for f,v in row['production_hashes'].items())
    assert n.T.resolve()!=Path('C:/Program Files/MetaTrader 5').resolve()
    profile=n.T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    n.available()
    cache_receipt('NATIVE-CACHE-BEFORE.json')
    deps=[Path(__file__),R/'NATIVE-CACHE-BEFORE.json',R/'ReadOnlyAudit.mqh',B/'ORB and Range Breakout RR05 Comparison 2026-10-08/run.py',B/'FTMO Exit Management Research 2026-09-27/run.py',B/'Portfolio Long History All ORB05 2026-10-14/PLAN.json',OLD/'FROZEN.json',OLD/'run.py',OLD/'INPUTS.json',OLD/'SOURCE-COVERAGE.json',OLD/'SUMMARY.json',OLD/'OUTCOMES.json']
    save(R/'NATIVE-PLAN.json',dict(prepared_utc=datetime.now(timezone.utc).isoformat(),source_period=[n.START,n.END],slice_period='2025-10-06 00 Europe/Prague to2026-10-06 00 Europe/Prague',source_case_id=cid,row=row,input_before=before,input_differences=differences,source_risk_percent=1.0,reason='Exact original source-ledger sizing normalization; actual replay source request remains0.5% then fixed50 guard.',tester=str(n.T),empty_profile=str(profile),agent_port=n.PORT,model=4,delay_ms=150,isolated=True,no_live_account_api=True,live_changes=False,optimization=False,terminal_processes_before=processes(),dependencies={str(f):sha(f) for f in deps},production_hashes=row['production_hashes'],math_engine_sha256=sha(R/'run.py'),old_math_engine_sha256=sha(OLD/'run.py')))
    assert sha(R/'run.py')==sha(OLD/'run.py'),'Portfolio mathematics must remain byte-identical'
    plan=R/'NATIVE-PLAN.json'
    save(R/'NATIVE-FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),before_native_outcomes=True,files={str(plan):sha(plan),**{str(f):sha(f) for f in deps}}))
    print(json.dumps(dict(native_plan=str(plan),plan_sha256=sha(plan),frozen_sha256=sha(R/'NATIVE-FROZEN.json'),tester=str(n.T),only_input_change=differences),indent=2),flush=True)
def verify():
    f=read(R/'NATIVE-FROZEN.json');assert all(sha(p)==v for p,v in f['files'].items())
    p=read(R/'NATIVE-PLAN.json');assert all(sha(p)==v for p,v in p['production_hashes'].items())
    return p
def run():
    p=verify();row=p['row'];n.available()
    source=inspect.getsource(n.run_case)
    replacements={
      "destination=T/'MQL5/Experts/AAA Research/RR05All20261008'":"destination=T/'MQL5/Experts/AAA Research/CoreDIoff20261016'",
      "Expert=AAA Research\\\\RR05All20261008\\\\{slug}":"Expert=AAA Research\\\\CoreDIoff20261016\\\\{slug}",
      "reports/rr05-all-20261008":"reports/core-dioff-20261016",
      "Report=reports\\\\rr05-all-20261008\\\\{tag}.htm":"Report=reports\\\\core-dioff-20261016\\\\{tag}.htm",
    }
    for a,b in replacements.items():
        assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
    exec(compile(source,str(R/'native_source.py')+'::isolated_names_only','exec'),n.__dict__)
    binary,build=n.build(row)
    result=n.run_case(row,'core-dioff-long-20261016',binary,build)
    assert result['inputs']['InpRequireDIAgreement']=='false'
    original=p['input_before']
    differences=[k for k in original if k in result['inputs'] and not n.h._same_setting(original[k],result['inputs'][k])]
    assert differences==['InpRequireDIAgreement'],differences
    after=processes()
    before={x['ProcessId'] for x in p['terminal_processes_before'] if x.get('ExecutablePath','').casefold()!=str(n.T/'terminal64.exe').casefold()}
    assert before <= {x['ProcessId'] for x in after},'Preexisting terminal disappeared; inspect but never restart/switch it'
    path=R/'native'/result['tag']/'results.json'
    cache_receipt('NATIVE-CACHE-AFTER.json')
    save(R/'NATIVE-RUN.json',dict(path=str(path),sha256=sha(path),input_differences=differences,live_processes_preserved=True,terminal_processes_after=after,source_only_DI_toggle=True,complete=True))
    verify()
    print('GENUINE DI-OFF NATIVE SOURCE COMPLETE; production and preexisting terminals preserved',flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['run']:
        with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lock:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            run()
    else:raise SystemExit('prepare | run')

