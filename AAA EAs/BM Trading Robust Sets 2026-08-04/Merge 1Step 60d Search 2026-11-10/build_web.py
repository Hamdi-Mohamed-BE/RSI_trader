"""Website evidence caches for the three research listings (EA store app/research_products.py) from the native-web runs of tester_jobs.py.
Standalone native MT5 Model 4, $10k, 1%, 150 ms; each period its own run ending 2026-11-11 exclusive (tester data to 2026-11-10). Active portfolio and installer files
must stay byte-identical. Run from AAA EAs/EA store:  uv run python "<this>" """
import gzip, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; STORE = B.parent / 'EA store'; CACHE = STORE / 'data/evidence-cache/v1'
sys.path.insert(0, str(B.parent / 'Calyx Research Pipeline'))
import buy_hold  # noqa: E402
SOURCE = 'native-mt5-research-listings-20261110'
EAS = {'overnight-bias-orb': ('Overnight Bias ORB', 'USTEC'), 'vault-break': ('Vault Break', 'USTEC'), 'gold-band-wave': ('Gold Band Wave', 'XAUUSD')}
PERIODS = {'6m': '2026-05-11', '1y': '2025-11-11', '3y': '2023-11-11', '5y': '2021-11-11'}
END = '2026-11-11'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, d):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(d, indent=2, allow_nan=False), encoding='utf-8')


def streaks(xs):
    best = {True: 0, False: 0}; cur = 0; last = None
    for w in xs:
        cur = cur + 1 if w == last else 1; last = w; best[w] = max(best[w], cur)
    return best[True], best[False]


