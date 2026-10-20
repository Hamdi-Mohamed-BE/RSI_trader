"""Top5 DI-OFF versus Prop Ready DI-ON, explicitly separate policy views.

Local frozen-ledger research only. Never controls a live terminal or installer.
Native source collection is separate, isolated, and frozen before its cases.
"""
from pathlib import Path
from collections import Counter, defaultdict
from bisect import bisect_left
import copy
import csv
import importlib.util
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO = BASE.parents[1]
ORIGINAL = BASE/'Prop Ready 1K Risk Replay 2026-10-17'
ACTUAL = ORIGINAL/'Actual5Percent'
OWNER = REPO/'clients/_owner/top5'
PUBLIC = REPO/'clients/top 5'
NATIVE = ROOT/'native'
_spec = importlib.util.spec_from_file_location('frozen_actual5_comparison_engine', ACTUAL/'run.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
base = engine.base
TOP5 = ('gold-overnight-value-area','xau-rsi-vwap','nasdaq-overnight',
        'nasdaq-5m-candle-momentum','orb-volume-profile')
SCENARIOS = tuple(dict(portfolio=portfolio, view=view, id=name,
    label='Fixed $50' if name == 'fixed50' else ('5% current balance' if portfolio == 'top5' and view == 'as_packaged' else '5% current equity'),
    mode='fixed' if name == 'fixed50' else ('balance' if portfolio == 'top5' and view == 'as_packaged' else 'percent'),
    value=50. if name == 'fixed50' else 5.,
    guard_policy='client' if portfolio == 'top5' and view == 'as_packaged' else 'current' if view == 'as_packaged' else 'research_10daily_20total')
    for view in ('as_packaged','common_research') for portfolio in ('top5','prop_ready') for name in ('fixed50','compound5'))


def client_lots(balance, unit, spec, scenario):
    """Mirror ClientGuard: BALANCE%, floor then broker MINIMUM override."""
    if not all(math.isfinite(x) and x > 0 for x in (balance, unit)):
        return 0., 0., False
    budget = scenario['value'] if scenario['mode'] == 'fixed' else balance*scenario['value']/100.
    if not math.isfinite(budget) or budget <= 0:
        return 0., 0., False
    step = spec['volume_step']
    volume = round(min(math.floor((budget/unit+1e-10)/step)*step, spec['volume_max']), 8)
    override = volume < spec['volume_min']
    if override:
        volume = spec['volume_min']
    return volume, budget, override


def client_cash_calendar(flows, initial=1000.):
    """Cash-only dates; zero/negative opening cash has no valid return rate."""
    per_day = defaultdict(float)
    for flow in flows:
        per_day[base.iso(flow['epoch'])[:10]] += flow['cash']
    rows, rates, balance = [], [], initial
    for t in range(base.START,base.END,86400):
        label, opening = base.iso(t)[:10],balance
        value = round(per_day[label],2)
        balance = round(balance+value,2)
        rates.append(value/opening if opening > 0 else None)
        rows.append(dict(date=label,opening_balance=opening,net_profit=value,ending_balance=balance))
    months = []
    for label in dict.fromkeys(r['date'][:7] for r in rows):
        ds = [r for r in rows if r['date'].startswith(label)]
        opening, ending = ds[0]['opening_balance'],ds[-1]['ending_balance']
        months.append(dict(month=label,first_date=ds[0]['date'],last_date=ds[-1]['date'],
            opening_balance=opening,ending_balance=ending,net_profit=round(sum(r['net_profit'] for r in ds),2),
            return_pct=(ending/opening-1)*100. if opening > 0 else None))
    valid = all(r is not None for r in rates)
    sharpe = statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365) if valid and statistics.stdev(rates)>0 else None
    return rows,months,sharpe


