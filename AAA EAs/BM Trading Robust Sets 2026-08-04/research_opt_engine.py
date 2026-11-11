"""Shared staged-optimisation engine (owner 2026-11-10: Vault Break, Overnight Bias ORB, Gold Band Wave), the method of USDJPY London Optimization 2026-11-05/opt.py:
parity with the raw ledger -> staged development search (top 3 per stage, native Model 1 screen) -> plateau (>= 70% of one-step neighbours profitable on dev) ->
Model 4 confirmation of the finalists on dev -> validation once (Model 4) -> OOS once (Model 4) -> three-way Monte Carlo on all years. Every run in <study>/RUNS.jsonl.
Split: data_split.research_split('2019-01-01', '2026-11-11'); development starts at the symbol's first history day. A study calls run_study(Spec)."""
import gzip, hashlib, importlib.util, json, os, shutil, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
PACKAGE = Path(__file__).resolve().parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
SPLIT = data_split.research_split('2019-01-01', '2026-11-11')
dot = lambda s: s.replace('-', '.')  # noqa: E731
BOOLS = ('true', 'false')


def run_study(S):
    """S: H, EX5, SYM, FIRST (history start), RAW (raw all-years ledger dir), RAW_END, BASE, STAGES, NEIGHBOUR, PERIOD(cfg)->'M15'|..., EXPERT_DIR"""
    W = {'dev': (S.FIRST, SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
         'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': (S.FIRST, '2026-11-11'), 'parity': (S.FIRST, S.RAW_END)}
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = S.H; b.OUT = S.H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    runs = S.H / 'RUNS.jsonl'; DONE = {}
    if runs.exists():
        for line in runs.read_text(encoding='utf-8').splitlines():
            x = json.loads(line); DONE[(x['sig'], x['window'], x['model'])] = x

    def norm(cfg): return {k: (v if v in BOOLS else str(float(v))) for k, v in cfg.items()}
    def signature(cfg): return hashlib.sha256(json.dumps(norm(cfg), sort_keys=True).encode()).hexdigest()[:10]
    def ledger(cfg, window, model): return json.loads(gzip.open(b.OUT / f'nw-{S.SYM}-V{signature(cfg)}m{model}-{window}/trades.json.gz').read())

    def run(cfg, window, model=1, tag=''):
        sig = signature(cfg)
        if (sig, window, model) in DONE: return DONE[(sig, window, model)]
        variant = f'V{sig}m{model}'; b.CONFIG['variants'][variant] = {'label': variant, 'inputs': cfg}; b.CONFIG['common_inputs'] = {}
        b.CONFIG['end_date'] = dot(W[window][1]); b.CONFIG['model'] = model; b.CONFIG['period'] = S.PERIOD(cfg); meta = None
        for _ in range(4):
            try:
                meta = b.run_case(S.SYM, variant, window); break
            except SystemExit:
                time.sleep(60)
        if meta is None:
            print('CASE FAILED', variant, window, flush=True); return None
        d = b.OUT / f'nw-{S.SYM}-{variant}-{window}'; dd = buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz')
        T = json.loads(gzip.open(d / 'trades.json.gz').read()); net = sum(t['net_profit'] for t in T)
        gw = sum(t['net_profit'] for t in T if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in T if t['net_profit'] < 0); nb = norm(S.BASE)
        rec = dict(sig=sig, window=window, model=model, tag=tag, ret=round(net / 100, 2), pf=round(gw / gl, 3) if gl else None, trades=len(T),
                   win=round(100 * sum(t['net_profit'] > 0 for t in T) / max(1, len(T)), 1), dd=dd, score=round((net / 100) / dd, 3) if dd else None,
                   changes={k: v for k, v in cfg.items() if nb.get(k) != norm({k: v})[k]}, flags=meta['journal_flags'])
        DONE[(sig, window, model)] = rec
        with runs.open('a', encoding='utf-8') as f: f.write(json.dumps(rec) + '\n')
        return rec

    def eligible(r): return r and r['pf'] is not None and r['pf'] >= 1.15 and r['trades'] >= S.MIN_TRADES and r['ret'] > 0
    def better(r, base): return r and r['ret'] > 0 and (r['pf'] or 0) >= 1.15 and (r['score'] or -1e9) > (base['score'] or -1e9)

    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts' / S.EXPERT_DIR; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(S.EX5, dest / 'opt.ex5')
    b.CONFIG.update(periods={k: dot(a) for k, (a, _) in W.items()}, deposit=10000, currency='USD', model=1, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400,
                    expert_dir=S.EXPERT_DIR, expert_file='opt.ex5', controls={}, variants={}, period=S.PERIOD(S.BASE))
    run(S.BASE, 'parity', 4, 'parity'); raw = json.loads(gzip.open(S.RAW / 'trades.json.gz').read())
    key = lambda T: [(t['open_time'], t['close_time'], t['side'], t['volume'], round(t['net_profit'], 2)) for t in sorted(T, key=lambda t: (t['open_time'], t['close_time']))]  # noqa: E731
    # 2026-11-10 (Vault parity): the raw runs were made late on 2026-11-09/10 when the tester had only part of the last day; trades opened from the day before the raw file
    # was written are excluded from BOTH ledgers, so parity is checked on the history both runs had. The excluded counts are printed and kept in PARITY.json.
    import datetime as _dt
    cut = min(S.RAW_END, (_dt.date.fromtimestamp((S.RAW / 'trades.json.gz').stat().st_mtime) - _dt.timedelta(days=1)).isoformat())
    mine_all = ledger(S.BASE, 'parity', 4); mine = [t for t in mine_all if t['open_time'] < cut]; raw_c = [t for t in raw if t['open_time'] < cut]
    same = key(mine) == key(raw_c); print('PARITY', same, 'cutoff', cut, len(mine), len(raw_c), 'excluded', len(mine_all) - len(mine), len(raw) - len(raw_c), flush=True)
    (S.H / 'PARITY.json').write_text(json.dumps(dict(identical=same, cutoff_open_before=cut, compared=len(mine), research_excluded=len(mine_all) - len(mine), raw_excluded=len(raw) - len(raw_c),
                                                     net_research=round(sum(t['net_profit'] for t in mine), 2), net_raw=round(sum(t['net_profit'] for t in raw_c), 2)), indent=1), encoding='utf-8')
    if not same:   # 2026-11-11 (GBW): the tester's swap rate changed after the raw run; accept only if every trade's path (times, side, prices, comments) is identical
        P = ('open_time', 'close_time', 'side', 'open_price', 'close_price', 'entry_comment', 'exit_comment'); srt = lambda T: sorted(T, key=lambda t: (t['open_time'], t['close_time']))  # noqa: E731
        A, Bm = srt(raw_c), srt(mine); path = len(A) == len(Bm) and all(all(a[f] == x[f] for f in P) for a, x in zip(A, Bm))
        note = dict(path_identical=path, volume_diffs=sum(a['volume'] != x['volume'] for a, x in zip(A, Bm)), swap_raw=round(sum(t['swap'] for t in A), 2), swap_research=round(sum(t['swap'] for t in Bm), 2))
        print('PARITY path-only', note, flush=True); pj = S.H / 'PARITY.json'; d = json.loads(pj.read_text(encoding='utf-8')); d.update(note, accepted='path identical; cash differs only through swap'); pj.write_text(json.dumps(d, indent=1), encoding='utf-8')
        same = path
    assert same, 'research EA differs from the raw EA'
    b4 = run(S.BASE, 'dev', 4, 'baseline'); b1 = run(S.BASE, 'dev', 1, 'baseline'); print('BASELINE dev model4', b4, 'model1', b1, flush=True)
    top = [S.BASE]
    for name, grid in S.STAGES:
        seen = {}
        for parent in top:
            for change in grid:
                cfg = dict(parent, **change); sig = signature(cfg)
                if sig not in seen: seen[sig] = (cfg, run(cfg, 'dev', 1, name))
        ranked = sorted([v for v in seen.values() if eligible(v[1])], key=lambda v: -(v[1]['score'] or -1e9))
        if ranked: top = [v[0] for v in ranked[:3]]
        print('STAGE', name, len(seen), 'configs; best', [(v[1]['score'], v[1]['ret'], v[1]['pf'], v[1]['trades'], v[1]['win'], v[1]['dd'], v[1]['changes']) for v in ranked[:3]], flush=True)
    (S.H / 'FINALISTS.json').write_text(json.dumps(top, indent=1), encoding='utf-8')
    plateau = []
    for cfg in top:
        res = []
        for k, grid in S.NEIGHBOUR.items():
            if k not in cfg: continue
            try: i = [float(x) for x in grid].index(float(cfg[k]))
            except ValueError: continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(grid): res.append(run(dict(cfg, **{k: str(grid[j])}), 'dev', 1, 'plateau'))
        ok = [r for r in res if r]; share = sum(r['ret'] > 0 for r in ok) / len(ok) if ok else 0
        plateau.append(dict(sig=signature(cfg), neighbours=len(ok), profitable_share=round(share, 3), passes=share >= 0.70)); print('PLATEAU', plateau[-1], flush=True)
    dev4 = [run(cfg, 'dev', 4, 'confirm') for cfg in top]; print('MODEL4 DEV', dev4, flush=True)
    base_val = run(S.BASE, 'val', 4, 'baseline'); val = [(cfg, run(cfg, 'val', 4, 'validation'), pl) for cfg, pl in zip(top, plateau)]
    for _c, r, _p in val: print('VALIDATION', r, flush=True)
    passing = [(c, r) for c, r, pl in val if pl['passes'] and better(r, base_val)]
    base_oos = run(S.BASE, 'oos', 4, 'baseline')
    verdict = dict(windows=W, plateau=plateau, base_dev=b4, base_dev_model1=b1, dev_model4=dev4, base_val=base_val, validation=[r for _, r, _ in val], base_oos=base_oos, finalists=top)
    if passing:
        cfg, r = max(passing, key=lambda x: x[1]['score'] or -1e9); oos = run(cfg, 'oos', 4, 'oos')
        verdict.update(chosen=cfg, chosen_sig=signature(cfg), oos=oos, oos_passes=oos['ret'] > 0 and (oos['pf'] or 0) >= 1.15 and (oos['score'] or -1e9) >= (base_oos['score'] or -1e9))
        print('OOS', oos, 'baseline', base_oos, 'passes', verdict['oos_passes'], flush=True)
    else:
        cfg = max((x for x in val if x[1]), key=lambda x: x[1]['score'] or -1e9)[0]
        verdict.update(chosen=None, diagnostic=cfg, diagnostic_sig=signature(cfg), diagnostic_oos=run(cfg, 'oos', 4, 'diagnostic')); print('NO CANDIDATE PASSED PLATEAU + VALIDATION', flush=True)
    show = verdict.get('chosen') or verdict.get('diagnostic'); out = {}
    for label, cfg in (('baseline', S.BASE), ('candidate', show)):
        allrun = run(cfg, 'all', 4, 'final-all'); T = sorted(ledger(cfg, 'all', 4), key=lambda t: t['close_time']); bal = 1e4; rr = []
        for t in T: rr.append(t['net_profit'] / (0.01 * bal)); bal += t['net_profit']
        tw = robustness.three_monte_carlo(rr, runs=1000, seed=20261104)
        out[label] = dict(all=allrun, mc=dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct']),
                          mc_passes=tw['resample']['red_pct'] <= 5 and tw['randomize']['both']['red_pct'] <= 10)
        print('ALL+MC', label, out[label], flush=True)
    verdict['final'] = out
    try: verdict['buy_hold'] = buy_hold.run(S.H, S.SYM, {k: v for k, v in W.items() if k != 'parity'})
    except Exception as e: verdict['buy_hold'] = f'not run: {e}'
    (S.H / 'VERDICT.json').write_text(json.dumps(verdict, indent=1, default=str), encoding='utf-8'); print('SEARCH DONE', len(DONE), flush=True)
