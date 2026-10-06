"""Gold Trio full pipeline (PROTOCOL.md). Isolated tester only; no live terminal API or orders.

python search.py smoke | parity | search A|B|C | finish | all
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv, gzip, hashlib, io, itertools, json, math, msvcrt, os, re, shutil, statistics, subprocess, sys, time
import xml.etree.ElementTree as ET
import pandas as pd
from metrics import stats

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent.parent
EA = ROOT / 'EA'
OUT = ROOT / 'native'
OUT.mkdir(exist_ok=True)
RAW = ROOT.parent
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxGoldSpeedSearch20261005'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number  # noqa: E402

FIELDS = 'module tf entry offset stop sl rr trail start dist exit session direction filter day max_day hold flat season p1 p2 p3 p4 fast speed volavg adx'.split()
RAWCASE = {
 'A': dict(zip(FIELDS,[0,240,0,0,0,2.5,0,2,1,0,0,0,0,0,0,0,0,0,0,24,.5,100,1,6,1,50,20])),
 'B': dict(zip(FIELDS,[1,60,0,0,0,2,2.5,2,1,0,0,0,0,0,0,0,0,0,1,480,60,.1,50,0,0,50,20])),
 'C': dict(zip(FIELDS,[2,1440,0,0,0,2,0,0,1,0,0,0,0,0,0,0,0,0,0,-1,2,0,0,0,0,50,20])),
}
DEV=('2021.10.05','2024.03.29')
VAL=('2024.04.05','2025.09.28')
HOLD=('2019.10.05','2021.09.27')
RECENT=('2025.10.05','2026.10.05')
WEB={'3m':('2026.07.05','2026.10.05'),'6m':('2026.04.05','2026.10.05'),'1y':RECENT,'3y':('2023.10.05','2026.10.05'),'5y':('2021.10.05','2026.10.05')}
MIN_DEV={'A':30,'B':20,'C':12}
MIN_OOS={'A':30,'B':20,'C':12}
FAIL_KEYS = ['entry_fail', 'close_fail', 'modify_fail', 'cancel_fail', 'bad_risk']
MAGIC = 1005040


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, allow_nan=False, default=str), encoding='utf-8')


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()


def read(p):
    b = p.read_bytes()
    return b.decode('utf-16') if b[:2] in (b'\xff\xfe', b'\xfe\xff') else b.decode('utf-8-sig', errors='replace')


def status(message, **kw):
    save(ROOT / 'status.json', dict(utc=datetime.now(timezone.utc).isoformat(timespec='seconds'), message=message, **kw))
    print(datetime.now().strftime('%H:%M:%S'), message, json.dumps(kw, default=str), flush=True)


def free():
    cmd = "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"
    r = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode == 0, 'Cannot verify terminal isolation'
    assert str(TESTER).lower() not in r.stdout.lower(), 'Isolated tester occupied; no process touched'
    r = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert not any(':3000 ' in l and 'LISTENING' in l for l in r.stdout.splitlines()), 'Tester agent port busy'


def logs():
    return list((TESTER / 'logs').glob('*.log')) + list((TESTER / 'Tester/logs').glob('*.log')) + list((TESTER / 'Tester').glob('Agent-*/logs/*.log'))


def parse_xml(p, n):
    ns = {'s': 'urn:schemas-microsoft-com:office:spreadsheet'}
    headers, result = None, {}
    for row in ET.parse(p).getroot().findall('.//s:Row', ns):
        vals = []
        for cell in row.findall('s:Cell', ns):
            i = cell.attrib.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
            if i:
                while len(vals) < int(i) - 1:
                    vals.append('')
            d = cell.find('s:Data', ns)
            vals.append(''.join(d.itertext()) if d is not None else '')
        if 'Pass' in vals and 'InpCase' in vals:
            headers = vals
            continue
        if not headers or len(vals) != len(headers):
            continue
        rec = dict(zip(headers, vals))
        if not rec.get('InpCase', '').isdigit():
            continue
        result[int(rec['InpCase'])] = float(rec.get('Profit', 'nan').replace(' ', ''))
    assert sorted(result) == list(range(n)), ('Incomplete optimisation XML', len(result), n)
    return result


def to_date(end):
    return end  # MT5 ToDate is exclusive, matching immutable raw runner.


def ledger(stem):
    tp = COMMON / (stem + '-trades.csv')
    return pd.read_csv(tp) if tp.exists() else None


def batch(name, cases, start, end, model=1, optimize=True, control=False, retry=False, warmup=180, slots=None, symbol='XAUUSD', risk=1.0):
    """Runs a case table natively. optimize=True: one pass per case (complete optimiser over InpCase).
    optimize=False: one single test with slots (list of up to 3 case indices) running together."""
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    frozen = dict(name=name, cases=cases, start=start, end=end, model=model, optimize=optimize, control=control, retry=retry,
                  warmup=warmup, slots=slots, symbol=symbol, risk=risk, logic=sha(EA / 'Logic.mqh'), protocol=sha(ROOT / 'PROTOCOL.md'))
    manifest = folder / 'manifest.json'
    if manifest.exists():
        assert load(manifest) == frozen, 'Frozen batch changed: ' + name
        if (folder / 'results.json').exists():
            return load(folder / 'results.json')
    else:
        save(manifest, frozen)
    for attempt in range(240):
        try:
            free()
            break
        except AssertionError:
            if attempt == 239:
                raise
            time.sleep(5)
    table = 'double Cases[][' + str(len(FIELDS)) + ']={\n' + ',\n'.join('{' + ','.join(repr(float(c[f])) for f in FIELDS) + '}' for c in cases) + '\n};\n'
    src = EA / 'GoldSpeedSearch.mq5'
    src.write_text('#property strict\n#property version "1.00"\n#property description "Tester-only Gold Trio search EA (generated case table)."\n' + table + '#include "Logic.mqh"\n', encoding='utf-8')
    log = EA / 'compile.log'
    began = time.time()
    subprocess.run(f'"{TESTER / "metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    body = read(log)
    assert '0 errors, 0 warnings' in body, body[-4000:]
    ex5 = src.with_suffix('.ex5')
    assert ex5.stat().st_mtime >= began - 2
    for p in (src, ex5, log, EA / 'Logic.mqh'):
        shutil.copy2(p, folder / p.name)
    dest = TESTER / 'MQL5/Experts/AAA Research/GoldSpeedSearch20261005'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ex5, dest / 'GoldSpeedSearch.ex5')
    tag = 'gsp-' + name + '-' + digest(frozen)[:10]
    sdate = datetime.strptime(start, '%Y.%m.%d')
    warm = (sdate - timedelta(days=warmup)).strftime('%Y.%m.%d')
    todate = to_date(end)
    if optimize:
        vals = dict(InpCase=f'0||0||1||{len(cases) - 1}||Y', InpCase2=-1, InpCase3=-1)
    else:
        sl = (slots or [0]) + [-1, -1]
        vals = dict(InpCase=sl[0], InpCase2=sl[1], InpCase3=sl[2])
    vals |= dict(InpControl=str(control).lower(), InpRetryClosed=str(retry).lower(), InpRiskPercent=risk, InpSeed=20261005,
                 InpTradeFrom=start + ' 00:00:00', InpTag=tag, InpMagic=MAGIC)
    setname = tag + '.set'
    setbody = '\n'.join(f'{k}={v}' for k, v in vals.items()) + '\n'
    (folder / setname).write_text(setbody, encoding='utf-8')
    (TESTER / 'MQL5/Profiles/Tester' / setname).write_text(setbody, encoding='utf-8')
    header = read(BASE / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ext = '.xml' if optimize else '.htm'
    rp = TESTER / 'reports/gold-speed-search-20261005' / (tag + ext)
    rp.parent.mkdir(parents=True, exist_ok=True)
    ini = folder / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldSpeedSearch20261005\\GoldSpeedSearch
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
FromDate={warm}
ToDate={todate}
ForwardMode=0
Report=reports\\gold-speed-search-20261005\\{tag + ext}
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    profile = TESTER / 'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    offsets = {p: p.stat().st_size for p in logs()}
    began = time.time()
    free()
    status('START ' + name, cases=len(cases), model=model, optimize=optimize, window=f'{start}->{end}')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    proc = subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=TESTER,
                            creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
    save(folder / 'owned-process.json', dict(pid=proc.pid, started=began, executable=str(TESTER / 'terminal64.exe')))
    try:
        proc.wait(timeout=4 * 3600)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=30)
        raise RuntimeError('Owned research batch timeout')
    journal = ''
    for p in logs():
        if p.stat().st_mtime < began - 2:
            continue
        with p.open('rb') as f:
            f.seek(offsets.get(p, 0))
            journal += '\n' + str(p.relative_to(TESTER)) + '\n' + f.read().decode('utf-16-le', errors='replace')
    (folder / 'journal.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert proc.returncode == 0 and rp.exists() and rp.stat().st_mtime >= began - 2, ('Missing fresh successful report', journal[-2500:])
    fatal = re.findall(r'[^\n]*(?:initialization failed|start time changed|not enough history|access violation|critical error|array out of range|zero divide|some error after pass finished)[^\n]*', journal, re.I)
    assert not fatal, ('History/runtime failure', fatal[:6])
    stopouts = len(re.findall(r'stop out|margin call', journal, re.I))
    (folder / (rp.name + '.gz')).write_bytes(gzip.compress(rp.read_bytes(), mtime=0))
    t0 = datetime.strptime(start, '%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()
    if optimize:
        profits = parse_xml(rp, len(cases))
        indices = list(range(len(cases)))
        native_metrics = None
    else:
        actual = _report_inputs(rp)
        expected = {k: v for k, v in vals.items()} | dict(InpTradeFrom=int(t0))
        assert all(k in actual and _same_setting(str(v), actual[k]) for k, v in expected.items()), 'Native inputs differ from frozen inputs'
        rb = _read_report(rp)
        assert all(x in rb for x in (symbol, warm, todate))
        native_metrics = _native_metrics(rp)
        native_metrics['equity_dd_pct'] = _number(_metric(rb, 'Equity Drawdown Relative'))
        profits = {0: native_metrics['net_profit']}
        indices = [0]
    rows = []
    for i in indices:
        stem = f'{tag}-{i if optimize else vals["InpCase"]}'  # the EA names files after the first slot's case index
        nj, tp = COMMON / (stem + '-net.json'), COMMON / (stem + '-trades.csv')
        assert nj.exists() and tp.exists() and nj.stat().st_mtime >= began - 2, ('Missing fresh ledger', stem)
        net = json.loads(nj.read_text())
        d = pd.read_csv(tp)
        assert len(d) == net['trades'] and abs(d.net_profit.sum() - net['net_profit']) < .02, ('Ledger mismatch', stem)
        assert (abs(d.volume - d.closed_volume) < 1e-7).all(), 'Unclosed ledger ' + stem
        assert (d.open_epoch >= t0).all(), 'Warm-up leak ' + stem
        assert abs(net['net_profit'] - profits[i]) < max(.15, len(d) * .001), ('Native/ledger mismatch', stem, net['net_profit'], profits[i])
        for suffix in ('net.json', 'trades.csv', 'deals.csv', 'signals.csv', 'trace.csv'):
            p = COMMON / f'{stem}-{suffix}'
            if p.exists() and p.stat().st_mtime >= began - 2:
                (folder / f'{i}-{suffix}.gz').write_bytes(gzip.compress(p.read_bytes(), mtime=0))
        eqdd = native_metrics['equity_dd_pct'] if native_metrics else net['equity_dd_pct']
        st = stats(d, start, end, equity_dd=eqdd)
        clean = not any(net[k] for k in FAIL_KEYS) and stopouts == 0
        rows.append(dict(index=i, parameters=cases[i] if optimize else None, slots=slots, net=net, stats=st, clean=clean,
                         stage=name, start=start, end=end, model=model, parameters_sha=digest(cases[i]) if optimize else None,
                         report_sha=sha(rp), native=native_metrics, tag=tag, symbol=symbol, risk_percent=risk, stopouts_in_batch=stopouts))
    save(folder / 'results.json', rows)
    status('DONE ' + name, cases=len(cases), seconds=round(time.time() - began, 1), stopouts=stopouts)
    return rows


def dedupe(cases):
    return list({digest(c): c for c in cases}.values())


def read_ledger(name, i=0):
    return pd.read_csv(io.BytesIO(gzip.decompress((OUT / name / f'{i}-trades.csv.gz').read_bytes())))


def patches(stage, m):
    stops=[dict(stop=0,sl=x) for x in [.5,.75,1,1.5,2,2.5,3,4]]+[dict(stop=1,sl=x) for x in [.1,.2,.5]]+[dict(stop=x) for x in [2,3,5]]+[dict(stop=4,sl=x) for x in [5,10,20]]
    trails=([dict(trail=0)]+[dict(trail=1,start=x) for x in [.5,1,1.5]]+[dict(trail=2,start=x) for x in [.5,1,1.5,2]]
      +[dict(trail=3,start=s,dist=d) for s in [.5,1,1.5] for d in [1,2,3]]+[dict(trail=4,start=1,dist=x) for x in [.1,.2,.5]]
      +[dict(trail=5,start=1),dict(trail=6,start=1),dict(trail=7,start=1,dist=3),dict(trail=8,start=1)])
    exits=[dict(exit=0,rr=x) for x in [.5,.75,1,1.25,1.5,2,2.5,3,4,5,6,0]]+[dict(exit=1,hold=x) for x in [8,16,32]]+[dict(flat=1),dict(exit=3)]
    filters=[dict(filter=0),dict(filter=1),dict(filter=2),dict(filter=4),dict(filter=5),dict(filter=6),dict(filter=7)]
    filters += [dict(filter=f,adx=x) for f in [3,8] for x in [15,20,25,30]]
    common={'timeframe':[dict(tf=x) for x in [1,3,5,15,30,60,240,1440]],
      'entry':[dict(entry=0),dict(entry=1)]+[dict(entry=e,offset=x) for e in [2,3] for x in [.1,.25,.5]],
      'stop':stops,'trailing':trails,'exit':exits,'session':[dict(session=x) for x in range(6)],
      'direction':[dict(direction=x) for x in range(3)],'filters':filters,
      'management':[dict(day=x) for x in range(4)]+[dict(max_day=x) for x in range(4)]+[dict(flat=x) for x in range(3)]+[dict(season=x) for x in range(3)]}
    if stage=='logic':
      if m=='A':return ([dict(p1=x) for x in [12,24,48]]+[dict(fast=x) for x in [3,6,12]]+[dict(speed=0),dict(speed=1)]
        +[dict(p2=x) for x in [0,.25,.5,1]]+[dict(p3=x) for x in [50,100,200]]+[dict(p4=0),dict(p4=1)]+[dict(volavg=x) for x in [20,50,100]])
      if m=='B':return [dict(p1=x) for x in [240,480,960]]+[dict(p2=x) for x in [20,40,60,120]]+[dict(p3=x) for x in [.05,.1,.2,.5]]+[dict(p4=x) for x in [0,20,50,100]]
      return [dict(p1=x) for x in [-1,-2,-3]]+[dict(p2=x) for x in [1,2,3]]
    if m=='C':
      if stage=='entry':return [dict(p3=x) for x in [0,7,13.5]]
      if stage=='stop':return stops
      if stage=='exit':return exits+[dict(p2=x) for x in [1,2,3]]
    return common[stage]


STAGES={m:['timeframe','entry','stop','trailing','exit','session','direction','filters','management','logic'] for m in 'AB'}
STAGES['C']=['entry','stop','trailing','exit','session','filters','management','logic']


def score(r, minimum=30):
    s=r['stats'];pf=s['pf'] or 0
    if not r['clean']:return -1e9
    if s['trades']<minimum:return -1000+s['trades']/100
    if s['net']<=0:return -1-abs(s['net'])/10000-r['net']['equity_dd_pct']/100
    return (pf-1)*math.sqrt(s['trades'])/(1+r['net']['equity_dd_pct']/10)


def eligible(r, minimum=30):
    return r['clean'] and r['stats']['trades']>=minimum and r['stats']['net']>0 and (r['stats']['pf'] or 0)>=1.15


def slim(r):
    return {k:r[k] for k in ['index','parameters','stage','start','end','model','symbol','risk_percent','stats','net','clean','report_sha']}


def parity():
    cases=[RAWCASE[m] for m in 'ABC']
    new=batch('parity-shared3y',cases,*WEB['3y'],model=4,optimize=False,slots=[0,1,2])[0]
    d=read_ledger('parity-shared3y');old=pd.read_csv(RAW/'native/3Y/trades.csv')
    keys=['module','open_epoch','close_epoch','side','volume','open_price','close_price','initial_sl','initial_tp','requested_risk','actual_risk','net_profit','commission','swap','fee']
    def key(df):return sorted(tuple(v if isinstance(v,str) else round(float(v),6) for v in row) for row in df[keys].itertuples(index=False))
    equal=key(d)==key(old)
    save(ROOT/'PARITY.json',dict(exact=equal,old_n=len(old),new_n=len(d),new_net=float(d.net_profit.sum()),old_net=float(old.net_profit.sum()),native_equity_dd_pct=new['net']['equity_dd_pct']))
    if not equal:
      changes=[(a,b) for a,b in itertools.zip_longest(key(old),key(d)) if a!=b];save(ROOT/'PARITY-DIFFERENCES.json',changes[:25])
    assert equal,'Parameterized defaults do not reproduce raw; optimisation prohibited'
    opt=batch('parity-optimizer',[RAWCASE['A']],*RECENT,model=1)[0]
    single=batch('parity-single',[RAWCASE['A']],*RECENT,model=1,optimize=False)[0]
    assert key(read_ledger('parity-optimizer'))==key(read_ledger('parity-single')),'Optimizer/single differ'
    status('PARITY VERIFIED: raw188 and optimizer/single')


def search(m):
    leaders=[RAWCASE[m]];stages=[]
    for stage in STAGES[m]:
      cases=dedupe(leaders+[b|patch for b in leaders for patch in patches(stage,m)])
      rows=batch(m+'-'+stage,cases,*DEV)
      ranked=sorted(rows,key=lambda r:score(r,MIN_DEV[m]),reverse=True)
      leaders=[r['parameters'] for r in ranked if r['clean']][:3]
      assert leaders,'No execution-clean candidates; '+m+' '+stage
      stages.append(dict(stage=stage,cases=len(cases),qualified=sum(eligible(r,MIN_DEV[m]) for r in rows),top=[slim(r) for r in ranked[:3]]))
      save(ROOT/f'STAGES-{m}.json',stages)
    finalists=[r for r in ranked if r['clean']][:3]
    save(ROOT/f'FINALISTS-{m}.json',[slim(r) for r in finalists])
    return finalists


def neighbours(m,b):
    axes=[]
    if b['stop'] in [0,1,4]:axes.append('sl')
    if b['rr']>0:axes.append('rr')
    if b['trail'] in [3,4,7]:axes.append('dist')
    if b['entry'] in [2,3]:axes.append('offset')
    axes+=['p1','p3','p2'] if m=='A' else ['p1','p2','p3'] if m=='B' else ['p1','p2']
    axes=list(dict.fromkeys(axes))[:3];cases=[]
    for delta in itertools.product([-1,0,1],repeat=len(axes)):
      c=dict(b)
      for k,d in zip(axes,delta):
        if m=='C' and k in ['p1','p2']:c[k]=max(-4,min(-1,b[k]+d)) if k=='p1' else max(1,min(4,b[k]+d))
        elif k in ['p1','p2','p3'] and ((m=='A' and k!='p2') or (m=='B' and k!='p3')):c[k]=max(2,round(b[k]*(1+.2*d)))
        else:c[k]=round(b[k]*(1+.2*d),6)
      if m=='B' and c['p2']>=c['p1']:c['p2']=c['p1']-1
      cases.append(c)
    return dedupe(cases),axes


def validate(m,finalists):
    groups=[];cases=[]
    for r in finalists:
      ns,axes=neighbours(m,r['parameters']);groups.append((r['parameters'],axes,len(cases),len(ns)));cases+=ns
    rows=batch(m+'-plateau',cases,*DEV)
    plateau=[];passed=[]
    for b,axes,i,num in groups:
      subset=rows[i:i+num];positive=sum(r['clean'] and r['stats']['net']>0 for r in subset)/num;med=statistics.median(r['stats']['pf'] or 0 for r in subset)
      ok=len(axes)>=2 and positive>=2/3 and med>1
      plateau.append(dict(parameters=b,axes=axes,neighbours=num,positive_fraction=positive,median_pf=med,passed=ok))
      if ok:passed.append(b)
    save(ROOT/f'PLATEAU-{m}.json',plateau)
    # Failed plateau finalists are still confirmed for transparent diagnostic, never qualified.
    val=batch(m+'-validation',[r['parameters'] for r in finalists],*VAL,model=4)
    qualified=[r for r in val if r['parameters'] in passed and eligible(r,MIN_OOS[m])]
    pick=max(qualified or val,key=lambda r:score(r,MIN_OOS[m]))
    out=dict(module=m,parameters=pick['parameters'],qualified=bool(qualified),plateau=plateau,validation=[slim(r) for r in val],selected=slim(pick))
    save(ROOT/f'PICK-{m}.json',out);return out


def freeze(picks):
    cases=[picks[m]['parameters'] for m in 'ABC']+[RAWCASE[m] for m in 'ABC'];combos=[]
    raw_plateaus=[]
    for m in 'ABC':
      cs,axes=neighbours(m,RAWCASE[m]);rs=batch('raw-plateau-'+m,cs,*DEV)
      positive=sum(r['clean'] and r['stats']['net']>0 for r in rs)/len(rs);med=statistics.median(r['stats']['pf'] or 0 for r in rs)
      center=next(r for r in rs if r['parameters']==RAWCASE[m])
      raw_plateaus.append(dict(module=m,positive_fraction=positive,median_pf=med,axes=axes,minimum_development=eligible(center,MIN_DEV[m]),passed=positive>=2/3 and med>1 and eligible(center,MIN_DEV[m])))
    for mask in range(1,8):
      slots=[i for i in range(3) if mask&(1<<i)]
      r=batch('combo-validation-'+str(mask),cases,*VAL,model=4,optimize=False,slots=slots)[0]
      combos.append(dict(mask=mask,slots=slots,qualified=eligible(r) and all(picks['ABC'[i]]['qualified'] for i in slots),result=slim(r)))
    anchor=batch('raw-validation',cases,*VAL,model=4,optimize=False,slots=[3,4,5])[0]
    combos.append(dict(mask=7,slots=[3,4,5],variant='UNCHANGED_RAW',qualified=eligible(anchor) and all(r['passed'] for r in raw_plateaus),result=slim(anchor)))
    qs=[r for r in combos if r['qualified']]
    pick=max(qs or combos,key=lambda r:score(r['result']))
    frozen=dict(cases=cases,selected_mask=pick['mask'],selected_variant=pick.get('variant','TUNED'),slots=pick['slots'],qualified_validation=bool(qs),combinations=combos,raw_validation=slim(anchor),raw_plateaus=raw_plateaus,logic_sha256=sha(EA/'Logic.mqh'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),selection_amendment_sha256=sha(ROOT/'SELECTION AMENDMENT.txt'),frozen_utc=datetime.now(timezone.utc).isoformat(),note='Chosen on validation incl. original raw anchor; no future retuning. Best examined diagnostic if gates fail.')
    save(ROOT/'FROZEN FINAL.json',frozen);status('FINAL FROZEN',mask=pick['mask'],qualified=bool(qs));return frozen


def finish(frozen):
    cases=frozen['cases'];slots=frozen['slots'];results={}
    for label,window in [('HOLD',HOLD),('DEV',DEV),('VAL',VAL)]+[(k.upper(),v) for k,v in WEB.items()]:
      results[label]=batch('final-'+label,cases,*window,model=4,optimize=False,slots=slots)[0]
      save(ROOT/'FINAL RESULTS.json',results)
    comparisons=[]
    for i in slots:
      r=batch('module-'+str(i)+'-1y',cases,*RECENT,model=4,optimize=False,slots=[i])[0];comparisons.append(r)
    save(ROOT/'MODULE RESULTS.json',comparisons)
    silver=batch('final-XAG1Y',cases,*RECENT,model=4,optimize=False,slots=slots,symbol='XAGUSD')[0]
    save(ROOT/'XAG RESULTS.json',silver)
    risks=[]
    for risk in [.25,.5,.75,1,1.25]:risks.append(batch('risk-'+str(risk),cases,*RECENT,model=4,optimize=False,slots=slots,risk=risk)[0])
    save(ROOT/'RISK RESULTS.json',risks)
    controls={}
    for label,window in [('3Y',WEB['3y']),('5Y',WEB['5y'])]:controls[label]=batch('control-'+label,cases,*window,model=4,optimize=False,slots=slots,control=True)[0]
    save(ROOT/'CONTROLS.json',controls)
    trials=[]
    for f in sorted(OUT.glob('*/results.json')):trials+=load(f)
    save(ROOT/'SEARCH RESULTS.json',trials)
    configs=set()
    for r in trials:
        if r['parameters'] is not None:
            configs.add(digest(r['parameters']))
        else:
            receipt=load(OUT/r['stage']/'manifest.json')
            configs.update(digest(receipt['cases'][i]) for i in r['slots'] or [])
    extra=81 if (ROOT/'CONTROLLER RESTART.txt').exists() else 0
    save(ROOT/'TRIAL ACCOUNTING.json',dict(total_native_passes=len(trials),unique_parameter_vectors=len(configs),interrupted_attempt_upper_bound=extra,all_included_in_DSR=len(trials)+extra,search_model1='Fast development screen only; not native real-tick confirmation. Interrupted attempt conservatively added to trial-count penalty; see controller receipt.'))
    status('NATIVE RESEARCH COMPLETE',passes=len(trials))


def main():
    with (TESTER/'gold-speed-pipeline.lock').open('a+b') as lease:
      lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
      if sys.argv[1]=='parity':parity();return
      assert load(ROOT/'PARITY.json')['exact'],'Parity first'
      picks=load(ROOT/'PICKS.json') if (ROOT/'PICKS.json').exists() else {}
      if sys.argv[1] in ['all','search']:
        mods=sys.argv[2:] or list('ABC')
        for m in mods:
          picks[m]=validate(m,search(m));save(ROOT/'PICKS.json',picks)
      if sys.argv[1] in ['all','finish']:
        frozen=load(ROOT/'FROZEN FINAL.json') if (ROOT/'FROZEN FINAL.json').exists() else freeze(picks)
        finish(frozen)


if __name__=='__main__':main()