class ClientReplay(engine.ResearchReplay):
    """Delivered client sizing, WITHOUT invented Prop Ready loss/risk guards."""
    def __init__(self, scenario, broker, stress=False, reference=1000.):
        super().__init__(scenario, broker, stress, reference)
        self.capital_exhaustion_epoch = None
        self.minimum_sampled_margin_level = None

    def budget(self):
        return self.scenario['value'] if self.scenario['mode'] == 'fixed' else self.balance*self.scenario['value']/100.

    def observe(self, t, record=True):
        self.equity = self.balance+sum(p['mark_unit']*p['lots'] for p in self.active.values())
        current_day = base.day(t)
        if current_day != self.today:
            self.today, self.anchor = current_day, self.balance
            self.daily_entries = self.daily_losses = 0
            self.day_peak, self.day_closed_peak = self.equity, self.balance
        for p in self.active.values():
            if p['mark_epoch'] is None:
                self.mark_quality['initial_zero_observations'] += 1
                self.max_initial_lag = max(self.max_initial_lag, max(0, t-p['row']['op']))
            else:
                age = max(0, t-p['mark_epoch'])
                self.max_mark_age = max(self.max_mark_age, age)
                self.mark_quality['stale_over_900s_observations'] += age > 900
        self.peak, self.closed_peak = max(self.peak,self.equity), max(self.closed_peak,self.balance)
        self.day_peak, self.day_closed_peak = max(self.day_peak,self.equity), max(self.day_closed_peak,self.balance)
        self.dd = max(self.dd,self.peak-self.equity)
        self.dd_pct = max(self.dd_pct,100*(self.peak-self.equity)/self.peak)
        self.closed_dd = max(self.closed_dd,self.closed_peak-self.balance)
        self.closed_dd_pct = max(self.closed_dd_pct,100*(self.closed_peak-self.balance)/self.closed_peak)
        self.daily_eq_dd = max(self.daily_eq_dd,self.day_peak-self.equity)
        self.daily_closed_dd = max(self.daily_closed_dd,self.day_closed_peak-self.balance)
        self.daily_anchor_loss = max(self.daily_anchor_loss,self.anchor-self.equity)
        if self.equity <= 0 and self.capital_exhaustion_epoch is None:
            self.capital_exhaustion_epoch = t
        margin = sum(p['margin'] for p in self.active.values())
        if margin > 0:
            level = self.equity/margin*100.
            self.minimum_sampled_margin_level = level if self.minimum_sampled_margin_level is None else min(level,self.minimum_sampled_margin_level)
        if record:
            self.curve.append(dict(epoch=t,balance=self.balance,equity=self.equity))

    def opening(self, row, t):
        self.observe(t)
        self.per_ea[row['ea']]['candidates'] += 1
        spec = self.broker['symbols'][row['symbol']]
        lots, budget, override = client_lots(self.balance,row['unit_risk'],spec,self.scenario)
        risk, margin = lots*row['unit_risk'], lots*base.margin_unit(row,spec)
        used = sum(p['margin'] for p in self.active.values())
        reason = None
        if self.capital_exhaustion_epoch is not None or self.equity <= 0:
            reason = 'capital_exhaustion_unresolved'
        elif any(p['row']['ea'] == row['ea'] for p in self.active.values()):
            reason = 'same_ea_exposure'
        elif lots <= 0:
            reason = 'invalid_budget'
        elif margin > self.equity-used:
            reason = 'margin_proxy'
        self.decisions.append(dict(id=row['id'],ea=row['ea'],epoch=t,equity=self.equity,balance=self.balance,
            budget=budget,source_volume_ceiling=None,volume=lots,stop_risk=risk,
            minimum_lot_risk=spec['volume_min']*row['unit_risk'],minimum_lot_override=override,
            stop_risk_pct_equity=100*risk/self.equity if self.equity > 0 else None,
            reason=reason or 'opened'))
        self.counts[reason or 'opened'] += 1
        self.per_ea[row['ea']][reason or 'opened'] += 1
        if reason:
            return
        assert risk <= budget+1e-7 or override
        entry = round((row['entry_unit_cost']-(base.extra_cost_unit(row,spec,'entry') if self.stress else 0.))*lots,2)
        self.balance = round(self.balance+entry,2)
        self.flows.append(dict(epoch=t,cash=entry,id=row['id'],kind='entry'))
        self.active[row['id']] = dict(row=row,lots=lots,risk=risk,margin=margin,entry_cash=entry,
            mark_unit=0.,swap_unit=0.,mark_epoch=None)
        self.daily_entries += 1
        self.last_entry = t
        self.observe(t)

    def result(self):
        self.observe(base.END-1)
        daily,months,sharpe = client_cash_calendar(self.flows,self.reference)
        assert abs(daily[-1]['ending_balance']-self.balance)<1e-7
        metrics = base.cash_metrics(self.trades,self.reference)
        metrics.update(ending_balance=self.balance,ending_sampled_equity=self.equity,
            return_pct=(self.balance/self.reference-1)*100.,open_positions=len(self.active),
            ending_equity_return_pct=(self.equity/self.reference-1)*100.,
            daily_closed_return_sharpe=sharpe,sharpe_annualization=365,
            max_sampled_equity_dd_cash=self.dd,max_sampled_equity_dd_pct=self.dd_pct,
            max_closed_dd_cash=self.closed_dd,max_closed_dd_pct=self.closed_dd_pct,
            max_daily_sampled_equity_dd_cash=self.daily_eq_dd,max_daily_closed_dd_cash=self.daily_closed_dd,
            max_daily_anchor_equity_loss=self.daily_anchor_loss,hard_loss_latch=False,counts=dict(self.counts),
            average_trades_per_calendar_day=len(self.trades)/61.,average_trades_per_weekday=len(self.trades)/45.,
            cash_profit=round(self.balance-self.reference,2),unrealized_sampled_profit=self.equity-self.balance,
            first_breach_epoch=None,paused_days=[],
            min_lot_override_entries=sum(d['reason']=='opened' and d.get('minimum_lot_override',False) for d in self.decisions),
            capital_exhaustion_epoch=self.capital_exhaustion_epoch,
            minimum_sampled_margin_level=self.minimum_sampled_margin_level,
            broker_stopout_reconstructed=False,
            historical_path_executable_uncertainty=self.capital_exhaustion_epoch is not None)
        quality = Counter(self.mark_quality)
        quality.update(maximum_past_mark_age_seconds=self.max_mark_age,maximum_initial_zero_segment_seconds=self.max_initial_lag)
        return dict(scenario=self.scenario,stress=self.stress,metrics=metrics,daily=daily,months=months,
            per_ea={k:dict(v) for k,v in self.per_ea.items()},trades=self.trades,decisions=self.decisions,curve=self.curve,
            mark_quality=dict(quality),cash_flows=self.flows,
            open_positions=[dict(id=p['row']['id'],ea=p['row']['ea'],symbol=p['row']['symbol'],op=p['row']['op'],lots=p['lots'],
                initial_risk=p['risk'],paid_entry_cash=p['entry_cash'],mark_epoch=p['mark_epoch'],mark_unit=p['mark_unit'],
                sampled_floating=p['mark_unit']*p['lots']) for p in self.active.values()])


