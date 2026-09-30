"""3 Way Gold production build: compile + native parity against the frozen research BEST trio. Isolated tester only.

python deploy.py compile | parity | run <label> <start> <end> [key=value ...]
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, hashlib, json, os, re, shutil, subprocess, sys, time, msvcrt
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
EA_DIR = BASE / '3 Way Gold EA'
SRC = EA_DIR / '3 Way Gold EA.mq5'
EX5 = SRC.with_suffix('.ex5')
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
DEST = TESTER / 'MQL5/Experts/AAA Research/3WayGold20260930'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/Calyx3WayGold'
RESEARCH = BASE / 'QuantLab Gold Trio Pipeline 2026-09-30'
OUT = ROOT / 'native'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    b = Path(p).read_bytes()
    return b.decode('utf-16') if b[:2] in (b'\xff\xfe', b'\xfe\xff') else b.decode('utf-8-sig', errors='replace')


def save(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, indent=2, default=str), encoding='utf-8')


def free():
    r = subprocess.run(['powershell', '-NoProfile', '-Command', "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],
                       capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode == 0 and str(TESTER).lower() not in r.stdout.lower(), 'Isolated tester busy; nothing stopped'


def logs():
    return list((TESTER / 'logs').glob('*.log')) + list((TESTER / 'Tester/logs').glob('*.log')) + list((TESTER / 'Tester').glob('Agent-*/logs/*.log'))


def compile_ea():
    log = ROOT / 'compile.log'
    began = time.time()
    subprocess.run(f'"{TESTER / "metaeditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    text = read(log)
    assert '0 errors, 0 warnings' in text, text[-3000:]
    assert EX5.stat().st_mtime >= began - 2
    shutil.copy2(log, EA_DIR / 'compile.log')
    DEST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EX5, DEST / EX5.name)
    save(ROOT / 'BUILD.json', {'source': sha(SRC), 'ex5': sha(EX5), 'shared_governor': sha(BASE / '_Shared/CalyxAdaptivePortfolio.mqh')})
    print('Compile clean', sha(EX5)[:12])


def run(label, start, end, extra=None, warmup=180, model=4):
    free_ok = False
    for _ in range(240):
        try:
            free(); free_ok = True; break
        except AssertionError:
            time.sleep(5)
    assert free_ok
    build = json.loads((ROOT / 'BUILD.json').read_text())
    assert sha(EX5) == build['ex5'] and sha(DEST / EX5.name) == build['ex5']
    out = OUT / label
    out.mkdir(parents=True, exist_ok=True)
    warm = (datetime.strptime(start, '%Y.%m.%d') - timedelta(days=warmup)).strftime('%Y.%m.%d')
    vals = dict(InpEnableTrading='true', InpEnableMomentum='true', InpEnableBreakout='true', InpEnableTurnOfMonth='true', InpMarketEntries='false',
                InpRiskPercent=1, InpRiskMode=0, InpFixedRiskMoney=0, InpAdaptivePortfolioControls='false', InpMagic=930930100,
                InpMaximumDeviationPoints=1000, InpAutoServerUtcOffsetLive='true', InpServerUtcOffsetHours=0,
                InpTradeFrom=start + ' 00:00:00', InpResearchLedger='true') | (extra or {})
    setname = f'3wg-{label}.set'
    body = '\n'.join(f'{k}={v}' for k, v in vals.items()) + '\n'
    (out / setname).write_text(body, encoding='utf-8')
    (TESTER / 'MQL5/Profiles/Tester' / setname).write_text(body, encoding='utf-8')
    header = read(BASE / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    rp = TESTER / 'reports/3-way-gold-20260930' / f'{label}.htm'
    rp.parent.mkdir(parents=True, exist_ok=True)
    ini = out / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\3WayGold20260930\\3 Way Gold EA
ExpertParameters={setname}
Symbol=XAUUSD
Period=M15
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=150
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\3-way-gold-20260930\\{label}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    ledger = COMMON / 'ledger.csv'
    offsets = {p: p.stat().st_size for p in logs()}
    began = time.time()
    print('START', label, flush=True)
    proc = subprocess.Popen(f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=TESTER, creationflags=subprocess.CREATE_NO_WINDOW)
    proc.wait(timeout=4 * 3600)
    journal = ''
    for p in logs():
        if p.stat().st_mtime < began - 2:
            continue
        with p.open('rb') as f:
            f.seek(offsets.get(p, 0))
            journal += f.read().decode('utf-16-le', errors='replace')
    (out / 'journal.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert rp.exists() and rp.stat().st_mtime >= began - 2, 'No fresh report'
    (out / 'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(), mtime=0))
    actual = _report_inputs(rp)
    t0 = int(datetime.strptime(start, '%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
    expected = vals | dict(InpTradeFrom=t0)
    bad = [k for k, v in expected.items() if k not in actual or not _same_setting(str(v), actual[k])]
    assert not bad, ('Report inputs differ', bad)
    fatal = re.findall(r'[^\r\n]*(?:initialization failed|critical error|access violation|not enough history|testing start time changed)[^\r\n]*', journal, re.I)
    assert not fatal, fatal[:3]
    assert ledger.exists() and ledger.stat().st_mtime >= began - 2, 'No fresh ledger'
    shutil.copy2(ledger, out / 'ledger.csv')
    d = pd.read_csv(out / 'ledger.csv')
    rb = _read_report(rp)
    m = _native_metrics(rp)
    m['equity_dd_pct'] = _number(_metric(rb, 'Equity Drawdown Relative'))
    assert abs(d.net_profit.sum() - m['net_profit']) < .02, 'Ledger/report cash mismatch'
    res = dict(label=label, start=start, end=end, inputs=actual, trades=len(d), net=round(float(d.net_profit.sum()), 2), native=m,
               summaries=sorted(set(re.findall(r'3WG_SUMMARY[^\r\n]*', journal))), spec=sorted(set(re.findall(r'3WG_SPEC[^\r\n]*', journal))),
               report_sha=sha(rp), ex5_sha=build['ex5'], seconds=round(time.time() - began, 1))
    save(out / 'run.json', res)
    print('DONE', label, res['trades'], res['net'], flush=True)
    return res, d


def compare(label, research_folder, extra=None):
    res, new = run(label, '2021.09.29', '2026.09.29', extra)
    old = pd.read_csv(RESEARCH / 'native' / research_folder / '0-trades.csv.gz')
    keys = ['module', 'open_epoch', 'close_epoch', 'side', 'open_price', 'close_price', 'volume', 'net_profit', 'initial_sl', 'initial_tp']
    norm = lambda d: sorted(tuple(round(float(v), 6) if not isinstance(v, str) else v for v in row) for row in d.assign(module=d.module.str[-3:]).loc[:, keys].itertuples(index=False))  # noqa: E731
    return dict(exact=norm(old) == norm(new), research_trades=len(old), production_trades=len(new), research_net=round(float(old.net_profit.sum()), 2),
                production_net=res['net'], research_source=str(RESEARCH / 'native' / research_folder), ex5_sha=res['ex5_sha'])


def parity():
    out = {'standard (limit entries) vs research BEST trio': compare('parity-5y', 'combo-best-3-ABC-5y'),
           'FTMO market entries vs research market variant': compare('parity-5y-market', 'ftmo-market-variant-5y', {'InpMarketEntries': 'true'})}
    save(ROOT / 'PARITY.json', out)
    print(json.dumps(out, indent=1))
    assert all(v['exact'] for v in out.values()), 'Production does not reproduce the research runs'


def main():
    lock = TESTER / '3-way-gold-deploy.lock'
    with lock.open('a+b') as h:
        h.seek(0)
        msvcrt.locking(h.fileno(), msvcrt.LK_NBLCK, 1)
        cmd = sys.argv[1]
        if cmd == 'compile':
            compile_ea()
        elif cmd == 'parity':
            parity()
        elif cmd == 'run':
            extra = dict(a.split('=', 1) for a in sys.argv[5:])
            run(sys.argv[2], sys.argv[3], sys.argv[4], extra)
        h.seek(0)
        msvcrt.locking(h.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
