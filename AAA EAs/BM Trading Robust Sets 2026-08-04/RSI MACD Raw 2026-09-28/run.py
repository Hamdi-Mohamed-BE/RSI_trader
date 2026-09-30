"""Sequential native MT5 raw research. Never connects to the user's trading terminal."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, importlib.util, json, os, re, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
CFG = json.loads((ROOT/'run-config.json').read_text())
TESTER = BASE/'_Backtests/MT5-DMC-20260811'
DEST = TESTER/'MQL5/Experts/AAA Research/RSI MACD 20260928'
COMMON = Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxRsiMacd20260928'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(BASE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _report_inputs, _same_setting, _read_report, _metric, _number
# Reuse the previously audited full position-ID ledger, process isolation and log readers.
spec = importlib.util.spec_from_file_location('pd_runner_helpers', BASE/'PD Sweep Reversal Raw 2026-09-28/run.py')
helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
sha, read, free, logs, ledger = helpers.sha, helpers.read, helpers.free, helpers.logs, helpers.ledger


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def status(message, **kw):
    save(ROOT/'status.json', dict(utc=datetime.now(timezone.utc).isoformat(), message=message, **kw))
    print(message, json.dumps(kw), flush=True)


def compile_ea():
    free(); began = time.time(); log = ROOT/'compile.log'
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{ROOT/"EA/RsiMacd.mq5"}" /log:"{log}"',
                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    body = read(log)
    assert '0 errors, 0 warnings' in body, body
    binary = ROOT/'EA/RsiMacd.ex5'
    assert binary.stat().st_mtime >= began-2
    DEST.mkdir(parents=True, exist_ok=True); shutil.copy2(binary, DEST/binary.name)
    paths = [ROOT/p for p in ('EA/RsiMacd.mq5', 'EA/RsiMacd.ex5', 'RULES.md', 'run-config.json')]
    paths += [BASE/'RSI Mean Reversion 15m Raw 2026-09-25/EA'/p for p in ('AAA_Final_Common.mqh', 'DynamicTrailingSessionFilter.mqh')]
    paths += [BASE/'_Shared/CalyxAdaptivePortfolio.mqh', BASE/'PD Sweep Reversal Raw 2026-09-28/run.py']
    save(ROOT/'BUILD.json', dict(hashes={str(p.relative_to(BASE)): sha(p) for p in paths},
                                compiled_utc=datetime.now(timezone.utc).isoformat(), compile=body[-500:]))
    status('Clean compile: 0 errors, 0 warnings')


def case(asset, variant, window, smoke=False):
    symbol = CFG['symbols'][asset]; tag = ('smoke-' if smoke else '')+f'{asset}-{variant}-{window}'
    out = ROOT/'native'/tag; out.mkdir(parents=True, exist_ok=True)
    build = json.loads((ROOT/'BUILD.json').read_text())
    for path, digest in build['hashes'].items():
        assert sha(BASE/path) == digest, (path, 'modified frozen dependency')
    assert sha(DEST/'RsiMacd.ex5') == sha(ROOT/'EA/RsiMacd.ex5')
    if (out/'run.json').exists():
        old = json.loads((out/'run.json').read_text()); assert old['ok'] and old['build'] == build
        return old
    start, end = (CFG['smoke_start'], CFG['smoke_end']) if smoke else (CFG['windows'][window], CFG['end'])
    warm = (datetime.strptime(start, '%Y.%m.%d')-timedelta(days=CFG['warmup_days'])).strftime('%Y.%m.%d')
    vals = dict(InpVariant=CFG['variants'][variant], InpRiskPercent=CFG['risk_percent'], InpRR=CFG['rr'],
                InpTradeFrom=start+' 00:00:00', InpTag=tag, InpMagic=9282630,
                InpAdaptivePortfolioControls='false', InpUseDynamicTrailingSL='false', InpResearchSession=0)
    setname = 'rm-'+tag+'.set'; body = '\n'.join(f'{k}={v}' for k, v in vals.items())+'\n'
    (out/setname).write_text(body, encoding='utf-8')
    (TESTER/'MQL5/Profiles/Tester'/setname).write_text(body, encoding='utf-8')
    # Private, already-authorized isolated research connection; never print its contents.
    header = (BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini').read_text(encoding='utf-8-sig').split('[Experts]')[0]
    ini = out/'tester.ini'; ini.write_text(header+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\RSI MACD 20260928\\RsiMacd
ExpertParameters={setname}
Symbol={symbol}
Period=M15
Deposit={CFG['deposit']}
Currency=USD
Leverage=1:2000
Model={CFG['model']}
ExecutionMode={CFG['delay_ms']}
Optimization=0
FromDate={warm}
ToDate={end}
Report=reports\\rsi-macd-20260928\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    report = TESTER/'reports/rsi-macd-20260928'/f'{tag}.htm'; report.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(120):
        try:
            free(); break
        except AssertionError:
            if attempt == 119: raise
            time.sleep(5)
    offsets = {p: p.stat().st_size for p in logs()}; began = time.time(); status('START '+tag)
    proc = subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
                            cwd=TESTER, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:
        proc.terminate(); proc.wait(timeout=30); raise RuntimeError('Owned isolated tester timeout: '+tag)
    journal = ''
    for p in logs():
        if p.stat().st_mtime < began-2: continue
        with p.open('rb') as f:
            f.seek(offsets.get(p, 0)); journal += '\n'+str(p.relative_to(TESTER))+'\n'+f.read().decode('utf-16-le', errors='replace')
    (out/'journal.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert report.exists() and report.stat().st_mtime >= began-2, ('No fresh report', tag)
    rb = _read_report(report); actual = _report_inputs(report)
    expected = {**vals, 'InpTradeFrom': int(datetime.strptime(start, '%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())}
    bad = [k for k, v in expected.items() if k not in actual or not _same_setting(str(v), actual[k])]
    assert not bad, (tag, 'input mismatch', bad)
    assert all(v in rb for v in (warm, end, symbol, 'RsiMacd'))
    assert f'testing with execution delay {CFG["delay_ms"]} milliseconds' in journal
    flags = {k: len(re.findall(p, journal, re.I)) for k, p in {
        'init_failed': r'initialization failed|INIT_FAILED', 'critical': r'critical error|access violation',
        'export_failed': r'RM_EXPORT_FAIL', 'history_shortened': r'testing start time changed|start date changed|no history data|not enough history',
        'invalid_volume': r'invalid volume', 'invalid_stops': r'invalid stops', 'market_closed': r'market closed',
        'margin_call': r'stop out|margin call'}.items()}
    assert not any(flags[k] for k in ('init_failed', 'critical', 'export_failed', 'history_shortened', 'invalid_volume')), (tag, flags)
    for suffix in ('deals.csv', 'audit.bin'):
        export = COMMON/f'{tag}-{suffix}'
        assert export.exists() and export.stat().st_mtime >= began-2, (tag, 'missing export', suffix)
        if suffix.endswith('.bin'):
            (out/(suffix+'.gz')).write_bytes(gzip.compress(export.read_bytes(), mtime=0))
        else:
            shutil.copy2(export, out/suffix)
    trades = ledger(out/'deals.csv'); metrics = _native_metrics(report)
    metrics.update(max_equity_dd_pct=_number(_metric(rb, 'Equity Drawdown Relative')),
                   max_balance_dd_pct=_number(_metric(rb, 'Balance Drawdown Relative')),
                   max_equity_dd_usd=_number(_metric(rb, 'Equity Drawdown Maximal')))
    assert len(trades) == metrics['trades'], (tag, 'trade count')
    assert abs(sum(t['net_profit'] for t in trades)-metrics['net_profit']) < max(.12, .01*len(trades)), (tag, 'net P&L')
    assert all(t['open_time'] >= datetime.strptime(start, '%Y.%m.%d').isoformat() for t in trades), 'Warmup trades'
    lines = sorted(set(re.findall(r'RM_[^\r\n]+', journal)))
    orders = [dict(re.findall(r'(\w+)=([^ ]+)', l)) for l in lines if l.startswith('RM_ORDER')]
    assert len(orders) == len(trades), (tag, 'orders versus positions')
    (out/'report.htm.gz').write_bytes(gzip.compress(report.read_bytes(), mtime=0))
    save(out/'trades.json', trades); save(out/'orders.json', orders)
    result = dict(ok=True, asset=asset, symbol=symbol, timeframe=15, variant=variant, window=window,
                  smoke=smoke, start=start, end=end, warmup_start=warm, inputs=actual, metrics=metrics,
                  flags=flags, build=build, elapsed_seconds=time.time()-began,
                  report_sha=sha(report), deals_sha=sha(out/'deals.csv'),
                  summary=[l for l in lines if l.startswith('RM_SUMMARY')],
                  symbol_spec=[l for l in lines if l.startswith('RM_SPEC')],
                  time_exits=[l for l in lines if l.startswith('RM_TIME_EXIT')],
                  tick_coverage=sorted(set(re.findall(r'[^\r\n]*(?:real ticks begin|real ticks.*%)[^\r\n]*', journal))))
    save(out/'run.json', result)
    status('DONE '+tag, trades=len(trades), net=metrics['net_profit'], seconds=round(time.time()-began, 1))
    return result


def main():
    cmd = sys.argv[1]
    if cmd == 'compile': compile_ea(); return
    if cmd == 'smoke':
        for variant in CFG['variants']: case('XAU', variant, 'smoke', True)
    elif cmd == 'grid':
        for window in (sys.argv[2:] or list(CFG['windows'])):
            for asset in CFG['symbols']:
                for variant in CFG['variants']: case(asset, variant, window)
    elif cmd == 'case': case(sys.argv[2], sys.argv[3], sys.argv[4])
    else: raise SystemExit('compile | smoke | grid [windows] | case asset variant window')
    status('COMPLETE '+cmd)


if __name__ == '__main__': main()
