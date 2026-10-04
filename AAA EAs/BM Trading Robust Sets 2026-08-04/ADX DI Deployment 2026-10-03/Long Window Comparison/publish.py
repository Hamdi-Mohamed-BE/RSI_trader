"""Publish only completed, frozen native long-window results and their baseline."""
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
import gzip, hashlib, json, os, shutil, sys

R=Path(__file__).resolve().parent
D=R.parent
B=D.parent
STORE=B.parent/'EA store'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path[:0]=[str(STORE),str(STORE/'tools')]
import precompute_evidence_cache as P
from app.catalog import get_product
from app.trade_metrics import enrich_trades
from app.evidence_cache import product_cache_path,product_trades_path,write_json,CACHE_ROOT


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def backup(p):
    target=D/'before'/p.relative_to(STORE)
    if p.is_file() and not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)


def payload(slug,result,start,end,selection,config):
    folder=R/'native'/result['tag']
    manifest=load(folder/'manifest.json')
    frozen=next(c for c in config['cases'] if c['tag']+'-ORIGINAL'==result['tag'])
    assert manifest['inputs']==frozen['inputs'] and manifest['build']['binary_sha']==frozen['binary_sha']
    assert sha(Path(frozen['binary']))==frozen['binary_sha']
    assert manifest['start']==result['start'] and manifest['end']==result['end_exclusive']
    assert manifest['protocol_sha']==config['protocol_sha']==sha(R/'PROTOCOL.txt')
    report=gzip.decompress((folder/'report.htm.gz').read_bytes())
    assert hashlib.sha256(report).hexdigest()==result['report_sha']
    rows=enrich_trades(json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes())),slug)
    s=result['stats']
    assert len(rows)==s['trades'] and abs(sum(r['net_profit'] for r in rows)-s['net'])<.01
    for n,r in enumerate(rows,1):
        r.update(number=n,cache_slug=slug,cache_mode='standard',cache_period=result['period'],source='Frozen native MT5 production EA, recorded costs; no new optimization')
    stats,series=P.portfolio_metrics(rows,start,end)
    stats.update(return_pct=s['return_pct'],profit_factor=s['pf'],win_rate_pct=s['win_pct'],max_drawdown_pct=s['equity_dd_pct'],
                 max_equity_drawdown_pct=s['equity_dd_pct'],max_closed_balance_drawdown_pct=s['closed_dd_pct'],
                 sharpe_annualized=s['sharpe'],sharpe_ratio=None,max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],
                 trades_per_month=s['trades_month'],trades_per_trading_day=s['trades_weekday'],to=str(end-timedelta(days=1)),end_exclusive=str(end))
    series[-1]['time']=end.isoformat()+'T00:00:00'
    product=get_product(slug)
    fp=P.source_fingerprint(product,'standard',start,end)
    assert fp['expert_sha256']==frozen['binary_sha']
    fp.update(production_native_report_sha256=result['report_sha'],native_ledger_sha256=sha(folder/'trades.json.gz'),
              frozen_protocol_sha256=config['protocol_sha'],frozen_case=result['tag'],configuration_release=selection['version'])
    note=f"Standalone Exness native MT5 Model 4, {start} to {end} exclusive; $10,000 start, 1% equity-risk target, 150ms delay and recorded costs. {s['history_quality']}; missing broker ticks are generated. Upward/minimum-lot rounding may exceed target risk. Native maximum equity drawdown includes floating P/L; plotted balance excludes it. Fixed filters selected in the recent year, no further tuning; overlapping retrospective window is not independent validation or a guarded FTMO simulation."
    if slug=='xau-trend-progression':note+=' Provisional selection: only 29 recent-year trades.'
    if slug=='xau-rsi-vwap':note+=' RSI VWAP source, binary, inputs and strategy remain unchanged.'
    p=dict(label=product.label,period=f'{start} to {end-timedelta(days=1)}',period_key=result['period'],mode='standard',currency='USD',
           series=series,stats=stats,available_from=str(start),available_to=str(end-timedelta(days=1)),end_exclusive=str(end),
           evidence_label='Frozen ADX/DI longer-window comparison' if slug!='xau-rsi-vwap' else 'Unchanged RSI VWAP reference',
           evidence_status='Provisional research' if slug=='xau-trend-progression' else 'Retrospective research evidence',
           history_quality=s['history_quality'],notice=note,source='native-mt5-adxdi-long-20261003',source_fingerprint=fp,
           cached_trade_count=len(rows),trade_coverage_from=min(t['open_time'] for t in rows),trade_coverage_to=max(t['close_time'] for t in rows),
           configuration_release=selection['version'],generated_at=datetime.now(timezone.utc).isoformat())
    return p,rows,report,fp


