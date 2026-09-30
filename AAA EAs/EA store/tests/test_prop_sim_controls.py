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


def test_presets_default_to_fixed_50_usd_with_daily_controls():
    presets = {p["id"]: p for p in client.get("/api/prop-sim/catalog").json()["presets"]}
    controls = presets["ftmo13-controls"]
    assert controls["sizing"] == "fixed_usd" and controls["risk_usd"] == 50 and len(controls["eas"]) == 14
    assert controls["guards"] == {"equity_stop_pct": 2.0, "profit_close_pct": 4.0}
    assert "NOT installed" in controls["note"]
    assert presets["ftmo13"]["guards"] == {}


def test_run_accepts_daily_controls():
    _prop_limiter._hits.clear()
    preset = next(p for p in client.get("/api/prop-sim/catalog").json()["presets"] if p["id"] == "ftmo13-controls")
    body = {"programme_id": preset["programme_id"], "account_size": 10000, "eas": preset["eas"], "paths": 200,
            **preset["guards"]}
    res = client.post("/api/prop-sim/run", json=body)
    assert res.status_code == 200, res.text
    assert any(k.startswith("closed flat by") or k.startswith("daily") for k in res.json()["stats"]["skipped"])


def test_every_registered_firm_has_a_local_logo():
    for pid in ("ftmo-2step-swing", "fundednext-stellar-2step", "the5ers-high-stakes", "e8-one-4pct",
                "fxify-two-phase", "gft-2step-standard", "fundingpips-2step", "blueberry-prime-2step"):
        url = get_programme(pid).logo_url
        assert url and url.startswith("/static/prop-firms/")
        assert client.get(url).status_code == 200
