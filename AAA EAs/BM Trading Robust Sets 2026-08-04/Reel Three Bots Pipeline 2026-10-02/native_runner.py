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
BASE = ROOT.parent
EA = ROOT / 'EA'
OUT = ROOT / 'native'
OUT.mkdir(exist_ok=True)
RAW = BASE / 'Reel Three Bots Raw 2026-10-02'
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/ReelPipeline20261002'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number  # noqa: E402

FIELDS = 'module tf entry offset stop sl rr trail start dist exit session direction filter day max_day hold flat season p1 p2 p3 range_start range_end range_flat maxpos reentry channel_tf atr_period partial stopbuffer adx_min regime_min regime_max'.split()
FAIL_KEYS = ['entry_fail','close_fail','modify_fail','cancel_fail','bad_risk']
MAGIC = 9801000


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
    return end


def ledger(stem):
    tp = COMMON / (stem + '-trades.csv')
    return pd.read_csv(tp) if tp.exists() else None


def batch(name, cases, start, end, model=1, optimize=True, control=False, retry=True, warmup=180, slots=None, risk=1, seed=301):
    """Runs a case table natively. optimize=True: one pass per case (complete optimiser over InpCase).
    optimize=False: one single test with slots (list of up to 3 case indices) running together."""
    if optimize and len(cases)==1: optimize=False
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    frozen = dict(name=name, cases=cases, start=start, end=end, model=model, optimize=optimize, control=control, retry=retry,
                  warmup=warmup, slots=slots, risk=risk, seed=seed, logic={p:sha(EA/p) for p in ['Engine.mqh','Extensions.mqh','Main.mqh']}, protocol=sha(ROOT/'PROTOCOL.txt'))
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
    src = EA / 'ReelSearch.mq5'
    src.write_text('#property strict\n#property version "1.00"\n#property description "Tester-only Gold Trio search EA (generated case table)."\n' + table + '#include "Main.mqh"\n', encoding='utf-8')
    log = EA / 'compile.log'
    began = time.time()
    subprocess.run(f'"{TESTER / "metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    body = read(log)
    assert '0 errors, 0 warnings' in body, body[-4000:]
    ex5 = src.with_suffix('.ex5')
    assert ex5.stat().st_mtime >= began - 2
    for p in (src, ex5, log, EA / 'Main.mqh', EA/'Engine.mqh', EA/'Extensions.mqh'):
        shutil.copy2(p, folder / p.name)
    dest = TESTER / 'MQL5/Experts/AAA Research/ReelPipeline20261002'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ex5, dest / 'ReelSearch.ex5')
    tag = 'reel-' + name + '-' + digest(frozen)[:10]
    sdate = datetime.strptime(start, '%Y.%m.%d')
    warm = (sdate - timedelta(days=warmup)).strftime('%Y.%m.%d')
    todate = to_date(end)
    if optimize:
        vals = dict(InpCase=f'0||0||1||{len(cases) - 1}||Y', InpCase2=-1, InpCase3=-1)
    else:
        sl = (slots or [0]) + [-1, -1]
        vals = dict(InpCase=sl[0], InpCase2=sl[1], InpCase3=sl[2])
    vals |= dict(InpControl=str(control).lower(), InpRetryClosed=str(retry).lower(), InpRiskPercent=risk, InpFixedRiskUSD=100, InpSeed=seed,
                 InpTradeFrom=start + ' 00:00:00', InpTag=tag, InpMagic=MAGIC)
    symbol = 'DE30' if all(c['module']==0 for c in cases) else 'XAUUSD'
    if optimize: assert len({c['module'] for c in cases})==1,'Do not optimise mixed symbols'
    setname = tag + '.set'
    setbody = '\n'.join(f'{k}={v}' for k, v in vals.items()) + '\n'
    (folder / setname).write_text(setbody, encoding='utf-8')
    (TESTER / 'MQL5/Profiles/Tester' / setname).write_text(setbody, encoding='utf-8')
    header = read(BASE / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ext = '.xml' if optimize else '.htm'
    rp = TESTER / 'reports/reel-search-20261002' / (tag + ext)
    rp.parent.mkdir(parents=True, exist_ok=True)
    ini = folder / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ReelPipeline20261002\\ReelSearch
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
Report=reports\\reel-search-20261002\\{tag + ext}
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
        proc.wait(timeout=8 * 3600)
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
    fatal = re.findall(r'[^\n]*(?:initialization failed|start time changed|not enough history|access violation|critical error|array out of range|zero divide)[^\n]*', journal, re.I)
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
        native_metrics['history_quality'] = _metric(rb, 'History Quality')
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
        for suffix in ('net.json', 'trades.csv', 'signals.csv', 'trace.csv'):
            p = COMMON / f'{stem}-{suffix}'
            if p.exists() and p.stat().st_mtime >= began - 2:
                (folder / f'{i}-{suffix}.gz').write_bytes(gzip.compress(p.read_bytes(), mtime=0))
        eqdd = native_metrics['equity_dd_pct'] if native_metrics else net['equity_dd_pct']
        st = stats(d, start, end, equity_dd=eqdd)
        clean = not any(net[k] for k in FAIL_KEYS) and stopouts == 0
        if len(d): assert (d.actual_risk > 0).all() and (d.requested_risk > 0).all(), 'Missing initial risk'
        tick_notes=sorted(set(re.findall(r'[^\n]*(?:real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded)[^\n]*',journal)))[:20]
        rows.append(dict(index=i, parameters=cases[i] if optimize or (len(cases)==1 and slots is None) else None, slots=slots, net=net, stats=st, clean=clean,
                         stage=name, start=start, end=end, model=model, parameters_sha=digest(cases[i]) if optimize or (len(cases)==1 and slots is None) else None,
                         report_sha=sha(rp), stopouts_in_batch=stopouts, native_metrics=native_metrics, tick_notes=tick_notes))
    save(folder / 'results.json', rows)
    status('DONE ' + name, cases=len(cases), seconds=round(time.time() - began, 1), stopouts=stopouts)
    return rows


def dedupe(cases):
    return list({digest(c): c for c in cases}.values())


def read_ledger(name, i=0):
    return pd.read_csv(io.BytesIO(gzip.decompress((OUT / name / f'{i}-trades.csv.gz').read_bytes())))


