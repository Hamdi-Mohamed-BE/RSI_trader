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
RAW = BASE / 'QuantLab Gold Trio Raw 2026-09-30'
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxGoldTrioSearch20260930'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number  # noqa: E402

FIELDS = 'module tf entry offset stop sl rr trail start dist exit session direction filter day max_day hold flat season p1 p2 p3 p4'.split()
RAWCASE = {
    'A': dict(module=0, tf=60, entry=0, offset=0, stop=0, sl=2.5, rr=0, trail=2, start=1, dist=0, exit=0, session=0, direction=0, filter=0,
              day=0, max_day=0, hold=0, flat=0, season=0, p1=24, p2=0.5, p3=100, p4=1),
    'B': dict(module=1, tf=30, entry=0, offset=0, stop=0, sl=2.0, rr=2.5, trail=2, start=1, dist=0, exit=0, session=0, direction=0, filter=0,
              day=0, max_day=0, hold=0, flat=0, season=0, p1=480, p2=60, p3=0.10, p4=50),
    'C': dict(module=2, tf=1440, entry=0, offset=0, stop=0, sl=2.0, rr=0, trail=0, start=1, dist=0, exit=0, session=0, direction=0, filter=0,
              day=0, max_day=0, hold=0, flat=0, season=0, p1=-1, p2=2, p3=0, p4=0),
}
RAW_TAG = {'A': 'A-momentum-3y-m4', 'B': 'B-breakout-3y-m4', 'C': 'C-turn-of-month-3y-m4'}
DEV = ('2021.09.29', '2024.03.29')
VAL = ('2024.03.29', '2025.09.29')
RECENT = ('2025.09.29', '2026.09.29')
HOLD = ('2019.09.29', '2021.09.29')
WEB = {'6m': ('2026.03.29', '2026.09.29'), '1y': RECENT, '3y': ('2023.09.29', '2026.09.29'), '5y': ('2021.09.29', '2026.09.29')}
DATA_END = '2026.09.29'
MIN_DEV = {'A': 60, 'B': 60, 'C': 20}
MIN_OOS = {'A': 30, 'B': 30, 'C': 12}
FAIL_KEYS = ['entry_fail', 'close_fail', 'modify_fail', 'cancel_fail', 'bad_risk']
MAGIC = 9309400


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
    return end if end == DATA_END else (datetime.strptime(end, '%Y.%m.%d') - timedelta(days=1)).strftime('%Y.%m.%d')


def ledger(stem):
    tp = COMMON / (stem + '-trades.csv')
    return pd.read_csv(tp) if tp.exists() else None


