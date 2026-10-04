"""Publish four source-bound recent caches; do not change any active allocation."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json
import pandas as pd
from analyse import R, pairs, metrics, report_values, number, clean

STORE = R.parents[1]/'EA store'
CACHE = STORE/'data/evidence-cache/v1'
SOURCE = 'native-mt5-hourly-profiles-20261003'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, allow_nan=False), encoding='utf-8')

def main():
    # Record untouched active artifacts separately from the documentation edited later.
    active = [R.parent/'_Auto Deploy/Install-BMTradingPortfolio.ps1']
    active += list((CACHE/'portfolio').rglob('*.json'))
    before = {str(p): sha(p) for p in active}
    release = []
    for asset in ('US30', 'US100'):
        slug = asset.lower()+'-hourly-profiles'
        for period, start in [('1y','2025-10-03'), ('6m','2026-04-03')]:
            folder = R/'native'/f'hourprof-20261003-{asset}-{period}-baseline'
            receipt = json.loads((folder/'RESULT.json').read_text())
            assert receipt['from'].replace('.','-') == start and receipt['to_exclusive'] == '2026.10.03'
            assert receipt['source_sha256'] == sha(R/'CalyxHourlyProfiles.mq5')
            assert receipt['binary_sha256'] == sha(R/'CalyxHourlyProfiles.ex5')
            assert receipt['set_sha256'] == sha(folder/'inputs.set') and not receipt['account_failure']
            df, native = pairs(folder, receipt)
            result = metrics(df, start, '2026-10-03')
            (folder/'positions.json.gz').write_bytes(gzip.compress(json.dumps(clean(df.to_dict('records'))).encode(),mtime=0))
            audit = pd.read_csv(folder/'audit.csv.gz').iloc[0]
            fills = pd.read_csv(folder/'fills.csv.gz')
            fills = fills[fills.retcode.isin([10009,10010])]
            zero = float(((fills.ask-fills.bid).abs()<1e-8).mean()*100)
            trades = []
            for i, row in enumerate(df.to_dict('records'), 1):
                trades.append(dict(number=i, ea=f'{asset} Hourly Profiles', symbol=receipt['symbol'],
                    side='Long' if row['side']=='buy' else 'Short', volume=row['lots'],
                    open_time=row['entry_utc'], close_time=row['exit_utc'], open_price=row['entry_price'],
                    close_price=row['exit_price'], gross_profit=row['profit'], commission=row['commission'],
                    swap=row['swap'], fees=row['fees'], total_costs=row['commission']+row['swap']+row['fees'],
                    net_profit=row['net_cash'], result='Win' if row['net_cash']>0 else 'Loss' if row['net_cash']<0 else 'Flat',
                    source='Native MT5 deals, reconciled by position; recorded costs',
                    entry_comment=f"Frozen NY {row['hour']:02d}:00 {row['side']}", exit_comment='Timed exit (actual broker fill)',
                    price_move=(row['exit_price']-row['entry_price'])*(1 if row['side']=='buy' else -1),
                    price_move_unit='points', pip_size=1.0, estimated_r=None, estimated_risk_cash=None,
                    configured_risk_pct=None, r_is_estimate=False, stop_loss=None, take_profit=None,
                    hold_minutes_actual=row['hold_minutes_actual'], late_exit_seconds=row['late_exit_seconds'],
                    cache_slug=slug, cache_mode='standard', cache_period=period))
            out = CACHE/'products'/slug/'standard'
            save(out/f'{period}.trades.json', trades)
            archive = CACHE/'source-runs'/slug/'standard'
            archive.mkdir(parents=True, exist_ok=True)
            for filename, suffix in [('report.htm.gz','.htm.gz'),('deals.csv.gz','.deals.csv.gz'),('audit.csv.gz','.audit.csv.gz')]:
                (archive/(period+suffix)).write_bytes((folder/filename).read_bytes())
            save(archive/f'{period}.meta.json', receipt)
            raw_report = gzip.decompress((folder/'report.htm.gz').read_bytes())
            assert hashlib.sha256(raw_report).hexdigest() == receipt['report_sha256']
            balance = 10000.0
            series = [dict(time=start+'T00:00:00+00:00', balance=balance)]
            for row in trades:
                balance += row['net_profit']
                series.append(dict(time=row['close_time'], balance=round(balance,2)))
            series.append(dict(time='2026-10-03T00:00:00+00:00', balance=round(balance,2)))
            assert abs(balance - 10000-result['net_cash']) < 1e-6
            quality = str(native['History Quality'])
            label = 'Last 1 year' if period=='1y' else 'Last 6 months'
            notice = (f"Standalone Exness {receipt['symbol']} native MT5 Model 4, {start} to 2026-10-03 exclusive. "
                f"$10,000 start, one fixed CFD lot, 150ms execution delay, recorded commission and swap. {quality}. "
                f"Zero-spread entry quotes: {zero:.1f}%; live transaction costs are not validated. "
                "Closed-balance curve attributes all position costs at its closing time; maximum drawdown includes native tickwise floating equity. "
                "Delayed and weekend exits are included. No SL, TP or percentage-risk cap. "
                "Hours were selected on the latest year; both recent windows overlap that selection. Failed long-history gate: research only, not an active BAT or portfolio allocation.")
            dd_cash = number(native['Equity Drawdown Maximal'].split('(')[0].strip())
            stats = dict(initial_balance=10000., final_balance=balance, net_profit=result['net_cash'],
                return_pct=result['return_pct'], profit_factor=result['pf'], win_rate_pct=result['win_rate_pct'],
                max_drawdown_pct=float(audit['max_equity_dd_pct']), max_drawdown_cash=dd_cash,
                max_equity_drawdown_pct=float(audit['max_equity_dd_pct']),
                max_closed_balance_drawdown_pct=result['closed_balance_dd_pct'],
                trades=result['trades'], wins=result['wins'], losses=result['losses'],
                sharpe_ratio=number(native['Sharpe Ratio']), recovery_factor=number(native['Recovery Factor']),
                gross_profit_before_costs=float(df.profit.sum()), commission=result['commission'], swap=result['swap'],
                total_costs=result['commission']+result['swap']+result['fees'],
                max_win_streak=result['max_win_streak'], max_loss_streak=result['max_loss_streak'],
                expected_payoff=result['expected_payoff'], late_positions=result['late_positions'],
                zero_spread_entry_pct=zero, fixed_lots=1.0, planned_risk_pct=None,
                **{'from':start,'to':'2026-10-02','end_exclusive':'2026-10-03'})
            fingerprint = dict(slug=slug,mode='standard',source_sha256=receipt['source_sha256'],
                expert_sha256=receipt['binary_sha256'],settings_sha256=receipt['set_sha256'],
                production_native_report_sha256=receipt['report_sha256'],
                cached_trades_sha256=sha(out/f'{period}.trades.json'),
                archived_report_sha256=sha(archive/f'{period}.htm.gz'),
                archived_deals_sha256=sha(archive/f'{period}.deals.csv.gz'),
                selection_sha256=sha(R/'SELECTED-HOURS.json'))
            payload = dict(label=f'{asset} Hourly Profiles', period=f'{start} to 2026-10-02 (end exclusive 2026-10-03)',
                period_key=period,mode='standard',currency='USD',series=series,stats=stats,
                available_from=start,available_to='2026-10-02',end_exclusive='2026-10-03',
                evidence_label=f'Precomputed {label} — frozen hourly research profile',evidence_status='Research evidence',
                history_quality=quality,notice=notice,source=SOURCE,source_fingerprint=fingerprint,
                cached_trade_count=len(trades),trade_coverage_from=trades[0]['open_time'],
                trade_coverage_to=trades[-1]['close_time'],generated_at=datetime.now(timezone.utc).isoformat(),
                website_only=True,not_in_active_portfolio=True)
            save(out/f'{period}.json',payload)
            release.append(dict(slug=slug,asset=asset,period=period,stats=stats,source_fingerprint=fingerprint))
            print(asset,period,'N',len(trades),'PF',round(stats['profit_factor'],3),'WR',round(stats['win_rate_pct'],2),
                  'return',round(stats['return_pct'],2),'DD',round(stats['max_drawdown_pct'],2),flush=True)
    after = {str(p):sha(p) for p in active}
    assert before == after, 'An active portfolio/installer artifact unexpectedly changed'
    save(R/'WEBSITE-RELEASE.json',dict(source=SOURCE,products=release,unchanged_active_artifacts=after))
    manifest = json.loads((CACHE/'manifest.json').read_text(encoding='utf-8-sig'))
    manifest['website_only_hourly_research'] = dict(source=SOURCE,slugs=sorted({r['slug'] for r in release}),
        periods=['6m','1y'],end_exclusive='2026-10-03',native_runs=4,active_portfolio_changed=False)
    save(CACHE/'manifest.json',manifest)

if __name__=='__main__': main()
