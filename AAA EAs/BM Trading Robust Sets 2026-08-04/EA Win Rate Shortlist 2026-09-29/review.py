"""Read-only catalogue/evidence inventory. Does not connect to MT5 or alter EAs."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

BASE = Path(r'C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04')
CACHE = BASE.parent / 'EA store/data/evidence-cache/v1'
OUT = Path(__file__).resolve().parent
AUDIT = BASE / 'FTMO Fourteen EA Study 2026-09-27'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None

def metrics(trades):
    ordered = sorted(trades, key=lambda t: (t['close_time'], t.get('number', 0)))
    values = [float(t['net_profit']) for t in ordered]
    wins = sum(x > 0 for x in values)
    losses = sum(x < 0 for x in values)
    gp, gl = sum(x for x in values if x > 0), -sum(x for x in values if x < 0)
    ws = ls = mw = ml = 0
    for x in values:
        ws = ws + 1 if x > 0 else 0
        ls = ls + 1 if x < 0 else 0
        mw, ml = max(mw, ws), max(ml, ls)
    return dict(trades=len(values), wins=wins, losses=losses, breakeven=len(values)-wins-losses,
                win_rate_pct=100*wins/len(values) if values else None,
                profit_factor=gp/gl if gl else None, net_profit=sum(values),
                max_win_streak=mw, max_loss_streak=ml,
                first=ordered[0]['open_time'] if ordered else None,
                last=ordered[-1]['close_time'] if ordered else None)

catalog = json.loads(urlopen('http://127.0.0.1:8080/api/eas', timeout=20).read())
assert len({x['slug'] for x in catalog}) == len(catalog)
records, checks = [], []
for product in catalog:
    slug = product['slug']
    variants = []
    for mode in ('standard', 'safe', 'dynamic'):
        path = CACHE / 'products' / slug / mode / '1y.json'
        if not path.exists():
            continue
        item = dict(mode=mode, source=str(path), periods={})
        expert = product.get('dynamic_expert_source') if mode == 'dynamic' else product.get('expert_source')
        expert = expert or product.get('expert_source')
        settings = product.get({'standard': 'set_source', 'safe': 'safe_set_source', 'dynamic': 'dynamic_set_source'}[mode])
        item['current_expert'] = str((BASE / expert).resolve()) if expert else None
        item['current_settings'] = str((BASE / settings).resolve()) if settings else None
        for period in ('1y', '3y'):
            p = path.with_name(period + '.json')
            if not p.exists():
                continue
            data = read(p)
            tp = p.with_name(period + '.trades.json')
            ledger = metrics(read(tp)) if tp.exists() else None
            meta = CACHE / 'source-runs' / slug / mode / (period + '.meta.json')
            source_meta = read(meta) if meta.exists() else {}
            fp = {}
            for typ, current, key in [('expert', item['current_expert'], 'expert_sha256'), ('settings', item['current_settings'], 'settings_sha256')]:
                now = sha(Path(current)) if current else None
                old = source_meta.get(key)
                fp[typ] = 'match' if now and old and now == old else ('different' if now and old else 'unknown')
            row = dict(period=data.get('period'), stats=data['stats'], ledger=ledger,
                       source=str(p), trades_source=str(tp), fingerprint=fp,
                       source_meta=source_meta, history_quality=data.get('history_quality') or data['stats'].get('history_quality'),
                       notice=data.get('notice'))
            item['periods'][period] = row
            if ledger:
                checks.append(dict(slug=slug, mode=mode, period=period,
                    count_ok=ledger['trades'] == data['stats']['trades'],
                    cash_difference=round(ledger['net_profit']-data['stats']['net_profit'], 4),
                    pf_difference=round(ledger['profit_factor']-data['stats']['profit_factor'], 5) if ledger['profit_factor'] is not None else None,
                    wr_difference=round(ledger['win_rate_pct']-data['stats']['win_rate_pct'], 4),
                    streak_equal=(ledger['max_win_streak']==data['stats'].get('max_win_streak') and ledger['max_loss_streak']==data['stats'].get('max_loss_streak'))))
        m = item['periods']['1y']
        # Use the stricter of native/displayed PF and all-cost ledger PF.
        item['pf_gate'] = min(m['stats']['profit_factor'], m['ledger']['profit_factor']) if m['ledger'] and m['ledger']['profit_factor'] is not None else m['stats']['profit_factor']
        variants.append(item)
    eligible = [v for v in variants if v['pf_gate'] >= 1.2]
    def rank(v):
        m = v['periods']['1y']['ledger'] or v['periods']['1y']['stats']
        return (m['win_rate_pct'], -m.get('max_loss_streak', 999), v['pf_gate'], m['trades'])
    best = max(eligible or variants, key=rank) if variants else None
    records.append(dict(slug=slug, label=product['label'], symbol=product['canonical'],
        variants=variants, selected_mode=best['mode'] if best else None,
        selection_passes=bool(eligible), default_mode='dynamic' if product.get('recommended_dynamic_mode') else 'safe' if product.get('recommended_safe_mode') else 'standard',
        risk_note=product.get('risk_note'), limitations=product.get('limitations'), newest_audit=None))

by_slug = {r['slug']: r for r in records}
for a in read(AUDIT / 'DATA_AUDIT.json')['eas']:
    if a['ea'] not in by_slug:
        continue
    p = AUDIT / 'native' / a['ea']
    run = read(p / 'run.json')
    ledger = metrics(read(p / 'trades.json'))
    assert ledger['trades'] == a['native_metrics']['trades']
    assert abs(ledger['net_profit'] - a['native_metrics']['net_profit']) < 0.02
    by_slug[a['ea']]['newest_audit'] = dict(stats=a['native_metrics'], ledger=ledger,
        from_date=run['from_date'], to_date=run['to_date'], source=str(p / 'run.json'),
        trade_source=str(p / 'trades.json'), inputs=run['inputs'], flags=a['flags'],
        expert_sha=run.get('expert_sha'), note='Dated audit inputs; not assumed identical to every cached mode or current preset.')

archived = []
for slug in ('orb-volume-profile-high-win-0-75r', 'xau-squeeze-momentum-high-win-0-75r', 'engineered-liquidity-xau', 'xag-session-vwap-snapback'):
    for mode in ('standard', 'safe'):
        periods = {}
        for period in ('1y', '3y'):
            p = CACHE / 'products' / slug / mode / (period + '.json')
            if p.exists():
                d = read(p)
                tp = p.with_name(period + '.trades.json')
                periods[period] = dict(stats=d['stats'], ledger=metrics(read(tp)) if tp.exists() else None, source=str(p))
        if periods:
            archived.append(dict(slug=slug, mode=mode, periods=periods, status='Not in current 34-product catalogue; retained research/cache only.'))

orb_path = BASE / 'US100 H1 ORB ADX RR1 Research 2026-09-23/NATIVE_RESULTS.json'
orb = read(orb_path)
research = [dict(name=name, stats=orb[name], source=str(orb_path), status='Retrospective same-year search; not out-of-sample or promoted.') for name in ('H1-RR1-adx25', 'H1-RR1-adx20')]

result = dict(date='2026-09-29', scope='34 current catalogue EAs; available Standard/Safe/Dynamic caches, 14 newer native audits, and explicitly identified related research. Not an exhaustive search of abandoned projects or proof that all catalogue EAs are running live.',
    method='Existing results only. Highest net win rate among 1y modes with both reported and net-ledger PF >= 1.20; ties prefer shorter losing streak, then PF. 3y is context, not an independent holdout. No optimization, new backtest, or deployment.',
    records=records, archived=archived, related_research=research, checks=checks)
(OUT / 'INVENTORY.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
assert all(c['count_ok'] and abs(c['cash_difference']) < 0.02 for c in checks), 'Cached ledger count/cash mismatch; investigate before reporting.'
print(json.dumps(dict(catalogue_count=len(records), modes=sum(len(r['variants']) for r in records), checked_ledgers=len(checks),
    nonmatching_streaks=[c for c in checks if not c['streak_equal']],
    larger_metric_differences=[c for c in checks if abs(c['wr_difference'])>.011 or (c['pf_difference'] is not None and abs(c['pf_difference'])>.04)]), indent=2))
for r in records:
    if not r['selected_mode']:
        print(r['label'], 'NO EVIDENCE')
        continue
    b = next(v for v in r['variants'] if v['mode']==r['selected_mode'])
    y, t = b['periods']['1y'], b['periods'].get('3y')
    m = y['ledger'] or y['stats']
    print(f"{r['label']} | {b['mode']} | {m['win_rate_pct']:.2f} | {y['stats']['profit_factor']:.2f}/{m['profit_factor']:.2f} | {m['trades']} | {m['max_win_streak']}/{m['max_loss_streak']} | {y['fingerprint']} | 3yPF {t['stats']['profit_factor'] if t else None}")
print('NEWER AUDIT (net ledger):')
for r in records:
    a = r['newest_audit']
    if a:
        m = a['ledger']
        print(f"{r['label']} | {m['win_rate_pct']:.2f} | {a['stats']['profit_factor']:.2f}/{m['profit_factor']:.2f} | {m['trades']} | {m['max_win_streak']}/{m['max_loss_streak']}")

# Build a user-facing inventory without silently overwriting weaker recent evidence
# with a favourable old result. All modes and original numbers remain in INVENTORY.
def display_row(label, version, stats, ledger, source, status, note='', longterm=None):
    m = ledger or stats
    pf = min(stats['profit_factor'], m['profit_factor']) if m['profit_factor'] is not None else stats['profit_factor']
    return dict(label=label, version=version, win_rate=m['win_rate_pct'], pf=pf,
        trades=m['trades'], wins=m['max_win_streak'], losses=m['max_loss_streak'],
        drawdown=stats.get('max_drawdown_pct'), source=source, status=status, note=note,
        passes=pf >= 1.2, longterm=longterm)

rows=[]
for r in records:
    if r['selected_mode'] is None:
        rows.append(dict(label=r['label'], version='Unranked', status='No comparable evidence', note='No 1y trade ledger in catalogue evidence.', source=None))
        continue
    b=next(v for v in r['variants'] if v['mode']==r['selected_mode'])
    y=b['periods']['1y']
    t=b['periods'].get('3y')
    if r['newest_audit'] and b['mode']=='standard':
        a=r['newest_audit']
        row=display_row(r['label'], 'Audited inputs, Sep 27', a['stats'], a['ledger'], a['source'], 'N', 'Newer native study; standalone 1% nominal sizing, not the daily-governed FTMO portfolio.')
    else:
        row=display_row(r['label'], b['mode'].title(), y['stats'], y['ledger'], y['source'], 'S',
            'Saved historical mode; current-code reproduction required.' if y['fingerprint']!={'expert':'match','settings':'match'} else 'Current catalogue expert and preset match the evidence fingerprints.',
            dict(stats=t['stats'], ledger=t['ledger']) if t else None)
        if y['fingerprint']=={'expert':'match','settings':'match'}:
            row['status']='M'
    if r['slug']=='gold-overnight-value-area':
        row['note']='High win rate but raw 3y PF 1.15 and 5y PF 1.04. Latest native audit has invalid-stop/market-closed messages. Not a robust FTMO selection.'
    if r['slug']=='ema3':
        row['note']='Old Safe mode: no distinct current Safe SET exposed by catalogue. Newer default audit: 65.12% / PF 1.73 / 43 trades / W7-L3; does not revalidate this Safe mode.'
    if r['slug']=='xau-squeeze-momentum-standard':
        row['note']='Only 14 yearly trades. Newer Standard audit: 38.89% / PF 1.27 / 18 trades / W4-L6; Safe mode not freshly retested.'
    if r['slug']=='us100-selective-orb-v3':
        row['note']='80% is only four wins from five trades. Not enough evidence to nominate as best.'
    if r['slug']=='nasdaq-5m-candle-momentum':
        row['version']='DI + wide stop + ATR6 trail'
        row['note']='Fingerprint-matched current research deployment; explicitly not pipeline-approved. 9-win/6-loss streaks are past observations only.'
    if r['slug']=='sell-nasdaq-15min':
        row['note']='Safe wins tie-break for shorter loss streak: 4 vs Dynamic 6. Dynamic has same 46.15% win rate, PF 1.44, W4/L6, DD7.81%.'
    if r['slug'].startswith('news-pulse-'):
        row['note']='Experimental news execution; exceptional tester PF is not live-fill evidence. Keep outside preferred shortlist pending execution validation.'
    if r['slug']=='xau-rsi-vwap':
        row['note']='Newer PF 1.18 is borderline below 1.20; old cache PF1.38 is not a substitute for this result.'
    if r['slug']=='dmc-fresh-reaction-us100':
        row['note']='Newer PF 1.08 fails. Old 66.67% / PF1.88 / 12 trades should not be presented as current proof.'
    rows.append(row)

# These research variants are explicitly separated from active deployment.
arch=next(a for a in archived if a['slug']=='orb-volume-profile-high-win-0-75r')
y,t=arch['periods']['1y'],arch['periods']['3y']
orb_high=display_row('ORB Volume Profile', 'Retained 0.75R high-win', y['stats'], y['ledger'], y['source'], 'R',
    'Not in current catalogue. 3y: 70.18%, reported PF1.48, 171 trades, W11/L3. Old binary requires revalidation.', t)
orb_trades=read(orb_path.parent / 'native/trades.json')
research_rows=[orb_high]
for name in ('H1-RR1-adx25','H1-RR1-adx20'):
    trades=[dict(close_time=t['exit'], open_time=t['entry'], net_profit=t['net'], number=i) for i,t in enumerate(orb_trades[name])]
    led=metrics(trades)
    m=orb[name]
    assert led['trades']==m['trades'] and abs(led['net_profit']-m['net_profit'])<0.02
    research_rows.append(display_row('US100 H1 ORB 13UTC', name, m, led, str(orb_path), 'R',
        'Selected from 25 configurations on the same year; no untouched validation. ADX25 has slightly higher WR; ADX20 has 57 vs48 trades with similar PF.'))

slow_dir=BASE/'XAU Slow Trend Filter Review 2026-09-29'
slow=read(slow_dir/'SUMMARY.json')
sl=metrics(read(slow_dir/'native/adx20-di-rising-1y-m4/trades.json'))
research_rows.append(display_row('XAU Slow Trend', 'ADX20 + DI + rising ADX', slow['one_year_candidate'], sl, str(slow_dir/'SUMMARY.json'), 'R',
    '22.22% wins and 15 consecutive losses: poor match for requested style. Latest six months PF0.47 and negative return. Not approved.'))
for i,r in enumerate(rows):
    if r['label']=='XAU Slow Trend':
        base=slow['one_year_baseline']
        led=metrics(read(slow_dir/'native/baseline-1y-m4/trades.json'))
        rows[i]=display_row(r['label'], 'Latest baseline, Sep29', base, led, str(slow_dir/'SUMMARY.json'), 'N',
            'Fails PF gate. ADX research reaches 22.22% / PF1.31 but 15 losses in a row and a losing recent six months; unsuitable for high-win preference.')

def link(path,label='source'):
    return f'[{label}](<{Path(path).as_posix()}>)'

def table(items):
    lines=['| EA / version | Win rate, net | PF* | Trades | Max wins / losses | Evidence / comment |',
           '|---|---:|---:|---:|---:|---|']
    for r in items:
        if 'pf' not in r:
            lines.append(f"| {r['label']} | — | — | — | — | {r['note']} |")
            continue
        state='Pass' if r['passes'] else 'Below 1.20'
        lines.append(f"| {r['label']} — {r['version']} | {r['win_rate']:.2f}% | {r['pf']:.2f} | {r['trades']} | {r['wins']} / {r['losses']} | {r['status']}; {state}. {r['note']} {link(r['source'])} |")
    return '\n'.join(lines)

report='''# EA win-rate and profit-factor review

29 September 2026 — results only; no EA, SET, installation, website, MT5 session or trading account changed.

## Decision

For your preference, the **most interesting high-win research variants are ORB Volume Profile 0.75R and US100 H1 ORB 1R + ADX**. They need current-build / out-of-sample checks before promotion. **EMA3's newer audited default and Nasdaq Overnight are the more practical existing-version shortlist.** Gold Overnight wins more often but its longer record is weak. This is a research shortlist, not an instruction to trade or a forecast of streaks.

- ORB Volume Profile 0.75R: 70.59% wins, PF 1.63, 51 yearly trades, max 7 wins / 2 losses; three-year 70.18%, PF 1.48, 171 trades, max 11 / 3. Retained old version, not a current catalogue default.
- US100 H1 ORB 1R + ADX25: 68.75%, PF 2.03, 48 trades, max 5 / 3. ADX20: 68.42%, PF 2.03, 57 trades, max 5 / 3. The extra 0.33 percentage point is not meaningful evidence that ADX25 is better than ADX20; both were searched on the same year.
- EMA3: newer default audit 65.12%, PF 1.73, 43 trades, max 7 / 3. Old Safe mode is numerically better at 70.27%, PF 2.71, 37 trades, max 9 / 4, but has no freshly verified current Safe configuration.
- Nasdaq Overnight: newer audit 60.81%, PF 1.63, 74 trades, max 10 / 4.
- Gold Overnight raw: newer 73.50%, PF 1.52, 200 trades, max 11 / 3; raw three-year PF 1.15 and five-year PF 1.04 weaken the case for relying on it.

## What was compared

34 current catalogue EAs; 45 saved Standard/Safe/Dynamic variants; 90 one-/three-year ledgers, plus 14 newer native audit ledgers and named related research. Catalogue membership is not proof that every EA is currently running on an MT5 chart. This is **not** an exhaustive search of all abandoned research folders or a new optimization/backtest.

Use PF ≥ 1.20 as the screen. Among cached modes passing it, prefer highest **net** win rate; ties prefer shorter losing streak and then PF. Replace stale default-mode figures with newer dated native tests when available, even if worse. Different Safe/research modes remain distinct and are explicitly labelled. Three-year results include the latest year: not independent validation. Test end dates differ between late August and late September 2026.

Wins and streaks are recalculated from closed trades after recorded commission/swap. Zero-net trades reset both streaks and remain in the win-rate denominator. PF* is the lower of the reported PF and net-ledger PF, a conservative screen; this preserves the familiar tester figure while not concealing a cost-adjusted failure. Full original and recalculated values are retained in INVENTORY.json. Some reported MT5 win rates count trades that are not net winners after costs: e.g. latest USDJPY 49.63% becomes 43.70% net. None of these figures includes a newly imposed extra-slippage stress.

Streaks are **historical maxima**, not forecasts or guaranteed loss limits. Risk/lot rounding differs among standalone tests, usually nominal 1%; these are not the 0.5% FTMO daily-stop portfolio results, pass probabilities, or payout projections. “Safe” is a saved mode name, not a safety guarantee.

Evidence labels: **N** newer native audit inputs; **M** cached expert and SET exactly match current catalogue fingerprints; **S** older saved mode without current-build proof; **R** related unpromoted/retained research. A different hash means not byte-identical, not necessarily changed strategy logic. Most older cache binaries differ from the current files. Generic 98–100% history quality does not prove 100% historical real ticks; newer yearly audits report about 73% real ticks and generated fallback before January 2026.

## All 34 catalogue EAs

The named mode is a candidate to review, not an automatic deployment recommendation. Read the separate research alternatives below for ORB and Slow Trend.

'''+table(rows)+'''

## Related versions that directly address your preference

'''+table(research_rows)+'''

## Versions I would not elevate solely on their win rate

- US100 Selective ORB V3:80% is4 wins from only5 trades; its three-year record has only20 trades.
- XAU Squeeze Safe:64.29% andPF3.27 but only14 trades in a year /38 over three years. The latest Standard test is much weaker and does not validate Safe.
- XAU RSI VWAP: latestPF1.18 is close to your request but below the strict screen. No rounding up to a pass.
- DMC Fresh US100: latestPF1.08 fails despite the old cache showing1.88.
- All News Pulse: reportedPF11–14 is attractive on paper, but highly execution-sensitive. Keep separate until replay/live execution evidence supports it. GoldNewsV9 has no comparable retained1y ledger here.
- XAU Slow Trend: latest baseline loses; filtered versions are low-win and still fail the latest six months. Long losing streaks conflict with your requested style.
- LTA, BTC POC Fibonacci and XAU Regime Switch can clearPF1.2 while having low win rates and long losing streaks. They are not the best psychological fit for this request.

## Longer-record context for the selected saved modes

| EA | Saved mode | 3y net win rate | Reported PF | Trades | Max wins / losses |
|---|---|---:|---:|---:|---:|
'''
for r in records:
    if not r['selected_mode']:
        continue
    b=next(v for v in r['variants'] if v['mode']==r['selected_mode'])
    t=b['periods'].get('3y')
    if t:
        m=t['ledger'] or t['stats']
        report+=f"| {r['label']} | {b['mode']} | {m['win_rate_pct']:.2f}% | {t['stats']['profit_factor']:.2f} | {m['trades']} | {m['max_win_streak']} / {m['max_loss_streak']} |\n"
report+='''
## Checks and limits

All 90 cached ledgers matched their reported trade counts and cash totals within two cents; all saved maximum streaks matched. All 14 newer audit ledgers matched their native counts and cash. Win-rate differences after costs are documented, not ignored. Research ORB 1R ledger counts and cash were checked against its native summaries. Source paths, hashes, native flags and alternative modes are preserved in INVENTORY.json; source inputs are not altered.

Historical selection introduces hindsight and multiple-testing risk. Higher win rate can be purchased with smaller wins relative to losses; it is not automatically a better strategy. Combining several gold bots can create concentrated exposure. Further validation should compare the exact candidate builds on common dates, realistic costs, unseen/forward data and the actual FTMO portfolio rules before any live change.

General limitation: [CFTC trading-system advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/fraudadv_tradingsystem.html) explains why hypothetical system results may differ from actual trading. All numbers here are local historical evidence, not broker-certified live returns or guaranteed future outcomes.
'''
(OUT/'REPORT.md').write_text(report,encoding='utf-8')
(OUT/'SHORTLIST.json').write_text(json.dumps(dict(catalogue=rows,research=research_rows),indent=2),encoding='utf-8')
assert len(rows) == 34
assert all(Path(r['source']).is_file() for r in rows+research_rows if r['source'])
(OUT/'CHECKS.json').write_text(json.dumps(dict(catalogue_rows=len(rows), saved_modes=45, cached_ledgers_checked=len(checks),
    native_ledgers_checked=sum(r['newest_audit'] is not None for r in records),
    cash_and_count_checks_passed=True, all_cached_streaks_match=all(c['streak_equal'] for c in checks),
    displayed_sources_exist=True, notes='Historical win rates recalculated net of recorded costs; no live changes.'), indent=2), encoding='utf-8')
print('Report written:', OUT/'REPORT.md')
