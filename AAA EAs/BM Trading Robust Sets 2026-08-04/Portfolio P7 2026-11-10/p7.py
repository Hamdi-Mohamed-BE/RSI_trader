"""Owner 2026-11-10: portfolio P7 = Vault Break + Overnight Bias ORB (US100, video ideas), Nasdaq 5M (deployed REPLACE build, DI OFF), EMA3, ORB Volume Profile,
XAU RSI VWAP (gold) and Gold Band Wave. FTMO 2-step and 1-Step, guard and no guard, 0.5 / 0.75 / 1%, plus every EA one by one. Frozen engines, $100k, 2021-10-07 -> 2026-10-06 streams.
Stages (run from AAA EAs/EA store):
  uv run --with pandas --with numpy python "<this>" streams      long-history runs with intratrade marks for the four new pieces (tester)
  uv run --with pandas --with numpy python "<this>" inputs       INPUTS-P7.json + one INPUTS file per EA
  uv run --with pandas --with numpy python "<this>" runall 5     FTMO jobs
  uv run --with pandas --with numpy python "<this>" report       -> RESULTS.json, RESULTS.md (portfolio + per EA, all years native + FTMO)"""
import collections, copy, gzip, hashlib, importlib.util, json, os, random, subprocess, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import data_split, robustness  # noqa: E402
SEL = PACKAGE / 'Prop Portfolio Selection 2026-11-03'; LONG = PACKAGE / 'Portfolio Long History All ORB05 2026-10-14'
VIDEO = PACKAGE / 'Video ORB VWAP Ideas Raw 2026-11-09'; GOLD = PACKAGE / 'Gold Band Wave Raw 2026-11-10'; CARRY = PACKAGE / 'Nasdaq 5M Carry Fix 2026-11-09'
DEPLOY_SRC = PACKAGE / 'Nasdaq 5M Carry Replace Deployment 2026-11-09/EA/Nasdaq 5M DI Wide ATR EA.mq5'
NAS = 'nasdaq-5m-candle-momentum'
# new piece: (label, slug, template case, symbol, period, source, inputs)
VIDEO_COMMON = dict(InpRiskPercent='1.0', InpSeed='1', InpServerUtcOffsetHours='0', InpUseBias='true', InpRandomDirection='false', InpMagic='91109001', InpDeviationPoints='50')


def edge_nasdaq():
    m = json.loads((PACKAGE / '_00 Live profiles/Packages/Edge10/Package.json').read_text(encoding='utf-8-sig'))
    i = {k: str(v) for k, v in next(x for x in m['entries'] if x['key'] == NAS)['inputs'].items() if not k.startswith('InpPortfolio')}
    i.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false', InpRequireDIAgreement='false'); return i


GBW_INPUTS = dict(InpRiskPercent='1.0', InpMagic='91110001', InpTrendPeriod='200', InpShortBB='20', InpLongBB='50', InpBBDeviation='2.0', InpSignalPeriod='9', InpATRPeriod='14', InpStopATR='2.0', InpRandomDirection='false', InpSeed='1', InpDeviationPoints='50')
NEW = {'VAULT': ('vault-break', 'nasdaq-5m-candle-momentum-0fba68cc8a1c', 'USTEC', 'M30', VIDEO / 'EA/Video Ideas Raw EA.mq5', dict(VIDEO_COMMON, InpStrategy='2')),
       'ONB': ('overnight-bias-orb', 'nasdaq-5m-candle-momentum-0fba68cc8a1c', 'USTEC', 'M15', VIDEO / 'EA/Video Ideas Raw EA.mq5', dict(VIDEO_COMMON, InpStrategy='4')),
       'NAS_REPLACE': (NAS, 'nasdaq-5m-candle-momentum-0fba68cc8a1c', 'USTEC', 'M5', DEPLOY_SRC, None),
       'GBW': ('gold-band-wave', 'ema3-824231b1376b', 'XAUUSD', 'H4', GOLD / 'EA/Gold Band Wave Raw EA.mq5', GBW_INPUTS)}
