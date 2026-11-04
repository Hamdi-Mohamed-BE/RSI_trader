"""Owner 2026-11-04: "for ftmo both phases and one phase what happens if we don't stop at the buffer". Same frozen prop_select engine,
streams, weekday starts, MC pool and seed ($100k).
  two   <cand> <risk>            FTMO 2-Step with the guard's 92% equity entry buffer REMOVED; every other guard line unchanged
                                 (sizes.ScaledChallenge.limits minus the buffer check). -> NB2-<cand>-<risk>.json (same summary as CH-*.json)
  ftmo1 <cand> <risk> <ON|OFF>   FTMO 1-Step (ftmo.com trading objectives, read 2026-11-03): one phase to +10%; max daily loss 3% of the
                                 initial capital measured from the midnight balance; max loss = highest end-of-day balance (or initial
                                 capital) - 10%, end-of-day trailing, only rises; best-day rule (orders from 12 Oct 2026): best day <= 50%
                                 of total profit, otherwise keep trading; no minimum days stated (modelled: 1). ON = the installed 92%
                                 buffer (static, of the initial balance), OFF = no buffer. -> F1-<cand>-<risk>-<ON|OFF>.json
Breach is checked on sampled equity marks as in the rest of the study. In-sample; OOS previously viewed. Run from EA store:
  uv run --with pandas --with numpy python "<this>" two FTMO17 1.00"""
import importlib.util, inspect, json, random, sys, time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('onestep_select', R / 'onestep_select.py')
O = importlib.util.module_from_spec(spec); spec.loader.exec_module(O)
S, C = O.S, O.C; SZ = C.S; EN = SZ.E                            # prop_select, compare.py, sizes.py, core engine


def no_buffer_limits(self, row, t, risk, margin):
    """sizes.ScaledChallenge.limits without the 92% buffer check; every other line identical."""
    k = self.k; m = self.cap_now / (50 * k)
    if self.day_stopped: return 'daily_300_latch'
    if self.daily_entries >= 7: return 'daily_7_entry_limit'
    if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
    total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
    if total + risk > 225 * m * k + 1e-7: return 'aggregate_initial_risk225'
    if same + risk > 150 * m * k + 1e-7: return 'same_symbol_initial_risk150'
    reserve = sum(1.25 * p['risk'] + 5 * k for p in self.active.values())
    projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5 * k
    if self.anchor - projected > 300 * k + 1e-8: return 'soft_daily_reserve300'
    existing = sum(p['margin'] for p in self.active.values())
    if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
    if t < self.last_entry + 3: return 'entry_reconciliation3s'
    return None


orig = [l.strip() for l in inspect.getsource(SZ.ScaledChallenge.limits).splitlines()[1:]]
mine = [l.strip() for l in inspect.getsource(no_buffer_limits).split('"""')[2].splitlines() if l.strip()]
assert [l for l in orig if 'soft_total_buffer9200' not in l] == mine, 'no_buffer_limits differs beyond the buffer line'


def two(name, risk):
    SZ.ScaledChallenge.limits = no_buffer_limits
    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan); sd = date(2030, 1, 7)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append((d, C.challenge_one(plan, name, cfg['guard'], r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON))))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, buffer='OFF', hist={s: S.T.summarize([x for d, x in rows if a <= d < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED)
    out['mc'] = S.T.summarize([C.challenge_one(plan, name, cfg['guard'], r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (R / f'NB2-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done two', name, risk, out['seconds'], flush=True)


def make_ftmo1(buffer_on):
    class FTMO1(C.Challenge):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw); self.hwm = self.C

        def floor(self): return self.hwm - 0.10 * self.C

        def day_reset(self, t):
            if not self.failed and not self.finished: self.hwm = max(self.hwm, self.balance)   # end-of-day balance trails the floor up
            super().day_reset(t)

        def observe(self, t):
            super().observe(t)                                   # stats + 2-step checks (90% static / 5% daily: never tighter)
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.eq <= self.floor() + 1e-8 or self.eq <= self.anchor - 0.03 * self.C + 1e-8:
                p = self.current(); kind = 'trailing' if self.eq <= self.floor() + 1e-8 else 'daily'
                p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor, hard_failure_kind=kind)
                self.failed = True; self.counts['ftmo1_' + kind + '_breach'] += 1

        def target(self): return 1.10 * self.C

        def best_day_ok(self):
            profit = self.balance - self.C; days = defaultdict(float)
            for x in self.trades: days[EN.day_of(x['cl'])] += x['net']
            return profit > 0 and max(days.values(), default=0.0) <= 0.5 * profit + 1e-8

        def maybe_pass(self, t):
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.balance >= self.target() - 1e-8 and len(self.days) >= 1 and not self.active and self.best_day_ok():
                self.current().update(status='passed', pass_epoch=t, entry_days=sorted(self.days), terminal_balance=self.balance,
                                      terminal_equity=self.eq, terminal_daily_anchor=self.anchor)
                self.finished = True

        def activate(self, t): return

        def reject_reason(self, row, t, risk, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            return SZ.ScaledChallenge.limits(self, row, t, risk, margin) if buffer_on else no_buffer_limits(self, row, t, risk, margin)
    return FTMO1


def ftmo1(name, risk, buf):
    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; Trial = make_ftmo1(buf == 'ON'); began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append(O.one(Trial, plan, name, cfg['guard'], r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, buffer=buf, rules='FTMO 1-Step: +10%, 3% daily from midnight balance, 10% EOD-trailing max loss, best day <= 50%',
               hist={s: O.summarize([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = O.summarize([O.one(Trial, plan, name, cfg['guard'], r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (R / f'F1-{name}-{risk}-{buf}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done ftmo1', name, risk, buf, out['seconds'], flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    two(a[1], a[2]) if a[0] == 'two' else ftmo1(a[1], a[2], a[3])
