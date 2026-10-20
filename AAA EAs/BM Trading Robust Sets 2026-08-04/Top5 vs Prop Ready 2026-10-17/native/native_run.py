"""Frozen current Top5 client-package native source acquisition only.

No MT5 Python API, normal terminal, account switching or live trading. Exactly
five tester-only observational builds, one exclusively leased portable tester.
The source $10K fixed-$50 cases are not shared-account $1K portfolio results.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import importlib.util
import json
import msvcrt
import os
import re
import shutil
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent.parent
REPO = BASE.parent.parent
OWNER = REPO/'clients/_owner/top5'
PUBLIC = REPO/'clients/top 5'
PRIOR = BASE/'Prop Ready 1K Risk Replay 2026-10-17'
MANIFEST = OWNER/'manifest.json'
START, END = '2026-08-17', '2026-10-17'
BEGIN, FINISH = (int(datetime.fromisoformat(x).replace(tzinfo=timezone.utc).timestamp()) for x in (START, END))
SERVER = 'Exness-MT5Trial16'
CONNECTION = BASE/'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
SPEC = importlib.util.spec_from_file_location('read_only_native_source_helpers', PRIOR/'native_run.py')
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
n, T = prior.n, prior.T
COMMON = Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/CalyxRR05All20261008'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    n.save(Path(path), value)


def private_header():
    text = n.h.text(CONNECTION)
    header = text.split('[Experts]')[0].split('[Tester]')[0].strip()
    assert '[Common]' in header and re.search(r'^Login=\d+\s*$', header, re.M)
    assert re.search(r'^Server='+re.escape(SERVER)+r'\s*$', header, re.M)
    assert not re.search(r'^Password=', header, re.M), 'No passwords in research'
    return header+'\n'


def ensure_free():
    prior.ensure_free()


def graph(path, found=None):
    found = set() if found is None else found
    path = Path(path).resolve()
    if path in found:
        return found
    assert path.is_file() and path.is_relative_to(OWNER/'build')
    found.add(path)
    for include in re.findall(r'^\s*#include\s+"([^\"]+)"', n.h.text(path), re.M):
        graph(path.parent/include.replace('\\', '/'), found)
    return found


def prepare():
    assert not (ROOT/'native_plan.json').exists() and not (ROOT/'native_status.json').exists(), 'Immutable pre-run protocol'
    manifest = read(MANIFEST)
    assert len(manifest['entries']) == 5
    assert {q['slug'] for q in manifest['entries']} == {
        'gold-overnight-value-area', 'xau-rsi-vwap', 'nasdaq-overnight',
        'nasdaq-5m-candle-momentum', 'orb-volume-profile'}
    assert sha(OWNER/'ClientGuard.mqh') == manifest['guard_sha256']
    guard = n.h.text(OWNER/'ClientGuard.mqh')
    assert 'lots=minimum;' in guard and 'ACCOUNT_BALANCE' in guard
    assert 'CLIENT_MIN_LOT_OVERRIDE' in guard and 'ClientRiskValue>5.0' in guard
    private_header()
    shutil.copy2(PRIOR/'native_sources/ReadOnlyAudit.mqh', ROOT/'ReadOnlyAuditBase.mqh')
    audit = n.h.text(PRIOR/'native_sources_v2/ReadOnlyAudit.mqh')
    assert audit.count('../native_sources/ReadOnlyAudit.mqh') == 1
    (ROOT/'ReadOnlyAudit.mqh').write_text(audit.replace('../native_sources/ReadOnlyAudit.mqh', 'ReadOnlyAuditBase.mqh'), encoding='utf-8')
    sources = {str(p): sha(p) for p in (MANIFEST, OWNER/'build.py', OWNER/'ClientGuard.mqh',
        PRIOR/'native_run.py', PRIOR/'native_sources/ReadOnlyAudit.mqh',
        PRIOR/'native_sources_v2/ReadOnlyAudit.mqh', CONNECTION,
        BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08/run.py',
        BASE/'FTMO Exit Management Research 2026-09-27/run.py')}
    cases = []
    for entry in manifest['entries']:
        public = PUBLIC/entry['expert']
        owner_binary = OWNER/'build'/entry['expert']
        wrapper = owner_binary.with_suffix('.mq5')
        assert sha(public) == entry['ex5_sha256'] == sha(owner_binary)
        paths = graph(wrapper)
        full = '\n'.join(n.h.text(p) for p in paths)
        assert not re.search(r'\bvoid\s+OnTradeTransaction\s*\(', full), 'Existing transaction callback needs forwarding'
        if entry['slug'] == 'nasdaq-5m-candle-momentum':
            assert entry['inputs']['InpRequireDIAgreement'] == 'false'
            assert re.search(r'input\s+bool\s+InpRequireDIAgreement\s*=\s*false\s*;', full)
        inputs = dict(entry['inputs'], ClientRiskMode='0', ClientRiskValue='50',
            ClientExpectedLogin='0', ClientExpectedServer='', ClientExpectedSymbol='')
        sources.update({str(p): sha(p) for p in paths|{public, owner_binary}})
        cases.append(dict(slug=entry['slug'], symbol=entry['symbol'], period=entry['period'],
            label=entry['label'], wrapper=str(wrapper), public_expert=str(public),
            public_ex5_sha256=entry['ex5_sha256'], inputs=inputs,
            production_hashes={str(p): sha(p) for p in paths|{public, owner_binary}},
            callbacks=dict(OnDeinit=bool(re.search(r'\bvoid\s+OnDeinit\s*\(', full)))))
    plan = dict(start=START, end_exclusive=END, source_server=SERVER, source_deposit=10000,
        currency='USD', leverage=2000, model=4, execution_delay_ms=150, empty_start=True,
        fixed_source_risk_usd=50, portfolio_result=False, live_changes=False, optimization=False,
        policy='Actual Top5 client fixedUSD gateway, minimum-lot override retained, no portfolio/daily guard. Nasdaq DI OFF; other source rules unchanged.',
        instrumentation='Rename only final owner wrapper callback exports, then observe around exact package callbacks; untouched ClientGuard/include source graph. Tester-only entry gate. No trade/stop/timing/sizing edits.',
        feed_caveat='Cached ExnessTrial16 historical source, not current connected Trial15 demo. Current-demo contract comparison supplied separately.',
        expiry='Normal packaged tester bypass of licence historical-date restriction; no expiry renewal or production change.',
        coverage='Exact17Augto17Octexclusive, no shifted/shortened dates accepted; end-of-test liquidations retained as evidence but censored downstream.',
        cases=cases, source_hashes=sources)
    save(ROOT/'native_plan.json', plan)
    save(ROOT/'FROZEN.json', dict(frozen_before_results=True, cases=5, searched_configurations=0,
        files={str(p): sha(p) for p in (ROOT/'native_run.py', ROOT/'native_plan.json', ROOT/'ReadOnlyAudit.mqh', ROOT/'ReadOnlyAuditBase.mqh')},
        source_files=sources))
    print('Frozen five Top5 client cases: Nasdaq DI OFF; fixed50/minimum-lot override; source Trial16.', flush=True)


def verify_freeze():
    frozen = read(ROOT/'FROZEN.json')
    assert all(sha(path) == digest for path, digest in {**frozen['files'], **frozen['source_files']}.items()), 'Frozen native source changed'
    return read(ROOT/'native_plan.json')


def build(row):
    folder = ROOT/'builds'/row['slug']
    folder.mkdir(parents=True, exist_ok=True)
    origin = Path(row['wrapper'])
    public_text = n.h.text(origin)
    rewritten = public_text
    for callback, typename in (('OnInit', 'int'), ('OnTick', 'void'), ('OnTimer', 'void')):
        expression = r'\b'+typename+r'\s+'+callback+r'\s*\('
        assert len(re.findall(expression, rewritten)) == 1, (row['slug'], callback)
        rewritten = re.sub(expression, typename+' Top5Package'+callback+'(', rewritten)
    rewritten = n.absolute_includes(rewritten, origin.parent)
    copied = folder/'PublicWrapperCopy.mq5'
    copied.write_text(rewritten, encoding='utf-8')
    # Source includes and ClientGuard are unmodified. Only these exported names
    # differ so the observer can call the exact public callbacks in order.
    reversed_names = rewritten
    for callback, typename in (('OnInit', 'int'), ('OnTick', 'void'), ('OnTimer', 'void')):
        reversed_names = reversed_names.replace(typename+' Top5Package'+callback+'(', typename+' '+callback+'(')
    assert reversed_names == n.absolute_includes(public_text, origin.parent), 'Public-wrapper callback-only parity'
    wrapper = '#property strict\n#define OnDeinit Top5PackageOnDeinit\n#include "PublicWrapperCopy.mq5"\n#undef OnDeinit\n'
    wrapper += '#include "'+str(ROOT/'ReadOnlyAudit.mqh').replace('\\', '/')+'"\n'
    wrapper += 'int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;int code=Top5PackageOnInit();if(code!=INIT_SUCCEEDED)return code;if(!RR05AuditInit())return INIT_FAILED;RR05Observe();return INIT_SUCCEEDED;}\n'
    wrapper += 'void OnTick(){RR05Observe();Top5PackageOnTick();RR05Observe();}\n'
    wrapper += 'void OnTimer(){RR05Observe();Top5PackageOnTimer();RR05Observe();}\n'
    wrapper += 'void OnDeinit(const int reason){RR05Observe();'+('Top5PackageOnDeinit(reason);' if row['callbacks']['OnDeinit'] else '')+'RR05Finish();}\n'
    source = folder/'Audit.mq5'
    source.write_text(wrapper, encoding='utf-8')
    ensure_free()
    log = folder/'compile.log'
    began = time.time()
    subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',
        timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    message = n.h.text(log)
    assert re.search(r'\b0 errors, 0 warnings\b', message), message[-6000:]
    binary = source.with_suffix('.ex5')
    assert binary.is_file() and binary.stat().st_mtime >= began-2
    proof = dict(public_ex5_sha256=row['public_ex5_sha256'], public_wrapper_sha256=sha(origin),
        source_copy_sha256=sha(copied), audit_wrapper_sha256=sha(source), audit_header_sha256=sha(ROOT/'ReadOnlyAudit.mqh'),
        binary_sha256=sha(binary), production_hashes=row['production_hashes'],
        callback_only_copy_verified=True, strategy_and_ClientGuard_graph_unchanged=True,
        tester_only=True, compile='0 errors, 0 warnings')
    save(folder/'build.json', proof)
    return binary, proof


def run_case(row, binary, proof):
    out = ROOT/row['slug']
    out.mkdir(parents=True, exist_ok=True)
    tag = 'top5-current-source-20261017-'+row['slug']
    inputs = dict(row['inputs'], InpRR05AuditTag=tag)
    verify_freeze()
    ensure_free()
    target = T/'MQL5/Experts/AAA Research/Top5CurrentSource20261017'
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, target/(row['slug']+'.ex5'))
    preset = tag+'.set'
    body = '\n'.join(k+'='+str(value) for k, value in inputs.items())+'\n'
    (out/'inputs.set').write_text(body, encoding='utf-8')
    (T/'MQL5/Profiles/Tester'/preset).write_text(body, encoding='utf-8')
    report = T/'reports/top5-current-source-20261017'/(tag+'.htm')
    report.parent.mkdir(parents=True, exist_ok=True)
    ini = out/'tester.private.ini'
    ini.write_text(private_header()+f'''[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Port=3010
Expert=AAA Research\\Top5CurrentSource20261017\\{row['slug']}
ExpertParameters={preset}
Symbol={row['symbol']}
Period={row['period']}
Deposit=10000
Currency=USD
Leverage=1:2000
Model=4
ExecutionMode=150
Optimization=0
FromDate=2026.08.17
ToDate=2026.10.17
ForwardMode=0
Report=reports\\top5-current-source-20261017\\{tag}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''', encoding='utf-8-sig')
    offsets = {p: p.stat().st_size for p in n.h.logfiles()}
    began = time.time()
    print('START Top5 native '+row['slug'], flush=True)
    proc = subprocess.Popen(f'"{T/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
        cwd=T, creationflags=subprocess.CREATE_NO_WINDOW)
    save(out/'owned-process.json', dict(pid=proc.pid, executable=str(T/'terminal64.exe'), started=began))
    try:
        proc.wait(timeout=2400)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=30)
        raise RuntimeError('Own isolated tester only terminated after timeout; no normal terminal touched')
    journal = ''
    for p in n.h.logfiles():
        if p.stat().st_mtime < began-2:
            continue
        with p.open('rb') as stream:
            stream.seek(offsets.get(p, 0))
            journal += stream.read().decode('utf-16-le', errors='replace')+'\n'
    (out/'journal.private.txt.gz').write_bytes(gzip.compress(journal.encode(), mtime=0))
    assert proc.returncode == 0 and report.is_file() and report.stat().st_mtime >= began-2
    servers = sorted(set(re.findall(r'authorized on (\S+) through', journal)))
    assert servers == [SERVER], ('Unexpected native actual source server', servers)
    flags = {name: len(re.findall(pattern, journal, re.I)) for name, pattern in dict(
        initialization='initialization failed', runtime='access violation|array out of range|zero divide',
        history='testing start time changed|not enough history', stopout='stop out|margin call',
        invalid_stops='invalid stops', invalid_volume='invalid volume', export='RR05_EXPORT_FAILED',
        no_money='not enough money', market_closed='market closed').items()}
    assert not any(flags[key] for key in ('initialization', 'runtime', 'history', 'stopout', 'export')), flags
    assert 'RR05_EXPORT_COMPLETE' in journal and '127.0.0.1:3010' in journal
    actual = n.h._report_inputs(report)
    # Generic report parser includes Inp*; the current client inputs are distinct.
    text = n.h._read_report(report)
    actual.update(dict(re.findall(r'<b>(Client\w+)=([^<]*)</b>', text)))
    missing = [key for key in inputs if key not in actual]
    assert not missing, ('Missing actual package input receipts', missing)
    assert all(n.h._same_setting(value, actual[key]) for key, value in inputs.items()), 'Package native input mismatch'
    assert START.replace('-', '.') in text and END.replace('-', '.') in text
    metrics = n.h._native_metrics(report)
    metrics.update(equity_dd_pct=n._number(n._metric(text, 'Equity Drawdown Relative')),
        balance_dd_pct=n._number(n._metric(text, 'Balance Drawdown Relative')))
    (out/'report.private.htm.gz').write_bytes(gzip.compress(report.read_bytes(), mtime=0))
    for name in ('deals', 'equity', 'entry_risk', 'contracts', 'coverage', 'benchmarks'):
        path = COMMON/(tag+'-'+name+'.csv')
        assert path.is_file() and path.stat().st_mtime >= began-2, ('Fresh native export absent', name)
        shutil.copy2(path, out/(name+'.csv'))
    trades, ledger = n.trades_from_deals(n.export_rows(out/'deals.csv'))
    assert abs(sum(p['net'] for p in trades)-metrics['net_profit']) < .031, 'Native net does not reconcile'
    assert all(BEGIN <= p['open_epoch'] <= p['close_epoch'] < FINISH for p in trades)
    assert all(not p['partial'] for p in trades), 'Partial exits need explicitly richer downstream ownership'
    ordered = sorted(trades, key=lambda p: (p['open_epoch'], p['position_id']))
    assert all(a['close_epoch'] <= b['open_epoch'] for a, b in zip(ordered, ordered[1:])), 'Same-EA overlap needs richer ownership'
    risks = n.export_rows(out/'entry_risk.csv')
    ids = {p['position_id'] for p in trades}
    assert len(risks) == len(ids) and {int(q['position_id']) for q in risks} == ids
    assert all(q['calculation_ok'] == '1' and q['sl_source'] == 'entry_order' and float(q['unit_risk']) > 0 and q['margin_ok'] == '1' for q in risks)
    trace, coverage = n.export_rows(out/'equity.csv'), n.export_rows(out/'coverage.csv')
    assert len(coverage) == 1
    first, last = min(int(p['epoch']) for p in trace), max(int(p['epoch']) for p in trace)
    coverage = coverage[0]
    assert first == BEGIN and datetime.fromtimestamp(last, timezone.utc).date().isoformat() == '2026-10-16'
    assert int(coverage['m1_count']) > 0 and int(coverage['m1_first']) >= BEGIN and int(coverage['m1_last']) < FINISH
    assert datetime.fromtimestamp(int(coverage['m1_last']), timezone.utc).date().isoformat() == '2026-10-16'
    contracts = n.export_rows(out/'contracts.csv')
    assert len(contracts) == 1 and int(contracts[0]['account_leverage']) == 2000
    for p in trades:
        p['end_censored'] = any('end of test' in comment.lower() for comment in p['exit_comments'])
    result = dict(tag=tag, slug=row['slug'], window=[START, END], inputs=actual, native=metrics,
        trades=trades, ledger=ledger, flags=flags, coverage=coverage, source_contract=contracts[0],
        source_deposit=10000, source_fixed_risk_usd=50, source_server=SERVER,
        actual_source_server_verified=True, actual_source_servers=servers,
        public_ex5_sha256=row['public_ex5_sha256'], binary_sha256=sha(binary),
        source_graph_callback_only_parity=True, build_receipt_sha256=sha(ROOT/'builds'/row['slug']/'build.json'),
        native_plan_sha256=sha(ROOT/'native_plan.json'), native_freeze_sha256=sha(ROOT/'FROZEN.json'),
        first_captured_snapshot_utc=prior.utc(first), last_captured_snapshot_utc=prior.utc(last),
        boundary_liquidation_positions=[p['position_id'] for p in trades if p['end_censored']],
        entry_risk_receipts=len(risks), standalone_source_only=True, live_changes=False,
        tick_notes=sorted(set(re.findall(r'real ticks begin from[^\r\n]*|real ticks absent[^\r\n]*|ticks discarded[^\r\n]*', journal, re.I)))[:30],
        seconds=time.time()-began, costs='Native recorded source fills/commission/fees/swap, not certified current-demo or historical execution costs.')
    save(out/'results.json', result)
    ensure_free()
    print('DONE Top5 native '+row['slug']+'; positions='+str(len(trades)), flush=True)
    return result


def publish_index(state):
    plan = verify_freeze()
    cases = []
    for row in plan['cases']:
        receipt = state['complete'].get(row['slug'])
        if receipt:
            assert sha(receipt['path']) == receipt['sha256']
            cases.append(dict(slug=row['slug'], symbol=row['symbol'], **receipt))
    save(ROOT/'native_cases.json', dict(start=START, end_exclusive=END, source_server=SERVER,
        cases=cases, complete=len(cases), total=5, no_live_changes=True, native_source_only=True,
        source_fixed_risk_usd=50, current_client_minimum_lot_override=True, Nasdaq_DI='OFF'))


def run():
    plan = verify_freeze()
    state = read(ROOT/'native_status.json') if (ROOT/'native_status.json').exists() else dict(
        total=5, complete={}, failed={}, window=[START, END], live_changes=False)
    for row in plan['cases']:
        slug = row['slug']
        if slug in state['complete']:
            assert sha(state['complete'][slug]['path']) == state['complete'][slug]['sha256']
            continue
        try:
            verify_freeze()
            binary, proof = build(row)
            result = run_case(row, binary, proof)
            path = ROOT/slug/'results.json'
            state['complete'][slug] = dict(path=str(path), sha256=sha(path), trades=len(result['trades']),
                history_quality=result['native']['history_quality'], seconds=result['seconds'])
            state['failed'].pop(slug, None)
        except Exception as exc:
            state['failed'][slug] = dict(error=str(exc), trace=traceback.format_exc()[-6000:])
            save(ROOT/'native_status.json', state)
            print('FAILED Top5 native '+slug+': '+str(exc), flush=True)
            raise
        save(ROOT/'native_status.json', state)
        publish_index(state)
    ensure_free()
    publish_index(state)
    print('Five current Top5 native sources complete; no normal terminal/account changes.', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['run']:
        with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lock:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            run()
    else:
        raise SystemExit('Use prepare or run')