OLD = {'ema3': 'INPUTS-FTMO17.json', 'xau-rsi-vwap': 'INPUTS-FTMO17.json', 'orb-volume-profile': 'INPUTS-FULL.json'}
EAS = ['vault-break', 'overnight-bias-orb', NAS, 'ema3', 'orb-volume-profile', 'xau-rsi-vwap', 'gold-band-wave']
LABEL = {'vault-break': 'Vault Break (US100)', 'overnight-bias-orb': 'Overnight Bias ORB (US100)', NAS: 'Nasdaq 5M REPLACE, DI OFF', 'ema3': 'EMA3 (gold)', 'orb-volume-profile': 'ORB Volume Profile (gold)',
         'xau-rsi-vwap': 'RSI VWAP (gold)', 'gold-band-wave': 'Gold Band Wave'}
RISKS = ('0.50', '0.75', '1.00'); PREFIX = {'ch': 'CH', 'f1g': 'F1P', 'f1u': 'F1U', 'fu': 'FU'}
# Owner 2026-11-10: P4 = the four kept EAs, FTMO 2-step / 1-Step / funded at 0.5 / 0.75 / 1 / 1.5 / 2 %, guard and no guard. 1.5 and 2 % are added to the frozen engines'
# risk table; every limit of the guarded model scales with the chosen risk, so above the installers' 2% entry cap the guarded rows are a model, not a built guard.
P4_EAS = ['overnight-bias-orb', NAS, 'ema3', 'gold-band-wave']; P4_RISKS = ('0.50', '0.75', '1.00', '1.50', '2.00')


def long_runner():
    spec = importlib.util.spec_from_file_location('long_history_runner', PACKAGE / 'Portfolio Long History 2026-10-08/run.py')
    m = importlib.util.module_from_spec(spec); sys.path.insert(0, str(PACKAGE / 'Portfolio Long History 2026-10-08')); spec.loader.exec_module(m); m.ROOT = H; m.n.R = H; return m


def streams():
    m = long_runner(); m.prepare_helpers(); cases = {c['case_id']: c for c in json.loads((LONG / 'PLAN.json').read_text(encoding='utf-8-sig'))['cases']}; rows = []
    for label, (slug, template, sym, per, src, inputs) in NEW.items():
        src = Path(src); ex5 = src.with_suffix('.ex5'); assert ex5.is_file(), ex5
        row = copy.deepcopy(cases[template]); row.update(slug=slug, label=label, symbol=sym, period=per, source=str(src), expert=str(ex5), preset=str(src), input_settings=dict(inputs or edge_nasdaq()), candidate_overrides={})
        row['production_hashes'] = {str(f): m.n.sha(f) for f in sorted(m.n.closure(src) | {ex5})}
        row['case_id'] = f"{slug}-{hashlib.sha256(json.dumps([row['source'], row['input_settings']], sort_keys=True).encode()).hexdigest()[:12]}"; row['derived_from'] = template; rows.append(row)
    (H / 'NATIVE_PLAN.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    state = json.loads((H / 'RUN_STATUS.json').read_text()) if (H / 'RUN_STATUS.json').exists() else dict(complete={}, failed={})
    for row in rows:
        if row['case_id'] in state['complete']: continue
        result = None
        for attempt in range(4):
            try:
                binary, build = m.n.build(row); result = m.n.run_case(row, 'long-' + row['case_id'].split('-')[-1], binary, build); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', row['label'], flush=True); time.sleep(60)
        if result is None: state['failed'][row['case_id']] = row['label']; continue
        p = H / 'native' / result['tag'] / 'results.json'
        state['complete'][row['case_id']] = dict(path=str(p), sha256=m.n.sha(p), trades=len(result['trades']), history_quality=result['native']['history_quality'], net=result['native'].get('net_profit'), label=row['label'])
        (H / 'RUN_STATUS.json').write_text(json.dumps(state, indent=1), encoding='utf-8'); print('DONE', row['label'], len(result['trades']), result['native'].get('net_profit'), flush=True)
    print('STREAMS DONE', flush=True)


def engines():
    spec = importlib.util.spec_from_file_location('f1_profile', SEL / 'f1_profile.py'); F1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F1)
    S = F1.S; O = F1.O; N = F1.N; C = F1.C; S.R = H; F1.R = H

    def setup(name):
        base = name[:-1] if name.endswith('U') else name
        data = json.loads((H / f'INPUTS-{base}.json').read_text(encoding='utf-8')); plan = S.T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
        plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
        events = S.E.master_events(plan, data); return data, plan, events, [x[0] for x in events]
    S.setup = setup
    S.RISKS.update({'1.50': 0.015, '2.00': 0.02})
    for base in ['P4', 'P7'] + [f'S{i}' for i in range(len(EAS))]:
        S.CANDIDATES[base] = dict(label=base, guard=True, risks=RISKS, members=None); S.CANDIDATES[base + 'U'] = dict(label=base + ' no guard', guard=False, risks=RISKS, members=None)
    return S, F1, O, N, C


