"""Max open drawdown per profile (owner 2026-11-05: "show max open draw down for each profile; what happens when we add guard for 1 step and 2 steps ftmo").
Frozen engines through merged.engines(), unchanged: a tracker subclass only reads the state on every 5-minute mark. Streams 2021-10-07 -> 2026-10-06 (the only data with intratrade marks),
$100k, every weekday start with a 180-day window, plus the same 2,000-path MC pool and seed. Measures, for as long as the run is live:
  open  = the largest floating loss on all open trades together (equity - balance at its lowest);
  eqdd  = the largest peak-to-trough equity drawdown including open trades;  closed = the same on closed balance;  n = most trades open at once;  day = worst equity loss within a Prague day.
Modes: NONE = no guard, no firm stop and no target, lots as the unguarded model, firm-limit touches only recorded (what the raw portfolio does);
       G2 = FTMO 2-step Prop Ready guard as simulated, stops at a breach or after both phases; G1 = FTMO 1-Step, the built ftmo 1_step guard, stops at a breach or a pass.
FULL = one continuous NONE path over all 5 years. G2 / G1 pass and breach rates must equal the stored CH-* / F1P-* results (parity).
  job <name> <mode> <risk> | runall [workers] | table      -> DD-<name>-<mode>-<risk>.json, TABLES_OPEN_DD.md
Run from EA store: uv run --with pandas --with numpy python "<this>" runall 9"""
import importlib.util, json, random, subprocess, sys, time
from datetime import date, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent; NAMES = ('FTMO17', 'E10', 'M22'); MODES = ('NONE', 'G2', 'G1'); RISKS = ('0.50', '0.75', '1.00')


def q(arr, p):
    arr = sorted(arr); return arr[min(len(arr) - 1, int(p * len(arr)))] if arr else None


