"""Only independently verified, period-matched News Pulse evidence is public."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from calendar import monthrange
from pathlib import Path
from typing import Any
from .news_profiles import MULTI_PROFILE, MULTI_SLUGS

NEWS_SLUGS=frozenset({'news-pulse-xau','news-pulse-xag','news-pulse-btc','news-pulse-eurusd'})
NEWS_EVIDENCE_VERSION=1
XAU_PROFILE='xau-event-specific-2026-09-19'
CACHE_ROOT=Path(__file__).resolve().parents[1]/'data'/'evidence-cache'/'v1'

def load_news_summary(slug: str, period: str='3y') -> dict[str, Any] | None:
    if slug not in NEWS_SLUGS or period not in {'6m','1y','3y','5y'}:
        return None
    path=CACHE_ROOT/'products'/slug/'standard'/f'{period}.json'
    if not path.is_file():
        return None
    try:
        payload=json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None
    if (not isinstance(payload, dict) or payload.get('news_evidence_version')!=NEWS_EVIDENCE_VERSION
            or payload.get('period_key')!=period
            or not payload.get('independent_native_run')
            or not payload.get('calendar_verified')):
        return None
    try:
        start=date.fromisoformat(payload['available_from'])
        end=date.fromisoformat(payload['available_to'])
        months={'6m':6,'1y':12,'3y':36,'5y':60}[period]
        year,month=divmod(end.year*12+end.month-1-months,12)
        expected_start=date(year,month+1,min(end.day,monthrange(year,month+1)[1]))
        if start!=expected_start or payload['stats']['from']!=str(start) or payload['stats']['to']!=str(end):
            return None
    except (KeyError,TypeError,ValueError):
        return None
    if slug=='news-pulse-xau' and payload.get('strategy_profile')!=XAU_PROFILE:
        return None
    if slug in MULTI_SLUGS and payload.get('strategy_profile')!=MULTI_PROFILE:
        return None
    return payload


def news_payload_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """Build public evidence only from an audited independent native window."""
    start, end = result['from_date'], result['to_exclusive']
    stats = {**result['stats'], 'from': start, 'to': end}
    trades = result['trades']
    if not result['calendar_complete'] or result['model'] != 4:
        raise ValueError('News coverage requires an audited Model 4 run.')
    if len(trades) != stats['trades'] or abs(sum(t['net_profit'] for t in trades) - stats['net_profit']) >= .05:
        raise ValueError('News trade ledger does not reconcile with the native report.')
    if any(not start <= t['open_time'][:10] < end for t in trades):
        raise ValueError('News trade falls outside the independent test window.')
    series = [dict(point) for point in result['series']]
    if not series or series[0]['time'][:10] > start:
        series.insert(0, {'time': start+'T00:00:00', 'balance': stats['initial_balance']})
    series.append({'time': end+'T00:00:00', 'balance': stats['final_balance']})
    xau_profile = result.get('slug') == 'news-pulse-xau'
    settings_note = (
        "XAU production profile: T-15, live Ask/Bid, 4-unit offset, 4-unit stop, no TP or trailing, "
        "both pending sides remain armed until the 60-second cleanup. "
        if xau_profile else
        "Current market-specific production geometry and native trailing are retained. "
    )
    notice = (
        f"Independent native MT5 run of current News Pulse v2.16, {start} to {end} (end exclusive), "
        f"starting from $10,000. Official BLS/Federal Reserve calendar: {result['calendar_expected']} releases; "
        f"{result['calendar_attempted']} attempted and {result['calendar_placed']} event straddles placed. "
        f"{len(result['events_without_closed_trades'])} scheduled events produced no closed trade. "
        f"MT5 reports {stats['history_quality']}; real-tick mode was requested, but older missing ticks may be generated. "
        "Original Exness XAUUSD/XAGUSD/BTCUSD evidence account; broker spread and recorded commission/swap included. "
        "Fixed 1 ms simulated delay, not a live-slippage guarantee. " + settings_note + "Risk is 0.75% planned "
        "per pending stop / 1.50% combined; rounding, gaps and costs can exceed that budget. "
        "PF and win rate are calculated after recorded fees; drawdown is native relative equity drawdown. "
        "No multi-year slicing or window rebasing; portfolio adaptive scaling is calculated separately."
    )
    if result.get('strategy_profile')==XAU_PROFILE:
        notice=(
            f"Independent native MT5 run of approved XAU event-specific v2.16, {start} to {end} (end exclusive), $10,000 start. "
            f"Official calendar: {result['calendar_expected']} releases; {result['calendar_attempted']} attempted; {result['calendar_placed']} placed. "
            f"MT5 reports {stats['history_quality']}; missing real ticks may be generated. "
            "Historical Exness bid/ask spread, recorded commission/swap and native gap fills included; fixed 1ms simulation is not a live-slippage guarantee. "
            "0.75% planned equity risk per pending side; both sides retained, adaptive exempt. Rounding, costs and gaps can exceed 1.50%. "
            "HINDSIGHT-OPTIMIZED: NFP/CPI/FOMC settings were selected using September-2025 to September-2026 history, overlapping these results. "
            "Earlier-selected settings returned +5.70% on later validation versus +19.34% for the previous preset. "
            "No future profitability claim. Each website period is a separate fresh-balance native run; dates differ from the September-19 research comparison. "
            "Calendar verification concerns release times, not verified historical-vintage data availability."
        )
    multi=result.get('strategy_profile')==MULTI_PROFILE
    if multi:
        notice=(
            f"Independent native MT5 v2.17 full-year optimized {result['label']} run, {start} to {end} (end exclusive), $10,000 start. "
            f"Official calendar: {result['calendar_expected']} releases; {result['calendar_attempted']} attempted; {result['calendar_placed']} placed. "
            f"MT5 history quality: {stats['history_quality']}; missing real ticks may be generated. "
            "Historical Exness bid/ask spread and recorded commission/swap included. Native gap fills and fixed 1ms simulated delay are not a live-liquidity or slippage guarantee. "
            "HINDSIGHT-OPTIMIZED: parameters were selected using 2025-09-19 to 2026-09-19, overlapping these results. "
            "0.75% planned equity risk per side; both directions retained, no adaptive taper. Tight stops, rounding, fees and news gaps can produce much larger losses. "
            "Every website period is an independent fresh-balance run ending 2026-09-05, not the September-19 research comparison. "
            "These historical returns are not expected future returns or evidence of prop-firm safety. Calendar verification covers release times, not historical data vintages."
        )
    return {
        'strategy_profile':result.get('strategy_profile','news-pulse-v2.15'),
        'optimization_in_sample':result.get('optimization_in_sample',False),
        'event_parameters':result.get('parameters'),
        'selection_window':result.get('selection_window'),
        'source_sha256':result.get('build',{}).get('source_sha256'),
        'evidence_label':('Hindsight-optimized event-specific — independent period replay' if multi else 'Hindsight-optimized XAU event-specific — independent period replay' if result.get('strategy_profile')==XAU_PROFILE else 'Official-calendar native period replay'),
        'label': result['label'], 'period': f'{start} to {end}', 'period_key': result['period_key'],
        'mode': 'standard', 'currency': 'USD', 'series': series, 'stats': stats,
        'available_from': start, 'available_to': end, 'cached_trade_count': len(trades),
        'trade_coverage_from': min((t['open_time'] for t in trades), default=None),
        'trade_coverage_to': max((t['close_time'] for t in trades), default=None),
        'source': 'precomputed-native-mt5-cache', 'notice': notice, 'history_quality': stats['history_quality'],
        'generated_at': datetime.now(timezone.utc).isoformat(), 'news_evidence_version': NEWS_EVIDENCE_VERSION,
        'independent_native_run': True, 'calendar_verified': True,
        **{key: result[key] for key in ('calendar_sha256', 'calendar_expected', 'calendar_attempted', 'calendar_placed',
                                      'events_without_closed_trades', 'source_report_sha256', 'source_report')},
        'data_model': 'MT5 Model 4; real-tick percentage disclosed', 'execution_delay_ms': 1,
        'equity_drawdown_basis': 'Native maximum relative equity drawdown; includes floating P/L',
    }