def build_inputs():
    S, *_ = engines(); P = S.P; PR = S.PR; begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END); src = S.sources(); cache = {}; cands = []
    for label, (slug, *_r) in NEW.items():
        c, info = S.member_candidates(slug, ('new', label), begin, end, cache, src); cands += c; print('NEW', label, len(c), info, flush=True)
    for slug, f in OLD.items():
        data = json.loads((SEL / f).read_text(encoding='utf-8')); c = [x for x in data['candidates'] if x['ea'] == slug]; cands += c; print('OLD', slug, len(c), flush=True)
        assert data['window'] == [P.DATA_START.isoformat(), P.DATA_END.isoformat()]
    assert len({x['id'] for x in cands}) == len(cands) and {x['ea'] for x in cands} == set(EAS), collections.Counter(x['ea'] for x in cands)
    base = dict(year_begin_epoch=begin, year_end_exclusive_epoch=end, window=[P.DATA_START.isoformat(), P.DATA_END.isoformat()])
    (H / 'INPUTS-P7.json').write_text(json.dumps(dict(base, candidates=cands), separators=(',', ':')), encoding='utf-8')
    for i, slug in enumerate(EAS):
        (H / f'INPUTS-S{i}.json').write_text(json.dumps(dict(base, candidates=[x for x in cands if x['ea'] == slug]), separators=(',', ':')), encoding='utf-8')
    print('P7 trades', len(cands), dict(collections.Counter(x['ea'] for x in cands)), flush=True)


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
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk), 'fu': lambda: S.funded(name, risk)}[kind]()


def queue():
    q = [(k, n, r) for r in RISKS for k, n in (('ch', 'P7'), ('ch', 'P7U'), ('f1g', 'P7'), ('f1u', 'P7U'))]
    for i in range(len(EAS)):                                            # every EA alone: guard and no guard, 2-step and 1-Step, at 1% (Gold Band Wave at all three risks: owner asked earlier)
        for r in (RISKS if EAS[i] == 'gold-band-wave' else ('1.00',)):
            q += [(k, n, r) for k, n in (('ch', f'S{i}'), ('ch', f'S{i}U'), ('f1g', f'S{i}'), ('f1u', f'S{i}U'))]
    return q


def queue_p4():
    return [(k, n, r) for r in P4_RISKS for k, n in (('ch', 'P4'), ('ch', 'P4U'), ('f1g', 'P4'), ('f1u', 'P4U'), ('fu', 'P4'), ('fu', 'P4U'))]


def build_p4():
    d = json.loads((H / 'INPUTS-P7.json').read_text(encoding='utf-8')); d['candidates'] = [x for x in d['candidates'] if x['ea'] in P4_EAS]
    assert {x['ea'] for x in d['candidates']} == set(P4_EAS); (H / 'INPUTS-P4.json').write_text(json.dumps(d, separators=(',', ':')), encoding='utf-8')
    print('P4 trades', len(d['candidates']), dict(collections.Counter(x['ea'] for x in d['candidates'])), flush=True)


