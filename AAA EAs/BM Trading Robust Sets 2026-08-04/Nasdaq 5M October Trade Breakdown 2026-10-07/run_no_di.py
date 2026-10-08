"""Same production binary and native window; only the DI input changes."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,importlib.util,json,re,shutil,subprocess,time
import pandas as pd

R=Path(__file__).resolve().parent; B=R.parent
spec=importlib.util.spec_from_file_location('october_shared',B/'Nasdaq Opening Candle Duration Comparison 2026-10-07/run.py')
d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
h=d.h; T=d.T
NAME='OctoberNoDI20261007'; OUT=R/'native'/NAME
OUT.mkdir(parents=True,exist_ok=True)

def main():
    held=d.lease()
    try:
        h.free()
        baseline=json.loads((R/'RESULTS.json').read_text())
        inputs=baseline['manifest']['inputs'].copy(); inputs['InpRequireDIAgreement']='false'
        assert d.sha(d.PROD)==baseline['manifest']['binary_sha256']
        diff={k for k in inputs if inputs[k]!=baseline['manifest']['inputs'][k]}
        assert diff=={'InpRequireDIAgreement'}
        manifest=dict(baseline['manifest'],name=NAME,inputs=inputs)
        d.save(OUT/'manifest.json',manifest)
        dest=T/'MQL5/Experts/AAA Research/OpeningDuration20261007'
        dest.mkdir(parents=True,exist_ok=True); shutil.copy2(d.PROD,dest/(NAME+'.ex5'))
        assert d.sha(dest/(NAME+'.ex5'))==manifest['binary_sha256']
        body='\n'.join(k+'='+v for k,v in inputs.items())+'\n'
        setname=NAME+'.set'
        (OUT/'Parameters.set').write_text(body,encoding='utf-8')
        (T/'MQL5/Profiles/Tester'/setname).write_text(body,encoding='utf-8')
        empty=T/'MQL5/Profiles/Charts/Calyx Research Empty'
        assert empty.is_dir() and not list(empty.glob('*.chr'))
        header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
        ini=OUT/'tester.ini'
        ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\OpeningDuration20261007\\{NAME}
ExpertParameters={setname}
Symbol=USTEC
Period=M5
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2026.10.01
ToDate=2026.10.08
ForwardMode=0
Report=reports\\opening-duration-20261007\\{NAME}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
        offsets={p:p.stat().st_size for p in h.logfiles()}; began=time.time()
        print('START DI-OFF native comparison',flush=True)
        si=subprocess.STARTUPINFO(); si.dwFlags|=subprocess.STARTF_USESHOWWINDOW; si.wShowWindow=0
        proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=si)
        d.save(OUT/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(T/'terminal64.exe')))
        try: proc.wait(timeout=900)
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait(timeout=20); raise RuntimeError('Owned isolated test timed out')
        journal=''
        for p in h.logfiles():
            if p.stat().st_mtime<began-2: continue
            with p.open('rb') as f: f.seek(offsets.get(p,0)); journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
        (OUT/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
        assert not re.search(r'initialization failed|not enough history|invalid volume|stop out|margin call|access violation|array out of range|zero divide|N5EMA order rejected',journal,re.I)
        rp=T/'reports/opening-duration-20261007'/(NAME+'.htm')
        assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2
        actual=h._report_inputs(rp)
        assert all(k in actual and h._same_setting(v,actual[k]) for k,v in inputs.items())
        from app.mt5_evidence_jobs import _metric,_number
        native=h._native_metrics(rp); rb=h._read_report(rp)
        native['equity_dd_pct']=_number(_metric(rb,'Equity Drawdown Relative'))
        trades=h._native_trades(rp,NAME); ords=d.orders(rp)
        assert len(trades)==native['trades']
        assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.03
        previous=None
        for t in trades:
            op=pd.Timestamp(t['open_time'],tz='UTC'); cl=pd.Timestamp(t['close_time'],tz='UTC')
            assert pd.Timestamp('2026-10-01',tz='UTC')<=op<=cl<pd.Timestamp('2026-10-07',tz='UTC')
            assert op.tz_convert('America/New_York').strftime('%H:%M')=='09:35'
            assert previous is None or previous<=t['open_time']; previous=t['close_time']
            t['open_ny']=op.tz_convert('America/New_York').isoformat(); t['close_ny']=cl.tz_convert('America/New_York').isoformat()
            t['hold_hours']=(cl-op).total_seconds()/3600
            t['boundary_exit']='end of test' in t['exit_comment'].lower()
            matches=[o for o in ords if o[0]==t['open_time'].replace('-','.').replace('T',' ') and o[10]==t['entry_comment']]
            assert len(matches)==1
            t['initial_sl']=_number(matches[0][6]); t['initial_tp']=_number(matches[0][7]); assert t['initial_tp']==0
            t['initial_stop_pct_from_fill']=abs(t['open_price']-t['initial_sl'])/t['open_price']*100
            assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.02
        assert len(set(t['open_ny'][:10] for t in trades))==len(trades)
        (OUT/'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
        d.save(OUT/'trades.json',trades); pd.DataFrame(trades).to_csv(OUT/'trades.csv',index=False)
        result=dict(manifest=manifest,native=native,summary=d.summary(trades,'2026-10-01','2026-10-07',native),trades=trades,report_sha256=d.sha(rp),
            stop_modify_failures=journal.count('N5EMA stop modification failed'),seconds=round(time.time()-began,1))
        d.save(OUT/'results.json',result); d.save(R/'NO-DI-RESULTS.json',result)
        print(json.dumps(dict(summary=result['summary'],native=native,trades=trades),indent=2),flush=True)
    finally: held.close()

if __name__=='__main__': main()
