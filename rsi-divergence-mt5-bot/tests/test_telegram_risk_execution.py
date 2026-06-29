from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from rsi_divergence_bot.config import AppConfig, SymbolConfig, TelegramChannelConfig, TelegramSignalsConfig
from rsi_divergence_bot.mt5_client import MT5Client
from rsi_divergence_bot.state import StateStore
from rsi_divergence_bot.symbol_registry import ensure_symbol_for_signal_copy
from rsi_divergence_bot.telegram_signals import ParsedTelegramSignal, TelegramSignalsBot
from rsi_divergence_bot.trader import TradeExecutor


def test_volume_for_risk_uses_five_percent_balance_and_floors_volume() -> None:
    client = MT5Client.__new__(MT5Client)
    client.account = lambda: {"balance": 300.0}
    client.money_for_distance = lambda _symbol, volume, _distance: 1000.0 * volume
    client.symbol_info = lambda _symbol: {"volume_step": 0.01, "volume_min": 0.01, "volume_max": 100.0}
    client.normalize_volume = lambda _symbol, volume: round(volume, 2)

    result = client.volume_for_risk("CADJPYm", 114.10, 114.26, 5.0)

    assert result["risk_money"] == 15.0
    assert result["raw_volume"] == 0.015
    assert result["volume"] == 0.01
    assert round(float(result["actual_risk_percent"]), 3) == 3.333


class DiscoveryClient:
    def symbol_info(self, symbol: str):
        return {"name": symbol} if symbol == "CADJPYm" else None

    def tick(self, symbol: str):
        return {"bid": 114.10, "ask": 114.12} if symbol == "CADJPYm" else None

    def symbols(self):
        return [SimpleNamespace(name="CADJPYm")]


def test_signal_registry_discovers_and_persists_actual_m_suffix() -> None:
    config = AppConfig(
        telegram_signals=TelegramSignalsConfig(auto_discover_symbols=True),
        symbols=[],
    )

    symbol_cfg, created, _persisted = ensure_symbol_for_signal_copy(
        "CADJPY",
        config,
        DiscoveryClient(),
        persist=False,
    )

    assert created is True
    assert symbol_cfg is not None
    assert symbol_cfg.demo_symbol == "CADJPYm"


def test_telegram_market_copy_uses_one_full_order_and_risk_volume() -> None:
    symbol_cfg = SymbolConfig(
        symbol="CADJPY",
        name="CADJPY",
        demo_symbol="CADJPYm",
        live_symbol="CADJPYm",
        lot_per_leg=0.25,
    )
    config = AppConfig(
        telegram_signals=TelegramSignalsConfig(
            execution_mode="full",
            use_risk_based_lot=True,
            risk_percent=5.0,
        ),
        symbols=[symbol_cfg],
    )
    config.bot.dry_run = False
    client = MagicMock()
    client.tick.return_value = {"bid": 114.10, "ask": 114.12}
    client.volume_for_risk.return_value = {
        "balance": 300.0,
        "risk_percent": 5.0,
        "risk_money": 15.0,
        "raw_volume": 0.023,
        "volume": 0.02,
        "actual_risk": 13.0,
        "actual_risk_percent": 4.333,
        "used_minimum_lot": False,
    }
    with tempfile.TemporaryDirectory() as tmp:
        state = StateStore(str(Path(tmp) / "state.json"))
        bot = TelegramSignalsBot(config, client, state, logging.getLogger("telegram-test"))
        bot.executor = MagicMock()
        bot.executor.place_market_setup.return_value = {
            "status": "placed",
            "tickets": [123],
            "ticket": 123,
            "entry_price": 114.10,
        }
        parsed = ParsedTelegramSignal(
            symbol="CADJPY",
            action="sell",
            stop_loss=114.26,
            tps=[113.90, 113.76, 113.60],
            confidence=1.0,
        )
        channel = TelegramChannelConfig(name="Profit Hacker", url="https://web.telegram.org/k/#-1303328644")

        with patch(
            "rsi_divergence_bot.telegram_signals.ensure_symbol_for_signal_copy",
            return_value=(symbol_cfg, False, False),
        ):
            result = bot._place_parsed_signal(
                parsed,
                source_id="29404",
                channel=channel,
                message_age_seconds=10,
            )

    assert result["status"] == "placed"
    kwargs = bot.executor.place_market_setup.call_args.kwargs
    assert kwargs["execution_mode"] == "full"
    assert kwargs["lot_per_leg"] == 0.02
    assert kwargs["tps"] == [113.90, 113.76, 113.60]


def test_full_position_moves_to_break_even_at_tp1_then_tp1_at_tp2() -> None:
    config = AppConfig(symbols=[SymbolConfig(symbol="CADJPY", name="CADJPY", lot_per_leg=0.01)])
    config.bot.dry_run = False
    client = MagicMock()
    client.normalize_price.side_effect = lambda _symbol, price: float(price)
    executor = TradeExecutor(config, client, MagicMock(), MagicMock())
    position = {"ticket": 123, "price_open": 114.10, "sl": 114.26, "tp": 113.60, "type": 1}
    setup = {
        "setup_id": "telegram:29404",
        "symbol": "CADJPYm",
        "side": "sell",
        "execution_mode": "full",
        "source": "telegram_signals",
        "tickets": [123],
        "tps": [113.90, 113.76, 113.60],
        "sl": 114.26,
        "moved_to_tp": 0,
    }

    client.tick.return_value = {"bid": 113.88, "ask": 113.89}
    executor._manage_full_setup(setup, {123: position}, True)
    client.update_position_sl.assert_called_with(123, "CADJPYm", 114.10, 113.60)
    assert setup["moved_to_tp"] == 1

    client.update_position_sl.reset_mock()
    position["sl"] = 114.10
    client.tick.return_value = {"bid": 113.74, "ask": 113.75}
    executor._manage_full_setup(setup, {123: position}, True)
    client.update_position_sl.assert_called_with(123, "CADJPYm", 113.90, 113.60)
    assert setup["moved_to_tp"] == 2


def test_pending_telegram_full_mode_places_only_final_tp_order() -> None:
    config = AppConfig(symbols=[SymbolConfig(symbol="CADJPY", name="CADJPY", lot_per_leg=0.01)])
    client = MagicMock()
    client.tick.return_value = {"bid": 114.10, "ask": 114.12}
    client.TRADE_DONE = 10009
    client.TRADE_PLACED = 10008
    client.send_pending.return_value = SimpleNamespace(retcode=10008, order=456, deal=0)
    state = MagicMock()
    executor = TradeExecutor(config, client, state, MagicMock())

    result = executor.place_pending_setup(
        setup_id="telegram:pending",
        symbol="CADJPYm",
        market_key="CADJPY",
        order_kind="sell_stop",
        side="sell",
        entry_price=114.00,
        sl=114.26,
        tps=[113.90, 113.76, 113.60],
        lot_per_leg=0.02,
        execution_mode="full",
        extra_setup={"source": "telegram_signals"},
    )

    assert result["status"] == "placed"
    assert result["legs"] == 1
    assert client.send_pending.call_count == 1
    assert client.send_pending.call_args.args[5] == 113.60
    saved_setup = state.add_setup.call_args.args[0]
    assert saved_setup["execution_mode"] == "pending_full"
    assert saved_setup["tps"] == [113.90, 113.76, 113.60]
