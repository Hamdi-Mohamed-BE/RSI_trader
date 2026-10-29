"""Five portfolios under FTMO 2-step rules at 0.5% / 0.75% / 1% risk (owner request 2026-10-22):
challenge pass rate and median days, then funded $100k monthly income and days until the account ends (breach or freeze).

Reuses the frozen engines unchanged (FTMO Faster Portfolio Screen core engine -> Dial Study trial -> FTMO First Payout
Study sizes/income/lowrisk models). New here: the 17-EA and 5-ORB signal streams (same five-year native sources as the
nine-EA streams, parity-checked) and an unguarded model for the two portfolios that have no Calyx admission guard.
No MT5 terminal, no trading.

python compare.py prepare | run <portfolio> <risk> challenge|funded | table
"""
import bisect, hashlib, importlib.util, json, math, random, statistics, sys, time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent
PAYOUT = B / 'FTMO First Payout Study 2026-10-20'; OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


L = load('lowrisk', PAYOUT / 'lowrisk.py'); I, S, P, T, D, E = L.I, L.S, L.P, L.T, L.D, L.E
PR = load('older_prepare', OLDER / 'prepare.py')
SIZE = 100000; K = SIZE / 10000; COST = 'recorded_exness'; HANDOVER = 'next_prague_midnight'
RISKS = {'0.50': 0.005, '0.75': 0.0075, '1.00': 0.01}
NINE = 'CORE4_PLUS_FIVE_ORBS_05R'
PORTFOLIOS = {
    'ftmo': dict(label='FTMO guarded · Current 14 + ORB (17 EAs)', stream='FTMO17', basket='FTMO17', guard=True),
    'current14-orb05': dict(label='Current 14 + ORB 0.5R (17 EAs, no guard)', stream='CUR17', basket='FTMO17', guard=False),
    'orbs-only': dict(label='ORB-only (5 ORBs, no guard)', stream='ORB5', basket='ORB5', guard=False),
    'prop-ready': dict(label='Prop ready (9 EAs, Nasdaq DI ON)', stream='DI_ON', basket=NINE, guard=True),
    'best-prop': dict(label='Best Prop (9 EAs, Nasdaq DI OFF)', stream='DI_OFF', basket=NINE, guard=True),
}
MAPPING = {'FTMO17': 'ftmo', 'CUR17': 'current14-orb05', 'ORB5': 'orbs-only'}


# ---------------------------------------------------------------- signal streams
def threeway_candidates(src, lookup, slug, begin, end):
    """3 Way Gold runs three concurrent modules (magic 930930100/101/102) with partial exits, which the frozen candidate
    builder rejects. Each module becomes its own lane (as in the real EA); partial exits are collapsed at the final close;
    no intratrade floating marks (one shared equity curve cannot be split between concurrent positions)."""
    import csv
    from collections import defaultdict
    case, folder = src['case'], src['folder']
    by_pid = defaultdict(list)
    for d in csv.DictReader((folder / 'deals.csv').open(encoding='utf-8-sig')): by_pid[int(d['position_id'])].append(d)
    out, lanes = [], defaultdict(list)
    for t in sorted(case['trades'], key=lambda t: (t['open_epoch'], t['position_id'])):
        if not begin <= t['open_epoch'] < end: continue
        boundary = any('end of test' in x.lower() for x in t['exit_comments']); old = lookup.get((slug, t['position_id']))
        if old is None: assert boundary, ('Unmapped ordinary trade', slug, t['position_id'])
        unit_risk = old['unit_risk'] if old else abs(t['open_price'] - t['sl']) * 100.
        opened = [d for d in by_pid[t['position_id']] if int(d['entry']) == 0]; assert len(opened) == 1
        lane = f"{slug}#{t['magic']}"; lanes[lane].append(t)
        out.append(dict(id=lane + '|' + str(t['position_id']), ea=lane, symbol='XAUUSD', position_id=t['position_id'], op=t['open_epoch'],
                        cl=None if boundary else t['close_epoch'], source_forced_close_epoch=t['close_epoch'] if boundary else None, end_censored=boundary,
                        side=t['side'], open_price=t['open_price'], close_price=t['close_price'], sl=t['sl'], tp=t['tp'], unit_risk=unit_risk,
                        source_volume=t['volume'], entry_unit_cost=sum(float(opened[0][k]) for k in ('gross', 'commission', 'swap', 'fee')) / t['volume'],
                        unit_gross=t['gross'] / t['volume'], unit_commission=(t['commission'] + t['fee']) / t['volume'], unit_swap=t['swap'] / t['volume'], marks=[]))
    within = {lane: sum(a['close_epoch'] > b['open_epoch'] for a, b in zip(v, v[1:])) for lane, v in lanes.items()}
    return out, within


