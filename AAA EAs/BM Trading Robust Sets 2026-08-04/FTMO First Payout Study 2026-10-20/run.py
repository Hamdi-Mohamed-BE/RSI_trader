"""FTMO first-payout study for the built Best Prop Portfolio on a $10k FTMO 2-Step (Swing) account (see PLAN.md).
Funded-phase replay with the exact package guard (retest Continuous rules) + first-reward tracking; end-to-end chain
from challenge start; block-bootstrap Monte Carlo. No MT5 terminal, no trading, nothing tuned.

python run.py freeze | run | report
"""
import bisect, gzip, hashlib, importlib.util, json, math, random, statistics, sys, time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
RT = B / 'Best Prop Portfolio Retest 2026-10-20'
RULES = B.parent / 'EA store' / 'data' / 'prop-rules' / 'ftmo-2step-swing.json'
SPLIT_PY = B.parent / 'Calyx Research Pipeline' / 'data_split.py'
HORIZON = 180; FIRST_AFTER = 14; THRESHOLDS = (20, 250, 500, 1000); PATHS = 2000; SEED = 20261020; E2E_SEED = 20261021
DATA_END = date(2026, 10, 6); DATA_START = date(2021, 10, 7); E2E_LAST_START = date(2025, 9, 27); E2E_BLOCKS = 14
SCEN = {'base': ('recorded_exness', 'next_prague_midnight'), 'stress': ('fixed_cost_stress', 'two_business_day_wait')}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


T = load('retest', RT / 'retest.py'); D = T.D; E = D.e; CAP = T.CAP
RULE = json.loads(RULES.read_text(encoding='utf-8'))['payout']; SPLIT = RULE['split_pct'] / 100
FEE_EUR = json.loads(RULES.read_text(encoding='utf-8'))['fees']['10000']
WINDOWS = None


class Funded(D.DialTrial):
    """Retest Continuous rules (funded: no phase target) + first flat moment >= day 14 with closed profit >= threshold."""
    def __init__(self, plan, start, cost):
        super().__init__(plan, D.BASKET, start, cost, 'next_prague_midnight', [(-1e9, CAP)])
        self.paid = {}

    def maybe_pass(self, t): return

    def reject_reason(self, row, t, risk, margin):  # identical to retest.continuous.Continuous.reject_reason
        m = self.cap_now / 50
        if self.failed: return 'permanent_hard_failure'
        if self.day_stopped: return 'daily_300_latch'
        if self.daily_entries >= 7: return 'daily_7_entry_limit'
        if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
        total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
        if total + risk > 225 * m + 1e-7: return 'aggregate_initial_risk225'
        if same + risk > 150 * m + 1e-7: return 'same_symbol_initial_risk150'
        reserve = sum(1.25 * p['risk'] + 5 for p in self.active.values())
        projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5
        if projected < 9200 - 1e-8: return 'soft_total_buffer9200'
        if self.anchor - projected > 300 + 1e-8: return 'soft_daily_reserve300'
        existing = sum(p['margin'] for p in self.active.values())
        if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
        if t < self.last_entry + 3: return 'entry_reconciliation3s'
        return None

    def check(self, t):
        if self.failed or self.active: return
        first = self.current()['first_trade_epoch']
        if first is None or t < midnight(E.day_of(first) + timedelta(days=FIRST_AFTER)) - 1e-6: return
        profit = round(self.balance - 10000.0, 2)
        for th in THRESHOLDS:
            if th not in self.paid and profit >= th - 1e-9:
                self.paid[th] = dict(epoch=t, profit=profit, trades=len(self.trades))

    def closing(self, row, t): super().closing(row, t); self.check(t)
    def day_reset(self, t): super().day_reset(t); self.check(t)


def drive(model, events):
    for t, kind, pr_, key, row, mark in events:
        if kind == 0: model.day_reset(t)
        elif kind in (1, 4): model.closing(row, t)
        elif kind == 2: model.mark(row, mark, t)
        else: model.opening(row, t)
    return model


def window(events, epochs, a, b): return events[bisect.bisect_left(epochs, a):bisect.bisect_left(epochs, b)]


def start_dict(d, days): return dict(date=d.isoformat(), epoch=midnight(d), horizon_date=(d + timedelta(days=days)).isoformat(), horizon_epoch=midnight(d + timedelta(days=days)))


