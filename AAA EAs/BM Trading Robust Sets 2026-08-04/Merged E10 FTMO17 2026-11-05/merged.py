"""Owner 2026-11-05: "what happen when we merge the E10 and FTMO 17 all together? show combined profile results with and without guard; do full
results and full monte carlo simulation for all the years". M22 = the FTMO17 stream + the five E10-only bots (ORB VP Volume Confirmed, ORB VP,
Sell Nasdaq 15min, XAU Regime Switch, XAU Elliott Wave) from INPUTS-FULL.json. Overlapping bots run once; 3 Way Gold keeps all modules as in
FTMO17 (market entries; it contains E10's breakout module). Frozen prop_select / compare / sizes / core engines, weekday starts, MC pools and
seeds, $100k, window 2021-10-07 -> 2026-10-06 (the streams with intratrade marks):
  ch  <name> <risk>  FTMO 2-step (prop_select.challenge)                                 -> CH-<name>-<risk>.json
  f1g <name> <risk>  FTMO 1-Step, the built ftmo 1_step guard (f1_profile.main)           -> F1P-<name>-<risk>.json
  f1u <name> <risk>  FTMO 1-Step, NO guard: firm rules + broker margin only               -> F1U-<name>-<risk>.json
  fu  <name> <risk>  FTMO funded income, 36 m MC (prop_select.funded)                      -> FU-<name>-<risk>.json
names: M22 / E10 / FTMO17 = guarded model; M22U / E10U / CUR17 = no guard (compare.py unguarded model, lots rounded up).
  build | runall [workers]     build INPUTS-M22.json | run the whole queue, skipping finished outputs
Run from EA store: uv run --with pandas --with numpy python "<this>" runall 10"""
import collections, importlib.util, json, random, subprocess, sys, time
from datetime import date, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'; E10D = H.parent / 'Edge Portfolio E10 2026-11-04'
EXTRA = {'orb-volume-profile-volume-confirmed', 'orb-volume-profile', 'sell-nasdaq-15min', 'xau-regime-switch', 'xau-elliott-wave-1-2-3'}
STREAM = {'M22': H / 'INPUTS-M22.json', 'M22U': H / 'INPUTS-M22.json', 'E10': E10D / 'INPUTS-E10.json', 'E10U': E10D / 'INPUTS-E10.json',
          'FTMO17': SEL / 'INPUTS-FTMO17.json', 'CUR17': SEL / 'INPUTS-FTMO17.json', 'E11': H / 'INPUTS-E11.json', 'E11U': H / 'INPUTS-E11.json', 'C9': H / 'INPUTS-C9.json', 'C9U': H / 'INPUTS-C9.json'}   # E11 = E10 + Gold Overnight VA (owner 2026-11-05)
RISKS = ('0.50', '0.75', '1.00')
QUEUE = ([('ch', n, r) for n in ('M22', 'M22U') for r in RISKS] + [('f1g', 'M22', r) for r in RISKS] + [('f1u', 'M22U', r) for r in RISKS]
         + [('ch', 'E10U', r) for r in RISKS] + [('ch', 'CUR17', '1.00'), ('ch', 'E10', '0.75'), ('ch', 'FTMO17', '0.75')]
         + [('f1u', n, r) for n in ('E10U', 'CUR17') for r in RISKS] + [('fu', n, r) for n in ('M22', 'M22U') for r in RISKS])
QUEUE_E11 = [(k, n, r) for r in RISKS for k, n in (('ch', 'E11'), ('ch', 'E11U'), ('f1g', 'E11'), ('f1u', 'E11U'), ('fu', 'E11'), ('fu', 'E11U'))]
QUEUE_C9 = [(k, n, r) for r in RISKS for k, n in (('ch', 'C9'), ('ch', 'C9U'), ('f1g', 'C9'), ('f1u', 'C9U'), ('fu', 'C9'), ('fu', 'C9U'))]   # Core 9, owner 2026-11-05
PREFIX = {'ch': 'CH', 'f1g': 'F1P', 'f1u': 'F1U', 'fu': 'FU'}


