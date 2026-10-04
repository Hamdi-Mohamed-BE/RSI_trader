"""Prop challenge simulator: rules registry, engine thresholds, ledger guards, compatibility and public API."""
from dataclasses import replace
from datetime import date, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import _prop_limiter, app
from app.prop_sim.engine import SimConfig, sample_indices, simulate, summarise
from app.prop_sim.ledger import EaProfile, Features, Guards, LedgerTrade, Selection, build_features
from app.prop_sim.rules import Payout, Phase, compatibility, get_programme, programmes

client = TestClient(app)


def feats(pnl, low=None, opened=None):
    pnl = np.asarray(pnl, dtype=float)
    low = np.minimum(np.asarray(low if low is not None else np.minimum(pnl, 0), dtype=float), 0)
    return Features(start=date(2026, 1, 1), days=pnl.size, pnl=pnl, low_closed=low, low_envelope=low,
                    opened=np.asarray(opened if opened is not None else (pnl != 0), dtype=float))


def run(programme, features, horizon=None, fee=100.0, size=10_000):
    cfg = SimConfig(account_size=size, fee=fee, horizon_days=horizon or features.days, method="rolling")
    idx = sample_indices(features.days, cfg)[:1]  # one deterministic path starting on day 0
    out = simulate(programme, features, features, cfg, idx, "closed")
    return out, summarise(out, cfg, cfg.horizon_days)


def base_programme(**changes):
    p = get_programme("ftmo-2step-swing")
    return replace(p, **changes)


# ---- registry --------------------------------------------------------------------------------------------------
def test_registry_has_many_mt5_programmes_with_sources():
    progs = programmes()
    assert len(progs) >= 14
    assert len({p.firm for p in progs.values()}) >= 8
    for p in progs.values():
        assert p.mt5 and p.verification["sources"] and p.verification["checked"]
        assert p.max_loss_pct > 0 and p.payout.split_pct > 0


def test_ftmo_rules_match_official_objectives():
    p = get_programme("ftmo-2step-standard")
    assert [(ph.target_pct, ph.min_trading_days) for ph in p.phases] == [(10, 4), (5, 4)]
    assert (p.daily_loss_pct, p.max_loss_pct, p.max_loss_type) == (5, 10, "static")
    assert p.verification["status"] == "official"


# ---- engine ----------------------------------------------------------------------------------------------------
def test_steady_profit_passes_both_phases_after_minimum_days_and_handover():
    p = base_programme(handover_days=(2, 5))
    out, res = run(p, feats([0.02] * 60))
    # Phase 1: +2%/day reaches 10% on day index 4. Handover 2 days -> trading resumes on index 6; phase 2 needs
    # 5% (3 days) but also 4 trading days -> index 9. Funded after the 5-day handover.
    assert out.pass_day[0].tolist() == [4, 9]
    assert res["pass_all_rate"] == 1.0
    assert out.funded_day[0] == 9 + 5


def test_minimum_trading_days_delay_a_fast_pass():
    out, _ = run(base_programme(), feats([0.20] + [0.0005] * 30, opened=[1] * 31))
    assert out.pass_day[0, 0] == 3  # target met on day 0 but 4 trading days needed


def test_daily_loss_breaches_exactly_at_the_limit():
    p = base_programme()
    out, res = run(p, feats([0.0, 0.0], low=[-0.05, 0.0]))
    assert out.breach_cause[0] == 1 and res["breaches"]["daily_loss"]["rate"] == 1.0
    out, _ = run(p, feats([0.0, 0.0], low=[-0.0499, 0.0]))
    assert out.breach_cause[0] == 0


def test_static_max_loss_counts_accumulated_losses():
    out, _ = run(base_programme(), feats([-0.03, -0.03, -0.03, -0.015, 0.0]))
    assert out.breach_cause[0] == 2  # 1 - 0.09 - 0.015 intraday low would be -10.5%


def test_eod_trailing_floor_follows_the_high_water_mark():
    p = base_programme(max_loss_type="eod_trailing", max_loss_pct=4.0, daily_loss_pct=None,
                       phases=(Phase("Challenge", 50, 0),))
    out, _ = run(p, feats([0.03, 0.03, -0.035, -0.01]))
    assert out.breach_cause[0] == 2  # trailing floor 1.06 - 0.04 = 1.02, balance 1.025 then 1.015
    static = replace(p, max_loss_type="static")
    assert run(static, feats([0.03, 0.03, -0.035, -0.01]))[0].breach_cause[0] == 0


