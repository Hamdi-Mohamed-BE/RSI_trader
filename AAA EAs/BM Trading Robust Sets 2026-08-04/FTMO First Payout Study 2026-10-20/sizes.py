"""Account-size extension of the first-payout study (PLAN.md addendum). Same package model; every guard / FTMO cash
limit scaled by k = size / 10,000 as CalyxFTMOGuard.mqh does; EA request stays 1% of equity; lot step / minimum /
maximum unchanged. k = 1 must reproduce RESULTS.json (DI OFF) exactly.

python sizes.py freeze | run <size> | table
"""
import bisect, hashlib, importlib.util, json, math, random, statistics, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


P = load('payout', R / 'run.py'); T, D, E = P.T, P.D, P.E
SIZES = (10000, 20000, 25000, 50000, 100000)
FEES = json.loads(P.RULES.read_text(encoding='utf-8'))['fees']


def lots_scaled(equity, unit, spec, cap_cash):
    """DialTrial.lots_for_cap with the EA request fixed at 1% of equity and the guard cap in cash (k=1: identical)."""
    if not math.isfinite(equity) or not math.isfinite(unit) or equity <= 0 or unit <= 0: return 0., 0.
    raw = equity * 0.01 / unit
    requested = math.ceil((min(raw, spec['maximum']) - 1e-12) / spec['step']) * spec['step']
    requested = min(spec['maximum'], max(spec['minimum'], requested))
    guarded = E.floor_lot(min(requested, cap_cash / unit, spec['maximum']), spec['step'])
    return (guarded if guarded >= spec['minimum'] - 1e-9 else 0.), requested


