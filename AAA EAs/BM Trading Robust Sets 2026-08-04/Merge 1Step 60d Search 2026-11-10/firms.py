"""Owner 2026-11-10: "find the best 1 step prop firm rules out there". Same frozen engine and streams as search.py, NO guard (only FTMO has a built guard),
$100k, weekday starts + MC 2,000. Firm rules are taken from third-party summaries found on 2026-11-10 (not the firms' own rulebooks) -> verify before buying.

  FTMO_1STEP   10% target, 3% daily (day-start balance), 10% max loss trailing the end-of-day balance, best day <= 50% of profit
  FUNDEDNEXT   Stellar 1-Step: 10% target, 3% daily, 6% STATIC max loss, >= 2 trading days
  THE5ERS      Hyper Growth: 10% target, 6% STATIC stop out, 3% daily PAUSE (not a breach; modelled as "no new entries for the rest of the day" while open
               trades keep running = optimistic: the real pause closes open trades)
  FTP_EXPRESS  Funded Trading Plus 1-Step Express: 10% target, 4% daily, 6% max loss trailing the end-of-day balance (trailing type assumed)
  SPEEDY       TraderScale Speedy: 10% target, 4% daily, 8% trailing that locks at the start balance, best day <= 40% of profit
  E8_ONE       E8 One (4% drawdown option): 6% target, 3% daily, 4% max loss trailing the end-of-day balance (type assumed)
Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" [members-json-file risk]   (default: the search picks in FINAL.json)"""
import json, random, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
import search as SR  # noqa: E402

N, C, S, O = SR.N, SR.C, SR.S, SR.O
FIRMS = {'FTMO_1STEP': dict(target=.10, daily=.03, maxloss=.10, kind='eod', best=.50, min_days=1, pause=False),
         'FUNDEDNEXT': dict(target=.10, daily=.03, maxloss=.06, kind='static', best=None, min_days=2, pause=False),
         'THE5ERS': dict(target=.10, daily=.03, maxloss=.06, kind='static', best=None, min_days=1, pause=True),
         'FTP_EXPRESS': dict(target=.10, daily=.04, maxloss=.06, kind='eod', best=None, min_days=1, pause=False),
         'SPEEDY': dict(target=.10, daily=.04, maxloss=.08, kind='eod_lock', best=.40, min_days=1, pause=False),
         'E8_ONE': dict(target=.06, daily=.03, maxloss=.04, kind='eod', best=None, min_days=1, pause=False)}


def make(f):
    class Firm(C.Challenge):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw); self.hwm = self.C; self.paused = False

        def floor(self):
            if f['kind'] == 'static': return (1 - f['maxloss']) * self.C
            fl = self.hwm - f['maxloss'] * self.C
            return min(fl, self.C) if f['kind'] == 'eod_lock' else fl

        def day_reset(self, t):
            if not self.failed and not self.finished: self.hwm = max(self.hwm, self.balance)
            self.paused = False; super().day_reset(t)

        def observe(self, t):
            super().observe(t)                                  # 2-step checks (10% static / 5% daily) are never tighter than these firms' limits
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            daily_hit = self.eq <= self.anchor - f['daily'] * self.C + 1e-8
            if self.eq <= self.floor() + 1e-8 or (daily_hit and not f['pause']):
                p = self.current(); kind = 'max' if self.eq <= self.floor() + 1e-8 else 'daily'
                p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor, hard_failure_kind=kind)
                self.failed = True; self.counts['firm_' + kind + '_breach'] += 1
            elif daily_hit: self.paused = True

        def target(self): return (1 + f['target']) * self.C

        def best_day_ok(self):
            if f['best'] is None: return True
            profit = self.balance - self.C; days = defaultdict(float)
            for x in self.trades: days[N.EN.day_of(x['cl'])] += x['net']
            return profit > 0 and max(days.values(), default=0.0) <= f['best'] * profit + 1e-8

        def maybe_pass(self, t):
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.balance >= self.target() - 1e-8 and len(self.days) >= f['min_days'] and not self.active and self.best_day_ok():
                self.current().update(status='passed', pass_epoch=t, entry_days=sorted(self.days), terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor)
                self.finished = True

        def activate(self, t): return

        def reject_reason(self, row, t, risk_, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            if self.paused: return 'daily_pause'
            return C.unguarded_reject(self, row, t, margin)
    return Firm


def run(args):
    firm, members, r = args
    if SR.ALL is None: SR.ALL = SR.pool()
    S.E.verify_freeze(); cls = make(FIRMS[firm]); name = 'XU'; data, plan, events, epochs = SR.setup(name, members); out = {}
    for seg in ('dev', 'val', 'oos'):
        a, b = S.SEG[seg]; rows = []; d = max(a, S.P.DATA_START)
        while d < b and d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
            if d.weekday() < 5: rows.append(O.one(cls, plan, name, False, r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
            d += timedelta(days=1)
        out[seg] = SR.summarize(rows)
    pl, mondays, index, priority = C.mc_pool(data, plan); rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = SR.summarize([O.one(cls, plan, name, False, r, sd, S.T.bootstrap_events(pl, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    return dict(firm=firm, risk=r, members=members, **out)


def main():
    if len(sys.argv) > 2: sets = {'custom': (json.loads(Path(sys.argv[1]).read_text()), float(sys.argv[2]))}
    else:
        F = json.loads((H / 'FINAL.json').read_text(encoding='utf-8'))
        sets = {'pick-forced': (F['picks']['NOGUARD-FORCED']['members'], None), 'pick': (F['picks']['NOGUARD']['members'], None),
                'Core9': (SR.REFS['Core9'], 0.0075), 'P4': (SR.REFS['P4'], 0.0075)}
    jobs = [(firm, m, r) for _k, (m, rr) in sets.items() for r in ((rr,) if rr else (0.005, 0.0075, 0.01)) for firm in FIRMS]
    labels = [k for k, (m, rr) in sets.items() for r in ((rr,) if rr else (0.005, 0.0075, 0.01)) for firm in FIRMS]
    with ProcessPoolExecutor(10) as ex: res = list(ex.map(run, jobs))
    for k, x in zip(labels, res): x['set'] = k
    (H / 'FIRMS.json').write_text(json.dumps(dict(rules=FIRMS, rows=res), indent=1, default=str), encoding='utf-8'); print('FIRMS DONE', flush=True)


if __name__ == '__main__':
    main()
