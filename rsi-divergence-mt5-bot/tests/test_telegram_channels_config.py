import pytest

from rsi_divergence_bot.config import (
    AppConfig,
    SymbolConfig,
    TelegramChannelConfig,
    TelegramSignalsConfig,
    add_telegram_channel,
    normalize_telegram_channel_url,
    remove_telegram_channel,
    update_telegram_channel,
)


def _config() -> AppConfig:
    return AppConfig(
        telegram_signals=TelegramSignalsConfig(
            channels=[
                TelegramChannelConfig(
                    name="FOREX USA MASTER",
                    url="https://web.telegram.org/k/#@FOREXUSAMASTER1",
                    enabled=True,
                )
            ]
        ),
        symbols=[SymbolConfig(symbol="EURUSD-VIP", name="EURUSD", lot_per_leg=0.25)],
    )


def test_normalize_telegram_channel_url_accepts_username():
    assert normalize_telegram_channel_url("@FOREXUSAMASTER1") == "https://web.telegram.org/k/#@FOREXUSAMASTER1"


def test_add_and_remove_telegram_channel():
    config = _config()
    added = add_telegram_channel(config, "#-1303328644", name="PROFIT HACKER")
    assert added.url == "https://web.telegram.org/k/#-1303328644"
    assert len(config.telegram_signals.channels) == 2
    removed = remove_telegram_channel(config, added.url)
    assert removed.name == "PROFIT HACKER"
    assert len(config.telegram_signals.channels) == 1


def test_add_duplicate_channel_raises():
    config = _config()
    with pytest.raises(ValueError, match="already exists"):
        add_telegram_channel(config, "https://web.telegram.org/k/#@FOREXUSAMASTER1")


def test_update_telegram_channel_enabled():
    config = _config()
    channel = update_telegram_channel(
        config,
        "https://web.telegram.org/k/#@FOREXUSAMASTER1",
        enabled=False,
    )
    assert channel.enabled is False
