"""Independent portfolio catalogue. Membership never changes the individual EA catalogue."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from functools import lru_cache

from .catalog import PACKAGE_ROOT, STORE_ROOT, get_website_catalog
from .risk_visuals import sharpe_sparkline_svg, streak_bars_svg
from .portfolio_analytics import allocation_replay, history_from_trades
from .portfolio_guard_replay import replay as guarded_replay

SNAPSHOT = STORE_ROOT / 'data' / 'portfolios.json'
RISK_LEDGER = STORE_ROOT / 'data' / 'portfolio-risk-ledgers.json'
STATUSES = {'all': 'All portfolios', 'active': 'Active', 'disabled': 'Disabled / research'}
PERIODS = {'3m': '3 months', '6m': '6 months', '1y': '1 year', '3y': '3 years', '5y': '5 years'}
MANIFESTS = ('FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json',
             'Current14 Plus ORB05 Portfolio 2026-10-08/Package.json',
             '_00 Live profiles/Profiles.json', '_00 Live profiles/Packages/FTMO/PACKAGE.json',
             '_00 Live profiles/Packages/ORB-only/Package.json')


def _chart(history):
    points = history.get('curve', [])
    if len(points) < 2:
        return None
    times = [datetime.fromisoformat(p['time']).timestamp() for p in points]
    values = [float(p['balance']) for p in points]
    lo, hi = min(values), max(values)
    span = hi - lo or 1
    time_span = times[-1] - times[0] or 1
    path = ' '.join(('M' if i == 0 else 'L') + f'{30+(t-times[0])/time_span*940:.2f},{265-(v-lo)/span*230:.2f}'
                    for i,(t,v) in enumerate(zip(times,values)))
    return dict(path=path, low=lo, high=hi, first=points[0]['time'][:10], last=points[-1]['time'][:10])


def _decorate_history(h):
    h['chart'] = _chart(h)
    h['sharpe_svg'] = sharpe_sparkline_svg(h.get('rolling_sharpe', []))
    h['streak_svg'] = streak_bars_svg(h.get('streaks', {}))
    h['latest_rolling_sharpe'] = next((point['sharpe'] for point in reversed(h.get('rolling_sharpe', []))
                                     if point.get('sharpe') is not None), None)
    return h


@lru_cache(maxsize=4)
def _load(mtime_ns, manifest_stamp):
    data = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    profiles = data['portfolios']
    inventory = {p.slug for p in get_website_catalog()}
    ids = [p['slug'] for p in profiles]
    if len(ids) != len(set(ids)) or set(ids) != {'ftmo','current14-orb05','orbs-only','full-eas'}:
        raise ValueError('Invalid portfolio publication')
    warnings = []
    # Portable publication works without the large research folders on the web host.
    # Locally available manifests are checked so a changed launcher cannot silently reuse its old publication.
    for name in MANIFESTS:
        path = PACKAGE_ROOT / name
        expected = data['source_hashes'].get(name.replace('/', '\\'), data['source_hashes'].get(name))
        if expected and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            warnings.append('A launcher manifest changed after this publication. Rebuild the portfolio snapshot before treating membership/settings as current.')
    for p in profiles:
        members = [m['slug'] for m in p['members']]
        if p['status'] not in ('active','disabled') or len(members) != len(set(members)) or not set(members) <= inventory:
            raise ValueError('Portfolio membership is invalid')
        p['ea_count'] = len(members)
        p['status_label'] = STATUSES[p['status']]
        p['url'] = '/portfolios/' + p['slug']
        p['summary'] = next((h for h in p['history'] if h['id'].startswith('1y')), p['history'][0])
        p['risk_defaults'] = dict(percent=.25 if p['slug']=='full-eas' else .5,
                                 fixed=25 if p['slug']=='full-eas' else 50, news_percent=.10)
        for h in p['history']:
            _decorate_history(h)
    return dict(data, warnings=warnings, counts={key:sum(p['status']==key for p in profiles) for key in ('active','disabled')})


def portfolio_catalog():
    stamp=tuple((name,(PACKAGE_ROOT/name).stat().st_mtime_ns if (PACKAGE_ROOT/name).exists() else None) for name in MANIFESTS)
    return _load(SNAPSHOT.stat().st_mtime_ns,stamp)


def portfolio_by_slug(slug):
    return next((p for p in portfolio_catalog()['portfolios'] if p['slug'] == slug), None)


def portfolio_history(profile, period='1y'):
    # Keep previously shared annual deep links valid, without substituting evidence.
    period = {'1y-reference':'1y', '1y-guard-proxy':'1y'}.get(period, period)
    return next((h for h in profile['history'] if h['id'] == period), None)


@lru_cache(maxsize=4)
def _risk_rows(stamp,expected_sha256=None):
    content=RISK_LEDGER.read_bytes()
    if expected_sha256 and hashlib.sha256(content).hexdigest()!=expected_sha256:
        raise ValueError('Portfolio evidence is being updated. Refresh and retry; no mixed-version risk result is shown.')
    return json.loads(content.decode('utf-8'))


def portfolio_scenario(profile, period='1y', risk_mode='recorded', risk_value=50., initial_balance=10000.,
                       news_risk_percent=.10, daily_limit_mode='off', daily_limit_value=0.):
    if risk_mode not in ('recorded','fixed','percent') or daily_limit_mode not in ('off','fixed','percent'):
        raise ValueError('Unknown sizing/limit mode.')
    for value in (risk_value,initial_balance,news_risk_percent,daily_limit_value):
        if not math.isfinite(value):raise ValueError('Enter finite numeric values.')
    if not 0<risk_value<=100000 or (risk_mode=='percent' and risk_value>10):
        raise ValueError('Risk must be positive; percentage at most 10%, fixed USD at most $100,000.')
    if not 100<=initial_balance<=10000000 or not 0<news_risk_percent<=10:
        raise ValueError('Balance must be $100–$10,000,000 and news risk greater than 0 and at most 10%.')
    if daily_limit_mode!='off' and (daily_limit_value<=0 or daily_limit_value>100000 or
                                   (daily_limit_mode=='percent' and daily_limit_value>100)):
        raise ValueError('Daily loss limit must be positive (percentage at most 100%).')
    if risk_mode=='recorded':
        if daily_limit_mode!='off':raise ValueError('Select fixed USD or dynamic % to calculate a custom daily-loss limit.')
        return portfolio_history(profile,period)
    if profile['slug']=='ftmo' and initial_balance!=10000:
        raise ValueError('Saved FTMO guard is specifically for $10,000; do not scale its fixed account thresholds to another balance.')
    return _scenario(SNAPSHOT.stat().st_mtime_ns,RISK_LEDGER.stat().st_mtime_ns,profile['slug'],period,
                     risk_mode,risk_value,initial_balance,news_risk_percent,daily_limit_mode,daily_limit_value)


@lru_cache(maxsize=128)
def _scenario(snapshot_stamp,ledger_stamp,slug,period,mode,value,initial,news,daily_mode,daily_value):
    catalog=portfolio_catalog()
    profile=next(p for p in catalog['portfolios'] if p['slug']==slug)
    original=portfolio_history(profile,period)
    if original is None or not original['available']:return original
    rows=_risk_rows(ledger_stamp,catalog.get('risk_ledger_sha256'))[slug]
    if isinstance(rows,dict):
        # Annual references and longer matched tests intentionally keep their
        # own ledgers; never replay a 5y scenario against the annual-only source.
        rows=rows[rows['window_sources'][period]]
    start,end=original['start'],original['end_exclusive']
    info={}
    scope='Entry-time sizing replay. Dynamic % uses simulated CLOSED BALANCE as an equity proxy; no intratrade floating-equity data is available. '
    if slug=='ftmo':
        begin=datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp()
        finish=datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()
        accepted=guarded_replay([dict(r) for r in rows if begin<=r['op']<r['cl']<finish],[],begin,finish,
            challenge=False,detail=True,risk_mode=mode,risk_value=value,daily_mode=daily_mode,daily_value=daily_value)
        trades=[dict(slug=t['ea'],position_id=i,close_time=datetime.fromisoformat(t['close']).astimezone(timezone.utc).isoformat(),
                     net_profit=t['net_profit']) for i,t in enumerate(accepted['log'])]
        info=dict(skips=accepted['counts'],guard_proxy_breach=accepted['breach'],
                  max_daily_stop_reserve_loss_cash=accepted['worst_daily_usd'],
                  unclosed_positions=accepted['open_positions'],last_admitted_entry=max((t['open'] for t in accepted['log']),default=None))
        scope+='Existing FTMO admission guards re-run from a fresh $10,000 window: $50 per-trade ceiling, rounding down to 0.01, $225/$150 exposures, $300 daily reserve and $9,200 buffer. Stop-reserve equity is a PROXY, not measured floating drawdown. '
        scope+='One continuous account, not rolling challenges or restart-after-failure simulations; challenge phase targets are not simulated. '
        if accepted['counts'].get('total_loss_buffer_rejected'):
            scope+='The unchanged $9,200 buffer blocked '+str(accepted['counts']['total_loss_buffer_rejected'])+' later entries; last admitted entry '+str(info['last_admitted_entry'])+'. Shorter windows start fresh and can have very different results. '
    else:
        trades,info=allocation_replay(rows,start,end,mode,value,initial,adaptive=slug=='full-eas',news_percent=news,
                                     daily_mode=daily_mode,daily_value=daily_value)
        scope+='Fractional lots; broker lot minimum/step, shared margin, execution feedback, spread changes and intra-position partial timing are not reconstructed. '
        if slug=='full-eas':
            if original.get('evidence_kind')=='matched-five-year-native-signal-ledger-offline-portfolio-replay':
                scope+='Matching tested current members only; filled initial stops define R except no-stop hourly EAs, which retain the frozen historical-loss reference. Missing members are not given zero P/L. Approximate adaptive entry tapers/UTC daily closed-loss controls applied; Nasdaq risk ×0.25, news separate and bypassing adaptive tapers. NOT a native simultaneous 37-EA account backtest. '
                scope+='XAU Weakness keeps half the selected idea budget per filled limit/stop order. '
            else:scope+='Archived covered EAs only; R is estimated from configured cash risk, not original filled stops. Approximate adaptive entry tapers/UTC daily closed-loss controls applied; Nasdaq risk ×0.25, news separate and bypassing adaptive tapers. NOT a test of the current 37-EA settings. '
    if daily_mode!='off':
        scope+='Custom daily loss limit blocks NEW entries after realized loss reaches the limit; reset on the next UTC day (Prague for FTMO). Existing positions are NOT liquidated and can exceed the limit. Simulation only; BAT settings are not changed. '
    scope+='Source entries and exits remain frozen; this is research, not a native equity backtest or prediction. Only positions opened and closed inside the selected window are replayed.'
    basis=f'Custom sizing scenario · ${initial:,.2f} start · '+(f'${value:,.2f} per trade' if mode=='fixed' else f'{value:g}% of entry-time simulated closed balance')
    h=history_from_trades(trades,start,end,period,original['label'].split(' · ')[0]+' · custom risk scenario',basis,scope,
                          original['missing_members'],initial)
    h.update(coverage=original['coverage'],requested_start=original['requested_start'],scenario=info,
             risk_settings=dict(risk_mode=mode,risk_value=value,initial_balance=initial,news_risk_percent=news,
                                daily_limit_mode=daily_mode,daily_limit_value=daily_value))
    if 'max_daily_stop_reserve_loss_cash' in info:h['stats']['max_daily_stop_reserve_loss_cash']=info['max_daily_stop_reserve_loss_cash']
    if original.get('evidence_kind'):
        h.update(evidence_kind=original['evidence_kind'],member_coverage=original['member_coverage'],
                 source_history_quality=original['source_history_quality'],
                 source_execution_warnings=original.get('source_execution_warnings',{}),
                 source_calendar_audits=original.get('source_calendar_audits',{}),
                 source_boundary_exclusions=original.get('source_boundary_exclusions',{}))
        h['scope']+='Frozen five-year native signal source; 3-year/recent views are slices/replays, not independent native tests. MT5 end-of-test liquidations are excluded. Source tick coverage: '+', '.join(original['source_history_quality'])+'. '
        if h['source_execution_warnings']:h['scope']+='Native stop/volume rejections are retained through actual fills; successful entries or trailing updates are not fabricated. '
        if h['source_calendar_audits']:h['scope']+='Sub-minute news results are especially sensitive to generated ticks; NOT a full real-tick execution validation. '
        if h['source_calendar_audits']:h['scope']+='Filled-stop-risk normalization does not reconstruct pending-order placement-time sizing; tiny/gap-shifted stop distances can exaggerate outcomes. '
    if original['coverage']=='partial':
        h['scope']='Partial coverage: requested start '+original['requested_start']+'. '+h['scope']
        if original['missing_members']:h['scope']+='Missing current members: '+', '.join(original['missing_members'])+'. '
    return _decorate_history(h)
