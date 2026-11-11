"""Gold Band Wave raw test + FTMO simulations (PLAN.md, frozen before results). Run from AAA EAs/EA store:
  uv run python "<this>" ea        compile (no tester)
  uv run python "<this>" native    GBW, GBW_CLIP, GBW_NOTREND, GBW_RAND + buy and hold (one tester job at a time)
  uv run python "<this>" report    -> RESULTS.json (raw gate, best trades)
  uv run python "<this>" streams   long-history run with intratrade marks (2021-10-06 -> 2026-10-06) for the FTMO engines
  uv run --with pandas --with numpy python "<this>" inputs     INPUTS-GBW.json
  uv run --with pandas --with numpy python "<this>" runall 6   FTMO 2-step / 1-Step, guard and no guard, 0.5 / 0.75 / 1%"""
import copy, gzip, hashlib, importlib.util, json, os, random, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
SRC = H / 'EA/Gold Band Wave Raw EA.mq5'; EX5 = SRC.with_suffix('.ex5'); SYM = 'XAUUSD'; SLUG = 'gold-band-wave'
START, END = '2019-01-01', '2026-11-10'; SPLIT = data_split.research_split(START, END)
WINDOWS = {k: (SPLIT[n]['start'], SPLIT[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
WINDOWS.update(all=(START, END), five_years=('2021-11-10', END), last_year=('2025-11-10', END))
YEARS = [(str(y), (f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else END)) for y in range(2019, 2027)]
dot = lambda s: s.replace('-', '.')  # noqa: E731
BASE = dict(InpRiskPercent='1.0', InpMagic='91110001', InpTrendPeriod='200', InpShortBB='20', InpLongBB='50', InpBBDeviation='2.0', InpSignalPeriod='9', InpATRPeriod='14', InpStopATR='2.0',
            InpRandomDirection='false', InpSeed='1', InpDeviationPoints='50')
V = {'GBW': ({}, 10000), 'GBW_CLIP': (dict(InpRiskPercent='1.5'), 100000), 'GBW_NOTREND': (dict(InpTrendPeriod='0'), 10000), 'GBW_RAND': (dict(InpRandomDirection='true'), 10000)}
RISKS = ('0.50', '0.75', '1.00'); PREFIX = {'ch': 'CH', 'f1g': 'F1P', 'f1u': 'F1U'}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def build_ea():
    editor = harness().TESTER / 'MetaEditor64.exe'; log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{editor}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); t = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); print(t[-600:])
    assert '0 errors, 0 warnings' in t and EX5.stat().st_mtime >= started - 2; print('COMPILED', flush=True)


def native():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxGoldWave'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'gbw.ex5')
    b.CONFIG.update(periods={'all': dot(START)}, end_date=dot(END), currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=21600,
                    expert_dir='CalyxGoldWave', expert_file='gbw.ex5', controls={}, variants={}, common_inputs=BASE, period='H4')
    for key, (inputs, deposit) in V.items():
        b.CONFIG['deposit'] = deposit; b.CONFIG['variants'][key] = {'label': key, 'inputs': inputs}
        for attempt in range(4):
            try:
                b.run_case(SYM, key, 'all'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
        print('DONE', key, flush=True)
    res = buy_hold.run(H, SYM, dict(WINDOWS)); print('BUYHOLD', {k: (v['return_pct'], v['max_dd_pct']) for k, v in res.items()}, flush=True)


def rows_of(key):
    deposit = V[key][1]; T = json.loads(gzip.open(H / 'native' / f'nw-{SYM}-{key}-all' / 'trades.json.gz').read()); bal = float(deposit); rows = []
    for t in sorted(T, key=lambda t: t['close_time']):
        risk = float(V[key][0].get('InpRiskPercent', BASE['InpRiskPercent'])) / 100.0
        rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (risk * bal), net=t['net_profit'], side=t['side'], open_price=t['open_price'], close_price=t['close_price'], exit=t.get('exit_comment') or '')); bal += t['net_profit']
    return rows


def stats(rows, a, b_):
    x = [r for r in rows if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = peak = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; peak = max(peak, eq); dd = max(dd, peak - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b_) - datetime.fromisoformat(a)).days / 30.4375; tot = sum(r['r'] for r in x); wins = [r['r'] for r in x if r['r'] > 0]; losses = [r['r'] for r in x if r['r'] <= 0]
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / (months * 21.74), 3), total_r=round(tot, 2), mean_r=round(tot / max(1, len(x)), 4),
                pf=round(gw / gl, 3) if gl else None, win=round(100 * len(wins) / max(1, len(x)), 1), avg_win_r=round(sum(wins) / max(1, len(wins)), 3), avg_loss_r=round(sum(losses) / max(1, len(losses)), 3),
                closed_dd_r=round(dd, 2), worst_day_r=round(min(days.values()), 2) if days else None, without_best5=round(tot - sum(sorted(days.values(), reverse=True)[:5]), 2),
                longs=sum(r['side'].lower() in ('buy', 'long') for r in x), shorts=sum(r['side'].lower() in ('sell', 'short') for r in x))


