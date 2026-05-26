import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from rsi_divergence_bot.config import SilverOptimizedConfig, SymbolConfig
from rsi_divergence_bot.silver_optimized import generate_signals, resolve_params, resolve_preset


def _symbol() -> SymbolConfig:
    return SymbolConfig(symbol="XAGUSD-VIP", name="Silver", lot_per_leg=0.01, timeframe="H1")


class SilverOptimizedTests(unittest.TestCase):
    def test_resolve_preset_auto_detects_silver(self) -> None:
        cfg = SilverOptimizedConfig(preset="auto")
        self.assertEqual(resolve_preset(_symbol(), cfg), "XAGUSD")

    def test_xag_preset_params(self) -> None:
        params = resolve_params(_symbol(), SilverOptimizedConfig(preset="xagusd"))
        self.assertEqual(params.stop_atr, 2.4)
        self.assertEqual(params.tp_atr, 3.8)
        self.assertEqual(params.trail_atr, 1.8)

    def test_generate_signals_returns_silver_algorithm(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = []
        price = 24.0
        for index in range(320):
            drift = 0.02 if index % 40 < 20 else -0.015
            price = max(1.0, price + drift)
            rows.append(
                {
                    "time": start + timedelta(hours=index),
                    "open": price - 0.01,
                    "high": price + 0.05,
                    "low": price - 0.05,
                    "close": price,
                    "tick_volume": 100,
                }
            )
        df = pd.DataFrame(rows)
        cfg = SilverOptimizedConfig(
            preset="xagusd",
            use_vol_filter=False,
            custom_htf_len=20,
        )
        signals = generate_signals(df, _symbol(), None, cfg)
        if signals:
            self.assertEqual(signals[0].algorithm, "silver_optimized")
            self.assertEqual(len(signals[0].tps), 1)
            self.assertIsNotNone(signals[0].trail_atr_mult)


if __name__ == "__main__":
    unittest.main()
