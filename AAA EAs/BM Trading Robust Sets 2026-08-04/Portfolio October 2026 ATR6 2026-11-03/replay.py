"""October 2026 replay of every installable portfolio profile, from the native October member ledgers of run.py, with the new
Nasdaq 5M (ATR6 stop) and, for comparison, the old one (0.60% stop). News EAs are excluded everywhere (owner 2026-11-03).

Method (R replay, not the website's exact engine, which needs each trade's initial stop):
- R per trade = net profit / (1% of the standalone run's balance at entry); commission, swap and spread are inside the net.
- Portfolio P&L per trade = its risk budget x R, one fresh $10,000 account per profile, trades in time order.
- Guards are checked at entry from CLOSED balance (floating equity, margin and close-all actions are not modelled):
  * FTMO / Prop ready / Best Prop: budget B ($50 or $100); open risk <= 4.5B, per symbol <= 3B; Prague-day closed loss >= 3% blocks;
    max 7 entries and 3 losing closes per Prague day; no entry below 92% of $10,000.
  * funded_v1 / Turbo 5 (trailing-floor guards): floor = peak closed balance - 6% (locked at the start balance once +6%);
    budget = min(base, 5% of the room above the floor, Turbo also <= 0.3%); open <= 2%, per symbol <= 1.5%; a day's closed loss >= 2%
    or closed win >= 0.75% blocks new entries for that day; no entry when the room < 0.25%.
  * Current 14 + ORB, ORB-only: 0.5% of balance; Full EA (no news): 0.25% of balance (BAT default). The Full EA's native adaptive
    governor (drawdown / loss-streak tapers, 5% daily closed-loss stop) is NOT modelled, and member runs had it switched off.
- Default Nasdaq DI: ON in FTMO / Current14 / Prop ready / funded_v1 / Full EA; OFF in Best Prop 9 / 15 and Turbo 5.
python replay.py -> RESULTS.md / RESULTS.json"""
import gzip, json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent; PRAGUE = ZoneInfo('Europe/Prague')
PLAN = json.loads((ROOT / 'PLAN.json').read_text())
S0 = 10000.0
WEEKDAYS = sum(1 for i in range(31) if (date(2026, 10, 1) + timedelta(days=i)).weekday() < 5)
NAS = 'nasdaq-5m-candle-momentum'
C14 = [(p['key'], 'NEW') for p in PLAN if p['tag'] == 'NEW']
ORBS = [(k, 'NEW') for k in ('xau-orb-london-ny-overlap-m30', 'us100-h1-orb-13utc', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30')]
PR9 = [(k, 'NEW') for k in ('xau-rsi-vwap', 'usdjpy-london-open-momentum', 'us100-month-end-flow', NAS)] + ORBS
BP15 = PR9 + [(k, 'NEW') for k in ('ema3', '3-way-gold', 'gold-overnight-value-area', 'dmc-current-xau', 'dmc-fresh-reaction-us100')] + [('dmc-fresh-reaction-xau', 'FULL')]
FUNDED = [(NAS, 'NEW'), ('ema3', 'NEW'), ('3-way-gold', 'FULL'), ('orb-volume-profile-volume-confirmed', 'FUNDED'), ('xau-orb-london-ny-overlap-m30', 'NEW'),
          ('dmc-fresh-reaction-us100', 'NEW'), ('dmc-current-xau', 'NEW'), ('xau-rsi-vwap', 'NEW'), ('gold-overnight-value-area', 'NEW')]
TURBO = [('gold-overnight-value-area', 'NEW'), ('ema3', 'NEW'), (NAS, 'NEW'), ('xau-rsi-vwap', 'NEW'), ('3-way-gold', 'FULL')]
FULL = [(p['key'], 'FULL') for p in PLAN if p['tag'] == 'FULL']
CUSTOM7 = [(k, 'NEW') for k in ('ema3', 'dmc-current-xau', 'dmc-fresh-reaction-us100', NAS, 'gold-overnight-value-area', 'xau-rsi-vwap')] + [('dmc-fresh-reaction-xau', 'FULL')]
PROP = lambda b: dict(kind='prop', budget=b)  # noqa: E731
TRAIL = lambda base, cap=None: dict(kind='trail', base=base, cap=cap)  # noqa: E731
PROFILES = {  # slug: (label, members, sizing, Nasdaq DI)
    'ftmo': ('FTMO guarded - Current 14 + ORB 0.5R (17); the any-broker test build is identical in this model', C14, PROP(50.0), 'ON'),
    'ftmo-1pct': ('FTMO guarded 17 at 1% (prop selection pick; ANY BROKER TEST BAT with 1% chosen)', C14, PROP(100.0), 'ON'),
    'current14-orb05': ('Current 14 + ORB 0.5R (17)', C14, dict(kind='pct', pct=0.5), 'ON'),
    'orbs-only': ('ORB-only - all five at 0.5R (5)', ORBS, dict(kind='pct', pct=0.5), None),
    'prop-ready': ('Prop ready / Codex_Best_FTMO (9)', PR9, PROP(50.0), 'ON'),
    'best-prop': ('Best Prop 9', PR9, PROP(100.0), 'OFF'),
    'best-prop-15': ('Best Prop 15', BP15, PROP(100.0), 'OFF'),
    'funded-v1': ('funded_v1 (9)', FUNDED, TRAIL(0.5), 'ON'),
    'turbo5': ('Turbo 50k - Custom 5 Guarded (5)', TURBO, TRAIL(0.75, 0.3), 'OFF'),
    'full-eas': ('Full EA portfolio - Recommended Adaptive, news removed (32)', FULL, dict(kind='pct', pct=0.25), 'ON'),
    # owner 2026-11-03: custom 7 (EMA3, all three DMCs, Nasdaq 5M, Gold Overnight VA, XAU RSI VWAP) under each sizing used above
    'custom7-0.25': ('Custom 7', CUSTOM7, dict(kind='pct', pct=0.25), 'ON'),
    'custom7-0.5': ('Custom 7', CUSTOM7, dict(kind='pct', pct=0.5), 'ON'),
    'custom7-50': ('Custom 7', CUSTOM7, PROP(50.0), 'ON'),
    'custom7-100': ('Custom 7', CUSTOM7, PROP(100.0), 'ON'),
    'custom7-trail': ('Custom 7', CUSTOM7, TRAIL(0.5), 'ON')}


def ledger(key, tag):
    row = next(p for p in PLAN if p['key'] == key and p['tag'] == tag); d = ROOT / 'native' / row['case']
    meta = json.loads((d / 'run.json').read_text()); t = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    t.sort(key=lambda x: x['close_time']); bal = S0; out = []
    for x in t:
        o = datetime.fromisoformat(x['open_time']).replace(tzinfo=timezone.utc); c = datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc)
        out.append(dict(key=key, symbol=row['symbol'], o=o, c=c, R=x['net_profit'] / (0.01 * bal))); bal += x['net_profit']
    return out, meta['metrics']


def nasdaq_tag(old, di, member_tag):
    if di is None: return member_tag
    return {('ON', False): member_tag if member_tag == 'FULL' else 'NEW', ('ON', True): 'OLD', ('OFF', False): 'NEWDIOFF', ('OFF', True): 'OLDDIOFF'}[(di, old)]


def replay(members, sz, di, old):
    rows = []
    for k, tag in members:
        rows += ledger(k, nasdaq_tag(old, di, tag) if k == NAS else tag)[0]
    events = sorted([(r['o'], 1, i) for i, r in enumerate(rows)] + [(r['c'], 0, i) for i, r in enumerate(rows)])
    bal = peak = S0; dd = 0.0; open_ = {}; taken, blocked = [], defaultdict(int); locked = False
    day_pnl, day_entries, day_losses = defaultdict(float), defaultdict(int), defaultdict(int)
    for t, kind, i in events:
        r = rows[i]; day = t.astimezone(PRAGUE).date() if sz['kind'] == 'prop' else t.date()
        if kind == 0:
            if i not in open_: continue
            risk = open_.pop(i); pnl = risk * r['R']; bal += pnl; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
            locked = locked or peak >= 1.06 * S0
            day_pnl[day] += pnl; day_losses[day] += pnl < 0; taken.append(dict(r, pnl=pnl)); continue
        sym_open = sum(v for j, v in open_.items() if rows[j]['symbol'] == r['symbol']); tot_open = sum(open_.values()); why = None
        if sz['kind'] == 'pct':
            risk = bal * sz['pct'] / 100
        elif sz['kind'] == 'prop':
            risk = b = sz['budget']
            why = ('daily loss reserve' if day_pnl[day] <= -0.03 * S0 else 'entries per day' if day_entries[day] >= 7 else
                   'losses per day' if day_losses[day] >= 3 else 'equity buffer' if bal < 0.92 * S0 else
                   'total open risk' if tot_open + risk > 4.5 * b + 1e-9 else 'symbol open risk' if sym_open + risk > 3 * b + 1e-9 else None)
        else:
            floor = S0 if locked else peak - 0.06 * S0; room = bal - floor
            risk = min(sz['base'] / 100 * S0, 0.05 * room, (sz['cap'] or 99) / 100 * S0)
            why = ('floor buffer' if room < 0.0025 * S0 else 'daily loss stop' if day_pnl[day] <= -0.02 * S0 else
                   'daily profit cap' if day_pnl[day] >= 0.0075 * S0 else 'total open risk' if tot_open + risk > 0.02 * S0 + 1e-9 else
                   'symbol open risk' if sym_open + risk > 0.015 * S0 + 1e-9 else None)
        if why: blocked[why] += 1; continue
        open_[i] = risk; day_entries[day] += 1
    p = [x['pnl'] for x in taken]; gp, gl = sum(v for v in p if v > 0), -sum(v for v in p if v < 0)
    by = defaultdict(lambda: [0, 0.0])
    for x in taken: by[x['key']][0] += 1; by[x['key']][1] += x['pnl']
    return dict(ret=round((bal / S0 - 1) * 100, 2), net=round(bal - S0, 2), pf=round(gp / gl, 2) if gl else None,
                win=round(100 * sum(v > 0 for v in p) / len(p), 1) if p else None, trades=len(p), per_day=round(len(p) / WEEKDAYS, 2),
                closed_dd=round(dd, 2), blocked=dict(blocked), members={k: dict(trades=v[0], pnl=round(v[1], 2)) for k, v in sorted(by.items())})


res = {}
for slug, (label, members, sz, di) in PROFILES.items():
    res[slug] = dict(label=label, new=replay(members, sz, di, False), old=replay(members, sz, di, True) if di else None)

members = {p['key'] + ('' if p['tag'] in ('NEW',) else ' [' + p['tag'] + ']'): ledger(p['key'], p['tag'])[1] for p in PLAN}
SIZE = {'pct': lambda s: f"{s['pct']}% of balance", 'prop': lambda s: f"${s['budget']:.0f}/trade, guard",
        'trail': lambda s: f"{s['base']}%{' (≤0.3%)' if s['cap'] else ''}, trailing-floor guard"}
md = ['# October 2026: every portfolio profile with the new Nasdaq 5M, news EAs removed (generated by replay.py)', '',
      'Native MT5 Model 4 member runs, 2026-10-01 → 2026-11-01 (100% real ticks), each member at 1% on the exact installed EX5 and inputs '
      '(Current 14 + ORB wrappers; Full EA members from the canonical installer\'s own effective inputs), then R-replayed into each profile '
      'from a fresh $10,000. Method and guard limits: replay.py docstring. Trades per day over the 22 October weekdays. Trades per month = trades.', '',
      '| Profile | Sizing | Nasdaq 5M | Return | Net $ | PF | Win % | Trades (/day) | Closed DD | Entries blocked |', '|---|---|---|---:|---:|---:|---:|---:|---:|---|']
for slug, r in res.items():
    sz = PROFILES[slug][2]; di = PROFILES[slug][3]
    for tag, x in (('**new ATR6**', r['new']), ('old 0.60%', r['old'])):
        if x is None: continue
        nas = 'no Nasdaq 5M' if di is None else tag + (' DI OFF' if di == 'OFF' else '')
        bl = ', '.join(f'{k} {v}' for k, v in x['blocked'].items()) or ('–' if sz['kind'] != 'pct' else 'no guard')
        md.append(f"| {r['label']} | {SIZE[sz['kind']](sz)} | {nas} | {x['ret']:+.2f}% | {x['net']:+,.0f} | {x['pf']} | {x['win']} | {x['trades']} ({x['per_day']}) | {x['closed_dd']}% | {bl} |")
md += ['', '## Members, October standalone at 1% (native report)', '| Member | Return | PF | Trades | Win % | Equity DD |', '|---|---:|---:|---:|---:|---:|']
for k, m in members.items():
    md.append(f"| {k} | {m['return_pct']:+}% | {m['profit_factor']} | {m['trades']} | {m['win_rate_pct']} | {m['max_drawdown_pct']}% |")
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(profiles=res, members=members), indent=1, default=str), encoding='utf-8')
print('\n'.join(md))
