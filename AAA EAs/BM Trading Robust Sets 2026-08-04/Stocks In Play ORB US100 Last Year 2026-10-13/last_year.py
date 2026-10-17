"""Rolling-year repeat of the frozen 2x-volume protocol. No optimisation."""
from __future__ import annotations
import hashlib
import html
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'Stocks In Play ORB US100 Raw 2026-10-13'
START, END = '2025-10-13', '2026-10-13'
spec = importlib.util.spec_from_file_location('frozen_engine', OLD / 'run.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
HOLIDAYS = {
    '2025-09-01', '2025-11-27', '2025-12-25',
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03',
    '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
}
EARLY = {'2025-11-28', '2025-12-24'}


def cash_sessions():
    return [(d.strftime('%Y-%m-%d'), e.utc(d.strftime('%Y-%m-%d'), '09:30'),
             e.utc(d.strftime('%Y-%m-%d'), '13:00' if d.strftime('%Y-%m-%d') in EARLY else '16:00'))
            for d in pd.date_range('2025-08-01', '2026-10-12')
            if d.dayofweek < 5 and d.strftime('%Y-%m-%d') not in HOLIDAYS]


e.cash_sessions = cash_sessions


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def load():
    meta = json.loads((ROOT / 'DATA.json').read_text())
    source = ROOT / 'USTEC-M1.npz'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == meta['sha256']
    raw = np.load(source, allow_pickle=False)['rates']
    f = pd.DataFrame(raw)
    f['time'] = pd.to_datetime(f.time, unit='s', utc=True)
    assert f.time.is_unique and f.time.is_monotonic_increasing
    assert ((f.high >= f[['open', 'low', 'close']].max(axis=1)) &
            (f.low <= f[['open', 'high', 'close']].min(axis=1))).all()
    assert (f.tick_volume >= 0).all()
    f = f.set_index('time')
    f['used_spread'] = f.spread.where(f.spread > 0).ffill() * .01
    meta['zero_spread_bars'] = int((f.spread <= 0).sum())
    meta['unknown_spread_bars'] = int(f.used_spread.isna().sum())
    meta['median_spread_points'] = float(f.used_spread.median())
    # Provenance cross-check through the separate MCP connector.
    spot = json.loads((ROOT / 'MT5-spot-check.json').read_text())
    for r in spot:
        b = f.loc[pd.Timestamp(r['time'])]
        for k in ['open', 'high', 'low', 'close', 'tick_volume', 'spread']:
            assert abs(float(b[k]) - r[k]) < 1e-8
    meta['mcp_spot_check_bars_matched'] = len(spot)
    return f, meta


def opening_audit(f, contexts):
    rows, prior = [], []
    lookup = {c['date']: c for c in contexts}
    for day, start, _ in cash_sessions():
        v = f.reindex(pd.date_range(start, periods=5, freq='min')).tick_volume
        volume = int(v.sum()) if v.notna().all() else None
        baseline = (sum(prior[-14:]) / 14 if len(prior) >= 14 and
                    all(x is not None and x > 0 for x in prior[-14:]) else None)
        rvol = volume / baseline if volume is not None and baseline else None
        prior.append(volume)
        if START <= day < END:
            c = lookup[day]
            assert c['opening_volume'] == volume
            assert (c['rvol'] is None) == (rvol is None)
            if rvol is not None:
                assert abs(c['rvol'] - rvol) < 1e-12
            rows.append(dict(date=day, opening_volume=volume, previous_14_mean=baseline,
                             rvol=rvol, passes_2x=rvol is not None and rvol >= 2))
    valid = [r for r in rows if r['rvol'] is not None]
    peak = max(valid, key=lambda r: r['rvol']) if valid else None
    return dict(scheduled_sessions=len(rows), assessable_sessions=len(valid),
                unassessable_sessions=len(rows) - len(valid),
                qualifying_sessions=sum(r['passes_2x'] for r in rows),
                peak_rvol=peak, independently_reconciled=True, records=rows)


def run(cs, optimistic=False, extra_cost=0., start=START):
    balance, trades, sessions = 10000., [], []
    for c in cs:
        if not start <= c['date'] < END:
            continue
        status = c['data_skip']
        if status is None and (c['rvol'] is None or c['atr14'] is None):
            status = 'missing previous-14-session inputs'
        if status is None and c['rvol'] < 2:
            status = 'RVOL below 2.0'
        if status is None and c['opening_close'] == c['opening_open']:
            status = 'doji'
        t = e.simulate_trade(c, optimistic) if status is None else None
        if status is None and t is None:
            status = 'pending never triggered'
        if t is not None:
            lots = min(500., math.floor((balance * .01 / t['risk_points'] + 1e-12) / .01) * .01)
            if lots < .05:
                status = 'below broker minimum lot'
            else:
                status = 'trade'
                risk = lots * t['risk_points']
                net = lots * (t['side'] * (t['exit'] - t['entry']) - extra_cost)
                t.update(date=c['date'], rvol=c['rvol'], atr14=c['atr14'],
                         lots=round(lots, 2), starting_balance=balance, planned_risk_usd=risk,
                         net_usd=net, net_r=net / risk, ending_balance=balance + net,
                         extra_round_trip_cost_points=extra_cost,
                         notional_leverage=lots * t['entry'] / balance)
                assert risk <= balance * .01 + 1e-8
                balance += net
                trades.append(t)
        sessions.append(dict(date=c['date'], status=status, balance=balance, rvol=c['rvol'],
                             atr14=c['atr14'], opening_volume=c['opening_volume'],
                             average_previous_opening_volume=c['avg_previous_volume']))
    return dict(trades=trades, sessions=sessions, summary=e.metrics(trades, sessions))


def report(result):
    n = lambda v, dp=2: 'N/A' if v is None else f'{v:,.{dp}f}'
    s, gate = result['primary']['summary'], result['opening_audit']
    rows = []
    for title, key in [('Last 3 months', '3m'), ('Last 6 months', '6m'), ('Last year', '1y')]:
        q = result['periods'][key]['summary']
        rows.append('<tr>' + ''.join(f'<td>{x}</td>' for x in [title, q['trades'], n(q['win_rate_pct']) + '%',
                    n(q['profit_factor']), n(q['return_pct']) + '%', n(q['max_closed_dd_pct']) + '%',
                    n(q['sharpe_daily_252']), q['max_win_streak'], q['max_loss_streak']]) + '</tr>')
    monthly = []
    for month in sorted({x['date'][:7] for x in result['primary']['sessions']}):
        ts = [t for t in result['primary']['trades'] if t['date'].startswith(month)]
        monthly.append(f'<tr><td>{month}</td><td>{len(ts)}</td><td>{n(sum(t["net_usd"] for t in ts))}</td></tr>')
    trade_rows = []
    for t in result['primary']['trades']:
        trade_rows.append('<tr>' + ''.join(f'<td>{html.escape(str(x))}</td>' for x in [
            t['date'], 'Buy' if t['side'] == 1 else 'Sell', n(t['rvol']), t['entry_time'],
            n(t['entry']), n(t['stop']), t['exit_time'], n(t['exit']), t['exit_reason'],
            n(t['lots']), n(t['net_r']), n(t['net_usd'])]) + '</tr>')
    gate_rows = []
    for r in gate['records']:
        c = next(x for x in result['primary']['sessions'] if x['date'] == r['date'])
        gate_rows.append('<tr>' + ''.join(f'<td>{html.escape(str(x))}</td>' for x in [
            r['date'], r['opening_volume'], n(r['previous_14_mean']), n(r['rvol'], 4),
            'Yes' if r['passes_2x'] else 'No', c['status']]) + '</tr>')
    scenarios = []
    for key, label in [('primary', 'Conservative M1'), ('alternative_ordering', 'Alternative entry-bar ordering'),
                       ('cost_stress', 'Conservative +2 points per round trip')]:
        q = result[key]['summary']
        scenarios.append(f'<tr><td>{label}</td><td>{q["trades"]}</td><td>{n(q["return_pct"])}%</td>'
                         f'<td>{n(q["profit_factor"])}</td><td>{n(q["max_closed_dd_pct"])}%</td></tr>')
    points = [10000.] + [x['balance'] for x in result['primary']['sessions']]
    lo, hi = min(points), max(points)
    spread = max(hi - lo, 200.)
    curve = ' '.join(f'{20 + i * 960 / max(1,len(points)-1):.1f},{240-(v-lo)*180/spread:.1f}'
                     for i, v in enumerate(points))
    peak = gate['peak_rvol']
    peak_text = f'{peak["rvol"]:.4f}x on {peak["date"]}' if peak else 'Unavailable'
    caveat = ('No trades: the 2x opening-volume gate never passed on assessable sessions.' if not gate['qualifying_sessions']
              else 'M1 bar simulation, not tick-perfect execution. Check the trade and data-quality ledgers below.')
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>US100 stocks-in-play ORB · last year</title><style>
    body{{background:#081a16;color:#e5f2ee;font:16px system-ui;max-width:1280px;margin:auto;padding:28px}}h1,h2{{color:#71f4c6}}
    p{{line-height:1.6}}.notice{{background:#263124;border:1px solid #b29b43;padding:18px;border-radius:12px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}.card{{border:1px solid #30564a;padding:16px;border-radius:12px}}.card b{{display:block;font-size:26px}}
    table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:11px;border-bottom:1px solid #30564a;text-align:left}}th{{color:#71f4c6}}.scroll{{overflow:auto}}a{{color:#71f4c6}}summary{{cursor:pointer;padding:15px 0}}svg{{width:100%;background:#0c231d}}
    </style></head><body><p>RESEARCH ONLY · NO LIVE CHANGES · NO OPTIMISATION</p>
    <h1>US100 5-minute ORB — last year</h1><p>{START} through 2026-10-12 inclusive (end {END} exclusive). Exness USTEC, $10,000 starting balance, 1% balance risk per trade.</p>
    <div class="notice">{caveat}<br>This is a single-index tick-volume adaptation, not a replication of the top-20 stock-universe strategy. The tested gate remains <b>2.0x</b>, not the paper's 1.0x threshold.</div>
    <h2>Results</h2><div class="grid">{''.join(f'<div class="card">{label}<b>{value}</b></div>' for label,value in [
    ('Trades',s['trades']),('Return',n(s['return_pct'])+'%'),('PF',n(s['profit_factor'])),
    ('Win rate',n(s['win_rate_pct'])+'%'),('Closed DD',n(s['max_closed_dd_pct'])+'%'),
    ('Daily Sharpe',n(s['sharpe_daily_252'])),('Win / loss streak',str(s['max_win_streak'])+' / '+str(s['max_loss_streak']))])}</div>
    <p>Ending balance ${n(s['final_balance'])}. Closed-balance DD is not floating-equity DD. Undefined PF/win rate/Sharpe are not shown as zero.</p>
    <h2>Closed balance</h2><svg viewBox="0 0 1000 270" role="img" aria-label="Closed balance across exchange sessions"><polyline points="{curve}" fill="none" stroke="#71f4c6" stroke-width="3"/><text x="20" y="260" fill="#b9dbcf">{START}</text><text x="800" y="260" fill="#b9dbcf">2026-10-12</text></svg>
    <h2>Recent periods · independent $10,000 starts</h2><div class="scroll"><table><tr><th>Period</th><th>Trades</th><th>Win rate</th><th>PF</th><th>Return</th><th>Closed DD</th><th>Sharpe</th><th>Win streak</th><th>Loss streak</th></tr>{''.join(rows)}</table></div>
    <h2>Signal / coverage audit</h2><p>{gate['scheduled_sessions']} scheduled cash sessions; {gate['assessable_sessions']} assessable opening-volume ratios; {gate['unassessable_sessions']} unavailable ratios; {gate['qualifying_sessions']} at or above 2x. Peak: {peak_text}.</p>
    <p>Execution statuses: {html.escape(json.dumps(s['session_statuses']))}. Execution data gaps and missing prior ATR are exclusions, not trading filters. Opening-volume audit is independent of later-session coverage.</p>
    <h2>Execution sensitivity</h2><table><tr><th>Scenario</th><th>Trades</th><th>Return</th><th>PF</th><th>Closed DD</th></tr>{''.join(scenarios)}</table>
    <h2>Frozen rules</h2><p>09:30–09:35 New York opening candle, bullish buy stop at high / bearish sell stop at low, no doji. Tick-volume sum divided by the mean of the preceding 14 exchange-session opening sums must be at least 2.0. Stop 10% of previous-14-cash-session ATR (simple mean of true ranges). One trade per day, no TP, exit at NY cash close / 13:00 early close. DST handled by America/New_York.</p>
    <p>Bid OHLC plus recorded M1 spread; zero spread uses previous positive observation only. Lot floor 0.01, minimum 0.05, maximum 500, $1 per index point per lot. Zero explicit commission assumed for Pro. No margin, latency, rejection or within-minute spread model. Entry-bar conflicts use conservative sequencing; alternative shown separately.</p>
    <details><summary>Monthly trade counts / cash contributions</summary><table><tr><th>Month</th><th>Trades</th><th>Net USD</th></tr>{''.join(monthly)}</table></details>
    <details><summary>Every trade · times UTC</summary><div class="scroll"><table><tr><th>Date</th><th>Side</th><th>RVOL</th><th>Entry time</th><th>Entry</th><th>SL</th><th>Exit time</th><th>Exit</th><th>Reason</th><th>Lots</th><th>Net R</th><th>Net USD</th></tr>{''.join(trade_rows) or '<tr><td colspan="12">No trades</td></tr>'}</table></div></details>
    <details><summary>Every opening-volume decision</summary><div class="scroll"><table><tr><th>Date</th><th>5m ticks</th><th>Prior mean</th><th>RVOL</th><th>Pass 2x</th><th>Execution status</th></tr>{''.join(gate_rows)}</table></div></details>
    <h2>Provenance & sources</h2><p>{result['data']['rows']:,} M1 bars, {html.escape(result['data']['server'])}, through {html.escape(result['data']['last'])}; {result['data']['mcp_spot_check_bars_matched']} bars independently matched against MCP.</p>
    <p><a href="https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/">Original research</a> · <a href="https://nasdaqtrader.com/Trader.aspx?id=Calendar">2026 exchange calendar</a> · <a href="https://www.nasdaqtrader.com/content/technicalsupport/2025tradingcalendar.pdf">2025 calendar</a> · <a href="RESULTS.json">Full result ledger</a> · <a href="PROTOCOL.json">Frozen protocol</a></p></body></html>'''
    (ROOT / 'Results.html').write_text(doc, encoding='utf-8')


def main():
    protocol = json.loads((OLD / 'PROTOCOL.json').read_text())
    protocol.update(start=START, end_exclusive=END, warmup_start='2025-08-01',
                    engine_sha256=hashlib.sha256((OLD / 'run.py').read_bytes()).hexdigest(),
                    note='Only the date window changed; retains previous 2x interpretation, not a 1x paper replication.')
    save('PROTOCOL.json', protocol)
    f, provenance = load()
    cs = e.contexts(f)
    result = dict(protocol=protocol, data=provenance, opening_audit=opening_audit(f, cs),
                  primary=run(cs), alternative_ordering=run(cs, True), cost_stress=run(cs, extra_cost=2.),
                  periods={key: run(cs, start=day) for key, day in
                           [('3m', '2026-07-13'), ('6m', '2026-04-13'), ('1y', START)]})
    save('RESULTS.json', result)
    report(result)
    print(json.dumps(dict(summary=result['primary']['summary'],
                          opening_audit={k:v for k,v in result['opening_audit'].items() if k != 'records'},
                          qualifying_dates=[r['date'] for r in result['opening_audit']['records'] if r['passes_2x']]), indent=2))


if __name__ == '__main__':
    main()
