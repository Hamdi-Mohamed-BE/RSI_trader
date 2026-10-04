import hashlib,json
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.catalog import PACKAGE_ROOT,get_product
from app.main import app
from app.news_evidence import XAU_PROFILE,load_news_summary
from tools.precompute_evidence_cache import independent_news_result

ROOT=PACKAGE_ROOT/'News Pulse Event Parameters Research 2026-09-19'/'Deployment'

def test_dedicated_xau_build_is_independent_of_multi_asset_news():
 xau=get_product('news-pulse-xau')
 assert 'Event Specific' in xau.expert_source
 for slug in ['news-pulse-xag','news-pulse-btc','news-pulse-eurusd']:
  assert 'Multi Asset Event' in get_product(slug).expert_source
 old=PACKAGE_ROOT/'AAA Final EAs'/'AAA Final News Pulse EA'/'AAA Final News Pulse EA.mq5'
 # Pin the unchanged legacy code committed before this risk-input release
 # (03a47d30). Normalize Git/Windows line endings, not code or whitespace.
 assert hashlib.sha256(old.read_bytes().replace(b'\r\n',b'\n')).hexdigest()=='6546008051e57c0d4fe844dd9471a97e0b7356f363ea5a36f4dae0896e2d5ad4'

def test_production_native_parity_and_runtime_event_recovery():
 product=get_product('news-pulse-xau');source=(PACKAGE_ROOT/product.expert_source).with_suffix('.mq5')
 parity=json.loads((ROOT/'PARITY.json').read_text())
 assert parity['passed']
 risk_root=PACKAGE_ROOT/'News Standalone Risk 2026-09-28'
 risk=json.loads((risk_root/'NATIVE_VERIFICATION.json').read_text())
 archived=json.loads((Path(__file__).resolve().parents[1]/'data/evidence-cache/v1/products/news-pulse-xau/standard/1y.json').read_text())
 assert risk['passed'] and risk['build']['XAU']['baseline_source_sha256']==archived['source_sha256']
 assert risk['build']['XAU']['source_sha256']!=hashlib.sha256(source.read_bytes()).hexdigest()
 assert parity['source_sha256']==risk['build']['XAU']['baseline_source_sha256']
 assert any(x['asset']=='XAU' and x['default_risk_exact_trade_parity'] for x in risk['checks'])
 assert parity['stats']['trades']==38 and parity['stats']['return_pct']==262.1
 code=source.read_text()
 assert 'NP_LeadSeconds(candidate_kind)' in code and 'NP_LeadSeconds(g_cached_event_kind)' in code
 assert 'NP_ApplyEventParameters(g_active_event_kind)' in code
 assert 'NP_KindFromComment(OrderGetString(ORDER_COMMENT))' in code
 assert 'NP_KindFromComment(PositionGetString(POSITION_COMMENT))' in code
 assert 'Deliberately not OCO' in code

@pytest.mark.parametrize('period,start',[('6m','2026-03-05'),('1y','2025-09-05'),('3y','2023-09-05'),('5y','2021-09-05')])
def test_prior_xau_web_data_is_archived_not_published_as_changed_geometry(period,start):
 payload=json.loads((Path(__file__).resolve().parents[1]/f'data/evidence-cache/v1/products/news-pulse-xau/standard/{period}.json').read_text())
 assert payload and payload['strategy_profile']==XAU_PROFILE
 result=json.loads((ROOT/f'news-pulse-xau-{period}-model4.json').read_text())
 assert payload['stats']['trades']==result['stats']['trades']
 assert payload['stats']['net_profit']==result['stats']['net_profit']
 assert payload['optimization_in_sample'] is True
 assert load_news_summary('news-pulse-xau',period) is None
 with pytest.raises(RuntimeError,match='source changed'):
  independent_news_result(get_product('news-pulse-xau'),'standard',period,date.fromisoformat(start),date(2026,9,5))
 with TestClient(app) as client:
  api=client.get('/api/evidence/news-pulse-xau/series',params={'period':period})
  assert api.status_code in (404,503)
  page=client.get('/eas/news-pulse-xau',params={'period':period})
  assert page.status_code==200
  assert f"{payload['stats']['return_pct']:+,.2f}%" not in page.text
  assert 'T+30' in page.text
  assert 'T-5s' in page.text and 'T-60s' in page.text

def test_all_maintained_bats_route_to_new_xau():
 for name in ['BEST RECOMMENDED 2026-09-01.bat','INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat','INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat','INSTALL AND RUN ON 100K MT5.bat','INSTALL AND RUN ON 900 USD MT5.bat','INSTALL AND RUN ON ACTIVE MT5.bat','RECOMMENDED ADAPTIVE.bat']:
  text=(PACKAGE_ROOT/name).read_text()
  assert 'XAU News Pulse v2.20' in text
 script=(PACKAGE_ROOT/'_Auto Deploy'/'Install-BMTradingPortfolio.ps1').read_text()
 assert "$inputs['InpUseXauEventSpecific'] = 'true'" in script
 assert "$inputs['InpMarketFallbackOnCrossedLevel'] = 'true'" in script
 assert "$inputs['InpEnableSellSide'] = 'true'" in script
 assert "$inputs['InpEnableBuySide'] = 'true'" in script
