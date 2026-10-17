"""Reuse audited native tester plumbing only; never invoke old search pipelines."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, sys

R = Path(__file__).resolve().parent
B = R.parent
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(R))
import build_engine

def main():
    import prepare
    prepare.main()
    spec = importlib.util.spec_from_file_location('frozen_news_raw_native_runner', B / 'US100 News Reversion Pipeline 2020-2024 2026-10-08/runner.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.R = R
    runner.B = B
    runner.CONFIG = json.loads((R / 'config.json').read_text())
    runner.build_engine = build_engine
    cfg = runner.CONFIG
    frozen = json.loads((R / 'FROZEN.json').read_text())
    assert frozen['locked']['engine_sha256'] == hashlib.sha256((R / 'engine.mq5').read_bytes()).hexdigest()
    assert '!MQLInfoInteger(MQL_TESTER)' in (R / 'engine.mq5').read_text()
    cases = json.loads((R / 'CASES.json').read_text())
    lock = runner.lease()
    try:
        rows = runner.batch('cpi-raw-20261016', cases, cfg['start'], cfg['end_exclusive'], model=4,
                            optimize=True, verbose=True, risk=cfg['risk_percent'], delay=cfg['execution_delay_ms'])
        assert len(rows) == 6 and all(x['parameters'] == cases[x['index']] for x in rows)
        runner.save(R / 'RESULTS.json', rows)
        runner.status('NATIVE RAW COMPLETE — independent analysis and report next', cases=len(rows),
                      parameters_searched=0, live_changes=False, finished_at_utc=datetime.now(timezone.utc).isoformat())
    finally:
        lock.close()

if __name__ == '__main__':
    main()