def prepare():
    long_dir = PR.LONG; plan = PR.read(long_dir / 'PLAN.json'); state = PR.read(long_dir / 'RUN_STATUS.json'); rows = PR.read(long_dir / 'RISK_ROWS.json')
    begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END)
    ref = json.loads((P.RT / 'INPUTS-DI_ON.json').read_text(encoding='utf-8'))
    out = dict(sources={})
    for name, mapping in MAPPING.items():
        lookup = {(x['key'], x['position_id']): x for x in rows[mapping]}
        cands = []
        for slug, cid in plan['mappings'][mapping].items():
            case_row = next(x for x in plan['cases'] if x['case_id'] == cid); receipt = state['complete'][cid]
            for file, digest in case_row['production_hashes'].items():
                assert sha(file) == digest, ('production source changed', file)
            path = Path(receipt['path']); assert sha(path) == receipt['sha256']
            src = dict(row=case_row, case=PR.read(path), folder=path.parent)
            if slug == '3-way-gold':
                extra, within = threeway_candidates(src, lookup, slug, begin, end); cands += extra
                out[f'{name}|3-way-gold module overlaps within a lane (second position blocked as same-EA exposure)'] = within
            else:
                cands += PR.candidates(src, lookup, slug, begin, end)
            out['sources'][f'{name}|{slug}'] = dict(case=cid, sha256=receipt['sha256'], history_quality=src['case'].get('native', {}).get('history_quality'))
        data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=[P.DATA_START.isoformat(), P.DATA_END.isoformat()])
        (R / f'INPUTS-{name}.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
        out[name] = dict(Counter(c['ea'] for c in cands))
        print(name, len(cands), out[name], flush=True)
    # Parity: the nine shared EAs of the FTMO17 stream must equal the retest's DI ON stream exactly.
    ftmo = json.loads((R / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))['candidates']
    nine = set(P.T.D.e.read(P.T.FASTER / 'PLAN.json')['baskets'][NINE])
    key = lambda c: c['id']  # noqa: E731
    mine = sorted((c for c in ftmo if c['ea'] in nine), key=key); theirs = sorted(ref['candidates'], key=key)
    assert mine == theirs, 'FTMO17 stream differs from the retest DI ON stream for the shared nine EAs'
    out['parity_nine_vs_retest_DI_ON'] = dict(candidates=len(mine), identical=True)
    (R / 'SOURCES.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print('parity nine EAs identical', len(mine))


def setup(stream):
    path = (P.RT if stream in ('DI_ON', 'DI_OFF') else R) / f'INPUTS-{stream}.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    plan = T.splan_for(data['window'])
    ftmo17 = sorted({c['ea'] for c in json.loads((R / 'INPUTS-FTMO17.json').read_text(encoding='utf-8'))['candidates']})
    plan['baskets']['FTMO17'] = ftmo17
    plan['baskets']['ORB5'] = ['us100-h1-orb-13utc', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30']
    plan['candidate_priority'] = plan['candidate_priority'] + [s for s in ftmo17 if s not in plan['candidate_priority']]
    events = E.master_events(plan, data)
    return data, plan, events, [x[0] for x in events]


# ---------------------------------------------------------------- models
def unguarded_lots(equity, unit, spec, r):
    """EA request r% of equity, rounded UP to the lot step (Calyx standard), broker minimum if below. No cap."""
    if not math.isfinite(equity) or not math.isfinite(unit) or equity <= 0 or unit <= 0: return 0.
    raw = equity * r / unit
    lot = math.ceil((min(raw, spec['maximum']) - 1e-12) / spec['step']) * spec['step']
    return round(min(spec['maximum'], max(spec['minimum'], lot)), 8)


def open_position(m, row, t, guard, r):
    """ScaledChallenge/LowRisk opening with the portfolio basket, risk r and guard on/off (identical bookkeeping)."""
    m.observe(t); m.maybe_pass(t)
    if row['ea'] not in m.plan['baskets'][m.portfolio]: return
    if row['op'] < m.start['epoch']: return
    if any(p['row']['ea'] == row['ea'] for p in m.active.values()): m.counts['same_ea_exposure'] += 1; return
    spec = m.specs[row['symbol']]
    if guard:
        m.cap_now = m.C * r; lot, requested = L.guard_lots(m.eq, row['unit_risk'], spec, min(m.cap_now, m.eq * r))
    else:
        lot = requested = unguarded_lots(m.eq, row['unit_risk'], spec, r)
    if lot <= 0: m.counts['minimum_lot_over50_or_source_request'] += 1; return
    risk = lot * row['unit_risk']; margin = lot * E.margin_per_lot(row, spec); reason = m.reject_reason(row, t, risk, margin)
    if reason: m.counts[reason] += 1; return
    if guard: assert risk <= m.cap_now + 1e-7 and lot <= requested + 1e-8
    fee = round(row['entry_unit_cost'] * lot, 2); m.balance = round(m.balance + fee, 2)
    m.active[row['id']] = dict(row=row, lots=lot, requested_lots=requested, risk=risk, margin=margin, mark_unit=0., mark_epoch=None, entry_cash=fee, phase=m.phase)
    m.last_entry = t; m.daily_entries += 1; m.days.add(str(E.day_of(t))); p = m.current(); p['entries'] += 1; p['entry_days'] = sorted(m.days)
    if p['first_trade_epoch'] is None: p['first_trade_epoch'] = t
    m.counts['opened'] += 1; m.observe(t)


def unguarded_reject(m, row, t, margin):
    """No Calyx admission guard: only FTMO account state and broker margin."""
    existing = sum(p['margin'] for p in m.active.values())
    if margin > m.eq - existing + 1e-8: return 'proxy_shared_margin'
    return None


class Challenge(S.ScaledChallenge):
    def __init__(self, plan, basket, start, guard, r):
        super().__init__(plan, basket, start, COST, HANDOVER, [(-1e9, P.CAP)], K); self.guard = guard; self.r = r; self.cap_now = self.C * r

    def cap(self): return self.C * self.r

    def reject_reason(self, row, t, risk, margin):
        if self.guard: return super().reject_reason(row, t, risk, margin)
        if self.failed: return 'permanent_hard_failure'
        if self.finished: return 'both_phases_completed'
        if self.current()['status'] != 'pending': return 'phase_review_wait'
        if self.balance >= self.target() - 1e-8 and len(self.days) >= 4: return 'target_entry_gate_await_flat'  # trader stops at target
        return unguarded_reject(self, row, t, margin)

    def opening(self, row, t): open_position(self, row, t, self.guard, self.r)


class Funded(I.Income):
    def __init__(self, plan, basket, start, guard, r):
        super().__init__(plan, start, COST, K, L.THRESHOLD); self.portfolio = basket; self.guard = guard; self.r = r; self.cap_now = self.C * r

    def cap(self): return self.C * self.r

    def reject_reason(self, row, t, risk, margin):
        if self.guard: return super().reject_reason(row, t, risk, margin)
        if self.failed: return 'permanent_hard_failure'
        return unguarded_reject(self, row, t, margin)

    def opening(self, row, t):
        before = self.last_entry; open_position(self, row, t, self.guard, self.r)
        if self.last_entry != before: self.buffer_at_entry = self.counts.get('soft_total_buffer9200', 0)


def challenge_one(plan, basket, guard, r, d, ev):
    m = Challenge(plan, basket, P.start_dict(d, P.HORIZON), guard, r)
    return T.per_trial(P.drive(m, ev).result())


def funded_one(plan, basket, guard, r, d, days, ev):
    """lowrisk.live2 control flow with this model."""
    s = P.start_dict(d, days); m = Funded(plan, basket, s, guard, r)
    for t, kind, pr_, key, row, mark in ev:
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


def mc_pool(data, plan):
    priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    pool = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op']); ops = [c['op'] for c in pool]
    mondays, m_ = [], date(2021, 10, 11)
    while m_ + timedelta(days=T.BLOCK_DAYS) <= P.DATA_END: mondays.append(m_); m_ += timedelta(days=7)
    index = {m_: (bisect.bisect_left(ops, P.midnight(m_)), bisect.bisect_left(ops, P.midnight(m_ + timedelta(days=T.BLOCK_DAYS)))) for m_ in mondays}
    return pool, mondays, index, priority


def run(slug, risk, part):
    E.verify_freeze(); cfg = PORTFOLIOS[slug]; r = RISKS[risk]; began = time.time()
    data, plan, events, epochs = setup(cfg['stream']); basket, guard = cfg['basket'], cfg['guard']
    pool, mondays, index, priority = mc_pool(data, plan); sd = date(2030, 1, 7)
    out = dict(portfolio=slug, label=cfg['label'], risk=r, part=part, size=SIZE, cost=COST, guard=guard, stream=cfg['stream'])
    if part == 'challenge':
        rows = []; d = P.DATA_START
        while d + timedelta(days=P.HORIZON) <= P.DATA_END:
            if d.weekday() < 5: rows.append(challenge_one(plan, basket, guard, r, d, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=P.HORIZON)))))
            d += timedelta(days=1)
        out['hist'] = T.summarize(rows)
        print(slug, risk, 'challenge hist', json.dumps({k: out['hist'][k] for k in ('pass_both_180', 'breach', 'median_days_both', 'median_days_funded')}), f'{time.time() - began:.0f}s', flush=True)
        rng = random.Random(T.SEED); mc = []
        for i in range(T.PATHS):
            mc.append(challenge_one(plan, basket, guard, r, sd, T.bootstrap_events(pool, mondays, index, rng, sd, priority)))
        out['mc'] = T.summarize(mc)
    else:
        rows = []; d = P.DATA_START
        while d <= I.HIST_LAST_START:
            if d.weekday() < 5: rows.append(funded_one(plan, basket, guard, r, d, I.HIST_DAYS, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=I.HIST_DAYS)))))
            d += timedelta(days=1)
        out['hist'] = L.summarize(rows, I.HIST_DAYS)
        print(slug, risk, 'funded hist', json.dumps({k: out['hist'][k] for k in ('ends', 'median_days_to_end', 'pooled_income_per_alive_month')}), f'{time.time() - began:.0f}s', flush=True)
        days = T.BLOCK_DAYS * I.MC_BLOCKS; rng = random.Random(I.MC_SEED); mc = []
        for i in range(P.PATHS):
            mc.append(funded_one(plan, basket, guard, r, sd, days, P.path_events(pool, mondays, index, rng, sd, priority, I.MC_BLOCKS)))
        out['mc'] = L.summarize(mc, days)
    out['seconds'] = round(time.time() - began)
    (R / f'RESULT-{slug}-{risk}-{part}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('done', slug, risk, part, out['seconds'], 's', flush=True)


def parity():
    """Best Prop guarded funded at 1% must equal lowrisk SET_1.00 (recorded) exactly; challenge vs retest MC/OOS not comparable (100k)."""
    data, plan, events, epochs = setup('DI_OFF'); pool, mondays, index, priority = mc_pool(data, plan); sd = date(2030, 1, 7)
    rows = []; d = P.DATA_START
    while d <= I.HIST_LAST_START:
        if d.weekday() < 5: rows.append(funded_one(plan, NINE, True, 0.01, d, I.HIST_DAYS, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=I.HIST_DAYS)))))
        d += timedelta(days=1)
    got = L.summarize(rows, I.HIST_DAYS); ref = json.loads((PAYOUT / 'LOWRISK-CAPS_0.50-recorded_exness.json').read_text(encoding='utf-8'))
    ref1 = json.loads((PAYOUT / 'LOWRISK-SET_1.00-recorded_exness.json').read_text(encoding='utf-8'))
    same = got == ref1['hist']['all_starts']
    print('funded hist parity vs lowrisk SET_1.00:', same)
    if not same:
        for k in got:
            if got[k] != ref1['hist']['all_starts'].get(k): print('  diff', k, got[k], ref1['hist']['all_starts'].get(k))
    (R / 'PARITY.json').write_text(json.dumps(dict(funded_hist_vs_lowrisk_SET_1_00=same), indent=1), encoding='utf-8')
    return same