def main():
    active = [B / '_Auto Deploy/Install-BMTradingPortfolio.ps1'] + list((CACHE / 'portfolio').rglob('*.json'))
    before = {str(p): sha(p) for p in active}; plan = {(r['key'], r['window']): r for r in json.loads((H / 'PLAN-web.json').read_text(encoding='utf-8'))}; release = []
    for slug, (label, sym) in EAS.items():
        for period, start in PERIODS.items():
            d = H / 'native-web' / f'nw-{sym}-{slug}-{period}'; run = json.loads((d / 'run.json').read_text(encoding='utf-8'))
            assert run['ok'] and run['start'] == start.replace('-', '.') and run['end_exclusive'] == END.replace('-', '.') and not run['input_mismatches'], (slug, period)
            T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); m = run['metrics']; p = plan[(slug, period)]
            bal = 10000.0; trades = []; series = [dict(time=start + 'T00:00:00+00:00', balance=bal)]
            for i, t in enumerate(T, 1):
                r = t['net_profit'] / (0.01 * bal); bal += t['net_profit']
                trades.append(dict(t, number=i, ea=label, open_time=t['open_time'] + '+00:00', close_time=t['close_time'] + '+00:00', fees=0.0,
                                   price_move=(t['close_price'] - t['open_price']) * (1 if t['side'] == 'Long' else -1), price_move_unit='points', pip_size=1.0,
                                   estimated_r=round(r, 4), estimated_risk_cash=None, configured_risk_pct=1.0, r_is_estimate=True,
                                   cache_slug=slug, cache_mode='standard', cache_period=period))
                series.append(dict(time=t['close_time'] + '+00:00', balance=round(bal, 2)))
            series.append(dict(time=END + 'T00:00:00+00:00', balance=round(bal, 2)))
            assert abs(bal - m['final_balance']) < 0.05, (slug, period, bal, m['final_balance'])
            gw = sum(t['net_profit'] for t in T if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in T if t['net_profit'] < 0)
            pk = 10000.0; cdd = 0.0; b2 = 10000.0
            for t in T:
                b2 += t['net_profit']; pk = max(pk, b2); cdd = max(cdd, (pk - b2) / pk * 100)
            ws, ls = streaks([t['net_profit'] > 0 for t in T])
            rep = d / f'{d.name}.htm.gz'; eqdd = buy_hold.relative_equity_dd(rep)
            stats = dict(initial_balance=10000.0, final_balance=round(bal, 2), net_profit=round(bal - 10000, 2), return_pct=round((bal - 10000) / 100, 4),
                         profit_factor=round(gw / gl, 4) if gl else None, win_rate_pct=round(100 * sum(t['net_profit'] > 0 for t in T) / len(T), 4) if T else 0.0,
                         max_drawdown_pct=eqdd, max_equity_drawdown_pct=eqdd, max_closed_balance_drawdown_pct=round(cdd, 4), mt5_maximal_drawdown_pct=m['max_drawdown_pct'],
                         trades=len(T), wins=sum(t['net_profit'] > 0 for t in T), losses=sum(t['net_profit'] < 0 for t in T), sharpe_ratio=m.get('sharpe_ratio'), recovery_factor=m.get('recovery_factor'),
                         commission=round(sum(t['commission'] for t in T), 2), swap=round(sum(t['swap'] for t in T), 2), total_costs=round(sum(t['total_costs'] for t in T), 2),
                         max_win_streak=ws, max_loss_streak=ls, expected_payoff=m.get('expected_payoff'), planned_risk_pct=1.0, **{'from': start, 'to': '2026-11-10', 'end_exclusive': END})
            out = CACHE / 'products' / slug / 'standard'; save(out / f'{period}.trades.json', trades)
            arch = CACHE / 'source-runs' / slug / 'standard'; arch.mkdir(parents=True, exist_ok=True); (arch / f'{period}.htm.gz').write_bytes(rep.read_bytes()); save(arch / f'{period}.meta.json', run)
            fp = dict(slug=slug, mode='standard', expert_sha256=p['ex5_sha'], settings_sha256=run['set_sha256'], production_native_report_sha256=run['report_sha256'],
                      cached_trades_sha256=sha(out / f'{period}.trades.json'), archived_report_sha256=sha(arch / f'{period}.htm.gz'))
            name = {'6m': 'Last 6 months', '1y': 'Last 1 year', '3y': 'Last 3 years', '5y': 'Last 5 years'}[period]
            notice = (f"Standalone Exness {sym} native MT5 Model 4, {start} to {END} exclusive. $10,000 start, 1% risk per trade (lots round up to the broker step), 150 ms execution delay, "
                      f"recorded commission and swap. {m['history_quality']}. Closed-balance curve; maximum drawdown is the native relative equity drawdown including floating P/L. "
                      "Raw research rules, not optimised; not an installer or website-portfolio member.")
            payload = dict(label=label, period=f'{start} to 2026-11-10 (end exclusive {END})', period_key=period, mode='standard', currency='USD', series=series, stats=stats,
                           available_from=start, available_to='2026-11-10', end_exclusive=END, evidence_label=f'Precomputed {name} - raw research rules', evidence_status='Research evidence',
                           history_quality=m['history_quality'], notice=notice, source=SOURCE, source_fingerprint=fp, cached_trade_count=len(trades),
                           trade_coverage_from=trades[0]['open_time'] if trades else None, trade_coverage_to=trades[-1]['close_time'] if trades else None,
                           generated_at=datetime.now(timezone.utc).isoformat(), website_only=True, not_in_active_portfolio=True)
            save(out / f'{period}.json', payload); release.append(dict(slug=slug, period=period, stats=stats, source_fingerprint=fp))
            print(slug, period, 'n', len(T), 'ret', stats['return_pct'], 'PF', stats['profit_factor'], 'eqDD', eqdd, flush=True)
    assert {str(p): sha(p) for p in active} == before, 'an active portfolio/installer artifact changed'
    save(H / 'WEBSITE-RELEASE.json', dict(source=SOURCE, products=release))
    man = json.loads((CACHE / 'manifest.json').read_text(encoding='utf-8-sig'))
    man['website_only_research_listings_20261110'] = dict(source=SOURCE, slugs=sorted(EAS), periods=list(PERIODS), end_exclusive=END, native_runs=len(release), active_portfolio_changed=False)
    save(CACHE / 'manifest.json', man); print('WEB DONE', flush=True)


if __name__ == '__main__':
    main()
