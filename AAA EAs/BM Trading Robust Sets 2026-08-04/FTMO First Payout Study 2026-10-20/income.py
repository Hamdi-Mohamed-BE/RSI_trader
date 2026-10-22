"""Long-run income on one funded account (PLAN.md addendum 2): repeated FTMO rewards every >= 14 days, balance reset to
the initial capital after each reward (guard assumed re-baselined), until FTMO breach or guard freeze.

python income.py freeze | parity | run <cost> <threshold> | table
"""
import bisect, hashlib, importlib.util, json, math, random, statistics, sys, time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


S = load('sizes', R / 'sizes.py'); P, T, D, E = S.P, S.T, S.D, S.E
SIZE = 100000; HIST_DAYS = 365; HIST_LAST_START = date(2025, 10, 6); MC_BLOCKS = 39; MC_SEED = 20261022; FREEZE_DAYS = 30
MONTH = 30.4375


class Income(S.ScaledFunded):
    def __init__(self, plan, start, cost, k, threshold):
        super().__init__(plan, start, cost, k)
        self.threshold = threshold; self.next_ok = None; self.payouts = []; self.withdrawn = 0.0
        self.buffer_at_entry = 0; self.dead = None

    def check(self, t):
        if self.threshold is None or self.failed or self.active: return
        first = self.current()['first_trade_epoch']
        if first is None: return
        if self.next_ok is None: self.next_ok = P.midnight(E.day_of(first) + timedelta(days=P.FIRST_AFTER))
        if t < self.next_ok - 1e-6: return
        profit = round(self.balance - self.C, 2)
        if profit >= (20 if self.threshold == 20 else self.threshold * self.k) - 1e-9:
            self.payouts.append(dict(epoch=t, profit=profit, payout=round(P.SPLIT * profit, 2)))
            self.withdrawn = round(self.withdrawn + profit, 2)
            self.balance = round(self.balance - profit, 2); self.anchor -= profit; self.eq = self.balance
            self.peak = self.eq; self.closed_peak = self.balance
            self.next_ok = P.midnight(E.day_of(t) + timedelta(days=14))

    def opening(self, row, t):
        before = self.last_entry; super().opening(row, t)
        if self.last_entry != before: self.buffer_at_entry = self.counts.get('soft_total_buffer9200', 0)

    def day_reset(self, t):
        super().day_reset(t)
        if self.failed: self.dead = ('breach', self.phases[1]['fail_epoch'])
        elif (not self.active and self.counts.get('soft_total_buffer9200', 0) > self.buffer_at_entry
              and t - max(self.last_entry, self.start['epoch']) > FREEZE_DAYS * 86400):
            self.dead = ('frozen', max(self.last_entry, self.start['epoch']))


def live(plan, events, d, days, cost, threshold, k):
    s = P.start_dict(d, days); m = Income(plan, s, cost, k, threshold)
    for t, kind, pr_, key, row, mark in events:
        if kind == 0:
            m.day_reset(t)
            if m.dead: break
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
        if m.failed and not m.dead: m.dead = ('breach', m.phases[1]['fail_epoch'])
    if not m.dead:  # close the horizon exactly as Trial.result does
        m.observe(s['horizon_epoch'] - 1e-4)
        if m.failed: m.dead = ('breach', m.phases[1]['fail_epoch'])
    nets = round(sum(x['net'] for x in m.trades), 2)
    open_cash = round(sum(p['entry_cash'] for p in m.active.values()), 2)
    assert abs((m.withdrawn + m.balance - m.C) - (nets + open_cash)) < 0.05 * (1 + len(m.trades) + len(m.payouts)), ('accounting', m.withdrawn, m.balance, nets, open_cash)
    end_epoch = m.dead[1] if m.dead else s['horizon_epoch']
    alive = max(1e-9, (end_epoch - s['epoch']) / 86400)
    pays = [p for p in m.payouts if p['epoch'] <= end_epoch + 1e-6]
    return dict(start=d.isoformat(), end=m.dead[0] if m.dead else 'alive', alive_days=round(alive, 2), payouts=len(pays),
                income=round(sum(p['payout'] for p in pays), 2), first_year_income=round(sum(p['payout'] for p in pays if p['epoch'] < s['epoch'] + 365 * 86400), 2),
                trades=len(m.trades), first_payout_day=None if not pays else (E.day_of(pays[0]['epoch']) - d).days + 1)


def q(a, p):
    s = sorted(a); return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))] if s else None


