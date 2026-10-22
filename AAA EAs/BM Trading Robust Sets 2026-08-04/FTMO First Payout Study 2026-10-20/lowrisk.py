"""Lower funded-phase risk variants (PLAN.md addendum 3) on the income model of income.py, $100k.

python lowrisk.py freeze | run <variant> <cost> | table
"""
import bisect, hashlib, importlib.util, json, math, random, statistics, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


I = load('income', R / 'income.py'); S, P, T, D, E = I.S, I.P, I.T, I.D, I.E
VARIANTS = {'LEGACY_1.00': ('legacy', 0.01), 'SET_1.00': ('set', 0.01), 'SET_0.75': ('set', 0.0075), 'SET_0.50': ('set', 0.005),
            'SET_0.25': ('set', 0.0025), 'CAPS_0.50': ('caps', 0.005)}
COSTS = ('recorded_exness', 'fixed_cost_stress'); THRESHOLD = 20


def guard_lots(equity, unit, spec, budget):
    """EA request (1% of equity, rounded UP) then CalyxFTMOGuard: floor(min(request, budget / unit, max))."""
    if not math.isfinite(equity) or not math.isfinite(unit) or equity <= 0 or unit <= 0 or budget <= 0: return 0., 0.
    raw = equity * 0.01 / unit
    requested = math.ceil((min(raw, spec['maximum']) - 1e-12) / spec['step']) * spec['step']
    requested = min(spec['maximum'], max(spec['minimum'], requested))
    guarded = E.floor_lot(min(requested, budget / unit, spec['maximum']), spec['step'])
    return (guarded if guarded >= spec['minimum'] - 1e-9 else 0.), requested


class LowRisk(I.Income):
    def __init__(self, plan, start, cost, k, threshold, mode, r):
        self.mode = mode; self.r = r
        super().__init__(plan, start, cost, k, threshold); self.cap_now = self.cap()

    def cap(self): return self.C * self.r if self.mode == 'caps' else P.CAP * self.k

    def opening(self, row, t):  # sizes.ScaledChallenge.opening + income buffer tracking; only the lot rule differs
        self.observe(t); self.maybe_pass(t)
        if row['ea'] not in self.plan['baskets'][self.portfolio]: return
        if row['op'] < self.start['epoch']: return
        if any(p['row']['ea'] == row['ea'] for p in self.active.values()): self.counts['same_ea_exposure'] += 1; return
        self.cap_now = self.cap(); spec = self.specs[row['symbol']]
        if self.mode == 'legacy': lot, requested = S.lots_scaled(self.eq, row['unit_risk'], spec, self.cap_now)
        else: lot, requested = guard_lots(self.eq, row['unit_risk'], spec, min(self.cap_now, self.eq * self.r))
        if lot <= 0: self.counts['minimum_lot_over50_or_source_request'] += 1; return
        risk = lot * row['unit_risk']; margin = lot * E.margin_per_lot(row, spec); reason = self.reject_reason(row, t, risk, margin)
        if reason: self.counts[reason] += 1; return
        assert risk <= self.cap_now + 1e-7 and lot <= requested + 1e-8
        self.counts[f'cap_{self.cap_now:g}'] += 1
        fee = row['entry_unit_cost'] * lot - (E.stress_per_lot(row, 'entry') * lot if self.cost == 'fixed_cost_stress' else 0.)
        fee = round(fee, 2); self.balance = round(self.balance + fee, 2)
        self.active[row['id']] = dict(row=row, lots=lot, requested_lots=requested, risk=risk, margin=margin, mark_unit=0., mark_epoch=None, entry_cash=fee, phase=self.phase)
        self.last_entry = t; self.daily_entries += 1; self.days.add(str(E.day_of(t))); p = self.current(); p['entries'] += 1; p['entry_days'] = sorted(self.days)
        if p['first_trade_epoch'] is None: p['first_trade_epoch'] = t
        self.counts['opened'] += 1; self.observe(t)
        self.buffer_at_entry = self.counts.get('soft_total_buffer9200', 0)