class ScaledChallenge(D.DialTrial):
    def __init__(self, plan, portfolio, start, cost, handover, bands, k):
        super().__init__(plan, portfolio, start, cost, handover, bands)
        self.k = k; self.C = 10000.0 * k
        self.balance = self.anchor = self.eq = self.peak = self.closed_peak = self.C; self.cap_now = P.CAP * k

    def cap(self): return P.CAP * self.k

    def observe(self, t):  # engine Trial.observe with 9000 / 500 / 300 scaled
        k = self.k
        self.eq = self.equity(t); self.peak = max(self.peak, self.eq); self.closed_peak = max(self.closed_peak, self.balance)
        self.max_dd = max(self.max_dd, self.peak - self.eq); self.max_closed_dd = max(self.max_closed_dd, self.closed_peak - self.balance)
        self.max_daily_loss = max(self.max_daily_loss, self.anchor - self.eq)
        self.max_risk = max(self.max_risk, sum(p['risk'] for p in self.active.values())); self.max_margin = max(self.max_margin, sum(p['margin'] for p in self.active.values()))
        self.mark_observations += len(self.active)
        for p in self.active.values():
            if p['mark_epoch'] is None: self.zero_mark_observations += 1; self.max_first_mark_lag = max(self.max_first_mark_lag, t - p['row']['op'])
            else:
                age = max(0, t - p['mark_epoch']); self.max_mark_age = max(self.max_mark_age, age); self.stale_mark_observations += age > 900
        if self.failed or self.finished or self.current()['status'] != 'pending': return
        if self.eq <= 9000.0 * k + 1e-8 or self.eq <= self.anchor - 500.0 * k + 1e-8:
            self.exact_floor_touches += abs(self.eq - 9000 * k) <= 1e-8 or abs(self.eq - (self.anchor - 500 * k)) <= 1e-8
            p = self.current(); p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor,
                                         hard_failure_kind='static' if self.eq <= 9000 * k + 1e-8 else 'daily')
            self.failed = True; self.counts['hard_' + p['hard_failure_kind'] + '_failure'] += 1
        elif self.eq <= self.anchor - 300.0 * k + 1e-8:
            if not self.day_stopped: self.counts['daily_300_latches'] += 1
            self.day_stopped = True

    def target(self): return (11000 if self.phase == 1 else 10500) * self.k

    def maybe_pass(self, t):
        if self.failed or self.finished or self.current()['status'] != 'pending': return
        if self.balance >= self.target() - 1e-8 and len(self.days) >= 4 and not self.active:
            p = self.current(); p.update(status='passed', pass_epoch=t, entry_days=sorted(self.days), terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor)
            if self.phase == 1: self.ready = E.phase2_ready(t, self.handover)
            else: self.finished = True

    def activate(self, t):
        if self.phase == 1 and self.phases[1]['status'] == 'passed' and self.ready is not None and t >= self.ready and t < self.start['horizon_epoch']:
            assert not self.active
            self.phase = 2; self.phases[2] = E.new_phase(self.ready); self.balance = self.anchor = self.eq = self.C; self.days = set()
            self.daily_entries = self.daily_losses = 0; self.day_stopped = False; self.last_entry = -math.inf; self.peak = self.closed_peak = self.C

    def limits(self, row, t, risk, margin):
        k = self.k; m = self.cap_now / (50 * k)
        if self.day_stopped: return 'daily_300_latch'
        if self.daily_entries >= 7: return 'daily_7_entry_limit'
        if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
        total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
        if total + risk > 225 * m * k + 1e-7: return 'aggregate_initial_risk225'
        if same + risk > 150 * m * k + 1e-7: return 'same_symbol_initial_risk150'
        reserve = sum(1.25 * p['risk'] + 5 * k for p in self.active.values())
        projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5 * k
        if projected < 9200 * k - 1e-8: return 'soft_total_buffer9200'
        if self.anchor - projected > 300 * k + 1e-8: return 'soft_daily_reserve300'
        existing = sum(p['margin'] for p in self.active.values())
        if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
        if t < self.last_entry + 3: return 'entry_reconciliation3s'
        return None

    def reject_reason(self, row, t, risk, margin):
        if self.failed: return 'permanent_hard_failure'
        if self.finished: return 'both_phases_completed'
        if self.current()['status'] != 'pending': return 'phase_review_wait'
        if self.day_stopped: return 'daily_300_latch'
        if self.balance >= self.target() - 1e-8 and len(self.days) >= 4: return 'target_entry_gate_await_flat'
        return self.limits(row, t, risk, margin)

    def opening(self, row, t):  # DialTrial.opening with lots_scaled
        self.observe(t); self.maybe_pass(t)
        if row['ea'] not in self.plan['baskets'][self.portfolio]: return
        if row['op'] < self.start['epoch']: return
        if any(p['row']['ea'] == row['ea'] for p in self.active.values()): self.counts['same_ea_exposure'] += 1; return
        self.cap_now = self.cap()
        spec = self.specs[row['symbol']]; lot, requested = lots_scaled(self.eq, row['unit_risk'], spec, self.cap_now)
        if lot <= 0: self.counts['minimum_lot_over50_or_source_request'] += 1; return
        risk = lot * row['unit_risk']; margin = lot * E.margin_per_lot(row, spec); reason = self.reject_reason(row, t, risk, margin)
        if reason: self.counts[reason] += 1; return
        assert risk <= self.cap_now + 1e-7 and lot <= requested + 1e-8
        self.counts[f'cap_{self.cap_now:g}'] += 1
        fee = row['entry_unit_cost'] * lot - (E.stress_per_lot(row, 'entry') * lot if self.cost == 'fixed_cost_stress' else 0.)
        fee = round(fee, 2); self.balance = round(self.balance + fee, 2)
        self.active[row['id']] = dict(row=row, lots=lot, requested_lots=requested, risk=risk, margin=margin, mark_unit=0., mark_epoch=None, entry_cash=fee, phase=self.phase)
        self.last_entry = t; self.daily_entries += 1; self.days.add(str(E.day_of(t))); p = self.current(); p['entries'] += 1; p['entry_days'] = sorted(self.days)
        if p['first_trade_epoch'] is None: p['first_trade_epoch'] = t
        self.counts['opened'] += 1; self.observe(t)


class ScaledFunded(ScaledChallenge):
    def __init__(self, plan, start, cost, k):
        super().__init__(plan, D.BASKET, start, cost, 'next_prague_midnight', [(-1e9, P.CAP)], k); self.paid = {}

    def maybe_pass(self, t): return

    def reject_reason(self, row, t, risk, margin):
        if self.failed: return 'permanent_hard_failure'
        return self.limits(row, t, risk, margin)

    def check(self, t):
        if self.failed or self.active: return
        first = self.current()['first_trade_epoch']
        if first is None or t < P.midnight(E.day_of(first) + timedelta(days=P.FIRST_AFTER)) - 1e-6: return
        profit = round(self.balance - self.C, 2)
        for th in P.THRESHOLDS:
            need = th if th == 20 else th * self.k
            if th not in self.paid and profit >= need - 1e-9: self.paid[th] = dict(epoch=t, profit=profit, trades=len(self.trades))

    def closing(self, row, t): super().closing(row, t); self.check(t)
    def day_reset(self, t): super().day_reset(t); self.check(t)


def replay_k(plan, start, cost, handover, events, k):
    return P.drive(ScaledChallenge(plan, D.BASKET, start, cost, handover, [(-1e9, P.CAP)], k), events).result()


