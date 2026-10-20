"""Synthetic fixtures only: no real archives, terminal, network, or outcomes."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


spec = importlib.util.spec_from_file_location("btc_weekend_pipeline_search", Path(__file__).with_name("search.py"))
search = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = search
assert spec.loader is not None
spec.loader.exec_module(search)

DT = np.dtype([("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8"), ("spread", "i4")])
SPLIT = {"development": {"start": "2026-01-01", "end_exclusive": "2027-01-01"}, "validation": {"start": "2027-01-01", "end_exclusive": "2028-01-01"}, "oos": {"start": "2028-01-01", "end_exclusive": "2030-01-01"}}


def epoch(text):
    return int(datetime.fromisoformat(text).timestamp())


def bars(times):
    result = np.zeros(len(times), dtype=DT)
    result["time"] = times
    result["open"], result["high"], result["low"], result["close"] = 100, 100.2, 99.8, 100.1
    result["tick_volume"], result["spread"] = 10, 100
    return result


@pytest.fixture
def weekend():
    entry = epoch("2026-07-03T21:00:00+00:00")
    leave = epoch("2026-07-05T21:00:00+00:00")
    data = bars(np.arange(entry - 1200 * 300, leave + 300, 300))
    return entry, leave, data


def make_engine(data, tmp_path=None, cap=1500):
    return search.WeekendEngine({5: data}, {"search": {"max_unique_configurations": cap}}, SPLIT, root=tmp_path)


def trade_for(data, config, entry, leave):
    engine = make_engine(data)
    return engine.panel(config, entry, leave + 300, include_paths=True)


def test_inactive_parameters_deduplicate_to_one_baseline():
    changed = {**search.BASELINE, "timeframe_minutes": 1440, "stop_value": 5, "target_rr": 6, "management_mode": 2, "management_value": 4}
    assert search.config_id(changed) == search.config_id(search.BASELINE)
    assert asdict(search.canonical(changed)) == search.BASELINE


def test_numerically_equivalent_integer_and_float_parameters_deduplicate():
    integer = {**search.BASELINE, "stop_mode": 1, "stop_value": 2, "target_rr": 1}
    floating = {**integer, "timeframe_minutes": 5.0, "stop_value": 2.0, "target_rr": 1.0}
    assert search.config_id(integer) == search.config_id(floating)


@pytest.mark.parametrize("field,value", [("timeframe_minutes", 7), ("entry_mode", 5), ("stop_mode", 7), ("management_mode", 9), ("filter_mode", 9), ("entry_minute_ny", -1), ("exit_minute_ny", 1440), ("stop_value", float("nan"))])
def test_invalid_configuration_rejected(field, value):
    with pytest.raises(ValueError):
        search.canonical({**search.BASELINE, field: value})


@pytest.mark.parametrize("start,end,hours", [("2026-03-06T00:00:00+00:00", "2026-03-10T00:00:00+00:00", 47), ("2026-10-30T00:00:00+00:00", "2026-11-03T00:00:00+00:00", 49), ("2026-07-03T00:00:00+00:00", "2026-07-07T00:00:00+00:00", 48)])
def test_wall_clock_schedule_handles_dst(start, end, hours):
    rows = list(search.schedule(epoch(start), epoch(end), search.Configuration()))
    assert len(rows) == 1
    assert (rows[0][2] - rows[0][1]) / 3600 == hours


def test_sma_atr_uses_prior_close_and_exact_fourteen_bar_seed():
    data = bars(np.arange(20) * 300)
    data["high"], data["low"], data["close"] = 102, 98, 100
    data["open"][1], data["high"][1], data["low"][1], data["close"][1] = 110, 111, 109, 110
    tr = search.true_range(data)
    assert tr[0] == 4 and tr[1] == 11 and tr[2] == 12
    atr = search.sma(tr, 14)
    assert np.isnan(atr[:13]).all()
    assert atr[13] == pytest.approx(tr[:14].mean())


def test_wilder_adx_has_explicit_seed_and_no_future_dependency():
    data = bars(np.arange(60) * 300)
    data["open"] = np.arange(60) + 100
    data["high"], data["low"], data["close"] = data["open"] + 2, data["open"] - 1, data["open"] + 1
    adx, plus, minus = search.wilder_adx(data)
    assert np.isnan(adx[:26]).all()
    assert adx[26] == pytest.approx(100)
    assert plus[26] > minus[26] == 0
    future = data.copy()
    future["high"][40:] = 10000
    future["low"][40:] = 1
    changed = search.wilder_adx(future)[0]
    assert np.array_equal(adx[:40], changed[:40], equal_nan=True)


def test_expanding_percentile_excludes_current_and_future_values():
    data = bars(np.arange(100) * 300)
    feature = search.Features(data, 5)
    feature.cache["atr"] = np.arange(100, dtype=float)
    before = feature.percentile(80)
    assert before == 100
    feature.cache["atr"][81:] = -9999
    feature.percentiles.clear()
    assert feature.percentile(80) == before
    assert np.isnan(feature.percentile(40))


def test_expanding_percentile_excludes_historical_incomplete_atr_lookbacks():
    data = bars(np.arange(120) * 300)
    complete = np.ones(120, dtype=bool)
    complete[20] = False
    feature = search.Features(data, 5, complete=complete)
    feature.cache["atr"] = np.ones(120)
    feature.cache["atr"][20:34] = 999
    feature.cache["atr"][100] = 2
    assert feature.percentile(100) == 100
    complete[100] = False
    invalid_current = search.Features(data, 5, complete=complete)
    invalid_current.cache["atr"] = np.ones(120)
    assert np.isnan(invalid_current.percentile(100))


def test_feature_lookup_never_uses_an_unclosed_timeframe_bar():
    data = bars(np.array([0, 3600, 7200]))
    feature = search.Features(data, 60)
    assert feature.at(3599) == -1
    assert feature.at(3600) == 0
    assert feature.at(7199) == 0
    assert feature.at(7200) == 1


def test_timestamp_cache_is_contiguous_without_changing_values_or_lookups(weekend):
    _, _, data = weekend
    assert not data["time"].flags.c_contiguous
    engine = make_engine(data)
    feature = engine.features(5)
    for cached, strided in ((engine.m5_times, engine.data[5]["time"]), (feature.open_times, feature.bars["time"])):
        assert cached.flags.c_contiguous
        assert cached.dtype == strided.dtype
        assert np.array_equal(cached, strided)
        for side in ("left", "right"):
            for at in (int(strided[0]) - 1, int(strided[0]), int(strided[len(strided) // 2]) + 1, int(strided[-1]) + 1):
                assert np.searchsorted(cached, at, side=side) == np.searchsorted(strided, at, side=side)


@pytest.mark.parametrize("overrides", [
    {},
    {"stop_mode": 2, "stop_value": 2, "target_rr": 1.5},
    {"timeframe_minutes": 60, "stop_mode": 1, "stop_value": 2, "management_mode": 4, "management_value": 2},
    {"timeframe_minutes": 15, "stop_mode": 3, "entry_mode": 1, "filter_mode": 1},
    {"filter_mode": 7, "filter_value": 2},
    {"stop_mode": 2, "stop_value": 1, "management_mode": 5},
])
def test_contiguous_timestamp_performance_cache_preserves_whole_panel(weekend, overrides):
    entry, leave, data = weekend
    shift = np.arange(len(data)) * .01
    data["open"] += shift
    data["high"] += shift
    data["low"] += shift
    data["close"] += shift
    cfg = {**search.BASELINE, **overrides}
    optimized = make_engine(data)
    legacy = make_engine(data)
    # Re-create the exact old strided lookup representation, not a different
    # strategy implementation.  Both must produce identical full receipts.
    legacy.time_arrays = {minutes: values["time"] for minutes, values in legacy.data.items()}
    legacy.m5_times = legacy.time_arrays[5]
    old_features = legacy.features(search.canonical(cfg).timeframe_minutes)
    old_features.open_times = old_features.bars["time"]
    expected = legacy.panel(cfg, entry, leave + 300, include_paths=True)
    actual = optimized.panel(cfg, entry, leave + 300, include_paths=True)
    assert actual == expected


def test_baseline_uses_open_not_later_high_low_or_close(weekend):
    entry, leave, data = weekend
    data["high"] = 999
    data["low"] = 1
    data["close"] = 700
    data["open"][-1] = 110
    panel = trade_for(data, search.BASELINE, entry, leave)
    row = panel["trades"][0]
    assert row["return_per_notional"] == pytest.approx(0.1)
    assert row["initial_stop_fraction"] is None
    assert row["exit_epoch"] == leave
    assert row["observed_spread_proxy_return"] == pytest.approx(110 / 101 - 1)


def test_ambiguous_stop_target_is_stop_first_and_intrabar_time_is_not_fabricated(weekend):
    entry, leave, data = weekend
    i = np.searchsorted(data["time"], entry)
    data["high"][i], data["low"][i] = 102, 98
    cfg = {**search.BASELINE, "stop_mode": 2, "stop_value": 1, "target_rr": 1}
    row = trade_for(data, cfg, entry, leave)["trades"][0]
    assert row["exit_price"] == 99
    assert row["bar_ambiguous"] is True
    assert row["return_per_notional"] == pytest.approx(-0.01)
    assert row["exit_interval_start"] == entry and row["exit_interval_end"] == entry + 299


@pytest.mark.parametrize("opening,expected,reason", [(98, 98, "SL opening gap"), (103, 101, "TP opening gap")])
def test_opening_gap_stop_fills_worse_open_and_target_is_conservative(weekend, opening, expected, reason):
    entry, leave, data = weekend
    i = np.searchsorted(data["time"], entry) + 1
    data["open"][i], data["high"][i], data["low"][i] = opening, opening + 0.1, opening - 0.1
    cfg = {**search.BASELINE, "stop_mode": 2, "stop_value": 1, "target_rr": 1}
    row = trade_for(data, cfg, entry, leave)["trades"][0]
    assert row["exit_price"] == expected
    assert row["exit_epoch"] == entry + 300
    assert row["exit_reason"].startswith(reason)


def test_sunday_deadline_does_not_use_later_sunday_bar_extremes(weekend):
    entry, leave, data = weekend
    data["open"][-1], data["high"][-1], data["low"][-1] = 101, 1000, 1
    cfg = {**search.BASELINE, "stop_mode": 2, "stop_value": 5, "target_rr": 3}
    row = trade_for(data, cfg, entry, leave)["trades"][0]
    assert row["exit_reason"] == "Sunday scheduled OPEN"
    assert row["exit_price"] == 101


def test_break_even_ignores_pre_entry_profitable_close_and_uses_only_completed_updates(weekend):
    entry, leave, data = weekend
    i = np.searchsorted(data["time"], entry)
    data["high"][i - 1], data["close"][i - 1] = 120, 120
    data["open"][-1], data["high"][-1], data["low"][-1] = 99.5, 99.6, 99.4
    cfg = {**search.BASELINE, "stop_mode": 2, "stop_value": 1, "management_mode": 1, "management_value": 1}
    row = trade_for(data, cfg, entry, leave)["trades"][0]
    assert row["exit_reason"] == "Sunday scheduled OPEN"
    assert row["exit_price"] == 99.5


def test_break_even_updates_after_completed_close_not_that_candles_future_high(weekend):
    entry, leave, data = weekend
    i = np.searchsorted(data["time"], entry)
    data["high"][i], data["close"][i] = 102.2, 102
    data["open"][i + 1], data["high"][i + 1], data["low"][i + 1] = 100.5, 100.6, 99.9
    cfg = {**search.BASELINE, "stop_mode": 2, "stop_value": 1, "management_mode": 1, "management_value": 1}
    row = trade_for(data, cfg, entry, leave)["trades"][0]
    assert row["exit_price"] == 100
    assert row["exit_interval_start"] == entry + 300


def test_missing_exact_price_is_not_a_zero_or_later_fill(weekend):
    entry, leave, data = weekend
    data = data[data["time"] != entry]
    panel = trade_for(data, search.BASELINE, entry, leave)
    assert not panel["trades"]
    assert panel["missing_week_ids"] == ["2026-07-03"]
    assert panel["weekly_returns"]["2026-07-03"] is None


def test_intrahold_gap_retains_descriptive_return_but_blocks_evidence_and_bootstrap(weekend):
    entry, leave, data = weekend
    data = data[data["time"] != entry + 300]
    panel = trade_for(data, search.BASELINE, entry, leave)
    assert len(panel["trades"]) == 1
    assert panel["trades"][0]["missing_bar_count"] == 1
    assert panel["metrics"]["coverage_evidence_pass"] is False
    assert panel["weekly_returns"]["2026-07-03"] is None
    assert panel["missing_week_ids"] == ["2026-07-03"]


def test_incomplete_tf_constituent_is_missing_not_profitable_filter_skip(weekend):
    entry, leave, data = weekend
    data = data[data["time"] != entry - 300]
    cfg = {**search.BASELINE, "timeframe_minutes": 60, "entry_mode": 1}
    panel = trade_for(data, cfg, entry, leave)
    assert not panel["trades"]
    assert panel["weekly_returns"]["2026-07-03"] is None
    assert panel["metrics"]["coverage_evidence_pass"] is False


def test_initial_indicator_warmup_is_known_no_entry_zero_not_missing_prices(weekend):
    entry, leave, data = weekend
    cfg = {**search.BASELINE, "timeframe_minutes": 1440, "filter_mode": 2}
    panel = trade_for(data, cfg, entry, leave)
    assert not panel["trades"]
    assert panel["weekly_returns"]["2026-07-03"] == 0
    assert panel["missing_week_ids"] == []
    assert panel["filtered_details"][0]["reason"].startswith("warmup")


def test_entire_missing_latest_tf_interval_never_uses_stale_closed_feature(weekend):
    entry, leave, data = weekend
    # Remove the complete hour immediately preceding an exact21:00 entry.
    data = data[(data["time"] < entry - 3600) | (data["time"] >= entry)]
    cfg = {**search.BASELINE, "timeframe_minutes": 60, "entry_mode": 1}
    panel = trade_for(data, cfg, entry, leave)
    assert not panel["trades"]
    assert panel["weekly_returns"]["2026-07-03"] is None
    assert "stale" in panel["missing_details"][0]["reason"]


def test_unknown_historical_spread_is_never_replaced_or_treated_as_passing_cap(weekend):
    entry, leave, data = weekend
    data["spread"] = 0
    cfg = {**search.BASELINE, "filter_mode": 7, "filter_value": 0.05}
    panel = trade_for(data, cfg, entry, leave)
    assert not panel["trades"]
    assert panel["weekly_returns"]["2026-07-03"] is None
    ordinary = trade_for(data, search.BASELINE, entry, leave)
    assert ordinary["trades"][0]["observed_spread_proxy_return"] is None


def test_spread_filter_uses_only_immediately_completed_m5_not_entry_bar_future_spread(weekend):
    entry, leave, data = weekend
    i = np.searchsorted(data["time"], entry)
    data["spread"][i - 1] = 1
    data["spread"][i:] = 999999
    cfg = {**search.BASELINE, "filter_mode": 7, "filter_value": 0.02}
    allowed = trade_for(data, cfg, entry, leave)
    assert len(allowed["trades"]) == 1
    data["spread"][i - 1] = 10000
    data["spread"][i:] = 1
    rejected = trade_for(data, cfg, entry, leave)
    assert not rejected["trades"]
    assert rejected["weekly_returns"]["2026-07-03"] == 0


def test_incomplete_current_weekend_is_censored_not_bootstrap_zero(weekend):
    entry, leave, data = weekend
    panel = make_engine(data).panel(search.BASELINE, entry, leave - 86400)
    assert panel["scheduled_week_ids"] == [] and panel["weekly_returns"] == {}
    assert panel["censored_incomplete_week_ids"] == ["2026-07-03"]


def test_oos_rejected_before_freeze_and_unfrozen_candidate_is_always_rejected(weekend, tmp_path):
    _, _, data = weekend
    engine = make_engine(data, tmp_path)
    with pytest.raises(PermissionError):
        engine.panel(search.BASELINE, "2028-01-01", "2028-02-01")
    with pytest.raises(PermissionError):
        engine.panel(search.BASELINE, "2028-01-01", "2028-02-01", allow_oos=True)
    (tmp_path / "FROZEN.json").write_text(json.dumps({"selected_config": search.BASELINE, "baseline_config": search.BASELINE, "locked": {}}))
    with pytest.raises(PermissionError):
        engine.panel({**search.BASELINE, "entry_mode": 1}, "2028-01-01", "2028-02-01", allow_oos=True)


def test_frozen_inputs_must_match_before_oos_authorization(weekend, tmp_path):
    _, _, data = weekend
    engine = make_engine(data, tmp_path)
    names = ["PLAN.json", "data-split.json", "search.py", "SEARCH RESULTS.json", "SELECTION.json", "DATA.json"]
    hashes = {}
    for name in names:
        (tmp_path / name).write_text(json.dumps({"selected_config": search.BASELINE}) if name == "SELECTION.json" else "frozen fixture")
        hashes[name] = search.digest(tmp_path / name)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "BTCUSD-M5.npz").write_bytes(b"fixture bytes, not a price archive")
    frozen = {"selected_config": search.BASELINE, "baseline_config": search.BASELINE, "locked": {"files": hashes, "source_hashes": {"BTCUSD-M5.npz": search.digest(tmp_path / "data" / "BTCUSD-M5.npz")}}}
    (tmp_path / "FROZEN.json").write_text(json.dumps(frozen))
    engine._authorize_window(search.Configuration(), epoch("2028-02-01T00:00:00+00:00"), True)
    (tmp_path / "PLAN.json").write_text("changed fixture")
    with pytest.raises(PermissionError):
        engine._authorize_window(search.Configuration(), epoch("2028-02-01T00:00:00+00:00"), True)


def test_registration_counts_actual_unique_parameters_and_cap_is_hard(weekend, monkeypatch):
    _, _, data = weekend
    engine = make_engine(data, cap=1)
    monkeypatch.setattr(engine, "panel", lambda *args, **kwargs: {"metrics": {"fixture": True}})
    first = engine.register(search.BASELINE, "first")
    second = engine.register({**search.BASELINE, "timeframe_minutes": 60}, "duplicate")
    assert first is second and len(engine.trials) == 1
    assert first["stages"] == ["first", "duplicate"]
    with pytest.raises(RuntimeError):
        engine.register({**search.BASELINE, "entry_mode": 1}, "over cap")


def test_profit_factor_undefined_without_losses_and_closed_dd_includes_initial_cash():
    records = [{"return_per_notional": value, "bar_ambiguous": False} for value in (-0.1, 0.2, -0.1)]
    stats = search.summarize(records, 0, 365 * 86400)
    assert stats["closed_dd_pct"] == pytest.approx(10)
    assert stats["return_pct"] == pytest.approx(-2.8)
    assert stats["profit_factor"] == pytest.approx(1800 / 2080)
    wins = search.summarize([{"return_per_notional": 0.01}], 0, 365 * 86400)
    assert wins["profit_factor"] is None


def test_short_timeframes_require_full_comparable_m1_coverage(weekend):
    _, _, data = weekend
    engine = make_engine(data)
    assert 1 not in engine.available_timeframes and 3 not in engine.available_timeframes
    with pytest.raises(ValueError):
        engine.features(1)


def test_neighborhood_is_joint_clock_offsets_and_adjacent_registered_stop_rr(weekend):
    _, _, data = weekend
    engine = make_engine(data)
    cfg = {**search.BASELINE, "stop_mode": 1, "stop_value": 2, "target_rr": 1.5}
    candidates = engine.neighbours(cfg)
    timing = {(candidate.entry_minute_ny, candidate.exit_minute_ny) for candidate in candidates}
    assert {(a, b) for a in (1005, 1020, 1035) for b in (1005, 1020, 1035)}.issubset(timing)
    assert {1.5, 2, 3}.issubset({candidate.stop_value for candidate in candidates})
    assert {1.25, 1.5, 2}.issubset({candidate.target_rr for candidate in candidates})


def test_missing_neighbor_scores_cannot_boost_plateau_or_count_as_positive_votes():
    rows = [{"config_id": str(index), "metrics": {"coverage_evidence_pass": index < 3, "return_pct": 10, "score": index + 1 if index < 3 else 99999}} for index in range(5)]
    stats = search.plateau_statistics(rows)
    assert stats["positive_neighbours"] == 3 and stats["total_neighbours"] == 5
    assert stats["median_score"] == 1
    assert stats["coverage_valid_neighbours"] == 3
    assert stats["missing_neighbour_ids"] == ["3", "4"]
    assert stats["majority_positive"] is True
    assert "INCLUDING centre" in stats["neighbourhood_scope"]


def test_majority_missing_neighbors_make_plateau_unavailable_not_finite_or_profitable():
    rows = [{"config_id": str(index), "metrics": {"coverage_evidence_pass": index < 2, "return_pct": 99, "score": 99999}} for index in range(5)]
    stats = search.plateau_statistics(rows)
    assert stats["positive_neighbours"] == 2
    assert stats["majority_positive"] is False
    assert stats["median_score"] is None


def test_failed_validation_freezes_best_development_not_best_validation(weekend, monkeypatch):
    _, _, data = weekend
    engine = make_engine(data)
    first = {"config": search.BASELINE, "config_id": search.config_id(search.BASELINE), "median_score": 10, "majority_positive": True, "metrics": {"eligible_development": True}}
    other_cfg = {**search.BASELINE, "entry_mode": 1}
    second = {"config": other_cfg, "config_id": search.config_id(other_cfg), "median_score": 9, "majority_positive": True, "metrics": {"eligible_development": True}}
    def panel(config, *_args, **_kwargs):
        return {"metrics": {"trades": 2, "losses": 0, "profit_factor": None, "return_pct": 50 if config == other_cfg else 1, "score": 50 if config == other_cfg else 1}}
    monkeypatch.setattr(engine, "panel", panel)
    result = engine.validate_finalists({"finalists": [first, second]})
    assert result["selected_config_id"] == first["config_id"]
    assert result["selection_status"] == "FAILED_VALIDATION_EXPLORATORY_ONLY"
    assert result["oos_read_for_selection"] is False
