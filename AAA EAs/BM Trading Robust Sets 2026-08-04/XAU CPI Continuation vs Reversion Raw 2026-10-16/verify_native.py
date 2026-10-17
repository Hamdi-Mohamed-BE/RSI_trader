"""Reconcile six native gold replays, contract units, and frozen raw mechanics.

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
import re
from html import unescape
import build_engine
from test_protocol import canonical

R = Path(__file__).resolve().parent
AGGREGATE = R / 'native' / 'cpi-xau-raw-20261016'
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
                      ('CASES.json','cases_sha256'), ('engine.mq5','engine_sha256'), ('build_engine.py','build_sha256'),
                      ('run_study.py','run_sha256')]:
        check(sha(R / name) == frozen['locked'][key], 'Source freeze: ' + name)
    prior = R.parent / 'US500 CPI Continuation vs Reversion Raw 2026-10-16'
    check(canonical((R/'engine.mq5').read_text(), gold=True) == canonical((prior/'engine.mq5').read_text()),
          'Core strategy parity: only identifiers and metadata receipt differ')
    check((R/'build_engine.py').read_bytes() == (prior/'build_engine.py').read_bytes(), 'Builder parity')
    check(cfg['continuation']['maximum_hold_minutes_from_fill'] == 15 and cfg['reversion']['maximum_hold_minutes_from_fill'] == 30,
          'User-confirmed original 15/30-minute holds')
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
        stage = row.get('stage', f'cpi-xau-raw-20261016-case-{index}')
        folder = (R / 'native' / stage).resolve()
        check(folder.parent == (R / 'native').resolve(), 'Native folder stays inside this study')
        manifest = load(folder / 'manifest.json')
        process = load(folder / 'owned-process.json')
        check(datetime.fromisoformat(frozen['frozen_at_utc']).timestamp() < process['started'], f'Case {index}: frozen before tester launch')
        check(manifest['cases'] == [case], f'Case {index}: one-case native manifest')
        check(manifest['symbol'] == cfg['symbol'] == 'XAUUSD', f'Case {index}: native symbol')
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
        report_text = report.decode('utf-16' if report[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig', errors='replace')
        visible_report = unescape(re.sub(r'<[^>]*>', ' ', report_text))
        check(re.search(r'Symbol:\s*XAUUSD\b', visible_report) is not None, f'Case {index}: actual HTML gold symbol')
        check(cfg['start'].replace('-', '.') in visible_report and cfg['end_exclusive'].replace('-', '.') in visible_report,
              f'Case {index}: actual HTML dates')
        check('InpRiskPct=0.25' in report_text, f'Case {index}: actual HTML risk')
        check('Currency=USD' in (folder/'tester.ini').read_text(encoding='utf-8-sig'), f'Case {index}: native USD account')
        for suffix in ('decisions','quotes','equity','deals','stats','contract'):
            original = folder / f'0-{suffix}.csv.gz'
            aggregate = AGGREGATE / f'{index}-{suffix}.csv.gz'
            check(original.exists() and aggregate.exists(), f'Case {index}: {suffix} original and aggregate exist')
            check(sha(original) == sha(aggregate), f'Case {index}: aggregate {suffix} is the exact original')
        contracts = read_csv(AGGREGATE / f'{index}-contract.csv.gz')
        check(len(contracts) == 1, f'Case {index}: one fresh native contract receipt')
        contract = contracts[0]
        check(contract['symbol'] == 'XAUUSD', f'Case {index}: contract symbol')
        check(contract['currency_profit'] == 'USD', f'Case {index}: gold quote/profit currency USD')
        tick = float(contract['tick_size'])
        point = float(contract['point'])
        contract_size = float(contract['contract_size'])
        volume_step, volume_min, volume_max = (float(contract[k]) for k in ('volume_step','volume_min','volume_max'))
        tick_loss, tick_profit = float(contract['tick_value_loss']), float(contract['tick_value_profit'])
        check(all(math.isfinite(v) and v > 0 for v in (tick,point,contract_size,volume_step,volume_min,volume_max,tick_loss,tick_profit)),
              f'Case {index}: finite positive gold contract specifications')
        check(volume_max >= volume_min, f'Case {index}: sensible broker lot limits')
        unit_cash_loss, unit_cash_profit = tick_loss/tick, tick_profit/tick
        check(abs(unit_cash_loss-contract_size) <= max(1e-6, contract_size*1e-6), f'Case {index}: actual USD loss conversion agrees with contract size')
        check(abs(unit_cash_profit-contract_size) <= max(1e-6, contract_size*1e-6), f'Case {index}: actual USD profit conversion agrees with contract size')
        price_tol = max(1e-8,tick*1e-5)
        native = row['native']
        requested_start = int(datetime.fromisoformat(cfg['start']).replace(tzinfo=timezone.utc).timestamp())
        requested_end = int(datetime.fromisoformat(cfg['end_exclusive']).replace(tzinfo=timezone.utc).timestamp())
        last_quote = int(float(native['last_quote_epoch']))
        latest_cpi = max(epochs)
        check(requested_start <= last_quote < requested_end, f'Case {index}: native cutoff stays within requested study')
        check(last_quote >= latest_cpi+3600, f'Case {index}: actual native cutoff covers latest scheduled CPI plus full event window')
        equity_rows = read_csv(AGGREGATE / f'{index}-equity.csv.gz')
        check(bool(equity_rows), f'Case {index}: captured equity snapshots available')
        first_snapshot = int(float(equity_rows[0]['epoch']))
        check(first_snapshot <= last_quote, f'Case {index}: captured snapshot chronology')
        trades = row['trades']
        net = sum(float(t['net_profit']) for t in trades)
        check(abs(net - float(native['net'])) < 0.03, f'Case {index}: trade/statistic net')
        check(abs(float(cfg['deposit']) + float(native['net']) - float(native['balance'])) < 0.03, f'Case {index}: balance/net')
        check(len(trades) == int(native['trades']), f'Case {index}: trade count')
        check(int(native['open_position']) == 0, f'Case {index}: no remaining native positions')
        check(int(native['failed_entries']) == 0, f'Case {index}: no entry failures')
        check(int(native['failed_updates']) == 0, f'Case {index}: no time-close failures')
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
        event_dispositions = []
        for event_epoch in sorted(epochs):
            event_log = [d for d in decisions if int(d['event_epoch']) == event_epoch]
            reasons = [d['reason'] for d in event_log]
            meaningful = [reason for reason in reasons if reason not in ('event_start','event_end','pre_event_reference_confirmed','impulse_confirmed')]
            disposition = 'traded' if event_counts[event_epoch] else meaningful[-1] if meaningful else 'no_qualifying_entry'
            event_dispositions.append(dict(event_epoch=event_epoch,
                                           release_utc=datetime.fromtimestamp(event_epoch,timezone.utc).isoformat(),
                                           disposition=disposition, native_event_started=event_epoch in started,
                                           explicitly_missing_event_window=event_epoch in unavailable,
                                           trades=event_counts[event_epoch], decision_reasons=reasons))
        check(len(event_dispositions) == len(events) == 81, f'Case {index}: all 81 scheduled CPI dispositions retained')
        for trade in trades:
            matches = [d for d in entries if abs(int(d['epoch'])-int(trade['open_epoch'])) <= 2]
            check(len(matches) == 1, f'Case {index}: unambiguous signal/fill matching')
            decision = matches[0]
            event = int(decision['event_epoch'])
            mode = case['mode']
            check(event in epochs, f'Case {index}: known CPI release')
            check(trade['open_epoch'] >= event+60, f'Case {index}: no first-minute lookahead')
            check(trade['close_epoch'] >= trade['open_epoch'], f'Case {index}: chronological fill/exit')
            # Logger runs after a synchronous delayed fill; allow at most two
            # seconds at the boundary, without assigning an ideal earlier fill.
            check(event+60 <= int(decision['epoch']) < event+(300 if mode == 0 else 600)+2, f'Case {index}: signal/fill within entry window plus recorded delay allowance')
            hold_seconds = 60*float(cfg['continuation' if mode == 0 else 'reversion']['maximum_hold_minutes_from_fill'])
            check(trade['close_epoch']-trade['open_epoch'] <= hold_seconds+5, f'Case {index}: configured hold cap at available quote')
            check(trade['close_epoch'] <= event+3600+5, f'Case {index}: hard event close')
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
            requested_stop = abs(request_entry-float(decision['sl']))
            unit_loss = float(decision['unit_loss'])
            check(abs(unit_loss-requested_stop*unit_cash_loss) <= max(1e-6,unit_loss*1e-7),
                  f'Case {index}: OrderCalcProfit actual gold loss conversion')
            lots = float(decision['lots'])
            budget = float(decision['risk_budget'])
            expected_lots = round(math.floor(min(budget/unit_loss,volume_max)/volume_step+1e-9)*volume_step,8)
            check(abs(lots-expected_lots) < 1e-7, f'Case {index}: exact broker-step downward sizing')
            check(volume_min-1e-8 <= lots <= volume_max+1e-8, f'Case {index}: actual gold min/max lot limits')
            check(abs(lots/volume_step-round(lots/volume_step)) < 1e-5, f'Case {index}: broker lot grid')
            for field in ('initial_sl','initial_tp','open_price','close_price'):
                value = float(trade[field])
                check(abs(value-round(value/tick)*tick) <= price_tol, f'Case {index}: {field} on actual gold tick grid')
            check(abs(float(trade['initial_sl'])-float(decision['sl'])) <= price_tol and
                  abs(float(trade['initial_tp'])-float(decision['tp'])) <= price_tol, f'Case {index}: attached levels match gold tick precision')
            expected_profit = direction*(float(trade['close_price'])-float(trade['open_price']))*float(trade['volume'])*unit_cash_profit
            check(abs(float(trade['profit'])-expected_profit) <= 0.011, f'Case {index}: actual price/contract/lots profit reconciles to USD cents')
            expected_risk_budget = (float(cfg['deposit'])+sum(float(t['net_profit']) for t in trades if t['close_epoch']<trade['open_epoch']))*float(cfg['risk_percent'])/100
            check(abs(budget-expected_risk_budget)<0.011, f'Case {index}: dynamic risk uses prior balance/equity')
            target_distance = direction*(float(decision['tp'])-request_entry)
            if mode == 0:
                check(abs(target_distance-1.5*requested_stop) <= tick+price_tol, f'Case {index}: continuation target outward tick-rounded 1.5R')
            if mode == 1:
                check(float(decision['entry_rr']) >= 1.5-1e-7, f'Case {index}: strict fade requested RR')
            if mode != 0:
                check(int(decision['bar_epoch'])+60 <= int(decision['epoch']), f'Case {index}: fade candle completed before signal')
                check(abs(trade['initial_tp']-float(decision['fair'])) <= tick/2+price_tol, f'Case {index}: fade anchor target at actual gold tick precision')
        details.append(dict(index=index, native_case_index=0, stage=stage, trades=len(trades),
                            events_started=len(started), events_explicitly_missing=len(unavailable),
                            scheduled_events=len(events), event_dispositions=event_dispositions,
                            actual_first_native_quote_utc=None,
                            first_native_quote_status='Not exported: the first event-near equity snapshot is not the first historical quote',
                            first_captured_equity_snapshot_utc=datetime.fromtimestamp(first_snapshot,timezone.utc).isoformat(),
                            actual_last_quote_utc=datetime.fromtimestamp(float(native['last_quote_epoch']),timezone.utc).isoformat(),
                            latest_scheduled_cpi_utc=datetime.fromtimestamp(latest_cpi,timezone.utc).isoformat(),
                            latest_scheduled_cpi_full_window_covered=True,
                            native_report=report_path.relative_to(R).as_posix(), report_sha256=row['report_sha256'],
                            binary_sha256=row['binary_sha256'], cash_reconciled=True,
                            contract=contract, actual_tick_size=tick, cash_per_gold_price_unit_per_lot=unit_cash_loss,
                            hold_cap_minutes=cfg['continuation' if case['mode']==0 else 'reversion']['maximum_hold_minutes_from_fill'],
                            live_changes=False))
    result = dict(passed=True, checks=checks, generated_at_utc=datetime.now(timezone.utc).isoformat(),
                  verification_source_sha256=sha(Path(__file__)),
                  scope='Independent source/hash/native contract/cash/lot grid/tick precision/elementary causality reconciliation only; NOT a strategy-validation or execution-quality pass',
                  orchestration='Six sequential single-case native launches; global index maps to native local index 0 in each originating case folder',
                  research_only=True, execution_quality_verified=False, live_changes=False, cases=details)
    (R / 'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    # Keep the complete per-event receipt on disk without flooding the review
    # console with six repeated 81-event inventories.
    display = dict(result)
    display['cases'] = [{k:v for k,v in item.items() if k != 'event_dispositions'} for item in details]
    print(json.dumps(display,indent=2))


if __name__ == '__main__':
    main()
