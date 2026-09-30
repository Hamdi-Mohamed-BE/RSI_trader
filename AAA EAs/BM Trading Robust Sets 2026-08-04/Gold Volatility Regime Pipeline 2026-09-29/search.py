"""Reproducible Gold-only native research; no normal terminal API or live orders."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv, gzip, hashlib, io, itertools, json, math, msvcrt, os, re, shutil, statistics, subprocess, sys, time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent; BASE=ROOT.parent; EA=ROOT/'EA'; OUT=ROOT/'native'; OUT.mkdir(exist_ok=True)
RAW=BASE/'Market Style Bots Raw 2026-09-29'; TESTER=BASE/'_Backtests/MT5-DMC-20260811'
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxGoldVol20260929'
os.environ['EA_STORE_DISABLE_MT5']='1'; sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report
FIELDS='tf entry offset stop sl rr trail start dist exit session direction filter day max_day max_pos reentry hold weekend flat fast slow hot persist train ema slope'.split()
DEFAULT=dict(zip(FIELDS,[60,0,.25,0,1.5,2,0,1,1.5,0,0,0,0,0,1,1,0,480,1,1,14,100,1.2,.55,252,50,5]))
DEV=('2021.09.27','2024.03.27'); VAL=('2024.03.27','2025.09.27'); RECENT=('2025.09.27','2026.09.27')
FLAGS='entry_fail close_fail modify_fail cancel_fail bad_risk boundary'.split()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def read(p):
    b=p.read_bytes(); return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(message,**kw):
    save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=message,**kw));print(message,kw,flush=True)
def free():
    cmd="Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,'Cannot verify terminal isolation'
    assert str(TESTER).lower() not in r.stdout.lower(),'Isolated tester occupied; no process touched'
    r=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert not any(':3000 ' in l and 'LISTENING' in l for l in r.stdout.splitlines()),'Tester agent port busy'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def parse_xml(p,cases):
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'}; headers=None; result=[]
    for row in ET.parse(p).getroot().findall('.//s:Row',ns):
        vals=[]
        for cell in row.findall('s:Cell',ns):
            i=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if i:
                while len(vals)<int(i)-1:vals.append('')
            d=cell.find('s:Data',ns);vals.append(''.join(d.itertext()) if d is not None else '')
        if 'Pass' in vals and 'InpCase' in vals:headers=vals;continue
        if not headers or len(vals)!=len(headers):continue
        rec=dict(zip(headers,vals))
        if not rec.get('InpCase','').isdigit():continue
        i=int(rec['InpCase']); assert 0<=i<len(cases)
        nums={}
        for k,v in rec.items():
            try:nums[k]=float(v.replace(' ',''))
            except ValueError:nums[k]=v
        result.append(dict(index=i,parameters=cases[i],native=nums))
    assert len(result)==len(cases)==len({r['index'] for r in result}),('Incomplete XML',len(result),len(cases),headers)
    return result
def trade_stats(trades,start,end):
    trades.sort(key=lambda t:(t['close_epoch'],t['position_id'])); ws=ls=wm=lm=0
    for t in trades:
        ws=ws+1 if t['net_profit']>0 else 0;ls=ls+1 if t['net_profit']<0 else 0;wm=max(wm,ws);lm=max(lm,ls)
    days=(datetime.strptime(end,'%Y.%m.%d')-datetime.strptime(start,'%Y.%m.%d')).days
    concurrent=maximum=0
    for _,change in sorted([(t['open_epoch'],1) for t in trades]+[(t['close_epoch'],-1) for t in trades]):concurrent+=change;maximum=max(maximum,concurrent)
    return dict(max_concurrent_positions=maximum,trades_per_month=len(trades)/(days/365.25*12),trades_per_calendar_day=len(trades)/days,
                max_win_streak=wm,max_loss_streak=lm,return_pct=sum(t['net_profit'] for t in trades)/100,
                max_actual_risk_pct=max([t['actual_risk']/t['requested_risk'] for t in trades if t['requested_risk']>0] or [0]),
                mean_net_R=statistics.mean([t['net_profit']/t['actual_risk'] for t in trades if t['actual_risk']>0]) if trades else 0)
def batch(name,cases,start,end,model=1,optimize=True,control=False,risk=1):
    folder=OUT/name;folder.mkdir(exist_ok=True)
    frozen=dict(symbol='XAUUSD',name=name,cases=cases,start=start,end=end,model=model,optimize=optimize,control=control,risk=risk,
                logic=sha(EA/'SearchLogic.mqh'),core=sha(EA/'RawCore.mqh'),protocol=sha(ROOT/'PROTOCOL.md'),warmup_days=180)
    assert sha(EA/'RawCore.mqh')==sha(RAW/'MarketStyles.mq5'),'Baseline changed'
    manifest=folder/'manifest.json'
    if manifest.exists():
        assert json.loads(manifest.read_text())==frozen,'Frozen batch changed: '+name
        if (folder/'results.json').exists():return json.loads((folder/'results.json').read_text())
    else:save(manifest,frozen)
    for attempt in range(120):
        try:free();break
        except AssertionError:
            if attempt==119:raise
            time.sleep(5)
    source='double Cases[]['+str(len(FIELDS))+']={\n'+',\n'.join('{'+','.join(str(c[f]) for f in FIELDS)+'}' for c in cases)+'\n};\n#include "SearchLogic.mqh"\n'
    # Mechanically generated case table; logic is separately versioned and frozen.
    src=EA/'Gold Volatility Search.mq5';src.write_text(source,encoding='utf-8');log=EA/'compile.log';began=time.time()
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=read(log);assert '0 errors, 0 warnings' in body,body[-5000:]
    assert src.with_suffix('.ex5').stat().st_mtime>=began-2
    for p in (src,src.with_suffix('.ex5'),log,EA/'RawCore.mqh',EA/'SearchLogic.mqh'):shutil.copy2(p,folder/p.name)
    dest=TESTER/'MQL5/Experts/AAA Research/Gold Vol Search 20260929';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src.with_suffix('.ex5'),dest/'Gold Volatility Search.ex5')
    tag='gv-'+name+'-'+digest(frozen)[:10]; start_date=datetime.strptime(start,'%Y.%m.%d'); warm=(start_date-timedelta(days=180)).strftime('%Y.%m.%d')
    vals=dict(InpCase=f'0||0||1||{len(cases)-1}||'+('Y' if optimize else 'N'),InpMode=2,InpControl=str(control).lower(),InpRiskPercent=str(risk),
              InpRR=2,InpSeed=290929,InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9294500)
    setname=tag+'.set';setbody='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
    (folder/setname).write_text(setbody,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
    header=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
    extension='.xml' if optimize else '.htm';rp=TESTER/'reports/gold-vol-search-20260929'/(tag+extension);rp.parent.mkdir(parents=True,exist_ok=True)
    ini=folder/'tester.ini';ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Gold Vol Search 20260929\\Gold Volatility Search
ExpertParameters={setname}
Symbol=XAUUSD
Period=M1
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization={1 if optimize else 0}
OptimizationCriterion=6
FromDate={warm}
ToDate={end}
ForwardMode=0
Report=reports\\gold-vol-search-20260929\\{tag+extension}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in logs()};began=time.time();free();status('START '+name,cases=len(cases),model=model)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup)
    save(folder/'owned-process.json',dict(pid=proc.pid,started=began,executable=str(TESTER/'terminal64.exe')))
    try:proc.wait(timeout=6*3600)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned research batch timeout')
    journal=''
    for p in logs():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,('Missing fresh successful report',journal[-2500:])
    fatal=re.findall(r'[^\n]*(?:initialization failed|start time changed|not enough history|access violation|critical error|array out of range|stop out)[^\n]*',journal,re.I)
    assert not fatal,('History/runtime failure',fatal[:6])
    (folder/(rp.name+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    if optimize:rows=parse_xml(rp,cases)
    else:
        actual=_report_inputs(rp);expected=vals|dict(InpCase=0,InpTradeFrom=int(start_date.replace(tzinfo=timezone.utc).timestamp()))
        assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items()),'Native inputs not equal to frozen inputs'
        rb=_read_report(rp);assert all(t in rb for t in ('XAUUSD',warm,end))
        rows=[dict(index=0,parameters=cases[0],metrics=_native_metrics(rp),
                   coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))]
    for row in rows:
        stem=tag+'-'+str(row['index']);p=COMMON/(stem+'-net.json');tp=COMMON/(stem+'-trades.csv')
        assert all(p.exists() and p.stat().st_mtime>=began-2 for p in (p,tp)),('Missing fresh ledger',stem)
        net=json.loads(p.read_text());trades=[{k:float(v) for k,v in t.items()} for t in csv.DictReader(io.StringIO(tp.read_text()))]
        assert len(trades)==net['trades'] and abs(sum(t['net_profit'] for t in trades)-net['net_profit'])<.02
        assert all(abs(t['volume']-t['closed_volume'])<1e-7 for t in trades),'Unclosed ledger'
        assert all(start_date.replace(tzinfo=timezone.utc).timestamp()<=t['open_epoch']<datetime.strptime(end,'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp() for t in trades),'Warmup/date leak'
        native_profit=row.get('native',{}).get('Profit',row.get('metrics',{}).get('net_profit'))
        assert native_profit is not None and abs(net['net_profit']-native_profit)<max(.15,len(trades)*.001),('Native/ledger mismatch',net,native_profit)
        net.update(trade_stats(trades,start,end));net['max_actual_risk_pct']*=risk/row['parameters']['max_pos']
        row.update(net=net,stage=name,start=start,end=end,model=model,binary_sha=sha(src.with_suffix('.ex5')),
                   parameters_sha=digest(row['parameters']),report_sha=sha(rp),clean=not any(net[k] for k in FLAGS))
        for suffix in ('net.json','trades.csv','signals.csv','trace.csv'):
            p=COMMON/(stem+'-'+suffix)
            if p.exists() and p.stat().st_mtime>=began-2:(folder/(str(row['index'])+'-'+suffix+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    save(folder/'results.json',rows);status('DONE '+name,cases=len(cases),seconds=round(time.time()-began,1));return rows
def dedupe(cases):return list({digest(c):c for c in cases}.values())
def patches(stage,b):
    if stage=='timeframe':return [dict(tf=v) for v in [1,3,5,15,30,60,240]]
    if stage=='entry':return [dict(entry=0),dict(entry=1)]+[dict(entry=e,offset=o) for e in [2,4] for o in [.1,.25,.5]]+[dict(entry=3,offset=o) for o in [1,3,5]]
    if stage=='stop':return [dict(stop=0,sl=v) for v in [.5,.75,1,1.5,2,3,4]]+[dict(stop=1,sl=v) for v in [.05,.1,.2]]+[dict(stop=2,sl=v) for v in [5,10,20]]+[dict(stop=v) for v in [3,4,5]]
    if stage=='trailing':return [dict(trail=0)]+[dict(trail=1,start=v) for v in [.5,1,1.5]]+[dict(trail=2,start=s,dist=d) for s in [.5,1,1.5,2] for d in [1,1.5,2]]+[dict(trail=3,dist=v) for v in [.05,.1,.2]]+[dict(trail=v) for v in [4,5,7]]+[dict(trail=6,dist=v) for v in [1.5,2,3]]
    if stage=='rr_exit':return [dict(exit=0,rr=v) for v in [.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+[dict(exit=1,trail=2,dist=v) for v in [1,1.5,2,3]]+[dict(exit=2),dict(exit=3,trail=0),dict(exit=4,trail=2,start=1),dict(exit=5)]
    if stage=='session':return [dict(session=v) for v in range(7)]
    if stage=='direction':return [dict(direction=v) for v in range(3)]
    if stage=='filters':return [dict(filter=v) for v in range(7)]
    if stage=='management':return [dict(day=v) for v in range(4)]+[dict(max_day=v) for v in [1,2,3]]+[dict(max_pos=1),dict(max_pos=2,max_day=max(2,b['max_day']))]+[dict(reentry=v) for v in [0,1]]+[dict(hold=v) for v in sorted(set([0,120,240,480,960,8*b['tf'],16*b['tf']]))]+[dict(weekend=v) for v in [0,1]]+[dict(flat=v) for v in [0,1]]
    if stage=='regime':return [dict(fast=v) for v in [7,14,28]]+[dict(slow=v) for v in [50,100,200]]+[dict(hot=v) for v in [1.1,1.2,1.3,1.5]]+[dict(persist=v) for v in [.45,.55,.65,.75]]+[dict(train=v) for v in [126,252]]+[dict(ema=v) for v in [20,50,100]]+[dict(slope=v) for v in [3,5,10]]
    raise ValueError(stage)
def capacity_valid(r):return r['parameters']['max_pos']==1 or (r['parameters']['max_day']>=2 and r['net'].get('max_concurrent_positions',0)>=2)
def eligible(r,minimum=60):return r['clean'] and r['net']['trades']>=minimum and r['net']['net_profit']>0 and r['net']['profit_factor']>=1.15
def neighborhood(b):
    axes=[]
    if b['stop'] in [0,1,2]:axes.append('sl')
    if b['exit'] in [0,4]:axes.append('rr')
    elif b['trail'] in [2,3,6]:axes.append('dist')
    if b['entry']>=2:axes.append('offset')
    if b['hold']>0:axes.append('hold')
    axes+=['hot','fast'];axes=list(dict.fromkeys(axes))[:3];cases=[]
    for factors in itertools.product([.8,1,1.2],repeat=len(axes)):
        c=b.copy()
        for key,factor in zip(axes,factors):c[key]=max(2,round(b[key]*factor)) if key in ['fast','hold'] else max(.81 if key=='hot' else .01,round(b[key]*factor,8))
        cases.append(c)
    return dedupe(cases),axes
def read_trades(name,index=0):return [{k:float(v) for k,v in t.items()} for t in csv.DictReader(io.StringIO(gzip.decompress((OUT/name/(str(index)+'-trades.csv.gz')).read_bytes()).decode()))]
def parity():
    r=batch('parity',[DEFAULT],*RECENT,4,False)[0]
    old=[{k:float(v) for k,v in t.items()} for t in csv.DictReader(io.StringIO(gzip.decompress((RAW/'native/gold-volatility-raw-1y-m4/trades.csv.gz').read_bytes()).decode()))]
    new=read_trades('parity');keys=['open_epoch','close_epoch','side','open_price','close_price','volume','net_profit','initial_sl','initial_tp']
    key=lambda t:tuple(round(t[k],6) for k in keys)
    ok=sorted(map(key,old))==sorted(map(key,new))
    check=dict(old_n=len(old),new_n=len(new),exact_trade_cash_parity=ok,fields=keys,old_net=sum(t['net_profit'] for t in old),new_net=sum(t['net_profit'] for t in new),clean=r['clean'])
    save(ROOT/'PARITY.json',check);assert ok and r['clean'],check;status('BASELINE PARITY PASSED',trades=len(new))
def search():
    assert json.loads((ROOT/'PARITY.json').read_text())['exact_trade_cash_parity']
    leaders=[DEFAULT];ledger=[];summary=[]
    for stage in ['timeframe','entry','stop','trailing','rr_exit','session','direction','filters','management','regime']:
        cases=dedupe(leaders+[b|p for b in leaders for p in patches(stage,b)])
        if stage not in ['management','regime']:
            rows=json.loads((OUT/stage/'results.json').read_text());assert [r['parameters'] for r in sorted(rows,key=lambda r:r['index'])]==cases
        else:rows=batch(stage+'-repair1',cases,*DEV)
        ledger.extend(rows);save(ROOT/'SEARCH RESULTS.json',ledger)
        ranked=sorted(rows,key=lambda r:r['net']['score'],reverse=True)
        clean=[r for r in ranked if r['clean'] and capacity_valid(r)];assert clean,'No execution-clean active-capacity candidates: '+stage
        leaders=[r['parameters'] for r in clean[:3]]
        summary.append(dict(stage=stage,cases=len(cases),leaders=clean[:3]));save(ROOT/'STAGES.json',summary)
    finalists=[r for r in ranked if eligible(r) and capacity_valid(r)][:3]
    if not finalists:
        save(ROOT/'VERDICT.json',dict(status='REJECTED_DEVELOPMENT',best=ranked[:3]));status('GOLD STOP: development gate failed');return
    save(ROOT/'DEVELOPMENT FINALISTS.json',finalists);valid=[];plateaus=[]
    for idx,leader in enumerate(finalists):
        b=leader['parameters'];cases,axes=neighborhood(b);neighbors=batch('plateau-repair1-'+str(idx),cases,*DEV)
        ledger.extend(neighbors);save(ROOT/'SEARCH RESULTS.json',ledger)
        positive=sum(r['net']['net_profit']>0 and r['clean'] for r in neighbors)/len(neighbors);median=statistics.median(r['net']['profit_factor'] for r in neighbors)
        plateau=dict(index=idx,axes=axes,positive_fraction=positive,median_pf=median,passed=len(axes)>=2 and positive>=2/3 and median>1)
        plateaus.append(plateau);save(ROOT/'PLATEAUS.json',plateaus)
        if not plateau['passed']:continue
        val=batch('validation-repair1-'+str(idx),[b],*VAL,4,False)[0]
        if eligible(val,30):valid.append(val)
    if not valid:
        save(ROOT/'VERDICT.json',dict(status='REJECTED_PLATEAU_OR_VALIDATION',development=finalists));status('GOLD STOP: plateau/validation gate failed');return
    # Validation ranking has no 60-position requirement: use the same score expression explicitly.
    best=max(valid,key=lambda r:(r['net']['profit_factor']-1)*math.sqrt(r['net']['trades'])/(1+r['net']['equity_dd_pct']/10))
    save(ROOT/'FROZEN FINAL.json',best);b=best['parameters']
    recent=batch('recent-frozen',[b],*RECENT,4,False)[0]
    if not eligible(recent,30):
        save(ROOT/'VERDICT.json',dict(status='REJECTED_RECENT_CONFIRMATION',validation=best,recent=recent));status('GOLD STOP: recent gate failed');return
    try:hold=batch('older-holdout',[b],'2019.09.27','2021.09.27',4,False)[0]
    except AssertionError as exc:
        save(ROOT/'VERDICT.json',dict(status='BLOCKED_OLDER_HISTORY',validation=best,recent=recent,error=str(exc)[:1000]));raise
    good=eligible(hold,30);save(ROOT/'VERDICT.json',dict(status='QUALIFIED_FOR_ROBUSTNESS' if good else 'REJECTED_OLDER_HOLDOUT',validation=best,recent=recent,holdout=hold))
    status('GOLD SEARCH COMPLETE',verdict='QUALIFIED_FOR_ROBUSTNESS' if good else 'REJECTED_OLDER_HOLDOUT',trials=len(ledger),unique=len({r['parameters_sha'] for r in ledger}))
def main():
    lease=TESTER/'gold-vol-research.lock'
    with lease.open('a+b') as handle:
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        try:
            cmd=sys.argv[1]
            if cmd=='smoke':batch('smoke',[DEFAULT],'2026.07.01','2026.07.08',4,False)
            elif cmd=='parity':parity()
            elif cmd=='search':search()
            elif cmd=='all':parity();search()
            else:raise ValueError(cmd)
        finally:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':main()