def runall(workers, q=None):
    (H / 'logs').mkdir(exist_ok=True)
    pending = [x for x in (q or queue()) if not (H / f'{PREFIX[x[0]]}-{x[1]}-{x[2]}.json').exists()]; running = []; print('queue', len(pending), flush=True)
    while pending or running:
        while pending and len(running) < workers:
            x = pending.pop(0); log = open(H / 'logs' / f"{'-'.join(x)}.log", 'w')
            running.append((x, subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', *x], stdout=log, stderr=subprocess.STDOUT), log))
        time.sleep(5)
        for item in running[:]:
            if item[1].poll() is not None:
                running.remove(item); item[2].close(); print('finished' if item[1].returncode == 0 else 'FAILED', *item[0], flush=True)
    print('QUEUE DONE', flush=True)


# ---------------------------------------------------------------- report: native all-years ledgers (fixed R) + FTMO
def native_rows():
    """Per EA, R = net / 1% of the balance before the trade, from each EA's own full-history native run (not the FTMO stream)."""
    def from_trades(path, deposit=1e4, risk=0.01):
        T = sorted(json.loads(gzip.open(path).read()), key=lambda t: t['close_time']); bal = deposit; out = []
        for t in T:
            out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (risk * bal))); bal += t['net_profit']
        return out
    M = PACKAGE / 'Merged E10 FTMO17 2026-11-05'; src = (M / 'analyze.py').read_text(encoding='utf-8').split('out = dict(native_checks')[0]
    ns = dict(__file__=str(M / 'analyze.py'), __name__='analyze_defs'); exec(compile(src, 'analyze_defs', 'exec'), ns); ALL = ns['ALL']
    old = {k: [dict(o=r['o'].isoformat() if hasattr(r['o'], 'isoformat') else str(r['o']), c=r['c'].isoformat(), r=r['R']) for r in ALL[k]] for k in ('ema3', 'orb-volume-profile', 'xau-rsi-vwap')}
    new = {'vault-break': from_trades(VIDEO / 'native/nw-USTEC-VAULT-all/trades.json.gz'), 'overnight-bias-orb': from_trades(VIDEO / 'native/nw-USTEC-ONB-all/trades.json.gz'),
           NAS: from_trades(CARRY / 'native/nw-USTEC-REPLACE-all/trades.json.gz'), 'gold-band-wave': from_trades(GOLD / 'native/nw-XAUUSD-GBW-all/trades.json.gz')}
    return {**old, **new}


def stats(x, a, b):
    x = sorted((r for r in x if a <= r['o'][:10] < b), key=lambda r: r['c']); gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = pk = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375; tot = sum(r['r'] for r in x)
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / (months * 21.74), 3), total_r=round(tot, 1), pf=round(gw / gl, 3) if gl else None,
                win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 1), worst_day_r=round(min(days.values()), 2) if days else None)


def report():
    split = data_split.research_split('2019-01-01', '2026-11-10')
    W = {k: (split[n]['start'], split[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
    W.update(all=('2019-01-01', '2026-11-10'), stream=('2021-10-07', '2026-10-06'), last_year=('2025-11-10', '2026-11-10'))
    R = native_rows(); port = [r for k in EAS for r in R[k]]
    out = dict(windows=W, portfolio=dict(native={w: stats(port, *v) for w, v in W.items()}), eas={})
    seq = [r['r'] for r in sorted(port, key=lambda r: r['c'])]; tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
    out['portfolio']['mc'] = dict(resample=tw['resample']['red_pct'], randomize=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct'])
    out['portfolio']['years'] = {str(y): stats(port, f'{y}-01-01', f'{y + 1}-01-01')['total_r'] for y in range(2019, 2027)}

    def mc(prefix, name, r):
        f = H / f'{prefix}-{name}-{r}.json'
        return json.loads(f.read_text(encoding='utf-8'))['mc'] if f.exists() else None
    out['portfolio']['ftmo'] = {r: dict(two_guard=mc('CH', 'P7', r), two_free=mc('CH', 'P7U', r), one_guard=mc('F1P', 'P7', r), one_free=mc('F1U', 'P7U', r)) for r in RISKS}
    for i, k in enumerate(EAS):
        out['eas'][k] = dict(label=LABEL[k], native={w: stats(R[k], *v) for w, v in W.items()},
                             ftmo={r: dict(two_guard=mc('CH', f'S{i}', r), two_free=mc('CH', f'S{i}U', r), one_guard=mc('F1P', f'S{i}', r), one_free=mc('F1U', f'S{i}U', r)) for r in RISKS})
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('REPORT written', flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'job': job(a[1], a[2], a[3])
    elif a[0] == 'runall': runall(int(a[1]) if len(a) > 1 else 5)
    elif a[0] == 'p4': build_p4(); runall(int(a[1]) if len(a) > 1 else 6, queue_p4())
    else: {'streams': streams, 'inputs': build_inputs, 'report': report}[a[0]]()
