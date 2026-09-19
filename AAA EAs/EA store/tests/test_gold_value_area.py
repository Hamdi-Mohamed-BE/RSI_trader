"""Raw-only integration, immutable evidence and shared-window regressions."""
import json
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.catalog import get_product,get_sellable_catalog
from app.gold_value_area import payload,SLUG
from app.evidence_cache import CACHE_ROOT
from tools.precompute_evidence_cache import common_cached_window,gold_raw_result

@pytest.mark.parametrize('period',('6m','1y','3y','5y'))
def test_raw_native_totals_and_routes(period):
    p,rows=payload(period)
    assert len(rows)==p['stats']['trades']
    assert abs(sum(r['net_profit'] for r in rows)-p['stats']['net_profit'])<.03
    assert abs(sum(r['commission'] for r in rows)-p['stats']['commission'])<.03
    assert abs(sum(r['swap'] for r in rows)-p['stats']['swap'])<.03
    c=TestClient(app)
    page=c.get(f'/eas/{SLUG}?period={period}')
    assert page.status_code==200
    result=c.get(f'/api/evidence/{SLUG}/series?period={period}')
    assert result.status_code==200
    assert result.json()['stats']==p['stats']
    assert result.json()['cached_trade_count']==len(rows)

def test_only_raw_mode_is_approved():
    product=get_product(SLUG)
    assert not product.safe_filter_supported
    assert not product.dynamic_mode_supported
    p,rows=payload('1y')
    assert len(rows)==200
    assert p['stats']['win_rate_pct']==74
    with pytest.raises(RuntimeError):gold_raw_result('standard','1y',date(2025,9,5),date(2026,9,5))

@pytest.mark.parametrize('period',('6m','1y','3y','5y'))
def test_portfolio_inventory_and_cash_flow(period):
    start,end=common_cached_window(get_sellable_catalog(),period)
    assert end==date(2026,8,30)
    p=json.loads((CACHE_ROOT/'portfolio/standard'/f'{period}.json').read_text())
    rr=json.loads((CACHE_ROOT/'portfolio/standard'/f'{period}.trades.json').read_text())
    assert p['available_from']==start.isoformat() and p['available_to']==end.isoformat()
    assert p['included_ea_count']==34 and p['tested_ea_count']==33
    assert abs(sum(r['net_profit'] for r in rr)-p['stats']['net_profit'])<.05
    assert any(r['cache_slug']==SLUG for r in rr)
    assert all(start.isoformat()<=r['close_time'][:10]<=end.isoformat() for r in rr)
    m=json.loads((CACHE_ROOT/'manifest.json').read_text())
    assert m['recommended_ea_count']==34
    assert any(r['slug']==SLUG and r['period']==period for r in m['generated_runs'])
