"""Immutable native raw Gold VA evidence; no terminal access or strategy fitting."""
from __future__ import annotations
import json,hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from .catalog import PACKAGE_ROOT
from .trade_metrics import enrich_trades

SLUG = 'gold-overnight-value-area'
ROOT = PACKAGE_ROOT / 'Gold Overnight Value Area Pipeline 2026-09-19'
NOTICE = ('Independent native MT5 raw baseline, Exness gold, 1% equity target, 150 ms execution delay. '
          'Commission and swap included; lots round UP and can exceed 1%. Broker tick volume is not exchange volume. '
          'Real ticks start January 2026; older coverage uses generated ticks. '
          'The June 20, 2025 New York session is unavailable. Not an FTMO account simulation or the optimized candidate.')

def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def evidence(period: str):
    return read(ROOT / 'raw-results.json')[period]

def catalog_evidence():
    r = evidence('1y')
    return dict(label='Raw Gold Overnight Value Area — native MT5', period='2025-09-19 to 2026-09-18',
                return_pct=r['return_pct'], profit_factor=r['profit_factor'], drawdown_pct=r['max_drawdown_pct'],
                win_rate_pct=r['win_rate_pct'], trades=r['trades'], max_win_streak=r['max_win_streak'],
                max_loss_streak=r['max_loss_streak'], history_quality=r['history_quality'], source_note=NOTICE,
                status='Experimental', caution='High win rate, variable sub-1R targets; weak five-year expectancy.')

def payload(period: str):
    production=PACKAGE_ROOT/'Gold Overnight Value Area EA'
    verified=read(production/'parity.json')
    source=production/'EA/Gold Overnight Value Area EA.mq5'
    assert verified['passed'] and hashlib.sha256(source.read_bytes()).hexdigest()==verified['source_sha256'], 'Gold source changed since native parity'
    assert hashlib.sha256(source.with_suffix('.ex5').read_bytes()).hexdigest()==verified['binary_sha256'], 'Gold executable changed since native parity'
    r = evidence(period)
    folder = ROOT / 'native' / r['case']
    report=folder/(r['case']+'.htm')
    assert hashlib.sha256(report.read_bytes()).hexdigest()==r['report_sha256'], 'Gold native report identity mismatch'
    run = read(folder / 'run.json')
    start = run['start'].replace('.', '-')
    end_exclusive = run['end_exclusive'].replace('.', '-')
    from datetime import timedelta
    end = (date.fromisoformat(end_exclusive) - timedelta(days=1)).isoformat()
    rows = read(folder / 'trades.json')
    # Website's historical timestamps are UTC without an offset. Normalize first.
    for number, row in enumerate(rows, 1):
        for key in ('open_time', 'close_time'):
            t = datetime.fromisoformat(row[key])
            row[key] = t.astimezone(timezone.utc).replace(tzinfo=None).isoformat() if t.tzinfo else t.isoformat()
        row.update(number=number, ea='Gold Overnight Value Area', cache_slug=SLUG, cache_mode='standard', cache_period=period)
    rows = enrich_trades(rows, SLUG)
    for row in rows:
        row.update(estimated_risk_cash=row['initial_risk_usd'], estimated_r=row['net_r'], r_is_estimate=False)
    assert len(rows) == r['trades']
    assert abs(sum(t['net_profit'] for t in rows) - r['net_profit']) < .03
    balance = 10000.0
    series = [dict(time=start+'T00:00:00', balance=balance)]
    for row in sorted(rows, key=lambda t: t['close_time']):
        balance += row['net_profit']
        series.append(dict(time=row['close_time'], balance=round(balance, 2)))
    stats = {k:r[k] for k in ('initial_balance','final_balance','net_profit','return_pct','profit_factor',
             'win_rate_pct','max_drawdown_pct','trades','commission','swap','max_win_streak','max_loss_streak')}
    stats.update({'from':start, 'to':end, 'total_costs':r['commission']+r['swap'],
                  'native_equity_drawdown_pct':r['max_drawdown_pct']})
    return dict(label='Gold Overnight Value Area',period=f'{start} to {end}',period_key=period,mode='standard',
                currency='USD',series=series,stats=stats,available_from=start,available_to=end,
                end_exclusive=end_exclusive,cached_trade_count=len(rows),trade_coverage_from=rows[0]['open_time'],
                trade_coverage_to=rows[-1]['close_time'],notice=NOTICE,source='audited-raw-native-mt5',
                source_report_sha256=r['report_sha256'],history_quality=r['history_quality'],
                generated_at=datetime.now(timezone.utc).isoformat()), rows
