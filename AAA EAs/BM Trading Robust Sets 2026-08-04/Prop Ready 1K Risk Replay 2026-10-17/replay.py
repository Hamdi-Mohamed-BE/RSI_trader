"""Research-only immutable-signal $1K portfolio replay; never accesses an account.

Risk budgets, source lot ceilings and entry guards are kept separate. Native
single-EA signals are not a native simultaneous portfolio or a live forecast.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
from bisect import bisect_left
import csv
import hashlib
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PACKAGE = BASE/'_00 Live profiles/Packages/PropReady'
UTC = timezone.utc
PRAGUE = ZoneInfo('Europe/Prague')
START = int(datetime(2026, 8, 17, tzinfo=UTC).timestamp())
END = int(datetime(2026, 10, 17, tzinfo=UTC).timestamp())
REFERENCE = 1000.
PERCENT_SOURCES = frozenset(('us100-orb-new-york-m30', 'xau-orb-new-york-m30', 'us100-selective-orb-v3'))
SCENARIOS = (
    dict(id='fixed_2p50', label='Fixed $2.50', mode='fixed', value=2.5),
    dict(id='percent_0p25', label='Dynamic 0.25%', mode='percent', value=.25),
    dict(id='fixed_5', label='Fixed $5', mode='fixed', value=5.),
    dict(id='percent_0p50', label='Dynamic 0.50%', mode='percent', value=.5),
    dict(id='percent_1', label='Dynamic 1% (still capped)', mode='percent', value=1.),
)


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def iso(t):
    return datetime.fromtimestamp(t, UTC).isoformat()


def day(t):
    return datetime.fromtimestamp(t, PRAGUE).date().isoformat()


def floor_lots(value, step):
    return max(0., round(math.floor(value/step+1e-9)*step, 8))


def risk_lots(equity, unit, spec, scenario, source_mode='fixed50', reference=REFERENCE):
    if not all(math.isfinite(x) and x > 0 for x in (equity, unit, reference)):
        return 0., 0., 0.
    cash = 50. if source_mode == 'fixed50' else equity*.005
    requested = min(spec['volume_max'], max(spec['volume_min'],
                    math.ceil((min(cash/unit, spec['volume_max'])-1e-12)/spec['volume_step'])*spec['volume_step']))
    allocation = scenario['value'] if scenario['mode'] == 'fixed' else equity*scenario['value']/100.
    budget = min(reference*.005, allocation)
    volume = floor_lots(min(requested, budget/unit, spec['volume_max']), spec['volume_step'])
    return (volume if volume >= spec['volume_min']-1e-9 else 0.), requested, budget


def margin_unit(row, spec, multiplier=1.):
    if row.get('receipt_margin_one_lot') is not None:
        return row['receipt_margin_one_lot']*multiplier
    # Current read-only OrderCalcMargin ratio applied to historical entry prices.
    # Not a reconstruction of broker historical/high-margin-requirement tiers.
    side = 'buy' if row['side'].lower() in ('buy', 'long', '0') else 'sell'
    current = spec[side+'_margin_one_lot']
    if row['symbol'] == 'USDJPY':
        return current*multiplier
    quote = spec['ask'] if side == 'buy' else spec['bid']
    return current*(row['open_price']/quote)*multiplier


def extra_cost_unit(row, spec, side):
    # Explicit sensitivity: ONE additional observed snapshot spread at EACH side.
    price = row['open_price'] if side == 'entry' else row['close_price']
    return spec['quote_spread']*spec['trade_contract_size']/(price if row['symbol'] == 'USDJPY' else 1.)


def native_candidate(row, trade, deals, owned):
    volume = float(trade['volume'])
    assert volume > 0
    opened = [d for d in deals if int(d['entry']) == 0]
    assert len(opened) == 1, 'Partial/multiple opens need a different ownership model'
    entry_cost = sum(float(opened[0][k]) for k in ('gross', 'commission', 'swap', 'fee'))/volume
    symbol = row['symbol']
    forced = any('end of test' in s.lower() for s in trade['exit_comments'])
    assert float(trade['sl']) > 0, 'Missing original stop'
    unit = abs(trade['open_price']-trade['sl'])*{'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000.}[symbol]
    if symbol == 'USDJPY':
        # Historical fill quote proxy; an exact entry-time OrderCalcProfit
        # receipt, if present, supersedes this approximation in prepare().
        unit /= trade['open_price']
    assert math.isfinite(unit) and unit > 0
    return dict(id=row['slug']+'|'+str(trade['position_id']), ea=row['slug'], symbol=symbol,
                position_id=trade['position_id'], op=trade['open_epoch'], cl=None if forced else trade['close_epoch'],
                end_censored=forced, side=trade['side'], open_price=trade['open_price'], close_price=trade['close_price'],
                sl=trade['sl'], tp=trade['tp'], unit_risk=unit, unit_risk_method='filled_quote_geometry_proxy',
                source_mode='percent0p5' if row['slug'] in PERCENT_SOURCES else 'fixed50',
                source_volume=volume, entry_unit_cost=entry_cost,
                unit_gross=trade['gross']/volume, unit_commission=(trade['commission']+trade['fee'])/volume,
                unit_swap=trade['swap']/volume, marks=owned)


def prepare():
    assert not (ROOT/'RESULTS.json').exists(), 'Never refreeze a protocol after risk outcomes'
    package = read(PACKAGE/'PACKAGE.json')
    broker = read(ROOT/'BROKER.json')
    assert broker['currency'] == 'USD' and broker['demo'] and broker['hedging']
    assert broker['leverage'] == 2000 and broker['server'] == 'Exness-MT5Trial15'
    expected = [e['slug'] for e in package['entries']]
    cases = read(ROOT/'native_cases.json')
    assert cases['start'] == '2026-08-17' and cases['end_exclusive'] == '2026-10-17'
    assert cases['source_server'] == 'Exness-MT5Trial16', 'Explicit fallback source must not silently change'
    assert sorted(e['slug'] for e in cases['cases']) == sorted(expected)
    candidates, coverage, hashes, spot_checks = [], [], {}, {}
    benchmarks = read(ROOT/'DEMO-BENCHMARKS.json')
    for meta in cases['cases']:
        path = Path(meta['path'])
        assert sha(path) == meta['sha256'], ('Native completion receipt changed', meta['slug'])
        case = read(path)
        trades = sorted(case['trades'], key=lambda x: (x['open_epoch'], x['position_id']))
        assert all(not t['partial'] for t in trades)
        assert all(a['close_epoch'] <= b['open_epoch'] for a, b in zip(trades, trades[1:])), 'Ambiguous floating ownership'
        by_pid = defaultdict(list)
        for d in csv.DictReader((path.parent/'deals.csv').open(encoding='utf-8-sig')):
            by_pid[int(d['position_id'])].append(d)
        boundaries = {int(t[k]) for t in trades for k in ('open_epoch', 'close_epoch')}
        opens = [t['open_epoch'] for t in trades]
        marks = defaultdict(list)
        previous = None
        dropped = Counter()
        first = last = None
        for m in csv.DictReader((path.parent/'equity.csv').open(encoding='utf-8-sig')):
            t = int(m['epoch'])
            if first is None:
                first = t
            last = t
            if not START <= t < END:
                continue
            assert previous is None or t >= previous
            if t == previous:
                dropped['duplicate'] += 1
                continue
            previous = t
            balance, equity = float(m['balance']), float(m['equity'])
            assert math.isfinite(balance) and math.isfinite(equity)
            if t in boundaries:
                dropped['position_boundary'] += 1
                continue
            i = bisect_left(opens, t)-1
            if i >= 0 and trades[i]['open_epoch'] < t < trades[i]['close_epoch']:
                trade = trades[i]
                swap = None if not m.get('open_swap') else float(m['open_swap'])/trade['volume']
                marks[trade['position_id']].append([t, (equity-balance)/trade['volume'], swap])
            else:
                assert abs(equity-balance) < .021, ('Unowned floating', meta['slug'], t)
                dropped['flat'] += 1
        # Friday's verified last available quote precedes UTC midnight. Require
        # coverage through that CURRENT demo close, not invented closed-hour ticks.
        quote_end = broker['symbols'][meta['symbol']]['quote_epoch']
        assert START <= quote_end < END and quote_end >= END-6*3600
        assert first is not None and first <= START and last >= quote_end-600, ('Incomplete curve', meta['slug'], first, last, quote_end)
        selected = [native_candidate(meta, t, by_pid[t['position_id']], marks[t['position_id']])
                    for t in trades if START <= t['open_epoch'] < END]
        risk_path = path.parent/'entry_risk.csv'
        receipts = list(csv.DictReader(risk_path.open(encoding='utf-8-sig')))
        by_receipt = {int(r['position_id']): r for r in receipts}
        assert len(by_receipt) == len(receipts), 'Duplicate initial risk receipts'
        for candidate in selected:
            receipt = by_receipt[candidate['position_id']]
            assert int(receipt['calculation_ok']) == 1 and receipt['sl_source'] == 'entry_order'
            assert receipt['symbol'] == candidate['symbol']
            assert abs(float(receipt['entry_price'])-candidate['open_price']) < 1e-7
            assert abs(float(receipt['sl'])-candidate['sl']) < 1e-7
            assert abs(int(receipt['epoch'])-candidate['op']) <= 1
            assert abs(int(receipt['quote_epoch'])-candidate['op']) <= 30
            assert int(receipt['margin_ok']) == 1
            unit = float(receipt['unit_risk'])
            assert math.isfinite(unit) and unit > 0
            assert math.isfinite(float(receipt['margin_one_lot'])) and float(receipt['margin_one_lot']) >= 0
            candidate.update(unit_risk=unit, unit_risk_method='native_actual_fill_OrderCalcProfit',
                             receipt_margin_one_lot=float(receipt['margin_one_lot']),
                             source_fill_quote_bid=float(receipt['quote_bid']), source_fill_quote_ask=float(receipt['quote_ask']))
        benchmark_path = path.parent/'benchmarks.csv'
        for sample in csv.DictReader(benchmark_path.open(encoding='utf-8-sig')):
            if int(sample['requested_epoch']) != 1792072800:
                continue
            symbol = meta['symbol']
            current = benchmarks['bars'][symbol]
            spot_checks[symbol] = dict(symbol=symbol, epoch=1792072800,
                native_server='Exness-MT5Trial16', current_server=broker['server'],
                native={k: float(sample[k]) for k in ('open','high','low','close','spread','tick_volume')},
                current=current,
                close_difference_current_minus_native=current['close']-float(sample['close']),
                full_feed_parity_proven=False)
        candidates.extend(selected)
        coverage.append(dict(ea=meta['slug'], source=str(path), first_epoch=first, last_epoch=last,
                             current_demo_final_quote_epoch=quote_end, end_coverage_convention='Through verified Friday market-close quote; no invented closed-hour ticks.',
                             candidates=len(selected), native=case['native'], discarded=dict(dropped),
                             zero_spread_entry_receipts=sum(abs(float(r['quote_ask'])-float(r['quote_bid']))<1e-10 for r in receipts),
                             end_censored=sum(x['end_censored'] for x in selected),
                             owned_marks=sum(len(x['marks']) for x in selected)))
        for source in (path, path.parent/'deals.csv', path.parent/'equity.csv', risk_path, benchmark_path):
            hashes[str(source)] = sha(source)
    assert set(x['ea'] for x in coverage) == set(expected)
    data = dict(candidates=candidates, coverage=coverage, feed_spot_checks=spot_checks)
    save(ROOT/'INPUTS.json', data)
    plan = dict(start_utc=iso(START), end_exclusive_utc=iso(END), initial_balance=REFERENCE,
        currency='USD', broker=broker['broker'], server=broker['server'], account_leverage=broker['leverage'],
        phase='Funded/continuous', priority=expected, scenarios=SCENARIOS,
        sensitivities=['recorded_native_costs', 'one_additional_snapshot_spread_each_side_and_double_negative_swap'],
        source_sizing='Six original wrapped helpers request fixed50cash; three added ORBs request0.5%currentequity; source ceiling rounds upward. Guard separately floors, rejects below minimum.',
        reference_risk_cap=.005, guard=dict(open_risk=.0225, same_symbol=.015, daily_reserved=.03,
            equity_buffer=.92, hard_equity_floor=.90, hard_daily_loss=.05, entries_per_day=7,
            losing_positions_per_day=3, per_position_slippage_reserve=.25, per_position_cash_reserve=.0005),
        trading_day='Europe/Prague calendar midnight including DST; first deployment anchor1000, no carry-in.',
        compounding='Percentage uses current sampled equity but cannot exceed $5 or original request. No automatic reference rebasing.',
        model='Estimated immutable-native-signal ledger replay, not simultaneous native or live execution.',
        source_server=cases.get('source_server','Exness-MT5Trial16'),
        feed_caveat='Historical native candidates are isolated ExnessTrial16; current demo lot/margin metadata are ExnessTrial15. Spot checks show DIFFERENT quotes/spreads (source USDJPY/USTEC often zero spread). Not a same-account native portfolio or exact current-demo cost test.',
        margin='Native source fill-time OrderCalcMargin receipts at1:2000 after contract/lot/currency parity checks; gross sum no hedge discount. Current-demo snapshot margin recorded. Not verified historical live tiers/HMR.',
        marks='Strict own-position past five-minute samples; zero until first owned sample, past carry, ages disclosed; no future interpolation. Missing current open-swap reserve explicitly counted.',
        risk_geometry='Actual fill-time native OrderCalcProfit one-lot receipt using original entry-order SL. Pre-request bid/ask geometry and slippage boundary are not reconstructed.',
        costs='BASE is sourceTrial16 recorded native spread/fills/fees/swap scaled byadmittedvolume, NOT actualTrial15Pro costs. STRESS addsone currentTrial15 snapshotspread EACHside and twice negativefinalswap; sensitivitynotexactProreproduction. Sourceexitsunchanged.',
        alternative_search=False, live_changes=False, rebase_reference=False,
        limitations=['Two exposed months do not establish a durable edge or an optimal live risk setting.',
            'Only observed standalone source fills are available; rejected trades can create unobserved later signals.',
            'Sampled equity is not tick maximum drawdown; guard slippage, request budgets, cooldown wallclock and full current-SL timeline are not reconstructed.',
            'Recorded costs are native tester costs, not verified historical commission/financing schedules.',
            'Snapshot spreads and margins are sensitivities/estimates, not historic realized execution or fixed future conditions.'])
    save(ROOT/'PLAN.json', plan)
    for file in (ROOT/'PLAN.json', ROOT/'INPUTS.json', ROOT/'BROKER.json', ROOT/'DEMO-BENCHMARKS.json', ROOT/'replay.py',
                 PACKAGE/'PACKAGE.json', PACKAGE/'CalyxFTMOGuard.mqh'):
        hashes[str(file)] = sha(file)
    save(ROOT/'FROZEN.json', dict(files=hashes, prepared_before_risk_outcomes=True))
    print(json.dumps(dict(candidates=len(candidates), coverage=coverage), indent=2))


class Replay:
    def __init__(self, scenario, broker, stress=False, reference=REFERENCE):
        self.scenario, self.broker, self.stress, self.reference = scenario, broker, stress, reference
        self.balance = self.equity = self.anchor = reference
        self.peak = self.closed_peak = self.day_peak = self.day_closed_peak = reference
        self.dd = self.dd_pct = self.closed_dd = self.closed_dd_pct = 0.
        self.daily_eq_dd = self.daily_closed_dd = self.daily_anchor_loss = 0.
        self.active = {}
        self.daily_entries = self.daily_losses = 0
        self.today = None
        self.day_stopped = self.breached = False
        self.last_entry = -math.inf
        self.trades, self.decisions, self.curve = [], [], []
        self.counts = Counter()
        self.per_ea = defaultdict(Counter)
        self.mark_quality = Counter()
        self.max_mark_age = 0
        self.max_initial_lag = 0

    def observe(self, t, record=True):
        current_day = day(t)
        if current_day != self.today:
            self.today = current_day
            self.anchor = self.balance
            self.daily_entries = self.daily_losses = 0
            self.day_stopped = False
            self.day_peak = self.balance
            self.day_closed_peak = self.balance
        self.equity = self.balance+sum(p['mark_unit']*p['lots'] for p in self.active.values())
        for p in self.active.values():
            if p['mark_epoch'] is None:
                self.mark_quality['initial_zero_observations'] += 1
                self.max_initial_lag = max(self.max_initial_lag, max(0, t-p['row']['op']))
            else:
                age = max(0, t-p['mark_epoch'])
                self.max_mark_age = max(self.max_mark_age, age)
                self.mark_quality['stale_over_900s_observations'] += age > 900
        self.peak, self.closed_peak = max(self.peak, self.equity), max(self.closed_peak, self.balance)
        self.day_peak, self.day_closed_peak = max(self.day_peak, self.equity), max(self.day_closed_peak, self.balance)
        self.dd = max(self.dd, self.peak-self.equity)
        self.dd_pct = max(self.dd_pct, 100*(self.peak-self.equity)/self.peak)
        self.closed_dd = max(self.closed_dd, self.closed_peak-self.balance)
        self.closed_dd_pct = max(self.closed_dd_pct, 100*(self.closed_peak-self.balance)/self.closed_peak)
        self.daily_eq_dd = max(self.daily_eq_dd, self.day_peak-self.equity)
        self.daily_closed_dd = max(self.daily_closed_dd, self.day_closed_peak-self.balance)
        self.daily_anchor_loss = max(self.daily_anchor_loss, self.anchor-self.equity)
        if self.equity <= self.reference*.90 or self.equity <= self.anchor-self.reference*.05:
            self.breached = True
        if self.equity <= self.anchor-self.reference*.03:
            self.day_stopped = True
        if record:
            self.curve.append(dict(epoch=t, balance=self.balance, equity=self.equity))

    def reject(self, row, risk, margin):
        r = self.reference
        if self.breached:
            return 'permanent_loss_latch'
        if self.day_stopped:
            return 'daily_loss_latch'
        if self.daily_entries >= 7:
            return 'daily_seven_entries'
        if self.daily_losses >= 3:
            return 'daily_three_net_losers'
        total = sum(p['risk'] for p in self.active.values())
        same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
        if total+risk > r*.0225+1e-7:
            return 'aggregate_risk'
        if same+risk > r*.015+1e-7:
            return 'same_symbol_risk'
        reserve = sum(p['risk']*1.25+r*.0005+max(0., -p['swap_unit']*p['lots']) for p in self.active.values())
        projected = min(self.equity, self.balance-reserve)-risk*1.25-r*.0005
        if projected < r*.92:
            return 'equity_buffer'
        if self.anchor-projected > r*.03:
            return 'daily_reserved_loss'
        existing = sum(p['margin'] for p in self.active.values())
        if existing+margin > projected*.8 or margin > self.equity-existing:
            return 'margin_proxy'
        if row['op'] < self.last_entry+3:
            return 'three_second_wait'
        return None

    def opening(self, row, t):
        self.observe(t)
        self.per_ea[row['ea']]['candidates'] += 1
        spec = self.broker['symbols'][row['symbol']]
        lots, source, budget = risk_lots(self.equity, row['unit_risk'], spec, self.scenario, row['source_mode'], self.reference)
        reason = None
        if any(p['row']['ea'] == row['ea'] for p in self.active.values()):
            reason = 'same_ea_exposure'
        elif lots <= 0:
            reason = 'minimum_lot_over_budget'
        risk = lots*row['unit_risk']
        margin = lots*margin_unit(row, spec)
        if reason is None:
            reason = self.reject(row, risk, margin)
        decision = dict(id=row['id'], ea=row['ea'], epoch=t, equity=self.equity, budget=budget,
                        source_volume_ceiling=source, volume=lots, stop_risk=risk,
                        minimum_lot_risk=spec['volume_min']*row['unit_risk'], reason=reason or 'opened')
        self.decisions.append(decision)
        self.counts[reason or 'opened'] += 1
        self.per_ea[row['ea']][reason or 'opened'] += 1
        if reason:
            return
        assert risk <= self.reference*.005+1e-7 and risk <= budget+1e-7 and lots <= source+1e-8
        cost = row['entry_unit_cost']*lots
        if self.stress:
            cost -= extra_cost_unit(row, spec, 'entry')*lots
        entry = round(cost, 2)
        self.balance = round(self.balance+entry, 2)
        self.active[row['id']] = dict(row=row, lots=lots, risk=risk, margin=margin,
            entry_cash=entry, mark_unit=0., swap_unit=0., mark_epoch=None)
        self.daily_entries += 1
        self.last_entry = t
        self.observe(t)

    def mark(self, row, mark, t):
        if row['id'] not in self.active:
            return
        p = self.active[row['id']]
        assert row['op'] < mark[0] <= t and (row['cl'] is None or mark[0] < row['cl'])
        if p['mark_epoch'] is None:
            self.max_initial_lag = max(self.max_initial_lag, mark[0]-row['op'])
        p.update(mark_unit=mark[1], mark_epoch=mark[0], swap_unit=mark[2] if mark[2] is not None else 0.)
        self.mark_quality['owned_marks'] += 1
        self.mark_quality['missing_open_swap_marks'] += mark[2] is None
        self.observe(t)

    def closing(self, row, t):
        if row['id'] not in self.active:
            return
        self.observe(t)
        p = self.active.pop(row['id'])
        swap = row['unit_swap']*(2 if self.stress and row['unit_swap'] < 0 else 1)
        cash = (row['unit_gross']+row['unit_commission']+swap-row['entry_unit_cost'])*p['lots']
        if self.stress:
            cash -= extra_cost_unit(row, self.broker['symbols'][row['symbol']], 'exit')*p['lots']
        exit_cash = round(cash, 2)
        net = round(exit_cash+p['entry_cash'], 2)
        self.balance = round(self.balance+exit_cash, 2)
        self.daily_losses += net < -.005
        self.trades.append(dict(id=row['id'], ea=row['ea'], symbol=row['symbol'], op=row['op'], cl=t,
            side=row['side'], open_price=row['open_price'], close_price=row['close_price'], sl=row['sl'], tp=row['tp'],
            lots=p['lots'], risk=p['risk'], entry_cash=p['entry_cash'], exit_cash=exit_cash, net=net,
            balance=self.balance, gross=row['unit_gross']*p['lots'], commission=row['unit_commission']*p['lots'],
            swap=swap*p['lots']))
        self.counts['closed'] += 1
        self.per_ea[row['ea']]['closed'] += 1
        self.observe(t)

    def result(self):
        self.observe(END-1)
        metrics = cash_metrics(self.trades, self.reference)
        daily, months, sharpe = calendar_cash(self.trades, self.reference)
        metrics.update(ending_balance=self.balance, ending_sampled_equity=self.equity,
            return_pct=(self.balance/self.reference-1)*100., open_positions=len(self.active),
            ending_equity_return_pct=(self.equity/self.reference-1)*100.,
            daily_closed_return_sharpe=sharpe, sharpe_annualization=365,
            max_sampled_equity_dd_cash=self.dd, max_sampled_equity_dd_pct=self.dd_pct,
            max_closed_dd_cash=self.closed_dd, max_closed_dd_pct=self.closed_dd_pct,
            max_daily_sampled_equity_dd_cash=self.daily_eq_dd, max_daily_closed_dd_cash=self.daily_closed_dd,
            max_daily_anchor_equity_loss=self.daily_anchor_loss,
            hard_loss_latch=self.breached, counts=dict(self.counts), average_trades_per_calendar_day=len(self.trades)/61,
            average_trades_per_weekday=len(self.trades)/45)
        quality = Counter(self.mark_quality)
        for c in self.curve:
            assert all(math.isfinite(c[k]) for k in ('balance', 'equity'))
        quality['maximum_past_mark_age_seconds'] = self.max_mark_age
        quality['maximum_initial_zero_segment_seconds'] = self.max_initial_lag
        return dict(scenario=self.scenario, stress=self.stress, metrics=metrics, daily=daily, months=months,
                    per_ea={k: dict(v) for k, v in self.per_ea.items()}, trades=self.trades,
                    decisions=self.decisions, curve=self.curve, mark_quality=dict(quality))


def cash_metrics(trades, initial=REFERENCE):
    values = [t['net'] for t in trades]
    wins, losses = [x for x in values if x > 0], [x for x in values if x < 0]
    w = l = mw = ml = 0
    for x in values:
        w = w+1 if x > 0 else 0
        l = l+1 if x < 0 else 0
        mw, ml = max(mw, w), max(ml, l)
    return dict(trades=len(values), win_rate_pct=100*len(wins)/len(values) if values else None,
                profit_factor=sum(wins)/-sum(losses) if losses else None,
                profit_factor_status='finite' if losses else 'no_losing_trades' if wins else 'no_trades',
                net_profit=round(sum(values), 2), wins=len(wins), losses=len(losses),
                max_win_streak=mw, max_loss_streak=ml,
                average_win=statistics.mean(wins) if wins else None,
                average_loss=statistics.mean(losses) if losses else None,
                largest_win=max(wins) if wins else None, largest_loss=min(losses) if losses else None)


def calendar_cash(trades, initial=REFERENCE):
    flows = defaultdict(float)
    closes = Counter()
    for t in trades:
        flows[iso(t['op'])[:10]] += t['entry_cash']
        flows[iso(t['cl'])[:10]] += t['exit_cash']
        closes[iso(t['cl'])[:10]] += 1
    rows, rates = [], []
    balance = initial
    stamp = START
    while stamp < END:
        label = iso(stamp)[:10]
        value = round(flows[label], 2)
        opening = balance
        balance = round(balance+value, 2)
        rates.append(value/opening if opening > 0 else 0.)
        rows.append(dict(date=label, opening_balance=opening, net_profit=value, ending_balance=balance,
                         return_pct=value/opening*100 if opening > 0 else None, trades=closes[label]))
        stamp += 86400
    months = []
    for label in dict.fromkeys(d['date'][:7] for d in rows):
        ds = [d for d in rows if d['date'].startswith(label)]
        ts = [t for t in trades if iso(t['cl']).startswith(label)]
        months.append(dict(month=label, first_date=ds[0]['date'], last_date=ds[-1]['date'],
            opening_balance=ds[0]['opening_balance'], ending_balance=ds[-1]['ending_balance'],
            net_profit=round(sum(d['net_profit'] for d in ds), 2),
            return_pct=(ds[-1]['ending_balance']/ds[0]['opening_balance']-1)*100,
            position_metrics=cash_metrics(ts, initial)))
    sharpe = statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365) if len(rates)>1 and statistics.stdev(rates)>0 else None
    return rows, months, sharpe


def events_for(plan, data):
    priority = {s: i for i, s in enumerate(plan['priority'])}
    events = []
    for row in data['candidates']:
        events.append((row['op'], 3, priority[row['ea']], row['id'], row, None))
        if row['cl'] is not None and row['cl'] < END:
            events.append((row['cl'], 4 if row['cl'] == row['op'] else 1, priority[row['ea']], row['id'], row, None))
        for mark in row['marks']:
            events.append((mark[0], 2, priority[row['ea']], row['id'], row, mark))
    d = datetime.fromtimestamp(START, PRAGUE).date()
    while True:
        t = datetime.combine(d, datetime.min.time(), tzinfo=PRAGUE).timestamp()
        if t >= END:
            break
        if t >= START:
            events.append((t, 0, -1, '', None, None))
        d += timedelta(days=1)
    return sorted(events, key=lambda e: e[:4])


def run():
    frozen = read(ROOT/'FROZEN.json')
    assert all(sha(p) == digest for p, digest in frozen['files'].items()), 'Frozen inputs changed'
    plan, data, broker = read(ROOT/'PLAN.json'), read(ROOT/'INPUTS.json'), read(ROOT/'BROKER.json')
    events = events_for(plan, data)
    results = []
    for stress in (False, True):
        for scenario in SCENARIOS:
            model = Replay(scenario, broker, stress)
            for t, kind, _, _, row, mark in events:
                if not START <= t < END:
                    continue
                if kind == 0:
                    model.observe(t)
                elif kind in (1, 4):
                    model.closing(row, t)
                elif kind == 2:
                    model.mark(row, mark, t)
                else:
                    model.opening(row, t)
            result = model.result()
            results.append(result)
            print(scenario['label'], 'stress' if stress else 'recorded', result['metrics'], flush=True)
    feasibility = []
    for ea in plan['priority']:
        rows = [r for r in data['candidates'] if r['ea'] == ea]
        risks = [r['unit_risk']*broker['symbols'][r['symbol']]['volume_min'] for r in rows]
        feasibility.append(dict(ea=ea, candidates=len(rows), minimum_lot_risk_min=min(risks) if risks else None,
            minimum_lot_risk_max=max(risks) if risks else None, candidates_fitting_5=sum(x<=5+1e-7 for x in risks),
            reference_needed_for_smallest_at_0p5pct=min(risks)/.005 if risks else None,
            reference_needed_for_largest_at_0p5pct=max(risks)/.005 if risks else None))
    save(ROOT/'RESULTS.json', dict(plan=plan, coverage=data['coverage'], feed_spot_checks=data['feed_spot_checks'], results=results, feasibility=feasibility,
         frozen_sha256=sha(ROOT/'FROZEN.json'), broker=broker, generated_at_utc=iso(datetime.now(UTC).timestamp())))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
