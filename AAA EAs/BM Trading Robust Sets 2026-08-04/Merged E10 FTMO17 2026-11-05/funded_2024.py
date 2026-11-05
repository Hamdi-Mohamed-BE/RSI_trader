"""Owner 2026-11-05: the same as equity_2024.py on a funded $100k account, no guard: when does it breach? Frozen engines (merged.engines), streams with 5-minute floating marks, one account
started 2024-01-01 at 1% of equity per trade (0.5% as a comparison), data ends 2026-10-06.
  FUNDED: compare.Funded control flow (FTMO standard funded rules: 10% max loss from the initial balance, 5% daily from the midnight balance, 80% rewards every 14 days withdrawn). Stops at the breach.
  RULES : no withdrawals, no firm stop; only records the first time equity touches the standard limits and the 1-Step limits (3% daily, 10% below the highest end-of-day balance).
Equity is marked every 5 minutes, so breaches include open losses, unlike the closed-balance figures. -> FUNDED_2024.json, FUNDED_2024.md
Run from EA store: uv run --with pandas --with numpy python "<this>" """
import importlib.util, json, subprocess, sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; NAMES = {'FTMO17': 'FTMO17', 'E10': 'E10', 'M22': 'Mixed (M22)'}; START = date(2024, 1, 1)


def iso(epoch): return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()


