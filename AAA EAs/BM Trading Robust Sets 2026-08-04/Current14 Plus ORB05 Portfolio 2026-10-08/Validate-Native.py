"""Short native execution/allocation regression, not a performance study.

Only launches the dedicated offline portable tester with live trading disabled.
Never initializes a trading API, changes the running live terminal or sends orders there.
"""
from pathlib import Path
import gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,time
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('allocation_test_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);T=h.TESTER

def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def case(e,percent=None,di_off=False):
    tag=e['key']+('-PCT'+str(percent) if percent else '-USD200')+('-DI-OFF' if di_off else '')
    out=R/'NativeTests'/tag;out.mkdir(parents=True,exist_ok=True)
    values=dict(e['inputs'])
    values.update(InpPortfolioRiskMode='0' if percent else '1',InpPortfolioPercent=str(percent or .5),InpPortfolioFixedUSD='200.0')
    if di_off:values['InpRequireDIAgreement']='false'
    start='2026-09-21';end='2026-10-07';deposit=20000
    binary=R/e['expert']
    manifest=dict(inputs=values,binary_sha256=sha(binary),start=start,end_exclusive=end,deposit=deposit,currency='USD',model=4,delay_ms=150,live_trading=False)
    if (out/'manifest.json').exists():
        assert json.loads((out/'manifest.json').read_text())==manifest,'Stale test, preserve it and use a new case'
        if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
    save(out/'manifest.json',manifest);h.free()
    dest=T/'MQL5/Experts/AAA Research/Current14ORB05';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(binary,dest/(tag+'.ex5'))
    setname='current14-orb05-'+tag+'.set';body='\n'.join(k+'='+v for k,v in values.items())+'\n'
    (T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8');(out/'Parameters.set').write_text(body,encoding='utf-8')
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    reportdir=T/'reports/current14-orb05-20261008';reportdir.mkdir(exist_ok=True);rp=reportdir/(tag+'.htm')
    tf={1:'M1',5:'M5',15:'M15',30:'M30',60:'H1',240:'H4'}[e['period']]
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Current14ORB05\\{tag}
ExpertParameters={setname}
Symbol={e['canonical']}
Period={tf}
Deposit={deposit}
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
ForwardMode=0
Report=reports\\current14-orb05-20261008\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    began=time.time();offsets={p:p.stat().st_size for p in h.logfiles()}
    print('START isolated native allocation check '+tag,flush=True)
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',dict(pid=proc.pid,executable=str(T/'terminal64.exe')))
    try:proc.wait(timeout=900)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timeout')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing native report'
    assert not re.search(r'initialization failed|start time changed|not enough history|access violation|array out of range|zero divide|invalid stops|invalid volume|not enough money',journal,re.I),'Native runtime/init/order error'
    actual=h._report_inputs(rp)
    mismatches={k:(v,actual.get(k)) for k,v in values.items() if k not in actual or not h._same_setting(v,actual[k])}
    assert not mismatches,('Native preset did not load',mismatches)
    report=h._read_report(rp);assert start.replace('-','.') in report and end.replace('-','.') in report
    readings=re.findall(r'UNIVERSAL_RISK mode=(\d+) budget=([\d.]+) equity=([\d.]+) percent=([\d.]+) currency=(\w+)',journal)
    for mode,budget,equity,pct,currency in readings:
        target=float(equity)*percent/100 if percent else 200
        assert int(mode)==(0 if percent else 1) and currency=='USD'
        assert abs(float(budget)-target)<.000001,('FTMO clamp or wrong allocation',mode,budget,equity,pct)
    native=h._native_metrics(rp)
    if native['trades']:assert readings,'Trades without verified risk readings'
    (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    result=dict(case=tag,native_initialization_and_inputs=True,trade_count=native['trades'],risk_budget_readings=len(readings),allocation='percent-equity' if percent else 'USD200',deposit=deposit,seconds=round(time.time()-began,1),binary_sha256=sha(binary),live_account_access=False,performance_validation=False)
    save(out/'result.json',result);print('PASS '+tag+' trades='+str(native['trades'])+' budget_checks='+str(len(readings)),flush=True)
    return result

def main():
    lock=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try:
        package=json.loads((R/'Package.json').read_text());results=[]
        for e in package['entries']:results.append(case(e))
        for key,pct in [('nasdaq-5m-candle-momentum',2),('usdjpy-london-open-momentum',1.5)]:
            e=next(e for e in package['entries'] if e['key']==key);results.append(case(e,pct,True))
        assert sum(e['risk_budget_readings'] for e in results)>0
        save(R/'VALIDATION.json',dict(all_passed=True,cases=len(results),all_15_initialization_checked=True,no_live_account_access=True,not_a_performance_backtest=True,results=results))
        print('All isolated native allocation checks passed. Live terminal untouched.',flush=True)
    finally:lock.close()

if __name__=='__main__':main()