def funded_run(plan, ev, d, cost):
    s = start_dict(d, HORIZON); m = drive(Funded(plan, s, cost), ev); res = m.result()
    fail = m.phases[1]['fail_epoch']; first = m.phases[1]['first_trade_epoch']
    stuck = (not m.failed and 20 not in m.paid and m.counts.get('soft_total_buffer9200', 0) > 0 and s['horizon_epoch'] - m.last_entry > 30 * 86400)
    paid = {th: dict(day=(E.day_of(v['epoch']) - d).days + 1, profit=v['profit'], payout=round(SPLIT * v['profit'], 2), trades=v['trades'], epoch=v['epoch'])
            for th, v in m.paid.items()}
    return dict(start=d.isoformat(), paid=paid, failed=m.failed, fail_day=None if fail is None else (E.day_of(fail) - d).days + 1,
                first_trade_day=None if first is None else (E.day_of(first) - d).days + 1, stuck=stuck, trades=len(res['trades']),
                ending_equity=round(res['ending_sampled_equity'], 2), eqdd=round(res['max_sampled_equity_drawdown_cash'], 1))


def access_start(trial):
    acc = trial.get('access_5bd_illustration_epoch')
    if not acc or trial['outcome'] != 'horizon_completed_both': return None
    d = E.day_of(acc); return d if midnight(d) >= acc - 1e-6 else d + timedelta(days=1)


def q(a, p):
    s = sorted(a); return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))] if s else None


def summarize_funded(rows):
    n = len(rows); out = dict(n=n, median_trades_180d=statistics.median(r['trades'] for r in rows))
    out['trades_per_month'] = round(out['median_trades_180d'] / (HORIZON / 30.4375), 2); out['trades_per_weekday'] = round(out['median_trades_180d'] / (HORIZON * 5 / 7), 3)
    out['breach_180d'] = round(sum(r['failed'] for r in rows) / n, 4); out['eqdd_p50'] = q([r['eqdd'] for r in rows], .5); out['eqdd_p95'] = q([r['eqdd'] for r in rows], .95)
    for th in THRESHOLDS:
        paid = [r['paid'][th] for r in rows if th in r['paid']]
        breach_first = sum(1 for r in rows if th not in r['paid'] and r['failed'])
        alive = [r for r in rows if th not in r['paid'] and not r['failed']]
        days = [p['day'] for p in paid]; pay = [p['payout'] for p in paid]
        out[str(th)] = dict(paid_180=round(len(paid) / n, 4), paid_30=round(sum(d <= 30 for d in days) / n, 4), paid_60=round(sum(d <= 60 for d in days) / n, 4),
                            paid_90=round(sum(d <= 90 for d in days) / n, 4), breach_before=round(breach_first / n, 4),
                            no_payout_alive=round(len(alive) / n, 4), stuck_buffer=round(sum(r['stuck'] for r in alive) / n, 4),
                            median_day=statistics.median(days) if days else None, p25_day=q(days, .25), p75_day=q(days, .75),
                            median_payout=round(statistics.median(pay), 2) if pay else None, p25_payout=q(pay, .25), p75_payout=q(pay, .75),
                            ev_payout=round(sum(pay) / n, 2), median_trades_to_request=statistics.median(p['trades'] for p in paid) if paid else None)
    return out


def summarize_e2e(rows):
    n = len(rows); out = dict(n=n, outcomes=dict(Counter(r['outcome'] for r in rows)))
    for th in (20, 500):
        paid = [r for r in rows if r['outcome'] == 'paid' and th in r['funded']['paid']]
        tot = [r['total_days'][str(th)] for r in paid]; pay = [r['funded']['paid'][th]['payout'] for r in paid]
        out[str(th)] = dict(paid_any=round(len(paid) / n, 4), **{f'paid_{k}': round(sum(x <= k for x in tot) / n, 4) for k in (90, 120, 180, 270, 365)},
                            median_total_day=statistics.median(tot) if tot else None, p25_total_day=q(tot, .25), p75_total_day=q(tot, .75),
                            median_payout=round(statistics.median(pay), 2) if pay else None, ev_payout=round(sum(pay) / n, 2))
    fund = [r['funded_day'] for r in rows if r['funded_day']]
    out['funded_access'] = round(len(fund) / n, 4); out['median_funded_access_day'] = statistics.median(fund) if fund else None
    tr = [r['challenge_trades'] + (r['funded']['trades'] if r['funded'] else 0) for r in rows]
    out['median_trades_chain'] = statistics.median(tr); return out


