from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from rsi_divergence_bot.box_theory import (
    attach_previous_day_box,
    box_zone,
    is_aggressive_bear,
    is_john_wick_hammer,
    resolve_box_theory_params,
)
from rsi_divergence_bot.config import AppConfig, BotRuntimeConfig, BoxTheoryConfig, RiskConfig, SymbolConfig
from rsi_divergence_bot.signal_engine import generate_signals
from rsi_divergence_bot.strategy_modes import CANONICAL_STRATEGIES, is_box_theory_strategy


def _bar(day: int, hour: int, minute: int, o: float, h: float, low: float, c: float) -> dict:
    return {
        "time": datetime(2024, 1, day, hour, minute, tzinfo=timezone.utc),
        "open": o,
        "high": h,
        "low": low,
        "close": c,
    }


def _config() -> AppConfig:
    return AppConfig(
        bot=BotRuntimeConfig(strategy="box_theory"),  # type: ignore[arg-type]
        risk=RiskConfig(),
        box_theory=BoxTheoryConfig(
            zone_edge_fraction=0.25,
            aggressive_body_frac=0.55,
            aggressive_range_frac=0.15,
            wick_body_ratio_min=2.0,
            max_body_range_ratio=0.35,
        ),
        symbols=[SymbolConfig(symbol="ES", name="S&P", lot_per_leg=0.1, sessions=[])],
    )


class BoxTheoryTests(unittest.TestCase):
    def test_strategy_is_selectable(self) -> None:
        self.assertIn("box_theory", CANONICAL_STRATEGIES)
        self.assertTrue(is_box_theory_strategy("box_theory"))

    def test_box_zone_edges(self) -> None:
        self.assertEqual(box_zone(100.0, 100.0, 200.0, 0.25), "bottom")
        self.assertEqual(box_zone(190.0, 100.0, 200.0, 0.25), "top")
        self.assertEqual(box_zone(150.0, 100.0, 200.0, 0.25), "middle")

    def test_buy_trap_sequence(self) -> None:
        rows = []
        for hour in range(8):
            rows.append(_bar(1, hour, 0, 150.0, 151.0, 149.0, 150.0))
        for hour in range(8, 16):
            rows.append(_bar(2, hour - 8, 0, 102.0, 103.0, 101.0, 102.0))
        rows.extend(
            [
                _bar(2, 8, 0, 102.0, 102.5, 100.0, 100.5),
                _bar(2, 8, 15, 100.5, 101.0, 99.0, 100.8),
                _bar(2, 8, 30, 100.8, 102.0, 100.7, 101.5),
            ]
        )
        df = pd.DataFrame(rows)
        config = _config()
        params = resolve_box_theory_params(config)
        frame = attach_previous_day_box(df)
        aggressive = frame.iloc[-3]
        hammer = frame.iloc[-2]
        box_low = float(aggressive.box_low)
        box_high = float(aggressive.box_high)
        box_height = box_high - box_low
        self.assertEqual(box_zone(float(aggressive.close), box_low, box_high, 0.25), "bottom")
        self.assertTrue(is_aggressive_bear(aggressive, box_height, params))
        self.assertTrue(is_john_wick_hammer(hammer, params))

        signals = generate_signals(config, df, config.symbols[0], config.risk)
        self.assertTrue(signals)
        self.assertEqual(signals[-1].side, "buy")
        self.assertEqual(len(signals[-1].tps), 1)
        self.assertAlmostEqual(signals[-1].tps[0], box_high)


if __name__ == "__main__":
    unittest.main()