def build():
    full = json.loads((SEL / 'INPUTS-FULL.json').read_text(encoding='utf-8')); ftmo = json.loads((SEL / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    assert all(full[k] == ftmo[k] for k in ('year_begin_epoch', 'year_end_exclusive_epoch', 'window'))
    c = ftmo['candidates'] + [x for x in full['candidates'] if x['ea'] in EXTRA]
    assert len({x['id'] for x in c}) == len(c)
    ftmo['candidates'] = c; (H / 'INPUTS-M22.json').write_text(json.dumps(ftmo, separators=(',', ':')), encoding='utf-8')
    print('M22 trades', len(c), dict(collections.Counter(x['ea'] for x in c)))


def build_e11():
    e10 = json.loads((E10D / 'INPUTS-E10.json').read_text(encoding='utf-8')); ftmo = json.loads((SEL / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    assert all(e10[k] == ftmo[k] for k in ('year_begin_epoch', 'year_end_exclusive_epoch', 'window'))
    e10['candidates'] += [x for x in ftmo['candidates'] if x['ea'] == 'gold-overnight-value-area']; assert len({x['id'] for x in e10['candidates']}) == len(e10['candidates'])
    (H / 'INPUTS-E11.json').write_text(json.dumps(e10, separators=(',', ':')), encoding='utf-8'); print('E11 trades', len(e10['candidates']), flush=True)


def build_c9():
    # Core 9 (core_pick.py list + XAU RSI VWAP, owner 2026-11-05): the FTMO17 stream members plus Sell Nasdaq and ORB VP Volume Confirmed from INPUTS-FULL.json; 3 Way Gold breakout module only, market variant.
    full = json.loads((SEL / 'INPUTS-FULL.json').read_text(encoding='utf-8')); ftmo = json.loads((SEL / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))
    a = {'nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', '3-way-gold#930930101', 'ema3', 'xau-squeeze-momentum-standard', 'us100-selective-orb-v3', 'xau-rsi-vwap'}; b = {'sell-nasdaq-15min', 'orb-volume-profile-volume-confirmed'}
    c = [x for x in ftmo['candidates'] if x['ea'] in a] + [x for x in full['candidates'] if x['ea'] in b]; assert len({x['id'] for x in c}) == len(c) and {x['ea'] for x in c} == a | b
    ftmo['candidates'] = c; (H / 'INPUTS-C9.json').write_text(json.dumps(ftmo, separators=(',', ':')), encoding='utf-8'); print('C9 trades', len(c), dict(collections.Counter(x['ea'] for x in c)), flush=True)


def engines():
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py')
    F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S; O = F1.O; N = F1.N; C = F1.C

    def setup(name):                                     # prop_select.setup, reading each stream from its own folder
        data = json.loads(STREAM[name].read_text(encoding='utf-8'))
        plan = S.T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
        plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
        events = S.E.master_events(plan, data)
        return data, plan, events, [x[0] for x in events]
    S.setup = setup; S.R = H; F1.R = H
    S.CANDIDATES.update(M22=dict(label='Merged 22, guarded', guard=True, risks=RISKS, members=None), M22U=dict(label='Merged 22, no guard', guard=False, risks=RISKS, members=None),
                        E10=dict(label='Edge 10, guarded', guard=True, risks=RISKS, members=None), E10U=dict(label='Edge 10, no guard', guard=False, risks=RISKS, members=None),
                        C9=dict(label='Core 9, guarded', guard=True, risks=RISKS, members=None), C9U=dict(label='Core 9, no guard', guard=False, risks=RISKS, members=None),
                        E11=dict(label='E10 + Gold Overnight, guarded', guard=True, risks=RISKS, members=None), E11U=dict(label='E10 + Gold Overnight, no guard', guard=False, risks=RISKS, members=None))
    return S, F1, O, N, C


def f1u(name, risk):
    S, F1, O, N, C = engines()

    class NoGuard(N.make_ftmo1(True)):                   # FTMO 1-Step firm rules only (no Calyx guard)
        def reject_reason(self, row, t, risk_, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            return C.unguarded_reject(self, row, t, margin)

    cfg = S.CANDIDATES[name]; r = S.RISKS[risk]; began = time.time(); S.E.verify_freeze(); assert cfg['guard'] is False
    data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan)
    rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append(O.one(NoGuard, plan, name, False, r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, guard=False, rules='FTMO 1-Step firm rules only', hist={s: O.summarize([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = O.summarize([O.one(NoGuard, plan, name, False, r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    out['seconds'] = round(time.time() - began)
    (H / f'F1U-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done f1u', name, risk, out['seconds'], flush=True)


def job(kind, name, risk):
    if kind == 'f1u': return f1u(name, risk)
    S, F1, *_ = engines()
    {'ch': lambda: S.challenge(name, risk), 'fu': lambda: S.funded(name, risk), 'f1g': lambda: F1.main(name, risk)}[kind]()


def runall(workers, queue=None):
    (H / 'logs').mkdir(exist_ok=True)
    pending = [q for q in (queue or QUEUE) if not (H / f'{PREFIX[q[0]]}-{q[1]}-{q[2]}.json').exists()]; running = []
    print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            q = pending.pop(0); log = open(H / 'logs' / f'{q[0]}-{q[1]}-{q[2]}.log', 'w')
            running.append((q, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *q], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(10)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close(); print('finished' if item[1].returncode == 0 else 'FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'build': build()
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 10)
    elif a[0] == 'c9': build_c9(); runall(int(a[1]) if len(a) > 1 else 5, QUEUE_C9)
    elif a[0] == 'e11': build_e11(); runall(int(a[1]) if len(a) > 1 else 5, QUEUE_E11)
    elif a[0] == 'job': job(a[1], a[2], a[3])