def test_best_day_consistency_blocks_the_pass_until_satisfied():
    p = base_programme(phases=(Phase("Challenge", 10, 0),), consistency_best_day_pct=50.0)
    out, _ = run(p, feats([0.12, 0.01, 0.01, 0.05, 0.08]))
    assert out.pass_day[0, 0] == 4  # best day 0.12 must be <= 50% of positive-day profit (0.27 total)


def test_time_limit_expires_an_unfinished_phase():
    p = base_programme(phases=(Phase("Challenge", 10, 0, time_limit_days=5),))
    out, res = run(p, feats([0.001] * 20))
    assert out.breach_cause[0] == 3 and res["breaches"]["time_limit"]["rate"] == 1.0


def test_instant_account_pays_out_on_cadence_and_refunds_fee_once():
    p = base_programme(phases=(), daily_loss_pct=None, max_loss_type="eod_trailing_lock_initial", max_loss_pct=6.0,
                       payout=Payout(split_pct=80, first_after_days=14, every_days=14, min_usd=50, fee_refund=True))
    out, res = run(p, feats([0.001] * 60), fee=100.0)
    assert out.payouts[0] == 4  # days 14, 28, 42, 56
    assert res["payout"]["expected_payout_usd"] == pytest.approx(4 * 0.8 * 0.014 * 10_000)
    assert res["payout"]["expected_value_usd"] == pytest.approx(res["payout"]["expected_payout_usd"])


def test_bootstrap_indices_are_reproducible_blocks():
    cfg = SimConfig(account_size=10_000, fee=None, paths=50, horizon_days=100, block_days=10, seed=7)
    a, b = sample_indices(300, cfg), sample_indices(300, cfg)
    assert a.shape == (50, 100) and (a == b).all()
    assert (np.diff(a[:, :10], axis=1) == 1).all()  # whole calendar blocks


# ---- ledger ----------------------------------------------------------------------------------------------------
def T(ea, day, hour, dur_h, r, volume=0.10, risk=100.0):  # noqa: N802
    opened = datetime(2026, 1, day, hour)
    return LedgerTrade(ea, "XAUUSD", opened, opened + timedelta(hours=dur_h), r, volume, risk)


def test_daily_loss_guard_skips_later_entries_the_same_day():
    ledgers = {"a": (T("a", 5, 8, 1, -1.0), T("a", 5, 10, 1, -1.0), T("a", 5, 12, 1, 2.0))}
    none = build_features(ledgers, [Selection("a", 1.0)], 10_000, Guards(), date(2026, 1, 1), date(2026, 1, 10))
    assert none.skipped == {} and none.pnl.sum() == pytest.approx(0.0)  # -1%, -1%, +2%
    # 1.5% guard: after two closed losses (-2%) the 12:00 entry is blocked.
    f = build_features(ledgers, [Selection("a", 1.0)], 10_000, Guards(daily_stop_pct=1.5),
                       date(2026, 1, 1), date(2026, 1, 10))
    assert f.skipped == {"daily loss guard": 1} and f.pnl.sum() == pytest.approx(-0.02)
    # 1.0% guard: the first closed loss already reaches it, so both later entries are blocked.
    f = build_features(ledgers, [Selection("a", 1.0)], 10_000, Guards(daily_stop_pct=1.0),
                       date(2026, 1, 1), date(2026, 1, 10))
    assert f.skipped == {"daily loss guard": 2} and f.pnl.sum() == pytest.approx(-0.01)


def test_lot_rounding_skips_trades_below_minimum_and_scales_the_rest():
    ledgers = {"a": (T("a", 5, 8, 1, 1.0, volume=0.01, risk=100.0), T("a", 6, 8, 1, 1.0, volume=0.30, risk=100.0))}
    f = build_features(ledgers, [Selection("a", 0.25)], 10_000, Guards(), date(2026, 1, 1), date(2026, 1, 10))
    assert f.skipped == {"below minimum lot": 1}
    assert f.pnl.sum() == pytest.approx(0.0025 * (0.07 / 0.075))  # 0.075 lots wanted -> 0.07 traded


def test_envelope_counts_carried_positions_on_quiet_days():
    ledgers = {"a": (T("a", 2, 10, 24 * 4, -1.0),)}
    f = build_features(ledgers, [Selection("a", 1.0)], 10_000, Guards(), date(2026, 1, 1), date(2026, 1, 10))
    assert f.low_envelope[1:6].tolist() == pytest.approx([-0.01] * 5)
    assert f.low_closed[1:5].tolist() == [0.0] * 4 and f.low_closed[5] == pytest.approx(-0.01)