def funded_run_k(plan, ev, d, cost, k):
    s = P.start_dict(d, P.HORIZON); m = P.drive(ScaledFunded(plan, s, cost, k), ev); res = m.result()
    fail = m.phases[1]['fail_epoch']; first = m.phases[1]['first_trade_epoch']
    stuck = (not m.failed and 20 not in m.paid and m.counts.get('soft_total_buffer9200', 0) > 0 and s['horizon_epoch'] - m.last_entry > 30 * 86400)
    paid = {th: dict(day=(E.day_of(v['epoch']) - d).days + 1, profit=v['profit'], payout=round(P.SPLIT * v['profit'], 2), trades=v['trades'], epoch=v['epoch'])
            for th, v in m.paid.items()}
    return dict(start=d.isoformat(), paid=paid, failed=m.failed, fail_day=None if fail is None else (E.day_of(fail) - d).days + 1,
                first_trade_day=None if first is None else (E.day_of(first) - d).days + 1, stuck=stuck, trades=len(res['trades']),
                ending_equity=round(res['ending_sampled_equity'], 2), eqdd=round(res['max_sampled_equity_drawdown_cash'], 1),
                skipped_min_lot=res['counts'].get('minimum_lot_over50_or_source_request', 0))


def e2e_one_k(plan, ch_ev, fund_events_for, s, cost, handover, k):
    trial = replay_k(plan, P.start_dict(s, P.HORIZON), cost, handover, ch_ev, k)
    fd = P.access_start(trial); row = dict(start=s.isoformat(), challenge_trades=len(trial['trades']), funded_day=None, funded=None, total_days={})
    if fd is None:
        row['outcome'] = 'challenge_breach' if trial['outcome'].startswith('failed') else 'challenge_not_done_180d'; return row
    row['funded_day'] = (fd - s).days + 1
    f = funded_run_k(plan, fund_events_for(fd), fd, cost, k); row['funded'] = f
    for th, p in f['paid'].items(): row['total_days'][str(th)] = (fd - s).days + p['day']
    row['outcome'] = 'paid' if 20 in f['paid'] else ('funded_breach_before_payout' if f['failed'] else ('funded_stuck_buffer' if f['stuck'] else 'funded_no_payout_180d'))
    return row


def mean(v): return round(statistics.fmean(v), 1) if v else None


def funded_means(rows):
    out = {}
    for th in (20, 500):
        paid = [r['paid'][th] for r in rows if th in r['paid']]
        out[str(th)] = dict(mean_day=mean([p['day'] for p in paid]), mean_payout=mean([p['payout'] for p in paid]))
    out['skipped_min_lot_median'] = statistics.median(r['skipped_min_lot'] for r in rows); return out


def e2e_means(rows):
    fund = [r['funded_day'] for r in rows if r['funded_day']]
    out = dict(mean_funded_access_day=mean(fund))
    for th in (20, 500):
        paid = [r for r in rows if r['outcome'] == 'paid' and th in r['funded']['paid']]
        out[str(th)] = dict(mean_total_day=mean([r['total_days'][str(th)] for r in paid]), mean_payout=mean([r['funded']['paid'][th]['payout'] for r in paid]))
    return out


