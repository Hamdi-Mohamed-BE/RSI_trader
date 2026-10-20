"""Self-contained, escaped HTML presentation of the frozen $1K replay.

This module only reads public result receipts and writes Results.html. It never
touches terminals, private connection files, strategy inputs, or the live site.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
from pathlib import Path
import statistics
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
UTC = timezone.utc
PRAGUE = ZoneInfo('Europe/Prague')
LABELS = {
    'xau-rsi-vwap': 'XAU RSI VWAP',
    'xau-orb-london-ny-overlap-m30': 'XAU ORB London–NY overlap M30',
    'xau-orb-new-york-m30': 'XAU ORB New York M30',
    'us100-orb-new-york-m30': 'US100 ORB New York M30',
    'us100-selective-orb-v3': 'US100 Selective ORB V3',
    'us100-orb-13utc-h1': 'US100 H1 ORB 13 UTC',
    'us100-h1-orb-13utc': 'US100 H1 ORB 13 UTC',
    'nasdaq-5m-candle-momentum': 'Nasdaq 5M candle momentum',
    'xau-ema3': 'XAU EMA3',
    'us100-month-end-flow': 'US100 month-end flow',
    'usdjpy-london-open-momentum': 'USDJPY London open momentum',
}
REASONS = {
    'opened': 'Admitted',
    'minimum_lot_over_budget': 'Minimum lot exceeds budget',
    'same_ea_exposure': 'Same EA already open',
    'permanent_loss_latch': 'Permanent loss latch',
    'daily_loss_latch': 'Daily loss latch',
    'daily_seven_entries': 'Daily seven-entry limit',
    'daily_three_net_losers': 'Daily three-loser limit',
    'aggregate_risk': 'Aggregate open-risk limit',
    'same_symbol_risk': 'Same-symbol open-risk limit',
    'equity_buffer': 'Equity buffer',
    'daily_reserved_loss': 'Daily reserved-loss budget',
    'margin_proxy': 'Estimated margin capacity',
    'three_second_wait': 'Three-second entry wait',
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def h(value):
    return escape(str(value), quote=True)


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def number(value, decimals=2):
    return f'{value:,.{decimals}f}' if finite(value) else '—'


def cash(value, signed=False):
    if not finite(value):
        return '—'
    sign = '+' if signed and value > 0 else '−' if value < 0 else ''
    return sign + '$' + number(abs(value))


def percent(value, signed=False):
    if not finite(value):
        return '—'
    return ('+' if signed and value > 0 else '') + number(value) + '%'


def pf(metrics):
    if finite(metrics.get('profit_factor')):
        return number(metrics['profit_factor'])
    return 'No losses' if metrics.get('profit_factor_status') == 'no_losing_trades' else '—'


def dt(value, local=False):
    if not finite(value):
        return '—'
    return datetime.fromtimestamp(value, PRAGUE if local else UTC).strftime('%Y-%m-%d %H:%M:%S')


def label(slug):
    return LABELS.get(slug, str(slug).replace('-', ' ').strip())


def table(headers, rows, caption=None):
    text = '<div class="table-wrap"><table>'
    if caption:
        text += '<caption>' + h(caption) + '</caption>'
    text += '<thead><tr>' + ''.join('<th scope="col">' + h(x) + '</th>' for x in headers) + '</tr></thead><tbody>'
    if rows:
        text += ''.join('<tr>' + ''.join('<td>' + h(x) + '</td>' for x in row) + '</tr>' for row in rows)
    else:
        text += '<tr><td colspan="' + str(len(headers)) + '">No matching records.</td></tr>'
    return text + '</tbody></table></div>'


def reduced_curve(curve, limit=1800):
    """Rendering only: preserve endpoints and every bucket's price extrema."""
    points = [x for x in curve if all(finite(x.get(k)) for k in ('epoch', 'balance', 'equity'))]
    if len(points) <= limit:
        return points
    stride = max(1, math.ceil(len(points) / max(1, (limit-2)//4)))
    chosen = {0, len(points)-1}
    for start in range(0, len(points), stride):
        indexes = range(start, min(start+stride, len(points)))
        for key in ('balance', 'equity'):
            chosen.add(min(indexes, key=lambda i: points[i][key]))
            chosen.add(max(indexes, key=lambda i: points[i][key]))
    return [points[i] for i in sorted(chosen)]


def cash_periods(result, plan):
    """Cash-flow dates, not misleading exit-date allocation of entry charges.

    Keeps curve event order, including same-second opening/closing cash. Uses
    Prague day labels like the replay guard, with zero/no-trade dates retained.
    """
    initial = float(plan.get('initial_balance', 1000))
    if not result.get('curve'):
        return [], []
    start = datetime.fromisoformat(plan['start_utc']).astimezone(PRAGUE)
    end = datetime.fromisoformat(plan['end_exclusive_utc']).astimezone(PRAGUE)
    end_date = (end-timedelta(microseconds=1)).date()
    days = {}
    d = start.date()
    while d <= end_date:
        days[d.isoformat()] = dict(date=d.isoformat(), net_cash=0., entries=0, closes=0,
                                  wins=0, losses=0, start_balance=None, end_balance=None,
                                  partial=(d == start.date() and start.time() != datetime.min.time()) or
                                          (d == end.date() and end.time() != datetime.min.time()))
        d += timedelta(days=1)
    prior = initial
    for point in result.get('curve', []):
        epoch, balance = point.get('epoch'), point.get('balance')
        if not finite(epoch) or not finite(balance):
            continue
        key = datetime.fromtimestamp(epoch, PRAGUE).date().isoformat()
        if key not in days:
            continue
        days[key]['net_cash'] += balance-prior
        prior = balance
    for decision in result.get('decisions', []):
        if decision.get('reason') == 'opened' and finite(decision.get('epoch')):
            key = datetime.fromtimestamp(decision['epoch'], PRAGUE).date().isoformat()
            if key in days:
                days[key]['entries'] += 1
    for trade in result.get('trades', []):
        if not finite(trade.get('cl')):
            continue
        key = datetime.fromtimestamp(trade['cl'], PRAGUE).date().isoformat()
        if key in days:
            days[key]['closes'] += 1
            days[key]['wins'] += trade.get('net', 0) > 0
            days[key]['losses'] += trade.get('net', 0) < 0
    balance = initial
    months = {}
    for row in days.values():
        row['net_cash'] = round(row['net_cash'], 8)
        row['start_balance'] = balance
        balance = round(balance + row['net_cash'], 8)
        row['end_balance'] = balance
        key = row['date'][:7]
        month = months.setdefault(key, dict(month=key, start_balance=row['start_balance'],
            end_balance=balance, net_cash=0., entries=0, closes=0, wins=0, losses=0))
        month['end_balance'] = balance
        for field in ('net_cash', 'entries', 'closes', 'wins', 'losses'):
            month[field] += row[field]
    return list(days.values()), list(months.values())


def trade_summary(trades):
    values = [float(t['net']) for t in trades]
    winners = [x for x in values if x > 0]
    losers = [x for x in values if x < 0]
    return dict(net=sum(values), count=len(values),
        win_rate=100*len(winners)/len(values) if values else None,
        profit_factor=sum(winners)/-sum(losers) if losers else None,
        profit_factor_status='finite' if losers else 'no_losing_trades' if winners else 'no_trades')


def per_ea_table(result, plan):
    rows = []
    for slug in plan.get('priority', result.get('per_ea', {}).keys()):
        counts = result.get('per_ea', {}).get(slug, {})
        decisions = [d for d in result.get('decisions', []) if d.get('ea') == slug]
        trades = [t for t in result.get('trades', []) if t.get('ea') == slug]
        risks = [d['minimum_lot_risk'] for d in decisions if finite(d.get('minimum_lot_risk'))]
        summary = trade_summary(trades)
        median = statistics.median(risks) if risks else None
        cap = plan.get('reference_risk_cap', .005)
        cap_range = (' / '.join(cash(v/cap) for v in (min(risks), median, max(risks)))
                     if risks and finite(cap) and cap > 0 else '—')
        rows.append([label(slug), counts.get('candidates', len(decisions)), counts.get('opened', 0),
            summary['count'], counts.get('minimum_lot_over_budget', 0), pf(summary),
            percent(summary['win_rate']), cash(summary['net'], True), cash(median), cap_range])
    return table(['EA', 'Source candidates', 'Admitted', 'Closed', 'Min-lot skips', 'Admitted PF',
        'Admitted wins', 'Closed net', 'Median min-lot stop risk', 'Reference balance needed at 0.5% cap: min / median / max'], rows)


def metrics_html(result):
    m = result.get('metrics', {})
    sharpe = next((m[k] for k in ('daily_closed_return_sharpe', 'daily_closed_sharpe', 'sharpe_daily_closed', 'sharpe') if k in m), None)
    entries = sum(d.get('reason') == 'opened' for d in result.get('decisions', []))
    rows = [
        ('Ending balance', cash(m.get('ending_balance'))),
        ('Ending sampled equity', cash(m.get('ending_sampled_equity'))),
        ('Closed-balance return', percent(m.get('return_pct'), True)),
        ('Whole positions closed', str(m.get('trades', len(result.get('trades', []))))),
        ('Entries admitted', str(entries)),
        ('Win rate', percent(m.get('win_rate_pct'))), ('Profit factor', pf(m)),
        ('Closed-position net profit', cash(m.get('net_profit'), True)),
        ('Max closed drawdown', cash(m.get('max_closed_dd_cash')) + ' / ' + percent(m.get('max_closed_dd_pct'))),
        ('Max sampled-equity drawdown', cash(m.get('max_sampled_equity_dd_cash')) + ' / ' + percent(m.get('max_sampled_equity_dd_pct'))),
        ('Max daily closed drawdown', cash(m.get('max_daily_closed_dd_cash'))),
        ('Max daily sampled-equity drawdown', cash(m.get('max_daily_sampled_equity_dd_cash'))),
        ('Max day-anchor sampled-equity loss', cash(m.get('max_daily_anchor_equity_loss'))),
        ('Max winning / losing streak', str(m.get('max_win_streak', '—')) + ' / ' + str(m.get('max_loss_streak', '—'))),
        ('Average win / loss', cash(m.get('average_win')) + ' / ' + cash(m.get('average_loss'))),
        ('Largest win / loss', cash(m.get('largest_win')) + ' / ' + cash(m.get('largest_loss'))),
        ('UTC daily closed-cash-return Sharpe', number(sharpe)),
        ('Closed trades / elapsed calendar day', number(m.get('average_trades_per_calendar_day'))),
        ('Closed trades / UTC weekday', number(m.get('average_trades_per_weekday'))),
        ('Open positions at endpoint', str(m.get('open_positions', '—'))),
        ('Permanent loss latch reached', 'Yes' if m.get('hard_loss_latch') else 'No'),
    ]
    return '<dl class="metrics">' + ''.join('<div><dt>'+h(k)+'</dt><dd>'+h(v)+'</dd></div>' for k, v in rows) + '</dl>'


def build_view(result, plan):
    days, months = cash_periods(result, plan)
    month_rows = [[m['month'], cash(m['net_cash'], True),
                   percent(100*m['net_cash']/m['start_balance'] if m['start_balance'] else None, True),
                   m['entries'], m['closes'], m['wins'], m['losses'], cash(m['end_balance'])] for m in months]
    day_rows = [[d['date'] + (' · partial UTC-window day' if d['partial'] else ''), cash(d['net_cash'], True),
                 d['entries'], d['closes'], d['wins'], d['losses'], cash(d['end_balance'])] for d in days]
    trade_rows = [[i+1, label(t.get('ea', '')), t.get('symbol', ''), t.get('side', ''), dt(t.get('op')),
                   dt(t.get('cl')), number(t.get('lots'), 3), number(t.get('open_price'), 3),
                   number(t.get('close_price'), 3), number(t.get('sl'), 3), number(t.get('tp'), 3),
                   cash(t.get('risk')), cash(t.get('gross'), True), cash(t.get('commission'), True),
                   cash(t.get('swap'), True), cash(t.get('net'), True), cash(t.get('balance'))]
                  for i, t in enumerate(result.get('trades', []))]
    decision_rows = [[dt(d.get('epoch')), label(d.get('ea', '')), REASONS.get(d.get('reason'), d.get('reason', '')),
                      cash(d.get('equity')), cash(d.get('budget')), cash(d.get('minimum_lot_risk')),
                      number(d.get('source_volume_ceiling'), 3), number(d.get('volume'), 3), cash(d.get('stop_risk'))]
                     for d in result.get('decisions', [])]
    reasons = result.get('metrics', {}).get('counts', {})
    reason_rows = [[REASONS.get(k, k), v] for k, v in sorted(reasons.items()) if k != 'closed']
    quality = result.get('mark_quality', {})
    quality_rows = [[k.replace('_', ' '), number(v, 0) if finite(v) else str(v)] for k, v in quality.items()]
    return dict(metrics=metrics_html(result), per_ea=per_ea_table(result, plan),
        reasons=table(['Decision', 'Count'], reason_rows),
        months=table(['Prague month', 'Net cash change', 'Cash return in displayed month portion', 'Entries', 'Closes', 'Wins', 'Losses', 'Ending balance'], month_rows),
        days=table(['Prague date', 'Net cash change', 'Entries', 'Closes', 'Wins', 'Losses', 'Ending balance'], day_rows),
        trades=table(['#', 'EA', 'Symbol', 'Side', 'Entry UTC', 'Exit UTC', 'Lots', 'Entry', 'Exit', 'Initial SL', 'TP',
            'Initial stop risk', 'Gross', 'Commission / fees', 'Swap', 'Net incl. stress', 'Balance after exit'], trade_rows),
        decisions=table(['Signal UTC', 'EA', 'Decision', 'Sampled equity', 'Risk budget', 'Min-lot stop risk',
            'Source lot ceiling', 'Replay lots', 'Initial stop risk'], decision_rows),
        quality=table(['Mark-quality field', 'Recorded value'], quality_rows),
        curve=reduced_curve(result.get('curve', [])),
        curve_original_points=len(result.get('curve', [])),
        scenario=result.get('scenario', {}), stress=bool(result.get('stress')))


def comparison(results):
    rows = []
    for r in results:
        m = r.get('metrics', {})
        skipped = sum(d.get('reason') == 'minimum_lot_over_budget' for d in r.get('decisions', []))
        sharpe = next((m[k] for k in ('daily_closed_return_sharpe', 'daily_closed_sharpe', 'sharpe_daily_closed', 'sharpe') if k in m), None)
        rows.append([r.get('scenario', {}).get('label', 'Unnamed'), 'Extra-cost sensitivity' if r.get('stress') else 'Source-account recorded costs',
            cash(m.get('ending_balance')), percent(m.get('return_pct'), True), m.get('trades', 0),
            percent(m.get('win_rate_pct')), pf(m), percent(m.get('max_closed_dd_pct')),
            percent(m.get('max_sampled_equity_dd_pct')), cash(m.get('max_daily_closed_dd_cash')),
            str(m.get('max_win_streak', 0))+' / '+str(m.get('max_loss_streak', 0)), number(sharpe), skipped])
    return table(['Risk preset', 'Cost basis', 'Ending cash', 'Return', 'Closed trades', 'Wins', 'PF',
        'Closed DD', 'Sampled equity DD', 'Daily closed DD', 'Win / loss streak', 'Daily Sharpe', 'Min-lot skips'], rows)


def broker_table(broker):
    rows = []
    for symbol, spec in broker.get('symbols', {}).items():
        rows.append([symbol, number(spec.get('volume_min'), 3), number(spec.get('volume_step'), 3),
            number(spec.get('trade_contract_size'), 2), number(spec.get('quote_spread'), 5),
            cash(spec.get('buy_margin_one_lot')), cash(spec.get('sell_margin_one_lot')), dt(spec.get('quote_epoch'))])
    return table(['Symbol', 'Min lot', 'Lot step', 'Contract size', 'Snapshot spread in price',
        'Current buy margin / lot', 'Current sell margin / lot', 'Quote UTC'], rows)


def source_coverage(coverage):
    rows = []
    for row in coverage:
        native = row.get('native', {})
        rows.append([label(row.get('ea', '')), row.get('candidates', '—'), row.get('end_censored', 0),
            row.get('owned_marks', '—'), dt(row.get('first_epoch')), dt(row.get('last_epoch')),
            native.get('history_quality', 'Not supplied')])
    return table(['EA source', 'Candidate fills', 'Boundary-censored', 'Owned marks', 'First source snapshot UTC',
        'Last source snapshot UTC', 'Native history quality'], rows)


def outcome_notes(results, plan):
    """Measured conclusions, never 'the winner' inferred from this short window."""
    base = next((r for r in results if r.get('scenario', {}).get('id') == 'fixed_5' and not r.get('stress')), None)
    small = next((r for r in results if r.get('scenario', {}).get('id') == 'fixed_2p50' and not r.get('stress')), None)
    notes = []
    if base:
        m = base.get('metrics', {})
        count = len(plan.get('priority', []))
        used = sum(base.get('per_ea', {}).get(slug, {}).get('opened', 0) > 0 for slug in plan.get('priority', []))
        skipped = sum(d.get('reason') == 'minimum_lot_over_budget' for d in base.get('decisions', []))
        notes.append('At fixed $5, '+str(used)+' of '+str(count)+' EAs admitted an order; '+str(skipped)+
            ' of '+str(len(base.get('decisions', [])))+' observed source entries were skipped for minimum lot size. '+
            'The admitted subset closed '+str(m.get('trades', 0))+' positions, returned '+percent(m.get('return_pct'), True)+
            ', and had PF '+pf(m)+'. That is not execution of the full nine-EA profile.')
    if small:
        m = small.get('metrics', {})
        losses = -sum(min(0., t.get('net', 0)) for t in small.get('trades', []))
        notes.append('The fixed-$2.50 view shows '+percent(m.get('return_pct'), True)+' and PF '+pf(m)+
            ', but only '+str(m.get('trades', 0))+' closed positions and '+cash(losses)+
            ' total recorded losses. A tiny denominator can inflate PF dramatically; it is not evidence of a dependable live edge or a recommended winner.')
    notes.append('Do not raise risk just to force all strategies into a $1,000 account. First validate minimum-size compatibility and actual demo execution; changing contract sizes, capital or the reference cap requires separate testing.')
    return '<div class="warning"><strong>What this window actually says</strong><ul>'+''.join('<li>'+h(x)+'</li>' for x in notes)+'</ul></div>'


def evidence_links(root):
    if root is None:
        return ''
    names = ('RESULTS.json', 'PLAN.json', 'FROZEN.json', 'BROKER.json', 'INPUTS.json',
             'native_plan.json', 'native_freeze.json', 'native_cases.json', 'VERIFICATION.json',
             'FEED CHECK.json', 'DEMO-BENCHMARKS.json')
    links = ['<a href="'+quote(name)+'">'+h(name)+'</a>' for name in names if (Path(root)/name).is_file()]
    return '<nav aria-label="Public evidence files" class="evidence">' + ' · '.join(links) + '</nav>'


def script_json(value):
    """Escapes script terminators, HTML comments, and JS line separators."""
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            .replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def render(data, root=None):
    plan, results, broker = data['plan'], data['results'], data.get('broker', {})
    if not results:
        raise ValueError('No finished replay outcomes: do not generate an empty results report')
    views = [build_view(r, plan) for r in results]
    default = next((i for i, r in enumerate(results) if r.get('scenario', {}).get('id') == 'fixed_5' and not r.get('stress')), 0)
    view = views[default]
    seen = set()
    scenarios = []
    for r in results:
        scenario = r.get('scenario', {})
        if scenario.get('id') not in seen:
            seen.add(scenario.get('id'))
            scenarios.append(scenario)
    options = ''.join('<option value="'+h(s.get('id', ''))+'"'+(' selected' if s.get('id') == view['scenario'].get('id') else '')+'>'+h(s.get('label', 'Unnamed'))+'</option>' for s in scenarios)
    generated = data.get('generated_at_utc', 'Not supplied')
    fields = ''.join('<section id="section-'+name+'"><h2>'+heading+'</h2><div id="'+name+'">'+view[name]+'</div></section>'
        for name, heading in [('metrics', 'Selected risk preset'), ('per_ea', 'Which EAs fit this $1,000 account?')])
    html = TEMPLATE
    tokens = {
        '@@WINDOW@@': h(plan.get('start_utc', 'Unknown'))+' → '+h(plan.get('end_exclusive_utc', 'Unknown'))+' (end exclusive)',
        '@@INITIAL@@': cash(plan.get('initial_balance', 1000)),
        '@@BROKER@@': h(broker.get('broker', 'Unknown'))+' · '+h(broker.get('server', 'Unknown'))+' · '+h(broker.get('currency', 'USD'))+' · 1:'+h(broker.get('leverage', 'Unknown')),
        '@@OPTIONS@@': options,
        '@@COMPARISON@@': comparison(results),
        '@@OUTCOME@@': outcome_notes(results, plan),
        '@@TOPSECTIONS@@': fields,
        '@@MONTHS@@': view['months'], '@@DAYS@@': view['days'], '@@TRADES@@': view['trades'],
        '@@DECISIONS@@': view['decisions'], '@@REASONS@@': view['reasons'], '@@QUALITY@@': view['quality'],
        '@@SPECS@@': broker_table(broker), '@@COVERAGE@@': source_coverage(data.get('coverage', [])),
        '@@EVIDENCE@@': evidence_links(root), '@@GENERATED@@': h(generated),
        '@@FEEDCHECK@@': ('<details><summary>Matched timestamp feed spot checks · not full-feed parity</summary><pre>'+
            h(json.dumps(data.get('feed_spot_checks'),ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details>'
            if data.get('feed_spot_checks') else '<p class="subtle">No feed-parity receipt supplied; parity is not assumed.</p>'),
        '@@PAYLOAD@@': script_json(dict(views=views, default=default)),
        '@@LIMITATIONS@@': ''.join('<li>'+h(s)+'</li>' for s in plan.get('limitations', [])),
        '@@DEFAULTLABEL@@': h(view['scenario'].get('label', 'Unnamed')),
    }
    # Replace each token once; escaped source strings cannot become template directives.
    for key, value in tokens.items():
        html = html.replace(key, value)
    return html


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prop Ready · $1,000 risk &amp; compounding replay</title>
<style>
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;color:#a7c9bf}
:root{color-scheme:dark;--bg:#06120f;--panel:#0b201a;--ink:#e9fff7;--muted:#a7c9bf;--line:#234b3e;--accent:#75efc1;--warn:#ffd18a;--loss:#ffb1a9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1500px;margin:auto;padding:36px 24px 80px}h1{font-size:clamp(29px,4vw,50px);line-height:1.12;max-width:1000px;margin:12px 0 18px}h2{font-size:24px;line-height:1.3;margin:0 0 16px}h3{font-size:18px;margin:20px 0 8px}p{max-width:1050px}a{color:var(--accent)}section{margin-top:40px;padding-top:30px;border-top:1px solid var(--line)}.eyebrow{color:var(--accent);font:12px/1.5 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}.subtle,small{color:var(--muted)}.warning{padding:18px 20px;border:1px solid #796238;border-radius:14px;background:#292619;color:var(--warn);margin:20px 0}.note{padding-left:16px;border-left:3px solid var(--line)}.controls{display:flex;gap:18px;flex-wrap:wrap;margin:24px 0}.controls label{display:flex;flex-direction:column;gap:7px;min-width:240px}select{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;max-width:100%}.table-wrap{overflow-x:auto;max-width:100%}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.45;font-variant-numeric:tabular-nums}th,td{padding:13px 11px;text-align:right;vertical-align:top;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;white-space:normal;min-width:90px}td:first-child,th:first-child{text-align:left;min-width:170px}td{white-space:nowrap}td:nth-child(2){white-space:normal}tbody tr:hover{background:#102a21}caption{text-align:left;margin-bottom:12px;color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:12px;margin:0}.metrics>div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.metrics dt{color:var(--muted);font-size:12px}.metrics dd{margin:6px 0 0;font-size:22px;font-weight:650;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.legend{display:flex;gap:25px;flex-wrap:wrap;color:var(--muted)}.legend span:before{content:"";display:inline-block;width:24px;height:3px;background:var(--accent);margin-right:8px;vertical-align:middle}.legend span:nth-child(2):before{background:#9dbdff}.chart{width:100%;height:310px;display:block}.chart text{font:12px system-ui;fill:var(--muted)}.chart path{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}.chart .balance{stroke:var(--accent)}.chart .equity{stroke:#9dbdff;stroke-dasharray:5 3}.chart line{stroke:var(--line);stroke-width:1}.chart .baseline{stroke-dasharray:3 5}details{margin:24px 0}summary{cursor:pointer;color:var(--accent);padding:8px 0}ul{padding-left:22px;max-width:1150px}.evidence{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0;font-size:13px}.rule-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px 28px}.rule-grid p{margin:8px 0}footer{margin-top:40px;color:var(--muted);font-size:12px}#selected-state{color:var(--accent)}@media(max-width:600px){main{padding:24px 14px 60px}.controls{display:block}.controls label{margin:14px 0;min-width:0}.metrics{grid-template-columns:1fr 1fr}.metrics>div{padding:12px}.metrics dd{font-size:19px}.chart{height:280px}th,td{padding:11px 8px}h2{font-size:22px}}@media(max-width:360px){.metrics{grid-template-columns:1fr}}
</style></head><body><main>
<header><div class="eyebrow">Calyx · recorded research · no live account changes</div>
<h1>Can Prop Ready fit a $1,000 account?</h1>
<p>Five risk presets, the same nine strategies, and a separate extra-cost check. This is a shared-ledger replay of native standalone signals—not a native simultaneous portfolio backtest or a promise of live returns.</p>
<p class="subtle">UTC window: @@WINDOW@@<br>Starting cash: @@INITIAL@@ · Target account specifications: @@BROKER@@</p>
<div class="warning"><strong>Important: this is not an exact current-demo cost backtest.</strong> The connected target is Exness-MT5Trial15 (Pro-like contracts); fresh standalone sources use isolated Exness-MT5Trial16 (Raw-like pricing). Source US100 and USDJPY entry receipts include zero bid–ask spread plus recorded commissions, while the target demo snapshot spreads are positive. The base view retains source-account costs. The stress view adds a current-demo snapshot spread at <em>each</em> side plus doubled negative swap; this is a sensitivity, not exact replacement of Raw pricing with Pro pricing. Prices and fills can also differ. Neither view is a verified native backtest on your currently connected account.</div>
<p class="note">No strategies, BATs, risk inputs or live positions were changed. Both existing DI filters remain <strong>ON</strong>; all five included ORBs retain <strong>0.5R</strong>. The comparison changes only replay sizing and the explicit cost sensitivity.</p></header>

@@OUTCOME@@
<section><h2>Risk comparison · all presets</h2>
<p class="subtle">Percentage budgets use current sampled equity, but every preset still has the existing initial-reference cap of <strong>$5 per position</strong>. A 1% input therefore does not risk $10 here. The original source strategy’s lot request can impose a second ceiling. Minimum-size orders are skipped rather than rounded above the replay budget.</p>
@@COMPARISON@@</section>

<section><h2>Explore one preset</h2><div class="controls">
<label for="scenario">Risk setting<select id="scenario">@@OPTIONS@@</select></label>
<label for="cost">Cost setting<select id="cost"><option value="0">Source-account recorded costs</option><option value="1">Extra current-demo spread + negative-swap sensitivity</option></select></label>
</div><p id="selected-state" role="status" aria-live="polite">@@DEFAULTLABEL@@ · source-account recorded costs</p></section>
@@TOPSECTIONS@@
<p class="subtle">Min-lot stop risk comes from observed source entries and the target demo’s minimum lot. Reference-balance values are min / median / max of that risk ÷ 0.5%; they test only the reference-cap constraint, not margin or portfolio safety. A fixed-$5 allocation remains a $5 ceiling even at a larger balance. No source signals means no inferred capital requirement. An EA skipped for minimum size is operationally incompatible with this budget; a zero admitted return does <strong>not</strong> mean its strategy has no edge.</p>

<section><h2>Cash path · selected preset</h2><div class="legend"><span>Closed balance</span><span>Sampled equity</span></div>
<svg class="chart" id="cash-chart" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Closed balance and sampled equity in US dollars</title><desc id="chart-desc">Chronological replay cash and owned-position floating samples. Missing intratrade extrema are not reconstructed.</desc></svg>
<p class="subtle" id="chart-note"></p><p class="subtle">Floating marks are past-only, own-position five-minute samples; no future interpolation. Chart downsampling is visual only. Drawdown metrics use the full replay path, but are still sampled estimates—not tick-accurate worst losses. Daily drawdowns reset on Europe/Prague calendar midnight, including daylight-saving time.</p></section>

<section><h2>Monthly and daily cash breakdown</h2><p class="subtle">These are the observed portions of August, September and October, not three full months. Cash changes include entry charges when paid, not only a whole trade’s net assigned to its exit day. Win/loss counts use whole-position closures. Days use Europe/Prague; the UTC test window creates partial boundary dates.</p><div id="months">@@MONTHS@@</div><details><summary>All daily dates, including no-trade dates</summary><div id="days">@@DAYS@@</div></details></section>

<section><h2>Why signals were admitted or skipped</h2><div id="reasons">@@REASONS@@</div><details><summary>Every observed source-entry decision</summary><p class="subtle">This is the frozen standalone-source candidate ledger. An entry rejected by this portfolio can change an EA’s later state and create signals absent from its standalone run; those alternative signals cannot be invented here. These rows are not a complete counterfactual native order stream.</p><div id="decisions">@@DECISIONS@@</div></details></section>

<section><h2>Trade-by-trade · admitted positions</h2><p class="subtle">Times are UTC. Whole-position net includes the selected sensitivity. Gross, commission/fees and swap columns are their scaled source components; extra spread deductions and cent rounding are also included in net. Boundary-forced tester closes are not treated as natural strategy exits; admitted positions still open at the endpoint remain open in sampled equity.</p><div id="trades">@@TRADES@@</div></section>

<section><h2>What the existing guards mean on $1,000</h2><div class="rule-grid">
<p><strong>Per-position ceiling:</strong> $5 initial-stop risk, or the lower requested allocation/source lot ceiling. Stops and fills can slip.</p>
<p><strong>Open risk:</strong> $22.50 overall; $15 on one symbol. This is not the same as a guaranteed daily maximum loss.</p>
<p><strong>Daily reserved loss:</strong> $30 reference budget, including a 25% stop-risk reserve and $0.50 cash reserve per position.</p>
<p><strong>Equity protection:</strong> $920 projected buffer; $900 hard reference floor; $50 hard day-anchor loss latch.</p>
<p><strong>Frequency:</strong> at most seven entries and three net losing positions per Prague day; fixed priority and a three-second entry wait.</p>
<p><strong>Compounding:</strong> percentage allocation changes with sampled equity; the original reference does not automatically rebase. Gains do not raise the $5 ceiling.</p>
</div><p class="warning">Guard thresholds are controls, not guaranteed realized loss caps. Gaps, slippage, simultaneous exposure, sample timing and broker execution can exceed an intended limit. A $1,000 account is not made safe by selecting high leverage, and this study does not support a reliable 2%-per-day or 10%-per-month target.</p></section>

<section><h2>Practical next steps · not a live optimum</h2><ul>
<li><strong>Solve order-size feasibility first.</strong> Keep the existing safety guards and skip orders whose true minimum-lot stop risk is too large. Do not tighten a strategy’s stop solely to make the lot size fit.</li>
<li><strong>Use the demo to verify the actual order stream.</strong> Check broker costs, symbols, minimum lots, source-state differences and every skipped order before treating this research replay as attainable execution.</li>
<li><strong>Do not call the 1% input full compounding.</strong> All five presets remain capped at $5 initial-stop risk here. Raising the reference cap or rebasing it after profits would be a new, separately tested risk policy—not something this replay authorizes.</li>
<li><strong>Test smaller contract sizes or more capital separately.</strong> The minimum-capital estimates above only address one order’s stop-risk constraint; the same nine EAs still need simultaneous-risk and margin headroom.</li>
<li><strong>Validate longer, unchanged rules before increasing risk.</strong> These two recent months cannot establish a best live percentage, dependable monthly income, or a low blow-up probability. A positive winner chosen here still needs forward demo evidence.</li>
</ul></section>

<section><h2>Broker-size and cost assumptions</h2>@@SPECS@@
<p class="subtle">These are the current target-account contract, quote and read-only margin snapshots—not a historical spread or high-margin-requirement schedule. The replay prefers native entry-time source-account OrderCalcMargin receipts when recorded. Otherwise current buy/sell one-lot margins are scaled by historical entry price, except USD-base USDJPY where the fallback per-lot proxy is held fixed. Neither is certification of historical target Trial15 account margin tiers. Gross margin is reserved without hedging discounts.</p>
<p><strong>Source-account recorded-cost view:</strong> Trial16 native source fills, spreads, commissions/fees and swaps are scaled to admitted lots, with entry and exit cash rounded to cents. This retains Raw-like source commissions and is not a current-demo Pro cost model. Native tester costs are not a certification of historical financing or real live execution.</p>
<p><strong>Extra-cost sensitivity:</strong> one additional observed snapshot spread from the target Trial15 demo is charged at each side, and negative final swap is doubled. This is deliberately an extra charge on top of source fills and commissions, not replacement of the embedded spread or exact Pro repricing. Signals and exits are unchanged.</p>
<p class="subtle">Initial risk prefers native entry-time source-account OrderCalcProfit receipts for the actual fill and original stop; filled-price geometry is only a fallback. Applying target minimum lots does not turn source-account receipts into exact historical Trial15 execution. The pre-request quote and slippage boundary are not reconstructible. <a href="https://www.mql5.com/en/docs/trading/ordercalcprofit">MQL5 profit estimation</a> and <a href="https://www.mql5.com/en/docs/trading/ordercalcmargin">MQL5 margin estimation</a> describe the broker/account-dependent calculations. <a href="https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/leveraged-investing-strategies-know-risks-using-these-advanced-investment-tools">Investor.gov: general leverage risks</a> (not this CFD broker’s contract rules).</p>@@FEEDCHECK@@</section>

<section><h2>Evidence quality and limits</h2>@@COVERAGE@@<details><summary>Selected replay’s floating-mark quality</summary><div id="quality">@@QUALITY@@</div></details>
<ul>@@LIMITATIONS@@<li>Risk presets were specified before replay results; choosing a live preset from just these two exposed months would still be retrospective selection.</li><li>Sharpe uses daily closed-cash returns on all 61 UTC calendar dates, including no-trade dates, annualized by √365 when supplied—not a confidence score. Daily cash tables use Prague dates for consistency with guard resets. PF and win streaks can be dominated by very few trades.</li><li>Minimum-lot skips mean a lower-risk preset may be a materially different admitted subset of the nine-strategy profile.</li><li>Daily sampled-equity protection, original-stop reservations and a margin proxy cannot reproduce every native guard state, current-stop modification, cooldown or simultaneous execution outcome.</li></ul>
@@EVIDENCE@@</section>
<footer>Generated from frozen public research receipts at @@GENERATED@@. Research only. No optimization, deployment, automatic reference rebasing or live-account changes.</footer>
</main><script id="replay-data" type="application/json">@@PAYLOAD@@</script>
<script>
(()=>{'use strict';
const data=JSON.parse(document.getElementById('replay-data').textContent), select=document.getElementById('scenario'), cost=document.getElementById('cost');
let current=data.default;
const money=n=>'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
function draw(){
 const view=data.views[current],points=view.curve,svg=document.getElementById('cash-chart'),ns='http://www.w3.org/2000/svg';
 const width=Math.max(280,Math.round(svg.getBoundingClientRect().width||700)),height=width<450?280:310,left=75,right=20,top=20,bottom=54;
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
 svg.replaceChildren();
 function node(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs||{}))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;svg.appendChild(n);return n;}
 node('title',{id:'chart-title'},'Closed balance and sampled equity in US dollars');node('desc',{id:'chart-desc'},'Past-only owned-position sampled path; not tick-accurate drawdown.');
 if(!points.length){node('text',{x:left,y:70},'No recorded path');return;}
 const xs=points.map(p=>p.epoch),ys=points.flatMap(p=>[p.balance,p.equity]),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys),pad=Math.max(.5,(ymax-ymin)*.12);
 const low=ymin-pad,high=ymax+pad,x=t=>left+(t-xmin)/Math.max(1,xmax-xmin)*(width-left-right),y=v=>top+(high-v)/(high-low)*(height-top-bottom);
 for(let i=0;i<4;i++){const val=low+(high-low)*i/3,yy=y(val);node('line',{x1:left,x2:width-right,y1:yy,y2:yy});node('text',{x:left-8,y:yy+4,'text-anchor':'end'},money(val));}
 for(let i=0;i<3;i++){const t=xmin+(xmax-xmin)*i/2;node('text',{x:x(t),y:height-bottom+22,'text-anchor':i===0?'start':i===2?'end':'middle'},new Date(t*1000).toISOString().slice(0,10));}
 for(const key of ['equity','balance'])node('path',{class:key,d:points.map((p,i)=>(i?'L':'M')+x(p.epoch).toFixed(2)+','+y(p[key]).toFixed(2)).join(' ')});
 node('text',{x:left,y:height-5},'UTC date');node('text',{x:width-right,y:height-5,'text-anchor':'end'},'USD');
 document.getElementById('chart-note').textContent=`${view.curve_original_points.toLocaleString()} recorded path observations; ${points.length.toLocaleString()} extrema-preserving points rendered.`;
}
function update(){const stress=cost.value==='1';const i=data.views.findIndex(v=>v.scenario.id===select.value&&v.stress===stress);if(i<0){document.getElementById('selected-state').textContent='No completed outcome for this combination.';return;}current=i;const v=data.views[i];for(const id of ['metrics','per_ea','months','days','trades','decisions','reasons','quality'])document.getElementById(id).innerHTML=v[id];document.getElementById('selected-state').textContent=v.scenario.label+' · '+(v.stress?'extra-cost sensitivity':'source-account recorded costs');draw();}
select.addEventListener('change',update);cost.addEventListener('change',update);new ResizeObserver(draw).observe(document.getElementById('cash-chart'));draw();
})();
</script></body></html>'''


def main():
    source = ROOT/'RESULTS.json'
    if not source.is_file():
        print('Report template ready; RESULTS.json is not present. No empty report generated.')
        return
    output = ROOT/'Results.html'
    output.write_text(render(read(source), ROOT), encoding='utf-8')
    print('Created ' + str(output))


if __name__ == '__main__':
    main()
