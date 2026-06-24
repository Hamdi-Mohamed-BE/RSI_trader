from unittest.mock import MagicMock

from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramChannelConfig, TelegramSignalsConfig
from rsi_divergence_bot.telegram_signals import ParsedTelegramSignal, TelegramSignalsBot, _looks_like_trade


def _config() -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(
            channels=[TelegramChannelConfig(name="Test", url="https://t.me/test")],
        ),
        symbols=[
            SymbolConfig(symbol="XAUUSD-VIP", name="XAUUSD", lot_per_leg=0.08),
        ],
    )


def test_looks_like_trade_detects_signal_text():
    text = "CHFJPY SELL NOW STOPLOSS @ 204.080 TP @ 202.100"
    assert _looks_like_trade(text) is True


def test_hard_place_skips_daily_guard():
    config = _config()
    config.bot.dry_run = True
    client = MagicMock()
    client.tick.return_value = {"bid": 4525.0, "ask": 4525.5}
    state = MagicMock()
    state.get_telegram_message.return_value = None
    logger = MagicMock()
    bot = TelegramSignalsBot(config, client, state, logger, daily_risk_status=lambda: {"enabled": True, "halted": True})
    parsed = ParsedTelegramSignal(
        symbol="XAUUSD",
        action="sell",
        stop_loss=4537.0,
        tps=[4524.0, 4520.0],
    )
    channel = TelegramChannelConfig(name="Test", url="https://t.me/test")
    result = bot._place_parsed_signal(parsed, source_id="abc", channel=channel, hard=True)
    assert result["status"] == "paper"


def test_hard_place_rejects_invalid_tps():
    config = _config()
    config.bot.dry_run = True
    client = MagicMock()
    client.tick.return_value = {"bid": 4510.0, "ask": 4510.5}
    state = MagicMock()
    logger = MagicMock()
    bot = TelegramSignalsBot(config, client, state, logger)
    parsed = ParsedTelegramSignal(
        symbol="XAUUSD",
        action="sell",
        stop_loss=4537.0,
        tps=[4524.0, 4520.0],
    )
    channel = TelegramChannelConfig(name="Test", url="https://t.me/test")
    result = bot._place_parsed_signal(parsed, source_id="abc", channel=channel, hard=True)
    assert result["status"] == "skipped"
    assert "TPs no longer valid" in str(result.get("reason"))
