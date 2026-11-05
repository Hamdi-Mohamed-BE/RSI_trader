"""USDJPY London Open optimisation (PLAN.md, frozen before results). Run from AAA EAs/EA store:  uv run python "<this>"
Compiles the research EA, proves parity with the production ledger, runs the staged development search, plateau, validation, OOS and diagnostics. Every run is recorded in RUNS.jsonl. python mc.py afterwards."""
import copy, gzip, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split  # noqa: E402
SRC = H / 'EA/london/USDJPY London Research EA.mq5'; EX5 = SRC.with_suffix('.ex5'); SYM = 'USDJPY'
SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
           'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': ('2019-01-01', '2026-11-01'), '1y': ('2025-11-01', '2026-11-01'), '6m': ('2026-05-01', '2026-11-01'), '3m': ('2026-08-01', '2026-11-01')}
assert WINDOWS['oos'] == ('2024-11-01', '2026-11-01')
dot = lambda s: s.replace('-', '.')  # noqa: E731
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
item = next(i for i in json.loads((PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json').read_text(encoding='utf-8-sig')) if i['label'] == 'USDJPY London Open Momentum')
BASE = {k: str(v) for k, v in item['inputs'].items()}; BASE.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false', InpTrailAtrStartR='0', InpTrailAtrMultiple='4', InpLockAtR='0', InpLockToR='0.5')
RUNS = H / 'RUNS.jsonl'; DONE = {}
if RUNS.exists():
    for line in RUNS.read_text(encoding='utf-8').splitlines():
        x = json.loads(line); DONE[(x['sig'], x['window'])] = x
ROWS = lambda **k: {a: str(v) for a, v in k.items()}  # noqa: E731
DAYS = {'wed-fri': (0, 0, 1, 1, 1), 'mon-fri': (1, 1, 1, 1, 1), 'tue-fri': (0, 1, 1, 1, 1), 'tue-thu': (0, 1, 1, 1, 0), 'mon-thu': (1, 1, 1, 1, 0), 'wed-thu': (0, 0, 1, 1, 0), 'thu-fri': (0, 0, 0, 1, 1)}
NAMES = ('InpTradeMonday', 'InpTradeTuesday', 'InpTradeWednesday', 'InpTradeThursday', 'InpTradeFriday')
STAGES = [
    ('stop', [ROWS(InpStopMode=0, InpStopAtrMultiple=v) for v in (2, 3, 4, 5, 6, 7, 8, 10)] + [ROWS(InpStopMode=1, InpFormationRangeStopMultiple=v) for v in (1, 1.5, 2)]),
    ('break_even', [ROWS(InpBreakEvenAtR=v) for v in (0, 0.5, 0.75, 1, 1.5, 2)]),
    ('r_trail', [ROWS(InpTrailStartAtR=0)] + [ROWS(InpTrailStartAtR=s, InpTrailDistanceR=d) for s in (0.5, 1, 1.5, 2) for d in (0.25, 0.5, 0.75, 1)]),
    ('atr_trail', [ROWS(InpTrailAtrStartR=0)] + [ROWS(InpTrailAtrStartR=s, InpTrailAtrMultiple=m) for s in (0.5, 1, 1.5) for m in (2, 3, 4, 6, 8)]),
    ('lock', [ROWS(InpLockAtR=0)] + [ROWS(InpLockAtR=a, InpLockToR=t) for a in (1, 1.5, 2) for t in (0.25, 0.5, 1)]),
    ('target', [ROWS(InpTargetMode=0)] + [ROWS(InpTargetMode=1, InpTargetR=v) for v in (0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6)]),
    ('exit_hour', [ROWS(InpExitLondonHour=f'{v}.0') for v in (11, 12, 13, 14, 15, 16, 17, 18, 19, 20)]),
    ('formation', [ROWS(InpFormationMinutes=v) for v in (15, 30, 45, 60, 90, 120)]),
    ('signal', [ROWS(InpMinimumSignalAtr=v) for v in (0, 0.1, 0.2, 0.3, 0.5)] + [ROWS(InpMinimumVolumePctMedian=v) for v in (0, 50, 75)]),
    ('adx_di', [ROWS(InpUseADXFilter='true', InpADXMinimum=v) for v in (15, 20, 25, 30)] + [ROWS(InpUseADXFilter='false'), ROWS(InpRequireDIAgreement='true'), ROWS(InpRequireDIAgreement='false')]),
    ('direction', [ROWS(InpDirection=v) for v in (0, 1, 2)]),
    ('weekdays', [dict(zip(NAMES, ('true' if d else 'false' for d in v))) for v in DAYS.values()])]
NEIGHBOUR = {'InpStopAtrMultiple': (2, 3, 4, 5, 6, 7, 8, 10), 'InpBreakEvenAtR': (0, 0.5, 0.75, 1, 1.5, 2), 'InpTrailDistanceR': (0.25, 0.5, 0.75, 1), 'InpTrailStartAtR': (0.5, 1, 1.5, 2), 'InpTrailAtrStartR': (0.5, 1, 1.5), 'InpTrailAtrMultiple': (2, 3, 4, 6, 8),
             'InpLockAtR': (1, 1.5, 2), 'InpLockToR': (0.25, 0.5, 1), 'InpTargetR': (0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6), 'InpExitLondonHour': (11, 12, 13, 14, 15, 16, 17, 18, 19, 20), 'InpFormationMinutes': (15, 30, 45, 60, 90, 120), 'InpMinimumSignalAtr': (0, 0.1, 0.2, 0.3, 0.5),
             'InpMinimumVolumePctMedian': (0, 25, 50, 75), 'InpADXMinimum': (15, 20, 25, 30)}


def signature(cfg): return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]


def run(cfg, window, tag=''):
    sig = signature(cfg)
    if (sig, window) in DONE: return DONE[(sig, window)]
    variant = 'V' + sig; b.CONFIG['variants'][variant] = {'label': variant, 'inputs': cfg}; b.CONFIG['common_inputs'] = {}; b.CONFIG['end_date'] = dot(WINDOWS[window][1])
    meta = None
    for attempt in range(4):                             # the tester agent can time out at startup when the CPU is busy
        try:
            meta = b.run_case(SYM, variant, window); break
        except SystemExit:
            time.sleep(60)
    if meta is None:
        print('CASE FAILED', variant, window, flush=True); return None
    d = b.OUT / f'nw-{SYM}-{variant}-{window}'; m = meta['metrics']; dd = buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz')
    T = json.loads(gzip.open(d / 'trades.json.gz').read()); net = sum(t['net_profit'] for t in T)
    rec = dict(sig=sig, window=window, tag=tag, ret=round(net / 100, 2), pf=m.get('profit_factor'), trades=len(T), win=m.get('win_rate_pct'), dd=dd, score=round((net / 100) / dd, 3) if dd else None,
               changes={k: v for k, v in cfg.items() if BASE.get(k) != v}, flags=meta['journal_flags'])
    DONE[(sig, window)] = rec
    with RUNS.open('a', encoding='utf-8') as f: f.write(json.dumps(rec) + '\n')
    return rec


def eligible(r): return r and r['pf'] is not None and r['pf'] >= 1.15 and r['trades'] >= 100 and r['ret'] > 0


def main():
    flag = PACKAGE / 'US30 5M Momentum Raw 2026-11-05/DONE.flag'                 # owner rule: one tester at a time; the US30 raw test runs first
    while not flag.exists(): time.sleep(30)
    assert not b.isolated_running(), 'Tester is occupied'
    log = SRC.with_suffix('.compile.log'); subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    raw = log.read_bytes(); assert '0 errors, 0 warnings' in raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); print('COMPILED', b.sha(EX5)[:12], flush=True)
    dest = b.TESTER / 'MQL5/Experts/CalyxUsdJpyOpt'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'usdjpy-opt.ex5')
    b.CONFIG.update(periods={k: dot(a) for k, (a, _) in WINDOWS.items()}, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxUsdJpyOpt', expert_file='usdjpy-opt.ex5', controls={}, variants={}, period='M15')
    # parity: research EX5 with the new inputs off = the production ledger of USDJPY London MC OOS 2026-11-04, trade for trade
    run(BASE, 'all', 'baseline')
    mine = json.loads(gzip.open(b.OUT / f"nw-{SYM}-V{signature(BASE)}-all/trades.json.gz").read()); prod = json.loads(gzip.open(PACKAGE / 'USDJPY London MC OOS 2026-11-04/native/nw-USDJPY-PROD-all/trades.json.gz').read())
    key = lambda T: [(t['open_time'], t['close_time'], t['side'], t['volume'], t['net_profit']) for t in sorted(T, key=lambda t: t['open_time'])]  # noqa: E731
    same = key(mine) == key(prod); print('PARITY', same, len(mine), len(prod), flush=True); assert same, 'research EA differs from production'
    base_dev = run(BASE, 'dev', 'baseline'); print('BASELINE dev', base_dev, flush=True)
    top = [BASE]
    for name, grid in STAGES:
        seen = {}
        for parent in top:
            for change in grid:
                cfg = dict(parent, **change); sig = signature(cfg)
                if sig not in seen: seen[sig] = (cfg, run(cfg, 'dev', name))
        ranked = sorted([v for v in seen.values() if eligible(v[1])], key=lambda v: -(v[1]['score'] or -1e9))
        if ranked: top = [v[0] for v in ranked[:3]]
        print('STAGE', name, len(seen), 'configs; best', [(v[1]['score'], v[1]['ret'], v[1]['pf'], v[1]['trades'], v[1]['dd'], v[1]['changes']) for v in ranked[:3]], flush=True)
    (H / 'FINALISTS.json').write_text(json.dumps(top, indent=1), encoding='utf-8')
    # plateau of each finalist: one-step neighbours on development
    plateau = []
    for cfg in top:
        res = []
        for k, grid in NEIGHBOUR.items():
            if k not in cfg: continue
            try: i = [float(x) for x in grid].index(float(cfg[k]))
            except ValueError: continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(grid): res.append(run(dict(cfg, **{k: (f'{grid[j]}.0' if k == 'InpExitLondonHour' else str(grid[j]))}), 'dev', 'plateau'))
        ok = [r for r in res if r]; share = sum(r['ret'] > 0 for r in ok) / len(ok) if ok else 0
        plateau.append(dict(sig=signature(cfg), neighbours=len(ok), profitable_share=round(share, 3), passes=share >= 0.70))
        print('PLATEAU', plateau[-1], flush=True)
    base_val = run(BASE, 'val', 'baseline'); val = []
    for cfg, pl in zip(top, plateau):
        r = run(cfg, 'val', 'validation'); val.append((cfg, r, pl))
        print('VALIDATION', r, flush=True)
    passing = [(c, r) for c, r, pl in val if pl['passes'] and eligible_val(r, base_val)]
    verdict = dict(plateau=plateau, base_dev=base_dev, base_val=base_val, validation=[r for _, r, _ in val])
    base_oos = run(BASE, 'oos', 'baseline')
    if passing:
        cfg, r = max(passing, key=lambda x: x[1]['score'] or -1e9); oos = run(cfg, 'oos', 'oos'); verdict.update(chosen=cfg, chosen_sig=signature(cfg), oos=oos, base_oos=base_oos, oos_passes=oos['ret'] > 0 and (oos['pf'] or 0) >= 1.15 and (oos['score'] or -1e9) >= (base_oos['score'] or 0))
        print('OOS', oos, 'baseline', base_oos, 'passes', verdict['oos_passes'], flush=True)
    else:
        # labelled diagnostic only: the best-validation candidate still shown on OOS so the owner sees what was rejected
        cfg = max((x for x in val if x[1]), key=lambda x: x[1]['score'] or -1e9)[0]; verdict.update(chosen=None, diagnostic=cfg, diagnostic_sig=signature(cfg), diagnostic_oos=run(cfg, 'oos', 'diagnostic'), base_oos=base_oos); print('NO CANDIDATE PASSED PLATEAU + VALIDATION', flush=True)
    show = verdict.get('chosen') or verdict.get('diagnostic')
    for w in ('all', '1y', '6m', '3m'):
        run(BASE, w, 'baseline'); run(show, w, 'finalist')
    (H / 'VERDICT.json').write_text(json.dumps(verdict, indent=1), encoding='utf-8'); print('SEARCH DONE', len(DONE), flush=True)


def eligible_val(r, base): return r and r['ret'] > 0 and (r['pf'] or 0) >= 1.15 and (r['score'] or -1e9) > (base['score'] or 0)


if __name__ == '__main__':
    main()
