from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from rsi_divergence_bot.config import AppConfig, MT5Config, SymbolConfig
from rsi_divergence_bot.enitrend import EniTrendBacktestSettings, run_enitrend_backtest


class FakeMT5Client:
    def __init__(self, rates: pd.DataFrame) -> None:
        self.rates = rates
        self.calls: list[tuple[str, str]] = []

    def initialize(self) -> None:
        return None

    def rates_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        self.calls.append((symbol, timeframe))
        start_ts = pd.Timestamp(start).tz_convert("UTC")
        end_ts = pd.Timestamp(end).tz_convert("UTC")
        window = self.rates[(self.rates["time"] >= start_ts) & (self.rates["time"] <= end_ts)]
        return window.reset_index(drop=True)

    def money_for_distance(self, symbol: str, volume: float, price_distance: float) -> float:
        return float(price_distance) * float(volume)


def _sample_rates() -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    prices: list[float] = []
    for index in range(240):
        if index < 60:
            price += 0.02
        elif index < 120:
            price += 1.2
        elif index < 170:
            price += 0.05
        elif index < 220:
            price -= 1.4
        else:
            price -= 0.03
        prices.append(price)

    rows: list[dict] = []
    previous_close = 100.0
    for index, close in enumerate(prices):
        opened = previous_close
        rows.append(
            {
                "time": pd.Timestamp(start + timedelta(minutes=15 * index)),
                "open": opened,
                "high": max(opened, close) + 0.25,
                "low": min(opened, close) - 0.25,
                "close": close,
            }
        )
        previous_close = close
    return pd.DataFrame(rows)


def test_enitrend_backtest_runs_as_standalone_subsystem() -> None:
    config = AppConfig(
        mt5=MT5Config(is_demo=True),
        symbols=[
            SymbolConfig(
                symbol="TEST",
                name="Synthetic trend test",
                demo_symbol="TEST.DEMO",
                live_symbol="TEST.LIVE",
                lot_per_leg=1.0,
            )
        ],
    )
    settings = EniTrendBacktestSettings(
        symbols=("TEST",),
        execution_timeframe="M15",
        higher_timeframe="H1",
        volatility_lookback=8,
        trend_smoothing=5,
        volatility_multiplier=1.6,
        use_higher_timeframe_filter=False,
        volume=1.0,
        stop_loss_mode="off",
        take_profit_mode="off",
    )
    client = FakeMT5Client(_sample_rates())

    result = run_enitrend_backtest(
        client,
        config,
        settings,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 3, 12, tzinfo=timezone.utc),
        starting_balance=1000.0,
    )

    assert result["subsystem"] == "dynamic_volatility_momentum"
    assert result["settings"]["execution_timeframe"] == "M15"
    assert result["total_pnl"] > 0
    assert client.calls == [("TEST.DEMO", "M15")]

    symbol = result["symbols"][0]
    assert symbol["symbol"] == "TEST"
    assert symbol["mt5_symbol"] == "TEST.DEMO"
    assert symbol["raw_signals"] == 2
    assert symbol["aligned_signals"] == 2
    assert symbol["trades"] == 2
    assert [trade["exit_kind"] for trade in symbol["trade_logs"]] == ["trend_flip", "period_end"]
    assert result["daily_performance"]
