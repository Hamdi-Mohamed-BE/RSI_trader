"""Immutable raw EAs over four requested windows, isolated native tester only."""
from pathlib import Path
import gzip,importlib.util,json,msvcrt,os,re,shutil,subprocess,time,sys
import pandas as pd

R=Path(__file__).resolve().parent; RAW=R.parent;B=RAW.parent
spec=importlib.util.spec_from_file_location('golden_original_raw',RAW/'run.py')
raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw);h=raw.h;T=raw.T
CONFIG=json.loads((R/'run-config.json').read_text());WINDOWS=CONFIG['raw_windows']
def save(p,v):raw.save(p,v)
def run(mode,phase):
    name,tf,slug,source,preset,_=raw.paths(mode);out=R/'native'/('raw-'+slug+'-'+phase);out.mkdir(parents=True,exist_ok=True)
    start,end=WINDOWS[phase];inputs=raw.params(preset);tag='golden-pipeline-raw-'+slug+'-'+phase+'-20261007'
    frozen={'mode':mode,'name':name,'window':[start,end],'source':raw.sha(source),'engine':raw.sha(RAW/'Golden Trio Engine.mqh'),'binary':raw.sha(source.with_suffix('.ex5')),'preset':raw.sha(preset),'config':raw.sha(R/'run-config.json')}
    if (out/'result.json').exists():
        result=json.loads((out/'result.json').read_text());assert result['frozen']==frozen;return result
    save(out/'manifest.json',frozen);h.free()
    destination=T/'MQL5/Experts/AAA Research/Golden Pipeline Raw 20261007';destination.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),destination/source.with_suffix('.ex5').name)
    setname=tag+'.set';shutil.copy2(preset,T/'MQL5/Profiles/Tester'/setname)
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini=out/'tester.ini';a=start.replace('-','.');b=end.replace('-','.')
    ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Golden Pipeline Raw 20261007\\{name}
ExpertParameters={setname}
Symbol=USTEC
Period={tf}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={a}
ToDate={b}
Report=reports\\golden-pipeline-20261007\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    rp=T/'reports/golden-pipeline-20261007'/(tag+'.htm');rp.parent.mkdir(parents=True,exist_ok=True)
    offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free()
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',{'pid':proc.pid,'started':began});print(f'RAW {name} {phase}: isolated native test started',flush=True)
    while proc.poll() is None and time.time()-began<2400:
        time.sleep(20);print(f'RAW {name} {phase}: {int(time.time()-began)}s',flush=True)
    if proc.poll() is None:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated test timed out')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert rp.exists() and rp.stat().st_mtime>=began-2,'No fresh native report'
    body=h._read_report(rp);assert a in body and b in body and 'USTEC' in body
    assert not re.search(r'initialization failed|start time changed|not enough history|invalid volume|access violation|array out of range|not enough money',journal,re.I),'Native data/initialisation/execution error'
    actual=raw.inputs(rp);assert all(h._same_setting(v,actual.get(k,'')) for k,v in inputs.items())
    shutil.copy2(rp,out/'report.htm')
    for suffix in ['decisions','equity','bars','sessions']:
        p=raw.COMMON/('golden-trio-'+slug+'-20261006-'+suffix+'.csv');assert p.stat().st_mtime>=began-2;shutil.copy2(p,out/(suffix+'.csv'))
    trades=h._native_trades(rp,name);native=h._native_metrics(rp)
    assert len(trades)==native['trades'] and abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.05
    from app.mt5_evidence_jobs import _metric,_number
    native['equity_dd_pct']=_number(_metric(body,'Equity Drawdown Relative'))
    m=raw.stats(trades,start,end);m['equity_dd']=native['equity_dd_pct']
    decisions=pd.read_csv(out/'decisions.csv',encoding='utf-16');sent=decisions[decisions.reason=='entry_sent']
    assert len(sent)==len(trades);assert ((sent.lots*sent.unit_loss)<=sent.risk_budget+1e-6).all()
    assert (pd.to_datetime(sent.epoch,unit='s',utc=True)>=pd.Timestamp(start,tz='UTC')).all()
    eq=pd.read_csv(out/'equity.csv',encoding='utf-16');assert abs(eq.balance.iloc[-1]-native['final_balance'])<.05
    result={'frozen':frozen,'name':name,'phase':phase,'from':start,'end_exclusive':end,'net_metrics':m,'native':native,'trades':trades,
      'first_tick_epoch':int(eq.epoch.iloc[0]),'last_tick_epoch':int(eq.epoch.iloc[-1]),'report_sha256':raw.sha(rp),'seconds':time.time()-began,
      'tick_notes':sorted(set(re.findall(r'USTEC\s*:\s*real ticks begin from[^\r\n]*',journal)))}
    save(out/'result.json',result);print('RAW COMPLETED '+name+' '+phase+': '+json.dumps(m),flush=True)
    records={}
    for p in (R/'native').glob('raw-*/result.json'):
        v=json.loads(p.read_text());records[v['name']+' '+v['phase']]={k:x for k,x in v.items() if k!='trades'}
    save(R/'RAW RESULTS.json',records)
    return result
if __name__=='__main__':
    with (B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        for mode in [1,3]:
            for phase in ['5Y','3Y','1Y','6M']:run(mode,phase)
