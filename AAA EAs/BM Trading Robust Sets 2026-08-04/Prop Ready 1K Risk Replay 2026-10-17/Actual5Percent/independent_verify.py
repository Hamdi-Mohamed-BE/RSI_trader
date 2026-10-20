"""Independent reconstruction of the genuine-5% supplemental experiment.

Never imports the experiment's run.py/replay.py, contacts MT5 or modifies source
artifacts. Reuses only the earlier independent verifier's receipt/hash checks.
Its sole output is child-local VERIFICATION.json.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
from bisect import bisect_left
import csv
import importlib.util
import json
import math
import statistics


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
TZ = ZoneInfo('Europe/Prague')
UTC = timezone.utc
SOURCE_SPEC = importlib.util.spec_from_file_location('independent_source_evidence', PARENT/'independent_verify.py')
source = importlib.util.module_from_spec(SOURCE_SPEC)
SOURCE_SPEC.loader.exec_module(source)
load, digest, require, close = source.load, source.digest, source.require, source.close


def label_day(t):
    return datetime.fromtimestamp(t, TZ).date()


def utc_label(t):
    return datetime.fromtimestamp(t, UTC).date().isoformat()


def isoclock(t):
    return datetime.fromtimestamp(t, UTC).isoformat()


def verify_native_mark_values(data, native, begin, end):
    """Reconstruct every stored floating mark from captured native equity CSVs."""
    for case in native['cases']:
        path = Path(case['path'])
        source_trades = sorted(load(path)['trades'], key=lambda p: (p['open_epoch'], p['position_id']))
        opens = [p['open_epoch'] for p in source_trades]
        boundaries = {p[key] for p in source_trades for key in ('open_epoch', 'close_epoch')}
        expected = defaultdict(list)
        previous = None
        with (path.parent/'equity.csv').open(encoding='utf-8-sig', newline='') as file:
            for point in csv.DictReader(file):
                stamp = int(point['epoch'])
                if not begin <= stamp < end:
                    continue
                require(previous is None or stamp >= previous, 'Native curve timestamp regression', 'captured_marks')
                if previous == stamp:
                    continue
                previous = stamp
                if stamp in boundaries:
                    continue
                index = bisect_left(opens, stamp)-1
                if index >= 0 and opens[index] < stamp < source_trades[index]['close_epoch']:
                    p = source_trades[index]
                    floating = (float(point['equity'])-float(point['balance']))/p['volume']
                    swap = float(point['open_swap'])/p['volume'] if point.get('open_swap') else None
                    expected[p['position_id']].append((stamp, floating, swap))
                else:
                    require(abs(float(point['equity'])-float(point['balance'])) < .021,
                            'Unowned nonzero native floating equity', 'captured_marks')
        for q in (p for p in data['candidates'] if p['ea'] == case['slug']):
            marks = expected[q['position_id']]
            require(len(marks) == len(q['marks']), 'Native mark count mismatch', 'captured_marks')
            for actual, recorded in zip(q['marks'], marks):
                require(actual[0] == recorded[0], 'Native captured timestamp mismatch', 'captured_marks')
                close(actual[1], recorded[1], 'Native captured per-lot floating value', 'captured_marks')
                if recorded[2] is None:
                    require(actual[2] is None, 'Unknown native open swap not zero-imputed', 'captured_marks')
                else:
                    close(actual[2], recorded[2], 'Native captured open swap', 'captured_marks')


def audit(record, data, original_plan, new_plan, broker):
    start, end = (int(datetime.fromisoformat(x).timestamp()) for x in new_plan['window_utc'])
    initial = float(new_plan['initial_balance'])
    scenario, stress = record['scenario'], record['stress']
    current = scenario['guard_policy'] == 'current'
    aggressive = scenario['guard_policy'] == 'research_10daily_20total'
    priority = {ea: index for index, ea in enumerate(original_plan['priority'])}
    events = []
    for q in data['candidates']:
        events.append((q['op'], 3, priority[q['ea']], q['id'], q, None))
        if q['cl'] is not None and q['cl'] < end:
            events.append((q['cl'], 4 if q['cl'] == q['op'] else 1, priority[q['ea']], q['id'], q, None))
        events.extend((m[0], 2, priority[q['ea']], q['id'], q, m) for m in q['marks'])
    date = label_day(start)
    while True:
        stamp = int(datetime.combine(date, datetime.min.time(), tzinfo=TZ).timestamp())
        if stamp >= end:
            break
        if stamp >= start:
            events.append((stamp, 0, -1, '', None, None))
        date += timedelta(days=1)
    events.sort(key=lambda e: e[:4])
    active, trades, flows, curve = {}, [], [], []
    counts, quality = Counter(), Counter()
    per_ea = defaultdict(Counter)
    cash = equity = anchor = initial
    today = None
    day_entries = day_losses = 0
    daily_stopped = permanent = False
    first_breach = None
    paused_days = set()
    last_entry = -math.inf
    max_age = max_initial_lag = 0
    decisions = iter(record['decisions'])
    independently_derived_decisions = []

    def observe(stamp):
        nonlocal equity, today, anchor, day_entries, day_losses, daily_stopped, permanent
        nonlocal first_breach, max_age, max_initial_lag
        equity = cash+sum(p['volume']*p['floating'] for p in active.values())
        if label_day(stamp) != today:
            today, anchor, day_entries, day_losses, daily_stopped = label_day(stamp), cash, 0, 0, False
        for p in active.values():
            if p['mark_epoch'] is None:
                quality['initial_zero_observations'] += 1
                max_initial_lag = max(max_initial_lag, max(0, stamp-p['op']))
            else:
                age = max(0, stamp-p['mark_epoch'])
                max_age = max(max_age, age)
                quality['stale_over_900s_observations'] += age > 900
        if aggressive:
            if equity <= .80*initial:
                permanent = True
                if first_breach is None:
                    first_breach = stamp
            if equity <= .90*anchor:
                daily_stopped = True
                paused_days.add(today.isoformat())
        else:
            permanent = permanent or equity <= .90*initial or equity <= anchor-.05*initial
            daily_stopped = daily_stopped or equity <= anchor-.03*initial
        curve.append(dict(epoch=stamp, balance=cash, equity=equity))

    def budget():
        value = scenario['value'] if scenario['mode'] == 'fixed' else equity*scenario['value']/100.
        return min(initial*.005, value) if current else value

    def spread(q, entering):
        spec = broker['symbols'][q['symbol']]
        price = q['open_price'] if entering else q['close_price']
        return spec['quote_spread']*spec['trade_contract_size']/(price if q['symbol'] == 'USDJPY' else 1.)

    for stamp, kind, _, _, q, mark in events:
        if not start <= stamp < end:
            continue
        if kind == 0:
            observe(stamp)
        elif kind == 2:
            if q['id'] not in active:
                continue
            p = active[q['id']]
            require(q['op'] < mark[0] <= stamp and (q['cl'] is None or mark[0] < q['cl']),
                    'Future/unowned floating mark', 'causality')
            if p['mark_epoch'] is None:
                max_initial_lag = max(max_initial_lag, mark[0]-q['op'])
            p.update(floating=mark[1], swap=mark[2] if mark[2] is not None else 0., mark_epoch=mark[0])
            quality['owned_marks'] += 1
            quality['missing_open_swap_marks'] += mark[2] is None
            observe(stamp)
        elif kind in (1, 4):
            if q['id'] not in active:
                continue
            require(not q['end_censored'] and q['cl'] == stamp, 'Invented final liquidation', 'censoring')
            observe(stamp)
            p = active.pop(q['id'])
            swap = q['unit_swap']*(2. if stress and q['unit_swap'] < 0 else 1.)
            unit_exit = q['unit_gross']+q['unit_commission']+swap-q['entry_unit_cost']
            exit_cash = round((unit_exit-(spread(q, False) if stress else 0.))*p['volume'], 2)
            cash = round(cash+exit_cash, 2)
            net = round(exit_cash+p['entry_cash'], 2)
            day_losses += net < -.005
            trades.append(dict(id=q['id'], ea=q['ea'], symbol=q['symbol'], op=q['op'], cl=stamp,
                side=q['side'], open_price=q['open_price'], close_price=q['close_price'], sl=q['sl'], tp=q['tp'],
                lots=p['volume'], risk=p['risk'], entry_cash=p['entry_cash'], exit_cash=exit_cash,
                net=net, balance=cash, gross=q['unit_gross']*p['volume'],
                commission=q['unit_commission']*p['volume'], swap=swap*p['volume']))
            flows.append(dict(epoch=stamp, cash=exit_cash, id=q['id'], kind='exit'))
            per_ea[q['ea']]['closed'] += 1
            counts['closed'] += 1
            observe(stamp)
        else:
            observe(stamp)
            spec = broker['symbols'][q['symbol']]
            allowance = budget()
            unit, step = q['unit_risk'], spec['volume_step']
            ceiling = None
            if current:
                source_cash = 50. if q['source_mode'] == 'fixed50' else .005*equity
                ceiling = min(spec['volume_max'], max(spec['volume_min'],
                    math.ceil((min(source_cash/unit, spec['volume_max'])-1e-12)/step)*step))
            desired = min(allowance/unit, spec['volume_max'], ceiling if ceiling is not None else math.inf)
            volume = max(0., round(math.floor(desired/step+1e-9)*step, 8))
            if volume < spec['volume_min']-1e-9:
                volume = 0.
            risk = unit*volume
            margin = q['receipt_margin_one_lot']*volume
            total = sum(p['risk'] for p in active.values())
            same = sum(p['risk'] for p in active.values() if p['symbol'] == q['symbol'])
            reserve = sum(p['risk']*1.25+.0005*initial+max(0., -p['swap']*p['volume']) for p in active.values())
            protected = min(equity, cash-reserve)-1.25*risk-.0005*initial
            existing_margin = sum(p['margin'] for p in active.values())
            aggregate_limit = 2*allowance if aggressive else .0225*initial
            symbol_limit = allowance if aggressive else .015*initial
            buffer = .80*initial if aggressive else .92*initial
            day_reserve = .10*anchor if aggressive else .03*initial
            reason = None
            if any(p['ea'] == q['ea'] for p in active.values()):
                reason = 'same_ea_exposure'
            elif volume <= 0:
                reason = 'minimum_lot_over_budget'
            elif permanent:
                reason = 'permanent_loss_latch'
            elif daily_stopped:
                reason = 'daily_loss_latch'
            elif day_entries >= 7:
                reason = 'daily_seven_entries'
            elif day_losses >= 3:
                reason = 'daily_three_net_losers'
            elif total+risk > aggregate_limit+1e-7:
                reason = 'aggregate_risk'
            elif same+risk > symbol_limit+1e-7:
                reason = 'same_symbol_risk'
            elif protected < buffer:
                reason = 'equity_buffer'
            elif anchor-protected > day_reserve:
                reason = 'daily_reserved_loss'
            elif existing_margin+margin > protected*.8 or margin > equity-existing_margin:
                reason = 'margin_proxy'
            elif stamp < last_entry+3:
                reason = 'three_second_wait'
            expected = dict(id=q['id'], ea=q['ea'], epoch=stamp, equity=equity, budget=allowance,
                source_volume_ceiling=ceiling, volume=volume, stop_risk=risk,
                minimum_lot_risk=unit*spec['volume_min'], reason=reason or 'opened')
            if not current:
                expected.update(source_sizing_override_research_only=True,
                    stop_risk_pct_equity=risk/equity*100. if equity > 0 else None)
            d = next(decisions)
            for key, value in expected.items():
                if value is None or isinstance(value, (str, bool)):
                    require(d[key] == value, ('Decision', scenario['id'], stress, q['id'], key, d[key], value), 'decisions')
                else:
                    close(d[key], value, ('Decision number', scenario['id'], stress, q['id'], key), 'decisions')
            expected.update(balance_before_entry=cash, projected_protected_cash=protected,
                            Prague_day_anchor=anchor, existing_initial_risk=total)
            independently_derived_decisions.append(expected)
            per_ea[q['ea']]['candidates'] += 1
            per_ea[q['ea']][reason or 'opened'] += 1
            counts[reason or 'opened'] += 1
            if reason:
                continue
            require(risk <= allowance+1e-7, 'Actual stop exposure exceeds allocation', 'admitted_guards')
            require(volume >= spec['volume_min']-1e-9 and volume <= spec['volume_max']+1e-9,
                    'Broker lot min/max breached', 'admitted_guards')
            if current:
                require(volume <= ceiling+1e-7 and risk <= .005*initial+1e-7,
                        'Literal existing caps exceeded', 'admitted_guards')
            require(total+risk <= aggregate_limit+1e-7 and same+risk <= symbol_limit+1e-7,
                    'Aggregate/symbol admission breached', 'admitted_guards')
            require(protected >= buffer and anchor-protected <= day_reserve,
                    'Reserved loss admission breached', 'admitted_guards')
            require(day_entries < 7 and day_losses < 3, 'Daily count admission breached', 'admitted_guards')
            entry_cash = round((q['entry_unit_cost']-(spread(q, True) if stress else 0.))*volume, 2)
            cash = round(cash+entry_cash, 2)
            flows.append(dict(epoch=stamp, cash=entry_cash, id=q['id'], kind='entry'))
            active[q['id']] = dict(volume=volume, risk=risk, margin=margin, entry_cash=entry_cash,
                floating=0., swap=0., mark_epoch=None, ea=q['ea'], symbol=q['symbol'], op=q['op'])
            day_entries += 1
            last_entry = stamp
            observe(stamp)
    observe(end-1)
    require(next(decisions, None) is None and len(record['decisions']) == len(data['candidates']),
            'Candidate decisions not exhaustive', 'decisions')
    require(len(trades) == len(record['trades']), 'Closed positions differ', 'cash')
    for actual, expected in zip(record['trades'], trades):
        for key, value in expected.items():
            if isinstance(value, (int, float)):
                close(actual[key], value, ('Whole position cash', key, expected['id']), 'cash')
            else:
                require(actual[key] == value, ('Whole position field', key), 'cash')
    require(record['per_ea'] == {key: dict(value) for key, value in per_ea.items()}, 'Per EA counts', 'counts')
    require(record['metrics']['counts'] == dict(counts), 'Reason counts', 'counts')
    require(sum(v for key, v in counts.items() if key != 'closed') == len(data['candidates']),
            'Opened plus rejected does not reconcile', 'counts')
    require(record['metrics']['hard_loss_latch'] == permanent, 'Permanent guard latch', 'latches')
    if not current:
        require(record['metrics']['first_breach_epoch'] == first_breach, 'First breach time', 'latches')
        require(record['metrics']['paused_days'] == sorted(paused_days), 'Paused loss days', 'latches')
        require(record['cash_flows'] == flows, 'Recorded cash event ledger', 'cash')
        close(record['metrics']['cash_profit'], cash-initial, 'Cash profit', 'cash')
        close(record['metrics']['unrealized_sampled_profit'], equity-cash, 'Unrealized terminal float', 'cash')
        require(len(record['open_positions']) == len(active), 'Censored open list', 'censoring')
        for p in record['open_positions']:
            a = active[p['id']]
            for key, expected in dict(lots=a['volume'], initial_risk=a['risk'],
                paid_entry_cash=a['entry_cash'], mark_epoch=a['mark_epoch'],
                mark_unit=a['floating'], sampled_floating=a['volume']*a['floating']).items():
                if expected is None:
                    require(p[key] is None, ('Censor mark', key), 'censoring')
                else:
                    close(p[key], expected, ('Censor mark', key), 'censoring')
    quality.update(maximum_past_mark_age_seconds=max_age, maximum_initial_zero_segment_seconds=max_initial_lag)
    require(record['mark_quality'] == dict(quality), 'Past-only mark quality counters differ', 'causality')
    require(len(curve) == len(record['curve']), 'Sampled curve length', 'curve')
    for expected, actual in zip(curve, record['curve']):
        require(expected['epoch'] == actual['epoch'], 'Sampled curve timestamp', 'curve')
        close(actual['balance'], expected['balance'], 'Sampled curve cash', 'curve')
        close(actual['equity'], expected['equity'], 'Sampled curve equity', 'curve')
    expected_metrics = source.metrics([t['net'] for t in trades])
    for key, value in expected_metrics.items():
        if value is None:
            require(record['metrics'][key] is None, ('Unavailable metric', key), 'metrics')
        else:
            close(record['metrics'][key], value, key, 'metrics')
    close(cash, round(initial+sum(f['cash'] for f in flows), 2), 'Cent cash ledger reconciliation', 'cash')
    close(cash, round(initial+sum(t['net'] for t in trades)+sum(p['entry_cash'] for p in active.values()), 2),
          'Closed net plus censored entry fees', 'cash')
    close(record['metrics']['ending_balance'], cash, 'Ending cash', 'cash')
    close(record['metrics']['ending_sampled_equity'], equity, 'Ending sampled equity', 'cash')
    close(record['metrics']['return_pct'], (cash/initial-1)*100., 'Cash return', 'metrics')
    close(record['metrics']['ending_equity_return_pct'], (equity/initial-1)*100., 'Sampled equity return', 'metrics')
    close(record['metrics']['open_positions'], len(active), 'Open position count', 'censoring')
    close(record['metrics']['average_trades_per_calendar_day'], len(trades)/61., 'Calendar frequency', 'metrics')
    close(record['metrics']['average_trades_per_weekday'], len(trades)/45., 'Weekday frequency', 'metrics')
    eq_peak = cash_peak = initial
    day_eq_peak = day_cash_peak = initial
    dd_cash = dd_pct = closed_cash = closed_pct = 0.
    daily_eq = daily_cash = daily_anchor = 0.
    date = None
    for p in curve:
        if label_day(p['epoch']) != date:
            date = label_day(p['epoch'])
            anchor_cash = day_cash_peak = p['balance']
            day_eq_peak = p['equity'] if aggressive else p['balance']
        eq_peak, cash_peak = max(eq_peak, p['equity']), max(cash_peak, p['balance'])
        day_eq_peak, day_cash_peak = max(day_eq_peak, p['equity']), max(day_cash_peak, p['balance'])
        dd_cash, dd_pct = max(dd_cash, eq_peak-p['equity']), max(dd_pct, 100*(eq_peak-p['equity'])/eq_peak)
        closed_cash, closed_pct = max(closed_cash, cash_peak-p['balance']), max(closed_pct, 100*(cash_peak-p['balance'])/cash_peak)
        daily_eq = max(daily_eq, day_eq_peak-p['equity'])
        daily_cash = max(daily_cash, day_cash_peak-p['balance'])
        daily_anchor = max(daily_anchor, anchor_cash-p['equity'])
    for key, value in dict(max_sampled_equity_dd_cash=dd_cash, max_sampled_equity_dd_pct=dd_pct,
        max_closed_dd_cash=closed_cash, max_closed_dd_pct=closed_pct,
        max_daily_sampled_equity_dd_cash=daily_eq, max_daily_closed_dd_cash=daily_cash,
        max_daily_anchor_equity_loss=daily_anchor).items():
        close(record['metrics'][key], value, key, 'drawdowns')
    by_date = defaultdict(float)
    for f in flows:
        by_date[utc_label(f['epoch'])] += f['cash']
    account_cash, rates = initial, []
    require(len(record['daily']) == (end-start)//86400, 'Calendar no-trade days omitted', 'calendar')
    for index, p in enumerate(record['daily']):
        require(p['date'] == utc_label(start+index*86400), 'Calendar day out of order', 'calendar')
        daily_profit = round(by_date[p['date']], 2)
        close(p['opening_balance'], account_cash, 'UTC opening balance', 'calendar')
        close(p['net_profit'], daily_profit, 'UTC daily cash profit', 'calendar')
        rates.append(daily_profit/account_cash if account_cash > 0 else 0.)
        account_cash = round(account_cash+daily_profit, 2)
        close(p['ending_balance'], account_cash, 'UTC ending balance', 'calendar')
    close(account_cash, cash, 'Final daily balance', 'calendar')
    expected_sharpe = statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365) if statistics.stdev(rates) > 0 else None
    if expected_sharpe is None:
        require(record['metrics']['daily_closed_return_sharpe'] is None, 'Zero-return Sharpe unavailable', 'calendar')
    else:
        close(record['metrics']['daily_closed_return_sharpe'], expected_sharpe, 'UTC cash Sharpe', 'calendar')
    require(len(record['months']) == 3, 'Expected three partial/full calendar months', 'calendar')
    for p in record['months']:
        days = [x for x in record['daily'] if x['date'].startswith(p['month'])]
        close(p['opening_balance'], days[0]['opening_balance'], 'Monthly opening cash', 'calendar')
        close(p['ending_balance'], days[-1]['ending_balance'], 'Monthly ending cash', 'calendar')
        close(p['net_profit'], round(sum(x['net_profit'] for x in days), 2), 'Monthly profit', 'calendar')
        close(p['return_pct'], (days[-1]['ending_balance']/days[0]['opening_balance']-1)*100., 'Monthly return', 'calendar')
    summary = dict(scenario=scenario['id'], stress=stress, closed_positions=len(trades),
        ending_cash=cash, ending_sampled_equity=equity, cash_profit=round(cash-initial, 2),
        sampled_equity_dd_pct=dd_pct, profit_factor=expected_metrics['profit_factor'],
        permanent_hard_latch=permanent, paused_days=sorted(paused_days), open_positions=len(active),
        candidates=len(data['candidates']), observations=len(curve))
    return summary, independently_derived_decisions


def compare_cost_paths(records, detailed_decisions):
    diagnostics = []
    for name in ('fixed50', 'compound5'):
        baseline = next(r for r in records if r['scenario']['id'] == name and not r['stress'])
        stress = next(r for r in records if r['scenario']['id'] == name and r['stress'])
        base_decisions = detailed_decisions[(name, False)]
        stress_decisions = detailed_decisions[(name, True)]
        differences = [(a, b) for a, b in zip(base_decisions, stress_decisions)
                       if (a['reason'] == 'opened') != (b['reason'] == 'opened')]
        first = differences[0] if differences else None
        before = [(a, b) for a, b in zip(base_decisions, stress_decisions)
                  if first is None or a['epoch'] < first[0]['epoch']]
        require(all((a['reason'] == 'opened') == (b['reason'] == 'opened') for a, b in before),
                'Admission paths differ before first reported divergence', 'cost_paths')
        base_trades = {p['id']: p for p in baseline['trades']}
        matched_same_volume = []
        for t in stress['trades']:
            a = base_trades.get(t['id'])
            if a and abs(a['lots']-t['lots']) < 1e-10:
                require(t['net'] <= a['net']+1e-8, 'Additional costs improved identical trade net', 'cost_paths')
                matched_same_volume.append(dict(id=t['id'], lots=t['lots'],
                    recorded_net=a['net'], stressed_net=t['net'], extra_loss=round(a['net']-t['net'], 2)))
        diagnostics.append(dict(scenario=name,
            first_admission_divergence_utc=isoclock(first[0]['epoch']) if first else None,
            first_admission_divergence=dict(recorded=first[0], stress=first[1]) if first else None,
            matching_equal_volume_positions=len(matched_same_volume), cost_checks=matched_same_volume,
            all_equal_volume_stress_trades_no_better=True,
            explanation='Higher costs alter the cash/equity path and therefore reserved-risk admission. Aggregate outcomes across different admitted trades are not a same-trade execution-cost comparison.'))
    fixed = next(x for x in diagnostics if x['scenario'] == 'fixed50')
    require(fixed['first_admission_divergence_utc'] == '2026-09-11T08:00:00+00:00',
            'Unexpected first fixed-risk admission divergence', 'cost_paths')
    fixed['specific_explanation'] = (
        '11 September USDJPY London #12: recorded path admits $49.1335 planned risk at equity $877.95, '
        'with $816.033125 projected protected cash. Stress has equity $852.58 and projected $790.663125, '
        'so rejects below the $800 floor. The admitted recorded trade loses $49.40 and leaves $828.55. '
        'Stress later admits a smaller-lot gold overlap position with $38.052 risk and wins $19.21, '
        'then a subsequent Nasdaq trade wins $90.11. Different future admitted trades explain the '
        'higher stressed ending cash; adding cost did not improve any identical-volume closed position.')
    return diagnostics


def main():
    frozen, results = load(ROOT/'FROZEN.json'), load(ROOT/'RESULTS.json')
    original_frozen = load(PARENT/'FROZEN.json')
    data, native = load(PARENT/'INPUTS.json'), load(PARENT/'native_cases.json')
    source.verify_sources(data, native, original_frozen)
    original_plan = load(PARENT/'PLAN.json')
    begin, end = (int(datetime.fromisoformat(original_plan[key]).timestamp())
                  for key in ('start_utc', 'end_exclusive_utc'))
    verify_native_mark_values(data, native, begin, end)
    for path, expected in {**frozen['files'], **frozen['source_files']}.items():
        require(digest(path) == expected, ('Supplement frozen file changed', path), 'supplement_freeze')
    require(frozen['frozen_before_new_outcomes'] is True, 'Supplement freeze ordering declaration', 'supplement_freeze')
    require(results['frozen_sha256'] == digest(ROOT/'FROZEN.json'), 'Outcome freeze receipt', 'supplement_freeze')
    plan = load(ROOT/'PLAN.json')
    broker = load(PARENT/'BROKER.json')
    require(results['plan'] == plan and results['broker'] == broker, 'Plan/broker publication mismatch', 'protocol')
    expected_pairs = {(s['id'], stress) for s in plan['scenarios'] for stress in (False, True)}
    pairs = [(r['scenario']['id'], r['stress']) for r in results['results']]
    require(len(pairs) == 10 and set(pairs) == expected_pairs, 'Ten unique paired scenarios expected', 'protocol')
    summaries, detailed = [], {}
    for record in results['results']:
        summary, decisions = audit(record, data, original_plan, plan, broker)
        summaries.append(summary)
        detailed[(record['scenario']['id'], record['stress'])] = decisions
    cost_paths = compare_cost_paths(results['results'], detailed)
    payload = dict(status='PASS', checks=sum(source.CHECKS.values()), categories=dict(source.CHECKS),
        verified_candidates=len(data['candidates']), native_source_eas=len(native['cases']),
        scenarios=summaries, cost_path_diagnostics=cost_paths,
        result_sha256=digest(ROOT/'RESULTS.json'), freeze_sha256=digest(ROOT/'FROZEN.json'),
        verifier_sha256=digest(__file__), method=(
            'Independent separate event ledger and sizing/guard reconstruction, without importing run.py '
            'or replay.py or accessing an account. Independently validates native receipts through the '
            'original read-only verifier, every decision, volume, planned risk, curve point, cent cash flow, '
            'whole-position net, censored entry fee, past-only mark, count, latch, drawdown, daily/monthly '
            'cash and Sharpe. All original and supplemental frozen hashes remain unchanged.'),
        limitations=[
            'Implementation/evidence verification, not verification of a durable trading edge or future returns.',
            'Only immutable standalone source fills; additional or changed live signals, market impact, commission tiers and fill differences are not reconstructed.',
            'Trial16 native history and Trial15 demo lot/margin metadata are different feeds.',
            'Five-minute observed floating marks and missing open-swap marks cannot certify intrabar loss caps.',
            'The fixed-risk cost stress follows a different admission path; its improved aggregate result is not evidence that higher execution costs are beneficial.',
            'The $800 threshold is an initial-capital floor, not a 20% trailing maximum-drawdown guarantee.'
        ])
    (ROOT/'VERIFICATION.json').write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
