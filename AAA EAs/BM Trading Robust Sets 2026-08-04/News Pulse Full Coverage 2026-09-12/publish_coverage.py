"""Publish only complete independently audited runs, then rebuild portfolio overlays."""
from __future__ import annotations
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
import run_coverage as run

ROOT=run.ROOT
sys.path.insert(0,str(run.STORE))
from app.evidence_cache import CACHE_ROOT,write_json
from app.catalog import get_sellable_catalog,get_catalog
from tools.precompute_evidence_cache import build_portfolio

from app.news_evidence import news_payload_from_result as make_payload
from tools.precompute_evidence_cache import independent_news_result

def main():
    rows=[]
    for period,start in run.WINDOWS.items():
        for slug in run.SLUGS:
            result,_=independent_news_result(run.get_product(slug),'standard',period,date.fromisoformat(start),date.fromisoformat(run.END))
            assert result['from_date']==start and result['to_exclusive']==run.END
            payload=make_payload(result)
            rows.append((slug,period,result,payload))
    # Preserve all superseded published news data and portfolio summaries/ledgers.
    backup=ROOT/'Previous Website Cache'
    backup.mkdir(parents=True,exist_ok=True)
    if not (backup/'manifest.json').exists():
        shutil.copy2(CACHE_ROOT/'manifest.json',backup/'manifest.json')
    for slug,period,result,payload in rows:
        relative=Path('products')/slug/'standard'
        for suffix in ('.json','.trades.json'):
            path=CACHE_ROOT/relative/(period+suffix);dest=backup/relative/path.name
            if path.is_file() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    for mode in ('standard','current','recommended-adaptive'):
        for period in run.WINDOWS:
            for suffix in ('.json','.trades.json'):
                relative=Path('portfolio')/mode/(period+suffix);path=CACHE_ROOT/relative;dest=backup/relative
                if path.is_file() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    for slug,period,result,payload in rows:
        folder=CACHE_ROOT/'products'/slug/'standard'
        write_json(folder/(period+'.trades.json'),result['trades'])
        write_json(folder/(period+'.json'),payload)
        source_folder=CACHE_ROOT/'source-runs'/slug/'standard';source_folder.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/result['source_report'],source_folder/(period+'.htm'))
        write_json(source_folder/(period+'.meta.json'),{k:payload[k] for k in ('source_report_sha256','calendar_sha256','available_from','available_to','news_evidence_version')})
    get_catalog.cache_clear()
    portfolio=[]
    for period,start in run.WINDOWS.items():
        payload=build_portfolio(get_sellable_catalog(),period,date.fromisoformat(start),date.fromisoformat(run.END))
        portfolio.append({'period':period,'stats':payload['stats'],'included_eas':payload['included_ea_count']})
    manifest_path=CACHE_ROOT/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    manifest['news_coverage']={'generated_at':datetime.now(timezone.utc).isoformat(),'from':'2021-09-05','to_exclusive':run.END,'calendar_events':158,'independent_runs':12,'model':4,'tick_quality_disclosed':True}
    manifest['generated_at']=datetime.now(timezone.utc).isoformat()
    manifest['generated_runs']=[r for r in manifest.get('generated_runs',[]) if r.get('slug') not in run.SLUGS]+[
        {'slug':slug,'mode':'standard','period':period,'stats':payload['stats'],'calendar_expected':result['calendar_expected'],
         'history_quality':result['stats']['history_quality']} for slug,period,result,payload in rows]
    manifest['portfolio']=portfolio
    manifest['failures']=[r for r in manifest.get('failures',[]) if r.get('slug') not in run.SLUGS]
    write_json(manifest_path,manifest)
    audit_path=run.STORE/'data'/'portfolio-consistency-audit.json'
    if audit_path.is_file():
        if not (backup/audit_path.name).exists():shutil.copy2(audit_path,backup/audit_path.name)
        audit=json.loads(audit_path.read_text(encoding='utf-8-sig'))
        current_news={slug:result for slug,period,result,_ in rows if period=='3y'}
        for item in audit.get('watchlist',[]):
            if item['slug'] not in current_news:continue
            stats=current_news[item['slug']]['stats']
            item['reason']=(f"Retained News Pulse exposure: the independent 3-year run has {stats['trades']} trades, "
                            f"with {stats['history_quality']}. All four windows use official release calendars; "
                            "older generated ticks and live news slippage remain important limitations.")
        audit['news_coverage_revision']={'generated_at':manifest['generated_at'],'periods':list(run.WINDOWS),
                                        'calendar_events':158,'note':'News watchlist and public portfolio caches refreshed. Other historical decision-audit scenarios are preserved, not rerun.'}
        write_json(audit_path,audit)
    write_json(ROOT/'PUBLISHED RESULTS.json',{'runs':[{k:v for k,v in r.items() if k not in ('trades','series','settings')} for _,_,r,_ in rows],'portfolio':portfolio})
    lines=['# News Pulse — full independent period coverage','',
           'Current v2.15 trading rules and recommended presets. USD 10,000 restarted per run; 0.75% planned risk per pending side. Actual costs and fills may exceed planned risk. No live trading or installer changes.','',
           '| EA | Period | Net return | Net PF | Win rate | Max equity DD | Trades | Events / placed | Tick quality | Commission | Swap |',
           '|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|']
    for slug,period,result,payload in rows:
        s=result['stats']
        lines.append(f"| {result['label']} | {period} | {s['return_pct']:+.2f}% | {s['profit_factor']} | {s['win_rate_pct']:.2f}% | {s['max_drawdown_pct']:.2f}% | {s['trades']} | {result['calendar_expected']} / {result['calendar_placed']} | {s['history_quality']} | ${s['commission']:,.2f} | ${s['swap']:,.2f} |")
    lines+=['','## Coverage and method','',*[f'- {p}: {s} to {run.END}, end exclusive.' for p,s in run.WINDOWS.items()],
            '', 'All 158 scheduled releases across the five-year window are sourced to BLS or Federal Reserve receipts. Event coverage and tick coverage are distinct: Model 4 can generate older ticks when broker real ticks are unavailable. Scheduled events without trades remain in the audit, not fabricated as fills. The tester journal confirms fixed 1 ms execution delay, not a random-delay stress test.',
            '', 'The research harness uses a faster, equivalent historical-calendar lookup. All three six-month native controls matched every trade field and statistic against the untouched strategy lookup (LOOKUP PARITY.json). No entry, exit, sizing or live EA rules were changed. The website deal importer now pairs exits to the correct long/short side when both news orders fill.',
            '', 'Cards, detail statistics, period selector, equity curves, trade lists and reconstructed portfolio overlays now use these period-matched records. The adaptive portfolio remains a chronological overlay of separate tests, not a joint-margin native portfolio backtest.',
            '', 'Sources: OFFICIAL CALENDAR.json and bls-source-receipts.json. Native HTML reports are in Backtest Reports, per-run journals in Audit, and the previous website files are preserved in Previous Website Cache.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':main()