def top5_inputs():
    """Build unit-risk/cash/owned-mark inputs from fresh five-case receipts."""
    index = base.read(NATIVE/'native_cases.json')
    assert index['source_server'] == 'Exness-MT5Trial16'
    assert {r['slug'] for r in index['cases']} == set(TOP5)
    broker = base.read(ORIGINAL/'BROKER.json')
    candidates, coverage, hashes = [], [], {}
    for meta in index['cases']:
        path = Path(meta['path'])
        assert base.sha(path) == meta['sha256']
        case = base.read(path)
        trades = sorted(case['trades'],key=lambda r:(r['open_epoch'],r['position_id']))
        assert all(not t.get('partial',False) for t in trades), 'Partial-position ownership needs a separate model'
        assert all(a['close_epoch'] <= b['open_epoch'] for a,b in zip(trades,trades[1:])), 'Within-EA overlapping ownership unsupported'
        deals = defaultdict(list)
        for d in csv.DictReader((path.parent/'deals.csv').open(encoding='utf-8-sig')):
            deals[int(d['position_id'])].append(d)
        opens = [t['open_epoch'] for t in trades]
        boundaries = {int(t[k]) for t in trades for k in ('open_epoch','close_epoch')}
        marks, dropped, previous = defaultdict(list), Counter(), None
        first = last = None
        for m in csv.DictReader((path.parent/'equity.csv').open(encoding='utf-8-sig')):
            t = int(m['epoch'])
            if first is None:
                first = t
            last = t
            if not base.START <= t < base.END:
                continue
            # V3 exporter explicitly distinguishes post-test native liquidation.
            # Its cash/equity can be stamped with the last MARKET quote time;
            # it is not a contemporaneous floating observation for decisions.
            phase = m.get('phase')
            assert phase in (None,'','market_sample','finish_after_native_liquidation'), ('Unknown equity phase',phase)
            if phase == 'finish_after_native_liquidation':
                dropped['post_test_or_nonmarket_snapshot'] += 1
                continue
            assert previous is None or previous <= t
            if previous == t:
                dropped['duplicate'] += 1
                continue
            previous = t
            if t in boundaries:
                dropped['position_boundary'] += 1
                continue
            j = bisect_left(opens,t)-1
            if j >= 0 and trades[j]['open_epoch'] < t < trades[j]['close_epoch']:
                trade = trades[j]
                swap = float(m['open_swap'])/trade['volume'] if m.get('open_swap') else None
                marks[trade['position_id']].append([t,(float(m['equity'])-float(m['balance']))/trade['volume'],swap])
            else:
                assert abs(float(m['equity'])-float(m['balance'])) < .021, 'Unowned floating equity'
                dropped['flat'] += 1
        assert first <= base.START and last >= broker['symbols'][meta['symbol']]['quote_epoch']-600
        receipt_list = list(csv.DictReader((path.parent/'entry_risk.csv').open(encoding='utf-8-sig')))
        receipts = {int(r['position_id']):r for r in receipt_list}
        assert len(receipts) == len(receipt_list)
        selected = []
        for trade in trades:
            if not base.START <= trade['open_epoch'] < base.END:
                continue
            q = base.native_candidate(meta,trade,deals[trade['position_id']],marks[trade['position_id']])
            receipt = receipts[q['position_id']]
            assert receipt['calculation_ok'] == '1' and receipt['margin_ok'] == '1' and receipt['sl_source'] == 'entry_order'
            assert receipt['symbol'] == q['symbol']
            assert abs(float(receipt['entry_price'])-q['open_price']) < 1e-7
            assert abs(float(receipt['sl'])-q['sl']) < 1e-7
            assert abs(int(receipt['epoch'])-q['op']) <= 1
            assert float(receipt['unit_risk']) > 0
            q.update(unit_risk=float(receipt['unit_risk']),unit_risk_method='native_actual_fill_OrderCalcProfit',
                receipt_margin_one_lot=float(receipt['margin_one_lot']),source_mode='client_fixed50',
                source_fill_quote_bid=float(receipt['quote_bid']),source_fill_quote_ask=float(receipt['quote_ask']))
            selected.append(q)
        assert len(selected) == len(trades)
        candidates.extend(selected)
        coverage.append(dict(ea=meta['slug'],source=str(path),first_epoch=first,last_epoch=last,
            current_demo_final_quote_epoch=broker['symbols'][meta['symbol']]['quote_epoch'],candidates=len(selected),
            native=case['native'],discarded=dict(dropped),end_censored=sum(x['end_censored'] for x in selected),
            owned_marks=sum(len(x['marks']) for x in selected)))
        for name in ('results.json','deals.csv','equity.csv','entry_risk.csv','contracts.csv','coverage.csv'):
            p = path.parent/name
            hashes[str(p)] = base.sha(p)
    return dict(candidates=candidates,coverage=coverage),hashes