def job(name, mode, risk):
    spec = importlib.util.spec_from_file_location('merged', H / 'merged.py'); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    S, F1, O, N, C = M.engines(); r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze()

    def tracked(Base):
        class Tracked(Base):
            def __init__(self, *a, **k):
                super().__init__(*a, **k); self.x_open = self.x_dd = self.x_day = 0.0; self.x_n = 0; self.x_touch2 = self.x_touch1 = False

            def live_update(self):
                self.x_open = min(self.x_open, self.eq - self.balance); self.x_dd = max(self.x_dd, self.peak - self.eq)
                self.x_day = max(self.x_day, self.anchor - self.eq); self.x_n = max(self.x_n, len(self.active))

            def observe(self, t):
                was_live = not self.failed and not self.finished
                super().observe(t)
                if was_live: self.live_update()
        return Tracked

    class Raw(tracked(N.make_ftmo1(True))):              # no guard, no firm stop, no target: limits are only recorded
        def observe(self, t):
            super().observe(t)
            self.x_touch2 = self.x_touch2 or self.eq <= 0.90 * self.C + 1e-8 or self.eq <= self.anchor - 0.05 * self.C + 1e-8
            self.x_touch1 = self.x_touch1 or self.eq <= self.floor() + 1e-8 or self.eq <= self.anchor - 0.03 * self.C + 1e-8
            if self.failed:
                self.failed = False; p = self.current(); p['status'] = 'pending'

        def maybe_pass(self, t): return

        def reject_reason(self, row, t, risk_, margin): return C.unguarded_reject(self, row, t, margin)

    Cls = {'NONE': Raw, 'G2': tracked(C.Challenge), 'G1': tracked(F1.Profile)}[mode]; guard = mode != 'NONE'; assert not guard or S.CANDIDATES[name]['guard'] is True
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan)

    def one(d, ev, days=S.P.HORIZON):
        m = Cls(plan, name, S.P.start_dict(d, days), guard, r); res = S.P.drive(m, ev).result(); c = m.C / 100
        ph = res['phase2'] if mode == 'G2' else res['phase1']
        return dict(start=d.isoformat(), open=round(-m.x_open / c, 3), eqdd=round(m.x_dd / c, 3), closed=round(res['max_closed_drawdown_cash'] / c, 3), day=round(m.x_day / c, 3), n=m.x_n,
                    risk=round(res['max_initial_open_risk'] / c, 3), touch2=m.x_touch2, touch1=m.x_touch1, passed=ph['status'] == 'passed',
                    breach=any(res[k]['status'] == 'failed' for k in ('phase1', 'phase2') if res.get(k)), trades=len(res['trades']), end=round(res['ending_balance'] / c - 100, 2))

    def summ(rows):
        out = dict(n=len(rows))
        for k in ('open', 'eqdd', 'closed', 'day', 'n', 'risk'):
            v = [x[k] for x in rows]; out[k] = dict(p50=q(v, .5), p95=q(v, .95), max=max(v))
        for k in ('touch2', 'touch1', 'passed', 'breach'): out[k] = round(sum(x[k] for x in rows) / len(rows), 4)
        return out

    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append(one(d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    out = dict(name=name, mode=mode, risk=r, hist={s: summ([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    worst = max(rows, key=lambda x: x['open']); out['worst_open_window'] = dict(start=worst['start'], open=worst['open'], eqdd=worst['eqdd'], n=worst['n'])
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = summ([one(sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    if mode == 'NONE':
        days = (S.P.DATA_END - S.P.DATA_START).days; full = one(S.P.DATA_START, S.P.window(events, epochs, S.P.midnight(S.P.DATA_START), S.P.midnight(S.P.DATA_START + timedelta(days=days))), days)
        out['full_5y'] = full
    out['seconds'] = round(time.time() - began)
    (H / f'DD-{name}-{mode}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, mode, risk, out['seconds'], flush=True)


def runall(workers):
    (H / 'logs').mkdir(exist_ok=True)
    pending = [(n, m, r) for n in NAMES for m in MODES for r in RISKS if not (H / f'DD-{n}-{m}-{r}.json').exists()]; running = []
    print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            q_ = pending.pop(0); log = open(H / 'logs' / f"dd-{'-'.join(q_)}.log", 'w')
            running.append((q_, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *q_], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(10)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close(); print('finished' if item[1].returncode == 0 else 'FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


def table():
    DIRS = (H, H.parent / 'Edge Portfolio E10 2026-11-04', H.parent / 'Prop Portfolio Selection 2026-11-03')

    def stored(f):
        for d in DIRS:
            if (d / f).exists(): return json.loads((d / f).read_text(encoding='utf-8'))
    L = ['Percent of the $100k account. Max open = largest floating loss on all open trades together. Median / worst 5% / worst of the Monte Carlo paths, then the worst real historical window.', '',
         '| Portfolio | Risk | Version | Max open loss: median / p95 / worst MC | Worst real window | Equity DD: median / p95 / worst MC | Worst real window | Worst day p95 | Most trades open | Touches 1-Step / 2-step limit | Pass rate | Parity vs stored |', '|---|---|---|---|---:|---|---:|---:|---:|---|---:|---|']
    LABEL = {'NONE': 'No guard', 'G2': '2-step guard', 'G1': '1-Step guard'}
    for n in NAMES:
        for r in RISKS:
            for m in MODES:
                p = H / f'DD-{n}-{m}-{r}.json'
                if not p.exists(): L.append(f'| {n} | {r}% | {LABEL[m]} | running |||||||||'); continue
                d = json.loads(p.read_text(encoding='utf-8')); mc, a = d['mc'], d['hist']['all']; par = '-'
                if m != 'NONE':
                    s = stored(f"{'CH' if m == 'G2' else 'F1P'}-{n}-{r}.json"); key = 'pass_both_180' if m == 'G2' else 'pass_180'
                    if s: par = 'OK' if abs(s['mc'][key] - mc['passed']) < 1e-3 and abs(s['hist']['all'][key] - a['passed']) < 1e-3 else f"DIFF {s['mc'][key]} vs {mc['passed']}"
                f = lambda k: f"{mc[k]['p50']:.1f} / {mc[k]['p95']:.1f} / {mc[k]['max']:.1f}%"  # noqa: E731
                touch = f"{100 * mc['touch1']:.0f}% / {100 * mc['touch2']:.0f}%" if m == 'NONE' else f"{100 * mc['breach']:.0f}% breach"
                L.append(f"| {n} | {r}% | {LABEL[m]} | {f('open')} | {a['open']['max']:.1f}% | {f('eqdd')} | {a['eqdd']['max']:.1f}% | {mc['day']['p95']:.1f}% | {mc['n']['max']} | {touch} | {'-' if m == 'NONE' else f'{100 * mc['passed']:.0f}%'} | {par} |")
    # The stored full_5y path is not tabulated: compounded cash against the $100k start gives meaningless percentages (for example 959%). See FUNDED_2024.md for % of peak.
    (H / 'TABLES_OPEN_DD.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'job': job(a[1], a[2], a[3])
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 9)
    elif a[0] == 'table': table()