def live2(plan, events, d, days, cost, k, mode, r):
    """income.live with the LowRisk model (identical control flow) + first-reward amount."""
    s = P.start_dict(d, days); m = LowRisk(plan, s, cost, k, THRESHOLD, mode, r)
    for t, kind, pr_, key, row, mark in events:
        if kind == 0:
            m.day_reset(t)
            if m.dead: break
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
        if m.failed and not m.dead: m.dead = ('breach', m.phases[1]['fail_epoch'])
    if not m.dead:
        m.observe(s['horizon_epoch'] - 1e-4)
        if m.failed: m.dead = ('breach', m.phases[1]['fail_epoch'])
    nets = round(sum(x['net'] for x in m.trades), 2); open_cash = round(sum(p['entry_cash'] for p in m.active.values()), 2)
    assert abs((m.withdrawn + m.balance - m.C) - (nets + open_cash)) < 0.05 * (1 + len(m.trades) + len(m.payouts)), 'accounting'
    end_epoch = m.dead[1] if m.dead else s['horizon_epoch']; alive = max(1e-9, (end_epoch - s['epoch']) / 86400)
    pays = [p for p in m.payouts if p['epoch'] <= end_epoch + 1e-6]
    return dict(start=d.isoformat(), end=m.dead[0] if m.dead else 'alive', alive_days=round(alive, 2), payouts=len(pays),
                income=round(sum(p['payout'] for p in pays), 2), first_year_income=round(sum(p['payout'] for p in pays if p['epoch'] < s['epoch'] + 365 * 86400), 2),
                trades=len(m.trades), first_payout_day=None if not pays else (E.day_of(pays[0]['epoch']) - d).days + 1,
                first_payout=None if not pays else pays[0]['payout'], eqdd=round(m.max_dd, 1))


def summarize(rows, horizon):
    out = I.summarize([{k: v for k, v in r.items() if k not in ('first_payout', 'eqdd')} for r in rows], horizon)
    first = [r for r in rows if r['first_payout'] is not None]
    out['first_payout_share'] = round(len(first) / len(rows), 4)
    out['first_payout_day_median'] = statistics.median(r['first_payout_day'] for r in first) if first else None
    out['first_payout_median'] = round(statistics.median(r['first_payout'] for r in first), 2) if first else None
    out['alive_at_horizon'] = round(sum(r['end'] == 'alive' for r in rows) / len(rows), 4)
    return out


