"""Combine the 2-week standalone native runs (ledger overlay) and compare with the demo account's actual trades."""
import gzip, json, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEL = json.loads((ROOT / 'selection.json').read_text())
DEMO = Path(sys.argv[1]) if len(sys.argv) > 1 else None
START = datetime(2026, 9, 25, tzinfo=timezone.utc)
END = datetime(2026, 10, 10, tzinfo=timezone.utc)
DEP = 10000.0


def ts(v):
    v = str(v).replace('.', '-').replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(v[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(v)


def stats(trades):
    p = [t['net'] for t in trades]
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    bal, peak, dd = DEP, DEP, 0.0
    for t in sorted(trades, key=lambda t: t['close']):
        bal += t['net']; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
    return dict(n=len(p), net=round(sum(p), 2), ret=round(sum(p) / DEP * 100, 2), pf=round(gp / gl, 2) if gl else (None if not gp else 99.0),
                win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None, dd=round(dd, 2))


cases = {}
for r in SEL['rows']:
    run = ROOT / 'native' / f"nw-{r['symbol']}-{r['slug']}-2w"
    meta = json.loads((run / 'run.json').read_text()) if (run / 'run.json').exists() else None
    tr = json.loads(gzip.decompress((run / 'trades.json.gz').read_bytes())) if (run / 'trades.json.gz').exists() else None
    trades = [dict(close=ts(t['close_time']), net=float(t['net_profit']), slug=r['slug']) for t in (tr or [])]
    magic = next((r['inputs'][k] for k in ('InpMagic', 'InpMagicNumber', 'MagicNumber', 'Magic') if k in r['inputs']), None)
    cases[r['slug']] = dict(row=r, meta=meta, trades=trades, magic=int(magic) if magic and str(magic).lstrip('-').isdigit() else None)

# demo account actual trades in the same window, per magic
demo_by_magic = defaultdict(list)
if DEMO and DEMO.exists():
    deals = json.loads(DEMO.read_text(encoding='utf-8'))['result']
    pos = defaultdict(list)
    for d in deals:
        if d['type'] in (0, 1):
            pos[d['position_id']].append(d)
    for ds in pos.values():
        outs = [d for d in ds if d['entry'] in (1, 2, 3)]
        if not outs:
            continue
        close = datetime.fromtimestamp(max(d['time'] for d in outs), tz=timezone.utc)
        if not (START <= close < END):
            continue
        ins = [d for d in ds if d['entry'] == 0]
        magic = (ins[0] if ins else ds[0])['magic']
        demo_by_magic[magic].append(dict(close=close, net=sum(d['profit'] + d['commission'] + d['swap'] + d.get('fee', 0) for d in ds)))

print(f"Window {START:%Y-%m-%d} -> {END:%Y-%m-%d} (end exclusive); each EA standalone $10,000, 1% risk; news excluded.\n")
print(f"{'phase':7} {'EA':40} {'sim n':>5} {'sim $':>9} {'PF':>5} {'win%':>5} {'eqDD%':>6} | {'demo n':>6} {'demo $':>9} | audit")
rows = []
for slug, c in cases.items():
    s = stats(c['trades']); m = c['meta'] or {}
    eqdd = (m.get('metrics') or {}).get('relative_equity_dd_pct')
    demo = demo_by_magic.get(c['magic'], []) if 'reviewed' not in slug else []
    dn, dnet = len(demo), round(sum(t['net'] for t in demo), 2)
    ok = 'ok' if m.get('audited') else ('MISSING' if not m else 'FLAG')
    rows.append((c['row']['phase'], c['row']['label'], s, eqdd, dn, dnet, ok, slug))
for ph, label, s, eqdd, dn, dnet, ok, slug in sorted(rows, key=lambda x: ({'live': 0, 'paused': 1, 'review': 2}.get(x[0], 3), -x[2]['net'])):
    pf = '—' if s['pf'] is None else f"{s['pf']:.2f}"
    win = '—' if s['win'] is None else f"{s['win']:.0f}"
    dd = '—' if eqdd is None else f"{eqdd:.2f}"
    print(f"{ph:7} {label[:40]:40} {s['n']:5d} {s['net']:+9.2f} {pf:>5} {win:>5} {dd:>6} | {dn:6d} {dnet:+9.2f} | {ok}")


def portfolio(slugs, title):
    tr = [t for s in slugs for t in cases[s]['trades']]
    st = stats(tr)
    days = (END - START).days; weekdays = 10
    print(f"\n{title}: {len(slugs)} EAs | trades {st['n']} ({st['n'] / days * 30.44:.0f}/month, {st['n'] / weekdays:.1f}/weekday) | "
          f"net {st['net']:+.2f} ({st['ret']:+.2f}% of $10k) | PF {st['pf']} | win {st['win']}% | closed-balance DD {st['dd']}%")
    daily = defaultdict(float)
    for t in tr:
        daily[t['close'].date()] += t['net']
    print('   daily: ' + ', '.join(f"{d:%a %d}: {v:+.0f}" for d, v in sorted(daily.items())))
    return st


normal = [s for s in cases if 'reviewed' not in s]
reviewed = [s for s in cases if (cases[s]['row']['phase'] == 'live' and s != 'xau-trend-progression') or s == 'xau-trend-progression--reviewed']
portfolio(normal, 'ALL EAs (old full roster, normal Trend 0.6R)')
portfolio(reviewed, 'REVIEWED live profile (20 non-news of the 25; Trend 1.5R)')
dt = [t for v in demo_by_magic.values() for t in v]
ds = stats(dt)
print(f"\nDEMO ACCOUNT actual (all magics incl. news/manual): trades {ds['n']} | net {ds['net']:+.2f} | PF {ds['pf']} | win {ds['win']}%")
news = {861302: 'News Pulse XAG', 861303: 'News Pulse XAU', 861304: 'News Pulse EURUSD', 861305: 'News Pulse BTC', 90915001: 'Gold News V9'}
for mg, name in news.items():
    if mg in demo_by_magic:
        print(f"   demo {name}: n={len(demo_by_magic[mg])} net={sum(t['net'] for t in demo_by_magic[mg]):+.2f}")
known = {c['magic'] for c in cases.values()} | set(news)
other = {m: v for m, v in demo_by_magic.items() if m not in known}
for m, v in other.items():
    print(f"   demo other magic {m}: n={len(v)} net={sum(t['net'] for t in v):+.2f}")
