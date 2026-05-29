import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from rsi_divergence_bot.config import ForexTradeConfig, SymbolConfig, load_config, update_forex_trade_settings
from rsi_divergence_bot.forex_trade import (
    _long_condition,
    _price_levels,
    generate_signals,
    prepare_frame,
    symbol_allowed,
)


def _symbol() -> SymbolConfig:
    return SymbolConfig(symbol="EURUSD-VIP", name="EURUSD", lot_per_leg=0.25, timeframe="H1")


class ForexTradeTests(unittest.TestCase):
    def test_symbol_allowed_matches_name_and_key(self) -> None:
        cfg = ForexTradeConfig(symbol_keys=["EURUSD", "GBPUSD"])
        self.assertTrue(symbol_allowed(_symbol(), cfg))
        self.assertFalse(
            symbol_allowed(
                SymbolConfig(symbol="XAUUSD-VIP", name="Gold", lot_per_leg=0.01, timeframe="H1"),
                cfg,
            )
        )

    def test_prepare_frame_adds_rsi(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = []
        price = 1.1000
        for index in range(40):
            price += 0.0001
            rows.append(
                {
                    "time": start + timedelta(hours=index),
                    "open": price - 0.0001,
                    "high": price + 0.0002,
                    "low": price - 0.0002,
                    "close": price,
                    "tick_volume": 100,
                }
            )
        frame = prepare_frame(pd.DataFrame(rows), ForexTradeConfig())
        self.assertIn("rsi", frame.columns)

    def test_price_levels_use_percent_stops(self) -> None:
        cfg = ForexTradeConfig(stop_loss_pct=0.05, take_profit_pct=0.125)
        sl, tp = _price_levels(1.0, "buy", cfg)
        self.assertAlmostEqual(sl, 0.95)
        self.assertAlmostEqual(tp, 1.125)

    def test_long_condition_on_rsi_cross(self) -> None:
        cfg = ForexTradeConfig(rsi_long_entry=30.0)
        frame = pd.DataFrame(
            {
                "close": [1.0, 1.0],
                "rsi": [31.0, 28.0],
            }
        )
        self.assertTrue(_long_condition(frame, 1, cfg))
        self.assertFalse(_long_condition(frame, 0, cfg))

    def test_generate_signals_returns_forex_algorithm(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = []
        price = 1.0800
        for index in range(320):
            drift = -0.0004 if index % 60 < 30 else 0.0003
            price = max(0.5, price + drift)
            rows.append(
                {
                    "time": start + timedelta(hours=index),
                    "open": price - 0.0001,
                    "high": price + 0.0004,
                    "low": price - 0.0004,
                    "close": price,
                    "tick_volume": 100,
                }
            )
        signals = generate_signals(pd.DataFrame(rows), _symbol(), None, ForexTradeConfig())
        if signals:
            self.assertEqual(signals[0].algorithm, "forex_trade")
            self.assertEqual(len(signals[0].tps), 1)

    def test_update_forex_trade_settings_roundtrip(self) -> None:
        example = load_config(
            __import__("pathlib").Path(__file__).resolve().parents[1] / "config.example.yaml"
        )
        update_forex_trade_settings(
            example,
            timeframe="H1",
            rsi_long_entry=30,
            rsi_short_entry=70,
            rsi_long_exit=50,
            rsi_short_exit=50,
            stop_loss_pct=0.05,
            take_profit_pct=0.125,
            symbol_keys=["EURUSD"],
        )
        cfg = example.bot.forex_trade
        self.assertEqual(cfg.rsi_long_entry, 30)
        self.assertEqual(cfg.rsi_short_entry, 70)
        self.assertEqual(cfg.stop_loss_pct, 0.05)
        self.assertEqual(cfg.take_profit_pct, 0.125)


if __name__ == "__main__":
    unittest.main()
