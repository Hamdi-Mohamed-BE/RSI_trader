"""Publish only completed, source-matched production XAU native windows."""
import json,shutil,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PACKAGE=ROOT.parent;DEPLOY=ROOT/'Deployment';STORE=PACKAGE.parent/'EA store'
sys.path.insert(0,str(STORE))
from app.catalog import get_product,get_sellable_catalog
from app.news_evidence import news_payload_from_result
from app.evidence_cache import CACHE_ROOT,write_json
from tools.precompute_evidence_cache import independent_news_result,build_portfolio,source_paths,source_fingerprint

archive=DEPLOY/'Previous Website Cache';archive.mkdir(exist_ok=True)
for relative in ['products/news-pulse-xau','portfolio','manifest.json']:
 source=CACHE_ROOT/relative;target=archive/relative
 if source.exists() and not target.exists():
  target.parent.mkdir(parents=True,exist_ok=True)
  if source.is_dir():shutil.copytree(source,target)
  else:shutil.copy2(source,target)

summary={}
for period,start in [('6m','2026-03-05'),('1y','2025-09-05'),('3y','2023-09-05'),('5y','2021-09-05')]:
 result,report=independent_news_result(get_product('news-pulse-xau'),'standard',period,date.fromisoformat(start),date(2026,9,5))
 payload=news_payload_from_result(result)
 dest=CACHE_ROOT/'products'/'news-pulse-xau'/'standard'
 write_json(dest/(period+'.json'),payload);write_json(dest/(period+'.trades.json'),result['trades'])
 product=get_product('news-pulse-xau')
 cached_report,metadata=source_paths(product,'standard',period)
 cached_report.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(report,cached_report)
 write_json(metadata,source_fingerprint(product,'standard',date.fromisoformat(start),date(2026,9,5)))
 summary[period]=result['stats']

get_sellable_catalog.cache_clear() if hasattr(get_sellable_catalog,'cache_clear') else None
products=get_sellable_catalog();portfolio_rows=[]
for period,start in [('6m','2026-03-05'),('1y','2025-09-05'),('3y','2023-09-05'),('5y','2021-09-05')]:
 # Preserve each existing portfolio's established range, without fabricating
 # new prices or rebasing other EAs onto the research September-19 window.
 reference=json.loads((CACHE_ROOT/'portfolio'/'standard'/(period+'.json')).read_text())
 pstart=date.fromisoformat(reference['available_from']);pend=date.fromisoformat(reference['available_to'])
 portfolio=build_portfolio(products,period,pstart,pend)
 portfolio_rows.append({'period':period,'stats':portfolio['stats'],'included_ea_count':portfolio['included_ea_count'],'tested_ea_count':portfolio['tested_ea_count']})
 for mode in ['current','standard','recommended-adaptive']:
  path=CACHE_ROOT/'portfolio'/mode/(period+'.json');value=json.loads(path.read_text())
  value['news_xau_strategy_profile']='xau-event-specific-2026-09-19'
  value['notice']=value.get('notice','')+' XAU News Pulse now uses user-approved event-specific parameters selected on overlapping history; portfolio performance inherits this hindsight bias and mixed real/generated tick coverage. Not a forward forecast.'
  write_json(path,value)
manifest_path=CACHE_ROOT/'manifest.json';manifest=json.loads(manifest_path.read_text())
manifest['portfolio']=portfolio_rows;manifest['news_xau_strategy_profile']='xau-event-specific-2026-09-19'
manifest['methodology']=manifest.get('methodology','')+' XAU News Pulse v2.16 event-specific configuration was user-approved after in-sample optimization; four independent native windows replace its old evidence.'
write_json(manifest_path,manifest)
write_json(DEPLOY/'PUBLISHED.json',{'xau':summary,'portfolio':portfolio_rows})
print(json.dumps({'xau':summary,'portfolio':portfolio_rows},indent=2))
