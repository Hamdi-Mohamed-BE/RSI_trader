"""Nasdaq 5M, all versions + candle-colour entry (PLAN.md, frozen before results). Stages, run from AAA EAs/EA store:
  uv run python "<this>" native    compile the research EA, parity, 8 versions x dev / val / oos / all + control + buy and hold on USTEC
  uv run python "<this>" streams   the audited long-history runs with intratrade marks (2021-10-06 -> 2026-10-06), then INPUTS-<V>.json
  uv run --with pandas --with numpy python "<this>" runall 9       FTMO 2-step, 1-Step and funded for every version, guard and no guard
  python analyze.py                tables"""
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split  # noqa: E402
SRC = H / 'EA/Nasdaq 5M Candle Rule Research EA.mq5'; EX5 = SRC.with_suffix('.ex5'); SYM = 'USTEC'
SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
           'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'all': ('2019-01-01', '2026-11-01')}
ATR6 = dict(InpStopMode='0', InpInitialStopATR='6.0'); P60 = dict(InpStopMode='2', InpInitialStopATR='4.0', InpInitialStopPercent='0.60')
ON, OFF = dict(InpRequireDIAgreement='true'), dict(InpRequireDIAgreement='false')
VERSIONS = {'EMA_ATR6_DION': {**ATR6, **ON, 'InpDirectionRule': '0'}, 'EMA_ATR6_DIOFF': {**ATR6, **OFF, 'InpDirectionRule': '0'}, 'EMA_P60_DION': {**P60, **ON, 'InpDirectionRule': '0'},
            'EMA_P60_DIOFF': {**P60, **OFF, 'InpDirectionRule': '0'}, 'CANDLE_ATR6_DION': {**ATR6, **ON, 'InpDirectionRule': '1'}, 'CANDLE_ATR6_DIOFF': {**ATR6, **OFF, 'InpDirectionRule': '1'},
            'CANDLE_P60_DION': {**P60, **ON, 'InpDirectionRule': '1'}, 'CANDLE_P60_DIOFF': {**P60, **OFF, 'InpDirectionRule': '1'}}
# Addendum 1 (owner 2026-11-05, before any result): the old fixed version: stop 4 x ATR, fixed 2.5R target, no trailing, closed at session end; plus the old DYNAMIC 50-20 preset.
FIXED = dict(InpStopMode='0', InpInitialStopATR='4.0', InpUseFixedTarget='true', InpRewardRisk='2.5', InpUseATRTrailing='false', InpCloseAtSessionEnd='true')
VERSIONS.update({'EMA_FIXED_DION': {**FIXED, **ON, 'InpDirectionRule': '0'}, 'EMA_FIXED_DIOFF': {**FIXED, **OFF, 'InpDirectionRule': '0'},
                 'CANDLE_FIXED_DION': {**FIXED, **ON, 'InpDirectionRule': '1'}, 'CANDLE_FIXED_DIOFF': {**FIXED, **OFF, 'InpDirectionRule': '1'},
                 'EMA_DYN_DIOFF': dict(InpStopMode='0', InpInitialStopATR='4.0', InpCloseAtSessionEnd='true', InpUseDynamicTrailingSL='true', InpDynamicTriggerFraction='0.5', InpDynamicLockFraction='0.2', **OFF, InpDirectionRule='0')})
CONTROL = {'CONTROL_ATR6_DIOFF': {**ATR6, **OFF, 'InpDirectionRule': '2'}}
RISKS = ('0.50', '0.75', '1.00'); PREFIX = {'ch': 'CH', 'f1g': 'F1P', 'f1u': 'F1U', 'fu': 'FU'}


