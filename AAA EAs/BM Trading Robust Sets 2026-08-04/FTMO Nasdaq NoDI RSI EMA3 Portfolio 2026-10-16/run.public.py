"""Publication template: explicit research-login environment input; original run.py remains private/hash-bound."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import csv, gzip, hashlib, importlib.util, io, json, msvcrt, os, re, shutil, subprocess, sys, time
R=Path(__file__).resolve().parent;B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('ftmo3_native_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
T=h.TESTER;COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
DEST=T/'MQL5/Experts/AAA Research/FTMO3_20261016'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def status(message,**v):save(R/'RUN_STATUS.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=message,**v));print(message,json.dumps(v),flush=True)
def verify_freeze():
    f=read(R/'FROZEN.json')
    assert all(sha(p)==digest for p,digest in f['files'].items()),'Frozen research input changed'
    assert all(sha(p)==digest for p,digest in f['production_hashes'].items()),'Production source/binary/SET changed'
    return read(R/'PLAN.json')
def lease():
    f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);return f
def ensure_free():
    h.free()
    body=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
    assert not any(':3010 ' in line and 'LISTENING' in line for line in body.splitlines()),'Research tester3010 occupied; no process stopped'
    empty=T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert empty.exists() and not list(empty.glob('*.chr')),'Research profile must contain zero live charts'
def compile_all():
    verify_freeze();ensure_free();build={}
    for name in ('SharedPortfolio','NasdaqDirect'):
        source=R/(name+'.mq5');log=R/(name+'.compile.log');began=time.time()
        subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        body=h.text(log);assert '0 errors, 0 warnings' in body,body[-7000:]
        assert source.with_suffix('.ex5').stat().st_mtime>=began-2
        build[name]=dict(source_sha256=sha(source),binary_sha256=sha(source.with_suffix('.ex5')),compile='0 errors, 0 warnings')
    save(R/'BUILD.json',build);print('COMPILED both frozen tester-only adapters',flush=True)
def rows(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding='utf-8-sig'))))
def required_research_login():
    value=os.environ.get('CALYX_RESEARCH_MT5_LOGIN','').strip()
    if not re.fullmatch(r'[1-9]\d{0,18}',value) or int(value)>2**63-1:
        raise RuntimeError('Set CALYX_RESEARCH_MT5_LOGIN explicitly to an authorized isolated research tester login; no default is provided.')
    return value
def case(row,start=None,trading_from=0):
    research_login=required_research_login()
    plan=verify_freeze();cfg=plan['config'];tag=row['tag'];start=start or cfg['start'];end=cfg['end_exclusive']
    direct=row.get('direct',False);name='NasdaqDirect' if direct else 'SharedPortfolio'
    binary=R/(name+'.ex5');assert read(R/'BUILD.json')[name]['binary_sha256']==sha(binary)
    primary=cfg['entries'][row['index']-1]['symbol'] if row['index'] else 'USTEC'
    period={5:'M5',16385:'H1',16388:'H4'}[cfg['entries'][row['index']-1]['timeframe']] if row['index'] else 'M5'
    inputs={'InpDirectTag':tag} if direct else dict(InpCase=str(row['index']),InpNasdaqDI=str(row['di']).lower(),InpChallenge=str(row['challenge']).lower(),InpPhase=str(row['phase']),InpTag=tag,InpTradingFromEpoch=str(trading_from))
    manifest=dict(tag=tag,start=start,end_exclusive=end,trading_from_epoch=trading_from,primary_symbol=primary,period=period,deposit=10000,leverage=15,model=4,execution_delay_ms=150,binary_sha256=sha(binary),config_sha256=sha(R/'CONFIG.json'),inputs=inputs,case=row)
    out=R/'native'/tag;out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():
        assert read(out/'manifest.json')==manifest,'Manifest mutation'
        if (out/'results.json').exists():return read(out/'results.json')
    else:save(out/'manifest.json',manifest)
    ensure_free();DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(binary,DEST/(tag+'.ex5'))
    setname='ftmo3-'+tag+'.set';body='\n'.join(k+'='+str(v) for k,v in inputs.items())+'\n'
    (out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
    report_dir=T/'reports/ftmo3-20261016';report_dir.mkdir(parents=True,exist_ok=True);rp=report_dir/(tag+'.htm')
    ini=out/'tester.ini';ini.write_text(f'''[Common]
Login={research_login}
Server=Exness-MT5Trial16
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port=3010
Expert=AAA Research\\FTMO3_20261016\\{tag}
ExpertParameters={setname}
Symbol={primary}
Period={period}
Deposit=10000
Currency=USD
Leverage=1:15
Model=4
ExecutionMode=150
Optimization=0
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
ForwardMode=0
Report=reports\\ftmo3-20261016\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    began=time.time();offsets={p:p.stat().st_size for p in h.logfiles()};status('START '+tag,start=start,end_exclusive=end)
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(T/'terminal64.exe')))
    try:proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated tester timeout only; no other process stopped')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as stream:stream.seek(offsets.get(p,0));journal+=stream.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing fresh native report'
    assert not re.search(r'initialization failed|start time changed|not enough history|stop out|margin call|access violation|array out of range|zero divide',journal,re.I),'Invalid native test'
    report=h._read_report(rp);actual=h._report_inputs(rp)
    assert start.replace('-','.') in report and end.replace('-','.') in report and primary in report
    assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'Wrong native inputs'
    from app.mt5_evidence_jobs import _metric,_number
    native=h._native_metrics(rp)
    native.update(equity_dd_pct=_number(_metric(report,'Equity Drawdown Relative')),balance_dd_pct=_number(_metric(report,'Balance Drawdown Relative')))
    suffixes=['equity','deals'] if direct else ['equity','deals','events','admissions','days','contracts','status']
    for suffix in suffixes:
        source=COMMON/f'FTMO3_20261016_{tag}-{suffix}.csv'
        assert source.exists() and source.stat().st_mtime>=began-2,('Missing fresh audit',suffix)
        shutil.copy2(source,out/(suffix+'.csv'))
    deals=rows(out/'deals.csv');cash=sum(sum(float(d[k]) for k in ('gross','commission','swap','fee')) for d in deals)
    assert abs(cash-native['net_profit'])<.031,(cash,native)
    (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    warnings={label:len(re.findall(pattern,journal,re.I)) for label,pattern in dict(invalid_stops='invalid stops',invalid_volume='invalid volume',market_closed='market closed',not_enough_money='not enough money',entry_reject='entry_rejected|N5EMA order rejected').items()}
    result=dict(manifest=manifest,native=native,seconds=round(time.time()-began,1),warnings=warnings,report_sha256=sha(rp),tick_notes=sorted(set(line.strip() for line in journal.splitlines() if re.search(r'real ticks begin|real ticks absent|ticks discarded|generated ticks',line,re.I)))[:50],raw_deals=len(deals),audit=re.findall(r'FTMO3_(?:COMPLETE|DIRECT_COMPLETE)[^\r\n]*',journal))
    save(out/'results.json',result);status('DONE '+tag,native=native,warnings=warnings);return result
def main():
    held=lease();action=sys.argv[1]
    try:
        if action=='compile':compile_all()
        elif action=='all':
            plan=verify_freeze();results=[]
            # Exact preregistered cases, no outcome-based selection or parameter changes.
            for row in plan['cases']:results.append(case(row))
            challenge=rows(R/'native/noDI-challenge/status.csv')[0]
            if int(challenge['status'])==1:
                passed=datetime.fromtimestamp(int(challenge['status_epoch']),timezone.utc).astimezone(ZoneInfo('Europe/Prague'))
                next_day=datetime.combine(passed.date()+timedelta(days=1),datetime.min.time(),tzinfo=ZoneInfo('Europe/Prague'))
                epoch=int(next_day.timestamp());end=datetime.fromisoformat(plan['config']['end_exclusive']).replace(tzinfo=timezone.utc)
                if next_day.astimezone(timezone.utc)<end:
                    start=next_day.astimezone(timezone.utc).date().isoformat();row=dict(tag='noDI-verification',index=0,di=False,challenge=True,phase=2)
                    save(R/'PHASE2-HANDOVER.json',dict(phase1_status=challenge,verification_start_utc=next_day.astimezone(timezone.utc).isoformat(),native_history_from_date=start,trading_from_epoch=epoch,assumption='Fresh account next Prague calendar day, not guaranteed official review time.'))
                    results.append(case(row,start,epoch))
            save(R/'RUNS.json',results);status('COMPLETE all preregistered native cases',cases=len(results))
        elif action=='case':case(next(row for row in verify_freeze()['cases'] if row['tag']==sys.argv[2]))
        else:raise ValueError(action)
    finally:held.close()
if __name__=='__main__':main()
