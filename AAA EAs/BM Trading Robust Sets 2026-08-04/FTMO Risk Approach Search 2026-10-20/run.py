"""FTMO risk-approach search: funded within 90 days at >= 70% (PLAN.json). No MT5 / trading.

python run.py freeze | dev | val | oos
"""
import bisect, copy, hashlib, importlib.util, itertools, json, math, os, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
SEARCH = B / 'FTMO Fastest Funded Search 2026-10-20'; DIAL = B / 'FTMO Dial Study 2026-10-20'; FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
PACKAGE = B / '_00 Live profiles/Packages/FTMO/PACKAGE.json'
PLAN = json.loads((R / 'PLAN.json').read_text(encoding='utf-8'))
L = PLAN['levers']; COSTS = ['recorded_exness', 'fixed_cost_stress']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


S = load('search', SEARCH / 'run.py')     # starts(), WINDOWS, G_BASKETS (read-only use)


def configs():
    out = []
    for bk, c1, p2, latch, buf in itertools.product(L['basket'], L['phase1_cap_usd'], ('same', 'half'), L['daily_latch_and_reserve_usd'], L['entry_equity_buffer_usd']):
        out.append(dict(basket=bk, cap1=c1, cap2=c1 if p2 == 'same' else c1 / 2, phase2=p2, latch=latch, buffer=buf))
    return out


def freeze():
    files = [R / 'PLAN.json', Path(__file__), SEARCH / 'run.py', SEARCH / 'INPUTS-5y.json', SEARCH / 'ELIGIBILITY.json', SEARCH / 'DEV.json', DIAL / 'run.py', FASTER / 'core_engine.py']
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files), 'configs', len(configs()))


def check_frozen():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'


G = {}


def init_worker():
    d = load('dial', DIAL / 'run.py'); e = d.e
    data = json.loads((SEARCH / 'INPUTS-5y.json').read_text(encoding='utf-8'))
    plan = copy.deepcopy(e.read(FASTER / 'PLAN.json'))
    plan['history'] = dict(plan['history'], start_prague=data['window'][0], end_exclusive_prague=data['window'][1])
    plan['candidate_priority'] = [x['slug'] for x in json.loads(PACKAGE.read_text(encoding='utf-8-sig'))['entries'] if x['slug'] in data['eligible']]
    plan['baskets'] = json.loads((SEARCH / 'ELIGIBILITY.json').read_text(encoding='utf-8'))['baskets']
    events = e.master_events(plan, data)

    class RiskTrial(d.DialTrial):
        def __init__(self, plan, portfolio, start, cost, handover, cfg):
            super().__init__(plan, portfolio, start, cost, handover, [(-1e9, cfg['cap1'])])
            self.cfg = cfg

        def cap(self):
            return self.cfg['cap1'] if self.phase == 1 else self.cfg['cap2']

        def observe(self, t):
            self.eq = self.equity(t); self.peak = max(self.peak, self.eq); self.closed_peak = max(self.closed_peak, self.balance)
            self.max_dd = max(self.max_dd, self.peak - self.eq); self.max_closed_dd = max(self.max_closed_dd, self.closed_peak - self.balance)
            self.max_daily_loss = max(self.max_daily_loss, self.anchor - self.eq)
            self.max_risk = max(self.max_risk, sum(p['risk'] for p in self.active.values())); self.max_margin = max(self.max_margin, sum(p['margin'] for p in self.active.values()))
            self.mark_observations += len(self.active)
            for p in self.active.values():
                if p['mark_epoch'] is None: self.zero_mark_observations += 1; self.max_first_mark_lag = max(self.max_first_mark_lag, t - p['row']['op'])
                else:
                    age = max(0, t - p['mark_epoch']); self.max_mark_age = max(self.max_mark_age, age); self.stale_mark_observations += age > 900
            if self.failed or self.finished or self.current()['status'] != 'pending': return
            if self.eq <= 9000.0 + 1e-8 or self.eq <= self.anchor - 500.0 + 1e-8:
                self.exact_floor_touches += abs(self.eq - 9000) <= 1e-8 or abs(self.eq - (self.anchor - 500)) <= 1e-8
                p = self.current(); p.update(status='failed', fail_epoch=t, terminal_balance=self.balance, terminal_equity=self.eq, terminal_daily_anchor=self.anchor,
                                              hard_failure_kind='static' if self.eq <= 9000 + 1e-8 else 'daily')
                self.failed = True; self.counts['hard_' + p['hard_failure_kind'] + '_failure'] += 1
            elif self.eq <= self.anchor - self.cfg['latch'] + 1e-8:
                if not self.day_stopped: self.counts['daily_300_latches'] += 1
                self.day_stopped = True

        def reject_reason(self, row, t, risk, margin):
            m = self.cap_now / 50
            if self.failed: return 'permanent_hard_failure'
            if self.finished: return 'both_phases_completed'
            if self.current()['status'] != 'pending': return 'phase_review_wait'
            if self.day_stopped: return 'daily_300_latch'
            if self.balance >= (11000 if self.phase == 1 else 10500) - 1e-8 and len(self.days) >= 4: return 'target_entry_gate_await_flat'
            if self.daily_entries >= 7: return 'daily_7_entry_limit'
            if self.daily_losses >= 3: return 'daily_3_closed_loss_limit'
            total = sum(p['risk'] for p in self.active.values()); same = sum(p['risk'] for p in self.active.values() if p['row']['symbol'] == row['symbol'])
            if total + risk > 225 * m + 1e-7: return 'aggregate_initial_risk225'
            if same + risk > 150 * m + 1e-7: return 'same_symbol_initial_risk150'
            reserve = sum(1.25 * p['risk'] + 5 for p in self.active.values())
            projected = min(self.eq, self.balance - reserve) - 1.25 * risk - 5
            if projected < self.cfg['buffer'] - 1e-8: return 'soft_total_buffer9200'
            if self.anchor - projected > self.cfg['latch'] + 1e-8: return 'soft_daily_reserve300'
            existing = sum(p['margin'] for p in self.active.values())
            if existing + margin > projected * .8 + 1e-8 or margin > self.eq - existing + 1e-8: return 'proxy_shared_margin'
            if t < self.last_entry + 3: return 'entry_reconciliation3s'
            return None

    G.update(d=d, e=e, plan=plan, events=events, epochs=[x[0] for x in events], RiskTrial=RiskTrial)


