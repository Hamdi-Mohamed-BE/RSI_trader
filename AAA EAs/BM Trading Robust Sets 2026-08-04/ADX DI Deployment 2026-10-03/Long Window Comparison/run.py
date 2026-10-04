"""Frozen 18-run long-window comparison; isolated tester only, no live API."""
from pathlib import Path
import gzip, importlib.util, json, os, shutil

R = Path(__file__).resolve().parent
D = R.parent
B = D.parent
S = B / 'ADX DI Five Bot Review 2026-10-03'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
spec = importlib.util.spec_from_file_location('long_study_runner', S / 'run.py')
m = importlib.util.module_from_spec(spec)
code = (S / 'run.py').read_text().replace('ADXDI20261003', 'ADXDILong20261003').replace('adxdi20261003', 'adxdilong20261003')
exec(compile(code, str(S / 'run.py'), 'exec'), m.__dict__)
m.R = R
m.OUT = R / 'native'
m.DEST = m.T / 'MQL5/Experts/AAA Research/ADXDILong20261003'
WINDOWS = {'3y': ('2023.10.02', '2026.10.02'), '5y': ('2021.10.02', '2026.10.02')}
ORDER = ('ema3', 'london', 'asia', 'trend', 'rsi')


def prepare():
    bots = m.load(S / 'bots.json')
    selection = m.load(D / 'SELECTION.json')
    assert m.load(D / 'PARITY.json')['passed']
    profiles = {p['key']: p for p in selection['profiles'].values()}
    cases, build = [], {}
    for period, (start, end) in WINDOWS.items():
        for key in ORDER:
            b = bots[key]
            assert m.sha(Path(b['original'])) == b['original_sha'], ('Baseline changed', key)
            assert m.sha(Path(b['source'])) == b['source_sha'], ('Baseline source changed', key)
            for arm in (('unchanged',) if key == 'rsi' else ('baseline', 'filtered')):
                p = profiles.get(key)
                binary = B / p['expert'] if arm == 'filtered' else Path(b['original'])
                source = binary.with_suffix('.mq5')
                inputs = dict(p['inputs'] if arm == 'filtered' else b['inputs'])
                expected = p['expert_sha'] if arm == 'filtered' else b['original_sha']
                assert m.sha(binary) == expected
                tag = f'{key}-{period}-{arm}'
                item = dict(key=key, period=period, arm=arm, tag=tag, start=start, end=end,
                            binary=str(binary), source=str(source), binary_sha=expected,
                            source_sha=m.sha(source), inputs=inputs,
                            symbol=b['symbol'], timeframe=b['period'])
                cases.append(item)
                build[tag] = dict(source_sha=item['source_sha'], binary_sha=expected,
                                  original_sha=expected, source=str(source), binary=str(binary))
                target = m.DEST / tag
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(binary, target / 'Original.ex5')
    frozen = dict(protocol_sha=m.sha(R / 'PROTOCOL.txt'), windows=WINDOWS,
                  selection_sha=m.sha(D / 'SELECTION.json'), cases=cases,
                  runs=len(cases), optimization=False, live_terminal_changed=False)
    frozen = json.loads(json.dumps(frozen))
    config = R / 'run-config.json'
    if config.exists():
        assert m.load(config) == frozen, 'Frozen inputs changed'
    else:
        m.save(config, frozen)
    if (R / 'BUILD.json').exists():
        assert m.load(R / 'BUILD.json') == build
    else:
        m.save(R / 'BUILD.json', build)
    return bots, cases


def main():
    bots, cases = prepare()
    results = []
    for c in cases:
        m.START, m.END = c['start'], c['end']
        b = dict(bots[c['key']])
        b.update(inputs=c['inputs'], original=c['binary'],
                 label=f"{b['label']} / {c['period']} / {c['arm']}")
        result = m.case(c['tag'], b, 'BASE', True)
        result = dict(result, key=c['key'], period=c['period'], arm=c['arm'],
                      start=c['start'], end_exclusive=c['end'])
        results.append(result)
        m.save(R / 'PROGRESS.json', results)
    m.save(R / 'SUMMARY.json', results)
    m.status('COMPLETE: 18 frozen native comparisons; no live terminal changed')


if __name__ == '__main__':
    main()
