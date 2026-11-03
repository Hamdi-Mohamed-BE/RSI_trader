"""Owner 2026-11-03: "test the 6x open risk cap over 5 years". Same frozen engine and streams as prop_select.py; the ONLY change is the
guard's total open-risk cap: 225*m*k (4.5 x the per-trade cap) -> 300*m*k (6 x). Per symbol 3x, daily reserve, 92% buffer, 7 entries /
3 losses a day, margin and phase rules unchanged. Writes CH6-<candidate>-<risk>.json next to the 4.5x CH-*.json.
Run from EA store: uv run --with pandas --with numpy python "<this>" <candidate> <risk>   (e.g. FTMO17 1.00)"""
import importlib.util, json, random, sys, time
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prop_select', R / 'prop_select.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
SZ = S.C.S                                                     # FTMO First Payout Study sizes.py (ScaledChallenge.limits)
TOTAL_MULTIPLE = 6.0


def limits(self, row, t, risk, margin):
    """sizes.ScaledChallenge.limits with the total cap 4.5x -> TOTAL_MULTIPLE x; every other line identical."""
    k = self.k; m = self.cap_now / (50 * k)
    if self.day_stopped: return 'daily_300_latch'
    if self.daily_entries >= 7: return 'daily_7_entry_limit'
    if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
    total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
    if total + risk > 50 * TOTAL_MULTIPLE * m * k + 1e-7: return 'aggregate_initial_risk225'
    if same + risk > 150 * m * k + 1e-7: return 'same_symbol_initial_risk150'
    reserve = sum(1.25 * p['risk'] + 5 * k for p in self.active.values())
    projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5 * k
    if projected < 9200 * k - 1e-8: return 'soft_total_buffer9200'
    if self.anchor - projected > 300 * k + 1e-8: return 'soft_daily_reserve300'
    existing = sum(p['margin'] for p in self.active.values())
    if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
    if t < self.last_entry + 3: return 'entry_reconciliation3s'
    return None


# guard: the patched function must equal the original except for the cap line
import inspect  # noqa: E402
orig = inspect.getsource(SZ.ScaledChallenge.limits).replace('225 * m * k', '50 * TOTAL_MULTIPLE * m * k')
mine = inspect.getsource(limits).split('"""')[0] + inspect.getsource(limits).split('"""', 2)[2].lstrip('\n')
assert [l.strip() for l in orig.splitlines()[1:]] == [l.strip() for l in mine.splitlines()[1:]], 'patched limits differs beyond the cap'
SZ.ScaledChallenge.limits = limits


def challenge(name, risk):
    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = S.C.mc_pool(data, plan); sd = date(2030, 1, 7)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5:
            rows.append((d, S.C.challenge_one(plan, name, cfg['guard'], r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON))))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, total_open_risk_multiple=TOTAL_MULTIPLE,
               hist={s: S.T.summarize([x for d, x in rows if a <= d < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED)
    out['mc'] = S.T.summarize([S.C.challenge_one(plan, name, cfg['guard'], r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (R / f'CH6-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, risk, out['seconds'], flush=True)


if __name__ == '__main__':
    challenge(sys.argv[1], sys.argv[2])
