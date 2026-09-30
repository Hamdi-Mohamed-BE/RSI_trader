"""Serial, isolated native tester for the Gold Trio raw study; no live terminal API, no production imports.

Usage: python run.py compile | smoke | main | case <name> <window>
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, hashlib, json, os, re, shutil, subprocess, sys, time, msvcrt
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
DEST = TESTER / 'MQL5/Experts/AAA Research/GoldTrio20260930'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxGoldTrio20260930'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number  # noqa: E402

CFG = json.loads((ROOT / 'run-config.json').read_text())
BUILD_FILES = ['GoldTrio.mq5', 'GoldTrio.ex5', 'RULES.md', 'run-config.json']


def save(p, x):
    p.write_text(json.dumps(x, indent=2, allow_nan=False, default=lambda v: v.item() if isinstance(v, np.generic) else str(v)), encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    b = p.read_bytes()
    return b.decode('utf-16') if b[:2] in (b'\xff\xfe', b'\xfe\xff') else b.decode('utf-8-sig', errors='replace')


def status(msg, **kw):
    save(ROOT / 'status.json', dict(message=msg, at=datetime.now().isoformat(timespec='seconds'), **kw))
    print(msg, json.dumps(kw), flush=True)


def free():
    p = subprocess.run(['powershell', '-NoProfile', '-Command', "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],
                       capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode == 0 and str(TESTER).lower() not in p.stdout.lower(), 'Research tester busy; nothing stopped'
    net = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    assert not any(':3000 ' in l and 'LISTENING' in l for l in net.splitlines()), 'Tester port busy'


def logs():
    return list((TESTER / 'logs').glob('*.log')) + list((TESTER / 'Tester/logs').glob('*.log')) + list((TESTER / 'Tester').glob('Agent-*/logs/*.log'))


def compile_ea():
    free()
    log = ROOT / 'compile.log'
    began = time.time()
    subprocess.run(f'"{TESTER / "metaeditor64.exe"}" /portable /compile:"{ROOT / "GoldTrio.mq5"}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
    text = read(log)
    assert '0 errors, 0 warnings' in text, text
    assert (ROOT / 'GoldTrio.ex5').stat().st_mtime >= began - 2
    DEST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'GoldTrio.ex5', DEST / 'GoldTrio.ex5')
    save(ROOT / 'BUILD.json', {p: sha(ROOT / p) for p in BUILD_FILES})
    status('Compile clean')


def case(spec, window, attempt=0):
    model = CFG['model']
    tag = f"{spec['name']}-{window}-m{model}"
    out = ROOT / 'native' / tag
    out.mkdir(parents=True, exist_ok=True)
    build = json.loads((ROOT / 'BUILD.json').read_text())
    assert all(sha(ROOT / p) == h for p, h in build.items()), 'Build changed since compile'
    assert sha(DEST / 'GoldTrio.ex5') == build['GoldTrio.ex5']
    if (out / 'run.json').exists():
        old = json.loads((out / 'run.json').read_text())
        assert old['build'] == build
        return old
    start, end = CFG['smoke'] if window == 'smoke' else (CFG['windows'][window], CFG['end'])
    warm = (datetime.strptime(start, '%Y.%m.%d') - timedelta(days=90)).strftime('%Y.%m.%d')
    vals = dict(InpModules=spec['modules'], InpBreakoutQ4Only=str(spec['q4']).lower(), InpControl=str(spec['control']).lower(),
                InpRiskPercent=CFG['risk_percent'], InpSeed=CFG['seed'], InpTradeFrom=start + ' 00:00:00', InpTag=tag, InpMagic=9309300)
    body = '\n'.join(f'{k}={v}' for k, v in vals.items()) + '\n'
    setname = 'gt-' + tag + '.set'
    (out / setname).write_text(body, encoding='utf-8')
    (TESTER / 'MQL5/Profiles/Tester' / setname).write_text(body, encoding='utf-8')
    header = read(BASE / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    ini = out / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\GoldTrio20260930\\GoldTrio
ExpertParameters={setname}
Symbol={CFG['symbol']}
Period=M1
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\gold-trio-20260930\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    rp = TESTER / 'reports/gold-trio-20260930' / f'{tag}.htm'
    rp.parent.mkdir(parents=True, exist_ok=True)
    profile = TESTER / 'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    for a in range(120):
        try:
            free()
            break
        except AssertionError:
            if a == 119:
                raise
            time.sleep(5)
    offsets = {p: p.stat().st_size for p in logs()}
    began = time.time()
    status('START ' + tag)
    proc = subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=TESTER, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        proc.wait(timeout=5400)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=15)
        raise RuntimeError('Owned research test timeout')
    journal = ''
    for p in logs():
        if p.stat().st_mtime < began - 2:
            continue
        with p.open('rb') as f:
            f.seek(offsets.get(p, 0))
            journal += '\n' + f.read().decode('utf-16-le', errors='replace')
    (out / f'journal-attempt{attempt}.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert rp.exists() and rp.stat().st_mtime >= began - 2, 'No fresh report ' + tag
    (out / f'report-attempt{attempt}.htm.gz').write_bytes(gzip.compress(rp.read_bytes(), mtime=0))
    actual = _report_inputs(rp)
    if not actual and 'tester agent authorization error' in journal and attempt < 2:
        return case(spec, window, attempt + 1)
    expected = vals | dict(InpTradeFrom=int(datetime.strptime(start, '%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()))
    assert all(k in actual and _same_setting(str(v), actual[k]) for k, v in expected.items()), 'Report input mismatch ' + tag
    rb = _read_report(rp)
    assert all(x in rb for x in [CFG['symbol'], warm, end, 'GoldTrio'])
    assert 'testing with execution delay 150 milliseconds' in journal
    fatal = re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|testing start time changed|not enough history)[^\r\n]*', journal, re.I)
    assert not fatal, fatal[:3]
    for suffix in ['trades.csv', 'signals.csv', 'trace.csv']:
        src = COMMON / f'{tag}-{suffix}'
        assert src.exists() and src.stat().st_mtime >= began - 2, 'Missing ' + suffix
        (out / (suffix + '.gz')).write_bytes(gzip.compress(src.read_bytes(), mtime=0))
    d = pd.read_csv(out / 'trades.csv.gz')
    metrics = _native_metrics(rp)
    metrics['equity_dd_pct'] = _number(_metric(rb, 'Equity Drawdown Relative'))
    metrics['balance_dd_pct'] = _number(_metric(rb, 'Balance Drawdown Relative'))
    if len(d):
        assert ((d.volume - d.closed_volume).abs() < 1e-8).all(), 'Unclosed volume'
        assert abs(d.net_profit.sum() - metrics['net_profit']) < .02, 'Deal/report cash mismatch'
        assert (d.open_epoch >= expected['InpTradeFrom']).all()
        assert (d.actual_risk > 0).all()
    p = d.net_profit.to_numpy()
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    metrics.update(trades=len(p), net_profit=float(p.sum()), profit_factor=float(gp / gl) if gl else None,
                   mean_net_R=float((d.net_profit / d.actual_risk).mean()) if len(p) else None,
                   return_pct=float(p.sum() / CFG['deposit'] * 100), win_rate_pct=float(100 * (p > 0).mean()) if len(p) else 0)
    flags = dict(entry_fail=len(re.findall('GT_ENTRY_FAIL', journal)), close_fail=len(re.findall('GT_CLOSE_FAIL', journal)),
                 modify_fail=len(re.findall('GT_MODIFY_FAIL', journal)), invalid_volume=len(re.findall('invalid volume', journal, re.I)),
                 invalid_stops=len(re.findall('invalid stops', journal, re.I)), stopout=len(re.findall('stop out|margin call', journal, re.I)))
    outdata = dict(tag=tag, spec=spec, window=window, model=model, start=start, end=end, warmup_from=warm, build=build, inputs=actual,
                   metrics=metrics, flags=flags, seconds=round(time.time() - began, 2),
                   tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*', journal)))[:20],
                   summaries=sorted(set(re.findall(r'GT_SUMMARY[^\r\n]*', journal))), spec_lines=sorted(set(re.findall(r'GT_SPEC[^\r\n]*', journal))),
                   report_sha=sha(rp), attempt=attempt)
    save(out / 'run.json', outdata)
    pf = metrics['profit_factor']
    status('DONE ' + tag, n=len(p), PF=round(pf, 3) if pf is not None else None, net=round(metrics['net_profit'], 2), flags=flags)
    return outdata


def main():
    mode = sys.argv[1]
    with (ROOT / 'tester.lock').open('a+b') as lease:
        lease.seek(0)
        msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        if mode == 'compile':
            compile_ea()
            return
        if mode == 'smoke':
            case(next(c for c in CFG['cases'] if c['name'] == 'video-A+B+C'), 'smoke')
            case(next(c for c in CFG['cases'] if c['name'] == 'D-ma-trend'), 'smoke')
        elif mode == 'main':
            for c in CFG['cases']:
                case(c, '3y')
        elif mode == 'case':
            case(next(c for c in CFG['cases'] if c['name'] == sys.argv[2]), sys.argv[3])
        else:
            raise ValueError(mode)
    status('COMPLETE ' + mode)


if __name__ == '__main__':
    main()
