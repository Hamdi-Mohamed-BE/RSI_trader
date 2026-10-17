"""Reuse audited native tester plumbing only; never invoke old search pipelines."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, os, shutil, sys, time

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
    assert cfg['symbol'] == 'XAUUSD', 'Gold study must never inherit USTEC default'
    frozen = json.loads((R / 'FROZEN.json').read_text())
    assert frozen['locked']['engine_sha256'] == hashlib.sha256((R / 'engine.mq5').read_bytes()).hexdigest()
    assert '!MQLInfoInteger(MQL_TESTER)' in (R / 'engine.mq5').read_text()
    cases = json.loads((R / 'CASES.json').read_text())
    lock = runner.lease()
    try:
        # Fixed cases sequentially: avoid six copies of a multi-year tick cache
        # competing for the user's RAM/disk. Same frozen signals and dates.
        aggregate = R / 'native/cpi-xau-raw-20261016'
        aggregate.mkdir(parents=True, exist_ok=True)
        runner.save(aggregate / 'orchestration.json', dict(cases=cases, optimize=False,
                    mode='Six preregistered fixed cases, sequential isolated launches',
                    reason='Avoid concurrent multi-year tick-cache resource contention',
                    parameters_searched=0, live_changes=False))
        rows = []
        for index, case in enumerate(cases):
            base_stage = 'cpi-xau-raw-20261016-case-' + str(index)
            for attempt in range(3):
                stage = base_stage + ('-retry-' + str(attempt) if attempt else '')
                failed_journal = R / 'native' / stage / 'journal.txt.gz'
                if failed_journal.exists() and not (R / 'native' / stage / 'results.json').exists():
                    previous_log = gzip.decompress(failed_journal.read_bytes()).decode()
                    if 'tester agent authorization error' in previous_log:
                        # Preserve the failed agent-start receipt. No strategy
                        # result was produced; retry the IDENTICAL frozen case.
                        runner.status('RETRY TRANSIENT LOCAL AGENT HANDSHAKE', case=index, failed_stage=stage)
                        continue
                try:
                    row = runner.batch(stage, [case], cfg['start'], cfg['end_exclusive'], model=4,
                                       optimize=False, verbose=True, risk=cfg['risk_percent'], delay=cfg['execution_delay_ms'], symbol=cfg['symbol'])[0]
                    break
                except AssertionError:
                    text = gzip.decompress(failed_journal.read_bytes()).decode() if failed_journal.exists() else ''
                    if 'tester agent authorization error' not in text or attempt == 2:
                        raise
                    runner.status('RETRY TRANSIENT LOCAL AGENT HANDSHAKE', case=index, failed_stage=stage)
                    time.sleep(2)
            else:
                raise RuntimeError('Local agent handshake failed three times; no failed case is reported as a result')
            # Keep the broker contract receipt with this exact native run.
            native_folder = R / 'native' / stage
            values = dict(line.split('=', 1) for line in (native_folder / 'Parameters.set').read_text().splitlines() if '=' in line)
            contract_source = runner.COMMON / (values['InpTag'] + '-0-contract.csv')
            owned = runner.load(native_folder / 'owned-process.json')
            assert contract_source.exists() and contract_source.stat().st_mtime >= owned['started']-2, 'Missing fresh Gold broker contract receipt'
            (native_folder / '0-contract.csv.gz').write_bytes(gzip.compress(contract_source.read_bytes(), mtime=0))
            row = dict(row, index=index, native_case_index=0)
            for suffix in ['deals', 'decisions', 'equity', 'quotes', 'stats', 'contract']:
                shutil.copy2(R / 'native' / stage / ('0-' + suffix + '.csv.gz'), aggregate / (str(index) + '-' + suffix + '.csv.gz'))
            rows.append(row)
            runner.save(R / 'PARTIAL-RESULTS.json', rows)
        assert len(rows) == 6 and all(x['parameters'] == cases[x['index']] for x in rows)
        runner.save(R / 'RESULTS.json', rows)
        runner.status('NATIVE RAW COMPLETE — independent analysis and report next', cases=len(rows),
                      parameters_searched=0, live_changes=False, finished_at_utc=datetime.now(timezone.utc).isoformat())
    finally:
        lock.close()

if __name__ == '__main__':
    main()
