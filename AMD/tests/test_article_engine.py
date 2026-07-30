from dataclasses import replace
from datetime import date, datetime, timezone

import pandas as pd

from amd_bot.article_engine import ArticleParams, article_candidates_for_day
from amd_bot.config import load_config
from amd_bot.live import build_article_signal


def _day_frame() -> pd.DataFrame:
    times = pd.date_range(
        "2026-07-30T00:00:00Z",
        "2026-07-30T12:00:00Z",
        freq="min",
        inclusive="left",
    )
    frame = pd.DataFrame(
        {
            "time": times,
            "open": 105.0,
            "high": 106.0,
            "low": 104.0,
            "close": 105.0,
            "spread": 1,
            "tick_volume": 10,
        }
    )
    frame.loc[10, "high"] = 110.0
    frame.loc[20, "low"] = 100.0
    return frame


def test_distribution_requires_breakout_then_confirmed_retest() -> None:
    frame = _day_frame()
    breakout = frame["time"].between(
        "2026-07-30T08:00:00Z",
        "2026-07-30T08:04:00Z",
    )
    frame.loc[breakout, ["open", "high", "low", "close"]] = [
        109.5,
        111.5,
        109.0,
        111.0,
    ]
    retest = frame["time"].between(
        "2026-07-30T08:05:00Z",
        "2026-07-30T08:09:00Z",
    )
    frame.loc[retest, ["open", "high", "low", "close"]] = [
        110.2,
        111.2,
        109.8,
        110.8,
    ]
    config = replace(load_config(), regime_filter_enabled=False)
    params = ArticleParams(
        enable_fade=False,
        enable_distribution=True,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        distribution_rr=1.5,
        breakout_fraction=0.0,
        retest_tolerance_fraction=0.04,
        stop_buffer_fraction=0.03,
    )
    candidates, asia_high, asia_low = article_candidates_for_day(
        frame,
        0.01,
        config,
        params,
        date(2026, 7, 30),
    )
    assert asia_high == 110.0
    assert asia_low == 100.0
    assert len(candidates) == 1
    assert candidates[0].phase == "london_distribution"
    assert candidates[0].side == "buy"
    assert candidates[0].entry_time == pd.Timestamp(
        "2026-07-30T08:10:00Z"
    )


def test_fade_requires_sweep_and_close_back_inside() -> None:
    frame = _day_frame()
    sweep = frame["time"].between(
        "2026-07-30T08:00:00Z",
        "2026-07-30T08:04:00Z",
    )
    frame.loc[sweep, ["open", "high", "low", "close"]] = [
        109.0,
        112.0,
        108.0,
        109.5,
    ]
    config = replace(load_config(), regime_filter_enabled=False)
    params = ArticleParams(
        enable_fade=True,
        enable_distribution=False,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        fade_rr=1.5,
        sweep_min_fraction=0.02,
        sweep_max_fraction=0.60,
        stop_buffer_fraction=0.03,
    )
    candidates, _, _ = article_candidates_for_day(
        frame,
        0.01,
        config,
        params,
        date(2026, 7, 30),
    )
    assert len(candidates) == 1
    assert candidates[0].phase == "london_fade"
    assert candidates[0].side == "sell"
    assert candidates[0].entry_time == pd.Timestamp(
        "2026-07-30T08:05:00Z"
    )


def test_live_signal_is_available_on_next_m1_open() -> None:
    frame = _day_frame()
    breakout = frame["time"].between(
        "2026-07-30T08:00:00Z",
        "2026-07-30T08:04:00Z",
    )
    frame.loc[breakout, ["open", "high", "low", "close"]] = [
        109.5,
        111.5,
        109.0,
        111.0,
    ]
    retest = frame["time"].between(
        "2026-07-30T08:05:00Z",
        "2026-07-30T08:09:00Z",
    )
    frame.loc[retest, ["open", "high", "low", "close"]] = [
        110.2,
        111.2,
        109.8,
        110.8,
    ]
    config = replace(
        load_config(),
        regime_filter_enabled=False,
        article_enable_fade=False,
        article_enable_distribution=True,
        article_trade_london=True,
        article_trade_new_york=False,
    )
    now = datetime(2026, 7, 30, 8, 10, 30, tzinfo=timezone.utc)
    signal, reason = build_article_signal(frame, 0.01, config, now)
    assert reason == "ready"
    assert signal is not None
    assert signal.phase == "london_distribution"
    assert signal.signal_time == datetime(
        2026, 7, 30, 8, 10, tzinfo=timezone.utc
    )
