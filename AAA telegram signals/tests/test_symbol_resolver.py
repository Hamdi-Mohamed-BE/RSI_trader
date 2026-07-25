import pytest
from unittest.mock import patch, MagicMock
from app.trading.symbol_resolver import SymbolResolver

@pytest.fixture
def mock_resolver():
    resolver = SymbolResolver()
    return resolver

@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_exact_match(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True
    
    # Mock symbols returned by MT5
    symbol_1 = MagicMock()
    symbol_1.name = "EURUSD"
    
    symbol_2 = MagicMock()
    symbol_2.name = "USDCAD"
    
    mock_mt5.symbols_get.return_value = [symbol_1, symbol_2]
    
    broker_sym, conf = mock_resolver.resolve("EURUSD")
    assert broker_sym == "EURUSD"
    assert conf == 1.0

@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_suffix_normalization(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True
    
    symbol_1 = MagicMock()
    symbol_1.name = "EURUSDm" # Standard suffix m
    
    symbol_2 = MagicMock()
    symbol_2.name = "USDCAD.raw" # Suffix .raw
    
    mock_mt5.symbols_get.return_value = [symbol_1, symbol_2]
    
    # Resolve EURUSD -> EURUSDm
    broker_sym, conf = mock_resolver.resolve("EURUSD")
    assert broker_sym == "EURUSDm"
    assert conf >= 0.90
    
    # Resolve USDCAD -> USDCAD.raw
    broker_sym, conf = mock_resolver.resolve("USDCAD")
    assert broker_sym == "USDCAD.raw"
    assert conf >= 0.90

@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_alias_mapping(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True
    
    symbol_1 = MagicMock()
    symbol_1.name = "XAUUSD" # Alias for GOLD
    
    symbol_2 = MagicMock()
    symbol_2.name = "USTEC" # Alias for NAS100
    
    mock_mt5.symbols_get.return_value = [symbol_1, symbol_2]
    
    # Resolve GOLD -> XAUUSD
    broker_sym, conf = mock_resolver.resolve("GOLD")
    assert broker_sym == "XAUUSD"
    assert conf >= 0.90
    
    # Resolve NAS100 -> USTEC
    broker_sym, conf = mock_resolver.resolve("NAS100")
    assert broker_sym == "USTEC"
    assert conf >= 0.90

@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_us100_to_suffixed_ustec(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True
    symbol = MagicMock()
    symbol.name = "USTECm"
    mock_mt5.symbols_get.return_value = [symbol]

    broker_sym, conf = mock_resolver.resolve("US100")

    assert broker_sym == "USTECm"
    assert conf >= 0.90


@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_us30_prefers_upcomers_index_over_dow_stock(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True

    dow_stock = MagicMock()
    dow_stock.name = "DOW"
    dow_stock.trade_mode = 4

    us30_index = MagicMock()
    us30_index.name = "DJCUSD.c"
    us30_index.trade_mode = 4

    mock_mt5.symbols_get.return_value = [dow_stock, us30_index]

    broker_sym, conf = mock_resolver.resolve("US30")

    assert broker_sym == "DJCUSD.c"
    assert conf >= 0.90


@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_dow_signal_prefers_us30_index_over_stock(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True

    dow_stock = MagicMock()
    dow_stock.name = "DOW"
    dow_stock.trade_mode = 4

    us30_index = MagicMock()
    us30_index.name = "DJCUSD.c"
    us30_index.trade_mode = 4

    mock_mt5.symbols_get.return_value = [dow_stock, us30_index]

    broker_sym, conf = mock_resolver.resolve("DOW")

    assert broker_sym == "DJCUSD.c"
    assert conf >= 0.90


@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_us100_prefers_upcomers_nasdaq_index(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True

    nasdaq_index = MagicMock()
    nasdaq_index.name = "NACUSD.c"
    nasdaq_index.trade_mode = 4

    mock_mt5.symbols_get.return_value = [nasdaq_index]

    for requested in ("US100", "NAS100", "USTEC"):
        mock_resolver.clear_cache()
        broker_sym, conf = mock_resolver.resolve(requested)

        assert broker_sym == "NACUSD.c"
        assert conf >= 0.90


@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_xaausd_skips_close_only_gold_stock(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True

    close_only_gold_stock = MagicMock()
    close_only_gold_stock.name = "GOLD"
    close_only_gold_stock.trade_mode = 3

    spot_gold = MagicMock()
    spot_gold.name = "XAUUSD"
    spot_gold.trade_mode = 4

    mock_mt5.symbols_get.return_value = [close_only_gold_stock, spot_gold]

    broker_sym, conf = mock_resolver.resolve("XAAUSD")

    assert broker_sym == "XAUUSD"
    assert conf >= 0.90


@patch("app.trading.symbol_resolver.mt5_client")
@patch("app.trading.symbol_resolver.mt5")
def test_resolve_rechecks_cached_symbol_after_account_switch(mock_mt5, mock_client, mock_resolver):
    mock_client.connect.return_value = True

    account = MagicMock()
    account.login = 1001
    account.server = "Broker-A"
    mock_mt5.account_info.return_value = account

    plain_gold = MagicMock()
    plain_gold.name = "XAUUSD"
    plain_gold.trade_mode = 4
    mock_mt5.symbol_info.return_value = plain_gold
    mock_mt5.symbols_get.return_value = [plain_gold]

    broker_sym, conf = mock_resolver.resolve("XAUUSD")
    assert broker_sym == "XAUUSD"
    assert conf >= 0.90

    account.login = 2002
    account.server = "Broker-B"
    mock_mt5.symbol_info.return_value = None

    suffixed_gold = MagicMock()
    suffixed_gold.name = "XAUUSD.."
    suffixed_gold.trade_mode = 4
    mock_mt5.symbols_get.return_value = [suffixed_gold]

    broker_sym, conf = mock_resolver.resolve("XAUUSD")

    assert broker_sym == "XAUUSD.."
    assert conf >= 0.90
