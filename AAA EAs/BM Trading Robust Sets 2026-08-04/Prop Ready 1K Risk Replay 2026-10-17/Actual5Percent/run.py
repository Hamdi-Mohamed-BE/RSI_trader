"""Separately frozen genuine 5% sizing experiments. NEVER modifies live EAs.

The original study is immutable. These are linear historical signal replays, not
native simultaneous executions. Source sizing/guard ceilings are overridden ONLY
in the explicitly hypothetical research classes below.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
import importlib.util
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
spec = importlib.util.spec_from_file_location('original_frozen_1k_replay', PARENT/'replay.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
START, END = base.START, base.END
SCENARIOS = (
    dict(id='requested5_current_caps', label='5% input / current $5 ceiling', mode='percent', value=5., guard_policy='current'),
    dict(id='fixed50_old_guards', label='True fixed $50 / old remaining guards', mode='fixed', value=50., guard_policy='old'),
    dict(id='compound5_old_guards', label='True 5% equity / old remaining guards', mode='percent', value=5., guard_policy='old'),
    dict(id='fixed50', label='True fixed $50', mode='fixed', value=50., guard_policy='research_10daily_20total'),
    dict(id='compound5', label='True 5% current equity', mode='percent', value=5., guard_policy='research_10daily_20total'),
)


def true_lots(equity, unit, spec, scenario):
    if not all(math.isfinite(x) and x > 0 for x in (equity, unit)):
        return 0., 0.
    budget = scenario['value'] if scenario['mode'] == 'fixed' else equity*scenario['value']/100.
    lots = base.floor_lots(min(budget/unit, spec['volume_max']), spec['volume_step'])
    return (lots if lots >= spec['volume_min']-1e-9 else 0.), budget


class ResearchReplay(base.Replay):
    def __init__(self, scenario, broker, stress=False, reference=1000.):
        super().__init__(scenario, broker, stress, reference)
        self.aggressive = scenario['guard_policy'] == 'research_10daily_20total'
        self.flows = []
        self.first_breach_epoch = None
        self.paused_days = set()

    def budget(self):
        return self.scenario['value'] if self.scenario['mode'] == 'fixed' else self.equity*self.scenario['value']/100.

    def observe(self, t, record=True):
        if not self.aggressive:
            return super().observe(t, record)
        self.equity = self.balance+sum(p['mark_unit']*p['lots'] for p in self.active.values())
        current_day = base.day(t)
        if current_day != self.today:
            self.today = current_day
            self.anchor = self.balance
            self.daily_entries = self.daily_losses = 0
            self.day_stopped = False
            # Equity daily peak starts from the contemporaneous carried-past
            # mark, not day-start CASH when a position remains open overnight.
            self.day_peak = self.equity
            self.day_closed_peak = self.balance
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
        if self.equity <= self.reference*.80:
            self.breached = True
            if self.first_breach_epoch is None:
                self.first_breach_epoch = t
        if self.equity <= self.anchor*.90:
            self.day_stopped = True
            self.paused_days.add(current_day)
        if record:
            self.curve.append(dict(epoch=t, balance=self.balance, equity=self.equity))

    def reject(self, row, risk, margin):
        if not self.aggressive:
            return super().reject(row, risk, margin)
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
        if total+risk > 2*self.budget()+1e-7:
            return 'aggregate_risk'
        if same+risk > self.budget()+1e-7:
            return 'same_symbol_risk'
        reserve = sum(p['risk']*1.25+self.reference*.0005+max(0., -p['swap_unit']*p['lots']) for p in self.active.values())
        projected = min(self.equity, self.balance-reserve)-risk*1.25-self.reference*.0005
        if projected < self.reference*.80:
            return 'equity_buffer'
        if self.anchor-projected > self.anchor*.10:
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
        lots, budget = true_lots(self.equity, row['unit_risk'], spec, self.scenario)
        reason = None
        if any(p['row']['ea'] == row['ea'] for p in self.active.values()):
            reason = 'same_ea_exposure'
        elif lots <= 0:
            reason = 'minimum_lot_over_budget'
        risk = lots*row['unit_risk']
        margin = lots*base.margin_unit(row, spec)
        if reason is None:
            reason = self.reject(row, risk, margin)
        self.decisions.append(dict(id=row['id'], ea=row['ea'], epoch=t, equity=self.equity, budget=budget,
            source_volume_ceiling=None, source_sizing_override_research_only=True,
            volume=lots, stop_risk=risk, stop_risk_pct_equity=risk/self.equity*100. if self.equity > 0 else None,
            minimum_lot_risk=spec['volume_min']*row['unit_risk'], reason=reason or 'opened'))
        self.counts[reason or 'opened'] += 1
        self.per_ea[row['ea']][reason or 'opened'] += 1
        if reason:
            return
        assert risk <= budget+1e-7 and lots <= spec['volume_max']+1e-7
        cost = row['entry_unit_cost']*lots
        if self.stress:
            cost -= base.extra_cost_unit(row, spec, 'entry')*lots
        entry = round(cost, 2)
        self.balance = round(self.balance+entry, 2)
        self.flows.append(dict(epoch=t, cash=entry, id=row['id'], kind='entry'))
        self.active[row['id']] = dict(row=row, lots=lots, risk=risk, margin=margin,
            entry_cash=entry, mark_unit=0., swap_unit=0., mark_epoch=None)
        self.daily_entries += 1
        self.last_entry = t
        self.observe(t)

    def closing(self, row, t):
        was_active = row['id'] in self.active
        super().closing(row, t)
        if was_active:
            self.flows.append(dict(epoch=t, cash=self.trades[-1]['exit_cash'], id=row['id'], kind='exit'))

    def result(self):
        result = super().result()
        # Parent's closed-trade-only calendar is unsuitable for paid fees on
        # positions still open at the horizon. Rebuild from actual cash events.
        daily, months, sharpe = cash_calendar(self.flows, self.reference)
        assert abs(daily[-1]['ending_balance']-self.balance) < 1e-7
        result.update(daily=daily, months=months, cash_flows=self.flows,
            open_positions=[dict(id=p['row']['id'], ea=p['row']['ea'], op=p['row']['op'], lots=p['lots'],
                initial_risk=p['risk'], paid_entry_cash=p['entry_cash'], mark_epoch=p['mark_epoch'],
                mark_unit=p['mark_unit'], sampled_floating=p['mark_unit']*p['lots']) for p in self.active.values()])
        result['metrics'].update(daily_closed_return_sharpe=sharpe,
            cash_profit=round(self.balance-self.reference, 2),
            unrealized_sampled_profit=self.equity-self.balance,
            first_breach_epoch=self.first_breach_epoch, paused_days=sorted(self.paused_days))
        return result


def cash_calendar(flows, initial):
    per_day = defaultdict(float)
    for f in flows:
        per_day[base.iso(f['epoch'])[:10]] += f['cash']
    rows, rates, balance = [], [], initial
    for t in range(START, END, 86400):
        label = base.iso(t)[:10]
        value, opening = round(per_day[label], 2), balance
        balance = round(balance+value, 2)
        rates.append(value/opening if opening > 0 else 0.)
        rows.append(dict(date=label, opening_balance=opening, net_profit=value, ending_balance=balance))
    months = []
    for label in dict.fromkeys(r['date'][:7] for r in rows):
        ds = [r for r in rows if r['date'].startswith(label)]
        months.append(dict(month=label, first_date=ds[0]['date'], last_date=ds[-1]['date'],
            opening_balance=ds[0]['opening_balance'], ending_balance=ds[-1]['ending_balance'],
            net_profit=round(sum(r['net_profit'] for r in ds), 2),
            return_pct=(ds[-1]['ending_balance']/ds[0]['opening_balance']-1)*100.))
    sharpe = statistics.mean(rates)/statistics.stdev(rates)*math.sqrt(365) if statistics.stdev(rates) > 0 else None
    return rows, months, sharpe


def freeze():
    assert not (ROOT/'RESULTS.json').exists(), 'Never refreeze after outcomes'
    original = base.read(PARENT/'FROZEN.json')
    assert all(base.sha(p) == h for p, h in original['files'].items())
    plan = dict(window_utc=[base.iso(START), base.iso(END)], initial_balance=1000., currency='USD',
        user_request='Actual 5% base risk then compound, not the original capped5%input. No preferred loss limits given; stated research defaults used.',
        scenarios=SCENARIOS, stress_scenarios=[False, True],
        actual_sizing='Fixed50 OR5%current sampled equity; floor to brokerlotstep; reject below minimum; no initial5USDcap or originalsource volume ceiling in RESEARCH ONLY.',
        guards='Aggressive research: pauseNEWentries at10%lossfromPragueday-startCASH; permanententryhalt at20%lossfrominitial1000. Soft projected/reservedrisk must also stayabove800 and within10%dayanchor.',
        exposure='Totalretainedinitialrisk<=2timescurrentrequestedbudget; samesymbol<=1timesbudget. Existingrisknotreleasedbyprofitabletrail. Reserve1.25risk+negativeknownopenswap+0.50perposition. Margin80%protectedEq. 7entries/3netlosers/day;3s wait.',
        no_liquidation=True, default_live_profile_changed=False, new_strategy_search=False,
        controls='Current5%INPUTstill$5cap; actualfixed50/5%witholdremainingportfolioadmissionguards.',
        compounding='5%ofcurrentpast-onlysampledequity BEFORE entryfees; includesknownfloating, but reservedriskprojectedbalance prevents assumingunrealizedprofitfinancesfreshpositions.',
        costs=base.read(PARENT/'PLAN.json')['costs'], feed_caveat=base.read(PARENT/'PLAN.json')['feed_caveat'],
        limitations=base.read(PARENT/'PLAN.json')['limitations']+[
            'Higher volumes are linear resizes of existing standalone fills; liquidity/commission tiers and unseen signals after rejected source trades are not reconstructed.',
            'Five-minute sampled DD and admission stops do not guarantee the20%/10%loss limits against gaps or intrabar moves.',
            'An end-censored position remains open; its entry fee is cash, final sampled floating is unrealized, and its artificial native liquidation is never booked.',
            'Risk and drawdown limits are hypotheses, not a live recommendation or a pass-probability estimate.'])
    base.save(ROOT/'PLAN.json', plan)
    files = {str(ROOT/'run.py'): base.sha(ROOT/'run.py'), str(ROOT/'PLAN.json'): base.sha(ROOT/'PLAN.json'),
        str(ROOT/'test_run.py'): base.sha(ROOT/'test_run.py')}
    for p in (PARENT/'FROZEN.json', PARENT/'PLAN.json', PARENT/'INPUTS.json', PARENT/'BROKER.json', PARENT/'replay.py'):
        files[str(p)] = base.sha(p)
    base.save(ROOT/'FROZEN.json', dict(files=files, source_files=original['files'], frozen_before_new_outcomes=True))
    print('Frozen genuine5% research scenarios; original study and live profile untouched.')


def run():
    frozen = base.read(ROOT/'FROZEN.json')
    assert all(base.sha(p) == h for p, h in {**frozen['files'], **frozen['source_files']}.items())
    original_plan, data, broker = base.read(PARENT/'PLAN.json'), base.read(PARENT/'INPUTS.json'), base.read(PARENT/'BROKER.json')
    events = base.events_for(original_plan, data)
    results = []
    for stress in (False, True):
        for scenario in SCENARIOS:
            model = base.Replay(scenario, broker, stress) if scenario['guard_policy'] == 'current' else ResearchReplay(scenario, broker, stress)
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
            print(scenario['id'], stress, result['metrics'], flush=True)
    base.save(ROOT/'RESULTS.json', dict(plan=base.read(ROOT/'PLAN.json'), broker=broker,
        results=results, coverage=data['coverage'], frozen_sha256=base.sha(ROOT/'FROZEN.json'), original_study_unchanged=True))


if __name__ == '__main__':
    {'freeze': freeze, 'run': run}[sys.argv[1]]()