def summarize(rows, horizon_days):
    n = len(rows); ended = [r for r in rows if r['end'] != 'alive']
    out = dict(n=n, horizon_days=horizon_days, ends=dict(Counter(r['end'] for r in rows)))
    for mo in (3, 6, 12, 24, 36):
        if mo * MONTH <= horizon_days + 5: out[f'ended_by_{mo}m'] = round(sum(r['alive_days'] <= mo * MONTH for r in ended) / n, 4)
    life = sorted(r['alive_days'] if r['end'] != 'alive' else math.inf for r in rows)
    med = life[(n - 1) // 2]; out['median_days_to_end'] = None if math.isinf(med) else round(med, 1)
    out['median_days_to_end_among_ended'] = round(statistics.median(r['alive_days'] for r in ended), 1) if ended else None
    out['mean_alive_days_within_horizon'] = round(statistics.fmean(r['alive_days'] for r in rows), 1)
    monthly = [r['income'] / (r['alive_days'] / MONTH) for r in rows]
    out['monthly_income_while_alive_median'] = round(statistics.median(monthly), 2); out['monthly_income_while_alive_mean'] = round(statistics.fmean(monthly), 2)
    out['pooled_income_per_alive_month'] = round(sum(r['income'] for r in rows) / (sum(r['alive_days'] for r in rows) / MONTH), 2)
    out['income_total_median'] = round(statistics.median(r['income'] for r in rows), 2); out['income_total_mean'] = round(statistics.fmean(r['income'] for r in rows), 2)
    out['income_total_p25'] = q([r['income'] for r in rows], .25); out['income_total_p75'] = q([r['income'] for r in rows], .75)
    out['first_year_income_mean'] = round(statistics.fmean(r['first_year_income'] for r in rows), 2)
    out['first_year_income_median'] = round(statistics.median(r['first_year_income'] for r in rows), 2)
    out['payouts_median'] = statistics.median(r['payouts'] for r in rows); out['zero_payout'] = round(sum(r['payouts'] == 0 for r in rows) / n, 4)
    tm = [r['trades'] / (r['alive_days'] / MONTH) for r in rows if r['alive_days'] >= 14]
    out['trades_per_month_alive_median'] = round(statistics.median(tm), 2); out['trades_per_weekday_alive_median'] = round(out['trades_per_month_alive_median'] / (MONTH * 5 / 7), 3)
    return out


def setup():
    data = json.loads((P.RT / 'INPUTS-DI_OFF.json').read_text(encoding='utf-8'))
    plan = T.splan_for(data['window']); events = E.master_events(plan, data); return data, plan, events, [x[0] for x in events]


def freeze():
    prev = json.loads((R / 'FROZEN-SIZES.json').read_text(encoding='utf-8'))['files']
    files = [Path(__file__), R / 'sizes.py', R / 'run.py', R / 'PLAN.md'] + [Path(p) for p in prev if Path(p).name not in ('PLAN.md', 'sizes.py', 'run.py')]
    (R / 'FROZEN-INCOME.json').write_text(json.dumps(dict(frozen_at=datetime.now(P.Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def verify():
    for p, h in json.loads((R / 'FROZEN-INCOME.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    E.verify_freeze()


def parity():
    verify(); data, plan, events, epochs = setup(); ref = json.loads((P.RT / 'RESULTS.json').read_text(encoding='utf-8'))['continuous']; out = {}
    for cost in ('recorded_exness', 'fixed_cost_stress'):
        s = dict(date=T.OOS[0].isoformat(), epoch=P.midnight(T.OOS[0]), horizon_date=T.OOS[1].isoformat(), horizon_epoch=P.midnight(T.OOS[1]))
        m = Income(plan, s, cost, 1.0, None)
        for t, kind, pr_, key, row, mark in P.window(events, epochs, s['epoch'], s['horizon_epoch']):
            if kind == 0: S.ScaledFunded.day_reset(m, t)
            elif kind in (1, 4): m.closing(row, t)
            elif kind == 2: m.mark(row, mark, t)
            else: m.opening(row, t)
        res = m.result(); r = ref[f'DI_OFF|{cost}']
        got = (len(res['trades']), round(sum(x['net'] for x in res['trades']), 2), round(res['ending_balance'], 2))
        assert got == (r['trades'], r['net'], r['ending_balance']), ('income parity', cost, got)
        out[cost] = dict(trades=got[0], net=got[1], ending_balance=got[2], match=True)
    (R / 'INCOME-PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('parity exact', out)


def run(cost, threshold):
    verify(); began = time.time(); k = SIZE / 10000; data, plan, events, epochs = setup()
    split = load('data_split', P.SPLIT_PY).research_split(P.DATA_START, P.DATA_END)
    wins = {w: (date.fromisoformat(split[w]['start']), date.fromisoformat(split[w]['end_exclusive'])) for w in ('development', 'validation', 'oos')}
    rows = []; d = P.DATA_START
    while d <= HIST_LAST_START:
        if d.weekday() < 5:
            rows.append(live(plan, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=HIST_DAYS))), d, HIST_DAYS, cost, threshold, k))
        d += timedelta(days=1)
    out = dict(size=SIZE, cost=cost, threshold=threshold, hist={'all_starts': summarize(rows, HIST_DAYS)})
    for w, (a, b) in wins.items():
        sel = [r for r in rows if a <= date.fromisoformat(r['start']) < b]
        if sel: out['hist'][f'{w}_starts'] = summarize(sel, HIST_DAYS)
    print('hist', cost, threshold, json.dumps(out['hist']['all_starts']), f'{time.time() - began:.0f}s', flush=True)
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m_ = [], date(2021, 10, 11)
    while m_ + timedelta(days=T.BLOCK_DAYS) <= P.DATA_END: mondays.append(m_); m_ += timedelta(days=7)
    index = {m_: (bisect.bisect_left(ops, P.midnight(m_)), bisect.bisect_left(ops, P.midnight(m_ + timedelta(days=T.BLOCK_DAYS)))) for m_ in mondays}
    sd = date(2030, 1, 7); days = T.BLOCK_DAYS * MC_BLOCKS; rng = random.Random(MC_SEED); mc = []
    for i in range(P.PATHS):
        ev = P.path_events(pool, mondays, index, rng, sd, priority, MC_BLOCKS)
        mc.append(live(plan, ev, sd, days, cost, threshold, k))
        if i % 500 == 0: print('mc', i, f'{time.time() - began:.0f}s', flush=True)
    out['mc'] = summarize(mc, days)
    print('mc', cost, threshold, json.dumps(out['mc']), f'{time.time() - began:.0f}s', flush=True)
    out['seconds'] = round(time.time() - began)
    (R / f'INCOME-{cost}-{threshold}.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('done', out['seconds'], 's')


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'freeze': freeze()
    elif c == 'parity': parity()
    elif c == 'run': run(sys.argv[2], int(sys.argv[3]))
