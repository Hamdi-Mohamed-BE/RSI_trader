"""Explicit cached Trial16 fallback; preserves the failed Trial15 feed attempt.

Only feed identity/provenance verification and extra read-only benchmark exports
differ from v1. No strategy parameter, date, source risk or execution rule changes.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, importlib.util, inspect, json, msvcrt, re, shutil, sys

R = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('prop1k_native_v1', R / 'native_run.py')
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)
v.S = R / 'native_sources_v2'
v.n.R = v.S
v.SERVER = 'Exness-MT5Trial16'
v.CONNECTION_SOURCE = v.B / 'FTMO Exit Management Research 2026-09-27/native/gold-native/tester.ini'


def prepare():
    assert not (R / 'native_plan_v2.json').exists() and not (R / 'native_status_v2.json').exists()
    original = v.verify_freeze()
    v.connection_header()
    plan = dict(original)
    plan.update(source_server=v.SERVER,
        source_revision='Explicit Trial16 cached feed fallback after requested Trial15 authorization was ignored by portable terminal.',
        previous_attempt=str(R / 'native_status.json'), previous_freeze_sha256=v.sha(R / 'native_freeze.json'),
        prior_attempt_usable=False,
        current_live_demo_reference='BROKER.json describes Trial15. These standalone historical sources are Trial16 and are not claimed to be the same account/feed.',
        original_rules_dates_sizing_unchanged=True,
        actual_server_verification='Every accepted case requires fresh private terminal journal authorization on Trial16; requested INI alone is not evidence.',
        created_utc=datetime.now(timezone.utc).isoformat())
    plan['source_hashes'] = dict(original['source_hashes'])
    plan['source_hashes'].update({str(p): v.sha(p) for p in (v.CONNECTION_SOURCE,
        R / 'native_freeze.json', R / 'native_sources/ReadOnlyAudit.mqh', R / 'BROKER.json')})
    v.save(R / 'native_plan_v2.json', plan)
    v.save(R / 'native_freeze_v2.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        files={str(p): v.sha(p) for p in (R / 'native_run_v2.py', R / 'native_run.py',
            v.S / 'ReadOnlyAudit.mqh', R / 'native_plan_v2.json')},
        source_files=plan['source_hashes'], cases=9, searched_configurations=0,
        feed_fallback_frozen_before_reruns=True, no_strategy_reselection=True))
    print('FROZEN V2: cached Trial16 source feed; current broker reference Trial15; all strategy/date/risk settings unchanged.', flush=True)


def verify_freeze():
    f = v.read(R / 'native_freeze_v2.json')
    assert all(v.sha(p) == digest for p, digest in f['files'].items()), 'V2 native protocol changed'
    assert all(v.sha(p) == digest for p, digest in f['source_files'].items()), 'V2 source/provenance changed'
    return v.read(R / 'native_plan_v2.json')


def publish_index(current=None):
    state_path = R / 'native_status_v2.json'
    rows = v.read(state_path)['complete'] if state_path.exists() else {}
    if current is not None:
        path = v.S / current['slug'] / 'results.json'
        rows[current['slug']] = dict(path=str(path), sha256=v.sha(path), trades=len(current['trades']))
    plan = verify_freeze()
    entries = []
    for row in plan['cases']:
        receipt = rows.get(row['slug'])
        if receipt is None:
            continue
        assert v.sha(receipt['path']) == receipt['sha256']
        entries.append(dict(slug=row['slug'], symbol=row['symbol'], **receipt))
    v.save(R / 'native_cases.json', dict(start=v.START, end_exclusive=v.END,
        source_server=v.SERVER, current_broker_server='Exness-MT5Trial15',
        cases=entries, complete=len(entries), total=9, native_source_only=True,
        source_revision='V2 explicit cached Trial16 fallback',
        entry_risk_receipts='Source folder/entry_risk.csv uses position_id and OrderCalcProfit unit_risk at native deal-add callback. calculation_ok=1 required; sl_source reports entry_order or contemporaneous position. Includes quote, source_volume, open_swap and margin_one_lot. Not pre-request risk.',
        no_live_changes=True))


_old_case = v.run_case


def run_case(row, binary, build):
    result = _old_case(row, binary, build)
    out = v.S / row['slug']
    journal = gzip.decompress((out / 'journal.private.txt.gz').read_bytes()).decode('utf-8')
    actual_servers = sorted(set(re.findall(r'authorized on (\S+) through', journal)))
    assert actual_servers == [v.SERVER], ('Wrong actual source server; not silently substituted', actual_servers)
    risks = list(csv.DictReader((out / 'entry_risk.csv').open(encoding='utf-8-sig')))
    ids = {int(t['position_id']) for t in result['trades']}
    assert len(risks) == len(ids) and {int(x['position_id']) for x in risks} == ids, 'Missing/duplicate native entry-risk receipts'
    assert all(x['calculation_ok'] == '1' and float(x['unit_risk']) > 0 for x in risks)
    contracts = list(csv.DictReader((out / 'contracts.csv').open(encoding='utf-8-sig')))
    assert len(contracts) == 1 and int(contracts[0]['account_leverage']) == 2000
    current = v.read(R / 'BROKER.json')['symbols'][row['symbol']]
    source = contracts[0]
    mappings = dict(contract_size='trade_contract_size', volume_min='volume_min', volume_step='volume_step',
        volume_max='volume_max', calc_mode='trade_calc_mode', profit_currency='currency_profit', tick_size='trade_tick_size')
    differences = {}
    for a, b in mappings.items():
        left, right = source[a], current[b]
        same = left == str(right) if a == 'profit_currency' else abs(float(left)-float(right)) < 1e-9
        if not same:
            differences[a] = dict(source=left, current=right)
    assert not any(k in differences for k in ('contract_size', 'volume_min', 'volume_step', 'calc_mode', 'profit_currency', 'tick_size')), differences
    common = Path(v.os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxRR05All20261008'
    benchmark = common / (result['tag'] + '-benchmarks.csv')
    assert benchmark.exists()
    shutil.copy2(benchmark, out / 'benchmarks.csv')
    result.update(actual_source_servers=actual_servers, actual_source_server_verified=True,
        source_server=v.SERVER, current_broker_server='Exness-MT5Trial15', source_spec_differences= differences,
        source_contract=source, entry_risk_receipts=len(risks), unit_risk_receipts_verified=True,
        native_plan_sha256=v.sha(R / 'native_plan_v2.json'), native_freeze_sha256=v.sha(R / 'native_freeze_v2.json'))
    v.save(out / 'results.json', result)
    publish_index(result)
    return result


def run():
    # Reuse the frozen v1 mechanics, changing only protocol/status artifact names.
    source = inspect.getsource(v.run)
    assert source.count("'native_status.json'") == 1
    source = source.replace("'native_status.json'", "'native_status_v2.json'")
    v.verify_freeze = verify_freeze
    v.run_case = run_case
    exec(compile(source, str(R / 'native_run_v2.py')+'::v2_protocol_names', 'exec'), v.__dict__)
    v.run()
    publish_index()


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:2] == ['run']:
        with (v.B / 'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
            lease.seek(0)
            msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            run()
    else:
        raise SystemExit('Use prepare or run [optional slug ...]')
