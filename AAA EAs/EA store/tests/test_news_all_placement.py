"""Fresh-quote repair contracts. No live trading or active terminal access."""
import hashlib
import re
import pytest
from app.catalog import PACKAGE_ROOT,get_product
from app.news_evidence import load_news_summary
def function(code,name):
    start=re.search(r'(?m)^(?:bool|void|int|double|string|datetime)\s+'+name+r'\(',code).start()
    brace=code.index('{',start);end=brace+1;depth=1
    while depth:
        depth+=(code[end]=='{')-(code[end]=='}');end+=1
    return code[brace:end]

NAMES=['AAA Final News Pulse XAU Event Specific EA','AAA Final News Pulse Multi Asset Event EA']
RELEASE=PACKAGE_ROOT/'News Placement All Assets 2026-10-03'

@pytest.mark.parametrize('name',NAMES)
def test_preserve_event_parameters_risk_and_exits(name):
    active=(PACKAGE_ROOT/'AAA Final EAs'/name/(name+'.mq5')).read_text()
    old=(RELEASE/'baseline'/(name+'.mq5')).read_text()
    for f in ['NP_ApplyEventParameters','NP_TrailPositions','NP_ClosePositions']:
        assert function(active,f)==function(old,f)
    for setting in ['InpRiskPercent','InpForceCloseSecondsAfterEvent','InpEntryOffsetPrice','InpStopLossPrice']:
        pattern=rf'input\s+\w+\s+{setting}=[^;]+;'
        assert re.search(pattern,active).group()==re.search(pattern,old).group()

@pytest.mark.parametrize('name',NAMES)
def test_definite_rejection_repairs_price_but_uncertain_outcome_does_not(name):
    code=(PACKAGE_ROOT/'AAA Final EAs'/name/(name+'.mq5')).read_text()
    side=function(code,'NP_SendSide')
    assert 'attempt<3' in side and 'now>=g_active_event_time' in side
    assert 'tick.ask+g_np_offset : tick.bid-g_np_offset' in side
    assert 'force_market=market || attempt>=1' in side
    assert 'if(!repairable) return false' in side
    unknown=side[side.index('if(rc==0'):side.index('g_side_inflight&=~bit;',side.index('if(rc==0'))]
    assert 'TRADE_RETCODE_TIMEOUT' in unknown and 'return false;' in unknown
    assert side.index('NP_PlanSide(')<side.index('AAA_LotsForRisk(')<side.index('AAA_Trade.Buy(')
    assert '(g_side_accepted & bit)!=0' in side and '(g_side_inflight & bit)!=0' in side
    assert 'SYMBOL_ORDER_STOP' in side and 'SYMBOL_EXPIRATION_GTC' in side
    assert 'NP_ReconcileSides();' in function(code,'OnInit')

@pytest.mark.parametrize('slug',['news-pulse-xau','news-pulse-xag','news-pulse-btc','news-pulse-eurusd'])
def test_previous_cache_not_misrepresented_as_current(slug):
    for period in ['6m','1y','3y','5y']:
        assert load_news_summary(slug,period) is None
    assert get_product(slug).evidence is None

def test_ftmo_installer_unchanged():
    assert hashlib.sha256((PACKAGE_ROOT/'_Auto Deploy/Install-FTMO13.ps1').read_bytes()).hexdigest()=='fefbb53e320ed9f9a84c9b4a347dcc3ebc0155352229c48dfcaee68b30c3dc22'

def test_v9_remains_directional_current_quote_market_with_bounded_repair():
    code=(PACKAGE_ROOT.parent.parent/'AI news/mt5/GoldNewsV9EA.mq5').read_text()
    assert 'bool OpenPredictedTrade(const int retry=0)' in code
    assert 'TimeGMT()>=release_utc' in code and 'retry<2' in code
    assert 'return OpenPredictedTrade(retry+1)' in code
    assert 'entry_rc==TRADE_RETCODE_DONE' in code
    assert 'trade.Buy(lot,trade_symbol,0.0' in code and 'trade.Sell(lot,trade_symbol,0.0' in code
    assert 'BuyStop(' not in code and 'SellStop(' not in code
