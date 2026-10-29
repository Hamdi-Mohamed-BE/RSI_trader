"""ORB Paper Ideas native runs (PLAN.md). Isolated tester only, one run at a time, report-input checks, resumable.

python native.py list | run [name-prefix]
"""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, time
R = Path(__file__).resolve().parent; B = R.parent
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sp = importlib.util.spec_from_file_location('orb_paper_helpers', B / 'FTMO Exit Management Research 2026-09-27/run.py'); h = importlib.util.module_from_spec(sp); sp.loader.exec_module(h)
T = h.TESTER; OUT = R / 'native'; DEST = T / 'MQL5/Experts/AAA Research/ORBPaper20261024'
START, END = '2021.10.24', '2026.10.24'
GEN = B / 'ORB Volume Data EA/ORB Volume Data EA.ex5'; V3 = B / 'US100 Selective ORB Research 2026-08-21/EA/US100 Selective ORB Retest EA.ex5'
LAD = R / 'ORB Paper Research EA.ex5'
O5 = B / '_00 Live profiles/ORB05 Sets'
BASES = {   # name: (expert, symbol, period, 0.5R set, full set, full RR, kind, entry window/cutoff)
    'XNY': (GEN, 'XAUUSD', 'M30', O5 / 'xau-orb-new-york-m30.set', B / 'Selected Portfolio Settings 2026-09-01/14 XAU ORB New York M30 - LOCKED STANDALONE.set', 1.5, 'gen', 180),
    'XLN': (GEN, 'XAUUSD', 'M30', O5 / 'xau-orb-london-ny-overlap-m30.set', B / 'Selected Portfolio Settings 2026-09-01/15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set', 1.0, 'gen', 180),
    'UNY': (GEN, 'USTEC', 'M30', O5 / 'us100-orb-new-york-m30.set', B / 'Selected Portfolio Settings 2026-09-01/16 US100 ORB New York M30 - LOCKED STANDALONE.set', 4.0, 'gen', 180),
    'UH1': (GEN, 'USTEC', 'M15', O5 / 'us100-h1-orb-13utc.set', B / 'ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set', 6.0, 'gen', 60),
    'UV3': (V3, 'USTEC', 'M5', O5 / 'us100-selective-orb-v3.set', B / 'US100 Selective ORB Research 2026-08-21/Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set', 2.0, 'v3', None)}


