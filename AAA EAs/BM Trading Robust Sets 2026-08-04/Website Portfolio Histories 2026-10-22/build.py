"""Website histories for the two nine-EA guarded portfolios (owner request 2026-10-22: publish Best Prop and every
portfolio on /portfolios). Same frozen engine, signal inputs and continuous (no phase target) model as
Best Prop Portfolio Retest 2026-10-20; every website window is replayed from a fresh $10,000 account.
No MT5 terminal, no trading. Parity: the retest's continuous OOS results must be reproduced exactly first.

python build.py   -> HISTORIES.json
"""
import bisect, hashlib, importlib.util, json, sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
RETEST = B / 'Best Prop Portfolio Retest 2026-10-20'
END = date(2026, 10, 6)  # same saved coverage end as the other published portfolios (signal ledgers end here)
PERIODS = [('3m', '3 months', 3), ('6m', '6 months', 6), ('1y', '1 year', 12), ('3y', '3 years', 36), ('5y', '5 years', 60)]
# slug: (signal stream = Nasdaq DI default of the package, per-entry cap on $10,000)
PORTFOLIOS = {'best-prop': ('DI_OFF', 100.0), 'prop-ready': ('DI_ON', 50.0)}
COST = 'recorded_exness'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


RT = load('retest', RETEST / 'retest.py'); D = RT.D


def period_start(end, months):
    import calendar
    y, m = divmod(end.year * 12 + end.month - 1 - months, 12)
    return date(y, m + 1, min(end.day, calendar.monthrange(y, m + 1)[1]))


class Continuous(D.DialTrial):
    """Identical to retest.continuous(): no phase targets; guard limits scale with the per-entry cap ($50 = Prop Ready,
    $100 = Best Prop: total 225/450, per symbol 150/300); $300 daily reserve and $9,200 buffer as in both packages."""

    def maybe_pass(self, t): return

    def reject_reason(self, row, t, risk, margin):
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


def replay(plan, events, epochs, cap, first, last):
    start = dict(date=first.isoformat(), epoch=RT.midnight(first), horizon_date=last.isoformat(), horizon_epoch=RT.midnight(last))
    m = Continuous(plan, D.BASKET, start, COST, 'next_prague_midnight', [(-1e9, cap)])
    for t, kind, _, _, row, mark in events[bisect.bisect_left(epochs, start['epoch']):bisect.bisect_left(epochs, start['horizon_epoch'])]:
        if kind == 0: m.day_reset(t)
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
    return m.result()


def main():
    frozen = json.loads((RETEST / 'FROZEN.json').read_text(encoding='utf-8'))['files']
    for p, h in frozen.items():
        assert sha(p) == h, f'retest input changed after its freeze: {p}'
    reference = json.loads((RETEST / 'RESULTS.json').read_text(encoding='utf-8'))['continuous']
    out = dict(engine='Best Prop Portfolio Retest 2026-10-20 (frozen FTMO Faster Portfolio Screen core engine + FTMO Dial Study trial)',
               cost=COST, end_exclusive=END.isoformat(), parity={}, portfolios={}, retest_frozen=frozen)
    streams = {}
    for name in ('DI_OFF', 'DI_ON'):
        data = json.loads((RETEST / f'INPUTS-{name}.json').read_text(encoding='utf-8'))
        plan = RT.splan_for(data['window']); events = D.e.master_events(plan, data)
        streams[name] = (plan, events, [x[0] for x in events], date.fromisoformat(data['window'][0]))
        # Parity: Best Prop ($100) continuous OOS from the retest, both streams.
        res = replay(plan, events, streams[name][2], 100.0, *RT.OOS)
        nets = [x['net'] for x in res['trades']]; ref = reference[f'{name}|{COST}']
        got = dict(trades=len(nets), net=round(sum(nets), 2), max_sampled_equity_dd=round(res['max_sampled_equity_drawdown_cash'], 2))
        want = {k: ref[k] for k in got}
        assert got == want, ('parity failed', name, got, want)
        out['parity'][name] = dict(window=[str(RT.OOS[0]), str(RT.OOS[1])], cap=100.0, reproduced=got)
        print('PARITY', name, got, flush=True)
    for slug, (name, cap) in PORTFOLIOS.items():
        plan, events, epochs, first_day = streams[name]
        rows = {}
        for period, title, months in PERIODS:
            requested = period_start(END, months); first = max(requested, first_day)
            res = replay(plan, events, epochs, cap, first, END)
            trades = [dict(slug=x['ea'], position_id=i, close_time=datetime.fromtimestamp(x['cl'], timezone.utc).isoformat(), net_profit=x['net'])
                      for i, x in enumerate(res['trades'])]
            rows[period] = dict(title=title, requested_start=requested.isoformat(), start=first.isoformat(), end_exclusive=END.isoformat(),
                                trades=trades, breached=res['outcome'].startswith('failed'), ending_balance=round(res['ending_balance'], 2),
                                max_sampled_equity_dd_cash=round(res['max_sampled_equity_drawdown_cash'], 2),
                                worst_day_sampled_equity_loss_cash=round(res['max_daily_sampled_equity_loss'], 2),
                                blocked=dict(Counter({k: v for k, v in res['counts'].items() if k.startswith(('daily_', 'aggregate', 'same_', 'soft_', 'proxy', 'entry_', 'minimum', 'permanent'))})))
            print(slug, period, len(trades), round(sum(t['net_profit'] for t in trades), 2), 'eqDD', rows[period]['max_sampled_equity_dd_cash'], flush=True)
        out['portfolios'][slug] = dict(stream=name, cap=cap, periods=rows)
    (R / 'HISTORIES.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('written', R / 'HISTORIES.json')


if __name__ == '__main__':
    main()
