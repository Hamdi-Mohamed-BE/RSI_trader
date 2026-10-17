"""Independent frozen-source, native cash, chronology and artifact verification."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv, gzip, hashlib, json, math
import build_engine

R = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    checks = 0
    def check(v, label):
        nonlocal checks
        assert bool(v), label
        checks += 1
    frozen = json.loads((R / 'FROZEN.json').read_text())
    for name, key in [('config.json', 'config_sha256'), ('calendar.json', 'calendar_sha256'),
                      ('CASES.json', 'cases_sha256'), ('engine.mq5', 'engine_sha256'), ('build_engine.py', 'build_sha256')]:
        check(sha(R / name) == frozen['locked'][key], 'Source freeze: ' + name)
    cases = json.loads((R / 'CASES.json').read_text())
    rows = json.loads((R / 'RESULTS.json').read_text())
    calendar = json.loads((R / 'calendar.json').read_text())['events']
    epochs = {e['epoch'] for e in calendar}
    check(len(rows) == len(cases) == 6, 'Six predeclared cases')
    folder = R / 'native/cpi-raw-20261016'
    manifest = json.loads((folder / 'manifest.json').read_text())
    process = json.loads((folder / 'owned-process.json').read_text())
    check(datetime.fromisoformat(frozen['frozen_at_utc']).timestamp() < process['started'], 'Frozen before tester launch')
    compiled = build_engine.build(cases)
    check((folder / 'OrbSearch.mq5').read_text() == compiled, 'Compiled source equality')
    check(hashlib.sha256(compiled.encode()).hexdigest() == manifest['engine_sha256'], 'Compiled source manifest')
    log = (folder / 'compile.log').read_text(encoding='utf-16', errors='replace')
    check('0 errors, 0 warnings' in log, 'Clean compilation')
    check('!MQLInfoInteger(MQL_TESTER)' in compiled, 'Tester-only guard')
    report = gzip.decompress((folder / 'report.xml.gz').read_bytes())
    details = []
    for row in rows:
        i = row['index']
        check(row['parameters'] == cases[i], 'Case mapping')
        check(row['binary_sha256'] == sha(folder / 'OrbSearch.ex5'), 'Native binary checksum')
        check(row['report_sha256'] == hashlib.sha256(report).hexdigest(), 'Report checksum')
        check(abs(sum(t['net_profit'] for t in row['trades']) - row['native']['net']) < 0.03, 'Ledger/statistic net')
        check(abs(10000 + row['native']['net'] - row['native']['balance']) < 0.03, 'Balance/net')
        check(len(row['trades']) == int(row['native']['trades']), 'Trade count')
        check(row['native']['open_position'] == 0, 'No remaining tester positions')
        check(row['native']['failed_entries'] == 0, 'No unreported entry failures')
        with gzip.open(folder / f'{i}-decisions.csv.gz', 'rt', newline='') as f:
            decisions = list(csv.DictReader(f))
        started = {int(d['event_epoch']) for d in decisions if d['reason'] == 'event_start'}
        unavailable = {int(d['event_epoch']) for d in decisions if d['reason'] == 'no_tradable_event_window'}
        check(started | unavailable == epochs, 'Every scheduled event started or explicitly missing')
        check(int(row['native']['events_seen']) == len(started), 'Native event-start count reconciles')
        entries = [d for d in decisions if d['reason'] in ('entry_continuation', 'entry_fade_min1_5R', 'entry_fade_anchor_diagnostic')]
        check(len(entries) == len(row['trades']), 'Decision/fill count')
        event_counts = Counter(int(d['event_epoch']) for d in entries)
        check(all(n == 1 for n in event_counts.values()), 'One trade per event')
        for t in row['trades']:
            match = [d for d in entries if abs(int(d['epoch']) - t['open_epoch']) <= 2]
            check(len(match) == 1, 'Unambiguous signal/fill matching')
            d = match[0]
            event = int(d['event_epoch'])
            mode = cases[i]['mode']
            check(event in epochs, 'Known CPI release')
            check(t['open_epoch'] >= event + 60, 'No first-minute lookahead')
            check(t['close_epoch'] >= t['open_epoch'], 'Chronological fill/exit')
            check(event + 60 <= int(d['epoch']) < event + (300 if mode == 0 else 600), 'Signal inside frozen entry window')
            check(t['initial_sl'] > 0 and t['initial_tp'] > 0 and t['volume'] > 0, 'Protected position')
            check(float(d['risk_budget']) > 0 and float(d['unit_loss']) > 0, 'Positive planned risk')
            check(float(d['lots']) * float(d['unit_loss']) <= float(d['risk_budget']) + 0.0001, 'Lot rounding does not exceed planned cash risk')
            check(abs(float(d['first_news_close']) - float(d['fair'])) + 1e-7 >= float(d['pre_atr']), 'Impulse threshold at entry')
            if cases[i]['require_positive_spread']:
                check(float(d['request_ask']) > float(d['request_bid']), 'Positive spread required at signal')
            check(float(d['request_ask']) - float(d['request_bid']) <= 0.1 * abs((float(d['request_ask']) if t['side'] == 'buy' else float(d['request_bid'])) - float(d['sl'])) + 1e-7, 'Spread cap at signal')
            if mode == 1:
                check(float(d['entry_rr']) >= 1.5 - 1e-7, 'Strict fade requested RR')
            if mode != 0:
                check(int(d['bar_epoch']) + 60 <= int(d['epoch']), 'Fade bar complete before signal')
                check(abs(t['initial_tp'] - float(d['fair'])) <= 0.011, 'Fade anchor target')
        details.append(dict(index=i, trades=len(row['trades']), events_started=int(row['native']['events_seen']),
                            actual_last_quote_utc=datetime.fromtimestamp(row['native']['last_quote_epoch'], timezone.utc).isoformat(),
                            cash_reconciled=True, live_changes=False))
    result = dict(passed=True, checks=checks, scope='Independent source/hash/cash/causality reconciliation only; NOT a strategy-validation or execution-quality pass',
                  research_only=True, execution_quality_verified=False, live_changes=False, cases=details)
    (R / 'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
