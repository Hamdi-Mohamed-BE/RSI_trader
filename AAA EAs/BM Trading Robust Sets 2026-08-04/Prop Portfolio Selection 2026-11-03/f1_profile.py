"""Simulate the built "ftmo 1_step" profile (owner 2026-11-04) on FTMO 1-Step rules at 0.5 / 0.75 / 1% per trade. Same frozen
prop_select engine, FTMO17 stream, weekday starts, MC pool and seed ($100k). Firm rules as nobuffer.py ftmo1 (10% EOD-trailing max loss,
3% daily from the midnight balance, best day <= 50%). Guard = the built CalyxFTMOGuard.mqh of _00 Live profiles/ftmo 1_step:
new entries need projected equity >= trailing floor + 2% and projected daily loss <= 2.5% (the day latches at 2.5%); no new entries
once today's P&L (equity - midnight balance) >= 4.5%; Challenge stops new entries at +10% once the best-day rule holds; caps 4.5x /
3x, 7 entries / 3 losses a day, margin, 3 s reconciliation unchanged. -> F1P-<cand>-<risk>.json
Run from EA store: uv run --with pandas --with numpy python "<this>" FTMO17 0.50"""
import importlib.util, json, random, sys, time
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('nobuffer', R / 'nobuffer.py')
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
S, C, O = N.S, N.C, N.O
FLOOR_BUFFER, DAILY_RESERVE, BEST_DAY_CAP = 0.02, 0.025, 0.045


class Profile(N.make_ftmo1(True)):
    def observe(self, t):
        super().observe(t)
        if not self.failed and not self.finished and self.eq <= self.anchor - DAILY_RESERVE * self.C + 1e-8: self.day_stopped = True

    def limits(self, row, t, risk, margin):
        k = self.k; m = self.cap_now / (50 * k)
        if self.day_stopped: return 'daily_latch_2.5'
        if self.daily_entries >= 7: return 'daily_7_entry_limit'
        if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
        if self.eq - self.anchor >= BEST_DAY_CAP * self.C - 1e-8: return 'best_day_cap_4.5'
        total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
        if total + risk > 225 * m * k + 1e-7: return 'aggregate_initial_risk'
        if same + risk > 150 * m * k + 1e-7: return 'same_symbol_initial_risk'
        reserve = sum(1.25 * p['risk'] + 5 * k for p in self.active.values())
        projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5 * k
        if projected < self.floor() + FLOOR_BUFFER * self.C - 1e-8: return 'trailing_floor_buffer'
        if self.anchor - projected > DAILY_RESERVE * self.C + 1e-8: return 'daily_reserve_2.5'
        existing = sum(p['margin'] for p in self.active.values())
        if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
        if t < self.last_entry + 3: return 'entry_reconciliation3s'
        return None

    def reject_reason(self, row, t, risk, margin):
        if self.failed: return 'permanent_hard_failure'
        if self.finished: return 'passed'
        if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
        return self.limits(row, t, risk, margin)


def one(plan, name, guard, r, d, ev):
    m = Profile(plan, name, S.P.start_dict(d, S.P.HORIZON), guard, r); res = S.P.drive(m, ev).result(); p = res['phase1']
    days = p['elapsed_to_terminal']['inclusive_prague_days'] if p['status'] == 'passed' else None
    return dict(start=d.isoformat(), passed=p['status'] == 'passed', breach=p['status'] == 'failed', kind=p.get('hard_failure_kind'), days=days,
                buffer=any(k.startswith('trailing_floor_buffer') for k in res['counts']), trades=len(res['trades']),
                bestcap=res['counts'].get('best_day_cap_4.5', 0) > 0)


def main(name, risk):
    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append(one(plan, name, cfg['guard'], r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    summ = lambda rr: dict(O.summarize(rr), best_day_cap_hit=round(sum(x['bestcap'] for x in rr) / len(rr), 4) if rr else None)  # noqa: E731
    out = dict(candidate=name, risk=r, profile='ftmo 1_step', guard=dict(floor_buffer=FLOOR_BUFFER, daily_reserve=DAILY_RESERVE, best_day_cap=BEST_DAY_CAP),
               hist={s: summ([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = summ([one(plan, name, cfg['guard'], r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (R / f'F1P-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, risk, out['seconds'], flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