def freeze():
    assert not (ROOT/'RESULTS.json').exists(), 'Never refreeze after comparison outcomes'
    actual_freeze = base.read(ACTUAL/'FROZEN.json')
    ancestor = {**actual_freeze['files'],**actual_freeze['source_files']}
    assert all(base.sha(p)==h for p,h in ancestor.items())
    # Preserve each audit-only protocol/resume revision as an ancestor rather
    # than silently replacing failed exports or changing a frozen source run.
    native_freezes = [p for p in NATIVE.glob('*.json') if 'freeze' in p.name.lower() or 'frozen' in p.name.lower()]
    assert native_freezes
    for receipt in native_freezes:
        f = base.read(receipt)
        graph = {**f.get('files',{}),**f.get('source_files',{})}
        assert all(base.sha(p)==h for p,h in graph.items()), ('Native protocol changed',str(receipt))
        ancestor.update(graph)
        ancestor[str(receipt)] = base.sha(receipt)
    top, hashes = top5_inputs()
    manifest = base.read(OWNER/'manifest.json')
    assert [r['slug'] for r in manifest['entries']] == list(TOP5)
    assert next(r for r in manifest['entries'] if r['slug']=='nasdaq-5m-candle-momentum')['inputs']['InpRequireDIAgreement'] == 'false'
    for row in manifest['entries']:
        assert base.sha(PUBLIC/row['expert']) == row['ex5_sha256']
        hashes[str(PUBLIC/row['expert'])] = row['ex5_sha256']
    base.save(ROOT/'INPUTS.json',dict(top5=top,prop_ready=base.read(ORIGINAL/'INPUTS.json')))
    original_plan = base.read(ORIGINAL/'PLAN.json')
    plan = dict(window_utc=[base.iso(base.START),base.iso(base.END)],initial_balance=1000.,currency='USD',
        portfolios=dict(top5=list(TOP5),prop_ready=original_plan['priority']),scenarios=SCENARIOS,cost_sensitivities=[False,True],
        model='Immutable standalone native source-signal replay; not a simultaneous same-demo native portfolio backtest.',
        di_settings='Top5 Nasdaq DI OFF; Prop Ready Nasdaq and USDJPY DI ON, otherwise each package retains its own selected rules.',
        as_packaged='Top5 fixedUSD or currentBALANCE%, floor then MINIMUM LOT OVERRIDE, no shared loss/risk guards. PropReady fixedUSD/currentEQUITY% input constrained by existing source ceilings, $5 reference cap, shared/daily/reserve guards on1000.',
        common_research='Research-only truefixed50/5%currentEQUITY, STRICT minimum-lot skip for BOTH, same10%Praguedaily-loss pause /20%INITIAL floor and projectedbuffer,2Baggregate/1Bsymbol,125%risk+.50+negativeknownswap reserve,80%margin,7entries/3losers,3swait. Neither live package is changed to these rules.',
        research_guards=base.read(ACTUAL/'PLAN.json')['exposure'],
        source_account='Exness-MT5Trial16 cached historical source. Current Trial15 USD demo contract/margin metadata reused read-only.',
        costs=base.read(ACTUAL/'PLAN.json')['costs'],
        feed_caveat=base.read(ACTUAL/'PLAN.json')['feed_caveat'],
        expiry='Top5 historical tester bypasses licence dates by its existing tester design; licence is NOT renewed or disabled in delivery.',
        margin='Sum native source fill-time margin receipts; as-packaged Top5 admission checks estimated free margin only, no invented80%guard. Historical tiers, hedge discounts and broker liquidation path are not reconstructed.',
        limitations=base.read(ACTUAL/'PLAN.json')['limitations']+[
            'As-packaged returns are NOT equal-risk rankings: Top5 and PropReady have materially different caps, rounding and percent bases.',
            'If sampled capital exhaustion occurs, post-exhaustion history is not an executable account path. Margin level proxies are disclosed; broker stopout is not silently simulated.',
            'Only current delivered Top5 Nasdaq has default DI changed; no PropReady or global production EA modification.'],
        live_changes=False,local_package_default_change_only=True,optimization=False)
    base.save(ROOT/'PLAN.json',plan)
    files = {str(p):base.sha(p) for p in (ROOT/'compare.py',ROOT/'test_compare.py',ROOT/'PLAN.json',ROOT/'INPUTS.json',
        NATIVE/'native_cases.json',OWNER/'manifest.json',OWNER/'ClientGuard.mqh',ORIGINAL/'BROKER.json',ACTUAL/'RESULTS.json')}
    files.update(hashes)
    base.save(ROOT/'FROZEN.json',dict(files=files,source_files=ancestor,frozen_before_outcomes=True))
    print('Frozen two profiles, two policy views, two risks, two cost cases; no optimization.')


