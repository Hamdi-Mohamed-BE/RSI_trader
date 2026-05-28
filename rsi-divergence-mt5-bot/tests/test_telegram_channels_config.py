from __future__ import annotations

import unittest

from rsi_divergence_bot.config import (
    AppConfig,
    SymbolConfig,
    TelegramChannelConfig,
    TelegramSignalsConfig,
    add_telegram_channel,
    normalize_telegram_channel_url,
    remove_telegram_channel,
    update_telegram_channel,
    update_telegram_ignore_open_trades,
    update_telegram_settings,
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


class TelegramChannelsConfigTests(unittest.TestCase):
    def test_normalize_telegram_channel_url_accepts_username(self) -> None:
        self.assertEqual(
            normalize_telegram_channel_url("@FOREXUSAMASTER1"),
            "https://web.telegram.org/k/#@FOREXUSAMASTER1",
        )

    def test_add_and_remove_telegram_channel(self) -> None:
        config = _config()
        added = add_telegram_channel(config, "#-1303328644", name="PROFIT HACKER")
        self.assertEqual(added.url, "https://web.telegram.org/k/#-1303328644")
        self.assertEqual(len(config.telegram_signals.channels), 2)
        removed = remove_telegram_channel(config, added.url)
        self.assertEqual(removed.name, "PROFIT HACKER")
        self.assertEqual(len(config.telegram_signals.channels), 1)

    def test_add_duplicate_channel_raises(self) -> None:
        config = _config()
        with self.assertRaisesRegex(ValueError, "already exists"):
            add_telegram_channel(config, "https://web.telegram.org/k/#@FOREXUSAMASTER1")

    def test_update_telegram_channel_enabled(self) -> None:
        config = _config()
        channel = update_telegram_channel(
            config,
            "https://web.telegram.org/k/#@FOREXUSAMASTER1",
            enabled=False,
        )
        self.assertFalse(channel.enabled)

    def test_update_telegram_ignore_open_trades(self) -> None:
        config = _config()
        self.assertTrue(config.telegram_signals.ignore_open_symbol_trades)
        update_telegram_ignore_open_trades(config, ignore_open=False)
        self.assertFalse(config.telegram_signals.ignore_open_symbol_trades)

    def test_update_telegram_settings(self) -> None:
        config = _config()
        self.assertTrue(config.telegram_signals.protect_tp)
        update_telegram_settings(config, ignore_open_symbol_trades=False, protect_tp=False)
        self.assertFalse(config.telegram_signals.ignore_open_symbol_trades)
        self.assertFalse(config.telegram_signals.protect_tp)


if __name__ == "__main__":
    unittest.main()