def base_inputs():
    item = next(i for i in json.loads((PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8-sig')) if i['label'] == 'Nasdaq 5M Candle Momentum')
    inputs = {k: str(v) for k, v in item['inputs'].items()}; inputs.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false'); return inputs, item


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def compile_ea(b):
    log = SRC.with_suffix('.compile.log')
    subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    raw = log.read_bytes(); text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in text, text[-1500:]
    print('COMPILED', b.sha(EX5)[:12], flush=True)


def native():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; compile_ea(b); inputs, _ = base_inputs()
    dest = b.TESTER / 'MQL5/Experts/CalyxNasCandle'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'nas-candle.ex5')
    dot = lambda s: s.replace('-', '.')  # noqa: E731
    b.CONFIG.update(periods={k: dot(a) for k, (a, _) in WINDOWS.items()}, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400,
                    expert_dir='CalyxNasCandle', expert_file='nas-candle.ex5', controls={}, period='M5', common_inputs=inputs, variants={k: {'label': k, 'inputs': v} for k, v in {**VERSIONS, **CONTROL}.items()})

    def run(v, w):
        b.CONFIG['end_date'] = dot(WINDOWS[w][1])
        for attempt in range(4):                         # the tester agent can time out at startup when the CPU is busy
            try:
                b.run_case(SYM, v, w); return
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', v, w, flush=True); time.sleep(60)
    for w in ('all', 'oos', 'val', 'dev'):
        for v in VERSIONS: run(v, w)
    run('CONTROL_ATR6_DIOFF', 'all')
    print('NATIVE DONE', flush=True)
    res = buy_hold.run(H, SYM, {'oos': WINDOWS['oos'], 'val': WINDOWS['val'], 'dev': WINDOWS['dev'], 'all': WINDOWS['all'], '5y': ('2021-11-01', '2026-11-01'), '3y': ('2023-11-01', '2026-11-01'),
                                '1y': ('2025-11-01', '2026-11-01'), '6m': ('2026-05-01', '2026-11-01')})
    print('BUYHOLD', {k: (v['return_pct'], v['max_dd_pct']) for k, v in res.items()}, flush=True)


def long_runner():
    spec = importlib.util.spec_from_file_location('long_history_runner', PACKAGE / 'Portfolio Long History 2026-10-08/run.py')
    m = importlib.util.module_from_spec(spec); sys.path.insert(0, str(PACKAGE / 'Portfolio Long History 2026-10-08')); spec.loader.exec_module(m); m.ROOT = H; m.n.R = H; return m


def streams():
    while not (H / 'SEP_DONE.flag').exists(): time.sleep(30)   # owner 2026-11-05: the short Sep-to-today comparison uses the tester first
    m = long_runner(); m.prepare_helpers(); LONG = PACKAGE / 'Portfolio Long History All ORB05 2026-10-14'
    plan = json.loads((LONG / 'PLAN.json').read_text(encoding='utf-8-sig')); base = next(c for c in plan['cases'] if c['case_id'] == 'nasdaq-5m-candle-momentum-0fba68cc8a1c'); rows = []
    for label, changes in VERSIONS.items():
        row = copy.deepcopy(base); row['input_settings'].update(changes); row['source'] = str(SRC); row['expert'] = str(EX5)
        row['production_hashes'] = {str(f): m.n.sha(f) for f in sorted(m.n.closure(SRC) | {EX5, Path(row['preset'])})}
        sig = hashlib.sha256(json.dumps([row['source'], row['input_settings']], sort_keys=True).encode()).hexdigest()[:12]
        row['case_id'] = f"{row['slug']}-{sig}"; row['derived_from'] = base['case_id']; row['label'] = label; rows.append(row)
    (H / 'NATIVE_PLAN.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    state = json.loads((H / 'RUN_STATUS.json').read_text()) if (H / 'RUN_STATUS.json').exists() else dict(complete={}, failed={})
    for row in rows:
        if row['case_id'] in state['complete']: continue
        for attempt in range(4):
            try:
                binary, build = m.n.build(row); result = m.n.run_case(row, 'long-' + row['case_id'].split('-')[-1], binary, build); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', row['label'], flush=True); time.sleep(60); result = None
        if result is None: continue
        p = H / 'native' / result['tag'] / 'results.json'
        state['complete'][row['case_id']] = dict(path=str(p), sha256=m.n.sha(p), trades=len(result['trades']), history_quality=result['native']['history_quality'], net=result['native'].get('net_profit'), label=row['label'])
        (H / 'RUN_STATUS.json').write_text(json.dumps(state, indent=1), encoding='utf-8'); print('DONE', row['label'], len(result['trades']), result['native'].get('net_profit'), flush=True)
    print('STREAMS DONE', flush=True)


def engines():
    SEL = PACKAGE / 'Prop Portfolio Selection 2026-11-03'
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py'); F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S; O = F1.O; N = F1.N; C = F1.C; S.R = H; F1.R = H

    def setup(name):
        data = json.loads((H / f"INPUTS-{name.removesuffix('U')}.json").read_text(encoding='utf-8')); plan = S.T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
        plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
        events = S.E.master_events(plan, data); return data, plan, events, [x[0] for x in events]
    S.setup = setup
    for v in VERSIONS:
        S.CANDIDATES[v] = dict(label=v, guard=True, risks=RISKS, members=None); S.CANDIDATES[v + 'U'] = dict(label=v + ' no guard', guard=False, risks=RISKS, members=None)
    return S, F1, O, N, C


def build_inputs():
    S, *_ = engines(); P = S.P; PR = S.PR; begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END); src = S.sources(); cache = {}
    for v in VERSIONS:
        cands, info = S.member_candidates(S.NAS, ('new', v), begin, end, cache, src)
        data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=[P.DATA_START.isoformat(), P.DATA_END.isoformat()])
        (H / f'INPUTS-{v}.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8'); print(v, len(cands), flush=True)
    ref = {x['id']: x for x in json.loads((PACKAGE / 'Prop Portfolio Selection 2026-11-03/INPUTS-FTMO17.json').read_text(encoding='utf-8'))['candidates'] if x['ea'] == S.NAS}
    mine = {x['id']: x for x in json.loads((H / 'INPUTS-EMA_ATR6_DION.json').read_text(encoding='utf-8'))['candidates']}
    # Same trades, opens, closes and stops; only the tester's swap table has drifted since 2026-11-03 (-2135.7 -> -2025.1 per lot in total) and lots differ by 0.01 from the compounding path. Production parity itself is the all-years ledger check in analyze.
    same = sorted(ref) == sorted(mine) and all(ref[k]['op'] == mine[k]['op'] and ref[k]['cl'] == mine[k]['cl'] and abs(ref[k]['unit_gross'] - mine[k]['unit_gross']) < 0.05 for k in ref)
    print('PARITY stream vs FTMO17 Nasdaq', same, len(ref), len(mine), flush=True); assert same


def f1u(name, risk):
    from datetime import date, timedelta
    import random
    S, F1, O, N, C = engines()

    class NoGuard(N.make_ftmo1(True)):
        def reject_reason(self, row, t, risk_, margin):
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'passed'
            if self.balance >= self.target() - 1e-8 and self.best_day_ok(): return 'target_entry_gate_await_flat'
            return C.unguarded_reject(self, row, t, margin)
    r = S.RISKS[risk]; S.E.verify_freeze(); data, plan, events, epochs = S.setup(name); pool, mondays, index, priority = C.mc_pool(data, plan); rows = []; d = S.P.DATA_START
    while d + timedelta(days=S.P.HORIZON) <= S.P.DATA_END:
        if d.weekday() < 5: rows.append(O.one(NoGuard, plan, name, False, r, d, S.P.window(events, epochs, S.P.midnight(d), S.P.midnight(d + timedelta(days=S.P.HORIZON)))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, guard=False, hist={s: O.summarize([x for x in rows if a <= date.fromisoformat(x['start']) < b]) for s, (a, b) in S.SEG.items()})
    rng = random.Random(S.T.SEED); sd = date(2030, 1, 7)
    out['mc'] = O.summarize([O.one(NoGuard, plan, name, False, r, sd, S.T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(S.T.PATHS)])
    (H / f'F1U-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')


def job(kind, name, risk):
    if kind == 'f1u': return f1u(name, risk)
    S, F1, *_ = engines()
    {'ch': lambda: S.challenge(name, risk), 'fu': lambda: S.funded(name, risk), 'f1g': lambda: F1.main(name, risk)}[kind]()


def runall(workers):
    (H / 'logs').mkdir(exist_ok=True)
    queue = [(k, n, r) for r in RISKS for v in VERSIONS for k, n in (('ch', v), ('ch', v + 'U'), ('f1g', v), ('f1u', v + 'U'), ('fu', v), ('fu', v + 'U'))]
    pending = [q for q in queue if not (H / f'{PREFIX[q[0]]}-{q[1]}-{q[2]}.json').exists()]; running = []; print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            q = pending.pop(0); log = open(H / 'logs' / f"{'-'.join(q)}.log", 'w')
            running.append((q, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *q], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(5)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close()
                if item[1].returncode: print('FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'native': native()
    elif a[0] == 'streams': streams()
    elif a[0] == 'inputs': build_inputs()
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 9)
    elif a[0] == 'job': job(a[1], a[2], a[3])