def cases():
    out = {}
    for b, (ex, sym, per, s05, sfull, rr, kind, win) in BASES.items():
        for tag, sset, r in (('05', s05, 0.5), ('FULL', sfull, rr)):
            base = dict(expert=ex, symbol=sym, period=per, settings=sset, overrides={})
            out[f'{b}-{tag}-BASE'] = base
            out[f'{b}-{tag}-EARLY'] = {**base, 'overrides': {'InpTradeWindowMinutes': str(win // 3)} if kind == 'gen' else {'InpEntryCutoffHour': '10', 'InpEntryCutoffMinute': '30'}}
            out[f'{b}-{tag}-BE60'] = {**base, 'overrides': {'InpBreakEvenAtR': f'{0.6 * r:.2f}'}}
            if kind == 'gen':
                out[f'{b}-{tag}-RETEST'] = {**base, 'overrides': {'InpEntryMode': '1'}}
                out[f'{b}-{tag}-STOPENTRY'] = {**base, 'overrides': {'InpUsePaperStopEntry': 'true'}}
                if tag == 'FULL':
                    out[f'{b}-{tag}-LADDER'] = {**base, 'expert': LAD, 'overrides': {'InpStepTrailR': 'true', 'InpRewardRisk': '20.0', 'InpBreakEvenAtR': '0.0', 'InpTrailStartAtR': '0.0'}}
    out['XNY-FULL-PARITY'] = {**out['XNY-FULL-BASE'], 'expert': LAD}   # research copy, ladder off: must equal production
    return out


CASES = cases()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(v, indent=2, allow_nan=False), encoding='utf-8')
def status(s): save(R / 'status.json', dict(utc=datetime.now(timezone.utc).isoformat(), message=s)); print(s, flush=True)


def run(name):
    c = CASES[name]; folder = OUT / name; folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'results.json').exists(): return json.loads((folder / 'results.json').read_text())
    inputs = dict(l.split('=', 1) for l in c['settings'].read_text(encoding='utf-8-sig').splitlines() if '=' in l and not l.startswith(';'))
    for k in c['overrides']:
        assert k in inputs or k in ('InpUsePaperStopEntry', 'InpStepTrailR'), (name, k)
    inputs.update(c['overrides'])
    frozen = dict(case=name, start=START, end_exclusive=END, deposit=10000, model=4, delay_ms=150, symbol=c['symbol'], period=c['period'], broker='Exness-MT5Trial16',
                  expert=str(c['expert']), binary_sha256=sha(c['expert']), settings=str(c['settings']), set_sha256=sha(c['settings']), overrides=c['overrides'],
                  plan_sha256=sha(R / 'PLAN.md'), inputs=inputs)
    mp = folder / 'manifest.json'
    if mp.exists(): assert json.loads(mp.read_text()) == frozen, 'Frozen inputs changed'
    else: save(mp, frozen)
    h.free(); profile = T / 'MQL5/Profiles/Charts/Calyx Research Empty'; assert profile.is_dir() and not list(profile.glob('*.chr'))
    DEST.mkdir(parents=True, exist_ok=True); ex = DEST / (name + '.ex5'); shutil.copy2(c['expert'], ex)
    setname = 'orbp-' + name + '.set'; body = '\n'.join(k + '=' + v for k, v in inputs.items()) + '\n'
    (folder / setname).write_text(body); (T / 'MQL5/Profiles/Tester' / setname).write_text(body)
    header = h.text(B / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').split('[Experts]')[0]
    rp = T / 'reports/orb-paper20261024' / (name + '.htm'); rp.parent.mkdir(parents=True, exist_ok=True)
    ini = folder / 'tester.ini'
    ini.write_text(header + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ORBPaper20261024\\{name}
ExpertParameters={setname}
Symbol={c['symbol']}
Period={c['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
ForwardMode=0
Report=reports\\orb-paper20261024\\{name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    offsets = {p: p.stat().st_size for p in h.logfiles()}; began = time.time(); h.free(); status('START ' + name)
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 0
    proc = subprocess.Popen(f'"{T / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"', cwd=T, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=si)
    try: proc.wait(timeout=1800)
    except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=20); raise RuntimeError('Owned isolated test timed out')
    journal = ''
    for p in h.logfiles():
        if p.stat().st_mtime < began - 2: continue
        with p.open('rb') as f: f.seek(offsets.get(p, 0)); journal += f.read().decode('utf-16-le', errors='replace') + '\n'
    (folder / 'journal.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert proc.returncode == 0 and rp.exists() and rp.stat().st_mtime >= began - 2, 'no fresh report'
    assert not re.search(r'initialization failed|not enough history|access violation|array out of range|zero divide', journal, re.I), 'Invalid test; see journal'
    report = h._read_report(rp); assert all(x in report for x in [START, END, c['symbol']])
    actual = h._report_inputs(rp); bad = [k for k, v in inputs.items() if k in actual and not h._same_setting(v, actual[k])]
    assert not bad and len(set(inputs) & set(actual)) >= 0.8 * len(inputs), ('SET not applied', bad[:5])
    from app.mt5_evidence_jobs import _metric, _number
    native = h._native_metrics(rp); native['equity_dd_pct'] = _number(_metric(report, 'Equity Drawdown Relative'))
    trades = h._native_trades(rp, name); assert len(trades) == native['trades'] and abs(sum(x['net_profit'] for x in trades) - native['net_profit']) < .10
    (folder / 'report.htm.gz').write_bytes(gzip.compress(rp.read_bytes(), mtime=0)); save(folder / 'trades.json', trades)
    result = dict(manifest=frozen, native=native, trades=trades, seconds=round(time.time() - began, 1), report_sha256=sha(rp),
                  failed_orders=len(re.findall(r'failed|rejected', journal, re.I)), tick_notes=sorted(set(re.findall(r'real ticks begin[^\r\n]*', journal)))[:3])
    save(folder / 'results.json', result); status(f"DONE {name} {native['net_profit']:+.0f} PF {native['profit_factor']} n={native['trades']} {result['seconds']}s")
    return result


if __name__ == '__main__':
    if sys.argv[1] == 'list':
        for k in CASES: print(k)
        print(len(CASES))
    else:
        pre = sys.argv[2] if len(sys.argv) > 2 else ''
        for name in CASES:
            if name.startswith(pre): run(name)
        status('COMPLETE ' + (pre or 'all'))