def freeze():
    main = json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files']
    plan_text = (R / 'PLAN.md').read_bytes(); prefix = plan_text.split(b'\n## Addendum')[0]
    assert hashlib.sha256(prefix).hexdigest() == main[str(R / 'PLAN.md')], 'PLAN.md body changed (only the addendum may be new)'
    files = [Path(__file__), R / 'run.py', R / 'PLAN.md'] + [Path(p) for p in main if Path(p).name != 'PLAN.md']
    (R / 'FROZEN-SIZES.json').write_text(json.dumps(dict(frozen_at=datetime.now(P.Z).isoformat(), plan_body_sha256_matches_main_freeze=True,
                                                         files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def run(size):
    for p, h in json.loads((R / 'FROZEN-SIZES.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    E.verify_freeze(); k = size / 10000; began = time.time(); name = 'DI_OFF'
    split = load('data_split', P.SPLIT_PY).research_split(P.DATA_START, P.DATA_END)
    wins = {w: (date.fromisoformat(split[w]['start']), date.fromisoformat(split[w]['end_exclusive'])) for w in ('development', 'validation', 'oos')}
    wins['all'] = (P.DATA_START, P.DATA_END)
    data = json.loads((P.RT / f'INPUTS-{name}.json').read_text(encoding='utf-8'))
    plan = T.splan_for(data['window']); events = E.master_events(plan, data); epochs = [x[0] for x in events]
    out = dict(size=size, k=k, fee_eur=FEES.get(str(size)), funded={}, funded_mc={}, e2e={}, e2e_mc={}, means={})
    for cost in ('recorded_exness', 'fixed_cost_stress'):
        rows = []; d = P.DATA_START
        while d + timedelta(days=P.HORIZON) <= P.DATA_END:
            if d.weekday() < 5: rows.append(funded_run_k(plan, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=P.HORIZON))), d, cost, k))
            d += timedelta(days=1)
        for w, (a, b) in wins.items():
            sel = [r for r in rows if a <= date.fromisoformat(r['start']) and date.fromisoformat(r['start']) + timedelta(days=P.HORIZON) <= b]
            out['funded'][f'{cost}|{w}'] = P.summarize_funded(sel); out['means'][f'funded|{cost}|{w}'] = funded_means(sel)
        print(size, 'funded', cost, json.dumps(out['funded'][f'{cost}|all']['20']), f'{time.time() - began:.0f}s', flush=True)
    for sc, (cost, handover) in P.SCEN.items():
        rows = []; d = P.DATA_START
        while d <= P.E2E_LAST_START:
            if d.weekday() < 5:
                ch = P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=P.HORIZON)))
                rows.append(e2e_one_k(plan, ch, lambda fd: P.window(events, epochs, P.midnight(fd), P.midnight(fd + timedelta(days=P.HORIZON))), d, cost, handover, k))
            d += timedelta(days=1)
        for w, (a, b) in wins.items():
            sel = [r for r in rows if a <= date.fromisoformat(r['start']) < b]
            if sel: out['e2e'][f'{sc}|{w}_starts'] = P.summarize_e2e(sel); out['means'][f'e2e|{sc}|{w}_starts'] = e2e_means(sel)
        print(size, 'e2e', sc, json.dumps(out['e2e'][f'{sc}|all_starts']['20']), f'{time.time() - began:.0f}s', flush=True)
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m_ = [], date(2021, 10, 11)
    while m_ + timedelta(days=T.BLOCK_DAYS) <= P.DATA_END: mondays.append(m_); m_ += timedelta(days=7)
    index = {m_: (bisect.bisect_left(ops, P.midnight(m_)), bisect.bisect_left(ops, P.midnight(m_ + timedelta(days=T.BLOCK_DAYS)))) for m_ in mondays}
    sd = date(2030, 1, 7); rng = random.Random(P.SEED); fr = {c: [] for c in ('recorded_exness', 'fixed_cost_stress')}
    for i in range(P.PATHS):
        ev = T.bootstrap_events(pool, mondays, index, rng, sd, priority)
        for c in fr: fr[c].append(funded_run_k(plan, ev, sd, c, k))
    for c, v in fr.items(): out['funded_mc'][c] = P.summarize_funded(v); out['means'][f'funded_mc|{c}'] = funded_means(v)
    print(size, 'funded MC', json.dumps(out['funded_mc']['recorded_exness']['20']), f'{time.time() - began:.0f}s', flush=True)
    rng = random.Random(P.E2E_SEED); er = {sc: [] for sc in P.SCEN}
    for i in range(P.PATHS):
        ev = P.path_events(pool, mondays, index, rng, sd, priority, P.E2E_BLOCKS); ee = [x[0] for x in ev]
        ch = P.window(ev, ee, P.midnight(sd), P.midnight(sd + timedelta(days=P.HORIZON)))
        for sc, (cost, handover) in P.SCEN.items():
            er[sc].append(e2e_one_k(plan, ch, lambda fd: P.window(ev, ee, P.midnight(fd), P.midnight(fd + timedelta(days=P.HORIZON))), sd, cost, handover, k))
    for sc, v in er.items(): out['e2e_mc'][sc] = P.summarize_e2e(v); out['means'][f'e2e_mc|{sc}'] = e2e_means(v)
    print(size, 'e2e MC', json.dumps(out['e2e_mc']['base']['20']), f'{time.time() - began:.0f}s', flush=True)
    if size == 10000:  # parity gate against the main 10k run
        ref = json.loads((R / 'RESULTS.json').read_text(encoding='utf-8'))
        for key, v in out['funded'].items(): assert v == ref['funded'][f'{name}|{key}'], ('funded parity', key)
        for key, v in out['funded_mc'].items(): assert v == ref['funded_mc'][f'{name}|{key}'], ('funded MC parity', key)
        for key, v in out['e2e'].items(): assert v == ref['e2e'][f'{name}|{key}'], ('e2e parity', key)
        for key, v in out['e2e_mc'].items(): assert v == ref['e2e_mc'][f'{name}|{key}'], ('e2e MC parity', key)
        out['parity_vs_main_10k'] = 'exact match: funded, funded MC, e2e, e2e MC'; print('10k parity exact', flush=True)
    out['seconds'] = round(time.time() - began)
    (R / f'RESULTS-SIZE-{size}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(size, 'done', out['seconds'], 's')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'freeze': freeze()
    elif cmd == 'run': run(int(sys.argv[2]))
