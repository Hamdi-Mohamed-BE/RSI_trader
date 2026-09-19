"""Independently verify saved study artifacts without launching MT5."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    rows = json.loads((ROOT / 'results.json').read_text())
    assert len(rows) == 21
    checked = []
    for row in rows:
        directory = ROOT / 'cases' / row['case']
        trades = json.loads((directory / 'trades.json').read_text())
        months = json.loads((directory / 'months.json').read_text())
        days = list(csv.DictReader((directory / 'daily-equity.csv').open(), delimiter=';'))
        assert len(trades) == row['trades']
        assert abs(sum(t['net_profit'] for t in trades) - row['net_profit']) < .03
        assert abs(sum(m['net_profit'] for m in months) - row['net_profit']) < .03
        assert abs(10000 + row['net_profit'] - row['final_balance']) < .02
        assert len({t['entry_day_prague'] for t in trades}) == row['entry_days']
        assert hashlib.sha256(Path(row['source_set']).read_bytes()).hexdigest() == row['source_set_sha256']
        assert hashlib.sha256(Path(row['report']).read_bytes()).hexdigest() == row['report_sha256']
        assert row['config']['InpRiskPercent'] == '1.0'
        assert row['config']['InpAdaptivePortfolioControls'] == 'false'
        assert row['config']['InpTesterServerUTCOffsetHours'] == '0'
        for day in days:
            assert abs(max(0, float(day['start_balance'])-float(day['min_equity']))-float(day['daily_loss_usd'])) < .021
        worst_day = max(float(d['daily_loss_usd']) for d in days)
        min_equity = min(float(d['min_equity']) for d in days)
        assert abs(worst_day-float(row['audit']['worst_daily_loss'])) < .02
        assert abs(min_equity-float(row['audit']['min_equity'])) < .02
        daily_breaches = [d['prague_day'] for d in days if float(d['daily_loss_usd']) > 500.005]
        total_breaches = [d['prague_day'] for d in days if float(d['min_equity']) < 8999.995]
        assert bool(daily_breaches or total_breaches) == bool(int(row['audit']['first_breach']))
        native_max_margin = max(float(d['max_margin_usd']) for d in days)
        known_gap_trades = [t for t in trades if t['entry_time'][:10] in ('2026-09-14', '2026-09-15')]
        checked.append(dict(case=row['case'],net_reconciled=True,source_unchanged=True,
                            daily_equity_reconciled=True,daily_breach_days=daily_breaches,
                            total_breach_days=total_breaches,max_native_margin_usd=native_max_margin,
                            entries_on_known_full_tick_gap_days=len(known_gap_trades),
                            net_on_known_full_tick_gap_days=round(sum(t['net_profit'] for t in known_gap_trades),2)))
    for slug in {r['slug'] for r in rows}:
        group = [r for r in rows if r['slug'] == slug]
        assert len(group) == 3
        controls = [{k:v for k,v in r['config'].items() if k not in ('InpRewardRisk','InpTrialAuditCase')} for r in group]
        assert controls[0] == controls[1] == controls[2], 'Unexpected non-RR parameter change'
    (ROOT / 'verification.json').write_text(json.dumps(checked, indent=2), encoding='utf-8')
    print(f'PASS: {len(checked)} native results reconcile; original sets unchanged; within-EA controls identical.')


if __name__ == '__main__':
    main()
