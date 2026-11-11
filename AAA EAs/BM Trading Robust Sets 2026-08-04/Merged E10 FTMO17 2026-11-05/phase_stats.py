"""Owner 2026-11-05: per-phase breach data the frozen engines do not summarise: days to breach, trading days before breach and worst CLOSED day on each
FTMO phase. Same engines, streams, seeds and MC paths as merged.py (Monte Carlo only, $100k): the pass / breach / income figures must reproduce the recorded
CH-, F1P-, F1U- and FU- files exactly, asserted at the end of every job.
Days = Prague calendar days from the phase activation, inclusive (as the engines count). Trading days = the engine's entry_days (Prague days with an entry).
Worst closed day = the biggest net loss of trades CLOSED on one Prague day inside the phase; floating daily loss is reported separately (sampled equity).
  job <two|one|fund> <name> <risk> | runall [workers]      -> PS-<kind>-<name>-<risk>.json, then table -> PHASE_STATS.md
Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" runall 6"""
import importlib.util, json, os, random, statistics, subprocess, sys, time
from collections import defaultdict
from datetime import date
from pathlib import Path

H = Path(__file__).resolve().parent
PATHS_OVERRIDE = int(os.environ.get('PS_PATHS', '0'))     # smoke test only; a full run asserts parity with the recorded files
DIRS = (H, H.parent / 'Edge Portfolio E10 2026-11-04', H.parent / 'Prop Portfolio Selection 2026-11-03')
RISKS = ('0.50', '0.75', '1.00'); GUARDED = ('C9', 'FTMO17', 'E10'); FREE = ('C9U', 'CUR17', 'E10U')
LABEL = {'C9': ('Core 9', 'guard'), 'C9U': ('Core 9', 'no guard'), 'FTMO17': ('FTMO17', 'guard'), 'CUR17': ('FTMO17', 'no guard'), 'E10': ('E10', 'guard'), 'E10U': ('E10', 'no guard')}
RECORDED = {'two': 'CH', 'fund': 'FU'}


