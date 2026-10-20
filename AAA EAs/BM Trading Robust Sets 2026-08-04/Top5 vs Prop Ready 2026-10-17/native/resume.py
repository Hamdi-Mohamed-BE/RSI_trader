"""Post-shutdown port-linger recovery; no trading-model changes.

The first source completed every trading/audit check and was saved. Only the
immediate final free-port assertion failed. Preserve that original attempt and
freeze this read-only bounded-wait/resume protocol before the other four cases.
"""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import inspect
import msvcrt
import sys
import time


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('immutable_top5_native_v1', ROOT/'native_run.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)
ORIGINAL_FREE = v.ensure_free
ORIGINAL_VERIFY = v.verify_freeze


def bounded_free():
    deadline = time.time()+60
    while True:
        try:
            return ORIGINAL_FREE()
        except AssertionError as error:
            # Never stop an existing process or modify listener state. Only
            # retry the observational port assertion after native shutdown.
            if 'port occupied' not in str(error).lower() or time.time() >= deadline:
                raise
            time.sleep(2)


def prepare():
    assert not (ROOT/'RESUME FREEZE.json').exists()
    plan = ORIGINAL_VERIFY()
    bounded_free()
    old_state = v.read(ROOT/'native_status.json')
    assert not old_state['complete'] and set(old_state['failed']) == {'gold-overnight-value-area'}
    failure = old_state['failed']['gold-overnight-value-area']
    assert failure['error'] == 'Tester port occupied; no process stopped'
    assert 'run_case' in failure['trace'] and 'line 312' in failure['trace']
    case = ROOT/'gold-overnight-value-area'
    result = v.read(case/'results.json')
    assert result['actual_source_server_verified'] and result['actual_source_servers'] == [v.SERVER]
    assert not any(result['flags'].values())
    assert result['source_graph_callback_only_parity']
    assert result['native_plan_sha256'] == v.sha(ROOT/'native_plan.json')
    assert result['native_freeze_sha256'] == v.sha(ROOT/'FROZEN.json')
    receipt = dict(path=str(case/'results.json'), sha256=v.sha(case/'results.json'),
        trades=len(result['trades']), history_quality=result['native']['history_quality'], seconds=result['seconds'])
    recovered = [case/'results.json', case/'inputs.set', ROOT/'builds/gold-overnight-value-area/build.json']
    recovered.extend(case/(name+'.csv') for name in ('deals', 'equity', 'entry_risk', 'contracts', 'coverage', 'benchmarks'))
    audit = dict(recovery_utc=datetime.now(timezone.utc).isoformat(), first_case='gold-overnight-value-area',
        first_case_fully_completed_before_postcondition_failure=True,
        previous_failure_preserved=str(ROOT/'native_status.json'), recovered_receipt=receipt,
        source_results_already_observed=True, source_reselection=False,
        change='Only retry free-port observation for up to60seconds after shutdown; no kills, no socket changes, no strategy/date/settings/risk edits.',
        unchanged_source_protocol_sha256=v.sha(ROOT/'FROZEN.json'), remaining_cases=4)
    v.save(ROOT/'RESUME PLAN.json', audit)
    files = {str(p): v.sha(p) for p in [ROOT/'resume.py', ROOT/'RESUME PLAN.json', ROOT/'native_status.json', ROOT/'FROZEN.json', *recovered]}
    v.save(ROOT/'RESUME FREEZE.json', dict(files=files, frozen_before_remaining_four_cases=True,
        source_reselection=False, original_native_protocol_unchanged=True))
    state = dict(total=5, complete={'gold-overnight-value-area': receipt}, failed={},
        window=[v.START, v.END], live_changes=False, recovery_plan_sha256=v.sha(ROOT/'RESUME PLAN.json'))
    v.save(ROOT/'native_status_v2.json', state)
    v.publish_index(state)
    print('Preserved initial post-shutdown failure; recovered fully audited gold source; froze unchanged four-case continuation.', flush=True)


def verify():
    plan = ORIGINAL_VERIFY()
    frozen = v.read(ROOT/'RESUME FREEZE.json')
    assert all(v.sha(path) == expected for path, expected in frozen['files'].items()), 'Resume evidence changed'
    return plan


def run():
    verify()
    source = inspect.getsource(v.run)
    assert "'native_status.json'" in source
    source = source.replace("'native_status.json'", "'native_status_v2.json'")
    v.ensure_free = bounded_free
    v.verify_freeze = verify
    exec(compile(source, str(ROOT/'resume.py')+'::unchanged_case_protocol_new_status', 'exec'), v.__dict__)
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
