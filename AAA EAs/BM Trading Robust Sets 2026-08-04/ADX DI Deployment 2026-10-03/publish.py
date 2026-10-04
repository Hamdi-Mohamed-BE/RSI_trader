"""Publish verified ONE-YEAR native ledgers, never invent other windows."""
from pathlib import Path
from datetime import date,datetime,timezone,timedelta
import gzip,json,os,sys,shutil,hashlib
R=Path(__file__).resolve().parent;B=R.parent;S=B/'ADX DI Five Bot Review 2026-10-03';STORE=B.parent/'EA store'
os.environ['EA_STORE_DISABLE_MT5']='1';sys.path[:0]=[str(STORE),str(STORE/'tools')]
import precompute_evidence_cache as P
from app.catalog import get_catalog,get_product
from app.trade_metrics import enrich_trades
from app.evidence_cache import product_cache_path,product_trades_path,write_json,CACHE_ROOT
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def backup(p):
 out=R/'before'/p.relative_to(STORE)
 if p.is_file() and not out.exists():out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
def publish():
 selection=load(R/'SELECTION.json');parity=load(R/'PARITY.json');assert parity['passed'] and len(parity['checks'])==4
 start=date(2025,10,2);end=date(2026,10,2);evidence={};checks=[]
 profiles=dict(selection['profiles'])
 profiles['xau-rsi-vwap']=dict(key='rsi',research_case='rsi-BASE',label='XAU RSI VWAP',provisional=False)
 for slug,p in profiles.items():
  case=S/'native'/p['research_case'];result=load(case/'result.json');s=result['stats']
  rows=json.loads(gzip.decompress((case/'trades.json.gz').read_bytes()))
  rows=enrich_trades(rows,slug)
  for n,row in enumerate(rows,1):row.update(number=n,cache_slug=slug,cache_mode='standard',cache_period='1y',source='Native MT5, costs included; research/production selected-filter parity verified' if slug!='xau-rsi-vwap' else 'Unchanged original strategy; native MT5 costs included')
  stats,series=P.portfolio_metrics(rows,start,end)
  stats.update(return_pct=s['return_pct'],profit_factor=s['pf'],win_rate_pct=s['win_pct'],max_drawdown_pct=s['equity_dd_pct'],max_equity_drawdown_pct=s['equity_dd_pct'],max_closed_balance_drawdown_pct=s['closed_dd_pct'],sharpe_annualized=s['sharpe'],sharpe_ratio=None,max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],trades_per_month=s['trades_month'],trades_per_trading_day=s['trades_weekday'],to=str(end-timedelta(days=1)),end_exclusive=str(end))
  series[-1]['time']=end.isoformat()+'T00:00:00'
  assert len(rows)==s['trades'] and abs(sum(t['net_profit'] for t in rows)-s['net'])<.01
  product=get_product(slug);assert product and product.expert_source
  fingerprint=P.source_fingerprint(product,'standard',start,end)
  fingerprint.update(research_case=p['research_case'],research_report_sha256=result['report_sha'],research_ledger_sha256=sha(case/'trades.json.gz'),production_parity_sha256=sha(R/'PARITY.json') if slug!='xau-rsi-vwap' else sha(S/'PARITY.json'))
  if slug!='xau-rsi-vwap':
   prod=R/'native'/(p['key']+'-ORIGINAL')
   fingerprint['production_native_report_sha256']=load(prod/'result.json')['report_sha']
   report=gzip.decompress((prod/'report.htm.gz').read_bytes())
  else:report=gzip.decompress((case/'report.htm.gz').read_bytes())
  note='Standalone Exness native MT5 Model 4, 2025-10-02 to 2026-10-02 exclusive; $10,000 start, 1% equity-risk target, 150ms delay and recorded costs. 75% real ticks; earlier segment generated. Upward/minimum-lot rounding can exceed target risk. Closed-balance curve; maximum equity drawdown measured natively. Retrospective one-year filter selection, not independent validation or a guarded FTMO simulation.'
  if p['provisional']:note+=' PROVISIONAL: only 29 trades, below the 30-trade screen.'
  if slug=='xau-rsi-vwap':note+=' RSI VWAP source, binary, inputs and strategy are unchanged.'
  payload=dict(label=product.label,period=f'{start} to {end-timedelta(days=1)}',period_key='1y',mode='standard',currency='USD',series=series,stats=stats,available_from=str(start),available_to=str(end-timedelta(days=1)),end_exclusive=str(end),evidence_label='User-selected ADX/DI · one-year retrospective screen' if slug!='xau-rsi-vwap' else 'Unchanged RSI VWAP · same one-year comparison',evidence_status='Provisional research' if p['provisional'] else 'Retrospective research evidence',history_quality=s['history_quality'],notice=note,source='native-mt5-adxdi-parity-20261003',source_fingerprint=fingerprint,cached_trade_count=len(rows),trade_coverage_from=min(t['open_time'] for t in rows),trade_coverage_to=max(t['close_time'] for t in rows),configuration_release=selection['version'],generated_at=datetime.now(timezone.utc).isoformat())
  paths=[product_cache_path(slug,'standard','1y'),product_trades_path(slug,'standard','1y'),*P.source_paths(product,'standard','1y')]
  for path in paths:backup(path)
  write_json(paths[1],rows);fingerprint['cached_trades_sha256']=sha(paths[1]);write_json(paths[0],payload)
  paths[2].parent.mkdir(parents=True,exist_ok=True);paths[2].write_bytes(report);write_json(paths[3],fingerprint)
  evidence[slug]=dict(label=payload['evidence_label'],period=payload['period'],return_pct=s['return_pct'],profit_factor=s['pf'],drawdown_pct=s['equity_dd_pct'],win_rate_pct=s['win_pct'],trades=s['trades'],sharpe_ratio=None,sharpe_annualized=s['sharpe'],max_win_streak=s['max_win_streak'],max_loss_streak=s['max_loss_streak'],history_quality=s['history_quality'],source_note=note,status=payload['evidence_status'])
  checks.append(dict(slug=slug,period='1y',stats=stats,configuration_release=selection['version']))
  print('PUBLISHED',slug,s['trades'],flush=True)
 write_json(R/'WEBSITE_SUMMARY.json',dict(version=selection['version'],results=evidence))
 path=CACHE_ROOT/'manifest.json';backup(path);manifest=load(path)
 manifest['admission_release']=dict(version=selection['version'],current_filtered_periods=['1y'],updated_slugs=list(selection['profiles']),portfolio_status='Prior portfolio/FTMO forecasts are archived, not revalidated',selection='Explicit user approval, retrospective; Trend provisional')
 for item in manifest.get('recommended_eas',[]):
  if item.get('slug') in selection['profiles']:item['mode']='standard';item['admission_release']=selection['version']
 write_json(path,manifest)
 write_json(R/'WEBSITE_PUBLICATION.json',dict(checks=checks,other_periods='Archived unfiltered configuration, preserved',live_mt5_changed=False,public_server_deployed=False))
 get_catalog.cache_clear()
if __name__=='__main__':publish()