def merged():
    spec = importlib.util.spec_from_file_location('merged', H / 'merged.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def recorded(prefix, name, risk):
    for d in DIRS:
        f = d / f'{prefix}-{name}-{risk}.json'
        if f.exists(): return json.loads(f.read_text(encoding='utf-8'))
    return None


def q(values, p):
    s = sorted(values); return s[min(len(s) - 1, int(p * len(s)))] if s else None


def med(values):
    return statistics.median(values) if values else None


def worst_closed(trades, day_of, phase=None):
    days = defaultdict(float)
    for t in trades:
        if phase is None or t.get('phase') == phase: days[day_of(t['cl'])] += t['net']
    return max(0.0, -min(days.values())) if days else 0.0


def phase_row(p, trades, phase, day_of):
    end = p['pass_epoch'] or p['fail_epoch']
    days = (day_of(end) - day_of(p['activation_epoch'])).days + 1 if end else None
    return dict(status=p['status'], days=days, trading_days=p.get('entry_days'), kind=p.get('hard_failure_kind'), worst=worst_closed(trades, day_of, phase))


def phase_summary(rows, total):
    n = len(rows); ok = [r for r in rows if r['status'] == 'passed']; bad = [r for r in rows if r['status'] == 'failed']; w = [r['worst'] for r in rows]
    return dict(entered=n, entered_share=round(n / total, 4), passed=round(len(ok) / n, 4) if n else None, breached=round(len(bad) / n, 4) if n else None, unfinished=round((n - len(ok) - len(bad)) / n, 4) if n else None,
                median_days_pass=med([r['days'] for r in ok]), median_trading_days_pass=med([r['trading_days'] for r in ok]),
                n_breach=len(bad), median_days_breach=med([r['days'] for r in bad]), p25_days_breach=q([r['days'] for r in bad], .25), p75_days_breach=q([r['days'] for r in bad], .75),
                median_trading_days_breach=med([r['trading_days'] for r in bad]), breach_daily=sum(r['kind'] == 'daily' for r in bad), breach_static=sum(r['kind'] == 'static' for r in bad),
                worst_closed_day_median=round(med(w), 1) if w else None, worst_closed_day_p95=round(q(w, .95), 1) if w else None, worst_closed_day_max=round(max(w), 1) if w else None)


def trial_classes(name):
    M = merged(); S, F1, O, N, C = M.engines(); guard = S.CANDIDATES[name]['guard']

    class NoGuard(N.make_ftmo1(True)):                   # exactly merged.f1u
        def reject_reason(self, row, t, risk_, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            return C.unguarded_reject(self, row, t, margin)
    return S, F1, O, C, guard, (F1.Profile if guard else NoGuard)


def job(kind, name, risk):
    S, F1, O, C, guard, OneStep = trial_classes(name); r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze()
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan); sd = date(2030, 1, 7); day_of = C.E.day_of
    I, L, P, T = C.I, C.L, C.P, C.T; out = dict(kind=kind, name=name, risk=risk, label=LABEL[name])
    paths = PATHS_OVERRIDE or T.PATHS
    if kind in ('two', 'one'):
        rng = random.Random(T.SEED); P1, P2 = [], []; float_day = []; trades = 0; passed = 0; breached = 0
        for _ in range(paths):
            ev = T.bootstrap_events(pool, mondays, index, rng, sd, priority)
            cls = C.Challenge if kind == 'two' else OneStep
            res = P.drive(cls(plan, name, P.start_dict(sd, P.HORIZON), guard, r), ev).result()
            P1.append(phase_row(res['phase1'], res['trades'], 1, day_of)); trades += len(res['trades']); float_day.append(res['max_daily_sampled_equity_loss'])
            if kind == 'two':
                if res['phase2']['status'] != 'pending' or res['phase2'].get('activation_epoch'): P2.append(phase_row(res['phase2'], res['trades'], 2, day_of)) if res['phase1']['status'] == 'passed' else None
                passed += res['outcome'] == 'passed_both' or bool(res['total_elapsed_to_both']); breached += res['outcome'].startswith('failed')
            else:
                passed += res['phase1']['status'] == 'passed'; breached += res['phase1']['status'] == 'failed'
        out.update(paths=paths, pass_all=round(passed / paths, 4), breach_any=round(breached / paths, 4), phase1=phase_summary(P1, paths), phase2=phase_summary(P2, paths) if kind == 'two' else None,
                   floating_day_median=round(med(float_day), 1), floating_day_p95=round(q(float_day, .95), 1), floating_day_max=round(max(float_day), 1), trades_per_path=round(trades / paths, 1))
        if not PATHS_OVERRIDE:
            rec = recorded('CH', name, risk)['mc'] if kind == 'two' else recorded('F1P' if guard else 'F1U', name, risk)['mc']
            want = rec['pass_both_180'] if kind == 'two' else rec['pass_180']
            assert abs(want - out['pass_all']) < 1e-9, ('parity pass', want, out['pass_all']); assert abs(rec['breach'] - out['breach_any']) < 1e-9, ('parity breach', rec['breach'], out['breach_any'])
            out['parity'] = 'exact vs recorded file'
    else:
        days = T.BLOCK_DAYS * I.MC_BLOCKS; rng = random.Random(I.MC_SEED); rows = []; extra = []
        for _ in range(paths):
            ev = P.path_events(pool, mondays, index, rng, sd, priority, I.MC_BLOCKS); s = P.start_dict(sd, days); m = C.Funded(plan, name, s, guard, r)
            for t, k, pr_, key, row, mark in ev:                 # compare.funded_one control flow, unchanged
                if k == 0:
                    m.day_reset(t)
                    if m.dead: break
                elif k in (1, 4): m.closing(row, t)
                elif k == 2: m.mark(row, mark, t)
                else: m.opening(row, t)
                if m.failed and not m.dead: m.dead = ('breach', m.phases[1]['fail_epoch'])
            if not m.dead:
                m.observe(s['horizon_epoch'] - 1e-4)
                if m.failed: m.dead = ('breach', m.phases[1]['fail_epoch'])
            end_epoch = m.dead[1] if m.dead else s['horizon_epoch']; alive = max(1e-9, (end_epoch - s['epoch']) / 86400); pays = [p for p in m.payouts if p['epoch'] <= end_epoch + 1e-6]
            rows.append(dict(start=sd.isoformat(), end=m.dead[0] if m.dead else 'alive', alive_days=round(alive, 2), payouts=len(pays), income=round(sum(p['payout'] for p in pays), 2),
                             first_year_income=round(sum(p['payout'] for p in pays if p['epoch'] < s['epoch'] + 365 * 86400), 2), trades=len(m.trades), first_payout_day=None if not pays else (C.E.day_of(pays[0]['epoch']) - sd).days + 1,
                             first_payout=None if not pays else pays[0]['payout'], eqdd=round(m.max_dd, 1)))
            extra.append(dict(end=rows[-1]['end'], days=int(alive) + 1, trading_days=len({day_of(x['op']) for x in m.trades}), worst=worst_closed(m.trades, day_of), floating=m.max_daily_loss))
        mc = L.summarize(rows, days); bad = [x for x in extra if x['end'] == 'breach']; fro = [x for x in extra if x['end'] == 'frozen']; w = [x['worst'] for x in extra]; f = [x['floating'] for x in extra]
        out.update(paths=paths, income=dict(monthly_median=mc['monthly_income_while_alive_median'], monthly_mean=mc['monthly_income_while_alive_mean'], total_median=mc['income_total_median'], total_mean=mc['income_total_mean'], first_year_median=mc['first_year_income_median'], first_payout_day=mc['first_payout_day_median'], first_payout=mc['first_payout_median'], trades_per_month=mc['trades_per_month_alive_median'], trades_per_weekday=mc['trades_per_weekday_alive_median']),
                   ends=mc['ends'], breach_share=round(len(bad) / paths, 4), frozen_share=round(len(fro) / paths, 4), alive_share=round(sum(x['end'] == 'alive' for x in extra) / paths, 4), median_life=mc['median_days_to_end'],
                   median_days_breach=med([x['days'] for x in bad]), p25_days_breach=q([x['days'] for x in bad], .25), p75_days_breach=q([x['days'] for x in bad], .75), median_trading_days_breach=med([x['trading_days'] for x in bad]),
                   median_days_frozen=med([x['days'] for x in fro]), median_trading_days_frozen=med([x['trading_days'] for x in fro]),
                   worst_closed_day_median=round(med(w), 1), worst_closed_day_p95=round(q(w, .95), 1), worst_closed_day_max=round(max(w), 1), floating_day_median=round(med(f), 1), floating_day_p95=round(q(f, .95), 1), floating_day_max=round(max(f), 1))
        rec = recorded('FU', name, risk)
        if rec and not PATHS_OVERRIDE:
            assert abs(rec['mc']['income_total_mean'] - mc['income_total_mean']) < 0.01, ('parity income', rec['mc']['income_total_mean'], mc['income_total_mean']); out['parity'] = 'exact vs recorded file'
    out['seconds'] = round(time.time() - began)
    tag = '-SMOKE' if PATHS_OVERRIDE else ''
    (H / f'PS-{kind}-{name}-{risk}{tag}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', kind, name, risk, out['seconds'], flush=True)


def runall(workers):
    (H / 'logs').mkdir(exist_ok=True)
    queue = [(k, n, r) for n in ('C9', 'C9U') for k in ('two', 'one') for r in RISKS] + [(k, n, r) for n in ('CUR17', 'FTMO17', 'E10U', 'E10') for k in ('two', 'one') for r in RISKS] + [('fund', n, r) for n in ('C9U', 'C9', 'E10U', 'CUR17', 'FTMO17', 'E10') for r in RISKS]
    pending = [q_ for q_ in queue if not (H / f'PS-{q_[0]}-{q_[1]}-{q_[2]}.json').exists()]; running = []
    print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            j = pending.pop(0); log = open(H / 'logs' / f'ps-{j[0]}-{j[1]}-{j[2]}.log', 'w')
            running.append((j, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *j], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(10)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close(); print('finished' if item[1].returncode == 0 else 'FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'job': job(a[1], a[2], a[3])
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 6)