def replay(cfg, start, cost, window_events):
    m = G['RiskTrial'](G['plan'], cfg['basket'], start, cost, 'next_prague_midnight', cfg)
    for t, kind, priority, key, row, mark in window_events:
        if kind == 0: m.day_reset(t)
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
    return m.result()


def one(task):
    cfg, cost, window = task
    rows = []
    for s in S.starts(window):
        w = G['events'][bisect.bisect_left(G['epochs'], s['epoch']):bisect.bisect_left(G['epochs'], s['horizon_epoch'])]
        t = replay(cfg, s, cost, w)
        both = t['total_elapsed_to_both']['inclusive_prague_days'] if t['total_elapsed_to_both'] else None
        acc = t.get('access_5bd_illustration_epoch')
        fund = None if not acc else (datetime.fromtimestamp(acc, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1
        rows.append(dict(both=both, funded=fund, breach=t['outcome'].startswith('failed'), trades=len(t['trades']), eqdd=t['max_sampled_equity_drawdown_cash'],
                         day=t['max_daily_sampled_equity_loss'], buffer=t['counts'].get('soft_total_buffer9200', 0) > 0))
    n = len(rows); passed = [r for r in rows if r['both'] and not r['breach']]; active = [(r['both'] or 180) for r in rows]
    return dict(cfg=cfg, cost=cost, window=window, starts=n, pass_share=round(len(passed) / n, 4),
                funded_90=round(sum(1 for r in passed if r['funded'] <= 90) / n, 4), funded_60=round(sum(1 for r in passed if r['funded'] <= 60) / n, 4),
                breach_share=round(sum(r['breach'] for r in rows) / n, 4), breaches=sum(r['breach'] for r in rows),
                median_days_both=statistics.median([r['both'] for r in passed]) if passed else None,
                median_days_funded=statistics.median([r['funded'] for r in passed]) if passed else None,
                buffer_share=round(sum(r['buffer'] for r in rows) / n, 4), eqdd_max=round(max(r['eqdd'] for r in rows), 1), day_max=round(max(r['day'] for r in rows), 1),
                median_trades_per_month=round(statistics.median(r['trades'] / a * 30.4375 for r, a in zip(rows, active)), 2),
                median_trades_per_weekday=round(statistics.median(r['trades'] / max(1, a * 5 / 7) for r, a in zip(rows, active)), 3))


def combine(results):
    by = {}
    for r in results:
        by.setdefault((json.dumps(r['cfg'], sort_keys=True), r['window']), {})[r['cost']] = r
    out = []
    for (cfgs, win), v in by.items():
        a, b = v['recorded_exness'], v['fixed_cost_stress']; f = [x['median_days_funded'] for x in (a, b) if x['median_days_funded'] is not None]
        out.append(dict(cfg=json.loads(cfgs), window=win, avg_funded_90=round((a['funded_90'] + b['funded_90']) / 2, 4), avg_pass_180=round((a['pass_share'] + b['pass_share']) / 2, 4),
                        funded_90_recorded=a['funded_90'], funded_90_stress=b['funded_90'], max_breach_share=max(a['breach_share'], b['breach_share']),
                        avg_median_funded=round(sum(f) / len(f), 1) if len(f) == 2 else None, buffer_share_avg=round((a['buffer_share'] + b['buffer_share']) / 2, 4),
                        eqdd_max=max(a['eqdd_max'], b['eqdd_max']), day_max=max(a['day_max'], b['day_max']), starts=a['starts'],
                        median_trades_per_month=a['median_trades_per_month'], median_trades_per_weekday=a['median_trades_per_weekday'], detail=v))
    return out


def run(tasks):
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1), initializer=init_worker) as ex:
        return list(ex.map(one, tasks, chunksize=1))