def batch(name, cases, start, end, model=1, optimize=True, control=False, retry=True, warmup=180, slots=None):
    """Runs a case table natively. optimize=True: one pass per case (complete optimiser over InpCase).
    optimize=False: one single test with slots (list of up to 3 case indices) running together."""
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    frozen = dict(name=name, cases=cases, start=start, end=end, model=model, optimize=optimize, control=control, retry=retry,
                  warmup=warmup, slots=slots, logic=sha(EA / 'TrioLogic.mqh'), protocol=sha(ROOT / 'PROTOCOL.md'))
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
    src = EA / 'GoldTrioSearch.mq5'
    src.write_text('#property strict\n#property version "1.00"\n#property description "Tester-only Gold Trio search EA (generated case table)."\n' + table + '#include "TrioLogic.mqh"\n', encoding='utf-8')
    log = EA / 'compile.log'
    began = time.time()
    subprocess.run(f'"{TESTER / "metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    body = read(log)
    assert '0 errors, 0 warnings' in body, body[-4000:]
    ex5 = src.with_suffix('.ex5')
    assert ex5.stat().st_mtime >= began - 2
    for p in (src, ex5, log, EA / 'TrioLogic.mqh'):
        shutil.copy2(p, folder / p.name)
    dest = TESTER / 'MQL5/Experts/AAA Research/GoldTrioSearch20260930'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ex5, dest / 'GoldTrioSearch.ex5')
    tag = 'gts-' + name + '-' + digest(frozen)[:10]
    sdate = datetime.strptime(start, '%Y.%m.%d')
    warm = (sdate - timedelta(days=warmup)).strftime('%Y.%m.%d')
    todate = to_date(end)
    if optimize:
        vals = dict(InpCase=f'0||0||1||{len(cases) - 1}||Y', InpCase2=-1, InpCase3=-1)
    else:
        sl = (slots or [0]) + [-1, -1]
        vals = dict(InpCase=sl[0], InpCase2=sl[1], InpCase3=sl[2])
    vals |= dict(InpControl=str(control).lower(), InpRetryClosed=str(retry).lower(), InpRiskPercent=1, InpSeed=300930,
                 InpTradeFrom=start + ' 00:00:00', InpTag=tag, InpMagic=MAGIC)
    setname = tag + '.set'
    setbody = '\n'.join(f'{k}={v}' for k, v in vals.items()) + '\n'
    (folder / setname).write_text(setbody, encoding='utf-8')
    (TESTER / 'MQL5/Profiles/Tester' / setname).write_text(setbody, encoding='utf-8')
    header = read(BASE / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ext = '.xml' if optimize else '.htm'
    rp = TESTER / 'reports/gold-trio-search-20260930' / (tag + ext)
    rp.parent.mkdir(parents=True, exist_ok=True)
    ini = folder / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldTrioSearch20260930\\GoldTrioSearch
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
ToDate={todate}
ForwardMode=0
Report=reports\\gold-trio-search-20260930\\{tag + ext}
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
        assert all(x in rb for x in ('XAUUSD', warm, todate))
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
        for suffix in ('net.json', 'trades.csv', 'signals.csv', 'trace.csv'):
            p = COMMON / f'{stem}-{suffix}'
            if p.exists() and p.stat().st_mtime >= began - 2:
                (folder / f'{i}-{suffix}.gz').write_bytes(gzip.compress(p.read_bytes(), mtime=0))
        eqdd = native_metrics['equity_dd_pct'] if native_metrics else net['equity_dd_pct']
        st = stats(d, start, end, equity_dd=eqdd)
        clean = not any(net[k] for k in FAIL_KEYS) and stopouts == 0
        rows.append(dict(index=i, parameters=cases[i] if optimize else None, slots=slots, net=net, stats=st, clean=clean,
                         stage=name, start=start, end=end, model=model, parameters_sha=digest(cases[i]) if optimize else None,
                         report_sha=sha(rp), stopouts_in_batch=stopouts))
    save(folder / 'results.json', rows)
    status('DONE ' + name, cases=len(cases), seconds=round(time.time() - began, 1), stopouts=stopouts)
    return rows


def dedupe(cases):
    return list({digest(c): c for c in cases}.values())


def read_ledger(name, i=0):
    return pd.read_csv(io.BytesIO(gzip.decompress((OUT / name / f'{i}-trades.csv.gz').read_bytes())))


# ---------------- search space (PROTOCOL.md) ----------------
def patches(stage, m, b):
    atr_stops = [dict(stop=0, sl=v) for v in [.75, 1, 1.5, 2, 2.5, 3, 4]] + [dict(stop=1, sl=v) for v in [.1, .2, .5]] + [dict(stop=2), dict(stop=3)]
    trails = ([dict(trail=0)] + [dict(trail=1, start=v) for v in [.5, 1, 1.5]] + [dict(trail=2, start=v) for v in [.5, 1, 1.5, 2]]
              + [dict(trail=3, start=s, dist=d) for s in [.5, 1, 1.5, 2] for d in [1, 1.5, 2, 3]] + [dict(trail=4, start=1, dist=v) for v in [.1, .2, .5]] + [dict(trail=5, start=1)])
    rrs = [dict(exit=0, rr=v) for v in [.5, .75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6]] + [dict(exit=0, rr=0)]
    if m == 'C':
        return {
            'entry': [dict(p3=v) for v in [0, 7, 13.5]],
            'stop': atr_stops[:10],  # structure stops need a price series of the entry timeframe; C keeps ATR/percent
            'trailing': trails,
            'exit': rrs + [dict(p2=v) for v in [1, 2, 3]] + [dict(exit=3)],
            'filters': [dict(filter=v) for v in range(7)],
            'management': [dict(season=v) for v in range(3)] + [dict(day=v) for v in range(3)],
            'logic': [dict(p1=v) for v in [-1, -2, -3]] + [dict(p2=v) for v in [1, 2, 3]],
        }[stage]
    common = {
        'timeframe': [dict(tf=v) for v in [5, 15, 30, 60, 240]],
        'entry': [dict(entry=0), dict(entry=1)] + [dict(entry=e, offset=o) for e in [2, 3] for o in [.1, .25, .5]],
        'stop': atr_stops,
        'trailing': trails,
        'exit': rrs + [dict(exit=1, hold=v) for v in [8, 16, 32]] + [dict(flat=1), dict(exit=3)],
        'session': [dict(session=v) for v in range(6)],
        'direction': [dict(direction=v) for v in range(3)],
        'filters': [dict(filter=v) for v in range(7)],
        'management': [dict(day=v) for v in range(4)] + [dict(max_day=v) for v in range(4)] + [dict(flat=v) for v in range(3)] + [dict(season=v) for v in range(3)],
    }
    if stage == 'logic':
        if m == 'A':
            return [dict(p1=v) for v in [12, 24, 48]] + [dict(p2=v) for v in [0, .25, .5, 1]] + [dict(p3=v) for v in [50, 100, 200]]
        return [dict(p1=v) for v in [240, 480, 960]] + [dict(p2=v) for v in [20, 40, 60, 120]] + [dict(p3=v) for v in [.05, .1, .2, .5]] + [dict(p4=v) for v in [0, 20, 50, 100]]
    return common[stage]


STAGES = {'A': ['timeframe', 'entry', 'stop', 'trailing', 'exit', 'session', 'direction', 'filters', 'management', 'logic'],
          'B': ['timeframe', 'entry', 'stop', 'trailing', 'exit', 'session', 'direction', 'filters', 'management', 'logic'],
          'C': ['entry', 'stop', 'trailing', 'exit', 'filters', 'management', 'logic']}


def eligible(r, m, minimum=None):
    st = r['stats']
    return r['clean'] and st['trades'] >= (minimum or MIN_DEV[m]) and st['net'] > 0 and (st['pf'] or 0) >= 1.15


def best_score(r, m, minimum=None):
    st = r['stats']
    dd = r['net']['equity_dd_pct']
    if not r['clean'] or st['trades'] < (minimum or MIN_DEV[m]):
        return -1000.0
    if st['net'] <= 0:
        return -1 - abs(st['net']) / 10000 - dd / 100
    return (st['pf'] - 1) * math.sqrt(st['trades']) / (1 + dd / 10)


def prop_scores(rows, m, minimum=None):
    ok = [r for r in rows if eligible(r, m, minimum)]
    out = {id(r): -1.0 for r in rows}
    if not ok:
        return out
    df = pd.DataFrame([dict(k=id(r), win=r['stats']['win_pct'] or 0, sharpe=r['stats']['sharpe'] if r['stats']['sharpe'] is not None else -99,
                            streak=r['stats']['max_win_streak']) for r in ok])
    ranks = df[['win', 'sharpe', 'streak']].rank(pct=True).mean(axis=1)
    for k, v in zip(df.k, ranks):
        out[k] = float(v)
    return out


def neighbourhood(m, b):
    axes = []
    if b['stop'] in (0, 1):
        axes.append('sl')
    if b['rr'] > 0:
        axes.append('rr')
    if b['trail'] in (3, 4):
        axes.append('dist')
    if b['entry'] in (2, 3):
        axes.append('offset')
    if b['exit'] == 1:
        axes.append('hold')
    axes += {'A': ['p1', 'p3', 'p2'], 'B': ['p1', 'p2', 'p3'], 'C': ['p1', 'p2']}[m]
    if m == 'A' and b['p2'] == 0:
        axes.remove('p2')
    axes = list(dict.fromkeys(axes))[:3]
    cases = []
    for factors in itertools.product([-1, 0, 1], repeat=len(axes)):
        c = dict(b)
        for key, f in zip(axes, factors):
            if m == 'C' and key in ('p1', 'p2'):
                c[key] = max(-4, min(-1, b[key] + f)) if key == 'p1' else max(1, min(4, b[key] + f))
            elif key in ('p1', 'p2', 'p3') and m in 'AB' and not (m == 'B' and key == 'p3') and not (m == 'A' and key == 'p2'):
                c[key] = max(2, round(b[key] * (1 + .2 * f)))
            elif key == 'hold':
                c[key] = max(1, round(b[key] * (1 + .2 * f)))
            else:
                c[key] = round(b[key] * (1 + .2 * f), 6)
        if m == 'B' and c['p2'] >= c['p1']:
            c['p2'] = c['p1'] - 1
        cases.append(c)
    return dedupe(cases), axes


def search(m):
    leaders = [RAWCASE[m]]
    summary = []
    for stage in STAGES[m]:
        cases = dedupe(leaders + [b | p for b in leaders for p in patches(stage, m, b)])
        rows = batch(f'{m}-{stage}', cases, *DEV)
        for r in rows:
            r['best_score'] = best_score(r, m)
        ps = prop_scores(rows, m)
        for r in rows:
            r['prop_score'] = ps[id(r)]
        clean = [r for r in rows if r['clean']]
        by_best = sorted(clean, key=lambda r: r['best_score'], reverse=True)[:3]
        by_prop = [r for r in sorted(rows, key=lambda r: r['prop_score'], reverse=True) if r['prop_score'] >= 0][:3]
        assert by_best, 'No execution-clean candidates: ' + stage
        leaders = dedupe([r['parameters'] for r in by_best + by_prop])
        summary.append(dict(stage=stage, cases=len(cases), best=[slim(r) for r in by_best], prop=[slim(r) for r in by_prop]))
        save(ROOT / f'STAGES-{m}.json', summary)
        save(OUT / f'{m}-{stage}' / 'ranked.json', [slim(r) for r in sorted(rows, key=lambda r: r['best_score'], reverse=True)])
    fin_best = [r for r in sorted(rows, key=lambda r: r['best_score'], reverse=True) if eligible(r, m)][:3]
    fin_prop = [r for r in sorted(rows, key=lambda r: r['prop_score'], reverse=True) if eligible(r, m)][:3]
    save(ROOT / f'FINALISTS-{m}.json', dict(best=[slim(r) for r in fin_best], prop=[slim(r) for r in fin_prop]))
    return fin_best, fin_prop


def slim(r):
    return dict(parameters=r['parameters'], stats=r['stats'], equity_dd_pct=r['net']['equity_dd_pct'], clean=r['clean'],
                best_score=r.get('best_score'), prop_score=r.get('prop_score'), flags={k: r['net'][k] for k in FAIL_KEYS + ['modify_closed', 'close_closed', 'retries', 'boundary']})


def plateau_and_validate(m, fin_best, fin_prop):
    finals = dedupe([r['parameters'] for r in fin_best + fin_prop])
    groups, allcases = [], []
    for b in finals:
        cases, axes = neighbourhood(m, b)
        groups.append((b, axes, len(allcases), len(cases)))
        allcases += cases
    rows = batch(f'{m}-plateau', allcases, *DEV) if allcases else []
    plats = []
    for b, axes, i0, n in groups:
        nb = rows[i0:i0 + n]
        pos = sum(r['stats']['net'] > 0 and r['clean'] for r in nb) / len(nb)
        med = statistics.median((r['stats']['pf'] or 0) for r in nb)
        plats.append(dict(parameters=b, axes=axes, neighbours=n, positive_fraction=round(pos, 3), median_pf=round(med, 3),
                          passed=len(axes) >= 2 and pos >= 2 / 3 and med > 1))
    save(ROOT / f'PLATEAUS-{m}.json', plats)
    passed = [p['parameters'] for p in plats if p['passed']]
    val = batch(f'{m}-validation', passed, *VAL, model=4) if passed else []
    for r in val:
        r['best_score'] = best_score(r, m, MIN_OOS[m])
    picks = {}
    for obj, fins in (('best', fin_best), ('prop', fin_prop)):
        want = [digest(r['parameters']) for r in fins]
        cand = [r for r in val if digest(r['parameters']) in want]
        ps = prop_scores(cand, m, MIN_OOS[m])
        for r in cand:
            r['prop_score'] = ps[id(r)]
        ok = [r for r in cand if eligible(r, m, MIN_OOS[m])]
        key = (lambda r: r['best_score']) if obj == 'best' else (lambda r: (r['prop_score'], r['best_score']))
        if ok:
            pick, verdict = max(ok, key=key), 'PASSED_VALIDATION'
        elif cand:
            pick, verdict = max(cand, key=lambda r: r['best_score']), 'REJECTED_VALIDATION'
        else:
            # nothing passed the plateau: report the top development finalist, labelled
            pick, verdict = (fins[0] if fins else None), 'REJECTED_PLATEAU' if fins else 'REJECTED_DEVELOPMENT'
        picks[obj] = dict(verdict=verdict, parameters=pick['parameters'] if pick else None,
                          validation=slim(pick) if pick and pick in val else None)
    save(ROOT / f'PICKS-{m}.json', picks)
    return picks


def confirm(picks):
    """Frozen picks (all modules/objectives): recent, older holdout, website periods, 5y control. No retuning."""
    names, cases = [], []
    for m in 'ABC':
        for obj in ('best', 'prop'):
            p = picks[m][obj]
            if p['parameters'] is not None:
                names.append(f'{m}-{obj}')
                cases.append(p['parameters'])
    uniq = dedupe(cases)
    idx = {n: uniq.index(c) for n, c in zip(names, cases)}
    runs = {}
    for label, (s, e) in [('recent', RECENT), ('holdout', HOLD), ('6m', WEB['6m']), ('3y', WEB['3y']), ('5y', WEB['5y'])]:
        runs[label] = batch(f'frozen-{label}', uniq, s, e, model=4)
    runs['control-5y'] = batch('frozen-control-5y', uniq, *WEB['5y'], model=4, control=True)
    out = {}
    for n in names:
        m, obj = n.split('-')
        i = idx[n]
        rec, hol = runs['recent'][i], runs['holdout'][i]
        verdict = picks[m][obj]['verdict']
        if verdict == 'PASSED_VALIDATION':
            if not eligible(rec, m, MIN_OOS[m]):
                verdict = 'REJECTED_RECENT'
            elif not eligible(hol, m, MIN_OOS[m]):
                verdict = 'REJECTED_OLDER_HOLDOUT'
            else:
                verdict = 'QUALIFIED'
        out[n] = dict(verdict=verdict, parameters=cases[names.index(n)], case_index=i,
                      periods={k: slim(runs[k][i]) for k in runs}, validation=picks[m][obj]['validation'])
    save(ROOT / 'FROZEN PICKS.json', out)
    return out, uniq


def combos(frozen, uniq):
    result = {}
    sets = {'BEST trio': ['A-best', 'B-best', 'C-best'], 'PROP trio': ['A-prop', 'B-prop', 'C-prop']}
    for obj in ('best', 'prop'):
        surv = [f'{m}-{obj}' for m in 'ABC' if frozen.get(f'{m}-{obj}', {}).get('verdict') == 'QUALIFIED']
        if surv and len(surv) < 3:
            sets[f'{obj.upper()} survivors ({"+".join(s[0] for s in surv)})'] = surv
    for label, members in sets.items():
        members = [x for x in members if x in frozen]
        slots = [frozen[x]['case_index'] for x in members]
        per = {}
        for period, (s, e) in [('validation', VAL), ('recent', RECENT), ('holdout', HOLD), ('6m', WEB['6m']), ('3y', WEB['3y']), ('5y', WEB['5y'])]:
            r = batch(f'combo-{label.split()[0].lower()}-{len(members)}-{"".join(x[0] for x in members)}-{period}', uniq, s, e, model=4, optimize=False, slots=slots)[0]
            d = read_ledger(f'combo-{label.split()[0].lower()}-{len(members)}-{"".join(x[0] for x in members)}-{period}')
            per[period] = dict(total=r['stats'], clean=r['clean'], flags={k: r['net'][k] for k in FAIL_KEYS + ['modify_closed', 'close_closed', 'retries']},
                               modules={mod: stats(d[d.module == mod], s, e) for mod in sorted(d.module.unique())})
        result[label] = dict(members=members, periods=per)
    save(ROOT / 'COMBINATIONS.json', result)
    return result


def parity():
    """Raw case of each module with InpRetryClosed=false must reproduce the raw 3y native trades exactly."""
    uniq = [RAWCASE[m] for m in 'ABC']
    out = {}
    for i, m in enumerate('ABC'):
        batch(f'parity-{m}', uniq, '2023.09.29', '2026.09.29', model=4, optimize=False, retry=False, warmup=90, slots=[i])
        new = read_ledger(f'parity-{m}')
        old = pd.read_csv(RAW / 'native' / RAW_TAG[m] / 'trades.csv.gz')
        keys = ['open_epoch', 'close_epoch', 'side', 'open_price', 'close_price', 'volume', 'net_profit', 'initial_sl', 'initial_tp']
        key = lambda d: sorted(tuple(round(float(v), 6) for v in row) for row in d[keys].itertuples(index=False))  # noqa: E731
        ok = key(old) == key(new)
        out[m] = dict(old_n=len(old), new_n=len(new), exact=ok, old_net=round(float(old.net_profit.sum()), 2), new_net=round(float(new.net_profit.sum()), 2))
    save(ROOT / 'PARITY.json', out)
    assert all(v['exact'] for v in out.values()), out
    status('PARITY PASSED', **{m: v['new_n'] for m, v in out.items()})


def trial_count():
    n, uniq = 0, set()
    for f in OUT.glob('*/results.json'):
        for r in load(f):
            n += 1
            uniq.add(r['parameters_sha'] or f.parent.name)
    return n, len(uniq)


def main():
    lease = TESTER / 'gold-trio-pipeline.lock'
    with lease.open('a+b') as handle:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            cmd = sys.argv[1]
            if cmd == 'smoke':
                batch('smoke', [RAWCASE[m] for m in 'ABC'], '2026.08.01', '2026.09.29', model=4, optimize=False, slots=[0, 1, 2])
                batch('smoke-opt', [RAWCASE[m] for m in 'ABC'], '2026.06.01', '2026.09.29', model=1)
            elif cmd == 'parity':
                parity()
            elif cmd in ('search', 'all'):
                assert all(v['exact'] for v in load(ROOT / 'PARITY.json').values())
                mods = sys.argv[2:] if cmd == 'search' and len(sys.argv) > 2 else list('ABC')
                picks = load(ROOT / 'PICKS.json') if (ROOT / 'PICKS.json').exists() else {}
                for m in mods:
                    fb, fp = search(m)
                    picks[m] = plateau_and_validate(m, fb, fp)
                    save(ROOT / 'PICKS.json', picks)
                if cmd == 'all' or set(picks) == set('ABC'):
                    frozen, uniq = confirm(picks)
                    combos(frozen, uniq)
                    n, u = trial_count()
                    save(ROOT / 'TRIAL ACCOUNTING.json', dict(passes=n, unique_or_single=u))
                    status('PIPELINE COMPLETE', passes=n)
            else:
                raise ValueError(cmd)
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
