from unittest.mock import MagicMock

from rsi_divergence_bot.config import AppConfig, SymbolConfig
from rsi_divergence_bot.trader import TradeExecutor


def _config() -> AppConfig:
    return AppConfig(
        symbols=[SymbolConfig(symbol="XAUUSD-VIP", name="Gold", lot_per_leg=0.08)],
    )


def test_place_market_setup_split_mode_ignores_full_strategy():
    config = _config()
    config.bot.strategy = "signal_full_with_tp_protection"
    client = MagicMock()
    client.tick.return_value = {"bid": 4525.0, "ask": 4525.5}
    client.TRADE_DONE = 10009

    def send_market(symbol, side, volume, sl, tp, magic, comment):
        result = MagicMock()
        result.retcode = 10009
        result.order = 1000 + int(tp)
        return result

    client.send_market.side_effect = send_market
    state = MagicMock()
    logger = MagicMock()
    executor = TradeExecutor(config, client, state, logger)
    result = executor.place_market_setup(
        setup_id="test:1",
        symbol="XAUUSD-VIP",
        market_key="XAUUSD",
        side="sell",
        sl=4537.0,
        tps=[4524.0, 4520.0, 4516.0],
        lot_per_leg=0.08,
        execution_mode="split",
    )
    assert result["status"] == "placed"
    assert result["legs"] == 3
    assert client.send_market.call_count == 3
