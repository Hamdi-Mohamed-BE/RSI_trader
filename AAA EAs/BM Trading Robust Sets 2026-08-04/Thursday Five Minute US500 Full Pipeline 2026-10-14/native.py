"""Native tester-only proof for frozen clock rules; no live trading API calls."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,msvcrt,os,re,shutil,subprocess,time
import research as r
R=r.R;B=r.B;T=B/'_Backtests/MT5-DMC-20260811';COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files'
h=r.module('clock_native_helpers',B/'FTMO Exit Management Research 2026-09-27/run.py')
def read(p):
    b=p.read_bytes();return b.decode('utf-16') if b[:2] in [b'\xff\xfe',b'\xfe\xff'] else b.decode('utf-8-sig',errors='replace')
def run(name,c,start,end,model):
    out=R/'native'/name;out.mkdir(parents=True,exist_ok=True)
    if (out/'RESULT.json').exists():return json.loads((out/'RESULT.json').read_text())
    h.free();src=R/'ClockResearch.mq5';log=R/'compile.log';began=time.time()
    if not (R/'BUILD.json').exists():
        subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        assert log.exists() and '0 errors, 0 warnings' in read(log),read(log)[-4000:]
        assert src.with_suffix('.ex5').stat().st_mtime>=began-2
        r.save('BUILD.json',dict(source=r.sha(src),binary=r.sha(src.with_suffix('.ex5')),compiler=read(log)[-400:]))
    build=r.load_json('BUILD.json');assert r.sha(src)==build['source'] and r.sha(src.with_suffix('.ex5'))==build['binary']
    dest=T/'MQL5/Experts/AAA Research/Clock Study 20261014';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(src.with_suffix('.ex5'),dest/'ClockResearch.ex5')
    tag='clock-20261014-'+name;setname=tag+'.set';values=dict(InpWeekday=c['weekday'],InpEntryMinuteET=c['entry_minute_et'],InpHoldMinutes=c['hold_minutes'],InpSide=c['side'],InpLots=1.,InpTag=tag)
    body='\n'.join(f'{k}={v}' for k,v in values.items())+'\n';(out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
    header=read(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    rp=T/'reports/clock-study-20261014'/(name+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Clock Study 20261014\\ClockResearch
ExpertParameters={setname}
Symbol=US500
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={start.replace('-','.')}
ToDate={end.replace('-','.')}
Report=reports\\clock-study-20261014\\{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr'))
    before={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free()
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    r.save('native/'+name+'/OWNED-PROCESS.json',dict(pid=proc.pid,path=str(T/'terminal64.exe'),started_utc=r.utcnow(),model=model,source_sha=build['source'],final_candidate_sha=r.sha(R/'FINAL-CANDIDATE.json')))
    print(f'NATIVE START {name} model={model} {start} -> {end}',flush=True)
    while proc.poll() is None and time.time()-began<2400:time.sleep(10)
    if proc.poll() is None:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Own isolated tester timeout; live terminal untouched')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(before.get(p,0));journal+='\n'+str(p.relative_to(T))+'\n'+f.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,('No fresh report',journal[-4500:])
    assert not re.search(r'initialization failed|access violation|array out of range|zero divide|not enough money|stop out|start time changed',journal,re.I),journal[-5000:]
    assert all(h._same_setting(str(v),h._report_inputs(rp).get(k,'')) for k,v in values.items()),'Native input mismatch'
    metadata=h._native_metrics(rp);stats=json.loads((COMMON/(tag+'-stats.json')).read_text());assert stats['failures']==0 and stats['open_positions']==0,stats
    deals=[json.loads(x) for x in (COMMON/(tag+'-deals.jsonl')).read_text().splitlines() if x.strip()];positions={}
    for d in deals:positions.setdefault(d['position_id'],[]).append(d)
    trades=[]
    for pid,ds in positions.items():
        a=[d for d in ds if d['entry']==0];z=[d for d in ds if d['entry']==1];assert len(a)==1 and len(z)==1
        assert abs(a[0]['volume']-z[0]['volume'])<1e-8 and a[0]['volume']==1
        cash=sum(d['profit']+d['commission']+d['swap']+d['fee'] for d in ds);trades.append(dict(open_epoch=a[0]['epoch'],close_epoch=z[0]['epoch'],entry=a[0]['price'],exit=z[0]['price'],side=1 if a[0]['type']==0 else -1,net_usd=cash,fees=sum(d['commission']+d['swap']+d['fee'] for d in ds)))
    trades.sort(key=lambda x:x['close_epoch']);assert len(trades)==metadata['trades'];assert abs(sum(t['net_usd'] for t in trades)-(stats['balance']-10000))<.05
    eq=COMMON/(tag+'-equity.jsonl');(out/'equity.jsonl.gz').write_bytes(gzip.compress(eq.read_bytes(),mtime=0));(out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    stats['reported_equity_dd_pct']=h._native_metrics(rp)['max_drawdown_pct']
    quality=[line for line in journal.splitlines() if re.search('real ticks begin|real ticks.*absent|generated ticks|ticks.*generated|history quality|ticks.*synchronized|ticks generating|ticks modeled|real ticks discarded',line,re.I)]
    result=dict(name=name,config=c,start=start,end_exclusive=end,model=model,execution_delay_ms=150,metadata=metadata,stats=stats,trades=trades,quality_journal=quality,report_path=str(rp),source_sha=build['source'],same_data_server=False,server_disclosure='Isolated tester on Exness-MT5Trial16; API source on Exness-MT5Trial15. Reconcile quote/fill differences rather than assert identical server history.')
    r.save('native/'+name+'/RESULT.json',result);print('NATIVE DONE '+name+' '+json.dumps(metadata),flush=True);return result
def main():
    lock=r.load_json('FINAL-CANDIDATE.json');assert lock['protocol_sha256']==r.sha(R/'PROTOCOL.json')
    lease=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
    try:
        results=[]
        for name,c in [('candidate',lock['parameters']),('original',r.CONFIGS[r.ORIGINAL])]:results.append(run(name+'-OOS',c,*r.PROTO['oos'],4))
        r.save('NATIVE.json',results)
    finally:lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_UNLCK,1);lease.close()
if __name__=='__main__':main()
