"""Publish reconciled production results and refresh affected portfolio overlays."""
import json, shutil, sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent;PACKAGE=ROOT.parent;DEPLOY=ROOT/'Deployment'
STORE=PACKAGE.parent/'EA store';sys.path.insert(0,str(STORE))
from app.catalog import get_product,get_sellable_catalog
from app.news_evidence import news_payload_from_result
from app.news_evidence import load_news_summary
from app.adaptive_portfolio import RULES as ADAPTIVE_RULES
from app.news_profiles import MULTI_PROFILE,MULTI_SLUGS,event_parameters
from app.evidence_cache import CACHE_ROOT,write_json
from tools.precompute_evidence_cache import independent_news_result,build_portfolio,source_paths,source_fingerprint,recommended_mode

WINDOWS={'6m':'2026-03-05','1y':'2025-09-05','3y':'2023-09-05','5y':'2021-09-05'}
NOTICE=' User-approved News Pulse XAG/BTC/EURUSD v2.17 full-year fit; XAU v2.16 unchanged. Event settings were selected on overlapping history. These are separately sized native ledgers, not simultaneous shared-margin account performance. Mixed real/generated tick coverage and adverse news execution limit inference. Not a forward forecast or prop-firm safety claim.'

def main():
    # Audit every new window before replacing even the first public record.
    audited={}
    for slug in sorted(MULTI_SLUGS):
        asset=slug.removeprefix('news-pulse-').upper()
        product=get_product(slug)
        for period,start in WINDOWS.items():
            result,report=independent_news_result(product,'standard',period,date.fromisoformat(start),date(2026,9,5))
            assert result['parameters']==event_parameters(asset)
            audited[slug,period]=(result,report,news_payload_from_result(result))
    archive=DEPLOY/'Previous Website Cache'
    backup_complete=(archive/'manifest.json').exists()
    for relative in [*(f'products/{slug}' for slug in sorted(MULTI_SLUGS)),*(f'source-runs/{slug}' for slug in sorted(MULTI_SLUGS)), 'portfolio','manifest.json']:
        source=CACHE_ROOT/relative;target=archive/relative
        if not backup_complete and source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.is_dir():shutil.copytree(source,target)
            else:shutil.copy2(source,target)
    summary={}
    for (slug,period),(result,report,payload) in audited.items():
        dest=CACHE_ROOT/'products'/slug/'standard'
        write_json(dest/(period+'.json'),payload);write_json(dest/(period+'.trades.json'),result['trades'])
        product=get_product(slug);cached_report,metadata=source_paths(product,'standard',period)
        cached_report.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(report,cached_report)
        write_json(metadata,source_fingerprint(product,'standard',date.fromisoformat(WINDOWS[period]),date(2026,9,5)))
        summary.setdefault(slug,{})[period]=result['stats']
    get_sellable_catalog.cache_clear() if hasattr(get_sellable_catalog,'cache_clear') else None
    products=get_sellable_catalog();portfolio_rows=[]
    assert len(products)==33
    for period in WINDOWS:
        reference=json.loads((CACHE_ROOT/'portfolio'/'standard'/(period+'.json')).read_text())
        pstart=date.fromisoformat(reference['available_from']);pend=date.fromisoformat(reference['available_to'])
        portfolio=build_portfolio(products,period,pstart,pend)
        assert portfolio['included_ea_count']==33 and portfolio['tested_ea_count']==32
        portfolio_rows.append(dict(period=period,stats=portfolio['stats'],included_ea_count=33,tested_ea_count=32))
        for mode in ('current','standard','recommended-adaptive'):
            path=CACHE_ROOT/'portfolio'/mode/(period+'.json');value=json.loads(path.read_text())
            value['news_multi_strategy_profile']=MULTI_PROFILE
            value['news_xau_strategy_profile']='xau-event-specific-2026-09-19'
            value['optimization_in_sample']=True
            value['notice']=value.get('notice','')+NOTICE
            write_json(path,value)
    path=CACHE_ROOT/'manifest.json';manifest=json.loads(path.read_text())
    manifest['generated_at']=datetime.now(timezone.utc).isoformat()
    manifest['recommended_eas']=[dict(slug=p.slug,label=p.label,symbol=p.canonical,timeframe=p.timeframe,mode=recommended_mode(p)) for p in products]
    manifest['recommended_ea_count']=len(products)
    manifest['tested_ea_count']=32
    manifest['adaptive_rules']=list(ADAPTIVE_RULES)
    manifest['generated_runs']=[row for row in manifest.get('generated_runs',[]) if not row.get('slug','').startswith('news-pulse-')]
    for p in products:
        if p.label.startswith('News Pulse '):
            for period in WINDOWS:
                payload=load_news_summary(p.slug,period)
                assert payload
                manifest['generated_runs'].append(dict(slug=p.slug,mode='standard',period=period,stats=payload['stats'],strategy_profile=payload['strategy_profile']))
    manifest['portfolio']=portfolio_rows;manifest['news_multi_strategy_profile']=MULTI_PROFILE
    if NOTICE not in manifest.get('methodology',''):
        manifest['methodology']=manifest.get('methodology','')+NOTICE
    write_json(path,manifest)
    write_json(DEPLOY/'PUBLISHED.json',dict(products=summary,portfolio=portfolio_rows))
    lines=['# Approved News Pulse deployment — 2026-09-19','','XAG/BTC/EURUSD: full-year fitted v2.17. XAU v2.16 unchanged. Both sides retained; 0.75% planned equity risk per side; adaptive exempt.',
           '', 'No running terminal was restarted or attached. Reapply a maintained BAT to install; RECOMMENDED ADAPTIVE.bat selects the updated 33-EA roster. No Git push performed.',
           '', '## Website native evidence', '', 'Every row is a separate $10,000 native test ending **2026-09-05**. This differs from the original research comparison ending 2026-09-19. Returns include recorded commissions and swaps. History quality is real-tick percentage; remaining ticks may be generated.',
           '', '| Asset | Period | Return | Trades | Win rate | PF | Equity DD | Real ticks |', '|---|---|---:|---:|---:|---:|---:|---|']
    for slug,periods in summary.items():
        for period,s in periods.items():
            lines.append(f"| {slug.removeprefix('news-pulse-').upper()} | {period} | {s['return_pct']:+,.2f}% | {s['trades']} | {s['win_rate_pct']:.2f}% | {s['profit_factor']:.2f} | {s['max_drawdown_pct']:.2f}% | {s['history_quality']} |")
    lines+=['','## Limits','','Hindsight optimization overlaps test history. Tight stops can produce losses far beyond 0.75% per side. Four concurrent News Pulse straddles plan 6% combined before fees, rounding and gaps; Gold News V9 adds exposure. No prop-firm safety claim.',
            '', 'Portfolio totals are a chronological overlay of independently sized ledgers, with closed-balance DD. They do not enforce shared margin or reproduce live portfolio equity.',
            '', 'Previous caches are recoverable in `Previous Website Cache`. Native reports, source hashes, exact SETs, production/research parity and approved parameter maps are retained in this folder and the parent research directory.']
    (DEPLOY/'DEPLOYMENT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(products=summary,portfolio=portfolio_rows),indent=2))

if __name__=='__main__':main()
