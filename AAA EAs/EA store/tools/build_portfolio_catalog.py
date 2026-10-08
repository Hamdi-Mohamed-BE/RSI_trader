"""Publish read-only portfolio definitions and labelled historical evidence. Never accesses MT5."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import calendar
import ast
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.catalog import PACKAGE_ROOT, get_website_catalog
from app.portfolio_analytics import performance, history_from_trades

OUT = ROOT / 'data' / 'portfolios.json'
FTMO = PACKAGE_ROOT / 'FTMO Thirteen EA Deployment 2026-09-27' / 'PACKAGE.json'
NEW = PACKAGE_ROOT / 'Current14 Plus ORB05 Portfolio 2026-10-08' / 'Package.json'
RESEARCH = PACKAGE_ROOT / 'FTMO ORB RR05 Portfolio Simulation 2026-10-08'
ORB = PACKAGE_ROOT / 'ORB and Range Breakout RR05 Comparison 2026-10-08'
LONG = PACKAGE_ROOT / 'Portfolio Long History 2026-10-08'
START, END = '2025-10-06', '2026-10-06'
SOURCES = {}
RISK_ROWS = {}
PERIODS = [('3m', '3 months', 3), ('6m', '6 months', 6), ('1y', '1 year', 12),
           ('3y', '3 years', 36), ('5y', '5 years', 60)]


def period_start(end, months):
    d = date.fromisoformat(end)
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    return date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1])).isoformat()




def period_histories(trades, coverage_start, end, label, basis, scope, missing=None):
    histories = []
    for period, title, months in PERIODS:
        requested = period_start(end, months)
        if requested < coverage_start and months > 12 and coverage_start == START:
            histories.append(dict(id=period, label=title+' · unavailable', available=False, coverage='unavailable',
                start=None, requested_start=requested, end_exclusive=end, stats={}, curve=[], months=[],
                rolling_sharpe=[], streaks={}, basis=basis, missing_members=missing or [],
                scope=f'No matching {title} history for these exact portfolio settings. Saved coverage: {coverage_start} → {end} (end exclusive). No shorter or different portfolio result is substituted.'))
            continue
        start = max(requested, coverage_start)
        h = history_from_trades(trades, start, end, period, title+' · '+label, basis, scope, missing)
        h['requested_start'] = requested
        if start != requested:
            h['coverage'] = 'partial'
            h['scope'] = f'Partial window: requested start {requested}; source begins {start}. Metrics cover only the shown available dates. '+h['scope']
        histories.append(h)
    return histories


def read(path):
    path = Path(path)
    SOURCES[str(path.relative_to(PACKAGE_ROOT)) if path.is_relative_to(PACKAGE_ROOT) else 'website/' + str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text(encoding='utf-8-sig'))


def atomic_json(path,value,compact=False):
    """Readers see a complete publication, never a half-written large JSON file."""
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as file:
        json.dump(value,file,indent=None if compact else 2,separators=(',',':') if compact else None,
                  ensure_ascii=False,allow_nan=False)
        file.write('\n')
        temporary=Path(file.name)
    temporary.replace(path)


def member(product, inputs=None, variant='Recommended normal preset', stats=None):
    inputs = inputs or {}
    rr = inputs.get('InpRewardRisk', inputs.get('RewardRisk'))
    if str(inputs.get('InpUseFixedTarget','true')).lower() == 'false':
        rr = None  # A retained unused RR parameter is not a live TP.
    return dict(slug=product.slug, label=product.label, symbol=product.canonical,
                timeframe=product.timeframe, strategy=product.strategy, variant=variant,
                target_rr=float(rr) if rr is not None else None, stats=stats,
                inputs=inputs, url='/eas/' + product.slug)


def rule(title, detail):
    return dict(title=title, detail=detail)


def normal_member(product):
    path = (product.dynamic_set_source if product.recommended_dynamic_mode else product.safe_set_source if product.recommended_safe_mode else product.set_source) or product.set_source
    path = Path(path)
    if not path.is_absolute():
        path = PACKAGE_ROOT / path
    SOURCES[str(path.relative_to(PACKAGE_ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = path.read_bytes()
    text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
    inputs = {}
    for line in text.splitlines():
        if '=' in line and not line.lstrip().startswith((';','#')):
            key,value = line.split('=',1)
            inputs[key.strip()] = value.split('||',1)[0].strip()
    mode = 'Dynamic' if product.recommended_dynamic_mode else 'Safe' if product.recommended_safe_mode else 'Standard'
    return member(product, inputs, mode + ' saved normal preset; BAT risk/adaptive overrides apply')




def native_rows(case, slug, symbol):
    contract = {'XAUUSD': 100.0, 'USTEC': 1.0, 'US100': 1.0, 'USDJPY': 100000.0}[symbol]
    rows = []
    for t in case['trades']:
        assert t['sl'] > 0 and t['volume'] > 0
        unit = abs(t['open_price'] - t['sl']) * contract / (t['sl'] if symbol == 'USDJPY' else 1.0)
        assert unit > 0
        rows.append(dict(key=slug, cl=t['close_epoch'], op=t['open_epoch'], position_id=t['position_id'],
                         unit_risk=unit, unit_gross=t['gross']/t['volume'],
                         unit_comm=(t['commission']+t.get('fee', 0))/t['volume'], unit_swap=t['swap']/t['volume']))
    return rows


def normalized_histories(rows, label, slug):
    # Fractional-lot reference ONLY. No fictional broker or shared account execution.
    start_ts = datetime.fromisoformat(START).replace(tzinfo=timezone.utc).timestamp()
    end_ts = datetime.fromisoformat(END).replace(tzinfo=timezone.utc).timestamp()
    trades = []
    RISK_ROWS[slug] = rows
    for r in rows:
        if not start_ts <= r['op'] < end_ts or not start_ts <= r['cl'] < end_ts:
            continue
        assert r['unit_risk'] > 0
        net = 50.0 / r['unit_risk'] * (r['unit_gross'] + r['unit_comm'] + r['unit_swap'])
        trades.append(dict(slug=r['key'], position_id=r.get('position_id', 0),
                           close_time=datetime.fromtimestamp(r['cl'], timezone.utc).isoformat(), net_profit=net))
    return period_histories(trades, START, END, label,
                basis='Unrestricted fractional-lot, fixed-$50 initial-stop risk reference on $10,000.',
                scope='Research overlay of separate native tests, not a native shared-margin or dynamic-equity run. '
                      'No daily guard, broker lot minimum/step, live retries or floating-equity path is reconstructed. '
                      'Partial exits are collapsed at the final position close. Recent windows are slices of the saved annual ledger, not independent re-runs. This is not a prediction of the BAT result.')


def extend_long_evidence(profiles):
    """Publish verified matching longer windows, never a different roster.

    Preserve existing annual references for the three selected portfolios; their
    risk scenarios keep the original annual signal ledger. New 3y/5y scenarios
    use the separately audited longer ledger. Full replaces its old archive with
    matching current members and discloses every untestable/missing member.
    """
    if not (LONG/'HISTORIES.json').is_file():return
    histories=read(LONG/'HISTORIES.json');audit=read(LONG/'AUDIT.json');rows=read(LONG/'RISK_ROWS.json')
    assert audit['production_files_unchanged'] and audit['selection_frozen'] and not audit['live_changes']
    assert not audit['native_simultaneous_portfolio']
    for profile in profiles:
        slug=profile['slug']
        if slug not in histories:continue
        evidence=audit['portfolios'][slug]
        tested={s['slug'] for s in evidence['sources']};missing={m['slug'] for m in evidence['missing']}
        assert tested|missing=={m['slug'] for m in profile['members']} and not tested&missing
        assert evidence['membership_fixed']
        if slug!='full-eas':assert not missing,'A selected portfolio still has incomplete component tests'
        original=RISK_ROWS[slug]
        RISK_ROWS[slug]=dict(annual=original,long=rows[slug],window_sources={
            period:('long' if slug=='full-eas' or period in ('3y','5y') else 'annual') for period,_,_ in PERIODS})
        updates={h['id']:h for h in histories[slug]}
        profile['history']=[updates[h['id']] if slug=='full-eas' or h['id'] in ('3y','5y') else h for h in profile['history']]
        profile['history_provenance']=dict(window=audit['window'],tested_members=len(tested),
            total_members=len(tested)+len(missing),missing=evidence['missing'],selection_frozen=True,
            source_history_quality=sorted(set(s['history_quality'] for s in evidence['sources'])))
        profile['caveats'].append('Longer windows hold today’s selection/settings fixed; they include selection/development history and are not untouched out-of-sample validation. Earlier missing real ticks may be simulated by MT5.')
        if slug=='full-eas':
            profile['description']='The current normal portfolio, including news and both no-stop hourly profiles. Matching historical component coverage is stated separately from the 37-EA membership.'
            profile['caveats']=[c for c in profile['caveats'] if not c.startswith('The archived combined results')]
            profile['caveats'].append('Matching current-basket replay is partial where historical inputs cannot be reproduced; missing members are not treated as zero-return systems. Not a native simultaneous 37-EA account backtest.')
            profile['caveats'].append('Sub-minute news outcomes on generated ticks can be misleading. These longer source tests have mixed/simulated tick coverage, not full real-tick execution validation.')


def main():
    catalog = {p.slug: p for p in get_website_catalog()}
    ftmo, new = read(FTMO), read(NEW)
    live = PACKAGE_ROOT/'_00 Live profiles'
    ftmo_live = read(live/'Packages/FTMO/PACKAGE.json') if (live/'Packages/FTMO/PACKAGE.json').is_file() else ftmo
    for name in ('Profiles.json','Packages/ORB-only/Package.json'):
        if (live/name).is_file():read(live/name)
    frozen = read(RESEARCH/'FROZEN_ROWS.json')
    RISK_ROWS['ftmo'] = frozen['baseline']
    research = read(RESEARCH/'Results.json')
    assert len(ftmo['entries']) == 14 and len(new['entries']) == 15 and len(catalog) == 37
    guard_rules = [
        rule('Risk selection / hard ceiling', 'Named launcher asks for fixed USD (default $50) or current-equity % (default 0.5%). All requested allocations remain capped at $50 planned initial-stop risk per trade on a $10,000 USD account. Lots round down; skip when minimum lot exceeds budget. The recorded reference remains fixed $50.'),
        rule('DI choices', 'Separate Nasdaq 5M and USDJPY DI ON/OFF prompts, default ON; USDJPY ADX ≥20 remains enabled. Changing DI does not inherit the recorded DI-ON performance.'),
        rule('Daily loss / reset', 'Saved guard: block new entries at a $300 daily equity loss from the Prague-midnight anchor. $500 daily loss and $9,000 equity latch a breach. This is an admission guard, NOT forced liquidation or a guaranteed maximum loss.'),
        rule('Portfolio exposure', '$225 aggregate initial-stop risk; $150 per symbol. Reserve 1.25× protected risk plus $5 per position and negative swap. Projected equity must stay at least $9,200 and within the $300 daily reserve.'),
        rule('Frequency and losses', 'At most 7 entries and 3 closed losing trades per Prague day; a 3-second shared entry reconciliation pause. Missing history, unprotected/unknown exposure or pending orders block admission.'),
        rule('Phase rules in the saved build', '$11,000 phase-1 / $10,500 phase-2 balance target after at least 4 trading days. New entries pause for review/new account; phase transitions are not automatic.'),
        rule('Margin and account', 'Projected margin at most 80% of protected equity and within free margin. Bound FTMO USD hedging account / server / symbol. News and no-stop hourly EAs excluded.'),
    ]
    baseline = next(x for x in research['historical'] if x['name']=='baseline')
    # Matching accepted-position log, not balance changes (which also contain entry fees).
    logged = read(PACKAGE_ROOT/'FTMO Three Portfolios Risk200 Daily400-450 2026-10-08/Results.json')
    accepted = next(x for x in logged['historical'] if x['profile']=='current14' and x['policy']=='original_50')
    for key in ('trades', 'pf', 'return_pct'):
        assert abs(accepted['portfolio'][key]-baseline['portfolio'][key]) < 1e-7
    ft_trades = [dict(slug=t['ea'], position_id=i, close_time=datetime.fromisoformat(t['close']).astimezone(timezone.utc).isoformat(),
                      net_profit=t['net_profit']) for i,t in enumerate(accepted['log'])]
    ft_history = period_histories(ft_trades, START, END, 'saved guarded $50 proxy',
        'Fixed $50 / $10,000; modelled FTMO admission rules.',
        'Slice of the saved annual accepted-position ledger, not a fresh guard replay for each window or a native simultaneous FTMO account. '
        'All position costs are attributed to final close; drawdown and Sharpe use closed-position cash, not entry-fee timing or floating equity. '
        'Guard retries, partial timing and broker execution are approximate.')
    assert abs(next(h for h in ft_history if h['id']=='1y')['stats']['return_pct']-baseline['portfolio']['return_pct']) < 1e-5
    assert {e['slug'] for e in ftmo_live['entries']}=={e['slug'] for e in ftmo['entries']}
    members_ft = [member(catalog[e['slug']], e['inputs'], 'Named FTMO default inputs; allocation capped at $50') for e in ftmo_live['entries']]
    members_new = [member(catalog[e['key']], e['inputs'], '0.5R ORB' if e['key'] in new['orb_keys'] else 'Current14 strategy inputs; no FTMO guard') for e in new['entries']]
    new_keys = {e['key'] for e in new['entries']}
    new_rows = [r for r in frozen['baseline'] if r['key'] in new_keys and r['key'] not in new['orb_keys']]
    for key in new['orb_keys']:
        c = read(ORB/'comparisons'/f'{key}.json')
        assert float(c['half']['inputs']['InpRewardRisk']) == .5
        new_rows += native_rows(c['half'], key, c['symbol'])
    assert {r['key'] for r in new_rows} == new_keys

    # Only actual opening-range systems, not every strategy in the range-breakout study.
    orb_keys = ['us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3',
                'orb-volume-profile','orb-volume-profile-volume-confirmed','xau-orb-new-york-m30',
                'xau-orb-london-ny-overlap-m30','asia-breakout']
    orb_members, orb_rows, screening = [], [], []
    for key in orb_keys:
        c = read(ORB/'comparisons'/f'{key}.json')
        qualified = [(name,c[name]) for name in ('half','current') if c[name]['metrics']['pf'] is not None
                     and math.isfinite(c[name]['metrics']['pf']) and c[name]['metrics']['pf'] >= 1.15
                     and c[name]['metrics']['win_rate'] >= 50]
        chosen = max(qualified, key=lambda item:item[1]['metrics']['win_rate']) if qualified else None
        screening.append(dict(slug=key, label=c['label'], selected=bool(chosen), variants=[
            dict(name=n, win_rate=c[n]['metrics']['win_rate'], profit_factor=c[n]['metrics']['pf'], trades=c[n]['metrics']['trades'],
                 selected=chosen is not None and chosen[0]==n) for n in ('half','current')]))
        if chosen:
            name,case = chosen
            inputs = case['inputs']; rr = inputs.get('InpRewardRisk')
            orb_members.append(member(catalog[key], inputs, f'{rr}R target · {name} comparison', case['metrics']))
            orb_rows += native_rows(case, key, c['symbol'])
    assert len(orb_members) == 5

    base = ROOT/'data/evidence-cache/v1/portfolio/standard'
    data = read(base/'5y.json'); archived = read(base/'5y.trades.json')
    s = data['stats']; archive_end = (date.fromisoformat(s['to'])+timedelta(days=1)).isoformat()
    coverage = {t.get('cache_slug') for t in archived}
    archive_trades = [dict(slug=t.get('cache_slug',''), position_id=i,
        close_time=datetime.fromisoformat(t['close_time']).astimezone(timezone.utc).isoformat(), net_profit=float(t['net_profit']))
        for i,t in enumerate(archived)]
    RISK_ROWS['full-eas'] = [dict(key=t['cache_slug'], symbol=t['symbol'],
        news=t['cache_slug'].startswith('news-') or t['cache_slug']=='gold-news-v9-direction',
        op=datetime.fromisoformat(t['open_time']).timestamp(), cl=datetime.fromisoformat(t['close_time']).timestamp(),
        unit_risk=float(t['estimated_risk_cash']), unit_gross=float(t.get('raw_gross_profit',t['gross_profit'])),
        unit_comm=float(t.get('raw_commission',t['commission'])), unit_swap=float(t.get('raw_swap',t['swap'])))
        for t in archived if t.get('estimated_risk_cash',0)>0]
    full_history = period_histories(archive_trades, s['from'], archive_end, 'archived adaptive overlay',
        'Archived adaptive cash-flow overlay; recorded cash sizes and adaptive scaling retained, rebased to $10,000 (not re-sized).',
        'Not a current 37-EA shared-account backtest. All periods are consistent close-time slices of the saved longest archived ledger, '
        'not fresh window-specific compounding runs. Hourly additions and revised news/filters/targets are not revalidated here. '
        'Source ends before the other portfolios; do not compare raw returns as equal-risk matched tests.',
        sorted(set(catalog)-coverage))

    profiles = [
        dict(slug='ftmo', name='FTMO guarded · Current 14', status='active', status_note='Existing guarded launcher available; not confirmation it is installed or passing.',
             description='Fourteen selected systems with the dedicated account-wide FTMO admission guard.',
             launcher='FTMO guarded - Current 14.bat', version='FTMO14-LIVE-PROMPTS-20261008', members=members_ft,
             risk_summary='Choose fixed USD or equity % · default $50 · hard $50 ceiling', rules=guard_rules, history=ft_history,
             caveats=['Named launcher adds allocation/DI choices to an isolated package; original FTMO guards remain. Custom choices are not a native validation.', 'Saved package rules are not a live statement of any firm’s current contract. Check the account agreement.', research['status']]),
        dict(slug='current14-orb05', name='Current 14 + ORB 0.5R', status='active', status_note='New compiled launcher available; not confirmation of live installation.',
             description='Fifteen unique systems: current 14 plus Gold New York ORB. Existing Gold overlap / US100 H1 ORBs are replaced, not duplicated.',
             launcher='Current 14 + ORB 0.5R.bat', version=new['version'], members=members_new,
             risk_summary='Choose fixed USD or dynamic equity % · default 0.5%',
             rules=[rule('Risk selection','Installer asks for fixed USD or dynamic % of current equity. Default 0.5% per trade; each 3-Way Gold module receives that risk. Not a portfolio-wide cap.'),
                    rule('Daily and overall drawdown','No shared daily stop, $400/$450 stop, total-loss limit, profit lock, FTMO phase target or fixed-$50 clamp. Individual protective stops and native exit logic remain.'),
                    rule('DI choices','Separate ON/OFF prompts for Nasdaq 5M and USDJPY (default ON). USDJPY ADX ≥20 stays enabled. DI OFF has not inherited DI-ON validation.'),
                    rule('Targets','Exactly three ORBs use 0.5R: US100 H1, Gold NY and Gold London–NY overlap. Trend retains 0.6R; Standard Squeeze uses Markov OFF. Selective V3 is not included.'),
                    rule('Account support','Supported MT5 demo/live hedging accounts; broker aliases mapped. Netting, MT4 and portable/tester/custom-config terminals are unsupported by this installer.'),
                    rule('Cash conversion and execution','Fixed USD on non-USD accounts requires fresh direct currency conversion; missing conversion skips entry. Fees, minimum lot/rounding, slippage and gaps can exceed the target. No news or hourly-timed EAs.')],
             history=normalized_histories(new_rows,'fixed-$50 reference, no shared guard','current14-orb05'),
             caveats=['Default dynamic-equity 0.5% performance has not been natively backtested as a combined account.', 'Previous guarded FTMO funding probabilities do not apply to this unrestricted package.']),
        dict(slug='orbs-only', name='ORB-only · 50%+ / PF 1.15+', status='disabled', status_note='Compiled named launcher available for review; composition remains disabled/research-only pending owner approval. Nothing has been installed.',
             description='All tested opening-range strategies meeting the requested annual net win-rate and finite profit-factor thresholds. Highest-win-rate qualifying version retained per EA.',
             launcher='ORB-only - 50pct+ PF1.15+.bat', version='ORB-ONLY-LIVE-PROMPTS-20261008', members=orb_members, screening=screening,
             risk_summary='Choose fixed USD or equity % · default 0.5% · research-only',
             rules=[rule('Admission screen','Annual native standalone win rate ≥50% and finite net PF ≥1.15. One qualifying version per EA; no duplicate strategies. Undefined PF is not treated as infinite.'),
                    rule('Targets are explicit','Three ORBs qualify at 0.5R; US100 New York qualifies only at its current target, and Selective V3 uses 2R. This five-EA profile is NOT an all-0.5R portfolio.'),
                    rule('Risk mode','Named launcher asks for fixed USD (default $50) or dynamic current-equity % (default 0.5%) per trade. Recorded history remains a fixed-$50 fractional-lot reference; custom calculator scenarios are offline approximations. No DI-enabled EA occurs in this selected roster, so no DI prompt is needed.'),
                    rule('Daily drawdown','No implemented portfolio-specific daily/total stop for this new five-EA selection. Older three/four-ORB FTMO and $200 / $400–450 simulations are different guarded profiles, not these results.')],
             selection_window=dict(start=START, end_exclusive=END),
             history=normalized_histories(orb_rows,'five screened ORBs, fixed-$50 reference','orbs-only'),
             caveats=['Selected on the same year shown: exploratory, not untouched out-of-sample validation.', 'Selective V3 has only five trades and Gold NY twelve; high win rate alone is not robust evidence.']),
        dict(slug='full-eas', name='Full EA portfolio · Recommended Adaptive', status='active', status_note='Existing normal launcher / 37-EA inventory; not proof every EA is attached or running.',
             description='The normal full portfolio, including news and the two no-stop hourly profiles. Archived evidence is kept separate from current membership.',
             launcher='Full EA portfolio - Recommended Adaptive.bat', version='NORMAL-37-LIVE-PROMPTS-20261008', members=[normal_member(p) for p in catalog.values()],
             risk_summary='Fixed USD or % · default non-news 0.25%; news separate 0.10%',
             rules=[rule('Standard risk','Named launcher asks for fixed USD (default $25) or current-equity % (default 0.25%) per non-news allocation. Nasdaq 5M uses 0.25× selected risk. XAU Weakness halves its idea budget per limit/stop order; each 3-Way Gold module receives the selected allocation. These are lower starting allocations, not optimized or guaranteed loss caps. Older normal BAT defaults remain 1%/0.75% news.'),
                    rule('Daily closed-loss stop','Non-news new entries stop after 5% account-wide daily CLOSED trading loss, reset at broker-server midnight. Not floating-equity liquidation; existing stops/positions are not changed.'),
                    rule('Drawdown / loss taper','Non-news entry risk ×0.50 at ≥4% closed-balance peak drawdown and ×0.25 at ≥7%. Per-EA consecutive loss taper ×0.50 at 3 losses and ×0.25 at 5; multipliers combine.'),
                    rule('News risk is separate','Four News Pulse assets plus Gold News V9 enabled. Named launcher asks separately, default 0.10% per order; two sides double one event’s exposure. Four simultaneous straddles plan 0.8% before V9, costs or gaps. News bypasses adaptive stops/tapers but its P/L affects non-news controls.'),
                    rule('DI choices','Separate ON/OFF choices for Nasdaq 5M and USDJPY London, both default ON. USDJPY ADX ≥20 stays enabled. Choice OFF has no inherited DI-ON validation.'),
                    rule('Hourly exception','US30 / US100 hourly EAs have NO stop-loss. Lots use a frozen historical maximum completed loss reference, not a future loss cap. Selected % applies; when not passed, hourly default 0.5% of balance. Fixed USD supported.'),
                    rule('Lot sizing and limits','Normal trades round up / minimum-lot override can exceed selected risk. Hourly sizing rounds down but minimum-lot fallback can exceed its historical budget. There is no guaranteed shared max loss or FTMO phase guard.')],
             history=full_history,
             caveats=['The archived combined results do not validate the current 37-EA composition, revised settings or hourly history-sizing.', 'News event settings and hourly selections are fitted to overlapping history; gaps and unbounded no-stop exposure matter.']),
    ]
    extend_long_evidence(profiles)
    for profile in profiles:
        keys=[m['slug'] for m in profile['members']]
        assert len(keys)==len(set(keys)) and set(keys)<=set(catalog)
    payload=dict(version='2026-10-08', launcher_directory=PACKAGE_ROOT.name+'/_00 Live profiles', status_meaning='Active means a configured launcher is available, not observed live installation. Disabled means research-only / not approved for live use, even when a compiled launcher is provided for review.',
                 metrics_note='Portfolio PF, win rate and streaks use net closed cash in chronological exit order; DD is closed-balance peak-to-trough. Daily closed DD uses each UTC day’s intraday closed-cash peak. Floating-equity DD is unavailable without intraday equity history; no proxy is presented as measured equity. Sharpe uses daily closed returns × sqrt(365), including no-trade days; payoff = average win / absolute average loss.',
                 period_options=[dict(value=p,label=l) for p,l,_ in PERIODS],
                 period_note='Calendar-month windows end at each portfolio’s latest saved coverage date, not necessarily today. The selected period changes metrics, curves and streaks; it never changes the selected EAs or risk rules.',
                 portfolios=profiles, source_hashes=SOURCES)
    # The longer-window ledger is ready before any new available history points to it.
    ledger_path=OUT.parent/'portfolio-risk-ledgers.json'
    atomic_json(ledger_path,RISK_ROWS,compact=True)
    payload['risk_ledger_sha256']=hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    atomic_json(OUT,payload)
    publish_guard_engine()
    print(json.dumps(dict(profiles={p['slug']:len(p['members']) for p in profiles}, output=str(OUT), no_mt5_access=True)))


def publish_guard_engine():
    """Bundle reviewed pure offline replay functions so web hosts need no research folders."""
    base=PACKAGE_ROOT/'FTMO Combination Study 2026-09-19'
    study=PACKAGE_ROOT/'FTMO Fourteen EA Study 2026-09-27/study.py'
    source=(base/'simulate.py').read_text(encoding='utf-8-sig')
    fn=next(n for n in ast.parse(study.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='engine')
    replacements=ast.literal_eval(next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='replacements' for t in n.targets)))
    for old,new in replacements.items():
        assert source.count(old)==1
        source=source.replace(old,new)
    changes={
        "if any(p['key']==key for p in active.values()):":"if any(p.get('lane',p['key'])==r.get('lane',key) for p in active.values()):",
        "lot=rounded(RISK/r['unit_risk'])":"budget=min(50.0,risk_value if risk_mode=='fixed' else bal*risk_value/100.0)*r.get('risk_weight',1.)\n                lot=rounded(budget/r['unit_risk'])",
        'assert risk<=RISK+1e-7':'assert risk<=budget+1e-7',
        'env=risk*(1.25 if stress else 1.)':'env=risk*(1.25*(1.25 if stress else 1.))+5.',
        "p=dict(lot=lot,risk=risk,margin=marg,env=env,key=key,group=":"p=dict(lot=lot,risk=risk,margin=marg,env=env,key=key,lane=r.get('lane',key),group=",
        "r=rows[i];key=r['key'];g,c,s,x=r['_costs'];sym=r['symbol']":"r=rows[i];key=r['key'];g,c,s,x=r['_costs'];sym=r['symbol']\n            if not r.get('order_compatible',True):counts['unsupported_pending_order']+=1;continue",
        'events.sort()':'events.sort(key=lambda e:(e[0],-1 if e[1]==2 else e[1],e[2]))',
        'detail=False):':"detail=False,risk_mode='fixed',risk_value=50.,daily_mode='off',daily_value=0.):",
        'today_count=0;max_daily_entries=0;':'custom_day_stopped=False;today_count=0;max_daily_entries=0;',
        "if t<ready:return 'phase_wait'":"if custom_day_stopped:return 'custom_closed_daily_stop'\n        if t<ready:return 'phase_wait'",
        'if kind==-1:anchor=bal;today_count=today_losses=0':'if kind==-1:anchor=bal;today_count=today_losses=0;custom_day_stopped=False',
        'eq=bal-envelope();peak=':"custom_limit=daily_value if daily_mode=='fixed' else anchor*daily_value/100.0\n        if daily_mode!='off' and anchor-bal>=custom_limit:custom_day_stopped=True\n        eq=bal-envelope();peak=",
    }
    for old,new in changes.items():
        assert old in source,old
        source=source.replace(old,new)
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('business','margin','replay')]
    cost=next(n for n in ast.parse((base/'prepare.py').read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name=='costs')
    cost.name='base_costs'
    header='''"""Generated from the saved pure offline guard replay; no trading imports. Rebuild via build_portfolio_catalog.py."""
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
PRAGUE=ZoneInfo('Europe/Prague')
CAPITAL=10000.0
DAY=86400
SPECS={'XAUUSD':(100,15),'XAGUSD':(5000,15),'USTEC':(1,15),'USDJPY':(100000,30),'EURUSD':(100000,30),'BTCUSD':(1,1),'ETHUSD':(10,1)}
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat() if t is not None else None
def rounded(v):return max(0.,math.floor(v/.01+1e-10)*.01)
def costs(row,stress=False):
    g,comm,swap,extra=base_costs(row,stress)
    if row['symbol']=='XAUUSD':comm=min(comm,-.000014*100*(row['open_price']+row['close_price']))
    elif row['symbol']=='USDJPY':comm=min(comm,-10.)
    return g,comm,swap,extra
def entry_charge(row,commission,extra):
    if row['symbol']=='XAUUSD':return -max(3.5,-row['unit_comm']/2,.000014*100*row['open_price'])-extra/2
    if row['symbol']=='USDJPY':return -max(5.,-row['unit_comm']/2)-extra/2
    return (commission-extra)/2
'''
    code=header+'\n'+ast.unparse(ast.Module(body=[cost]+nodes,type_ignores=[]))+'\n'
    (ROOT/'app/portfolio_guard_replay.py').write_text(code,encoding='utf-8')


if __name__ == '__main__':
    main()