def table():
    X = {(p.stem.split('-', 1)[1].rsplit('-', 2)[0], p.stem.rsplit('-', 2)[1], p.stem.rsplit('-', 1)[1]): json.loads(p.read_text(encoding='utf-8'))
         for p in sorted(R.glob('RESULT-*.json'))}
    pct = lambda v: '-' if v is None else f'{100 * v:.0f}%'; usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    days = lambda v, h: f'> {h}' if v is None else f'{v:g}'  # noqa: E731
    lines = ['# Five portfolios under FTMO 2-step rules · $100k · recorded Exness costs (generated from RESULT-*.json)', '',
             'Challenge: phase 1 +10%, phase 2 +5%, min 4 trading days, 5% daily / 10% max loss, 180-day horizon from purchase.',
             'Funded: $100k, 80% split, reward every 14 days (min $20), balance re-baselined after each reward, until breach or freeze.',
             'MC = 2,000 block-bootstrap paths (4-week blocks) from the 2021-10-07 → 2026-10-06 signal pool; History = every weekday start.', '']
    for src, title in (('mc', 'Monte Carlo'), ('hist', 'History, every weekday start')):
        lines += [f'## Challenge · {title}', '', '| Portfolio | Risk / trade | Pass both ≤180 d | Funded ≤90 d | Breach | Stuck at buffer | Median days to pass both | Median days to funded | Median challenge trades |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for slug, cfg in PORTFOLIOS.items():
            for risk in RISKS:
                x = X.get((slug, risk, 'challenge'))
                if not x: continue
                s = x[src]
                lines.append(f"| {cfg['label']} | {risk}% | {pct(s['pass_both_180'])} | {pct(s['funded_90'])} | {pct(s['breach'])} | {pct(s['stalled_buffer'])} | "
                             f"{s['median_days_both'] if s['median_days_both'] is not None else '-'} | {s['median_days_funded'] if s['median_days_funded'] is not None else '-'} | {s['median_trades']:g} |")
        lines.append('')
    for src, title in (('mc', 'Monte Carlo 36 months'), ('hist', 'History 12-month horizon, every weekday start')):
        lines += [f'## Funded $100k · {title}', '', '| Portfolio | Risk / trade | Avg monthly income while trading | Median days until the account ends | Breach / frozen | Still trading at horizon | Total income until end (median / mean) | First reward (share / median $) | Trades / month | / weekday |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for slug, cfg in PORTFOLIOS.items():
            for risk in RISKS:
                x = X.get((slug, risk, 'funded'))
                if not x: continue
                s = x[src]; n = s['n']; e = s['ends']
                lines.append(f"| {cfg['label']} | {risk}% | {usd(s['pooled_income_per_alive_month'])} | {days(s['median_days_to_end'], s['horizon_days'])} | "
                             f"{pct(e.get('breach', 0) / n)} / {pct(e.get('frozen', 0) / n)} | {pct(s['alive_at_horizon'])} | {usd(s['income_total_median'])} / {usd(s['income_total_mean'])} | "
                             f"{pct(s['first_payout_share'])} / {usd(s['first_payout_median'])} | {s['trades_per_month_alive_median']} | {s['trades_per_weekday_alive_median']} |")
        lines.append('')
    (R / 'TABLES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8'); print('\n'.join(lines))


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'prepare': prepare()
    elif c == 'parity': parity()
    elif c == 'run': run(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == 'table': table()
