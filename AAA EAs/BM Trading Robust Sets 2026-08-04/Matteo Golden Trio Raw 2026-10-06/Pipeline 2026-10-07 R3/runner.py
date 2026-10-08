"""Isolated native tester batches; no MT5 account API, live chart, or live order calls."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,io,json,math,msvcrt,os,re,shutil,subprocess,time
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import build_engine,search_plan
R=Path(__file__).resolve().parent;RAW=R.parent;B=RAW.parent
spec=importlib.util.spec_from_file_location('original_golden',RAW/'run.py');raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
h=raw.h;T=raw.T;COMMON=raw.COMMON;CONFIG=json.loads((R/'run-config.json').read_text())
def safe(x):
    if isinstance(x,float) and not math.isfinite(x):return None
    if isinstance(x,dict):return {k:safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [safe(v) for v in x]
    if isinstance(x,np.generic):return safe(x.item())
    return x
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(safe(x),indent=2,allow_nan=False,default=str),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def status(message,**kw):save(R/'status.json',dict(message=message,utc=datetime.now(timezone.utc).isoformat(),**kw));print(message,json.dumps(kw),flush=True)
def lease():
    f=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b');f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);return f
def ledger(deals,allow_open=False):
    if len(deals)==0:return []
    rows=[]
    for pid,d in deals.groupby('position_id',sort=False):
        d=d.sort_values(['epoch','ticket']);a=d[d.entry==0];z=d[d.entry==1]
        assert set(d.entry).issubset({0,1}),'Unexpected netting/reversal deal'
        assert len(a)==1,'Missing/duplicate entry history'
        if len(z)==0 or abs(a.volume.sum()-z.volume.sum())>=1e-7:
            assert allow_open and z.volume.sum()<a.volume.sum(),'Unclosed position ledger'
            continue
        first=a.iloc[0]
        last=z.iloc[-1];p=float(d.profit.sum());fees=float(d.commission.sum()+d.swap.sum()+d.fee.sum())
        side='buy' if int(first.type)==0 else 'sell';entry=float(first.price)
        rows.append(dict(position_id=int(pid),open_epoch=int(first.epoch),close_epoch=int(last.epoch),
           open_time=pd.Timestamp(first.epoch,unit='s').isoformat(sep=' '),close_time=pd.Timestamp(last.epoch,unit='s').isoformat(sep=' '),
           side=side,volume=float(first.volume),closed_volume=float(z.volume.sum()),open_price=entry,
           close_price=float((z.price*z.volume).sum()/z.volume.sum()),initial_sl=float(first.initial_sl),initial_tp=float(first.initial_tp),
           profit=p,commission=float(d.commission.sum()),swap=float(d.swap.sum()),fee=float(d.fee.sum()),net_profit=p+fees,
           planned_price_risk=abs(entry-float(first.initial_sl)),exit_deals=len(z),reason=int(last.reason)))
    rows.sort(key=lambda t:(t['close_epoch'],t['position_id']))
    if not allow_open:assert abs(sum(t['net_profit'] for t in rows)-float((deals.profit+deals.commission+deals.swap+deals.fee).sum()))<1e-6
    return rows
def metrics(trades,start,end,dd=0,initial=10000):
    m=raw.stats(trades,start,end,initial);m['equity_dd']=dd
    # Include Sunday closures on their actual date, without silently dropping their cash flow.
    days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));daily=pd.Series(0.,index=days)
    for t in trades:daily.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
    previous=(initial+daily.cumsum()).shift(1).fillna(initial);r=daily/previous
    m['daily_calendar_sharpe']=float(r.mean()/r.std(ddof=1)*np.sqrt(365)) if r.std(ddof=1)>0 else None
    m['daily_balance_sharpe_basis']='weekday/252 legacy comparison; calendar/365 additionally includes weekend cash flows'
    return m
def xml_results(p,n):
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};header=None;result={}
    for row in ET.parse(p).getroot().findall('.//s:Row',ns):
        vals=[]
        for c in row.findall('s:Cell',ns):
            i=c.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if i:
                while len(vals)<int(i)-1:vals.append('')
            d=c.find('s:Data',ns);vals.append(''.join(d.itertext()) if d is not None else '')
        if 'Pass' in vals and 'InpCase' in vals:header=vals;continue
        if not header or len(vals)!=len(header):continue
        rec=dict(zip(header,vals))
        if rec.get('InpCase','').isdigit():result[int(rec['InpCase'])]=float(rec['Profit'].replace(' ',''))
    assert sorted(result)==list(range(n)),('Incomplete native case table',len(result),n)
    return result
def batch(name,cases,start,end,model=1,optimize=True,verbose=False,control=0,symbol='USTEC',risk=1):
    h.free();out=R/'native'/name;out.mkdir(parents=True,exist_ok=True);logic=build_engine.build()
    frozen=dict(name=name,cases=cases,start=start,end=end,model=model,optimize=optimize,verbose=verbose,control=control,
      engine_sha256=hashlib.sha256(logic.encode()).hexdigest(),config_sha256=sha(R/'run-config.json'),search_plan_sha256=sha(R/'SEARCH PLAN.json'),risk=risk)
    if symbol!='USTEC':frozen['symbol']=symbol
    manifest=out/'manifest.json'
    if manifest.exists():
        assert load(manifest)==frozen,'Frozen batch changed: '+name
        if (out/'results.json').exists():return load(out/'results.json')
    else:save(manifest,frozen)
    assert optimize or len(cases)==1
    table='double Cases[][24]={\n'+',\n'.join('{'+','.join(repr(float(c[f])) for f in search_plan.FIELDS)+'}' for c in cases)+'\n};\n'
    source=out/'GoldenSearch.mq5';source.write_text(table+'#include "Logic.mqh"\n',encoding='utf-8');(out/'Logic.mqh').write_text(logic,encoding='utf-8')
    log=out/'compile.log';began=time.time()
    subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=h.text(log);assert '0 errors, 0 warnings' in body,body[-5000:]
    binary=source.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
    dest=T/'MQL5/Experts/AAA Research/GoldenSearch20261007';dest.mkdir(parents=True,exist_ok=True);shutil.copy2(binary,dest/'GoldenSearch.ex5')
    tag='gtr-'+name+'-'+digest(frozen)[:8];setname=tag+'.set'
    vals=dict(InpCase=f'0||0||1||{len(cases)-1}||Y' if optimize else 0,InpTag=tag,InpVerbose=str(verbose).lower(),InpControl=control,InpRiskPct=risk)
    setbody='\n'.join(f'{k}={v}' for k,v in vals.items())+'\n';(out/'Parameters.set').write_text(setbody,encoding='utf-8');(T/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
    header=h.text(B/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ext='.xml' if optimize else '.htm';a=start.replace('-','.');b=end.replace('-','.');rp=T/'reports/golden-search-20261007'/(tag+ext);rp.parent.mkdir(parents=True,exist_ok=True)
    ini=out/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldenSearch20261007\\GoldenSearch
ExpertParameters={setname}
Symbol={symbol}
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization={1 if optimize else 0}
OptimizationCriterion=6
FromDate={a}
ToDate={b}
ForwardMode=0
Report=reports\\golden-search-20261007\\{tag+ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=T/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in h.logfiles()};began=time.time();h.free();status('START '+name,cases=len(cases),model=model,from_date=start,end_exclusive=end)
    proc=subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=T,creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json',dict(pid=proc.pid,started=began,terminal=str(T)))
    while proc.poll() is None and time.time()-began<14400:time.sleep(15)
    if proc.poll() is None:proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned isolated research timeout')
    journal=''
    for p in h.logfiles():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+=f.read().decode('utf-16-le',errors='replace')+'\n'
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,'Missing fresh successful native report'
    assert not re.search(r'initialization failed|start time changed|not enough history|access violation|array out of range|zero divide|some error after pass finished|not enough money|stop out',journal,re.I),'Native history/runtime/margin failure'
    (out/('report'+ext+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    profits=xml_results(rp,len(cases)) if optimize else {0:h._native_metrics(rp)['net_profit']}
    if not optimize:
        actual=raw.inputs(rp);assert all(h._same_setting(str(v),actual.get(k,'')) for k,v in vals.items()),'Wrong actual native inputs'
        body=h._read_report(rp);assert a in body and b in body and symbol in body
    records=[]
    for i,c in enumerate(cases):
        stem=tag+'-'+str(i);dp=COMMON/(stem+'-deals.csv');sp=COMMON/(stem+'-stats.csv')
        assert dp.exists() and sp.exists() and sp.stat().st_mtime>=began-2,('Missing fresh native pass ledger',stem)
        deals=pd.read_csv(dp);trades=ledger(deals,allow_open=True);native=pd.read_csv(sp).iloc[0].to_dict()
        closed_ids={t['position_id'] for t in trades};open_deals=deals[~deals.position_id.isin(closed_ids)]
        whole_cash=float((deals.profit+deals.commission+deals.swap+deals.fee).sum())
        assert abs(whole_cash-profits[i])<max(.05,len(trades)*.001),'Native all-deal cash parity'
        complete=len(open_deals)==0 and not native.get('open_position',0) and not native.get('pending_orders',0)
        if complete:assert abs(sum(t['net_profit'] for t in trades)-profits[i])<max(.05,len(trades)*.001),'Native whole-position cash parity'
        assert abs(native['net']-profits[i])<.02 and abs(native['balance']-10000-profits[i])<.02
        assert all(t['open_epoch']>=pd.Timestamp(start,tz='UTC').timestamp() for t in trades),'Boundary/warm-up leak'
        for suffix in ['deals','stats']+(['decisions','equity','bars','sessions','quotes'] if verbose else [])+(['anchor-bars'] if verbose and c['tf']==240 else []):
            p=COMMON/(stem+'-'+suffix+'.csv');assert p.stat().st_mtime>=began-2;(out/(str(i)+'-'+suffix+'.csv.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
        m=metrics(trades,start,end,float(native['equity_dd']));rec=dict(index=i,parameters=c,stage=name,start=start,end=end,model=model,metrics=m,native=native,clean=native['failures']==0 and complete,
           complete_positions=complete,open_position_ids=sorted(set(int(x) for x in open_deals.position_id)),all_deal_cash=whole_cash,
           report_sha256=sha(rp),binary_sha256=sha(binary),trades=trades,symbol=symbol,risk_pct=risk,
           tick_notes=sorted(set(re.findall(r'USTEC\s*:\s*real ticks begin from[^\r\n]*',journal))))
        records.append(rec)
    save(out/'results.json',records);status('DONE '+name,cases=len(cases),seconds=round(time.time()-began,1));return records
def score(r,minimum=30):
    m=r['metrics'];pf=m['pf'] or 0
    if not r['clean']:return -1e6
    if m['trades']<minimum:return -1000+m['trades']/100
    if m['net']<=0:return -1-abs(m['net'])/10000-m['equity_dd']/100
    return (pf-1)*math.sqrt(m['trades'])/(1+m['equity_dd']/10)
def slim(r):return {k:v for k,v in r.items() if k!='trades'}
def dedupe(cases):return list({digest(c):c for c in cases}.values())
