"""Frozen native MT5 raw tests: 2020-2023 only. No live terminal/API writes."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,re,shutil,subprocess,time,sys
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
spec=importlib.util.spec_from_file_location('bb_native_shared',B/'Nasdaq Opening Candle Duration Comparison 2026-10-07/run.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
h=d.h; T=d.T; SRC=R/'EA/BollingerResearch.mq5'
CASES=[('momentum-middle-final',0,'Momentum — middle-band/session exit'),('momentum-2R-final',1,'Momentum — fixed 2R/session exit'),('contrarian-middle-final',2,'Contrarian — middle-band/session exit')]
INPUTS=dict(InpTimeframe='16385',InpBandsPeriod='20',InpBandsDeviation='2.0',InpATRPeriod='14',InpStopATR='2.0',InpRiskPercent='1.0',InpTargetR='2.0',
    InpStartNYMinutes='570',InpEndNYMinutes='958',InpServerUTCOffsetMinutes='0',InpBrokerCloseBufferSeconds='60',InpUseCashCalendar='true',InpMagic='2026100701',InpDeviationPoints='50',InpLogBars='true')
CALENDAR=json.loads((R/'CALENDAR.json').read_text())

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def status(msg,**kw):
    save(R/'status.json',dict(message=msg,utc=datetime.now(timezone.utc).isoformat(),**kw));print(msg,json.dumps(kw),flush=True)
def compile_ea():
    h.free(); began=time.time(); log=SRC.with_suffix('.compile.log')
    subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=h.text(log); assert '0 errors, 0 warnings' in body,body[-5000:]
    assert SRC.with_suffix('.ex5').stat().st_mtime>=began-2
    save(R/'BUILD.json',dict(source_sha256=sha(SRC),binary_sha256=sha(SRC.with_suffix('.ex5')),compiler='0 errors, 0 warnings',protocol_sha256=sha(R/'PROTOCOL.txt'),calendar_sha256=sha(R/'CALENDAR.json')))
    status('COMPILED research-only EA')

def session(ts):
    ny=pd.Timestamp(ts,tz='UTC').tz_convert('America/New_York')
    key=int(ny.strftime('%Y%m%d'));end=778 if key in CALENDAR['early_close_1300'] else 958
    return ny.weekday()<5 and key not in CALENDAR['closed'] and 570<=ny.hour*60+ny.minute<end

def run_case(name,variant,label):
    out=R/'native'/name;out.mkdir(parents=True,exist_ok=True)
    inputs=dict(INPUTS,InpVariant=str(variant)); build=json.loads((R/'BUILD.json').read_text())
    assert sha(SRC)==build['source_sha256'] and sha(SRC.with_suffix('.ex5'))==build['binary_sha256']
    manifest=dict(name=name,label=label,from_date='2020-01-01',end_exclusive='2024-01-01',symbol='USTEC',timeframe='H1',model=0,
        tick_mode='Generated every tick from historical M1 bars',delay_ms=150,deposit=10000,risk_percent=1,inputs=inputs,**build)
    mp=out/'manifest.json'
    if mp.exists():
        assert json.loads(mp.read_text())==manifest,'Frozen manifest changed'
        if (out/'results.json').exists(): return json.loads((out/'results.json').read_text())
    else:save(mp,manifest)
    h.free();empty=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert empty.is_dir() and not list(empty.glob('*.chr'))
    dest=T/'MQL5/Experts/AAA Research/Bollinger20261007';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SRC.with_suffix('.ex5'),dest/'BollingerResearch.ex5');assert sha(dest/'BollingerResearch.ex5')==build['binary_sha256']
    setname='bb20261007-'+name+'.set';body='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
    (out/'Parameters.set').write_text(body,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    reportdir=T/'reports/bollinger-20261007';reportdir.mkdir(parents=True,exist_ok=True);rp=reportdir/(name+'.htm')
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Bollinger20261007\\BollingerResearch
ExpertParameters={setname}
Symbol=USTEC
Period=H1
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=150
Optimization=0
FromDate=2020.01.01
ToDate=2024.01.01
ForwardMode=0
Report=reports\\bollinger-20261007\\{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    offsets={p:p.stat().st_size for p in h.logfiles()}; began=time.time();status('START '+name)
    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
    save(out/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(T/'terminal64.exe')))
    try:proc.wait(timeout=2700)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=20);raise RuntimeError('Owned isolated test timed out')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing fresh native report'
    assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|BB_ORDER_ERROR|BB_CLOSE_ERROR',journal,re.I),'Native runtime fault'
    summaries=set(re.findall(r'BB_SUMMARY\|order_errors=(\d+)\|close_errors=(\d+)\|size_skips=(\d+)',journal));assert summaries and all(x[0]=='0' and x[1]=='0' for x in summaries)
    actual=h._report_inputs(rp);assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'SET mismatch'
    from app.mt5_evidence_jobs import _metric,_number
    report=h._read_report(rp);assert '2020.01.01' in report and '2024.01.01' in report
    native=h._native_metrics(rp);native['equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
    trades=h._native_trades(rp,name);assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.03
    entries={};bars={};exits={}
    for line in journal.splitlines():
        if 'BB_ENTRY|' in line:
            v=line.split('BB_ENTRY|',1)[1].strip().split('|');assert len(v)==14
            key=(v[0],v[1]);entries[key]=dict(time=v[0].replace('.','-',2).replace(' ','T'),ticket=v[1],direction=int(v[2]),fill=float(v[3]),initial_sl=float(v[4]),initial_tp=float(v[5]),
                volume=float(v[6]),initial_risk_cash=float(v[7]),signal_close=float(v[8]),middle=float(v[9]),upper=float(v[10]),lower=float(v[11]),atr=float(v[12]),signal_time=v[13].replace('.','-',2).replace(' ','T'))
        if 'BB_BAR|' in line:
            v=line.split('BB_BAR|',1)[1].strip().split('|');assert len(v)==9
            current=pd.Timestamp(v[0].replace('.','-',2));signal=pd.Timestamp(v[1].replace('.','-',2));assert signal+pd.Timedelta(hours=1)<=current
            assert bool(int(v[8]))==session(current.isoformat())
            key=v[0];bars[key]=dict(time=current.isoformat(),signal_time=signal.isoformat(),close=float(v[2]),middle=float(v[3]),upper=float(v[4]),lower=float(v[5]),atr=float(v[6]),side=int(v[7]),session=bool(int(v[8])))
        if 'BB_EXIT|' in line:
            v=line.split('BB_EXIT|',1)[1].strip().split('|');assert len(v)==3
            exits[(v[0].replace('.','-',2).replace(' ','T'),v[2])]=v[1]
    assert len(entries)==len(trades) and len(bars)>20000,'Incomplete native trace'
    previous=None
    for t in trades:
        matches=[e for e in entries.values() if abs((pd.Timestamp(e['time'])-pd.Timestamp(t['open_time'])).total_seconds())<=2 and abs(e['fill']-t['open_price'])<.011 and e['direction']==(1 if t['side']=='Long' else -1)]
        assert len(matches)==1; e=matches[0];t.update(e)
        assert session(t['open_time']) and pd.Timestamp(t['signal_time'])+pd.Timedelta(hours=1)<=pd.Timestamp(t['open_time'])
        signal_direction=1 if t['signal_close']>t['upper'] else -1 if t['signal_close']<t['lower'] else 0
        assert signal_direction!=0 and e['direction']==(-signal_direction if variant==2 else signal_direction)
        assert previous is None or previous<=t['open_time'];previous=t['close_time']
        assert t['initial_risk_cash']>0
        t['net_R']=t['net_profit']/t['initial_risk_cash'];t['gross_R']=t['gross_profit']/t['initial_risk_cash']
        op=pd.Timestamp(t['open_time'],tz='UTC');cl=pd.Timestamp(t['close_time'],tz='UTC')
        assert pd.Timestamp('2020-01-01',tz='UTC')<=op<=cl<pd.Timestamp('2024-01-01',tz='UTC')
        t['open_ny']=op.tz_convert('America/New_York').isoformat();t['close_ny']=cl.tz_convert('America/New_York').isoformat()
        t['hold_hours']=(cl-op).total_seconds()/3600;t['boundary_exit']='end of test' in t['exit_comment'].lower()
        t['crossed_ny_session_date']=t['open_ny'][:10]!=t['close_ny'][:10]
        if t['boundary_exit']:t['exit_reason']='test boundary'
        elif t['exit_comment'].startswith('sl '):t['exit_reason']='hard stop'
        elif t['exit_comment'].startswith('tp '):t['exit_reason']='fixed 2R target'
        else:
            reasons=[(stamp,reason) for (stamp,ticket),reason in exits.items() if ticket==t['ticket'] and abs((pd.Timestamp(stamp)-pd.Timestamp(t['close_time'])).total_seconds())<=2]
            assert len(reasons)==1,(t['close_time'],t['ticket'],reasons)
            t['exit_reason']=reasons[0][1]
            t['exit_decision_time']=reasons[0][0]
        assert t['exit_reason']!='unknown',(t['close_time'],t['exit_comment'])
        if t['exit_reason']=='middle':
            stamp=t['exit_decision_time'].replace('-','.').replace('T',' ');b=bars[stamp]
            assert (b['close']<=b['middle'] if e['direction']>0 else b['close']>=b['middle']) if variant==0 else (b['close']>=b['middle'] if e['direction']>0 else b['close']<=b['middle'])
        if t['exit_reason']=='session':assert not session(t['close_time'])
    save(out/'trades.json',trades);pd.DataFrame(trades).to_csv(out/'trades.csv',index=False);save(out/'bar-checks.json',list(bars.values()))
    (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    for image in rp.parent.glob(name+'*.png'):shutil.copy2(image,out/image.name)
    summary=d.summary(trades,'2020-01-01','2024-01-01',native)
    summary['net_R']=sum(t['net_R'] for t in trades);summary['gross_R']=sum(t['gross_R'] for t in trades)
    summary['exit_reasons']={x:sum(t['exit_reason']==x for t in trades) for x in sorted(set(t['exit_reason'] for t in trades))}
    summary['crossed_session_dates']=sum(t['crossed_ny_session_date'] for t in trades)
    assert summary['crossed_session_dates']==0,'Unexpected session carryover: do not publish as session-flat strategy'
    result=dict(manifest=manifest,native=native,summary=summary,trades=trades,report_sha256=sha(rp),signal_checks=len(bars),seconds=round(time.time()-began,1),
        broker_sessions=sorted(set(re.findall(r'BB_SESSION[^\r\n]+',journal))),
        journal_history_notes=sorted(set(line.strip() for line in journal.splitlines() if re.search('history synchronized|history begins|generating based|real ticks|no history|gaps|ticks generated',line,re.I)))[:25])
    save(out/'results.json',result);status('DONE '+name,summary=summary,history_quality=native['history_quality']);return result

def main():
    held=d.lease()
    try:
        if sys.argv[1]=='compile':compile_ea()
        elif sys.argv[1]=='grid':
            rows=[]
            for name,v,label in CASES:
                rows.append(run_case(name,v,label));save(R/'RESULTS.json',rows)
            status('COMPLETE 3 preregistered raw native tests; no production changes')
        else:raise ValueError(sys.argv[1])
    finally:held.close()
if __name__=='__main__':main()