def e2e_one(plan, ch_ev, fund_events_for, s, cost, handover):
    trial = D.replay(plan, start_dict(s, HORIZON), cost, handover, ch_ev, [(-1e9, CAP)])
    fd = access_start(trial); row = dict(start=s.isoformat(), challenge_trades=len(trial['trades']), funded_day=None, funded=None, total_days={})
    if fd is None:
        row['outcome'] = 'challenge_breach' if trial['outcome'].startswith('failed') else 'challenge_not_done_180d'; return row
    row['funded_day'] = (fd - s).days + 1
    f = funded_run(plan, fund_events_for(fd), fd, cost); row['funded'] = f
    for th, p in f['paid'].items():
        row['total_days'][str(th)] = (fd - s).days + p['day']
    row['outcome'] = 'paid' if 20 in f['paid'] else ('funded_breach_before_payout' if f['failed'] else ('funded_stuck_buffer' if f['stuck'] else 'funded_no_payout_180d'))
    return row


def path_events(pool, mondays, index, rng, start_day, priority, blocks):
    rows = []
    for k in range(blocks):
        src = mondays[rng.randrange(len(mondays))]; tgt = start_day + timedelta(days=T.BLOCK_DAYS * k); shift = (tgt - src).days * 86400
        lo, hi = index[src]
        for c in pool[lo:hi]:
            rows.append(dict(c, id=f"{c['id']}#{k}", op=c['op'] + shift, cl=None if c['cl'] is None else c['cl'] + shift, marks=[(m[0] + shift, m[1]) for m in c['marks']]))
    end = midnight(start_day + timedelta(days=T.BLOCK_DAYS * blocks)); ev = []
    for r in rows:
        ev.append((r['op'], 3, priority[r['ea']], r['id'], r, None))
        if r['cl'] is not None and r['cl'] < end: ev.append((r['cl'], 4 if r['cl'] == r['op'] else 1, priority[r['ea']], r['id'], r, None))
        for m in r['marks']: ev.append((m[0], 2, priority[r['ea']], r['id'], r, m))
    x = start_day
    while x < start_day + timedelta(days=T.BLOCK_DAYS * blocks): ev.append((midnight(x), 0, -1, '', None, None)); x += timedelta(days=1)
    ev.sort(key=lambda z: z[:4]); return [z for z in ev if z[0] < end]


