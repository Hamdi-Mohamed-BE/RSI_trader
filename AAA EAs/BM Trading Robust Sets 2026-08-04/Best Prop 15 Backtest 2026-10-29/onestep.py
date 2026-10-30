"""Addendum (owner 2026-10-29: "what about 1 step phase challenges?"): Best Prop 15 and Best Prop 9 on a ONE-STEP challenge.
Rules = FundedNext Stellar 1-Step as in the owner's screenshot (fundednext_compare.py): one phase to +10%, daily loss 3% of the initial
balance from the day-start balance (engine: Prague midnight), max loss 6% STATIC (floor $9,400 on $10k), min 2 trading days, no time limit
(reported within 30 / 60 / 90 / 180 days). Same frozen engine, streams, starts, Monte Carlo and costs as bp15.py; only the firm rules and
the guard variant change.
Guard variants:
  INSTALLED-1.0 : the packages exactly as built ($100 / entry, $450 total, $300 symbol, $9,200 buffer, $300 daily latch/reserve) -- the
                  buffer sits BELOW the 1-step floor, so it cannot protect it;
  ONESTEP-1.0   : hypothetical 1-step guard: buffer $9,550, daily latch/reserve $250, otherwise as installed (NOT a built package);
  ONESTEP-0.5   : as ONESTEP-1.0 with $50 per entry (totals scale: $225 / $150).
Breach is checked on sampled equity (5-minute marks); 3 Way Gold has no intratrade marks. In-sample + previously viewed OOS; not a forecast.

python onestep.py run <BP9|BP15> <variant>   |   python onestep.py all   |   python onestep.py table
"""
import bisect, json, random, statistics, subprocess, sys, time
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
import bp15 as X  # noqa: E402

RT, D = X.RT, X.D; e = D.e
FLOOR, DAILY, TARGET, MIN_DAYS = 9400.0, 300.0, 11000.0, 2
VARIANTS = {'INSTALLED-1.0': dict(cap=100.0, buffer=9200.0, reserve=300.0), 'ONESTEP-1.0': dict(cap=100.0, buffer=9550.0, reserve=250.0),
            'ONESTEP-0.5': dict(cap=50.0, buffer=9550.0, reserve=250.0)}
MC_PATHS = 1000


def make_trial(v):
    class OneStep(D.DialTrial):
        def observe(self, t):
            super().observe(t)                                            # stats + the engine's 2-step checks (looser: never fire first)
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.eq <= FLOOR + 1e-8 or self.eq <= self.anchor - DAILY + 1e-8:
                p = self.current(); kind = 'static' if self.eq <= FLOOR + 1e-8 else 'daily'
                p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor, hard_failure_kind=kind)
                self.failed = True; self.counts['onestep_' + kind + '_breach'] += 1
            elif self.eq <= self.anchor - v['reserve'] + 1e-8:
                if not self.day_stopped: self.counts['guard_daily_latch'] += 1
                self.day_stopped = True

        def maybe_pass(self, t):
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.balance >= TARGET - 1e-8 and len(self.days) >= MIN_DAYS and not self.active:
                p = self.current(); p.update(status='passed', pass_epoch=t, entry_days=sorted(self.days), terminal_balance=self.balance, terminal_equity=self.eq,
                                             terminal_daily_anchor=self.anchor)
                self.finished = True

        def activate(self, t): return                                     # one phase only

        def reject_reason(self, row, t, risk, margin):
            m = self.cap_now / 50
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.day_stopped: return 'daily_latch'
            if self.balance >= TARGET - 1e-8 and len(self.days) >= MIN_DAYS: return 'target_entry_gate_await_flat'
            if self.daily_entries >= 7: return 'daily_7_entry_limit'
            if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
            total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
            if total + risk > 225 * m + 1e-7: return 'aggregate_initial_risk'
            if same + risk > 150 * m + 1e-7: return 'same_symbol_initial_risk'
            reserve = sum(1.25 * p['risk'] + 5 for p in self.active.values())
            projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5
            if projected < v['buffer'] - 1e-8: return 'soft_total_buffer'
            if self.anchor - projected > v['reserve'] + 1e-8: return 'soft_daily_reserve'
            existing = sum(p['margin'] for p in self.active.values())
            if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
            if t < self.last_entry + 3: return 'entry_reconciliation3s'
            return None
    return OneStep


def replay(Trial, plan, basket, start, cost, events, cap):
    m = Trial(plan, basket, start, cost, 'next_prague_midnight', [(-1e9, cap)])
    for t, kind, pr_, key, row, mark in events:
        if kind == 0: m.day_reset(t)
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
    r = m.result(); p = r['phase1']
    days = p['elapsed_to_terminal']['inclusive_prague_days'] if p['status'] == 'passed' else None
    return dict(start=r['start_date'], passed=p['status'] == 'passed', breach=p['status'] == 'failed', days=days, kind=p.get('hard_failure_kind'),
                buffer=any(k.startswith('soft_total_buffer') for k in r['counts']), trades=len(r['trades']), eqdd=r['max_sampled_equity_drawdown_cash'],
                day=r['max_daily_sampled_equity_loss'])


