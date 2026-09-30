"""Rolling Sharpe trend, streak distribution and their API / card rendering."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.risk_visuals import (MIN_TRADES_IN_WINDOW, ROLLING_WINDOW_DAYS, SAMPLE_EVERY_DAYS, rolling_sharpe,
                              sharpe_sparkline_svg, streak_bars_svg, streak_distribution)

client = TestClient(app)


def trade(day: date, pnl: float, number: int = 0) -> dict:
    return {"close_time": f"{day.isoformat()}T12:00:00", "net_profit": pnl, "number": number}


def test_streaks_count_runs_and_break_even_ends_a_streak():
    d = date(2026, 1, 1)
    pnls = [10, 5, -3, -2, -1, 0, 4, -1, 8, 9, 7]  # W2, L3, (BE), W1, L1, W3
    s = streak_distribution([trade(d + timedelta(days=i), p, i) for i, p in enumerate(pnls)])
    assert s["wins"] == {"1": 1, "2": 1, "3": 1}
    assert s["losses"] == {"1": 1, "3": 1}
    assert (s["max_win_streak"], s["max_loss_streak"]) == (3, 3)
    assert s["avg_win_streak"] == 2.0 and s["avg_loss_streak"] == 2.0
    assert s["timeline"] == [1, 2, -1, -2, -3, 0, 1, -1, 1, 2, 3]


def test_streaks_sort_by_close_time_not_input_order():
    d = date(2026, 1, 1)
    s = streak_distribution([trade(d + timedelta(days=2), 1, 3), trade(d, -1, 1), trade(d + timedelta(days=1), 1, 2)])
    assert s["losses"] == {"1": 1} and s["wins"] == {"2": 1}


def test_rolling_sharpe_samples_weekly_and_needs_enough_trades():
    start = date(2025, 1, 1)
    end = start + timedelta(days=ROLLING_WINDOW_DAYS + 3 * SAMPLE_EVERY_DAYS - 1)
    trades = [trade(start + timedelta(days=i), 20 if i % 3 else -10) for i in range(0, (end - start).days + 1, 2)]
    points = rolling_sharpe(trades, start, end)
    assert len(points) == 4
    assert points[0]["date"] == (start + timedelta(days=ROLLING_WINDOW_DAYS - 1)).isoformat()
    assert all(p["sharpe"] is not None and p["sharpe"] > 0 for p in points)
    sparse = rolling_sharpe(trades[:MIN_TRADES_IN_WINDOW - 1], start, end)
    assert all(p["sharpe"] is None for p in sparse)


def test_inline_svgs_are_empty_without_data_and_escape_titles():
    assert sharpe_sparkline_svg([{"sharpe": 1.0}]) == ""
    assert streak_bars_svg({"wins": {}, "losses": {}}) == ""
    svg = sharpe_sparkline_svg([{"sharpe": -0.5}, {"sharpe": 1.2}, {"sharpe": 0.8}])
    assert svg.startswith("<svg") and "latest 0.80" in svg and "<script" not in svg
    bars = streak_bars_svg({"wins": {"1": 9, "12": 1}, "losses": {"1": 4}, "max_win_streak": 12, "max_loss_streak": 1})
    assert bars.count("<rect") == 16  # 8 win + 8 loss slots, 12-long streak folded into the 8+ slot


def test_risk_series_api_matches_headline_sharpe():
    res = client.get("/api/evidence/xau-slow-trend/risk-series", params={"mode": "standard", "period": "3y"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["window_days"] == ROLLING_WINDOW_DAYS and data["rolling_sharpe"]
    detail = client.get("/api/evidence/xau-slow-trend/series", params={"mode": "standard", "period": "3y"}).json()
    assert data["sharpe_annualized"] == pytest.approx(detail["stats"]["sharpe_annualized"])
    assert data["streaks"]["max_win_streak"] >= 1


@pytest.mark.parametrize("params", [{"mode": "bogus"}, {"period": "10y"}])
def test_risk_series_api_rejects_bad_parameters(params):
    assert client.get("/api/evidence/xau-slow-trend/risk-series", params=params).status_code == 422


def test_risk_series_api_unknown_ea_is_404():
    assert client.get("/api/evidence/no-such-ea/risk-series").status_code == 404


def test_catalogue_and_detail_render_risk_visuals():
    page = client.get("/eas?period=3y").text
    assert 'aria-label="Rolling 90-day Sharpe' in page and 'aria-label="Streak lengths' in page
    detail = client.get("/eas/xau-slow-trend?period=3y").text
    assert "data-risk-visuals" in detail and "ea-metrics.js" in detail
