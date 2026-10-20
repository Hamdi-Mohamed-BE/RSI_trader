"""Frozen standalone native source ledgers for the Prop Ready $1K replay.

Never imports the MT5 Python API, accesses normal terminals, or trades accounts.
Only its exclusively leased, empty-chart, portable strategy tester is launched.
This is a $10K standalone source run, NOT the requested $1K portfolio result.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy, csv, gzip, hashlib, importlib.util, json, msvcrt, os, re, shutil, subprocess, sys, time, traceback

R = Path(__file__).resolve().parent
B = R.parent
S = R / 'native_sources'
START, END = '2026-08-17', '2026-10-17'
BEGIN = int(datetime.fromisoformat(START).replace(tzinfo=timezone.utc).timestamp())
FINISH = int(datetime.fromisoformat(END).replace(tzinfo=timezone.utc).timestamp())
PACKAGE = B / '_00 Live profiles/Packages/PropReady/PACKAGE.json'
PRIOR = B / 'Top10 EA Two Month Backtest 2026-10-16'
FACTORY = B / 'ORB and Range Breakout RR05 Comparison 2026-10-08/run.py'
T = B / '_Backtests/MT5-DMC-20260811'
SERVER = 'Exness-MT5Trial15'
CONNECTION_SOURCE = T / 'backtest-configs/dmc-cheat-sheet-regime-20260912/xau--matched-reference--fresh-current-locked--2db9e654a.ini'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
_spec = importlib.util.spec_from_file_location('prop1k_native_factory', FACTORY)
n = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(n)
n.R = S
NORMAL = Path('C:/Program Files/MetaTrader 5').resolve()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    n.save(Path(path), value)


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def ensure_free():
    assert T.resolve() != NORMAL
    n.available()
    n.h.free()
    profile = T / 'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr')), 'Research charts must be empty'


def prepare():
    assert not (R / 'native_status.json').exists(), 'Cannot prepare after any source run'
    assert not (R / 'native_plan.json').exists(), 'Never overwrite a frozen source protocol'
    package, previous = read(PACKAGE), read(PRIOR / 'PLAN.json')
    assert package['version'] == 'PROP-READY9-BROKER-NEUTRAL-20261017'
    assert len(package['entries']) == 9
    sources = {str(p): sha(p) for p in (PACKAGE, PRIOR / 'PLAN.json', PRIOR / 'RUN_STATUS.json', FACTORY,
        B / 'FTMO Exit Management Research 2026-09-27/run.py', B / 'PIPELINE.md')}
    sources[str(CONNECTION_SOURCE)] = sha(CONNECTION_SOURCE)
    connection_header()
    cases = []
    for entry in package['entries']:
        row = copy.deepcopy(next(x for x in previous['cases'] if x['slug'] == entry['slug']))
        source = Path(row['source'])
        assert all(sha(p) == digest for p, digest in row['production_hashes'].items()), ('Archived source graph changed', row['slug'])
        sources.update(row['production_hashes'])
        preset = PACKAGE.parent / 'package' / entry['settings']
        binary = PACKAGE.parent / 'package' / entry['expert']
        assert sha(preset) == entry['settings_sha'] and sha(binary) == entry['expert_sha']
        sources.update({str(preset): sha(preset), str(binary): sha(binary)})
        inputs = {k: str(v) for k, v in entry['inputs'].items() if not k.startswith('FTMO')}
        assert inputs['InpRiskPercent'] == '0.5'
        assert inputs['InpAdaptivePortfolioControls'] == 'false'
        if '-orb-' in row['slug']:
            assert inputs['InpRewardRisk'] == '0.5'
        if row['slug'] in ('nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum'):
            assert inputs['InpRequireDIAgreement'] == 'true'
        # Active strategy parameters must match the prior actual native report,
        # except the expressly frozen source risk change from 1% to 0.5%.
        old_receipt = read(PRIOR / 'RUN_STATUS.json')['complete'][row['slug']]
        assert sha(old_receipt['path']) == old_receipt['sha256']
        old_actual = read(old_receipt['path'])['inputs']
        for key, value in inputs.items():
            if key == 'InpRiskPercent':
                continue
            assert key in old_actual and n.h._same_setting(value, old_actual[key]), ('Current rule mismatch', row['slug'], key)
        row.update(input_settings=inputs, candidate_overrides={}, selected_risk_percent=0.5,
                   standalone_source_only=True, carry_in=False)
        cases.append(row)
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(), start=START, end_exclusive=END,
        timezone='UTC', source_server=SERVER, source_demo=True, currency='USD', source_deposit=10000,
        leverage=2000, model=4, execution_delay_ms=150, source_risk_percent=0.5,
        portfolio_result=False, production_guards=False, optimization=False, live_changes=False,
        purpose='Causal native strategy entry/exit and sampled-floating source ledger. $1K shared risk/lot/guard replay is separate.',
        empty_start=True, all_completed_days_through='2026-10-16', both_di_filters='ON', all_five_orbs_rr=0.5,
        boundary_policy='Keep native boundary liquidations in original evidence; mark end_censored and do not pretend they are natural strategy exits in portfolio replay.',
        fill_policy='Native broker costs, original strategy orders and lot rounding; current source account specifications, not historical execution certification.',
        coverage_policy='No date shifts. Reject history-start-change errors, incomplete terminal day, source mismatch, runtime or stopout. Audit snapshot first/last dates and copied M1 bar boundaries.',
        cases=cases, source_hashes=sources)
    save(R / 'native_plan.json', plan)
    freeze = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        files={str(p): sha(p) for p in (R / 'native_run.py', S / 'ReadOnlyAudit.mqh', R / 'native_plan.json')},
        source_files=sources, cases=9, searched_configurations=0, frozen_before_results=True)
    save(R / 'native_freeze.json', freeze)
    print('FROZEN nine fixed-rule standalone source cases; precise 2026-08-17 to 2026-10-17 exclusive. No portfolio outcomes.', flush=True)


def verify_freeze():
    f = read(R / 'native_freeze.json')
    assert all(sha(p) == digest for p, digest in f['files'].items()), 'Frozen native protocol changed'
    assert all(sha(p) == digest for p, digest in f['source_files'].items()), 'Production/source artifact changed'
    return read(R / 'native_plan.json')


def connection_header():
    # The parent provides a private, ignored file. Never put account identifiers
    # into the public plan/status/output or call the live terminal to discover it.
    text = n.h.text(CONNECTION_SOURCE)
    section = text.split('[Experts]')[0].split('[Tester]')[0].strip()
    assert '[Common]' in section and re.search(r'^Login=\d+\s*$', section, re.M)
    assert re.search(r'^Server=' + re.escape(SERVER) + r'\s*$', section, re.M)
    assert not re.search(r'^Password=', section, re.M), 'Do not store passwords in research source'
    return section + '\n'


def run_case(row, binary, build):
    slug, tag = row['slug'], 'pr1k-source-' + row['slug']
    out = S / slug
    out.mkdir(parents=True, exist_ok=True)
    inputs = dict(row['input_settings'], InpRR05AuditTag=tag)
    manifest = dict(tag=tag, slug=slug, inputs=inputs, start=START, end_exclusive=END,
        source_deposit=10000, leverage=2000, currency='USD', server=SERVER, model=4,
        execution_delay_ms=150, symbol=row['symbol'], period=row['period'],
        build_sha256=sha(S / 'EA' / slug / 'build.json'), binary_sha256=sha(binary),
        source_ledger_only=True, current_prop_ready_inputs_verified=True)
    manifest_path = out / 'manifest.json'
    if manifest_path.exists():
        assert read(manifest_path) == manifest, 'Source case mutation'
    else:
        save(manifest_path, manifest)
    if (out / 'results.json').exists():
        return read(out / 'results.json')
    verify_freeze()
    ensure_free()
    destination = T / 'MQL5/Experts/AAA Research/PropReady1KSource20261017'
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, destination / (slug + '.ex5'))
    preset = tag + '.set'
    body = '\n'.join(k + '=' + v for k, v in inputs.items()) + '\n'
    (out / 'inputs.set').write_text(body, encoding='utf-8')
    (T / 'MQL5/Profiles/Tester' / preset).write_text(body, encoding='utf-8')
    report = T / 'reports/prop-ready-1k-source-20261017' / (tag + '.htm')
    report.parent.mkdir(parents=True, exist_ok=True)
    ini = out / 'tester.private.ini'
    ini.write_text(connection_header() + f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port=3010
Expert=AAA Research\\PropReady1KSource20261017\\{slug}
ExpertParameters={preset}
Symbol={row['symbol']}
Period={row['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate={START.replace('-', '.')}
ToDate={END.replace('-', '.')}
ForwardMode=0
Report=reports\\prop-ready-1k-source-20261017\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    offsets = {p: p.stat().st_size for p in n.h.logfiles()}
    began = time.time()
    print('START standalone native source ' + slug, flush=True)
    proc = subprocess.Popen(f'"{T / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
        cwd=T, creationflags=subprocess.CREATE_NO_WINDOW)
    save(out / 'owned-process.json', dict(pid=proc.pid, executable=str(T / 'terminal64.exe'), started=began))
    try:
        proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=30)
        raise RuntimeError('Only own isolated tester terminated after timeout; no normal terminal touched')
    journal = ''
    for p in n.h.logfiles():
        if p.stat().st_mtime < began - 2:
            continue
        with p.open('rb') as stream:
            stream.seek(offsets.get(p, 0))
            journal += stream.read().decode('utf-16-le', errors='replace') + '\n'
    (out / 'journal.private.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert proc.returncode == 0 and report.is_file() and report.stat().st_mtime >= began - 2, 'Missing fresh native report'
    flags = {key: len(re.findall(pattern, journal, re.I)) for key, pattern in {
        'initialization': 'initialization failed', 'runtime': 'access violation|array out of range|zero divide',
        'history': 'testing start time changed|not enough history', 'stopout': 'stop out|margin call',
        'invalid_stops': 'invalid stops', 'invalid_volume': 'invalid volume', 'export': 'RR05_EXPORT_FAILED',
        'market_closed': 'market closed', 'no_money': 'not enough money'}.items()}
    assert not any(flags[k] for k in ('initialization', 'runtime', 'history', 'stopout', 'export')), flags
    assert 'RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal
    actual = n.h._report_inputs(report)
    unsupported = [key for key in inputs if key not in actual]
    assert not unsupported, ('Missing current Prop Ready strategy inputs', unsupported)
    assert all(n.h._same_setting(v, actual[k]) for k, v in inputs.items()), 'Native input mismatch'
    text = n.h._read_report(report)
    assert START.replace('-', '.') in text and END.replace('-', '.') in text and row['symbol'] in text
    native = n.h._native_metrics(report)
    native.update(equity_dd_pct=n._number(n._metric(text, 'Equity Drawdown Relative')),
                  balance_dd_pct=n._number(n._metric(text, 'Balance Drawdown Relative')))
    (out / 'report.private.htm.gz').write_bytes(gzip.compress(report.read_bytes(), mtime=0))
    common = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxRR05All20261008'
    for suffix in ('deals', 'equity', 'coverage', 'contracts', 'entry_risk'):
        source = common / (tag + '-' + suffix + '.csv')
        assert source.is_file() and source.stat().st_mtime >= began - 2, ('Missing fresh audit', suffix)
        shutil.copy2(source, out / (suffix + '.csv'))
    trades, ledger = n.trades_from_deals(n.export_rows(out / 'deals.csv'))
    assert abs(sum(t['net'] for t in trades) - native['net_profit']) < .031, 'Native cash reconciliation'
    assert all(BEGIN <= t['open_epoch'] <= t['close_epoch'] < FINISH for t in trades), 'Native trade outside frozen dates'
    trace = n.export_rows(out / 'equity.csv')
    coverage = n.export_rows(out / 'coverage.csv')
    assert len(coverage) == 1
    coverage = coverage[0]
    assert int(coverage['m1_count']) > 0 and int(coverage['m1_first']) >= BEGIN and int(coverage['m1_last']) < FINISH
    first, last = min(int(x['epoch']) for x in trace), max(int(x['epoch']) for x in trace)
    assert first == BEGIN, ('Initial source snapshot shifted', utc(first))
    assert datetime.fromtimestamp(last, timezone.utc).date().isoformat() == '2026-10-16', ('Source does not reach final requested day', utc(last))
    assert datetime.fromtimestamp(int(coverage['m1_last']), timezone.utc).date().isoformat() == '2026-10-16'
    for trade in trades:
        trade['end_censored'] = any('end of test' in comment.lower() for comment in trade['exit_comments'])
    result = dict(tag=tag, slug=slug, window=[START, END], source_deposit=10000, source_risk_percent=0.5,
        standalone_source_only=True, current_prop_ready_inputs_verified=True, inputs=actual,
        native=native, metrics=n.metrics(trades, trace, native), flags=flags, trades=trades, ledger=ledger,
        first_captured_snapshot_utc=utc(first), last_captured_snapshot_utc=utc(last),
        coverage=coverage, boundary_liquidation_positions=[t['position_id'] for t in trades if t['end_censored']],
        tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*', journal, re.I)))[:30],
        seconds=time.time()-began, binary_sha256=sha(binary), report_sha256=sha(report),
        no_live_changes=True, native_plan_sha256=sha(R / 'native_plan.json'), native_freeze_sha256=sha(R / 'native_freeze.json'))
    save(out / 'results.json', result)
    print('DONE standalone source ' + slug + '; trades=' + str(len(trades)) + '; ' + native['history_quality'], flush=True)
    ensure_free()
    return result


def run():
    plan = verify_freeze()
    connection_header()
    state_path = R / 'native_status.json'
    state = read(state_path) if state_path.exists() else dict(total=9, complete={}, failed={},
        window=[START, END], source_ledger_only=True, live_changes=False)
    selected = sys.argv[2:]
    for row in plan['cases']:
        slug = row['slug']
        if selected and slug not in selected:
            continue
        if slug in state['complete']:
            receipt = state['complete'][slug]
            assert sha(receipt['path']) == receipt['sha256']
            continue
        try:
            verify_freeze()
            ensure_free()
            binary, build = n.build(row)
            result = run_case(row, binary, build)
            path = S / slug / 'results.json'
            state['complete'][slug] = dict(path=str(path), sha256=sha(path), trades=len(result['trades']),
                history_quality=result['native']['history_quality'], seconds=result['seconds'])
            state['failed'].pop(slug, None)
        except Exception as exc:
            state['failed'][slug] = dict(error=str(exc), trace=traceback.format_exc()[-6000:])
            save(state_path, state)
            print('FAILED native source ' + slug + ': ' + str(exc), flush=True)
            raise
        save(state_path, state)
    verify_freeze()
    ensure_free()
    print('NATIVE SOURCE BATCH COMPLETE ' + str(len(state['complete'])) + '/9. No live changes.', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:2] == ['run']:
        with (B / 'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            run()
    else:
        raise SystemExit('Use prepare or run [optional slug ...]')
