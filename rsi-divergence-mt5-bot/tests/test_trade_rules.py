from rsi_divergence_bot.decision import skip_should_mark_seen
from rsi_divergence_bot.portfolio import BacktestPortfolio


def test_skip_should_mark_seen_matches_live_retry_rules():
    assert skip_should_mark_seen("max_setups") is False
    assert skip_should_mark_seen("spread") is True
    assert skip_should_mark_seen("position") is True


def test_portfolio_tracks_open_setups_for_account_filters():
    portfolio = BacktestPortfolio()
    portfolio.register_open("abc", "BTCUSD", exit_unix=200)
    assert portfolio.active_setup_count() == 1
    assert portfolio.open_market_keys() == {"BTCUSD"}
    portfolio.settle_through(200)
    assert portfolio.active_setup_count() == 0
    assert portfolio.open_market_keys() == set()