def rank(r):
    return (-r['avg_funded_90'], r['max_breach_share'], r['avg_median_funded'] or 1e9, r['cfg']['cap1'])


def label(c):
    return f"{c['basket']} ${c['cap1']:g}/{c['cap2']:g} latch{c['latch']} buf{c['buffer']}"


def dev():
    check_frozen(); began = time.time()
    res = combine(run([(c, cost, 'dev') for c in configs() for cost in COSTS]))
    # parity: standard guard configs must equal the Fastest Search development results
    ref = {(r['basket'], r['cap']): r for r in json.loads((SEARCH / 'DEV.json').read_text(encoding='utf-8'))['results']}
    checked = 0
    for r in res:
        c = r['cfg']
        if c['phase2'] == 'same' and c['latch'] == 300 and c['buffer'] == 9200 and (c['basket'], c['cap1']) in ref:
            x = ref[(c['basket'], c['cap1'])]
            for cost in COSTS:
                a, b = r['detail'][cost], x['detail'][cost]
                assert a['pass_share'] == b['pass_share'] and a['median_days_funded'] == b['median_days_funded'] and a['breaches'] == b['breaches'], ('PARITY FAIL', c, cost)
            checked += 1
    assert checked >= 10, checked
    ok = sorted([r for r in res if r['max_breach_share'] <= .05 and r['avg_funded_90'] >= .70], key=rank)
    pool = ok if ok else sorted([r for r in res if r['max_breach_share'] <= .05], key=rank)
    finalists = [r['cfg'] for r in pool[:5]]
    (R / 'DEV.json').write_text(json.dumps(dict(mode='eligible' if ok else 'NO_CONFIGURATION_REACHED_70PCT', parity_checked=checked, eligible=len(ok),
                                                seconds=round(time.time() - began), finalists=finalists, results=sorted(res, key=rank)), indent=1), encoding='utf-8')
    print('mode', 'eligible' if ok else 'NONE >=70%', 'parity', checked, 'seconds', round(time.time() - began))
    for r in sorted(res, key=rank)[:15]:
        print(f"{label(r['cfg']):60} funded<=90 {r['avg_funded_90']:.3f} (rec {r['funded_90_recorded']:.3f} str {r['funded_90_stress']:.3f}) pass180 {r['avg_pass_180']:.3f} breach {r['max_breach_share']:.3f} med {r['avg_median_funded']} eqdd {r['eqdd_max']}")


def stage(window):
    check_frozen(); devr = json.loads((R / 'DEV.json').read_text(encoding='utf-8'))
    res = combine(run([(c, cost, window) for c in devr['finalists'] for cost in COSTS]))
    out = dict(results=res)
    if window == 'val':
        ok = sorted([r for r in res if r['max_breach_share'] <= .05 and r['avg_funded_90'] >= .70], key=rank)
        choice = (ok or sorted(res, key=rank))[0]
        out.update(choice=choice['cfg'], choice_meets_target=bool(ok))
    (R / f'{window.upper()}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for r in res:
        print(f"{window} {label(r['cfg']):60} funded<=90 {r['avg_funded_90']:.3f} pass180 {r['avg_pass_180']:.3f} breach {r['max_breach_share']:.3f} med {r['avg_median_funded']}")
    if window == 'val':
        print('CHOICE', label(out['choice']), 'meets target:', out['choice_meets_target'])


if __name__ == '__main__':
    cmd = sys.argv[1]
    {'freeze': freeze, 'dev': dev}.get(cmd, lambda: stage(cmd))()
