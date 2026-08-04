from types import SimpleNamespace

from ema3_backtest.timeframe_compare import (
    SCALPING_TIMEFRAMES,
    TIMEFRAMES,
    confidence_requirements,
    exit_grid,
    pivot_distances,
    signal_variants,
    symbol_score,
)


def test_us100_alias_prefers_nasdaq_future_over_unrelated_stock() -> None:
    future = SimpleNamespace(
        name="NAS100U6", description="E-mini Nasdaq Future", trade_mode=4, visible=True
    )
    stock = SimpleNamespace(
        name="NDAQ.OQ", description="Nasdaq Inc", trade_mode=4, visible=True
    )
    assert symbol_score(future, "US100") > symbol_score(stock, "US100")


def test_scalping_timeframes_are_available() -> None:
    assert SCALPING_TIMEFRAMES == {"M1", "M5", "M15"}
    assert SCALPING_TIMEFRAMES.issubset(TIMEFRAMES)


def test_scalping_grid_respects_1_7r_cap() -> None:
    configs = exit_grid("M5")
    assert configs
    for config in configs:
        if config.mode == "fixed":
            assert config.target_r is not None and config.target_r <= 1.7
        else:
            assert config.target_cap_r == 1.7


def test_scalping_search_has_local_pivot_and_trend_variants() -> None:
    assert pivot_distances("M1") == (4, 6, 8)
    assert pivot_distances("M15") == (4, 6, 8)
    assert ("none", 1) in signal_variants("M5")
    assert ("ema200_slope", 6) in signal_variants("M5")
    assert confidence_requirements("M1", 30) == (120, 30)
