"""FTMO dial study: size by room to the static floor on the Prop Ready nine-EA basket.

Reuses the FTMO Faster Portfolio Screen 2026-10-16 engine, PLAN and INPUTS unchanged (hash-checked); only the per-entry
risk cap is replaced by a subclass. FLAT50 must reproduce the source trial records exactly before any dial result is
trusted. No MT5, trading, API, BAT, SET or guard change.

python run.py freeze | run
"""
import bisect, gzip, hashlib, importlib.util, json, math, statistics, sys, time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PLAN = json.loads((ROOT / 'PLAN.json').read_text(encoding='utf-8'))
SRC = Path(PLAN['source_study'])
spec = importlib.util.spec_from_file_location('faster_core', SRC / 'core_engine.py')
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
BASKET = PLAN['basket']
Z = ZoneInfo('Europe/Prague')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lots_for_cap(equity, unit, spec, cap):
    if not math.isfinite(equity) or not math.isfinite(unit) or equity <= 0 or unit <= 0:
        return 0., 0.
    raw = equity * (cap / 10000) / unit
    requested = math.ceil((min(raw, spec['maximum']) - 1e-12) / spec['step']) * spec['step']
    requested = min(spec['maximum'], max(spec['minimum'], requested))
    guarded = e.floor_lot(min(requested, cap / unit, spec['maximum']), spec['step'])
    return (guarded if guarded >= spec['minimum'] - 1e-9 else 0.), requested


class DialTrial(e.Trial):
    def __init__(self, plan, portfolio, start, cost, handover, bands):
        super().__init__(plan, portfolio, start, cost, handover)
        self.bands = bands; self.cap_now = bands[-1][1]

    def cap(self):
        room = (self.eq - 9000.0) / 1000.0
        for threshold, cap in self.bands:
            if room >= threshold:
                return cap
        return self.bands[-1][1]

    def reject_reason(self, row, t, risk, margin):
        m = self.cap_now / 50
        if self.failed: return 'permanent_hard_failure'
        if self.finished: return 'both_phases_completed'
        if self.current()['status'] != 'pending': return 'phase_review_wait'
        if self.day_stopped: return 'daily_300_latch'
        if self.balance >= (11000 if self.phase == 1 else 10500) - 1e-8 and len(self.days) >= 4: return 'target_entry_gate_await_flat'
        if self.daily_entries >= 7: return 'daily_7_entry_limit'
        if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
        total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
        if total + risk > 225 * m + 1e-7: return 'aggregate_initial_risk225'
        if same + risk > 150 * m + 1e-7: return 'same_symbol_initial_risk150'
        reserve = sum(1.25 * p['risk'] + 5 for p in self.active.values())
        projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5
        if projected < 9200 - 1e-8: return 'soft_total_buffer9200'
        if self.anchor - projected > 300 + 1e-8: return 'soft_daily_reserve300'
        existing = sum(p['margin'] for p in self.active.values())
        if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
        if t < self.last_entry + 3: return 'entry_reconciliation3s'
        return None

    def opening(self, row, t):
        self.observe(t); self.maybe_pass(t)
        if row['ea'] not in self.plan['baskets'][self.portfolio]: return
        if row['op'] < self.start['epoch']: return
        if any(p['row']['ea'] == row['ea'] for p in self.active.values()): self.counts['same_ea_exposure'] += 1; return
        self.cap_now = self.cap()
        spec = self.specs[row['symbol']]; lot, requested = lots_for_cap(self.eq, row['unit_risk'], spec, self.cap_now)
        if lot <= 0: self.counts['minimum_lot_over50_or_source_request'] += 1; return
        risk = lot * row['unit_risk']; margin = lot * e.margin_per_lot(row, spec); reason = self.reject_reason(row, t, risk, margin)
        if reason: self.counts[reason] += 1; return
        assert risk <= self.cap_now + 1e-7 and lot <= requested + 1e-8
        self.counts[f'cap_{self.cap_now:g}'] += 1
        fee = row['entry_unit_cost'] * lot - (e.stress_per_lot(row, 'entry') * lot if self.cost == 'fixed_cost_stress' else 0.)
        fee = round(fee, 2); self.balance = round(self.balance + fee, 2)
        self.active[row['id']] = dict(row=row, lots=lot, requested_lots=requested, risk=risk, margin=margin, mark_unit=0., mark_epoch=None, entry_cash=fee, phase=self.phase)
        self.last_entry = t; self.daily_entries += 1; self.days.add(str(e.day_of(t))); p = self.current(); p['entries'] += 1; p['entry_days'] = sorted(self.days)
        if p['first_trade_epoch'] is None: p['first_trade_epoch'] = t
        self.counts['opened'] += 1; self.observe(t)


def replay(plan, start, cost, handover, events, bands):
    model = DialTrial(plan, BASKET, start, cost, handover, bands)
    for t, kind, priority, key, row, mark in events:
        if kind == 0: model.day_reset(t)
        elif kind in (1, 4): model.closing(row, t)
        elif kind == 2: model.mark(row, mark, t)
        else: model.opening(row, t)
    return model.result()


def freeze():
    files = {str(p): sha(p) for p in (ROOT / 'PLAN.json', Path(__file__), SRC / 'core_engine.py', SRC / 'PLAN.json', SRC / 'INPUTS.json', SRC / 'FROZEN.json')}
    (ROOT / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files=files), indent=1), encoding='utf-8')
    print('frozen', len(files), 'files')


