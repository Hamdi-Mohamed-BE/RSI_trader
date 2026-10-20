"""Freeze eligible existing EA signals for an offline small-account challenge screen.

No account APIs, trading, outcome ranking, parameter optimisation, or live writes.
Source natural positions and every native deal cashflow are preserved.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
LONG = BASE / 'Portfolio Long History All ORB05 2026-10-14'
OLD_PUBLISH = BASE / 'Portfolio Long History 2026-10-08/publish.py'
DI = BASE / 'FTMO Core3 vs Core4 DI OFF Phase Timing 2026-10-16'
CACHED_SPECS = BASE / 'Daily Equity Controls Audit 2026-09-29/SOURCE_SPECS.json'
ETH_SPREAD = BASE / 'Daily Equity Controls Audit 2026-09-29/ETHUSD-M1.npz'
START = 1633478400  # 2021-10-06 00:00 UTC
END = 1791244800  # 2026-10-06 00:00 UTC, exclusive
EXCLUDED = {
    'us30-hourly-profiles': 'No actual stop; historical maximum loss is not a bounded future trade risk.',
    'us100-hourly-profiles': 'No actual stop; historical maximum loss is not a bounded future trade risk.',
    'gold-news-v9-direction': 'No timestamped historical pre-release forecast archive.',
    'news-pulse-btc': 'Excluded specialised news pending-order/event execution model from this bounded-risk non-news screen.',
    'news-pulse-eurusd': 'Excluded specialised news pending-order/event execution model from this bounded-risk non-news screen.',
    'news-pulse-xag': 'Excluded specialised news pending-order/event execution model from this bounded-risk non-news screen.',
    'news-pulse-xau': 'Excluded specialised news pending-order/event execution model from this bounded-risk non-news screen.',
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def near(a, b, tol=1e-7):
    return abs(float(a) - float(b)) <= tol


def forced(trade):
    return any('end of test' in x.lower() for x in trade['exit_comments'])


def symbols(broker, cached):
    result = {}
    for symbol in ('USTEC', 'XAUUSD', 'USDJPY', 'BTCUSD', 'ETHUSD'):
        current = broker['symbols'][symbol]
        previous = cached['symbols'][symbol]
        for field in ('trade_contract_size', 'volume_min', 'volume_step', 'volume_max'):
            assert near(current[field], previous[field]), (symbol, field, 'cached/current contract mismatch')
        ratios = [previous['margin_one_lot_current'] / previous['margin_quote']]
        for side in ('buy', 'sell'):
            quote = current['ask' if side == 'buy' else 'bid']
            margin = current.get(side + '_margin_one_lot')
            if quote and margin is not None:
                ratios.append(margin / quote)
        ratio = max(ratios)
        if symbol == 'ETHUSD':
            bars = np.load(ETH_SPREAD)['rates']
            bar = bars[np.where(bars['spread'] > 0)[0][-1]]
            spread_price = float(bar['spread']) * previous['point']
            spread_epoch = int(bar['time'])
            spread_source = 'Latest positive-spread cached Trial15 ETHUSD M1 bar; not a current quote.'
        else:
            spread_price = current['ask'] - current['bid']
            spread_epoch = current['time']
            spread_source = 'Read-only current broker last quote; market-closed symbols may be stale.'
        spread_cash = spread_price * current['trade_contract_size']
        if symbol == 'USDJPY':
            spread_cash /= current['bid']
        result[symbol] = {
            'trade_contract_size': current['trade_contract_size'],
            'volume_min': current['volume_min'], 'volume_step': current['volume_step'],
            'volume_max': current['volume_max'],
            'profit_currency': current['currency_profit'],
            'margin_model': 'fixed USD per one lot' if symbol == 'USDJPY' else 'entry_price_times_conservative_snapshot_ratio',
            'margin_fixed_per_lot': 50.0 if symbol == 'USDJPY' else None,
            'margin_per_price_unit': None if symbol == 'USDJPY' else ratio,
            'margin_ratio_candidates': ratios,
            'margin_proxy_only': True,
            'current_bid': current['bid'], 'current_ask': current['ask'],
            'current_quote_epoch': current['time'],
            'cached_margin_quote': previous['margin_quote'],
            'cached_margin_one_lot': previous['margin_one_lot_current'],
            'spread_cash_per_lot': spread_cash,
            'spread_price_proxy': spread_price, 'spread_proxy_epoch': spread_epoch,
            'spread_source': spread_source,
            'note': 'Historical HMR, broker tiers, hedge discounts, margin repricing and liquidation are not reconstructed.',
        }
        if symbol == 'USDJPY':
            assert near(previous['margin_one_lot_current'], 50.0)
            assert near(current['buy_margin_one_lot'], 50.0)
            assert near(current['sell_margin_one_lot'], 50.0)
    return result


def prepare():
    assert not (ROOT / 'RESULTS.json').exists(), 'Do not refreeze source definitions after outcomes.'
    plan = read(LONG / 'PLAN.json')
    state = read(LONG / 'RUN_STATUS.json')
    ledger = read(LONG / 'RISK_ROWS.json')['full-eas']
    broker = read(ROOT / 'BROKER.json')
    cached = read(CACHED_SPECS)
    assert broker['account']['server'] == cached['server'] == 'Exness-MT5Trial15'
    assert broker['account']['currency'] == 'USD' and broker['account']['leverage'] == 2000
    assert broker['account']['margin_mode'] == 2
    assert plan['start'] == '2021.10.06' and plan['end_exclusive'] == '2026.10.06'
    assert not state['failed']
    assert len(plan['mappings']['full-eas']) == 37
    source_hashes = {}

    def bind(path, expected=None):
        path = Path(path)
        digest = sha(path)
        assert expected is None or digest == expected, ('Source hash mismatch', str(path))
        source_hashes[str(path)] = digest

    for path in (LONG / 'PLAN.json', LONG / 'RUN_STATUS.json', LONG / 'RISK_ROWS.json',
                 ROOT / 'BROKER.json', CACHED_SPECS, ETH_SPREAD, OLD_PUBLISH, Path(__file__)):
        bind(path)
    production = {}
    for case in plan['cases']:
        for path, digest in case['production_hashes'].items():
            assert path not in production or production[path] == digest
            production[path] = digest
    for path, digest in production.items():
        bind(path, digest)
    native_receipts = {x['path']: x['sha256'] for x in state['complete'].values()}
    for path, digest in native_receipts.items():
        bind(path, digest)
    index = {x['case_id']: x for x in plan['cases']}
    ledger_groups = defaultdict(list)
    for row in ledger:
        ledger_groups[row['key']].append(row)
    specs = symbols(broker, cached)
    rows = []
    coverage = []
    epsilon = []
    warnings = []
    counts = Counter()

    def one_source(key, descriptor, receipt, ledger_rows=None, variant_group=None):
        path = Path(receipt['path'])
        bind(path, receipt['sha256'])
        native = read(path)
        assert native['slug'] == descriptor['slug']
        assert native['window'] == ['2021.10.06', '2026.10.06']
        assert native['no_live_changes']
        for flag in ('init_failed', 'runtime', 'history', 'stopout', 'export_failed'):
            assert not native['flags'][flag], (key, flag)
        for field, expected in descriptor['input_settings'].items():
            if field in native['inputs']:
                # Source run helpers intentionally add only audit inputs.
                actual = native['inputs'][field]
                try:
                    same = near(float(actual), float(expected), 1e-10)
                except (ValueError, TypeError):
                    same = str(actual).lower() == str(expected).lower()
                assert same, (key, field, actual, expected)
        by_pid = defaultdict(list)
        deal_path = path.parent / 'deals.csv'
        bind(deal_path)
        for d in csv.DictReader(deal_path.open(encoding='utf-8-sig')):
            by_pid[int(d['position_id'])].append(d)
        old_by_pid = {int(x['position_id']): x for x in ledger_rows or []}
        assert len(old_by_pid) == len(ledger_rows or [])
        forced_count = 0
        selected = []
        natural_count = 0
        source_deals = 0
        partial_positions = 0
        for t in native['trades']:
            end_censored = forced(t)
            forced_count += end_censored
            op, cl = float(t['open_epoch']), float(t['close_epoch'])
            assert START <= op <= cl < END
            initial_volume = float(t['volume'])
            assert initial_volume > 0
            ds = sorted(by_pid[int(t['position_id'])], key=lambda d: (int(d['epoch']), int(d['deal'])))
            opened = [d for d in ds if int(d['entry']) == 0]
            exited = [d for d in ds if int(d['entry']) in (1, 3)]
            assert len(opened) == 1 and len(opened) + len(exited) == len(ds), (key, t['position_id'], 'Complex deal ownership')
            opening = opened[0]
            assert near(opening['volume'], initial_volume) and near(opening['price'], t['open_price'])
            assert int(opening['epoch']) == op
            assert near(opening['sl'], t['sl']), (key, t['position_id'], 'Opening deal stop differs from original stop')
            assert math.fsum(float(d['volume']) for d in exited) > 0
            assert near(math.fsum(float(d['volume']) for d in exited), initial_volume)
            assert int(exited[-1]['epoch']) == cl
            sl = float(opening['sl'])
            assert sl > 0 and ((sl < t['open_price']) == (t['side'] == 'Long'))
            symbol = descriptor['symbol']
            unit_risk = abs(float(t['open_price']) - sl) * specs[symbol]['trade_contract_size']
            if symbol == 'USDJPY':
                unit_risk /= sl
            assert math.isfinite(unit_risk) and unit_risk > 0
            actual_cl = float(END + 1) if end_censored else max(cl, op + .001)
            if not end_censored and actual_cl != cl:
                epsilon.append(dict(key=key, position_id=t['position_id'], native_close_epoch=cl,
                                    ordering_close_epoch=actual_cl, adjustment_seconds=.001))
            flows = []
            for d in ds:
                if end_censored and 'end of test' in d['comment'].lower():
                    continue
                cash = math.fsum(float(d[k]) for k in ('gross', 'commission', 'swap', 'fee')) / initial_volume
                is_entry = int(d['entry']) == 0
                native_epoch = int(d['epoch'])
                event_epoch = float(native_epoch) if is_entry else max(float(native_epoch), op + .001)
                flows.append(dict(epoch=event_epoch, native_epoch=native_epoch,
                                  kind='entry' if is_entry else 'exit', cash_unit=cash,
                                  swap_unit=float(d['swap']) / initial_volume,
                                  closed_volume_fraction=0.0 if is_entry else float(d['volume']) / initial_volume,
                                  deal_id=int(d['deal'])))
            closed_fraction = math.fsum(f['closed_volume_fraction'] for f in flows)
            assert 0 <= closed_fraction <= 1.0 + 1e-7
            assert end_censored or near(closed_fraction, 1.0)
            assert not end_censored or closed_fraction < 1.0 - 1e-7
            unit_net = math.fsum(f['cash_unit'] for f in flows)
            assert near(math.fsum(math.fsum(float(d[k]) for k in ('gross', 'commission', 'swap', 'fee')) for d in ds), float(t['net']), .011)
            kept_deals = [d for d in ds if not (end_censored and 'end of test' in d['comment'].lower())]
            unit_gross = math.fsum(float(d['gross']) for d in kept_deals) / initial_volume
            unit_comm = math.fsum(float(d['commission']) + float(d['fee']) for d in kept_deals) / initial_volume
            unit_swap = math.fsum(float(d['swap']) for d in kept_deals) / initial_volume
            assert near(unit_net, unit_gross + unit_comm + unit_swap, 0.011 / initial_volume)
            if ledger_rows is not None and not end_censored:
                old = old_by_pid[int(t['position_id'])]
                assert near(old['op'], op) and near(old['cl'], actual_cl)
                for f, value in [('unit_risk', unit_risk), ('unit_gross', unit_gross),
                                 ('unit_comm', unit_comm), ('unit_swap', unit_swap)]:
                    assert near(old[f], value, 1e-6), (key, t['position_id'], f)
            margin = (specs[symbol]['margin_fixed_per_lot'] if symbol == 'USDJPY' else
                      float(t['open_price']) * specs[symbol]['margin_per_price_unit'])
            q = dict(id=key + '|' + str(t['position_id']), key=key,
                     variant_group=variant_group or key, symbol=symbol, news=False,
                     op=op, cl=actual_cl, native_cl=cl, position_id=int(t['position_id']),
                     end_censored=end_censored,
                     side=t['side'], open_price=t['open_price'], close_price=None if end_censored else t['close_price'],
                     initial_sl=sl, unit_risk=unit_risk, unit_gross=unit_gross,
                     unit_comm=unit_comm, unit_swap=unit_swap, unit_net=unit_net,
                     entry_unit_cash=math.fsum(f['cash_unit'] for f in flows if f['kind'] == 'entry'),
                     margin_unit_proxy=margin, partial=bool(t['partial']), source_volume=initial_volume,
                     flows=flows, source_result=str(path), source_case_id=descriptor['case_id'],
                     risk_reference='filled original SL geometry; USDJPY conversion at stop price')
            selected.append(q)
            natural_count += not end_censored
            source_deals += len(ds)
            partial_positions += bool(t['partial'])
        if ledger_rows is not None:
            assert natural_count == len(ledger_rows)
        assert len({x['id'] for x in selected}) == len(selected)
        rows.extend(selected)
        counts['positions'] += len(selected)
        counts['natural_positions'] += natural_count
        counts['end_censored_positions'] += forced_count
        counts['deals'] += source_deals
        counts['partial_positions'] += partial_positions
        source_flags = {k: v for k, v in native['flags'].items() if v}
        if source_flags:
            warnings.append(dict(key=key, native_flags=source_flags,
                                 note='Source tester diagnostics are preserved, not silently repaired or treated as filled trades.'))
        coverage.append(dict(key=key, variant_group=variant_group or key, symbol=descriptor['symbol'],
                             source_result=str(path), source_result_sha256=sha(path),
                             case_id=descriptor['case_id'], natural_positions=natural_count,
                             native_deals=source_deals, partial_positions=partial_positions,
                             retained_end_censored_positions=forced_count, artificial_final_exit_cash_omitted=forced_count,
                             first_open=min(q['op'] for q in selected), last_natural_close=max(q['native_cl'] for q in selected if not q['end_censored']),
                             source_window=native['window'], history_quality=native['native']['history_quality'],
                             tick_notes=native['tick_notes'], native_flags=source_flags,
                             source_inputs=native['inputs']))

    eligible = sorted(set(plan['mappings']['full-eas']) - set(EXCLUDED))
    assert len(eligible) == 30
    for key in eligible:
        cid = plan['mappings']['full-eas'][key]
        one_source(key, index[cid], state['complete'][cid], ledger_groups[key])
    assert sum(not q['end_censored'] for q in rows) == 9381
    current_nasdaq = next(x for x in coverage if x['key'] == 'nasdaq-5m-candle-momentum')
    assert current_nasdaq['source_inputs']['InpRequireDIAgreement'] == 'true'

    di_run = read(DI / 'NATIVE-RUN.json')
    di_plan = read(DI / 'NATIVE-PLAN.json')
    assert di_run['complete'] and di_run['source_only_DI_toggle'] and di_run['live_processes_preserved']
    assert di_plan['input_differences'] == ['InpRequireDIAgreement']
    assert di_plan['row']['input_settings']['InpRequireDIAgreement'] == 'false'
    assert di_plan['input_before']['InpRequireDIAgreement'] == 'true'
    for path in (DI / 'NATIVE-RUN.json', DI / 'NATIVE-PLAN.json', DI / 'NATIVE-FROZEN.json'):
        bind(path)
    for path, digest in di_plan['production_hashes'].items():
        bind(path, digest)
    one_source('nasdaq-5m-candle-momentum-no-di', di_plan['row'], di_run,
               variant_group='nasdaq-5m-candle-momentum')
    assert len(coverage) == 31
    assert len(rows) == len({q['id'] for q in rows})
    rows.sort(key=lambda q: (q['op'], q['key'], q['position_id']))
    limitations = [
        'Historical signal-ledger replay is not a simultaneous native or live execution; only original standalone signals exist.',
        'Current strategies and past data were previously researched. A later chronological split is a selection check, not genuinely untouched out-of-sample evidence.',
        'Native tests report 15% real ticks; real ticks begin January 2026. Earlier generated/mixed tick execution may alter tight-stop results.',
        'Entry sizing uses closed cash, not floating equity. No tick/intraday equity drawdown or liquidation path is available in this input model.',
        'Source actual fills/spread/commission/fees/swap are retained. Resized fills assume linear execution; liquidity and broker fee tiers are not reconstructed.',
        'Broker snapshot is Trial15; historical standalone test source is Trial16. Contract/lot parity is checked, quote and historical cost parity are not established.',
        'Margin is a conservative current/cached snapshot estimate, not historical HMR, tiers, repricing, netting, liquidation, or a guarantee of broker acceptance.',
        'ETH has no current quote/margin receipt; its cached Trial15 price-scaled margin ratio is used. BTC current margin ratio is lower than cached; larger cached ratio is retained.',
        'ETH spread stress uses the latest positive-spread cached Trial15 M1 bar from September 2026; this is a stale bar-spread proxy, not a live bid/ask receipt.',
        'USDJPY initial risk uses original SL-price currency conversion, consistent with the published ledger, not an exact historical fill-time OrderCalcProfit receipt.',
        'Six source-end censored entries are retained with known genuine deal cashflows and initial risk; their artificial final liquidations are omitted. Closed-cash simulation must retain their remaining exposure through the boundary.',
        'Source same-second exits use the publisher ordering epsilon of 1ms; this is an ordering convention, not measured millisecond precision.',
        'Nasdaq overnight source has no entries before June 2023; this is shorter observed coverage, not proof of no earlier signals.',
        'Four News Pulse EAs and Gold News V9 are excluded; this is not a claim that all 37 EAs were validly tested.',
        'No production EA, BAT, preset, active terminal, website, or account is changed by this preparation.',
    ]
    audit = dict(status='PASS', source_window_utc=['2021-10-06', '2026-10-06'],
                 current_active_eas=37, eligible_current_eas=30, alternatives=1,
                 excluded_eas=EXCLUDED, counts=dict(counts),
                 current_parameter_role_configurations=len(plan['cases']),
                 native_receipts_hash_checked=len(native_receipts), production_files_hash_checked=len(production),
                 candidate_count=len(rows), cashflows_reconciled=True, initial_stop_open_deal_verified=True,
                 partial_exit_flows_preserved=True, artificial_liquidation_cash_excluded=True,
                 source_end_censored_entries_retained=True,
                 publisher_ordering_epsilon=epsilon, source_warnings=warnings,
                 source_file_count=len(source_hashes), limitations=limitations,
                 live_changes=False, outcomes_evaluated=False)
    labels = {key: index[plan['mappings']['full-eas'][key]]['label'] for key in eligible}
    labels['nasdaq-5m-candle-momentum-no-di'] = labels['nasdaq-5m-candle-momentum'] + ' — DI OFF'
    named_baskets = {name: sorted(set(plan['mappings'][name]) & set(eligible))
                     for name in ('ftmo', 'current14-orb05', 'orbs-only')}
    named_baskets['full-non-news-with-stops'] = eligible
    named_baskets['prop-ready-9'] = [
        'xau-rsi-vwap', 'xau-orb-london-ny-overlap-m30', 'us100-h1-orb-13utc',
        'usdjpy-london-open-momentum', 'us100-month-end-flow', 'nasdaq-5m-candle-momentum',
        'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30']
    named_baskets['top5-no-di'] = ['gold-overnight-value-area', 'xau-rsi-vwap',
                                   'nasdaq-overnight', 'nasdaq-5m-candle-momentum-no-di',
                                   'orb-volume-profile']
    assert all(set(members) <= set(labels) for members in named_baskets.values())
    output = dict(version=1, rows=rows, symbols=specs, sources=coverage,
                  metadata=dict(window_start_utc='2021-10-06', window_end_exclusive_utc='2026-10-06',
                                earliest_epoch=START, end_exclusive_epoch=END,
                                current_eas=eligible, alternatives=['nasdaq-5m-candle-momentum-no-di'],
                                labels=labels, named_baskets=named_baskets,
                                exclusive_variant_groups={'nasdaq-5m-candle-momentum': ['nasdaq-5m-candle-momentum', 'nasdaq-5m-candle-momentum-no-di']},
                                excluded=EXCLUDED, limitations=limitations),
                  source_hashes=source_hashes)
    save(ROOT / 'INPUTS.json', output)
    save(ROOT / 'SOURCE AUDIT.json', audit)
    print(json.dumps(dict(status='PASS', rows=len(rows), variants=len(coverage),
                          native_deals=counts['deals'], partial_positions=counts['partial_positions'],
                          source_files=len(source_hashes), inputs_sha256=sha(ROOT / 'INPUTS.json'))))


if __name__ == '__main__':
    prepare()
