"""Frozen, resumable native research only. Never controls the normal MT5 account."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, hashlib, importlib.util, itertools, json, os, re, shutil, subprocess, sys, time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;EA=ROOT/'EA';OUT=ROOT/'native-v2';OUT.mkdir(exist_ok=True)
RAW=BASE/'Liquidity Continuation Raw 2026-09-27';TESTER=BASE/'_Backtests/MT5-DMC-20260811'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path.insert(0,str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_report_inputs,_same_setting,_read_report,_metric,_number
FIELDS='tf entry offset stop sl rr trail start dist exit session direction filter day max_day max_pos reentry hold weekend flat atr ttl mask'.split()
DEFAULT=dict(zip(FIELDS,[5,0,.25,0,1,1,0,1,1.5,0,0,0,0,0,0,1,0,60,1,0,14,6,0]))
COMMON=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxLC20260928'
TARGETS=[('XAU','XAUUSD',2),('BTC','BTCUSD',0),('US30','US30',0)]
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def read(p):
    b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig',errors='replace')
def status(message,**kw):
    save(ROOT/'status.json',dict(utc=datetime.now(timezone.utc).isoformat(),message=message,**kw));print(message,kw,flush=True)
def free():
    cmd="Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    out=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
    assert str(TESTER).lower() not in out.lower(),'Isolated tester occupied; no process touched'
    out=subprocess.run(['netstat','-ano','-p','TCP'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout
    assert not any(':3000 ' in l and 'LISTENING' in l for l in out.splitlines()),'Tester agent port busy'
def logs():return list((TESTER/'logs').glob('*.log'))+list((TESTER/'Tester/logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))
def parse_xml(p,cases):
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};headers=None;result=[]
    for row in ET.parse(p).getroot().findall('.//s:Row',ns):
        vals=[]
        for cell in row.findall('s:Cell',ns):
            i=cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if i:
                while len(vals)<int(i)-1:vals.append('')
            data=cell.find('s:Data',ns);vals.append(''.join(data.itertext()) if data is not None else '')
        if 'Pass' in vals and 'InpCase' in vals:headers=vals;continue
        if not headers or len(vals)!=len(headers):continue
        rec=dict(zip(headers,vals))
        if not rec.get('InpCase','').isdigit():continue
        i=int(rec['InpCase']);assert 0<=i<len(cases)
        nums={}
        for k,v in rec.items():
            try:nums[k]=float(v.replace(' ',''))
            except ValueError:nums[k]=v
        result.append(dict(index=i,parameters=cases[i],native=nums))
    assert len(result)==len(cases)==len({r['index'] for r in result}),('Incomplete XML',len(result),len(cases),headers)
    return result
def batch(asset,symbol,strategy,name,cases,start,end,model=1,optimize=True,control=False):
    folder=OUT/(asset+'-'+name);folder.mkdir(exist_ok=True)
    frozen=dict(asset=asset,symbol=symbol,strategy=strategy,name=name,cases=cases,start=start,end=end,model=model,optimize=optimize,control=control,
                logic=sha(EA/'SearchLogic.mqh'),core=sha(EA/'RawCore.mqh'),protocol=sha(ROOT/'PROTOCOL.md'))
    assert sha(EA/'RawCore.mqh')==sha(RAW/'Liquidity.mq5'),'Raw core changed'
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
    src=EA/'Liquidity Search.mq5';src.write_text(source,encoding='utf-8');log=EA/'compile.log';began=time.time()
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    body=read(log);assert '0 errors, 0 warnings' in body,body[-4500:]
    assert src.with_suffix('.ex5').stat().st_mtime>=began-2
    for p in (src,src.with_suffix('.ex5'),log,EA/'RawCore.mqh',EA/'SearchLogic.mqh'):shutil.copy2(p,folder/p.name)
    dest=TESTER/'MQL5/Experts/AAA Research/Liquidity Search 20260928';dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src.with_suffix('.ex5'),dest/'Liquidity Search.ex5')
    tag='lcs-'+asset+'-'+name+'-'+digest(frozen)[:10]
    start_date=datetime.strptime(start,'%Y.%m.%d');warm=(start_date-timedelta(days=300)).strftime('%Y.%m.%d')
    vals=dict(InpCase=f'0||0||1||{len(cases)-1}||'+('Y' if optimize else 'N'),InpStrategy=strategy,InpEntry=0,InpControl=str(control).lower(),
              InpRiskPercent='1.0',InpTradeFrom=start+' 00:00:00',InpTag=tag,InpMagic=9278120)
    setname=tag+'.set';setbody='\n'.join(k+'='+str(v) for k,v in vals.items())+'\n'
    (folder/setname).write_text(setbody,encoding='utf-8');(TESTER/'MQL5/Profiles/Tester'/setname).write_text(setbody,encoding='utf-8')
    common=(BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
    extension='.xml' if optimize else '.htm';rp=TESTER/'reports/liquidity-search-20260928'/(tag+extension);rp.parent.mkdir(parents=True,exist_ok=True)
    ini=folder/'tester.ini';ini.write_text(common+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\Liquidity Search 20260928\\Liquidity Search
ExpertParameters={setname}
Symbol={symbol}
Period=M5
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
Report=reports\\liquidity-search-20260928\\{tag+extension}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    profile=TESTER/'MQL5/Profiles/Charts/Calyx Research Empty';assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets={p:p.stat().st_size for p in logs()};began=time.time();free();status('START '+asset+' '+name,cases=len(cases),model=model)
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup)
    try:proc.wait(timeout=6*3600)
    except subprocess.TimeoutExpired:
        proc.terminate();proc.wait(timeout=30);raise RuntimeError('Owned research batch timeout')
    journal=''
    for p in logs():
        if p.stat().st_mtime<began-2:continue
        with p.open('rb') as f:f.seek(offsets.get(p,0));journal+='\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le',errors='replace')
    (folder/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(),mtime=0))
    assert proc.returncode==0 and rp.exists() and rp.stat().st_mtime>=began-2,('Missing fresh successful report',journal[-2500:])
    fatal=re.findall(r'[^\n]*(?:initialization failed|start time changed|not enough history|access violation|critical error)[^\n]*',journal,re.I)
    assert not fatal,('History/init failure',fatal[:6])
    (folder/(rp.name+'.gz')).write_bytes(gzip.compress(rp.read_bytes(),mtime=0))
    if optimize:rows=parse_xml(rp,cases)
    else:
        actual=_report_inputs(rp);expected=vals|dict(InpCase=0,InpTradeFrom=int(start_date.replace(tzinfo=timezone.utc).timestamp()))
        assert all(k in actual and _same_setting(str(v),actual[k]) for k,v in expected.items())
        rb=_read_report(rp);assert all(t in rb for t in (symbol,warm,end))
        ledger=COMMON/(tag+'-ledger.json');assert ledger.exists() and ledger.stat().st_mtime>=began-2
        trades=json.loads(ledger.read_text());m=_native_metrics(rp)
        for t in trades:
            t.update(ea=tag,symbol=symbol,side='Long' if t['side_code']==1 else 'Short',
                     open_time=datetime.fromtimestamp(t['open_epoch'],timezone.utc).replace(tzinfo=None).isoformat(),
                     close_time=datetime.fromtimestamp(t['close_epoch'],timezone.utc).replace(tzinfo=None).isoformat())
            assert abs(t['volume']-t['closed_volume'])<1e-6,'Unclosed position in ledger'
        trades.sort(key=lambda t:(t['close_time'],t['position_id']))
        assert all(t['open_time']>=start_date.isoformat() for t in trades),'Warmup leak'
        assert abs(sum(t['net_profit'] for t in trades)-m['net_profit'])<max(.12,len(trades)*.01),'PnL parser mismatch'
        (folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
        rows=[dict(index=0,parameters=cases[0],metrics=m,report_sha=sha(rp),binary_sha=sha(src.with_suffix('.ex5')),
                   coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*',journal))))]
    for row in rows:
        p=COMMON/(tag+'-'+str(row['index'])+'.json')
        assert p.exists() and p.stat().st_mtime>=began-2,('Missing native net position metrics',p)
        row['net']=json.loads(p.read_text());row['stage']=name;row['asset']=asset;row['source_sha']=sha(src.with_suffix('.ex5'))
        shutil.copy2(p,folder/('net-'+str(row['index'])+'.json'))
    save(folder/'results.json',rows);status('DONE '+asset+' '+name,cases=len(cases),seconds=round(time.time()-began,1))
    return rows
def dedupe(cases):return list({digest(c):c for c in cases}.values())
def patches(stage,symbol):
    if stage=='timeframe':return [dict(tf=v) for v in [1,3,5,15,30,60,240,1440]]
    if stage=='entry':return [dict(entry=0),dict(entry=1)]+[dict(entry=e,offset=o) for e in [2,4] for o in [.1,.25,.5]]+[dict(entry=3,offset=o) for o in ([1,3,5] if symbol=='XAUUSD' else [25,50,100])]
    if stage=='stop':return [dict(stop=0,sl=v) for v in [.5,.75,1,1.5,2,3,4]]+[dict(stop=1,sl=v) for v in [.05,.1,.2]]+[dict(stop=2,sl=v) for v in ([5,10,20] if symbol=='XAUUSD' else [100,250,500] if symbol=='BTCUSD' else [25,50,100])]+[dict(stop=v) for v in [3,4,5]]
    if stage=='trailing':return [dict(trail=0)]+[dict(trail=1,start=v) for v in [.5,1,1.5]]+[dict(trail=2,start=s,dist=d) for s in [.5,1,1.5,2] for d in [1,1.5,2]]+[dict(trail=3,dist=v) for v in [.05,.1,.2]]+[dict(trail=v) for v in [4,5,7]]+[dict(trail=6,dist=v) for v in [1.5,2,3]]
    if stage=='rr_exit':return [dict(exit=0,rr=v) for v in [.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+[dict(exit=1,trail=2,dist=v) for v in [1,1.5,2,3]]+[dict(exit=2),dict(exit=3),dict(exit=4,trail=2,start=1)]
    if stage=='session':return [dict(session=v) for v in range(6)]
    if stage=='direction':return [dict(direction=v) for v in range(3)]
    if stage=='filters':return [dict(filter=v) for v in range(7)]
    if stage=='management':return [dict(day=v) for v in range(4)]+[dict(max_day=v) for v in range(4)]+[dict(max_pos=v) for v in [1,2]]+[dict(reentry=v) for v in [0,1]]+[dict(hold=v) for v in [0,15,30,60,120,240]]+[dict(weekend=0),dict(weekend=1),dict(flat=0),dict(flat=1)]
    if stage=='levels':return [dict(mask=v) for v in range(5)]+[dict(atr=v) for v in [7,14,28]]+[dict(ttl=v) for v in [3,6,12]]
    raise ValueError(stage)
def eligible(r,minimum=60):return r['net']['trades']>=minimum and r['net']['net_profit']>0 and r['net']['profit_factor']>=1.15

def neighborhood(b,strategy):
    # Perturb only dimensions that change this candidate's actual execution.
    axes=[]
    if b['stop'] in [0,1,2]:axes.append('sl')
    if b['exit'] in [0,4]:axes.append('rr')
    elif b['trail'] in [2,3,6]:axes.append('dist')
    if b['entry']>=2:axes.append('offset')
    if b['trail'] in [1,2,3,4,5,6]:axes.append('start')
    if b['hold']>0:axes.append('hold')
    if strategy in [1,2]:axes.append('ttl')
    if b['stop'] in [0,3,4,5] or b['trail'] in [2,6] or b['entry'] in [2,4] or b['filter'] in [5,6]:axes.append('atr')
    axes=list(dict.fromkeys(axes))[:3]
    # A degenerate candidate cannot claim a 2-D plateau; the caller rejects it
    # without aborting the other assets or inventing inactive dimensions.
    cases=[]
    for factors in itertools.product([.8,1,1.2],repeat=len(axes)):
        c=b.copy()
        for key,factor in zip(axes,factors):
            c[key]=max(2,round(b[key]*factor)) if key in ['atr','ttl'] else max(.01,round(b[key]*factor,8))
        cases.append(c)
    return dedupe(cases),axes
def parity():
    checks=[]
    for asset,symbol,strategy,name in [('XAU','XAUUSD',0,'touch'),('XAU','XAUUSD',1,'retest'),('BTC','BTCUSD',0,'touch'),('US30','US30',0,'touch')]:
        result=batch(asset,symbol,strategy,'parity-'+name,[DEFAULT],'2025.09.27','2026.09.27',4,False)[0]
        old=json.loads((RAW/f'native/{asset}-{name}-1y/trades.json').read_text())
        new=json.loads(gzip.decompress((OUT/f'{asset}-parity-{name}/trades.json.gz').read_bytes()))
        key=lambda t:(t['open_time'],t['close_time'],t['side'],round(t['open_price'],8),round(t['close_price'],8),round(t['volume'],6))
        ok=[key(t) for t in old]==[key(t) for t in new]
        check=dict(asset=asset,entry=name,old_n=len(old),new_n=len(new),entry_exit_volume_equal=ok,old_net=sum(t['net_profit'] for t in old),new_net=sum(t['net_profit'] for t in new))
        checks.append(check);save(ROOT/'PARITY.json',checks);assert ok,check
    for w,start in [('6m','2026.03.27'),('1y','2025.09.27'),('3y','2023.09.27'),('5y','2021.09.27')]:
        batch('XAU','XAUUSD',2,'combined-raw-'+w,[DEFAULT],start,'2026.09.27',4,False)
def search():
    checks=json.loads((ROOT/'PARITY.json').read_text());assert len(checks)==4 and all(c['entry_exit_volume_equal'] for c in checks)
    results=[];ledger=[]
    for asset,symbol,strategy in TARGETS:
        leaders=[DEFAULT]
        for stage in ['timeframe','entry','stop','trailing','rr_exit','session','direction','filters','management','levels']:
            cases=dedupe(leaders+[b|p for b in leaders for p in patches(stage,symbol)])
            rows=batch(asset,symbol,strategy,stage,cases,'2021.09.27','2024.03.27')
            ledger.extend(rows);save(ROOT/'SEARCH RESULTS.json',ledger)
            ranked=sorted(rows,key=lambda r:r['net']['score'],reverse=True)
            leaders=[r['parameters'] for r in ranked[:3]]
        finalists=[r for r in ranked if eligible(r)][:3]
        if not finalists:
            results.append(dict(asset=asset,status='REJECTED_DEVELOPMENT',best=ranked[:3]));save(ROOT/'FINALISTS.json',results);continue
        valid=[]
        for idx,leader in enumerate(finalists):
            b=leader['parameters'];cases,axes=neighborhood(b,strategy)
            save(ROOT/f'{asset}-plateau-{idx}-axes.json',dict(axes=axes,cases=len(cases)))
            if len(axes)<2:continue
            neighbors=batch(asset,symbol,strategy,f'plateau-{idx}',cases,'2021.09.27','2024.03.27');ledger.extend(neighbors);save(ROOT/'SEARCH RESULTS.json',ledger)
            pf=sorted(r['net']['profit_factor'] for r in neighbors);positive=sum(r['net']['net_profit']>0 for r in neighbors)/len(neighbors)
            if positive<2/3 or pf[len(pf)//2]<=1:continue
            val=batch(asset,symbol,strategy,f'validation-{idx}',[b],'2024.03.27','2025.09.27',4,False)[0]
            if eligible(val,30):valid.append(val)
        if not valid:
            results.append(dict(asset=asset,status='REJECTED_PLATEAU_OR_VALIDATION',development=finalists));save(ROOT/'FINALISTS.json',results);continue
        best=max(valid,key=lambda r:r['net']['score']);save(ROOT/f'{asset}-FROZEN-FINAL.json',best)
        recent=batch(asset,symbol,strategy,'recent-frozen',[best['parameters']],'2025.09.27','2026.09.27',4,False)[0]
        try:hold=batch(asset,symbol,strategy,'older-holdout',[best['parameters']],'2019.09.27','2021.09.27',4,False)[0]
        except AssertionError as exc:
            results.append(dict(asset=asset,status='BLOCKED_OLDER_HISTORY',validation=best,recent=recent,error=str(exc)[:1000]));save(ROOT/'FINALISTS.json',results);continue
        good=eligible(hold,30) and eligible(recent,30)
        results.append(dict(asset=asset,status='QUALIFIED_FOR_ROBUSTNESS' if good else 'REJECTED_FROZEN_CONFIRMATION',validation=best,recent=recent,holdout=hold))
        save(ROOT/'FINALISTS.json',results)
    status('SEARCH COMPLETE',trials=len(ledger),unique_configurations=len({digest(r['parameters'])+r['asset'] for r in ledger}),results=[dict(asset=r['asset'],status=r['status']) for r in results])
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='smoke':batch('XAU','XAUUSD',2,'smoke-ledger',[DEFAULT],'2026.07.01','2026.07.08',4,False)
    elif cmd=='parity':parity()
    elif cmd=='search':search()
    elif cmd=='all':parity();search()
