"""Read-only final-export horizon repair; unchanged package trading callbacks.

Top5's one-second timer lets the tester create an artificial final liquidation
after the last market tick's TimeCurrent. Export complete native history and
explicitly tag the noncausal final snapshot. No trading logic/input changes.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import inspect
import msvcrt
import sys
import time


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('frozen_top5_native_protocol', ROOT/'native_run.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)
ORIGINAL_VERIFY = v.verify_freeze
ORIGINAL_FREE = v.ensure_free


def bounded_free():
    deadline = time.time()+60
    while True:
        try:
            return ORIGINAL_FREE()
        except AssertionError as error:
            if 'port occupied' not in str(error).lower() or time.time() >= deadline:
                raise
            time.sleep(2)


def prepare():
    assert not (ROOT/'EXPORT V3 FREEZE.json').exists()
    ORIGINAL_VERIFY()
    old = v.read(ROOT/'RESUME FREEZE.json')
    assert all(v.sha(path) == digest for path, digest in old['files'].items())
    state = v.read(ROOT/'native_status_v2.json')
    assert set(state['complete']) == {'gold-overnight-value-area', 'xau-rsi-vwap'}
    assert set(state['failed']) == {'nasdaq-overnight'}
    assert 'Missing/unsupported position' in state['failed']['nasdaq-overnight']['error']
    bounded_free()
    text = v.n.h.text(ROOT/'ReadOnlyAuditBase.mqh')
    replacements = {
        'FileWrite(rr05_equity_file,"epoch","balance","equity");':
        'FileWrite(rr05_equity_file,"epoch","balance","equity","phase");',
        'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));':
        'FileWrite(rr05_equity_file,(long)now,DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"market_sample");',
        'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2));':
        'FileWrite(rr05_equity_file,(long)TimeCurrent(),DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE),2),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),"finish_after_native_liquidation");',
        '!HistorySelect(0,TimeCurrent())': '!HistorySelect(0,TimeCurrent()+86400)',
    }
    for before, after in replacements.items():
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    reversed_export = text
    for before, after in reversed(list(replacements.items())):
        assert reversed_export.count(after) == 1
        reversed_export = reversed_export.replace(after, before)
    assert reversed_export == v.n.h.text(ROOT/'ReadOnlyAuditBase.mqh'), 'Exactly four observational-only header edits'
    (ROOT/'ReadOnlyAuditBaseV3.mqh').write_text(text, encoding='utf-8')
    header = v.n.h.text(ROOT/'ReadOnlyAudit.mqh')
    assert header.count('ReadOnlyAuditBase.mqh') == 1
    (ROOT/'ReadOnlyAuditV3.mqh').write_text(header.replace('ReadOnlyAuditBase.mqh', 'ReadOnlyAuditBaseV3.mqh'), encoding='utf-8')
    rejected = ROOT/'nasdaq-overnight'
    evidence = [rejected/name for name in ('inputs.set', 'deals.csv', 'equity.csv', 'entry_risk.csv',
        'coverage.csv', 'contracts.csv', 'benchmarks.csv', 'report.private.htm.gz', 'journal.private.txt.gz')]
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(), revision=3,
        original_native_protocol_sha256=v.sha(ROOT/'FROZEN.json'), earlier_resume_sha256=v.sha(ROOT/'RESUME FREEZE.json'),
        previously_completed_cases=sorted(state['complete']), remaining_cases=3,
        prior_failed_export_evidence={str(p): v.sha(p) for p in evidence},
        failure='Final forced tester exit at23:59:58 is later than last market TimeCurrent20:54:59. Old HistorySelect end omitted it.',
        only_changes=['Read-only HistorySelect export horizon TimeCurrent+86400 catches native-generated final deals.',
            'Equity CSV phase identifies market_sample versus finish_after_native_liquidation. Never treat final liquidated account cash as contemporaneous floating equity.',
            'New builds-v3/cases-v3 paths and native_status_v3 preserve rejected export evidence and both accepted old cases.'],
        strategy_parameters_dates_sizing_timers_unchanged=True, no_source_reselection=True,
        no_synthetic_closing_deals=True, live_changes=False)
    v.save(ROOT/'EXPORT V3 PLAN.json', plan)
    files = {str(p): v.sha(p) for p in (ROOT/'export_v3.py', ROOT/'ReadOnlyAuditBaseV3.mqh', ROOT/'ReadOnlyAuditV3.mqh',
        ROOT/'EXPORT V3 PLAN.json', ROOT/'native_status_v2.json', ROOT/'RESUME FREEZE.json', ROOT/'FROZEN.json', *evidence)}
    v.save(ROOT/'EXPORT V3 FREEZE.json', dict(files=files, frozen_before_remaining_reruns=True,
        unchanged_trading_protocol=True, observational_export_only=True))
    new_state = dict(total=5, complete=state['complete'], failed={}, window=[v.START, v.END],
        live_changes=False, export_v3_plan_sha256=v.sha(ROOT/'EXPORT V3 PLAN.json'))
    v.save(ROOT/'native_status_v3.json', new_state)
    print('Frozen observational export V3; old cases and incomplete export preserved; no strategy change.', flush=True)


def verify():
    plan = ORIGINAL_VERIFY()
    for filename in ('RESUME FREEZE.json', 'EXPORT V3 FREEZE.json'):
        freeze = v.read(ROOT/filename)
        assert all(v.sha(path) == expected for path, expected in freeze['files'].items()), 'Export repair evidence changed'
    return plan


def run():
    verify()
    build_source = inspect.getsource(v.build)
    assert "ROOT/'builds'" in build_source and "ROOT/'ReadOnlyAudit.mqh'" in build_source
    build_source = build_source.replace("ROOT/'builds'", "ROOT/'builds-v3'").replace("ROOT/'ReadOnlyAudit.mqh'", "ROOT/'ReadOnlyAuditV3.mqh'")
    case_source = inspect.getsource(v.run_case)
    assert "out = ROOT/row['slug']" in case_source
    case_source = case_source.replace("out = ROOT/row['slug']", "out = ROOT/'cases-v3'/row['slug']")
    case_source = case_source.replace("'top5-current-source-20261017-'", "'top5-current-source-v3-20261017-'")
    case_source = case_source.replace("ROOT/'builds'", "ROOT/'builds-v3'")
    run_source = inspect.getsource(v.run).replace("'native_status.json'", "'native_status_v3.json'")
    v.ensure_free, v.verify_freeze = bounded_free, verify
    exec(compile(build_source+'\n'+case_source, str(ROOT/'export_v3.py')+'::read_only_header_and_output_revision', 'exec'), v.__dict__)
    original_case = v.run_case
    def case_with_receipt(row, binary, proof):
        result = original_case(row, binary, proof)
        result.update(observational_export_revision=3,
            build_receipt_path=str(ROOT/'builds-v3'/row['slug']/'build.json'),
            export_v3_freeze_sha256=v.sha(ROOT/'EXPORT V3 FREEZE.json'),
            equity_phase_policy='Only market_sample rows may become past floating marks. finish_after_native_liquidation is not causal floating evidence.',
            native_boundary_deals_complete=True)
        v.save(ROOT/'cases-v3'/row['slug']/'results.json', result)
        return result
    v.run_case = case_with_receipt
    exec(compile(run_source, str(ROOT/'export_v3.py')+'::unchanged_case_order_new_status', 'exec'), v.__dict__)
    v.run()


if __name__ == '__main__':
    with (v.BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        if sys.argv[1:] == ['prepare']:
            prepare()
        elif sys.argv[1:] == ['run']:
            run()
        else:
            raise SystemExit('Use prepare or run')
