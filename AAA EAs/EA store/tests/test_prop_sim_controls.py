"""Daily equity stop / profit close, fixed-$ presets and firm logos."""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import _prop_limiter, app
from app.prop_sim.ledger import Guards, LedgerTrade, Selection, build_features
from app.prop_sim.rules import get_programme

client = TestClient(app)


def T(day, hour, dur_h, r):  # noqa: N802
    opened = datetime(2026, 1, day, hour)
    return LedgerTrade("a", "XAUUSD", opened, opened + timedelta(hours=dur_h), r, 0.10, 100.0)


def run(trades, **guards):
    return build_features({"a": tuple(trades)}, [Selection("a", 1.0)], 10_000, Guards(**guards),
                          date(2026, 1, 1), date(2026, 1, 10))


def test_equity_stop_caps_the_crossing_trade_flattens_others_and_blocks_the_day():
    # Day 5: -1.5% closes, a long trade is open, then another -1% closes (crosses -2%), then a +3% entry is attempted.
    trades = [T(5, 8, 1, -1.5), T(5, 9, 30, 2.0), T(5, 10, 1, -1.0), T(5, 12, 1, 3.0), T(6, 8, 1, 1.0)]
    f = run(trades, equity_stop_pct=2.0)
    assert f.pnl[4] == pytest.approx(-0.02)  # capped at the stop level
    assert f.skipped["closed flat by daily equity stop"] == 1  # the open long, its later +2% is dropped
    assert f.skipped["daily equity stop"] == 1  # the 12:00 entry
    assert f.pnl[5] == pytest.approx(0.01)  # next day trades normally


def test_profit_close_locks_the_day_at_the_target():
    trades = [T(5, 8, 1, 3.0), T(5, 9, 1, 2.0), T(5, 12, 1, -1.0)]
    f = run(trades, profit_close_pct=4.0)
    assert f.pnl[4] == pytest.approx(0.04)
    assert f.skipped == {"daily profit close": 1}


def test_changed_gold_targets_hide_stale_ftmo_package_forecasts():
    presets = {p["id"]: p for p in client.get("/api/prop-sim/catalog").json()["presets"]}
    assert 'ftmo13' not in presets and 'ftmo13-controls' not in presets


def test_run_accepts_daily_controls():
    _prop_limiter._hits.clear()
    body = {"programme_id": 'ftmo-2step-swing', "account_size": 10000,
            "eas": [{'slug':'xau-trend-progression','risk_pct':1.0}, {'slug':'xau-slow-trend','risk_pct':1.0}],
            "paths": 200, "equity_stop_pct":0.05, "profit_close_pct":0.05}
    res = client.post("/api/prop-sim/run", json=body)
    assert res.status_code == 200, res.text
    assert any(k.startswith("closed flat by") or k.startswith("daily") for k in res.json()["stats"]["skipped"])


def test_every_registered_firm_has_a_local_logo():
    for pid in ("ftmo-2step-swing", "fundednext-stellar-2step", "the5ers-high-stakes", "e8-one-4pct",
                "fxify-two-phase", "gft-2step-standard", "fundingpips-2step", "blueberry-prime-2step"):
        url = get_programme(pid).logo_url
        assert url and url.startswith("/static/prop-firms/")
        assert client.get(url).status_code == 200
