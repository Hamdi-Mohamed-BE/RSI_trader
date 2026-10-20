"""Independent, read-only reconstruction of the frozen $1K experiment.

Does not import replay.py or access MetaTrader. Its only output is this study's
VERIFICATION.json, including the hashes of the audited immutable artifacts.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Prague')
UTC = timezone.utc
CHECKS = Counter()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message, category='general'):
    CHECKS[category] += 1
    if not condition:
        raise AssertionError(message)


def close(a, b, message, category='numeric', tolerance=1e-8):
    require(a is not None and b is not None and
            math.isfinite(a) and math.isfinite(b) and
            abs(a-b) <= tolerance*max(1., abs(a), abs(b)),
            (message, a, b), category)


def local_day(t):
    return datetime.fromtimestamp(t, TZ).date()


def metrics(values):
    plus = [v for v in values if v > 0]
    minus = [v for v in values if v < 0]
    max_w = max_l = w = l = 0
    for v in values:
        w = (w+1) if v > 0 else 0
        l = (l+1) if v < 0 else 0
        max_w, max_l = max(w, max_w), max(l, max_l)
    return dict(trades=len(values), wins=len(plus), losses=len(minus),
                net_profit=round(sum(values), 2),
                win_rate_pct=100*len(plus)/len(values) if values else None,
                profit_factor=sum(plus)/-sum(minus) if minus else None,
                max_win_streak=max_w, max_loss_streak=max_l,
                average_win=statistics.mean(plus) if plus else None,
                average_loss=statistics.mean(minus) if minus else None,
                largest_win=max(plus) if plus else None,
                largest_loss=min(minus) if minus else None)


def verify_sources(data, native, frozen):
    for path, expected in frozen['files'].items():
        require(digest(path) == expected, ('Frozen file mismatch', path), 'frozen_hashes')
    require(frozen['prepared_before_risk_outcomes'] is True,
            'Freeze not declared before risk outcomes', 'protocol')
    require(len(data['candidates']) == 93, 'Expected 93 standalone source fills', 'sources')
    require(len(native['cases']) == 9, 'Expected nine source EAs', 'sources')
    all_candidates = {q['id']: q for q in data['candidates']}
    require(len(all_candidates) == 93, 'Duplicate candidate IDs', 'sources')
    checked = 0
    for case in native['cases']:
        path = Path(case['path'])
        require(digest(path) == case['sha256'], 'Native completion SHA mismatch', 'sources')
        saved = load(path)
        source_trades = {t['position_id']: t for t in saved['trades']}
        receipts = list(csv.DictReader((path.parent/'entry_risk.csv').open(encoding='utf-8-sig')))
        by_id = {int(q['position_id']): q for q in receipts}
        require(len(by_id) == len(receipts), 'Duplicate entry risk receipt', 'sources')
        deals = defaultdict(list)
        for d in csv.DictReader((path.parent/'deals.csv').open(encoding='utf-8-sig')):
            deals[int(d['position_id'])].append(d)
        for q in (x for x in data['candidates'] if x['ea'] == case['slug']):
            checked += 1
            t = source_trades[q['position_id']]
            receipt = by_id[q['position_id']]
            require(q['unit_risk_method'] == 'native_actual_fill_OrderCalcProfit',
                    'Unexpected risk geometry proxy', 'sources')
            close(q['unit_risk'], float(receipt['unit_risk']), 'Risk receipt', 'sources')
            close(q['receipt_margin_one_lot'], float(receipt['margin_one_lot']),
                  'Margin receipt', 'sources')
            close(q['open_price'], float(receipt['entry_price']), 'Fill quote', 'sources')
            close(q['sl'], float(receipt['sl']), 'Original stop', 'sources')
            require(int(receipt['calculation_ok']) == 1 and int(receipt['margin_ok']) == 1
                    and receipt['sl_source'] == 'entry_order', 'Invalid native risk receipt', 'sources')
            require(abs(q['op']-int(receipt['epoch'])) <= 1, 'Risk receipt timing', 'sources')
            require(q['op'] == t['open_epoch'], 'Source entry timing', 'sources')
            require(not t['partial'], 'Partial position outside model', 'sources')
            require(q['end_censored'] == any('end of test' in s.lower()
                    for s in t['exit_comments']), 'Censor classification', 'sources')
            require((q['cl'] is None) == q['end_censored'], 'Forced source exit improperly retained', 'sources')
            source_parts = deals[q['position_id']]
            opened = [d for d in source_parts if int(d['entry']) == 0]
            require(len(opened) == 1, 'Multiple source fills', 'sources')
            entry = sum(float(opened[0][k]) for k in ('gross', 'commission', 'swap', 'fee'))/t['volume']
            close(entry, q['entry_unit_cost'], 'Entry fee isolation', 'sources')
            close(q['unit_gross']*t['volume'], t['gross'], 'Source gross', 'sources')
            close(q['unit_commission']*t['volume'], t['commission']+t['fee'],
                  'Source commission/fees', 'sources')
            close(q['unit_swap']*t['volume'], t['swap'], 'Source swap', 'sources')
            previous = q['op']
            for mark in q['marks']:
                require(previous < mark[0] and (q['cl'] is None or mark[0] < q['cl']),
                        'Non-owned/ordered mark', 'owned_marks')
                require(math.isfinite(mark[1]), 'Invalid mark', 'owned_marks')
                previous = mark[0]
    require(checked == 93, 'Not all candidates verified', 'sources')


def audit_scenario(record, data, plan, broker):
    begin = int(datetime.fromisoformat(plan['start_utc']).timestamp())
    end = int(datetime.fromisoformat(plan['end_exclusive_utc']).timestamp())
    cash = float(plan['initial_balance'])
    reference = cash
    scenario = record['scenario']
    stress = record['stress']
    priority = {ea: n for n, ea in enumerate(plan['priority'])}
    events = []
    for q in data['candidates']:
        events.append((q['op'], 3, priority[q['ea']], q['id'], q, None))
        if q['cl'] is not None and q['cl'] < end:
            events.append((q['cl'], 4 if q['cl'] == q['op'] else 1,
                           priority[q['ea']], q['id'], q, None))
        events.extend((m[0], 2, priority[q['ea']], q['id'], q, m) for m in q['marks'])
    date = local_day(begin)
    while True:
        stamp = int(datetime.combine(date, datetime.min.time(), tzinfo=TZ).timestamp())
        if stamp >= end:
            break
        if stamp >= begin:
            events.append((stamp, 0, -1, '', None, None))
        date += timedelta(days=1)
    events.sort(key=lambda x: x[:4])
    active, trades, flows, curve = {}, [], [], []
    expected_decisions = iter(record['decisions'])
    per_ea = defaultdict(Counter)
    counts = Counter()
    day, anchor, day_entries, day_losses = None, cash, 0, 0
    permanent = daily_stop = False
    equity = cash
    last_entry = -math.inf

    def observe(stamp):
        nonlocal day, anchor, day_entries, day_losses, daily_stop, permanent, equity
        today = local_day(stamp)
        if today != day:
            day, anchor, day_entries, day_losses, daily_stop = today, cash, 0, 0, False
        equity = cash+sum(p['volume']*p['floating'] for p in active.values())
        permanent = permanent or equity <= reference*.9 or equity <= anchor-reference*.05
        daily_stop = daily_stop or equity <= anchor-reference*.03
        curve.append(dict(epoch=stamp, balance=cash, equity=equity))

    def spread(q, side):
        spec = broker['symbols'][q['symbol']]
        quote = q['open_price'] if side == 'entry' else q['close_price']
        return (spec['quote_spread']*spec['trade_contract_size']/
                (quote if q['symbol'] == 'USDJPY' else 1.))

    for stamp, kind, _, _, q, mark in events:
        if not begin <= stamp < end:
            continue
        if kind == 0:
            observe(stamp)
        elif kind == 2:
            if q['id'] in active:
                active[q['id']]['floating'] = mark[1]
                active[q['id']]['swap'] = mark[2] or 0.
                observe(stamp)
        elif kind in (1, 4):
            if q['id'] not in active:
                continue
            observe(stamp)
            p = active.pop(q['id'])
            swap = q['unit_swap']*(2 if stress and q['unit_swap'] < 0 else 1)
            unit_cash = q['unit_gross']+q['unit_commission']+swap-q['entry_unit_cost']
            exit_cash = round((unit_cash-(spread(q, 'exit') if stress else 0.))*p['volume'], 2)
            cash = round(cash+exit_cash, 2)
            net = round(exit_cash+p['entry_cash'], 2)
            day_losses += net < -.005
            trades.append(dict(id=q['id'], ea=q['ea'], op=q['op'], cl=stamp,
                lots=p['volume'], risk=p['risk'], entry_cash=p['entry_cash'],
                exit_cash=exit_cash, net=net, balance=cash))
            flows.append((stamp, exit_cash))
            per_ea[q['ea']]['closed'] += 1
            counts['closed'] += 1
            observe(stamp)
        else:
            observe(stamp)
            spec = broker['symbols'][q['symbol']]
            unit = q['unit_risk']
            source_cash = 50. if q['source_mode'] == 'fixed50' else equity/200.
            step = spec['volume_step']
            source = min(spec['volume_max'], max(spec['volume_min'],
                math.ceil((min(source_cash/unit, spec['volume_max'])-1e-12)/step)*step))
            allowance = min(reference/200., scenario['value'] if scenario['mode'] == 'fixed'
                            else equity*scenario['value']/100.)
            volume = round(math.floor(min(source, allowance/unit, spec['volume_max'])/step+1e-9)*step, 8)
            if volume < spec['volume_min']-1e-9:
                volume = 0.
            reason = None
            risk = volume*unit
            margin = volume*q['receipt_margin_one_lot']
            total = sum(p['risk'] for p in active.values())
            same = sum(p['risk'] for p in active.values() if p['symbol'] == q['symbol'])
            reserved = sum(1.25*p['risk']+reference*.0005+max(0., -p['swap']*p['volume'])
                           for p in active.values())
            projected = min(equity, cash-reserved)-1.25*risk-reference*.0005
            existing_margin = sum(p['margin'] for p in active.values())
            if any(p['ea'] == q['ea'] for p in active.values()):
                reason = 'same_ea_exposure'
            elif volume == 0:
                reason = 'minimum_lot_over_budget'
            elif permanent:
                reason = 'permanent_loss_latch'
            elif daily_stop:
                reason = 'daily_loss_latch'
            elif day_entries >= 7:
                reason = 'daily_seven_entries'
            elif day_losses >= 3:
                reason = 'daily_three_net_losers'
            elif total+risk > reference*.0225+1e-7:
                reason = 'aggregate_risk'
            elif same+risk > reference*.015+1e-7:
                reason = 'same_symbol_risk'
            elif projected < reference*.92:
                reason = 'equity_buffer'
            elif anchor-projected > reference*.03:
                reason = 'daily_reserved_loss'
            elif existing_margin+margin > projected*.8 or margin > equity-existing_margin:
                reason = 'margin_proxy'
            elif stamp < last_entry+3:
                reason = 'three_second_wait'
            decision = next(expected_decisions)
            require(decision['id'] == q['id'] and decision['reason'] == (reason or 'opened'),
                    ('Decision mismatch', scenario['id'], stress, q['id'], decision, reason), 'decisions')
            for key, expected in dict(equity=equity, budget=allowance, source_volume_ceiling=source,
                volume=volume, stop_risk=risk, minimum_lot_risk=unit*spec['volume_min']).items():
                close(decision[key], expected, ('Decision quantity', key, q['id']), 'decisions')
            per_ea[q['ea']]['candidates'] += 1
            per_ea[q['ea']][reason or 'opened'] += 1
            counts[reason or 'opened'] += 1
            if reason:
                continue
            require(risk <= allowance+1e-7 and risk <= reference*.005+1e-7,
                    'Admitted stop risk exceeds budget', 'admitted_guards')
            require(volume >= spec['volume_min']-1e-9 and volume <= source+1e-9,
                    'Admitted volume outside source/broker limits', 'admitted_guards')
            require(day_entries < 7 and day_losses < 3 and total+risk <= reference*.0225+1e-7
                    and same+risk <= reference*.015+1e-7,
                    'Admitted count/risk guard exceeded', 'admitted_guards')
            entry_cash = round((q['entry_unit_cost']-(spread(q, 'entry') if stress else 0.))*volume, 2)
            cash = round(cash+entry_cash, 2)
            flows.append((stamp, entry_cash))
            active[q['id']] = dict(volume=volume, floating=0., swap=0., entry_cash=entry_cash,
                risk=risk, margin=margin, ea=q['ea'], symbol=q['symbol'])
            day_entries += 1
            last_entry = stamp
            observe(stamp)
    observe(end-1)
    require(next(expected_decisions, None) is None, 'Unexpected extra decisions', 'decisions')
    require(len(record['decisions']) == 93, 'Not all candidates considered', 'decisions')
    require(len(trades) == len(record['trades']), 'Trade count mismatch', 'cash')
    for actual, expected in zip(record['trades'], trades):
        for key in expected:
            if isinstance(expected[key], (float, int)):
                close(actual[key], expected[key], ('Trade', actual['id'], key), 'cash')
            else:
                require(actual[key] == expected[key], ('Trade field', key), 'cash')
        require(not next(x for x in data['candidates'] if x['id'] == actual['id'])['end_censored'],
                'Source forced final close became a realized trade', 'censoring')
    require(record['per_ea'] == {k: dict(v) for k, v in per_ea.items()}, 'Per-EA counts differ', 'counts')
    require(record['metrics']['counts'] == dict(counts), 'Portfolio counts differ', 'counts')
    require(sum(v for k, v in counts.items() if k != 'closed') == 93,
            'Opened/rejected count does not cover all93', 'counts')
    require(len(curve) == len(record['curve']), 'Curve length mismatch', 'curve')
    for expected, actual in zip(curve, record['curve']):
        require(expected['epoch'] == actual['epoch'], 'Curve time mismatch', 'curve')
        close(expected['balance'], actual['balance'], 'Curve balance', 'curve')
        close(expected['equity'], actual['equity'], 'Curve equity', 'curve')
    expected_metrics = metrics([x['net'] for x in trades])
    for key, value in expected_metrics.items():
        if value is None:
            require(record['metrics'][key] is None, ('Metric should be unavailable', key), 'metrics')
        else:
            close(record['metrics'][key], value, key, 'metrics')
    require(not active, 'Unexpected open positions in this completed sample', 'cash')
    close(cash, reference+sum(value for _, value in flows), 'Cash-flow ledger', 'cash')
    close(cash, reference+sum(x['net'] for x in trades), 'Whole-trade cash ledger', 'cash')
    close(record['metrics']['ending_balance'], cash, 'Terminal balance', 'cash')
    close(record['metrics']['ending_sampled_equity'], equity, 'Terminal equity', 'cash')
    close(record['metrics']['return_pct'], (cash/reference-1)*100, 'Return', 'metrics')
    equity_peak = closed_peak = reference
    dd_cash = dd_pct = closed_cash = closed_pct = 0.
    day_eq_peak = day_cash_peak = reference
    daily_eq_dd = daily_cash_dd = daily_anchor = 0.
    current_day, anchor_balance = None, reference
    for c in curve:
        if local_day(c['epoch']) != current_day:
            current_day = local_day(c['epoch'])
            anchor_balance = day_eq_peak = day_cash_peak = c['balance']
        equity_peak = max(equity_peak, c['equity'])
        closed_peak = max(closed_peak, c['balance'])
        day_eq_peak = max(day_eq_peak, c['equity'])
        day_cash_peak = max(day_cash_peak, c['balance'])
        dd_cash = max(dd_cash, equity_peak-c['equity'])
        dd_pct = max(dd_pct, (equity_peak-c['equity'])/equity_peak*100)
        closed_cash = max(closed_cash, closed_peak-c['balance'])
        closed_pct = max(closed_pct, (closed_peak-c['balance'])/closed_peak*100)
        daily_eq_dd = max(daily_eq_dd, day_eq_peak-c['equity'])
        daily_cash_dd = max(daily_cash_dd, day_cash_peak-c['balance'])
        daily_anchor = max(daily_anchor, anchor_balance-c['equity'])
    for key, value in dict(max_sampled_equity_dd_cash=dd_cash, max_sampled_equity_dd_pct=dd_pct,
        max_closed_dd_cash=closed_cash, max_closed_dd_pct=closed_pct,
        max_daily_sampled_equity_dd_cash=daily_eq_dd, max_daily_closed_dd_cash=daily_cash_dd,
        max_daily_anchor_equity_loss=daily_anchor).items():
        close(record['metrics'][key], value, key, 'drawdowns')
    by_utc_date = defaultdict(float)
    for stamp, amount in flows:
        by_utc_date[datetime.fromtimestamp(stamp, UTC).date().isoformat()] += amount
    rates = []
    account_cash = reference
    for row in record['daily']:
        value = round(by_utc_date[row['date']], 2)
        close(row['net_profit'], value, 'Daily cash', 'calendar')
        close(row['opening_balance'], account_cash, 'Daily opening balance', 'calendar')
        rates.append(value/account_cash)
        account_cash = round(account_cash+value, 2)
        close(row['ending_balance'], account_cash, 'Daily terminal balance', 'calendar')
    require(len(record['daily']) == 61, 'No-trade calendar dates missing', 'calendar')
    close(record['metrics']['daily_closed_return_sharpe'],
          statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365), 'Daily Sharpe', 'calendar')
    return dict(scenario=scenario['id'], stress=stress, candidates=93, trades=len(trades),
                ending_balance=cash, profit_factor=expected_metrics['profit_factor'],
                closed_dd=closed_cash, curve_observations=len(curve))


def main():
    frozen, data, results = (load(ROOT/name) for name in ('FROZEN.json', 'INPUTS.json', 'RESULTS.json'))
    native = load(ROOT/'native_cases.json')
    require(results['frozen_sha256'] == digest(ROOT/'FROZEN.json'), 'Results reference wrong freeze', 'protocol')
    verify_sources(data, native, frozen)
    plan, broker = results['plan'], results['broker']
    require(plan == load(ROOT/'PLAN.json') and broker == load(ROOT/'BROKER.json'),
            'Published plan/broker mismatch', 'protocol')
    require(len(results['results']) == 10, 'Expectedfiveallocations times two costs', 'protocol')
    summaries = [audit_scenario(x, data, plan, broker) for x in results['results']]
    for stress in (False, True):
        group = {x['scenario']['id']: x for x in results['results'] if x['stress'] is stress}
        for a, b in (('fixed_2p50', 'percent_0p25'), ('fixed_5', 'percent_0p50'),
                     ('fixed_5', 'percent_1')):
            for key in ('metrics', 'trades', 'per_ea', 'curve', 'daily', 'months'):
                require(group[a][key] == group[b][key], ('Expected lot-granularity equivalence', stress, a, b, key),
                        'pair_equivalence')
    cost_matching = []
    for scenario in plan['scenarios']:
        base, stress = [next(x for x in results['results'] if x['scenario']['id'] == scenario['id']
                          and x['stress'] is c) for c in (False, True)]
        require([(t['id'], t['lots']) for t in base['trades']] ==
                [(t['id'], t['lots']) for t in stress['trades']],
                'Cost stress unexpectedly changed this sample admission set', 'cost_pairing')
        require(stress['metrics']['net_profit'] <= base['metrics']['net_profit'],
                'Stress should not improve same-position cash', 'cost_pairing')
        cost_matching.append(dict(scenario=scenario['id'], matched_trades=len(base['trades']),
            reduction_cash=round(base['metrics']['net_profit']-stress['metrics']['net_profit'], 2)))
    payload = dict(status='PASS', checks=sum(CHECKS.values()), categories=dict(CHECKS),
        scenarios=summaries, cost_pairing=cost_matching, verified_candidates=93,
        native_eas=9, results_sha256=digest(ROOT/'RESULTS.json'),
        freeze_sha256=digest(ROOT/'FROZEN.json'), verifier_sha256=digest(__file__),
        method='Independent event/cash/risk reconstruction; does not import replay.py or access an account.',
        limitations=['Verifies numerical implementation and frozen source evidence, not live profitability or feed quality.',
            'Trial16 native source and Trial15 broker metadata are not the same feed; no exact current-demo execution claim.',
            'Five-minute source marks, missing open-swap observations, immutable filled candidates and unobserved later signals remain limitations.',
            'Only three trades at lower allocation and fourteen at upper allocation; high small-sample PF is not robust edge evidence.'])
    (ROOT/'VERIFICATION.json').write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
