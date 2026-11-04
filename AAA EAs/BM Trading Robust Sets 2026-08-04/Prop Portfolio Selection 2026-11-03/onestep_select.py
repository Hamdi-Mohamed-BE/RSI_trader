"""Owner 2026-11-03: "what is median days to get funded on the two phases and 1 phase? ... and pass rate?" One-step version of the
prop_select challenge stage: same frozen compare.py / sizes.py engine, streams, weekday starts, MC pool and seed; only the firm rules
and (optionally) the guard thresholds change. Rules = FundedNext Stellar 1-Step as used in Best Prop 15 Backtest 2026-10-29/onestep.py
(owner screenshot): one phase to +10%, daily loss 3% of the initial balance from the day-start balance, max loss 6% STATIC, at least 2
trading days, no time limit (reported within 180 days). $100k account (k = 10).
Guard variants (as onestep.py, scaled to $100k):
  INSTALLED : the installed Prop Ready guard: 92% buffer, 3% daily reserve/latch -- the buffer sits BELOW the 94% one-step floor;
  ONESTEP   : hypothetical one-step guard, 95.5% buffer and 2.5% daily reserve/latch, otherwise identical (NOT a built package).
Writes OS-<candidate>-<risk>-<variant>.json. Run from EA store:
  uv run --with pandas --with numpy python "<this>" <candidate> <risk> <variant>"""
import importlib.util, json, random, statistics, sys, time
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prop_select', R / 'prop_select.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
C = S.C                                                         # Portfolio Prop Comparison compare.py
FLOOR, DAILY, TARGET, MIN_DAYS = 0.94, 0.03, 1.10, 2            # fractions of the initial balance
VARIANTS = {'INSTALLED': dict(buffer=0.92, reserve=0.03), 'ONESTEP': dict(buffer=0.955, reserve=0.025)}


def make(v):
    class OneStep(C.Challenge):
        def observe(self, t):
            super().observe(t)                                  # stats + the 2-step checks (9000k / 500k: looser, never fire first)
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.eq <= FLOOR * self.C + 1e-8 or self.eq <= self.anchor - DAILY * self.C + 1e-8:
                p = self.current(); kind = 'static' if self.eq <= FLOOR * self.C + 1e-8 else 'daily'
                p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor,
                         hard_failure_kind=kind)
                self.failed = True; self.counts['onestep_' + kind + '_breach'] += 1
            elif self.eq <= self.anchor - v['reserve'] * self.C + 1e-8:
                self.day_stopped = True

        def target(self): return TARGET * self.C

        def maybe_pass(self, t):
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.balance >= self.target() - 1e-8 and len(self.days) >= MIN_DAYS and not self.active:
                self.current().update(status='passed', pass_epoch=t, entry_days=sorted(self.days), terminal_balance=self.balance,
                                      terminal_equity=self.eq, terminal_daily_anchor=self.anchor)
                self.finished = True

        def activate(self, t): return                           # one phase only

        def reject_reason(self, row, t, risk, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and len(self.days) >= MIN_DAYS: return 'target_entry_gate_await_flat'
            return self.limits(row, t, risk, margin)

        def limits(self, row, t, risk, margin):                 # sizes.ScaledChallenge.limits with the variant buffer / reserve
            k = self.k; m = self.cap_now / (50 * k)
            if self.day_stopped: return 'daily_latch'
            if self.daily_entries >= 7: return 'daily_7_entry_limit'
            if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
            total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
            if total + risk > 225 * m * k + 1e-7: return 'aggregate_initial_risk'
            if same + risk > 150 * m * k + 1e-7: return 'same_symbol_initial_risk'
            reserve = sum(1.25 * p['risk'] + 5 * k for p in self.active.values())
            projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5 * k
            if projected < v['buffer'] * self.C - 1e-8: return 'soft_total_buffer'
            if self.anchor - projected > v['reserve'] * self.C + 1e-8: return 'soft_daily_reserve'
            existing = sum(p['margin'] for p in self.active.values())
            if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
            if t < self.last_entry + 3: return 'entry_reconciliation3s'
            return None
    return OneStep


def one(Trial, plan, name, guard, r, d, ev):
    m = Trial(plan, name, S.P.start_dict(d, S.P.HORIZON), guard, r); res = S.P.drive(m, ev).result(); p = res['phase1']
    days = p['elapsed_to_terminal']['inclusive_prague_days'] if p['status'] == 'passed' else None
    return dict(start=d.isoformat(), passed=p['status'] == 'passed', breach=p['status'] == 'failed', kind=p.get('hard_failure_kind'), days=days,
                buffer=any(k.startswith('soft_total_buffer') for k in res['counts']), trades=len(res['trades']))


def summarize(rows):
    n = len(rows); ok = sorted(r['days'] for r in rows if r['passed']); sh = lambda f: round(sum(1 for r in rows if f(r)) / n, 4) if n else None  # noqa: E731
    q = lambda p: ok[min(len(ok) - 1, int(p * len(ok)))] if ok else None  # noqa: E731
    return dict(n=n, pass_180=sh(lambda r: r['passed']), pass_30=sh(lambda r: r['passed'] and r['days'] <= 30), pass_60=sh(lambda r: r['passed'] and r['days'] <= 60),
                pass_90=sh(lambda r: r['passed'] and r['days'] <= 90), breach=sh(lambda r: r['breach']), breach_daily=sh(lambda r: r['kind'] == 'daily'),
                breach_static=sh(lambda r: r['kind'] == 'static'), still_open=sh(lambda r: not r['passed'] and not r['breach']),
                stuck_buffer=sh(lambda r: r['buffer'] and not r['passed'] and not r['breach']), median_days=statistics.median(ok) if ok else None,
                p25_days=q(.25), p75_days=q(.75), median_trades=statistics.median(r['trades'] for r in rows) if rows else None)


def main(name, risk, variant):
    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; Trial = make(VARIANTS[variant]); began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5:
            rows.append(one(Trial, plan, name, cfg['guard'], r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, variant=variant, guard=VARIANTS[variant], rules=dict(floor=FLOOR, daily=DAILY, target=TARGET, min_days=MIN_DAYS),
               hist={s: summarize([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = summarize([one(Trial, plan, name, cfg['guard'], r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (R / f'OS-{name}-{risk}-{variant}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, risk, variant, out['seconds'], flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:4])