def main():
    results=load(R/'SUMMARY.json');config=load(R/'run-config.json');selection=load(D/'SELECTION.json')
    assert len(results)==len(config['cases'])==18 and not config['optimization']
    for result in results:
        frozen=next(c for c in config['cases'] if c['tag']+'-ORIGINAL'==result['tag'])
        folder=R/'native'/result['tag'];m=load(folder/'manifest.json')
        assert m['inputs']==frozen['inputs'] and m['build']['binary_sha']==frozen['binary_sha']
        assert m['protocol_sha']==config['protocol_sha']==sha(R/'PROTOCOL.txt')
        assert m['start']==result['start'] and m['end']==result['end_exclusive']
        assert hashlib.sha256(gzip.decompress((folder/'report.htm.gz').read_bytes())).hexdigest()==result['report_sha']
    bykey={p['key']:slug for slug,p in selection['profiles'].items()};bykey['rsi']='xau-rsi-vwap'
    checks=[]
    for result in results:
        if result['arm']=='baseline':continue
        slug=bykey[result['key']]
        start=date.fromisoformat(result['start'].replace('.','-'));end=date.fromisoformat(result['end_exclusive'].replace('.','-'))
        p,rows,report,fp=payload(slug,result,start,end,selection,config)
        old=next((r for r in results if r['key']==result['key'] and r['period']==result['period'] and r['arm']=='baseline'),None)
        if old:
            # Baseline uses the historical binary, not today's product fingerprint.
            baseline_rows=json.loads(gzip.decompress((R/'native'/old['tag']/'trades.json.gz').read_bytes()))
            _,baseline_series=P.portfolio_metrics(baseline_rows,start,end)
            baseline_series[-1]['time']=end.isoformat()+'T00:00:00'
            p['baseline_comparison']=dict(label='Exact prior one-year study preset, no new ADX/DI filter',stats=old['stats'],series=baseline_series,case=old['tag'],report_sha=old['report_sha'])
        paths=[product_cache_path(slug,'standard',result['period']),product_trades_path(slug,'standard',result['period']),*P.source_paths(get_product(slug),'standard',result['period'])]
        for path in paths:backup(path)
        write_json(paths[1],rows);fp['cached_trades_sha256']=sha(paths[1]);write_json(paths[0],p)
        paths[2].parent.mkdir(parents=True,exist_ok=True);paths[2].write_bytes(report);write_json(paths[3],fp)
        checks.append(dict(slug=slug,period=result['period'],trades=len(rows),expert_sha=fp['expert_sha256'],native_report_sha=result['report_sha']))
        print('PUBLISHED',slug,result['period'],len(rows),flush=True)
    manifest_path=CACHE_ROOT/'manifest.json';backup(manifest_path);manifest=load(manifest_path)
    manifest['admission_release']['current_filtered_periods']=['1y','3y','5y']
    write_json(manifest_path,manifest)
    write_json(R/'WEBSITE_PUBLICATION.json',dict(checks=checks,remaining_archived=['6m'],old_portfolio_forecasts_revalidated=False,live_mt5_changed=False))
    publication=load(D/'WEBSITE_PUBLICATION.json')
    publication.update(current_periods=['1y','3y','5y'],other_periods='6m remains archived',long_window_publication='Long Window Comparison/WEBSITE_PUBLICATION.json')
    write_json(D/'WEBSITE_PUBLICATION.json',publication)


if __name__=='__main__':main()
