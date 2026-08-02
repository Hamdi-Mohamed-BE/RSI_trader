from types import SimpleNamespace

from ema3_backtest.timeframe_compare import symbol_score


def test_us100_alias_prefers_nasdaq_future_over_unrelated_stock() -> None:
    future = SimpleNamespace(
        name="NAS100U6", description="E-mini Nasdaq Future", trade_mode=4, visible=True
    )
    stock = SimpleNamespace(
        name="NDAQ.OQ", description="Nasdaq Inc", trade_mode=4, visible=True
    )
    assert symbol_score(future, "US100") > symbol_score(stock, "US100")
