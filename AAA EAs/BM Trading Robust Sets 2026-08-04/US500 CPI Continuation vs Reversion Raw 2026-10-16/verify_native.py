"""Reconcile six separate native US500 replays without trading or retesting.

Independent source/hash/cash/elementary chronology checks, not proof of true
historical tick liquidity or a strategy-validation pass. Each native launch
contains one local case (index 0); RESULTS.json uses global case indices 0..5.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
import build_engine

R = Path(__file__).resolve().parent
AGGREGATE = R / 'native' / 'cpi-us500-raw-20261016'
ENTRY_REASONS = {'entry_continuation', 'entry_fade_min1_5R', 'entry_fade_anchor_diagnostic'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    checks = 0
    def check(value, label):
        nonlocal checks
        assert bool(value), label
        checks += 1

    cfg = load(R / 'config.json')
    frozen = load(R / 'FROZEN.json')
    for name, key in [('config.json','config_sha256'), ('calendar.json','calendar_sha256'),
                      ('CASES.json','cases_sha256'), ('engine.mq5','engine_sha256'), ('build_engine.py','build_sha256')]:
        check(sha(R / name) == frozen['locked'][key], 'Source freeze: ' + name)
    cases = load(R / 'CASES.json')
    rows = load(R / 'RESULTS.json')
    events = load(R / 'calendar.json')['events']
    epochs = {int(e['epoch']) for e in events}
    check(len(rows) == len(cases) == 6, 'Six predeclared cases')
    check(sorted(int(row['index']) for row in rows) == list(range(6)), 'Unique global case indices')
    details = []
    for row in sorted(rows, key=lambda r: int(r['index'])):
        index = int(row['index'])
        case = cases[index]
        check(row['parameters'] == case, f'Case {index}: parameter mapping')
        check(int(row.get('native_case_index',0)) == 0, f'Case {index}: local native index 0')
        stage = row.get('stage', f'cpi-us500-raw-20261016-case-{index}')
        folder = (R / 'native' / stage).resolve()
        check(folder.parent == (R / 'native').resolve(), 'Native folder stays inside this study')
        manifest = load(folder / 'manifest.json')
        process = load(folder / 'owned-process.json')
        check(datetime.fromisoformat(frozen['frozen_at_utc']).timestamp() < process['started'], f'Case {index}: frozen before tester launch')
        check(manifest['cases'] == [case], f'Case {index}: one-case native manifest')
        check(manifest['symbol'] == cfg['symbol'] == 'US500', f'Case {index}: native symbol')
        check(not manifest['optimize'], f'Case {index}: optimization disabled')
        check(int(manifest['model']) == 4, f'Case {index}: requested Model 4 (not a data-quality certificate)')
        check(manifest['start'] == row['start'] == cfg['start'] and manifest['end'] == row['end'] == cfg['end_exclusive'], f'Case {index}: requested dates')
        check(abs(float(manifest['risk']) - float(cfg['risk_percent'])) < 1e-12, f'Case {index}: requested risk')
        compiled = build_engine.build([case])
        check((folder / 'OrbSearch.mq5').read_text(encoding='utf-8-sig') == compiled, f'Case {index}: compiled source equality')
        check(hashlib.sha256(compiled.encode()).hexdigest() == manifest['engine_sha256'], f'Case {index}: compiled source manifest')
        log = (folder / 'compile.log').read_text(encoding='utf-16',errors='replace')
        check('0 errors, 0 warnings' in log, f'Case {index}: clean compilation')
        check('!MQLInfoInteger(MQL_TESTER)' in compiled, f'Case {index}: tester-only guard')
        report_paths = [folder / 'report.htm.gz', folder / 'fullreport.htm.gz']
        report_path = next((path for path in report_paths if path.exists()), None)
        check(report_path is not None, f'Case {index}: native HTML report exists')
        report = gzip.decompress(report_path.read_bytes())
        check(row['binary_sha256'] == sha(folder / 'OrbSearch.ex5'), f'Case {index}: native binary checksum')
        check(row['report_sha256'] == hashlib.sha256(report).hexdigest(), f'Case {index}: native HTML checksum')
        for suffix in ('decisions','quotes','equity','deals','stats'):
            original = folder / f'0-{suffix}.csv.gz'
            aggregate = AGGREGATE / f'{index}-{suffix}.csv.gz'
            check(original.exists() and aggregate.exists(), f'Case {index}: {suffix} original and aggregate exist')
            check(sha(original) == sha(aggregate), f'Case {index}: aggregate {suffix} is the exact original')
        native = row['native']
        trades = row['trades']
        net = sum(float(t['net_profit']) for t in trades)
        check(abs(net - float(native['net'])) < 0.03, f'Case {index}: trade/statistic net')
        check(abs(float(cfg['deposit']) + float(native['net']) - float(native['balance'])) < 0.03, f'Case {index}: balance/net')
        check(len(trades) == int(native['trades']), f'Case {index}: trade count')
        check(int(native['open_position']) == 0, f'Case {index}: no remaining native positions')
        check(int(native['failed_entries']) == 0, f'Case {index}: no entry failures')
        deals = read_csv(AGGREGATE / f'{index}-deals.csv.gz')
        deal_net = sum(float(d[k]) for d in deals for k in ('profit','commission','swap','fee'))
        check(abs(net - deal_net) < 0.03, f'Case {index}: independent native deal cash')
        positions = defaultdict(list)
        for deal in deals:
            positions[int(deal['position_id'])].append(deal)
        check(len(positions) == len(trades), f'Case {index}: native deal position count')
        for position, ds in positions.items():
            opens = [d for d in ds if int(d['entry']) == 0]
            closes = [d for d in ds if int(d['entry']) == 1]
            check(len(opens) == 1 and len(closes) >= 1, f'Case {index}, position {position}: open/close structure')
            check(all(int(d['entry']) in (0,1) for d in ds), f'Case {index}, position {position}: no unsupported reversal deal')
            check(abs(sum(float(d['volume']) for d in opens)-sum(float(d['volume']) for d in closes)) < 1e-7,
                  f'Case {index}, position {position}: volume fully closed')
        decisions = read_csv(AGGREGATE / f'{index}-decisions.csv.gz')
        started = {int(d['event_epoch']) for d in decisions if d['reason'] == 'event_start'}
        unavailable = {int(d['event_epoch']) for d in decisions if d['reason'] == 'no_tradable_event_window'}
        check(started | unavailable == epochs, f'Case {index}: every scheduled event started or explicitly missing')
        check(int(native['events_seen']) == len(started), f'Case {index}: native event-start count')
        entries = [d for d in decisions if d['reason'] in ENTRY_REASONS]
        check(len(entries) == len(trades), f'Case {index}: successful decision/fill count')
        event_counts = Counter(int(d['event_epoch']) for d in entries)
        check(all(n == 1 for n in event_counts.values()), f'Case {index}: one trade per event')
        for trade in trades:
            matches = [d for d in entries if abs(int(d['epoch'])-int(trade['open_epoch'])) <= 2]
            check(len(matches) == 1, f'Case {index}: unambiguous signal/fill matching')
            decision = matches[0]
            event = int(decision['event_epoch'])
            mode = case['mode']
            check(event in epochs, f'Case {index}: known CPI release')
            check(trade['open_epoch'] >= event+60, f'Case {index}: no first-minute lookahead')
            check(trade['close_epoch'] >= trade['open_epoch'], f'Case {index}: chronological fill/exit')
            check(event+60 <= int(decision['epoch']) < event+(300 if mode == 0 else 600), f'Case {index}: signal in frozen entry window')
            check(trade['initial_sl'] > 0 and trade['initial_tp'] > 0 and trade['volume'] > 0, f'Case {index}: protected positive-volume position')
            direction = 1 if trade['side'] == 'buy' else -1
            check(direction*(trade['open_price']-trade['initial_sl']) > 0, f'Case {index}: positive filled stop distance')
            check(direction*(trade['initial_tp']-trade['open_price']) > 0, f'Case {index}: positive filled target distance')
            check(float(decision['risk_budget']) > 0 and float(decision['unit_loss']) > 0, f'Case {index}: positive planned cash risk')
            check(float(decision['lots'])*float(decision['unit_loss']) <= float(decision['risk_budget'])+0.0001,
                  f'Case {index}: lot rounding within planned risk budget')
            check(abs(float(decision['first_news_close'])-float(decision['fair']))+1e-7 >= float(decision['pre_atr']), f'Case {index}: impulse threshold')
            bid, ask = float(decision['request_bid']), float(decision['request_ask'])
            check(math.isfinite(bid) and math.isfinite(ask) and ask >= bid > 0, f'Case {index}: valid requested quote')
            if case['require_positive_spread']:
                check(ask > bid, f'Case {index}: positive spread at signal')
            request_entry = ask if direction > 0 else bid
            check(ask-bid <= 0.1*abs(request_entry-float(decision['sl']))+1e-7, f'Case {index}: spread cap')
            if mode == 1:
                check(float(decision['entry_rr']) >= 1.5-1e-7, f'Case {index}: strict fade requested RR')
            if mode != 0:
                check(int(decision['bar_epoch'])+60 <= int(decision['epoch']), f'Case {index}: fade candle completed before signal')
                check(abs(trade['initial_tp']-float(decision['fair'])) <= 0.011, f'Case {index}: fade anchor target')
        details.append(dict(index=index, native_case_index=0, stage=stage, trades=len(trades),
                            events_started=len(started), events_explicitly_missing=len(unavailable),
                            actual_last_quote_utc=datetime.fromtimestamp(float(native['last_quote_epoch']),timezone.utc).isoformat(),
                            native_report=report_path.relative_to(R).as_posix(), report_sha256=row['report_sha256'],
                            binary_sha256=row['binary_sha256'], cash_reconciled=True, live_changes=False))
    result = dict(passed=True, checks=checks,
                  scope='Independent source/hash/cash/elementary causality reconciliation only; NOT a strategy-validation or execution-quality pass',
                  orchestration='Six sequential single-case native launches; global index maps to native local index 0 in each originating case folder',
                  research_only=True, execution_quality_verified=False, live_changes=False, cases=details)
    (R / 'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