def funded_days(t):
    a = t.get('access_5bd_illustration_epoch')
    return None if not a else (datetime.fromtimestamp(a, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1


def summarize(trials):
    n = len(trials)
    both = sorted(t['total_elapsed_to_both']['inclusive_prague_days'] for t in trials if t['total_elapsed_to_both'])
    fund = sorted(d for d in (funded_days(t) for t in trials) if d)
    p1 = [t['phase1']['elapsed_to_terminal']['inclusive_prague_days'] for t in trials if t['phase1']['status'] == 'passed']
    share = lambda arr, d: round(sum(x <= d for x in arr) / n, 4) if n else None  # noqa: E731
    return dict(starts=n, outcomes=dict(Counter(t['outcome'] for t in trials)), both_completed=len(both),
                both_completion_share=round(len(both) / n, 4) if n else None,
                median_days_both=statistics.median(both) if both else None,
                p25_days_both=both[len(both) // 4] if both else None, p75_days_both=both[(3 * len(both)) // 4] if both else None,
                median_days_funded_plus5bd=statistics.median(fund) if fund else None,
                both_within={str(d): share(both, d) for d in (60, 90, 120, 150)},
                phase1_within_60=share(p1, 60), phase1_median=statistics.median(p1) if p1 else None,
                hard_failures=sum(t['outcome'].startswith('failed') for t in trials),
                pending_at_horizon=sum(t['outcome'].startswith('pending') or t['outcome'] == 'phase2_not_started_wait' for t in trials),
                soft_buffer_blocked_trials=sum(t['counts'].get('soft_total_buffer9200', 0) > 0 for t in trials),
                worst_sampled_equity_dd=round(max(t['max_sampled_equity_drawdown_cash'] for t in trials), 2),
                worst_daily_sampled_loss=round(max(t['max_daily_sampled_equity_loss'] for t in trials), 2),
                max_initial_open_risk=round(max(t['max_initial_open_risk'] for t in trials), 2),
                median_trades=statistics.median(len(t['trades']) for t in trials))


def run():
    frozen = json.loads((ROOT / 'FROZEN.json').read_text(encoding='utf-8'))
    for p, h in frozen['files'].items():
        assert sha(p) == h, f'Changed after freeze: {p}'
    e.verify_freeze()
    splan = e.read(SRC / 'PLAN.json'); data = e.read(SRC / 'INPUTS.json')
    members = set(splan['baskets'][BASKET]); universe = set(splan['baskets']['CORE4']) | members
    events = e.master_events(splan, dict(data, candidates=[x for x in data['candidates'] if x['ea'] in universe]))
    epochs = [x[0] for x in events]
    print('loading source outcomes for parity...', flush=True)
    prior = {(t['start_date'], t['cost'], t['handover']): t for t in e.read(SRC / 'OUTCOMES.json')['trials'] if t['portfolio'] == BASKET}
    began = time.time(); trials = []; parity = 0
    for name, pol in PLAN['policies'].items():
        bands = [tuple(b) for b in pol['bands']]
        for start in data['starts']:
            window = events[bisect.bisect_left(epochs, start['epoch']):bisect.bisect_left(epochs, start['horizon_epoch'])]
            for sc in splan['scenarios']:
                row = replay(splan, start, sc['cost'], sc['handover'], window, bands)
                if name == 'FLAT50':
                    ref = prior[(start['date'], sc['cost'], sc['handover'])]
                    cmp = dict(row); cmp['counts'] = {k: v for k, v in row['counts'].items() if not k.startswith('cap_')}
                    assert cmp == ref, ('FLAT50 parity failure', start['date'], sc)
                    parity += 1
                row['policy'] = name; trials.append(row)
        print(f'{name} done ({time.time() - began:.0f}s)', flush=True)
    assert parity == 134 * 4, parity
    summary = []
    for name in PLAN['policies']:
        for sc in splan['scenarios']:
            sub = [t for t in trials if t['policy'] == name and t['cost'] == sc['cost'] and t['handover'] == sc['handover']]
            summary.append(dict(policy=name, **sc, all_starts=summarize(sub), jan2026_plus=summarize([t for t in sub if t['start_date'] >= '2026-01-01'])))
    sel = []
    for name in PLAN['policies']:
        rows = [s for s in summary if s['policy'] == name]
        eligible = all(s['all_starts']['hard_failures'] == 0 and s['all_starts']['both_completed'] >= 128 and s['jan2026_plus']['both_completed'] >= 68 for s in rows)
        sel.append(dict(policy=name, eligible=eligible,
                        worst_median_days_both=max(s['all_starts']['median_days_both'] or 1e9 for s in rows),
                        worst_within_90=min(s['all_starts']['both_within']['90'] for s in rows),
                        max_cap=max(b[1] for b in PLAN['policies'][name]['bands'])))
    sel.sort(key=lambda x: (not x['eligible'], x['worst_median_days_both'], -x['worst_within_90'], x['max_cap']))
    (ROOT / 'OUTCOMES.json.gz').write_bytes(gzip.compress(json.dumps(dict(trials=trials)).encode(), 6, mtime=0))
    (ROOT / 'SUMMARY.json').write_text(json.dumps(dict(plan_sha256=sha(ROOT / 'PLAN.json'), engine_source_sha256=sha(SRC / 'core_engine.py'),
                                                         flat50_parity_trials=parity, seconds=round(time.time() - began, 1),
                                                         selection=sel, best_eligible=next((x['policy'] for x in sel if x['eligible']), None),
                                                         summary=summary), indent=1), encoding='utf-8')
    print(json.dumps(sel, indent=1))


if __name__ == '__main__':
    {'freeze': freeze, 'run': run}[sys.argv[1]]()
