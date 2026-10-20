"""Bookkeeping-only continuation: point completion receipts at cases-v3.

The immutable V3 test completed and saved Nasdaq Overnight successfully; its
outer batch still looked at the V1 result path. Preserve that failure status,
index the existing verified case and run only the final two unchanged tests.
"""
from pathlib import Path
import importlib.util
import inspect
import msvcrt
import sys


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('frozen_export_v3', ROOT/'export_v3.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
v = p.v
OLD_VERIFY = p.verify


def prepare():
    assert not (ROOT/'CONTINUATION FREEZE.json').exists()
    OLD_VERIFY()
    p.bounded_free()
    old = v.read(ROOT/'native_status_v3.json')
    assert set(old['complete']) == {'gold-overnight-value-area', 'xau-rsi-vwap'}
    assert set(old['failed']) == {'nasdaq-overnight'}
    assert 'No such file or directory' in old['failed']['nasdaq-overnight']['error']
    folder = ROOT/'cases-v3/nasdaq-overnight'
    result = v.read(folder/'results.json')
    assert result['observational_export_revision'] == 3 and result['native_boundary_deals_complete']
    assert result['actual_source_servers'] == [v.SERVER]
    assert not any(result['flags'][key] for key in ('initialization', 'runtime', 'history', 'stopout', 'export'))
    receipt = dict(path=str(folder/'results.json'), sha256=v.sha(folder/'results.json'),
        trades=len(result['trades']), history_quality=result['native']['history_quality'], seconds=result['seconds'])
    files = [ROOT/'continue_v3.py', ROOT/'native_status_v3.json', ROOT/'EXPORT V3 FREEZE.json',
             folder/'results.json', ROOT/'builds-v3/nasdaq-overnight/build.json']
    files += [folder/(key+'.csv') for key in ('deals', 'equity', 'entry_risk', 'coverage', 'contracts', 'benchmarks')]
    v.save(ROOT/'CONTINUATION PLAN.json', dict(
        change='Only completion-index path corrected from ROOT/slug to ROOT/cases-v3/slug; separate status preserves earlier bookkeeping failure.',
        recovered_case=receipt, remaining_cases=2, all_trading_and_export_parameters_unchanged=True,
        no_test_rerun_or_reselection=True, source_graph_and_inputs_unchanged=True))
    files.append(ROOT/'CONTINUATION PLAN.json')
    v.save(ROOT/'CONTINUATION FREEZE.json', dict(files={str(path): v.sha(path) for path in files},
        bookkeeping_only=True, frozen_before_last_two_cases=True))
    state = dict(old, complete={**old['complete'], 'nasdaq-overnight': receipt}, failed={})
    v.save(ROOT/'native_status_v4.json', state)
    v.publish_index(state)
    print('Recovered completed V3 Nasdaq source; fixed only receipt-index path; three accepted cases.', flush=True)


def verify():
    result = OLD_VERIFY()
    freeze = v.read(ROOT/'CONTINUATION FREEZE.json')
    assert all(v.sha(path) == expected for path, expected in freeze['files'].items()), 'Continuation evidence changed'
    return result


def run():
    verify()
    source = inspect.getsource(p.run)
    old = 'run_source = inspect.getsource(v.run).replace("\'native_status.json\'", "\'native_status_v3.json\'")'
    new = 'run_source = inspect.getsource(v.run).replace("\'native_status.json\'", "\'native_status_v4.json\'").replace("path = ROOT/slug/\'results.json\'", "path = ROOT/\'cases-v3\'/slug/\'results.json\'")'
    assert source.count(old) == 1
    source = source.replace(old, new)
    p.verify = verify
    exec(compile(source, str(ROOT/'continue_v3.py')+'::bookkeeping_path_only', 'exec'), p.__dict__)
    p.run()


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