def freeze():
    files = [Path(__file__), R / 'PLAN.md', RT / 'retest.py', RT / 'INPUTS-DI_OFF.json', RT / 'INPUTS-DI_ON.json', RT / 'RESULTS.json', RT / 'FROZEN.json',
             T.DIAL / 'run.py', T.FASTER / 'core_engine.py', T.FASTER / 'PLAN.json', T.PACKAGE, RULES, SPLIT_PY]
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def run():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    E.verify_freeze(); began = time.time()
    split = load('data_split', SPLIT_PY).research_split(DATA_START, DATA_END)
    wins = {'development': (date.fromisoformat(split['development']['start']), date.fromisoformat(split['development']['end_exclusive'])),
            'validation': (date.fromisoformat(split['validation']['start']), date.fromisoformat(split['validation']['end_exclusive'])),
            'oos': (date.fromisoformat(split['oos']['start']), date.fromisoformat(split['oos']['end_exclusive'])), 'all': (DATA_START, DATA_END)}
    retest = json.loads((RT / 'RESULTS.json').read_text(encoding='utf-8'))
    out = dict(split=split, rules=dict(RULE, fee_eur_10k=FEE_EUR, model_first_after_days=FIRST_AFTER, thresholds=THRESHOLDS), parity={}, funded={}, funded_mc={}, e2e={}, e2e_mc={})
    raw = dict(funded={}, e2e={})
    for name in ('DI_OFF', 'DI_ON'):
        data = json.loads((RT / f'INPUTS-{name}.json').read_text(encoding='utf-8'))
        plan = T.splan_for(data['window']); events = E.master_events(plan, data); epochs = [x[0] for x in events]
        # Parity gate 1: funded model == retest continuous OOS (payout tracking must not change trading).
        for cost in ('recorded_exness', 'fixed_cost_stress'):
            s = dict(date=T.OOS[0].isoformat(), epoch=midnight(T.OOS[0]), horizon_date=T.OOS[1].isoformat(), horizon_epoch=midnight(T.OOS[1]))
            m = drive(Funded(plan, s, cost), window(events, epochs, s['epoch'], s['horizon_epoch'])); res = m.result(); ref = retest['continuous'][f'{name}|{cost}']
            got = (len(res['trades']), round(sum(x['net'] for x in res['trades']), 2), round(res['ending_balance'], 2))
            assert got == (ref['trades'], ref['net'], ref['ending_balance']), ('continuous parity', name, cost, got, ref)
            out['parity'][f'continuous|{name}|{cost}'] = dict(trades=got[0], net=got[1], ending_balance=got[2], match=True)
        # Parity gate 2: base OOS challenge summary == retest.
        rows = [T.per_trial(D.replay(plan, s, 'recorded_exness', 'next_prague_midnight', window(events, epochs, s['epoch'], s['horizon_epoch']), [(-1e9, CAP)])) for s in T.oos_starts()]
        mine = T.summarize(rows); ref = retest['oos'][f'{name}|recorded_exness|next_prague_midnight']
        assert mine == ref, ('oos challenge parity', name, mine, ref)
        out['parity'][f'oos_challenge|{name}'] = dict(n=mine['n'], pass_both_180=mine['pass_both_180'], match=True)
        print('parity ok', name, f'{time.time() - began:.0f}s', flush=True)
        # A. funded-only historical
        for cost in ('recorded_exness', 'fixed_cost_stress'):
            rows = []; d = DATA_START
            while d + timedelta(days=HORIZON) <= DATA_END:
                if d.weekday() < 5:
                    rows.append(funded_run(plan, window(events, epochs, midnight(d), midnight(d + timedelta(days=HORIZON))), d, cost))
                d += timedelta(days=1)
            raw['funded'][f'{name}|{cost}'] = rows
            for w, (a, b) in wins.items():
                sel = [r for r in rows if a <= date.fromisoformat(r['start']) and date.fromisoformat(r['start']) + timedelta(days=HORIZON) <= b]
                out['funded'][f'{name}|{cost}|{w}'] = summarize_funded(sel)
            print('funded', name, cost, json.dumps(out['funded'][f'{name}|{cost}|all']['20']), f'{time.time() - began:.0f}s', flush=True)
        # C. end-to-end historical
        for sc, (cost, handover) in SCEN.items():
            rows = []; d = DATA_START
            while d <= E2E_LAST_START:
                if d.weekday() < 5:
                    ch = window(events, epochs, midnight(d), midnight(d + timedelta(days=HORIZON)))
                    rows.append(e2e_one(plan, ch, lambda fd: window(events, epochs, midnight(fd), midnight(fd + timedelta(days=HORIZON))), d, cost, handover))
                d += timedelta(days=1)
            raw['e2e'][f'{name}|{sc}'] = rows
            for w, (a, b) in wins.items():
                sel = [r for r in rows if a <= date.fromisoformat(r['start']) < b]
                if sel: out['e2e'][f'{name}|{sc}|{w}_starts'] = summarize_e2e(sel)
            print('e2e', name, sc, json.dumps(out['e2e'][f'{name}|{sc}|all_starts']['20']), f'{time.time() - began:.0f}s', flush=True)
        # B + C Monte Carlo
        priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
        pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
        mondays, m_ = [], date(2021, 10, 11)
        while m_ + timedelta(days=T.BLOCK_DAYS) <= DATA_END: mondays.append(m_); m_ += timedelta(days=7)
        index = {m_: (bisect.bisect_left(ops, midnight(m_)), bisect.bisect_left(ops, midnight(m_ + timedelta(days=T.BLOCK_DAYS)))) for m_ in mondays}
        sd = date(2030, 1, 7); rng = random.Random(SEED); fr = {c: [] for c in ('recorded_exness', 'fixed_cost_stress')}
        for i in range(PATHS):
            ev = T.bootstrap_events(pool, mondays, index, rng, sd, priority)
            for c in fr: fr[c].append(funded_run(plan, ev, sd, c))
        for c, v in fr.items(): out['funded_mc'][f'{name}|{c}'] = summarize_funded(v)
        print('funded MC', name, json.dumps(out['funded_mc'][f'{name}|recorded_exness']['20']), f'{time.time() - began:.0f}s', flush=True)
        rng = random.Random(E2E_SEED); er = {sc: [] for sc in SCEN}
        for i in range(PATHS):
            ev = path_events(pool, mondays, index, rng, sd, priority, E2E_BLOCKS); ee = [x[0] for x in ev]
            ch = window(ev, ee, midnight(sd), midnight(sd + timedelta(days=HORIZON)))
            for sc, (cost, handover) in SCEN.items():
                er[sc].append(e2e_one(plan, ch, lambda fd: window(ev, ee, midnight(fd), midnight(fd + timedelta(days=HORIZON))), sd, cost, handover))
        for sc, v in er.items(): out['e2e_mc'][f'{name}|{sc}'] = summarize_e2e(v)
        print('e2e MC', name, json.dumps(out['e2e_mc'][f'{name}|base']['20']), f'{time.time() - began:.0f}s', flush=True)
    out['seconds'] = round(time.time() - began)
    (R / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    with gzip.open(R / 'OUTCOMES.json.gz', 'wt', encoding='utf-8') as f: json.dump(raw, f, separators=(',', ':'))
    print('done', out['seconds'], 's')


if __name__ == '__main__':
    {'freeze': freeze, 'run': run}[sys.argv[1]]()