def report():
    out = dict(windows=WINDOWS, variants={}, failed=[])
    for k in V:
        d = H / 'native' / f'nw-{SYM}-{k}-all'
        if not (d / 'run.json').exists() or not json.loads((d / 'run.json').read_text(encoding='utf-8')).get('ok'): out['failed'].append(k); continue
        rows = rows_of(k)
        out['variants'][k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, years={y: stats(rows, *v)['total_r'] for y, v in YEARS},
                                  native_return_pct=round(sum(r['net'] for r in rows) / V[k][1] * 100, 2), equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'),
                                  three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104),
                                  best=[dict(open=r['o'], close=r['c'], side=r['side'], r=round(r['r'], 2), usd_at_1500=round(r['r'] * 1500), entry=r['open_price'], exit=r['close_price']) for r in sorted(rows, key=lambda r: -r['r'])[:5]])
    try:
        out['buy_hold'] = {w: {x: buy_hold.load(H, SYM, w)[x] for x in ('return_pct', 'max_dd_pct')} for w in WINDOWS}
    except Exception as e:
        out['buy_hold'] = f'not available: {e}'
    Vv = out['variants']
    if 'GBW' in Vv:
        g = Vv['GBW']; w = g['windows']; t = g['three_way']
        g['gate'] = dict(pf=(w['all']['pf'] or 0) >= 1.15, periods=all(w[x]['total_r'] > 0 for x in ('dev', 'val', 'oos')), without_best5=w['all']['without_best5'] > 0,
                         controls=all(w['all']['total_r'] > Vv[c]['windows']['all']['total_r'] for c in ('GBW_NOTREND', 'GBW_RAND') if c in Vv),
                         mc=t['resample']['red_pct'] <= 5 and t['randomize']['both']['red_pct'] <= 10)
        g['passes'] = all(g['gate'].values())
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('REPORT', json.dumps({k: (v['windows']['all'], v.get('passes')) for k, v in Vv.items()}, default=str)[:3000], flush=True)


def long_runner():
    spec = importlib.util.spec_from_file_location('long_history_runner', PACKAGE / 'Portfolio Long History 2026-10-08/run.py')
    m = importlib.util.module_from_spec(spec); sys.path.insert(0, str(PACKAGE / 'Portfolio Long History 2026-10-08')); spec.loader.exec_module(m); m.ROOT = H; m.n.R = H; return m


def streams():
    m = long_runner(); m.prepare_helpers(); LONG = PACKAGE / 'Portfolio Long History All ORB05 2026-10-14'
    base = next(c for c in json.loads((LONG / 'PLAN.json').read_text(encoding='utf-8-sig'))['cases'] if c['case_id'] == 'ema3-824231b1376b')
    row = copy.deepcopy(base); row.update(slug=SLUG, label='GBW', symbol=SYM, period='H4', source=str(SRC), expert=str(EX5), preset=str(SRC), input_settings=dict(BASE), candidate_overrides={})
    row['production_hashes'] = {str(f): m.n.sha(f) for f in sorted(m.n.closure(SRC) | {EX5})}
    row['case_id'] = f"{SLUG}-{hashlib.sha256(json.dumps([row['source'], row['input_settings']], sort_keys=True).encode()).hexdigest()[:12]}"; row['derived_from'] = base['case_id']
    (H / 'NATIVE_PLAN.json').write_text(json.dumps([row], indent=1), encoding='utf-8')
    state = json.loads((H / 'RUN_STATUS.json').read_text()) if (H / 'RUN_STATUS.json').exists() else dict(complete={}, failed={})
    if row['case_id'] not in state['complete']:
        result = None
        for attempt in range(4):
            try:
                binary, build = m.n.build(row); result = m.n.run_case(row, 'long-' + row['case_id'].split('-')[-1], binary, build); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', flush=True); time.sleep(60)
        assert result is not None, 'stream run failed'
        p = H / 'native' / result['tag'] / 'results.json'
        state['complete'][row['case_id']] = dict(path=str(p), sha256=m.n.sha(p), trades=len(result['trades']), history_quality=result['native']['history_quality'], net=result['native'].get('net_profit'), label='GBW')
        (H / 'RUN_STATUS.json').write_text(json.dumps(state, indent=1), encoding='utf-8')
    print('STREAMS DONE', flush=True)


def engines():
    SEL = PACKAGE / 'Prop Portfolio Selection 2026-11-03'
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py'); F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S; O = F1.O; N = F1.N; C = F1.C; S.R = H; F1.R = H

    def setup(name):
        data = json.loads((H / 'INPUTS-GBW.json').read_text(encoding='utf-8')); plan = S.T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
        plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
        events = S.E.master_events(plan, data); return data, plan, events, [x[0] for x in events]
    S.setup = setup
    S.CANDIDATES['GBW'] = dict(label='Gold Band Wave, guarded', guard=True, risks=RISKS, members=None); S.CANDIDATES['GBWU'] = dict(label='Gold Band Wave, no guard', guard=False, risks=RISKS, members=None)
    return S, F1, O, N, C


def build_inputs():
    S, *_ = engines(); P = S.P; PR = S.PR; begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END)
    cands, info = S.member_candidates(SLUG, ('new', 'GBW'), begin, end, {}, S.sources())
    data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=[P.DATA_START.isoformat(), P.DATA_END.isoformat()])
    (H / 'INPUTS-GBW.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8'); print('INPUTS', len(cands), info, flush=True)


def f1u(name, risk):
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
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk)}[kind]()


def runall(workers):
    (H / 'logs').mkdir(exist_ok=True)
    queue = [(k, n, r) for r in RISKS for k, n in (('ch', 'GBW'), ('ch', 'GBWU'), ('f1g', 'GBW'), ('f1u', 'GBWU'))]
    pending = [q for q in queue if not (H / f'{PREFIX[q[0]]}-{q[1]}-{q[2]}.json').exists()]; running = []; print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            q = pending.pop(0); log = open(H / 'logs' / f"{'-'.join(q)}.log", 'w')
            running.append((q, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *q], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(5)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close(); print('finished' if item[1].returncode == 0 else 'FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'job': job(a[1], a[2], a[3])
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 6)
    else: {'ea': build_ea, 'native': native, 'report': report, 'streams': streams, 'inputs': build_inputs}[a[0]]()