def freeze():
    prev = json.loads((R / 'FROZEN-INCOME.json').read_text(encoding='utf-8'))['files']
    files = [Path(__file__), R / 'PLAN.md'] + [Path(p) for p in prev if Path(p).name != 'PLAN.md']
    (R / 'FROZEN-LOWRISK.json').write_text(json.dumps(dict(frozen_at=datetime.now(P.Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def run(variant, cost):
    for p, h in json.loads((R / 'FROZEN-LOWRISK.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    E.verify_freeze(); mode, r = VARIANTS[variant]; k = I.SIZE / 10000; began = time.time(); data, plan, events, epochs = I.setup()
    split = load('data_split', P.SPLIT_PY).research_split(P.DATA_START, P.DATA_END)
    wins = {w: (date.fromisoformat(split[w]['start']), date.fromisoformat(split[w]['end_exclusive'])) for w in ('development', 'validation', 'oos')}
    rows = []; d = P.DATA_START
    while d <= I.HIST_LAST_START:
        if d.weekday() < 5: rows.append(live2(plan, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=I.HIST_DAYS))), d, I.HIST_DAYS, cost, k, mode, r))
        d += timedelta(days=1)
    out = dict(variant=variant, mode=mode, risk=r, cost=cost, hist={'all_starts': summarize(rows, I.HIST_DAYS)})
    for w, (a, b) in wins.items():
        sel = [x for x in rows if a <= date.fromisoformat(x['start']) < b]
        if sel: out['hist'][f'{w}_starts'] = summarize(sel, I.HIST_DAYS)
    print('hist', variant, cost, json.dumps({k_: out['hist']['all_starts'][k_] for k_ in ('ends', 'median_days_to_end', 'pooled_income_per_alive_month', 'income_total_mean')}), f'{time.time() - began:.0f}s', flush=True)
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m_ = [], date(2021, 10, 11)
    while m_ + timedelta(days=T.BLOCK_DAYS) <= P.DATA_END: mondays.append(m_); m_ += timedelta(days=7)
    index = {m_: (bisect.bisect_left(ops, P.midnight(m_)), bisect.bisect_left(ops, P.midnight(m_ + timedelta(days=T.BLOCK_DAYS)))) for m_ in mondays}
    sd = date(2030, 1, 7); days = T.BLOCK_DAYS * I.MC_BLOCKS; rng = random.Random(I.MC_SEED); mc = []
    for i in range(P.PATHS):
        mc.append(live2(plan, P.path_events(pool, mondays, index, rng, sd, priority, I.MC_BLOCKS), sd, days, cost, k, mode, r))
        if i % 500 == 0: print('mc', variant, cost, i, f'{time.time() - began:.0f}s', flush=True)
    out['mc'] = summarize(mc, days)
    if variant == 'LEGACY_1.00':  # parity gate vs income.py
        ref = json.loads((R / f'INCOME-{cost}-{THRESHOLD}.json').read_text(encoding='utf-8'))
        strip = lambda s: {k_: v for k_, v in s.items() if k_ not in ('first_payout_share', 'first_payout_day_median', 'first_payout_median', 'alive_at_horizon')}  # noqa: E731
        assert strip(out['mc']) == ref['mc'], 'legacy MC parity'
        for key, v in out['hist'].items(): assert strip(v) == ref['hist'][key], ('legacy hist parity', key)
        out['parity_vs_income'] = 'exact'; print('legacy parity exact', cost, flush=True)
    out['seconds'] = round(time.time() - began)
    (R / f'LOWRISK-{variant}-{cost}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('done', variant, cost, out['seconds'], 's', flush=True)


def table():
    X = {(p.stem.split('-')[1], p.stem.split('-')[2]): json.loads(p.read_text(encoding='utf-8')) for p in sorted(R.glob('LOWRISK-*-*.json'))}
    usd = lambda v: '-' if v is None else f'${v:,.0f}'; pct = lambda v: '-' if v is None else f'{100 * v:.0f}%'  # noqa: E731
    order = ['LEGACY_1.00', 'SET_1.00', 'SET_0.75', 'SET_0.50', 'SET_0.25', 'CAPS_0.50']
    label = {'LEGACY_1.00': '1.00% (old model)', 'SET_1.00': '1.00% (current package, guard-exact)', 'SET_0.75': '0.75% (installer input)', 'SET_0.50': '0.50% (installer input)',
             'SET_0.25': '0.25% (installer input)', 'CAPS_0.50': '0.50% + caps 2.25%/1.5% (guard change)'}
    parts = ['# Lower funded risk — one $100k account, $20 reward every 14 days (generated from LOWRISK-*.json)', '']
    for cost in COSTS:
        for src, lbl in (('mc', 'Monte Carlo 36 months'), ('all_starts', 'History 12-month horizon, all starts'), ('oos_starts', 'History, OOS 2024-25 starts'), ('development_starts', 'History, development starts')):
            parts += [f'## {lbl} · {cost}', '', '| Funded risk per trade | Avg monthly income while trading | Median days until it stops | Mean days | Still trading at horizon | Breach / frozen | Total income until end (median / mean) | First-year income (mean) | Payouts (median) | First reward (share / median day / median $) | Trades / month | / day |',
                      '|---|---|---|---|---|---|---|---|---|---|---|---|']
            for v in order:
                x = X.get((v, cost))
                if not x: continue
                s = x['mc'] if src == 'mc' else x['hist'].get(src)
                if not s: continue
                n = s['n']; e = s['ends']; med = s['median_days_to_end']
                parts.append(f"| {label[v]} | {usd(s['pooled_income_per_alive_month'])} | {'> ' + str(s['horizon_days']) if med is None else f'{med:g}'} | {s['mean_alive_days_within_horizon']:g} | {pct(s['alive_at_horizon'])} | "
                             f"{pct(e.get('breach', 0) / n)} / {pct(e.get('frozen', 0) / n)} | {usd(s['income_total_median'])} / {usd(s['income_total_mean'])} | {usd(s['first_year_income_mean'])} | {s['payouts_median']:g} | "
                             f"{pct(s['first_payout_share'])} / {s['first_payout_day_median']} / {usd(s['first_payout_median'])} | {s['trades_per_month_alive_median']} | {s['trades_per_weekday_alive_median']} |")
            parts.append('')
    (R / 'LOWRISK.md').write_text('\n'.join(parts) + '\n', encoding='utf-8'); print('\n'.join(parts))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'freeze': freeze()
    elif c == 'run': run(sys.argv[2], sys.argv[3])
    elif c == 'table': table()
