"""Publish the exact tested final presets; no MT5 or new parameter search."""
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import gzip,hashlib,json,os,shutil,sys

R=Path(__file__).resolve().parent;B=R.parent
OLD=B/'ADX DI Deployment 2026-10-03';LONG=OLD/'Long Window Comparison'
STUDY=B/'ADX DI Five Bot Review 2026-10-03';STORE=B.parent/'EA store'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path[:0]=[str(STORE),str(STORE/'tools')]
import precompute_evidence_cache as P
from app.catalog import get_product,get_catalog
from app.trade_metrics import enrich_trades
from app.evidence_cache import product_cache_path,product_trades_path,write_json,CACHE_ROOT

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def backup(p):
    target=R/'before'/p.relative_to(STORE)
    if p.is_file() and not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)

def main():
    selection=load(R/'SELECTION.json');long=load(LONG/'SUMMARY.json')
    evidence={};checks=[]
    for slug,profile in selection['profiles'].items():
        assert sha(B/profile['expert'])==profile['expert_sha']
        for period in ('1y','3y','5y'):
            if period=='1y':
                folder=(OLD if profile['filter_status']=='kept' else STUDY)/'native'/(profile['key']+'-ORIGINAL')
                result=load(folder/'result.json')
                start=date(2025,10,2)
            else:
                arm='filtered' if profile['filter_status']=='kept' else 'baseline'
                result=next(r for r in long if r['key']==profile['key'] and r['period']==period and r['arm']==arm)
                folder=LONG/'native'/result['tag'];start=date.fromisoformat(result['start'].replace('.','-'))
            end=date(2026,10,2);m=load(folder/'manifest.json');s=result['stats']
            assert m['inputs']==profile['inputs']
            assert m['build']['original_sha']==profile['expert_sha']
            assert m['start']==str(start).replace('-','.') and m['end']==str(end).replace('-','.')
            report=gzip.decompress((folder/'report.htm.gz').read_bytes())
            assert hashlib.sha256(report).hexdigest()==result['report_sha']
            rows=enrich_trades(json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes())),slug)
            assert len(rows)==s['trades'] and abs(sum(r['net_profit'] for r in rows)-s['net'])<.01
            for n,row in enumerate(rows,1):
                row.update(number=n,cache_slug=slug,cache_mode='standard',cache_period=period,
                           source='Exact native-tested final preset, recorded costs; no new optimization')
            stats,series=P.portfolio_metrics(rows,start,end)
            stats.update(return_pct=s['return_pct'],profit_factor=s['pf'],win_rate_pct=s['win_pct'],
                         max_drawdown_pct=s['equity_dd_pct'],max_equity_drawdown_pct=s['equity_dd_pct'],
                         max_closed_balance_drawdown_pct=s['closed_dd_pct'],sharpe_annualized=s['sharpe'],sharpe_ratio=None,
                         max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],
                         trades_per_month=s['trades_month'],trades_per_trading_day=s['trades_weekday'],
                         to=str(end-timedelta(days=1)),end_exclusive=str(end))
            series[-1]['time']=end.isoformat()+'T00:00:00'
            product=get_product(slug);fp=P.source_fingerprint(product,'standard',start,end)
            assert fp['expert_sha256']==profile['expert_sha'] and fp['settings_sha256']==profile['settings_sha']
            fp.update(production_native_report_sha256=result['report_sha'],native_ledger_sha256=sha(folder/'trades.json.gz'),
                      frozen_protocol_sha256=m['protocol_sha'],frozen_case=folder.name,
                      configuration_release=selection['version'],selection_sha256=sha(R/'SELECTION.json'))
            note=f"Standalone Exness native MT5 Model 4, {start} to {end} exclusive; $10,000 start, 1% equity-risk target, 150ms delay and recorded costs. {s['history_quality']}; missing broker ticks generated. Upward/minimum-lot rounding can exceed target risk. Native equity drawdown includes floating P/L; curve is closed balance. Final user selection: "
            note+=('USDJPY keeps ADX >=20 + DI.' if profile['filter_status']=='kept' else 'Added ADX/DI filter removed; exact baseline restored, existing unrelated filters and exits retained.')
            note+=' Overlapping retrospective windows are not independent validation or a guarded FTMO simulation.'
            payload=dict(label=product.label,period=f'{start} to {end-timedelta(days=1)}',period_key=period,mode='standard',
                         currency='USD',series=series,stats=stats,available_from=str(start),available_to=str(end-timedelta(days=1)),
                         end_exclusive=str(end),evidence_label='Final selection — '+('ADX20 + DI' if profile['filter_status']=='kept' else 'baseline restored'),
                         evidence_status='Retrospective research evidence',history_quality=s['history_quality'],notice=note,
                         source='native-mt5-adxdi-final-20261003',source_fingerprint=fp,cached_trade_count=len(rows),
                         trade_coverage_from=min(r['open_time'] for r in rows),trade_coverage_to=max(r['close_time'] for r in rows),
                         configuration_release=selection['version'],generated_at=datetime.now(timezone.utc).isoformat())
            paths=[product_cache_path(slug,'standard',period),product_trades_path(slug,'standard',period),*P.source_paths(product,'standard',period)]
            for path in paths:backup(path)
            write_json(paths[1],rows);fp['cached_trades_sha256']=sha(paths[1]);write_json(paths[0],payload)
            paths[2].parent.mkdir(parents=True,exist_ok=True);paths[2].write_bytes(report);write_json(paths[3],fp)
            if period=='1y':
                evidence[slug]=dict(label=payload['evidence_label'],period=payload['period'],return_pct=s['return_pct'],
                    profit_factor=s['pf'],drawdown_pct=s['equity_dd_pct'],win_rate_pct=s['win_pct'],trades=s['trades'],
                    sharpe_ratio=None,sharpe_annualized=s['sharpe'],max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],
                    history_quality=s['history_quality'],source_note=note,status=payload['evidence_status'])
            checks.append(dict(slug=slug,period=period,trades=len(rows),expert_sha=profile['expert_sha'],native_report_sha=result['report_sha']))
            print('PUBLISHED',slug,period,len(rows),flush=True)
    write_json(R/'WEBSITE_SUMMARY.json',dict(version=selection['version'],results=evidence))
    path=CACHE_ROOT/'manifest.json';backup(path);manifest=load(path)
    manifest['admission_release']=dict(version=selection['version'],current_periods=['1y','3y','5y'],updated_slugs=list(selection['profiles']),
        filtered_slugs=['usdjpy-london-open-momentum'],restored_slugs=['ema3','asia-breakout','xau-trend-progression'],
        portfolio_status='Prior portfolio/FTMO forecasts archived, not revalidated',selection='Explicit user final decision')
    for item in manifest.get('recommended_eas',[]):
        if item.get('slug') in selection['profiles']:item.update(mode='standard',admission_release=selection['version'])
    write_json(path,manifest)
    before=load(R/'BEFORE.json')
    assert all(sha(Path(p))==h for p,h in before['unchanged_hashes'].items())
    write_json(R/'WEBSITE_PUBLICATION.json',dict(checks=checks,remaining_archived=['6m'],rsi_and_client_unchanged=True,
        historical_filter_study_preserved=True,live_mt5_changed=False,public_server_deployed=False))
    get_catalog.cache_clear()

if __name__=='__main__':main()