def job(name, risk):
    spec = importlib.util.spec_from_file_location('merged', H / 'merged.py'); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    S, F1, O, N, C = M.engines(); S.E.verify_freeze(); r = S.RISKS[risk]; data, plan, events, epochs = S.setup(name); P = S.P
    days = (P.DATA_END - START).days; ev = P.window(events, epochs, P.midnight(START), P.midnight(P.DATA_END)); s = P.start_dict(START, days)
    m = C.Funded(plan, name, s, False, r); curve = []; last_day = None; low = None
    for t, kind, pr_, key, row, mark in ev:
        if kind == 0:
            m.day_reset(t)
            if m.dead: break
        elif kind in (1, 4): m.closing(row, t)
        elif kind == 2: m.mark(row, mark, t)
        else: m.opening(row, t)
        if m.failed and not m.dead: m.dead = ('breach', m.phases[1]['fail_epoch']); low = len(m.active)
        d = iso(t)
        if d != last_day: curve.append((d, round(m.balance + m.withdrawn, 2), round(m.withdrawn, 2))); last_day = d
    if not m.dead:
        m.observe(s['horizon_epoch'] - 1e-4)
        if m.failed: m.dead = ('breach', m.phases[1]['fail_epoch']); low = len(m.active)
    ref = C.funded_one(plan, name, False, r, START, days, ev); end_epoch = m.dead[1] if m.dead else s['horizon_epoch']; pays = [p for p in m.payouts if p['epoch'] <= end_epoch + 1e-6]
    assert ref['end'] == (m.dead[0] if m.dead else 'alive') and abs(ref['income'] - sum(p['payout'] for p in pays)) < 0.01 and ref['trades'] == len(m.trades), 'differs from compare.funded_one'
    p1 = m.phases[1]; months = defaultdict(lambda: [0.0, 0])
    for x in m.trades: k = iso(x['cl'])[:7]; months[k][0] += x['net']; months[k][1] += 1
    out = dict(name=name, risk=r, end=m.dead[0] if m.dead else 'alive at data end', end_date=iso(end_epoch), alive_days=ref['alive_days'], breach_kind=p1.get('hard_failure_kind'), breach_equity=p1.get('terminal_equity'), breach_balance=p1.get('terminal_balance'),
               breach_anchor=p1.get('terminal_daily_anchor'), open_at_breach=low, trades=len(m.trades), wins=sum(x['net'] > 0 for x in m.trades), payouts=[dict(date=iso(p['epoch']), payout=round(p['payout'], 2)) for p in pays], income=round(sum(p['payout'] for p in pays), 2),
               net_trading=round(sum(x['net'] for x in m.trades), 2), max_equity_dd=round(m.max_dd, 2), max_closed_dd=round(m.max_closed_dd, 2), worst_day_equity=round(m.max_daily_loss, 2), months={k: dict(pnl=round(v[0], 2), trades=v[1]) for k, v in sorted(months.items())}, curve=curve)

    class Raw(N.make_ftmo1(True)):                       # no guard, no firm stop, no payouts: first touch of each rule set, floating losses included
        def __init__(self, *a, **k):
            super().__init__(*a, **k); self.t2 = self.t1 = None; self.xdd = 0.0; self.xpeak = self.C

        def observe(self, t):
            super().observe(t)
            if self.t2 is None and (self.eq <= 0.90 * self.C + 1e-8 or self.eq <= self.anchor - 0.05 * self.C + 1e-8): self.t2 = (iso(t), round(self.eq / self.C * 100 - 100, 2), round((self.eq - self.anchor) / self.C * 100, 2))
            if self.t1 is None and (self.eq <= self.floor() + 1e-8 or self.eq <= self.anchor - 0.03 * self.C + 1e-8): self.t1 = (iso(t), round(self.eq / self.C * 100 - 100, 2), round((self.eq - self.anchor) / self.C * 100, 2))
            self.xpeak = max(self.xpeak, self.eq); self.xdd = max(self.xdd, (self.xpeak - self.eq) / self.xpeak * 100)
            if self.failed: self.failed = False; self.current()['status'] = 'pending'

        def maybe_pass(self, t): return

        def reject_reason(self, row, t, risk_, margin): return C.unguarded_reject(self, row, t, margin)

    raw = Raw(plan, name, s, False, r); res = P.drive(raw, ev).result()
    out['no_firm_stop'] = dict(first_touch_standard=raw.t2, first_touch_1step=raw.t1, end_return_pct=round(res['ending_balance'] / raw.C * 100 - 100, 1), max_equity_dd_pct=round(raw.xdd, 2), trades=len(res['trades']))
    (H / f'FUND24-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, risk, flush=True)


def table():
    rows = {(n, r): json.loads((H / f'FUND24-{n}-{r}.json').read_text(encoding='utf-8')) for n in NAMES for r in ('1.00', '0.50')}
    (H / 'FUNDED_2024.json').write_text(json.dumps({f'{a}-{b}': v for (a, b), v in rows.items()}, indent=1), encoding='utf-8')
    L = ['| Profile | Risk | Result | Date | Days alive | How | Equity at the breach vs start / that day | Trades | Rewards paid (count) | Worst equity DD | Worst closed DD | First touch if it kept going: standard / 1-Step rules | Kept going: end return, equity DD |', '|---|---|---|---|---:|---|---|---:|---|---:|---:|---|---|']
    for (n, r), x in rows.items():
        C = 100000; f = x['no_firm_stop']; eq = f"{(x['breach_equity'] / C - 1) * 100:+.1f}% / {(x['breach_equity'] - x['breach_anchor']) / C * 100:+.1f}%" if x['breach_equity'] else '-'
        L.append(f"| {NAMES[n]} | {float(r):g}% | {x['end']} | {x['end_date']} | {x['alive_days']:.0f} | {x['breach_kind'] or '-'} | {eq} | {x['trades']} | ${x['income']:,.0f} ({len(x['payouts'])}) | ${x['max_equity_dd']:,.0f} | ${x['max_closed_dd']:,.0f} | {f['first_touch_standard'][0] if f['first_touch_standard'] else 'never'} / {f['first_touch_1step'][0] if f['first_touch_1step'] else 'never'} | {f['end_return_pct']:+,.0f}%, {f['max_equity_dd_pct']}% |")
    for (n, r), x in rows.items():
        if r != '1.00': continue
        L += ['', f"## {NAMES[n]}, $100k at 1%, by month until the end (trading P&L, % of $100k)", '| Month | Net | % | Trades |', '|---|---:|---:|---:|']
        L += [f"| {k} | ${v['pnl']:+,.0f} | {v['pnl'] / 1000:+.1f}% | {v['trades']} |" for k, v in x['months'].items()]
    (H / 'FUNDED_2024.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'job': job(a[1], a[2])
    elif a and a[0] == 'table': table()
    else:
        procs = [subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'job', n, r]) for n in NAMES for r in ('1.00', '0.50')]
        assert all(p.wait() == 0 for p in procs); table()
