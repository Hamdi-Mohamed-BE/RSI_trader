"""Frozen native entry-duration experiment; never accesses live account APIs."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, math, msvcrt, os, re, shutil, subprocess, sys, time
import numpy as np
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
spec=importlib.util.spec_from_file_location('duration_native_helper',B/'FTMO Exit Management Research 2026-09-27/run.py')
h=importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
T=h.TESTER
PROD=B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5'
PRESET=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
SOURCE=R/'OpeningDuration.mq5'
DEST=T/'MQL5/Experts/AAA Research/OpeningDuration20261007'
WINDOWS={'3m':('2026-07-07','2026-10-07'),'6m':('2026-04-07','2026-10-07'),'1y':('2025-10-07','2026-10-07')}
MINUTES=[5,1,3,10,15]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def status(s,**kw):
    save(R/'status.json',dict(message=s,utc=datetime.now(timezone.utc).isoformat(),**kw)); print(s,json.dumps(kw),flush=True)
def lease():
    f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b')
    f.seek(0); msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1); return f
def params():
    return dict(line.split('=',1) for line in PRESET.read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith(';'))
def compile_adapter():
    h.free(); began=time.time(); log=R/'OpeningDuration.compile.log'
    subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=h.text(log); assert '0 errors, 0 warnings' in body,body[-4000:]
    binary=SOURCE.with_suffix('.ex5'); assert binary.stat().st_mtime>=began-2
    save(R/'BUILD.json',dict(adapter_source=sha(SOURCE),adapter_binary=sha(binary),production_binary=sha(PROD),production_source=sha(PROD.with_suffix('.mq5')),preset=sha(PRESET),compile='0 errors, 0 warnings'))
    status('COMPILED research-only entry adapter')

def orders(report):
    from app.mt5_evidence_jobs import _clean
    text=h._read_report(report); a=text.lower().find('<b>orders</b>'); b=text.lower().find('<b>deals</b>'); rows=[]
    for body in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text[a:b],re.S|re.I):
        cells=[_clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',body,re.S|re.I)]
        if len(cells)>=11 and re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]): rows.append(cells)
    return rows
def summary(trades,start,end,native):
    pnl=np.array([t['net_profit'] for t in trades],dtype=float)
    wins=float(pnl[pnl>0].sum()); losses=float(-pnl[pnl<0].sum())
    mw=ml=w=l=0
    for t in sorted(trades,key=lambda t:t['close_time']):
        if t['net_profit']>0: w+=1; l=0
        elif t['net_profit']<0: l+=1; w=0
        else: w=l=0
        mw=max(mw,w); ml=max(ml,l)
    days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1)); daily=pd.Series(0.,index=days)
    for t in trades: daily.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
    denominator=(10000+daily.cumsum()).shift(1).fillna(10000); returns=daily/denominator
    sd=returns.std(ddof=1); sharpe=float(returns.mean()/sd*np.sqrt(365)) if sd>0 else None
    return dict(trades=len(trades),wins=int((pnl>0).sum()),losses=int((pnl<0).sum()),flats=int((pnl==0).sum()),
        win_rate=100*float((pnl>0).mean()) if len(pnl) else None,pf=wins/losses if losses else None,
        net=round(float(pnl.sum()),2),return_pct=float(pnl.sum())/100,
        floating_dd=native['equity_dd_pct'],daily_realized_sharpe=sharpe,max_win_streak=mw,max_loss_streak=ml,
        commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),
        boundary_exits=sum(t['boundary_exit'] for t in trades),boundary_net=round(sum(t['net_profit'] for t in trades if t['boundary_exit']),2),
        mean_hold_hours=float(np.mean([t['hold_hours'] for t in trades])) if trades else None)

def run_case(minutes,window,production=False,start=None,end=None,tag=None):
    start,end=(start,end) if start else WINDOWS[window]
    name=tag or f'{window}-M{minutes}'+('-PRODUCTION' if production else '')
    out=R/'native'/name; out.mkdir(parents=True,exist_ok=True)
    binary=PROD if production else SOURCE.with_suffix('.ex5')
    inputs=params(); inputs['InpAdaptivePortfolioControls']='false'
    assert inputs['InpRiskPercent']=='1.0' and inputs['InpRequireDIAgreement']=='true' and inputs['InpSignalTimeframe']=='5'
    if not production: inputs['InpOpeningCandleTimeframe']=str(minutes)
    manifest=dict(name=name,minutes=minutes,window=window,start=start,end_exclusive=end,production=production,
        symbol='USTEC',indicator_timeframe='M5',deposit=10000,risk_percent=1,model=4,delay_ms=150,
        binary_sha256=sha(binary),preset_sha256=sha(PRESET),protocol_sha256=sha(R/'PROTOCOL.txt'),inputs=inputs)
    mp=out/'manifest.json'
    if mp.exists():
        assert json.loads(mp.read_text())==manifest,'Frozen inputs changed'
        if (out/'results.json').exists(): return json.loads((out/'results.json').read_text())
    else: save(mp,manifest)
    h.free(); empty=T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert empty.is_dir() and not list(empty.glob('*.chr'))
    DEST.mkdir(parents=True,exist_ok=True); shutil.copy2(binary,DEST/(name+'.ex5'))
    assert sha(DEST/(name+'.ex5'))==manifest['binary_sha256']
    setname='ndc20261007-'+name+'.set'; body='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
    (out/'Parameters.set').write_text(body,encoding='utf-8'); (T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    reportdir=T/'reports/opening-duration-20261007'; reportdir.mkdir(parents=True,exist_ok=True)
    rp=reportdir/(name+'.htm'); a=start.replace('-','.'); b=end.replace('-','.')
    ini=out/'tester.ini'; ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\OpeningDuration20261007\\{name}
ExpertParameters={setname}
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={a}
ToDate={b}
ForwardMode=0
Report=reports\\opening-duration-20261007\\{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    pending=out/'journal.txt.gz'; owned=out/'owned-process.json'
    if pending.exists() and owned.exists() and rp.exists():
        began=json.loads(owned.read_text())['started']
        assert rp.stat().st_mtime>=began-2
        journal=gzip.decompress(pending.read_bytes()).decode('utf-8')
        status('RECONCILE completed native report '+name)
    else:
        offsets={p:p.stat().st_size for p in h.logfiles()}; began=time.time(); h.free()
        status('START '+name,from_date=start,end_exclusive=end)
        si=subprocess.STARTUPINFO(); si.dwFlags|=subprocess.STARTF_USESHOWWINDOW; si.wShowWindow=0
        proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
        save(owned,dict(pid=proc.pid,started=began,executable=str(T/'terminal64.exe')))
        try: proc.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait(timeout=20); raise RuntimeError('Owned isolated tester timeout: '+name)
        journal=''
        for p in h.logfiles():
            if p.stat().st_mtime<began-2: continue
            with p.open('rb') as f: f.seek(offsets.get(p,0)); journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
        pending.write_bytes(gzip.compress(journal.encode(),mtime=0))
        assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing native report'
    assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|N5EMA order rejected',journal,re.I),'Invalid native test'
    report=h._read_report(rp); assert all(x in report for x in [a,b,'USTEC','M5'])
    actual=h._report_inputs(rp)
    assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items()),'Wrong applied SET'
    from app.mt5_evidence_jobs import _metric,_number
    native=h._native_metrics(rp); native['equity_dd_pct']=_number(_metric(report,'Equity Drawdown Relative'))
    trades=h._native_trades(rp,name); assert len(trades)==native['trades']
    assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.03,'Net P&L did not reconcile'
    ords=orders(rp); previous=None
    for t in trades:
        op=pd.Timestamp(t['open_time'],tz='UTC'); cl=pd.Timestamp(t['close_time'],tz='UTC')
        assert op>=pd.Timestamp(start,tz='UTC') and cl<pd.Timestamp(end,tz='UTC')
        expected=f'09:{30+minutes:02d}'; assert op.tz_convert('America/New_York').strftime('%H:%M')==expected,'Wrong NY entry close'
        assert previous is None or previous<=t['open_time'],'Overlapping positions'
        previous=t['close_time']; t['open_ny']=op.tz_convert('America/New_York').isoformat(); t['close_ny']=cl.tz_convert('America/New_York').isoformat()
        t['hold_hours']=(cl-op).total_seconds()/3600; t['boundary_exit']='end of test' in t['exit_comment'].lower()
        key=t['open_time'].replace('-','.').replace('T',' ')
        matches=[o for o in ords if o[0]==key and o[10]==t['entry_comment']]; assert len(matches)==1
        t['initial_sl']=_number(matches[0][6]); t['initial_tp']=_number(matches[0][7])
        assert t['initial_tp']==0,'Unexpected TP'
        assert t['initial_sl']<t['open_price'] if t['side']=='Long' else t['initial_sl']>t['open_price'],'Wrong stop side'
        # Stop is calculated from the submission quote before the delayed fill.
        # Preserve genuine slippage instead of rejecting fast opening fills.
        t['initial_stop_pct_from_fill']=abs(t['open_price']-t['initial_sl'])/t['open_price']*100
        assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.02
    assert len(set(t['open_ny'][:10] for t in trades))==len(trades),'Duplicate NY date entry'
    checks=[]
    for line in journal.splitlines():
        if 'NDC_CHECK|' not in line: continue
        values=line.split('NDC_CHECK|',1)[1].split('|')
        if len(values)!=10: continue
        tf,now,signal,indicator,close,ema,atr,direction,quality,di=values
        current=pd.Timestamp(now); s=pd.Timestamp(signal); i=pd.Timestamp(indicator)
        assert s+pd.Timedelta(minutes=int(tf))<=current
        assert i+pd.Timedelta(minutes=5)<=current,'M5 indicator lookahead'
        assert int(direction)==(1 if float(close)>float(ema) else -1 if float(close)<float(ema) else 0)
        checks.append(dict(minutes=int(tf),at=now,signal_time=signal,indicator_time=indicator,close=float(close),ema=float(ema),atr=float(atr),side=int(direction),di_pass=bool(int(di))))
    if not production: assert len(checks)>0,'Missing native signal checks'
    save(out/'checks.json',checks); save(out/'trades.json',trades); pd.DataFrame(trades).to_csv(out/'trades.csv',index=False)
    (out/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    for image in rp.parent.glob(name+'*.png'): shutil.copy2(image,out/image.name)
    result=dict(manifest=manifest,native=native,summary=summary(trades,start,end,native),trades=trades,
        report_sha256=sha(rp),stop_modify_failures=journal.count('N5EMA stop modification failed'),
        tick_notes=sorted(set(line.strip() for line in journal.splitlines() if re.search('real ticks begin|real ticks absent|ticks discarded',line,re.I)))[:20],
        seconds=round(time.time()-began,1),signal_checks=len(checks))
    save(out/'results.json',result); status('DONE '+name,summary=result['summary'],history_quality=native['history_quality']); return result

def verify_parity():
    a=json.loads((R/'native/3m-M5-PRODUCTION/results.json').read_text()); b=json.loads((R/'native/3m-M5/results.json').read_text())
    fields=['open_time','close_time','side','volume','open_price','close_price','gross_profit','commission','swap','net_profit','initial_sl','initial_tp','exit_comment']
    assert [{k:t[k] for k in fields} for t in a['trades']]==[{k:t[k] for k in fields} for t in b['trades']],'Adapter 5M does not match production'
    assert a['summary']==b['summary'],'Metrics do not match production'
    save(R/'BASELINE-PARITY.json',dict(passed=True,period=WINDOWS['3m'],positions=len(a['trades']),fields=fields,production_binary=sha(PROD),adapter_binary=sha(SOURCE.with_suffix('.ex5'))))
    status('VERIFIED 5M adapter matches exact production trade-for-trade',positions=len(a['trades']))

def main():
    held=lease()
    if sys.argv[1]=='compile': compile_adapter()
    elif sys.argv[1]=='baseline': run_case(5,'3m',production=True)
    elif sys.argv[1]=='grid':
        build=json.loads((R/'BUILD.json').read_text()); assert build['adapter_binary']==sha(SOURCE.with_suffix('.ex5')) and build['production_binary']==sha(PROD)
        run_case(5,'3m',production=True); run_case(5,'3m'); verify_parity()
        rows=[]
        for window in WINDOWS:
            for minutes in MINUTES:
                row=run_case(minutes,window,production=(minutes==5)); rows.append(row); save(R/'RESULTS.json',rows)
        status('COMPLETE 15 native comparison runs; production unchanged')
    elif sys.argv[1]=='case': run_case(int(sys.argv[2]),sys.argv[3])
    else: raise ValueError(sys.argv[1])
    held.close()
if __name__=='__main__': main()
