"""Frozen, offline M1 US100 adaptation. No terminal writes or trading APIs."""
from __future__ import annotations

import hashlib
import html
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'AAA Final EAs/AAA Final US100 Asia London Continuation EA/Research/data'
NY = 'America/New_York'
HOLIDAYS = {
  2019: '01-01 01-21 02-18 04-19 05-27 07-04 09-02 11-28 12-25',
  2020: '01-01 01-20 02-17 04-10 05-25 07-03 09-07 11-26 12-25',
  2021: '01-01 01-18 02-15 04-02 05-31 07-05 09-06 11-25 12-24',
  2022: '01-17 02-21 04-15 05-30 06-20 07-04 09-05 11-24 12-26',
}
EARLY = {2019: '07-03 11-29 12-24', 2020: '11-27 12-24', 2021: '11-26', 2022: '11-25'}
HOLIDAYS = {f'{y}-{d}' for y, ds in HOLIDAYS.items() for d in ds.split()}
EARLY = {f'{y}-{d}' for y, ds in EARLY.items() for d in ds.split()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def utc(day, time):
    return pd.Timestamp(f'{day} {time}', tz=NY).tz_convert('UTC')


def cash_sessions():
    out = []
    for dt in pd.date_range('2019-07-16', '2022-12-31', freq='D'):
        day = dt.strftime('%Y-%m-%d')
        if dt.dayofweek < 5 and day not in HOLIDAYS:
            out.append((day, utc(day, '09:30'), utc(day, '13:00' if day in EARLY else '16:00')))
    return out


def load():
    manifest = json.loads((DATA / 'manifest.json').read_text())
    indexed = {r['file']: r for r in manifest['files']}
    frames = []
    provenance = []
    for year in range(2019, 2023):
        p = DATA / f'Exness-USTEC-M1-{year}.csv.gz'
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest == indexed[p.name]['sha256'], f'Changed source {p.name}'
        f = pd.read_csv(p)
        f['time'] = pd.to_datetime(f['time'], utc=True)
        assert f['time'].is_unique and f['time'].is_monotonic_increasing
        for col in ['open', 'high', 'low', 'close', 'tick_volume', 'spread']:
            assert f[col].notna().all(), col
        assert ((f.high >= f[['open', 'close', 'low']].max(axis=1)) &
                (f.low <= f[['open', 'close', 'high']].min(axis=1))).all()
        frames.append(f)
        provenance.append({'file': p.name, 'sha256': digest, 'rows': len(f),
                           'first': f.time.iloc[0].isoformat(), 'last': f.time.iloc[-1].isoformat()})
    f = pd.concat(frames, ignore_index=True).set_index('time').sort_index()
    assert f.index.is_unique
    # A zero spread in MT5 minute history is not proof of frictionless execution.
    positive = f['spread'].where(f['spread'] > 0)
    f['used_spread'] = positive.ffill() * .01
    return f, {'files': provenance, 'saved_specification': manifest['specification'],
               'zero_spread_rows': int((f.spread <= 0).sum()),
               'unknown_initial_spread_rows': int(f.used_spread.isna().sum()),
               'median_used_spread_index_points': float(f.used_spread.median())}


def contexts(f):
    out = []
    previous_close = None
    for day, start, end in cash_sessions():
        bars = f.loc[(f.index >= start) & (f.index < end)]
        opening = bars.loc[bars.index < start + pd.Timedelta(minutes=5)]
        expected_opening = pd.date_range(start, periods=5, freq='min')
        expected_cash = pd.date_range(start, end - pd.Timedelta(minutes=1), freq='min')
        close_rows = f.loc[(f.index >= end) & (f.index <= end + pd.Timedelta(minutes=2))]
        # If no post-close quote exists, last cash bar close is not called a 16:00 fill.
        reason = None
        if not opening.index.equals(expected_opening):
            reason = 'incomplete opening five minutes'
        elif not bars.index.equals(expected_cash):
            reason = 'missing minute within cash session'
        elif close_rows.empty:
            reason = 'no cash-close quote within two minutes'
        elif bars.used_spread.isna().any() or not math.isfinite(float(close_rows.used_spread.iloc[0])):
            reason = 'unknown spread'
        if len(bars):
            high, low, close = float(bars.high.max()), float(bars.low.min()), float(bars.close.iloc[-1])
            complete_cash = bars.index.equals(expected_cash)
            tr = max(high - low, abs(high - previous_close), abs(low - previous_close)) if previous_close is not None and complete_cash else None
            previous_close = close if complete_cash else None
        else:
            tr = None
            previous_close = None
        good_opening = opening.index.equals(expected_opening)
        out.append({'date': day, 'start': start, 'end': end, 'bars': bars,
                    'close_row': close_rows.iloc[0] if len(close_rows) else None,
                    'close_time': close_rows.index[0] if len(close_rows) else None,
                    'opening_volume': float(opening.tick_volume.sum()) if good_opening else None,
                    'opening_high': float(opening.high.max()) if good_opening else None,
                    'opening_low': float(opening.low.min()) if good_opening else None,
                    'opening_open': float(opening.open.iloc[0]) if good_opening else None,
                    'opening_close': float(opening.close.iloc[-1]) if good_opening else None,
                    'true_range': tr, 'data_skip': reason})
    # Strictly shift inputs by one session. Missing sessions remain missing, not compressed away.
    for i, c in enumerate(out):
        prior = out[i-14:i] if i >= 14 else []
        volumes = [p['opening_volume'] for p in prior]
        ranges = [p['true_range'] for p in prior]
        c['avg_previous_volume'] = float(np.mean(volumes)) if len(volumes) == 14 and all(v is not None and v > 0 for v in volumes) else None
        c['atr14'] = float(np.mean(ranges)) if len(ranges) == 14 and all(v is not None and v > 0 for v in ranges) else None
        c['rvol'] = c['opening_volume'] / c['avg_previous_volume'] if c['opening_volume'] is not None and c['avg_previous_volume'] else None
    return out


def simulate_trade(c, optimistic=False):
    side = 1 if c['opening_close'] > c['opening_open'] else -1
    trigger = c['opening_high'] if side == 1 else c['opening_low']
    dist = c['atr14'] * .10
    entry = stop = None
    ambiguous = False
    for tm, b in c['bars'].iloc[5:].iterrows():
        sp = float(b.used_spread)
        eo, eh, el, ec = [float(b[k]) + (sp if side == 1 else 0) for k in ['open', 'high', 'low', 'close']]
        xo, xh, xl, xc = [float(b[k]) + (sp if side == -1 else 0) for k in ['open', 'high', 'low', 'close']]
        new = entry is None
        gap = False
        if new:
            triggered = eh >= trigger if side == 1 else el <= trigger
            if not triggered:
                continue
            gap = eo >= trigger if side == 1 else eo <= trigger
            entry = round((max(trigger, eo) if side == 1 else min(trigger, eo)) + 1e-12, 2)
            stop = round(entry - side * dist, 2)
            actual_risk = abs(entry - stop)
            entry_time = tm
            entry_spread = sp
            if actual_risk <= 0:
                return None
        hit = xl <= stop if side == 1 else xh >= stop
        if new and hit and not gap:
            ambiguous = True
            # High-before-low for longs / low-before-high for shorts is the conservative case.
            # Alternative ordering can exclude only the opposite extreme BEFORE entry.
            if optimistic:
                hit = xc <= stop if side == 1 else xc >= stop
        if hit:
            # Opening gaps apply only to positions already held at this minute's open,
            # or entries executed at that open. Never use a pre-entry opening price as an exit.
            exit_price = min(stop, xo) if side == 1 else max(stop, xo)
            if new and not gap:
                exit_price = stop
            return {'side': side, 'trigger': trigger, 'entry': entry, 'stop': stop, 'risk_points': actual_risk,
                    'exit': exit_price, 'entry_time': entry_time.isoformat(), 'exit_time': tm.isoformat(),
                    'exit_reason': 'SL', 'r': side * (exit_price - entry) / actual_risk,
                    'ambiguous_entry_bar': ambiguous, 'entry_spread': entry_spread, 'entry_open_gap': gap}
    if entry is None:
        return None
    b = c['close_row']
    exit_price = float(b.open) + (float(b.used_spread) if side == -1 else 0)
    # Existing stop can gap through at the closing quote; stop and close use the same quote.
    reason = 'SL at close gap' if side * (exit_price - stop) <= 0 else 'Cash close'
    return {'side': side, 'trigger': trigger, 'entry': entry, 'stop': stop, 'risk_points': actual_risk,
            'exit': exit_price, 'entry_time': entry_time.isoformat(), 'exit_time': c['close_time'].isoformat(),
            'exit_reason': reason, 'r': side * (exit_price - entry) / actual_risk,
            'ambiguous_entry_bar': ambiguous, 'entry_spread': entry_spread, 'entry_open_gap': gap}


def run(cs, optimistic=False, extra_cost=0.):
    balance = 10000.
    trades, sessions = [], []
    for c in cs:
        if not ('2020-01-01' <= c['date'] < '2023-01-01'):
            continue
        status = c['data_skip']
        if status is None and (c['atr14'] is None or c['rvol'] is None):
            status = 'missing previous-14-session inputs'
        if status is None and c['rvol'] < 2:
            status = 'RVOL below 2.0'
        if status is None and c['opening_close'] == c['opening_open']:
            status = 'doji'
        t = simulate_trade(c, optimistic) if status is None else None
        if status is None and t is None:
            status = 'pending never triggered'
        if t is not None:
            lots = min(500., math.floor((balance * .01 / t['risk_points'] + 1e-12) / .01) * .01)
            if lots < .05:
                status = 'below broker minimum lot'
            else:
                status = 'trade'
                cash_risk = lots * t['risk_points']
                net = lots * (t['side'] * (t['exit'] - t['entry']) - extra_cost)
                t.update({'date': c['date'], 'rvol': c['rvol'], 'atr14': c['atr14'],
                          'opening_volume': c['opening_volume'], 'average_previous_opening_volume': c['avg_previous_volume'],
                          'lots': round(lots, 2), 'starting_balance': balance, 'planned_risk_usd': cash_risk,
                          'net_usd': net, 'net_r': net / cash_risk, 'ending_balance': balance + net,
                          'extra_round_trip_cost_points': extra_cost,
                          'notional_leverage': lots * t['entry'] / balance})
                balance += net
                trades.append(t)
        sessions.append({'date': c['date'], 'status': status, 'balance': balance, 'rvol': c['rvol'],
                         'atr14': c['atr14'], 'opening_volume': c['opening_volume'],
                         'avg_previous_opening_volume': c['avg_previous_volume']})
    return {'trades': trades, 'sessions': sessions, 'summary': metrics(trades, sessions),
            'yearly': {str(y): metrics([t for t in trades if t['date'].startswith(str(y))],
                                      [s for s in sessions if s['date'].startswith(str(y))]) for y in range(2020, 2023)}}


def metrics(ts, ss):
    initial = ts[0]['starting_balance'] if ts else (ss[0]['balance'] if ss else 10000.)
    final = ts[-1]['ending_balance'] if ts else initial
    profits = np.array([t['net_usd'] for t in ts], dtype=float)
    rs = np.array([t['net_r'] for t in ts], dtype=float)
    wins, losses = profits[profits > 1e-8], profits[profits < -1e-8]
    balances = np.array([initial] + [t['ending_balance'] for t in ts])
    dd = 100 * (1 - balances / np.maximum.accumulate(balances))
    daily = np.diff(np.array([initial] + [s['balance'] for s in ss])) / np.array([initial] + [s['balance'] for s in ss[:-1]])
    sw = sl = mw = ml = 0
    for p in profits:
        sw = sw + 1 if p > 1e-8 else 0
        sl = sl + 1 if p < -1e-8 else 0
        mw, ml = max(mw, sw), max(ml, sl)
    return {'trades': len(ts), 'wins': len(wins), 'losses': len(losses),
            'win_rate_pct': 100 * len(wins) / len(ts) if ts else None,
            'profit_factor': float(wins.sum() / abs(losses.sum())) if len(losses) else None,
            'return_pct': 100 * (final / initial - 1), 'initial_balance': initial, 'final_balance': final,
            'net_usd': final - initial, 'net_r': float(rs.sum()), 'mean_r': float(rs.mean()) if len(rs) else None,
            'max_closed_dd_pct': float(dd.max()),
            'sharpe_daily_252': float(daily.mean() / daily.std(ddof=1) * math.sqrt(252)) if len(daily) > 1 and daily.std(ddof=1) > 0 else None,
            'max_win_streak': mw, 'max_loss_streak': ml,
            'mean_win_usd': float(wins.mean()) if len(wins) else None,
            'mean_loss_usd': float(losses.mean()) if len(losses) else None,
            'trades_per_exchange_session': len(ts) / len(ss) if ss else None,
            'exchange_sessions': len(ss), 'session_statuses': dict(Counter(s['status'] for s in ss)),
            'ambiguous_entry_bars': sum(t['ambiguous_entry_bar'] for t in ts),
            'long_trades': sum(t['side'] == 1 for t in ts), 'short_trades': sum(t['side'] == -1 for t in ts),
            'stop_exits': sum(t['exit_reason'].startswith('SL') for t in ts),
            'max_actual_loss_r': float(-rs.min()) if len(rs) else None,
            'max_notional_leverage': max((t['notional_leverage'] for t in ts), default=None)}


def opening_gate_audit(f, cs):
    """Independent audit of the opening gate; excludes no session for later prices/ATR."""
    records = []
    previous = []
    for day, start, end in cash_sessions():
        # Fetch exactly five timestamps. A missing quote-minute is not zero volume.
        expected = pd.date_range(start, periods=5, freq='min')
        bars = f.reindex(expected)
        volume = sum(int(v) for v in bars.tick_volume) if bars.tick_volume.notna().all() else None
        baseline = sum(previous[-14:]) / 14 if len(previous)>=14 and all(v is not None and v>0 for v in previous[-14:]) else None
        rv = volume / baseline if volume is not None and baseline else None
        previous.append(volume)
        if '2020-01-01' <= day < '2023-01-01':
            records.append({'date':day, 'opening_volume':volume, 'previous_14_mean':baseline,
                            'relative_volume':rv, 'passes_2x':rv is not None and rv>=2,
                            'cannot_assess':rv is None})
    # Reconcile against separately prepared daily contexts, not the execution output.
    context_lookup = {c['date']:c for c in cs}
    for row in records:
        c=context_lookup[row['date']]
        assert row['opening_volume']==c['opening_volume']
        assert (row['relative_volume'] is None)==(c['rvol'] is None)
        if row['relative_volume'] is not None:assert abs(row['relative_volume']-c['rvol'])<1e-12
    def counts(rows):
        valid=[r for r in rows if not r['cannot_assess']]
        peak=max(valid,key=lambda r:r['relative_volume']) if valid else None
        return {'scheduled_sessions':len(rows),'assessable':len(valid),'not_assessable':len(rows)-len(valid),
                'passes_2x':sum(r['passes_2x'] for r in rows),
                'max_rvol':peak['relative_volume'] if peak else None,
                'max_rvol_date':peak['date'] if peak else None}
    checks=[]
    for p in sorted(ROOT.glob('MT5-check-*.json')):
        check=json.loads(p.read_text()); rows=check['result']
        for row in rows:
            cached=f.loc[pd.Timestamp(row['time'])]
            assert int(cached.tick_volume)==row['tick_volume']
            for field in ['open','high','low','close']:
                assert abs(float(cached[field])-row[field])<1e-8
        checks.append({'sample':check['date'],'bar_count':len(rows),'price_and_tick_volume_match':True})
    return {'summary':counts(records),'yearly':{str(y):counts([r for r in records if r['date'].startswith(str(y))]) for y in range(2020,2023)},
            'independent_reconciliation_passed':True,'mt5_spot_checks':checks,'records':records}


def report(results):
    primary = results['primary']
    def n(v, dp=2):
        return 'n.a.' if v is None else f'{v:,.{dp}f}'
    fields = [('Period', None), ('Trades', 'trades'), ('Win rate %', 'win_rate_pct'), ('PF', 'profit_factor'),
              ('Return %', 'return_pct'), ('Closed DD %', 'max_closed_dd_pct'), ('Sharpe', 'sharpe_daily_252'),
              ('Net R', 'net_r'), ('Win streak', 'max_win_streak'), ('Loss streak', 'max_loss_streak')]
    rows = []
    for label, m in list(primary['yearly'].items()) + [('2020–2022', primary['summary'])]:
        rows.append('<tr><td>' + label + '</td>' + ''.join('<td>' + n(m[k], 0 if k in ['trades','max_win_streak','max_loss_streak'] else 2) + '</td>' for _, k in fields[1:]) + '</tr>')
    curve = [(i, s['balance']) for i, s in enumerate(primary['sessions'])]
    if curve:
        mn, mx = min(10000, min(v for _, v in curve)), max(10000, max(v for _, v in curve))
        pts = ' '.join(f'{30+940*i/max(1,len(curve)-1):.1f},{260-220*(v-mn)/max(1,mx-mn):.1f}' for i,v in curve)
        graph = f'<svg role="img" aria-label="Shared account closed balance, 2020 to 2022" viewBox="0 0 1000 300"><text x="30" y="22">Closed balance USD: {n(mn,0)}–{n(mx,0)}</text><polyline fill="none" stroke="#66edb5" stroke-width="3" points="{pts}"/><text x="30" y="293">Jan 2020</text><text x="430" y="293">2021</text><text x="860" y="293">Dec 2022</text></svg>'
    else:
        graph = ''
    sens = []
    for label, key in [('Conservative M1 ordering', 'primary'), ('Alternative entry-bar ordering', 'alternative_ordering'), ('Extra 2-point round-trip cost', 'extra_cost')]:
        m = results[key]['summary']
        sens.append(f'<tr><td>{label}</td><td>{m["trades"]}</td><td>{n(m["win_rate_pct"])}</td><td>{n(m["profit_factor"])}</td><td>{n(m["return_pct"])}</td><td>{n(m["max_closed_dd_pct"])}</td></tr>')
    trades = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in [
        t['date'], 'Buy' if t['side']==1 else 'Sell', t['entry_time'], n(t['entry']), n(t['stop']),
        t['exit_time'], n(t['exit']), t['exit_reason'], n(t['rvol']), n(t['atr14']), n(t['lots']),
        n(t['net_r']), n(t['net_usd']), n(t['ending_balance']), 'Yes' if t['ambiguous_entry_bar'] else 'No']) + '</tr>' for t in primary['trades'])
    protocol = results['protocol']
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>US100 Stocks-in-Play ORB 2020–2022</title><style>body{background:#071912;color:#e5f8ef;font:16px system-ui;max-width:1500px;margin:30px auto;padding:20px}p,li{color:#bcd4c8;line-height:1.6}h1{font-size:30px}h2{margin-top:32px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%}th,td{text-align:right;padding:12px;border-bottom:1px solid #315447;white-space:nowrap}th:first-child,td:first-child{text-align:left}a{color:#83ebc5}svg{max-height:350px;width:100%;background:#0c261c}svg text{fill:#bcd4c8;font:16px system-ui}.note{background:#3a2e13;padding:16px;border:1px solid #886b26;border-radius:10px}summary{cursor:pointer;color:#83ebc5}</style>'''
    body += '<h1>US100 five-minute Stocks-in-Play ORB</h1><p>Raw, unoptimised reconstruction. 1 January 2020 through 31 December 2022. $10,000 starting balance; 1% current balance risk per trade, broker lot rounding down.</p>'
    gate=results['opening_gate_audit']
    body += '<h2>Result: the requested 2× opening-volume gate never passed</h2><p class="note">Across '+str(gate['summary']['assessable'])+' assessable exchange sessions, maximum opening RVOL was '+n(gate['summary']['max_rvol'],4)+'×, below the required 2.0×. '+str(gate['summary']['not_assessable'])+' sessions could not be assessed because the current opening window or at least one of its previous 14 opening windows is incomplete. Zero trades is a no-signal result, not evidence of a profitable strategy. Performance of the unassessable sessions is unknown.</p>'
    gate_rows=''.join(f'<tr><td>{y}</td><td>{g["assessable"]}</td><td>{g["not_assessable"]}</td><td>{n(g["max_rvol"],4)}</td><td>{g["max_rvol_date"]}</td><td>{g["passes_2x"]}</td></tr>' for y,g in gate['yearly'].items())
    body += '<div class="scroll"><table><tr><th>Year</th><th>Assessable opening windows</th><th>Unassessable</th><th>Highest RVOL ×</th><th>Peak date</th><th>Passed 2×</th></tr>'+gate_rows+'</table></div>'
    body += '<p>The academic paper uses at least 100% of normal opening volume (RVOL ≥1.0), not 100% higher (RVOL ≥2.0). This test kept the 2.0 threshold in your transcript. Changing it would be a different test; no threshold was optimised. The paper also ranks the top 20 individual stocks, which a single US100 CFD cannot reproduce.</p>'
    body += '<p class="note">This is a conservative one-minute-bar simulation, not a real-tick MT5 backtest or a replication of the paper’s top-20 stock portfolio. US100 CFD tick activity is not traded stock volume. Closed-balance DD is not floating-equity DD. Zero explicit commission is assumed; additional execution cost is tested below.</p>'
    body += '<h2>Skipped-missing-data simulation</h2><p>The hypothetical account stays at $10,000 when all unassessable sessions are skipped. These zero returns and zero closed DD are not a complete three-year execution result or evidence of safety. No PF, win rate or Sharpe can be estimated without trades. The first-stage volume audit above is the meaningful result.</p><div class="scroll"><table><tr>' + ''.join(f'<th>{label}</th>' for label,_ in fields) + '</tr>' + ''.join(rows) + '</table></div>' + graph
    body += '<h2>Execution uncertainty and costs</h2><div class="scroll"><table><tr><th>Case</th><th>Trades</th><th>Win rate %</th><th>PF</th><th>Return %</th><th>Closed DD %</th></tr>' + ''.join(sens) + '</table></div><p>These checks have no trades to act on. They do not validate entry/exit accuracy. Some historical CFD records stop before 16:00 ET or have intraday gaps, so an executable cash-close backtest with a relaxed volume gate would require additional price data or an explicitly changed exit convention. Alternative ordering is a feasibility sensitivity, not a selected setting. The cost case deducts 2 additional index points per completed trade, alongside saved historical spreads.</p>'
    body += '<h2>Data coverage</h2><p>Excluded sessions and filters: ' + html.escape(json.dumps(primary['summary']['session_statuses'])) + '</p><p>Historical price/volume files verified against their original SHA-256 manifest. Missing minute data are not interpolated. Zero spread records use only an earlier observed positive spread. Holidays and early cash-session closures are respected, including Juneteenth from 2022.</p>'
    body += '<details><summary>Exact frozen rules and assumptions</summary><ul>' + ''.join(f'<li>{html.escape(k)}: {html.escape(str(v))}</li>' for k,v in protocol.items()) + '</ul></details>'
    body += '<h2>Trade-by-trade ledger</h2><p>No qualifying trades were generated.</p><div class="scroll"><table><tr>' + ''.join('<th>'+x+'</th>' for x in ['Session','Side','Entry UTC (minute)','Entry','Stop','Exit UTC (minute)','Exit','Reason','RVOL','ATR14','Lots','Net R','Net USD','Balance USD','Ambiguous entry bar']) + '</tr>' + trades + '</table></div>'
    gate_ledger=''.join('<tr><td>'+r['date']+'</td><td>'+n(r['opening_volume'],0)+'</td><td>'+n(r['previous_14_mean'])+'</td><td>'+n(r['relative_volume'],4)+'</td><td>'+('Unassessable' if r['cannot_assess'] else 'Below 2×')+'</td></tr>' for r in gate['records'])
    body += '<details><summary>All 756 opening-window decisions</summary><div class="scroll"><table><tr><th>Session date</th><th>Opening tick volume</th><th>Prior-14 opening average</th><th>RVOL ×</th><th>Status</th></tr>'+gate_ledger+'</table></div></details>'
    body += '<p>No live accounts, production EAs, BATs, portfolios or website were changed. <a href="https://alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content">Original academic paper</a>; <a href="https://ir.theice.com/press/news-details/2019/NYSE-Group-Announces-2020-2021-and-2022-Holiday-and-Early-Closings-Calendar/default.aspx">Cash exchange calendar</a>; <a href="https://www.nasdaq.com/articles/nasdaq-honors-juneteenth-through-our-continued-commitment-to-equality">2022 Juneteenth closure</a>.</p></html>'
    (ROOT / 'Results.html').write_text(body, encoding='utf-8')


def main():
    protocol = json.loads((ROOT / 'PROTOCOL.json').read_text())
    print('Verifying and loading immutable historical M1 files...', flush=True)
    f, provenance = load()
    print(f'Loaded {len(f):,} bid bars; preparing lagged daily inputs...', flush=True)
    cs = contexts(f)
    result = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256': hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest(),
              'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'data': provenance,
              'primary': run(cs), 'alternative_ordering': run(cs, optimistic=True),
              'extra_cost': run(cs, extra_cost=2.)}
    result['opening_gate_audit']=opening_gate_audit(f,cs)
    gate=result['opening_gate_audit']['summary']
    result['outcome']=f'No qualifying 2x opening-volume signal on {gate["assessable"]} assessable sessions; {gate["not_assessable"]} unassessable sessions unknown.'
    save(ROOT / 'RESULTS.json', result)
    report(result)
    print(json.dumps({k: result[k]['summary'] for k in ['primary','alternative_ordering','extra_cost']}, indent=2), flush=True)
    print(json.dumps(result['primary']['yearly'], indent=2), flush=True)
    print(json.dumps({k:v for k,v in result['opening_gate_audit'].items() if k!='records'},indent=2),flush=True)


if __name__ == '__main__':
    main()
