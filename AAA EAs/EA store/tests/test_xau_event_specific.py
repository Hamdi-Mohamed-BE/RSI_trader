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
 assert hashlib.sha256(old.read_bytes()).hexdigest()=='895f66f0189f7bc8c7411aa1cddcc7c82dfc56d9110864cc3d0c00143a13920f'

def test_production_native_parity_and_runtime_event_recovery():
 product=get_product('news-pulse-xau');source=(PACKAGE_ROOT/product.expert_source).with_suffix('.mq5')
 parity=json.loads((ROOT/'PARITY.json').read_text())
 assert parity['passed'] and parity['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
 assert parity['stats']['trades']==38 and parity['stats']['return_pct']==262.1
 code=source.read_text()
 assert 'NP_LeadSeconds(candidate_kind)' in code and 'NP_LeadSeconds(g_cached_event_kind)' in code
 assert 'NP_ApplyEventParameters(g_active_event_kind)' in code
 assert 'NP_KindFromComment(OrderGetString(ORDER_COMMENT))' in code
 assert 'NP_KindFromComment(PositionGetString(POSITION_COMMENT))' in code
 assert 'Deliberately not OCO' in code

@pytest.mark.parametrize('period,start',[('6m','2026-03-05'),('1y','2025-09-05'),('3y','2023-09-05'),('5y','2021-09-05')])
def test_current_xau_web_data_is_new_native_profile(period,start):
 payload=load_news_summary('news-pulse-xau',period)
 assert payload and payload['strategy_profile']==XAU_PROFILE
 result,_=independent_news_result(get_product('news-pulse-xau'),'standard',period,date.fromisoformat(start),date(2026,9,5))
 assert payload['stats']['trades']==result['stats']['trades']
 assert payload['stats']['net_profit']==result['stats']['net_profit']
 assert payload['optimization_in_sample'] is True
 with TestClient(app) as client:
  api=client.get('/api/evidence/news-pulse-xau/series',params={'period':period})
  assert api.status_code==200
  trades=api.json()['trades']
  assert len(trades)==payload['stats']['trades']
  assert sum(t['net_profit'] for t in trades)==pytest.approx(payload['stats']['net_profit'],abs=.05)
  page=client.get('/eas/news-pulse-xau',params={'period':period})
  assert page.status_code==200
  assert f"{payload['stats']['return_pct']:+,.2f}%" in page.text
  assert 'Hindsight-optimized' in page.text
  assert 'T-5s' in page.text and 'T-60s' in page.text

def test_all_maintained_bats_route_to_new_xau():
 for name in ['BEST RECOMMENDED 2026-09-01.bat','INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat','INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat','INSTALL AND RUN ON 100K MT5.bat','INSTALL AND RUN ON 900 USD MT5.bat','INSTALL AND RUN ON ACTIVE MT5.bat','RECOMMENDED ADAPTIVE.bat']:
  text=(PACKAGE_ROOT/name).read_text()
  assert 'XAU News Pulse v2.16' in text
 script=(PACKAGE_ROOT/'_Auto Deploy'/'Install-BMTradingPortfolio.ps1').read_text()
 assert "$inputs['InpUseXauEventSpecific'] = 'true'" in script
 assert "$inputs['InpEnableSellSide'] = 'true'" in script
 assert "$inputs['InpEnableBuySide'] = 'true'" in script
