import math
from datetime import date

from app.risk_metrics import annualised_sharpe, daily_returns, product_sharpe


def _trade(day: str, pnl: float) -> dict[str, object]:
    return {"close_time": f"{day}T12:00:00", "net_profit": pnl}


def test_daily_returns_cover_every_calendar_day_and_compound_balance() -> None:
    returns = daily_returns([_trade("2026-01-01", 100.0), _trade("2026-01-03", -101.0)],
                            date(2026, 1, 1), date(2026, 1, 3), 10_000.0)
    assert returns == [0.01, 0.0, -0.01]


def test_trades_outside_window_are_ignored() -> None:
    assert daily_returns([_trade("2025-12-31", 500.0)], date(2026, 1, 1), date(2026, 1, 2)) == [0.0, 0.0]


def test_annualised_sharpe_matches_hand_calculation() -> None:
    trades = [_trade(f"2026-01-{d:02d}", 50.0 if d % 3 else -40.0) for d in range(1, 31)]
    returns = daily_returns(trades, date(2026, 1, 1), date(2026, 1, 30))
    mean = sum(returns) / len(returns)
    sd = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
    assert annualised_sharpe(trades, date(2026, 1, 1), date(2026, 1, 30)) == round(mean / sd * math.sqrt(365), 2)


def test_too_few_trades_or_days_returns_none() -> None:
    assert annualised_sharpe([_trade("2026-01-01", 1.0)] * 5, date(2026, 1, 1), date(2026, 3, 1)) is None
    assert annualised_sharpe([_trade("2026-01-01", 1.0)] * 20, date(2026, 1, 1), date(2026, 1, 10)) is None


def test_every_cached_ea_has_an_annualised_sharpe_for_three_years() -> None:
    from app.catalog import get_sellable_catalog
    from app.evidence_cache import load_product_summary
    from app.main import _recommended_mode

    missing = []
    for product in get_sellable_catalog():
        mode = _recommended_mode(product)
        summary = load_product_summary(product.slug, mode, "3y")
        if summary and product_sharpe(product.slug, mode, "3y", summary.get("stats")) is None:
            missing.append(product.slug)
    assert missing == []