def run():
    frozen = base.read(ROOT/'FROZEN.json')
    assert all(base.sha(p)==h for p,h in {**frozen['files'],**frozen['source_files']}.items())
    plan, data, broker = base.read(ROOT/'PLAN.json'),base.read(ROOT/'INPUTS.json'),base.read(ORIGINAL/'BROKER.json')
    results = []
    for stress in (False,True):
        for scenario in SCENARIOS:
            if scenario['guard_policy']=='client':
                model = ClientReplay(scenario,broker,stress)
            elif scenario['guard_policy']=='current':
                model = base.Replay(scenario,broker,stress)
            else:
                model = engine.ResearchReplay(scenario,broker,stress)
            source = data[scenario['portfolio']]
            events = base.events_for(dict(priority=plan['portfolios'][scenario['portfolio']]),source)
            for t,kind,_,_,row,mark in events:
                if not base.START <= t < base.END:
                    continue
                if kind == 0:
                    model.observe(t)
                elif kind in (1,4):
                    model.closing(row,t)
                elif kind == 2:
                    model.mark(row,mark,t)
                else:
                    model.opening(row,t)
            result = model.result()
            result.update(portfolio=scenario['portfolio'],view=scenario['view'])
            assert len(result['decisions'])==len(source['candidates'])
            results.append(result)
            print(scenario['portfolio'],scenario['view'],scenario['id'],stress,result['metrics'],flush=True)
    base.save(ROOT/'RESULTS.json',dict(plan=plan,broker=broker,results=results,
        coverage={key:value['coverage'] for key,value in data.items()},
        frozen_sha256=base.sha(ROOT/'FROZEN.json'),generated_at_utc=base.iso(base.datetime.now(base.UTC).timestamp())))


if __name__=='__main__':
    {'freeze':freeze,'run':run}[sys.argv[1]]()