def test_hold_time_rule_voids_short_winning_trades_only():
    ledgers = {"a": (T("a", 5, 8, 0.01, 1.0), T("a", 6, 8, 0.01, -1.0), T("a", 7, 8, 2, 1.0))}
    f = build_features(ledgers, [Selection("a", 1.0)], 10_000, Guards(), date(2026, 1, 1), date(2026, 1, 10), 120)
    assert f.pnl.sum() == pytest.approx(0.0)  # +1% voided, -1% kept, +1% kept


# ---- compatibility ---------------------------------------------------------------------------------------------
def profile(**kw):
    base = dict(slug="x", label="X", symbol="XAUUSD", timeframe="H1", mode="standard", start=date(2024, 1, 1),
                end=date(2026, 1, 1), trades=100, weekend_holds=False, weekend_hold_share=0.0, news_ea=False,
                straddle=False, short_trade_share=0.0, evidence_status="Validated evidence")
    base.update(kw)
    return EaProfile(**base)


def test_compatibility_rules():
    std, swing, e8 = get_programme("ftmo-2step-standard"), get_programme("ftmo-2step-swing"), get_programme("e8-one-4pct")
    assert compatibility(std, profile(weekend_holds=True, weekend_hold_share=0.4)).status == "blocked"
    assert compatibility(std, profile(weekend_holds=True, weekend_hold_share=0.02)).status == "adjusted"
    assert compatibility(swing, profile(weekend_holds=True, weekend_hold_share=0.4)).status == "ok"
    assert compatibility(std, profile(news_ea=True)).status == "blocked"
    assert compatibility(e8, profile(news_ea=True, straddle=True)).status == "blocked"
    assert compatibility(get_programme("fxify-two-phase"), profile()).status == "approval"


# ---- public API ------------------------------------------------------------------------------------------------
def test_page_and_catalog_render():
    assert client.get("/prop-simulator").status_code == 200
    cat = client.get("/api/prop-sim/catalog").json()
    assert len(cat["programmes"]) >= 14 and len(cat["eas"]) >= 30
    assert not any(p['id']=='ftmo13' for p in cat['presets'])  # New Gold targets require a fresh guarded-package replay.


def test_custom_ledger_replay_returns_both_equity_modes_and_standard_stats():
    _prop_limiter._hits.clear()
    body = {"programme_id": 'ftmo-2step-swing', "account_size": 10000,
            "eas": [{'slug':'ema3','risk_pct':0.5},{'slug':'nasdaq-overnight','risk_pct':0.5}], "paths": 300}
    res = client.post("/api/prop-sim/run", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    c, o = data["results"]["conservative"], data["results"]["optimistic"]
    assert 0 <= c["pass_all_rate"] <= o["pass_all_rate"] + 0.02 <= 1.02
    assert c["breaches"]["max_loss"]["rate"] >= o["breaches"]["max_loss"]["rate"]
    stats = data["stats"]
    assert {"trades", "trades_per_month", "trades_per_day", "profit_factor", "win_rate_pct", "sharpe_annualized",
            "max_balance_dd_pct", "avg_win_streak", "max_loss_streak"} <= set(stats)


def test_invalid_and_incompatible_requests_are_rejected(monkeypatch):
    _prop_limiter._hits.clear()
    bad = client.post("/api/prop-sim/run", json={"programme_id": "ftmo-2step-swing", "account_size": 10000, "eas": []})
    assert bad.status_code == 422
    wrong_size = client.post("/api/prop-sim/run", json={"programme_id": "ftmo-2step-swing", "account_size": 12345,
                                                        "eas": [{"slug": "ema3", "risk_pct": 0.5}]})
    assert wrong_size.status_code == 422 and "account sizes" in wrong_size.json()["detail"]
    # Isolate rule rejection from the current news cache's unavailable sizing evidence.
    from app.prop_sim import service
    monkeypatch.setattr(service, "load_ea", lambda slug, period, mode=None:
                        (profile(news_ea=True, straddle=True), (T(slug, 5, 8, 1, 1.0),)))
    blocked = client.post("/api/prop-sim/run", json={"programme_id": "ftmo-2step-standard", "account_size": 10000,
                                                     "eas": [{"slug": "news-pulse-xau", "risk_pct": 0.5}]})
    assert blocked.status_code == 422 and "cannot run" in blocked.json()["detail"]


def test_rate_limit_protects_the_public_endpoint():
    _prop_limiter._hits.clear()
    body = {"programme_id": "ftmo-2step-swing", "account_size": 10000, "eas": [{"slug": "ema3", "risk_pct": 0.5}],
            "paths": 100}
    codes = [client.post("/api/prop-sim/run", json=body).status_code for _ in range(21)]
    assert codes[:20] == [200] * 20 and codes[20] == 429
    _prop_limiter._hits.clear()