def summarize(rows):
    n = len(rows); ok = [r['days'] for r in rows if r['passed']]
    sh = lambda f: round(sum(1 for r in rows if f(r)) / n, 4) if n else None  # noqa: E731
    return dict(n=n, pass_180=sh(lambda r: r['passed']), pass_30=sh(lambda r: r['passed'] and r['days'] <= 30), pass_60=sh(lambda r: r['passed'] and r['days'] <= 60),
                pass_90=sh(lambda r: r['passed'] and r['days'] <= 90), breach=sh(lambda r: r['breach']), breach_daily=sh(lambda r: r['kind'] == 'daily'),
                breach_static=sh(lambda r: r['kind'] == 'static'), still_open=sh(lambda r: not r['passed'] and not r['breach']), stuck_buffer=sh(lambda r: r['buffer'] and not r['passed'] and not r['breach']),
                median_days=statistics.median(ok) if ok else None, p25_days=RT.q(ok, .25) if ok else None, p75_days=RT.q(ok, .75) if ok else None,
                median_trades=statistics.median(r['trades'] for r in rows) if rows else None, eqdd_p95=round(RT.q([r['eqdd'] for r in rows], .95), 1) if rows else None,
                day_max=round(max(r['day'] for r in rows), 1) if rows else None)


def run(name, variant):
    v = VARIANTS[variant]; Trial = make_trial(v); began = time.time()
    data, plan, events = X.setup(name); epochs = [x[0] for x in events]; basket = 'CORE4_PLUS_FIVE_ORBS_05R' if name == 'BP9' else 'BP15'
    out = dict(portfolio=name, variant=variant, guard=v, rules=dict(floor=FLOOR, daily=DAILY, target=TARGET, min_days=MIN_DAYS), history={}, mc={})
    for cost in ('recorded_exness', 'fixed_cost_stress'):
        rows = []
        for s in X.starts(*X.SEG['all']):
            w = events[bisect.bisect_left(epochs, s['epoch']):bisect.bisect_left(epochs, s['horizon_epoch'])]
            rows.append(replay(Trial, plan, basket, s, cost, w, v['cap']))
        for seg in ('dev', 'val', 'oos', 'all'):
            a, b = X.SEG[seg]
            keep = [r for r in rows if a <= date.fromisoformat(r['start']) and date.fromisoformat(r['start']) + timedelta(days=180) <= b]
            out['history'][f'{seg}|{cost}'] = summarize(keep)
        print(name, variant, cost, 'history', json.dumps(out['history'][f'all|{cost}']), f'{time.time() - began:.0f}s', flush=True)
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m = [], date(2021, 10, 11)
    while m + timedelta(days=RT.BLOCK_DAYS) <= date(2026, 10, 6):
        mondays.append(m); m += timedelta(days=7)
    index = {m: (bisect.bisect_left(ops, RT.midnight(m)), bisect.bisect_left(ops, RT.midnight(m + timedelta(days=RT.BLOCK_DAYS)))) for m in mondays}
    rng = random.Random(RT.SEED); sd = date(2030, 1, 7)
    start = dict(date=sd.isoformat(), epoch=RT.midnight(sd), horizon_date=(sd + timedelta(days=180)).isoformat(), horizon_epoch=RT.midnight(sd + timedelta(days=180)))
    rows = {c: [] for c in ('recorded_exness', 'fixed_cost_stress')}
    for i in range(MC_PATHS):
        ev = RT.bootstrap_events(pool, mondays, index, rng, sd, priority)
        for c in rows: rows[c].append(replay(Trial, plan, basket, start, c, ev, v['cap']))
    for c, vv in rows.items():
        out['mc'][c] = summarize(vv); print(name, variant, c, 'MC', json.dumps(out['mc'][c]), flush=True)
    out['seconds'] = round(time.time() - began)
    (R / f'ONESTEP-{name}-{variant}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def run_all():
    procs = [subprocess.Popen([sys.executable, str(Path(__file__)), 'run', n, v], cwd=R, stdout=(R / f'onestep-{n}-{v}.log').open('w'), stderr=subprocess.STDOUT)
             for n in ('BP9', 'BP15') for v in VARIANTS]
    print('exit codes', [p.wait() for p in procs])


def table():
    pct = lambda x: '–' if x is None else f'{100 * x:.0f}%'  # noqa: E731
    md = ['# Best Prop 9 / 15 on a ONE-STEP challenge (generated by onestep.py)', '',
          'FundedNext Stellar 1-Step rules: +10% target, 3% daily, 6% static max loss, 2 trading days; $10k; recorded Exness costs (fixed-cost stress in brackets).',
          'History = every weekday start; MC = 1,000 four-week-block paths. In-sample / previously-viewed OOS, not a forecast.', '',
          '| Portfolio | Guard | Period | Pass ≤180 d | ≤30 d | ≤60 d | ≤90 d | Breach (daily / static) | Still open (stuck at buffer) | Median days to pass (p25–p75) | Median trades |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for n in ('BP9', 'BP15'):
        for v in VARIANTS:
            o = json.loads((R / f'ONESTEP-{n}-{v}.json').read_text(encoding='utf-8'))
            for seg, label in (('dev', 'History 2021-23'), ('val', 'History 2023-24'), ('oos', 'History 2024-26 (OOS)'), ('all', 'History all'), ('mc', 'Monte Carlo')):
                m = o['mc']['recorded_exness'] if seg == 'mc' else o['history'][f'{seg}|recorded_exness']
                s = o['mc']['fixed_cost_stress'] if seg == 'mc' else o['history'][f'{seg}|fixed_cost_stress']
                md.append(f"| {n} | {v} | {label} | {pct(m['pass_180'])} ({pct(s['pass_180'])}) | {pct(m['pass_30'])} | {pct(m['pass_60'])} | {pct(m['pass_90'])} | "
                          f"{pct(m['breach'])} ({pct(m['breach_daily'])} / {pct(m['breach_static'])}) | {pct(m['still_open'])} ({pct(m['stuck_buffer'])}) | "
                          f"{m['median_days']} ({m['p25_days']}–{m['p75_days']}) | {m['median_trades']} |")
    (R / 'ONESTEP.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    {'run': lambda: run(sys.argv[2], sys.argv[3]), 'all': run_all, 'table': table}[sys.argv[1]]()
