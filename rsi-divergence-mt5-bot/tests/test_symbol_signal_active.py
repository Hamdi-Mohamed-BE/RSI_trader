from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, RiskConfig, SymbolConfig, TelegramChannelConfig, TelegramSignalsConfig
from rsi_divergence_bot.telegram_signals import ParsedTelegramSignal, TelegramSignalsBot


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        bot=BotRuntimeConfig(dry_run=True, state_file=str(tmp_path / "state.json")),
        risk=RiskConfig(default_forex_lot=0.25),
        telegram_signals=TelegramSignalsConfig(
            channels=[TelegramChannelConfig(name="Test", url="https://t.me/test", enabled=True)],
        ),
        symbols=[
            SymbolConfig(
                symbol="XAUUSD-VIP",
                name="Gold",
                lot_per_leg=0.08,
                enabled=False,
                signal_active=False,
            ),
        ],
    )


class SymbolSignalActiveTests(unittest.TestCase):
    def test_place_skips_when_signal_active_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = _config(Path(tmp_dir))
        client = MagicMock()
        client.tick.return_value = {"bid": 2500.0, "ask": 2500.5}
        logger = MagicMock()
        from rsi_divergence_bot.state import StateStore

        bot = TelegramSignalsBot(config, client, StateStore(config.bot.state_file), logger)
        parsed = ParsedTelegramSignal(
            symbol="XAUUSD",
            action="buy",
            stop_loss=2490.0,
            tps=[2510.0],
        )
        channel = config.telegram_signals.channels[0]
        result = bot._place_parsed_signal(parsed, source_id="msg-1", channel=channel)
        self.assertEqual(result["status"], "signal_inactive")
        client.send_market.assert_not_called()


if __name__ == "__main__":
    unittest.main()
